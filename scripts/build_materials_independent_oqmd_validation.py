#!/usr/bin/env python3
"""Build an OQMD exact-structure diagnostic for materials A2 validation.

This script intentionally keeps the evidence boundary narrow:

* WBM/Matbench labels and public model predictions define the frozen PARC rows.
* OQMD is queried only after those rows are reconstructed.
* Primary matching requires exact reduced formula plus pymatgen StructureMatcher.
* Formula-only hits are counted as sensitivity/coverage diagnostics, not as
  independent FTR evidence.

Raw WBM structures and OQMD JSON responses are private inputs/caches. The public
milestone receives only public-safe candidate IDs, OQMD entry IDs, labels and
aggregate diagnostics.
"""

from __future__ import annotations

import argparse
import bz2
import concurrent.futures
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Composition, Lattice, Structure

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_materials_discovery_parc_flagship import (  # noqa: E402
    add_blocks,
    compute_evalues,
    element_list,
    load_materials_inputs,
    observed_positive_mask,
    scs_release_count,
    split_blocks,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs/milestones/materials_independent_dft_validation"
DEFAULT_PRIVATE = Path("/home/waas/paper_experiments/private/materials_independent_dft_validation")
DEFAULT_WBM_SUMMARY = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
DEFAULT_ALIGNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
DEFAULT_MEGNET = Path("/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
DEFAULT_STEP1 = Path(
    "/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2"
)
DEFAULT_STEP_DIR = Path("/home/waas/paper_experiments/private/wbm_raw_full")
OQMD_BASE = "http://oqmd.org/oqmdapi/formationenergy"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def load_frame(args: argparse.Namespace) -> pd.DataFrame:
    load_args = argparse.Namespace(
        wbm_summary=args.wbm_summary,
        primary_predictions=args.alignn_predictions,
        weak_predictions=args.megnet_predictions,
        primary_pred_col="e_form_per_atom_alignn_ff",
        weak_pred_col="e_form_per_atom_megnet",
        stability_threshold=0.0,
    )
    frame, _ = load_materials_inputs(load_args)
    return frame


def reconstruct_release_rows(frame: pd.DataFrame, *, alpha: float, rho: float, budget: int, seeds: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for seed in seeds:
        observed = observed_positive_mask(frame, "primary_score", rho=rho, seed=seed, strategy="top_score")
        cal_blocks, test_blocks = split_blocks(frame["composition_family_pair"].astype(str).tolist(), seed)
        test, diag = compute_evalues(
            frame,
            score_col="primary_score",
            block_col="composition_family_pair",
            observed_positive=observed,
            cal_blocks=cal_blocks,
            test_blocks=test_blocks,
            alpha=alpha,
        )
        pool = test.head(budget).copy()
        released, tau, margin, best_ratio = scs_release_count(pool["_evalue"].to_numpy(dtype=float), alpha=alpha, budget=budget)
        if released:
            selected_pos = np.argsort(pool["_evalue"].to_numpy(dtype=float))[::-1][:released]
            selected_ids = set(pool.iloc[selected_pos]["material_id"].astype(str))
        else:
            selected_ids = set()
        seed_rows.append(
            {
                "seed": seed,
                "K": budget,
                "alpha": alpha,
                "rho": rho,
                "released": int(released),
                "raw_topK_actual_FTR_wbm": float((~pool["stable_DFT"].astype(bool)).mean()) if len(pool) else math.nan,
                "PARC_actual_FTR_wbm": float((~pool[pool["material_id"].astype(str).isin(selected_ids)]["stable_DFT"].astype(bool)).mean())
                if selected_ids
                else 0.0,
                "best_mass_ratio": float(best_ratio),
                "required_e": float(diag["required_emax"]),
                "max_observed_e": float(pool["_evalue"].max()) if len(pool) else 0.0,
                "block_coverage": float(diag["block_coverage"]),
                "scs_tau": float(tau) if math.isfinite(tau) else math.inf,
                "scs_margin": float(margin),
            }
        )
        for rank, (_, row) in enumerate(pool.iterrows(), start=1):
            in_release = str(row["material_id"]) in selected_ids
            candidate_rows.append(
                {
                    "seed": seed,
                    "material_id": row["material_id"],
                    "formula": row["formula"],
                    "raw_rank": rank,
                    "raw_topK_member": True,
                    "parc_release_flag": bool(in_release),
                    "evalue": float(row["_evalue"]),
                    "score": float(row["primary_score"]),
                    "stable_DFT_wbm": bool(row["stable_DFT"]),
                    "e_above_hull_wbm": float(row["e_above_hull_mp2020_corrected_ppd_mp"]),
                    "composition_family_pair": row["composition_family_pair"],
                    "chemical_system": row["chemical_system"],
                    "wyckoff_family": row["wyckoff_family"],
                }
            )
    return pd.DataFrame(seed_rows), pd.DataFrame(candidate_rows)


def wbm_step_path(material_id: str, step1: Path, step_dir: Path) -> Path:
    step = int(str(material_id).split("-")[1])
    if step == 1:
        return step1
    return step_dir / f"step_{step}.json.bz2"


def load_step_entries_for_ids(material_ids: set[str], *, step1: Path, step_dir: Path) -> dict[str, dict[str, Any]]:
    by_step: dict[int, set[int]] = {}
    for mid in material_ids:
        parts = str(mid).split("-")
        if len(parts) != 3 or parts[0] != "wbm":
            continue
        by_step.setdefault(int(parts[1]), set()).add(int(parts[2]) - 1)

    out: dict[str, dict[str, Any]] = {}
    for step, indexes in sorted(by_step.items()):
        path = step1 if step == 1 else step_dir / f"step_{step}.json.bz2"
        if not path.exists():
            continue
        with bz2.open(path, "rt", encoding="utf-8") as handle:
            entries = json.load(handle)["entries"]
        for idx in sorted(indexes):
            if 0 <= idx < len(entries):
                out[f"wbm-{step}-{idx + 1}"] = entries[idx]
    return out


def parse_oqmd_structure(record: dict[str, Any]) -> Structure | None:
    try:
        lattice = Lattice(record["unit_cell"])
        species: list[str] = []
        coords: list[list[float]] = []
        for site in record.get("sites", []):
            specie, rest = str(site).split("@", 1)
            xyz = [float(value) for value in rest.split()[:3]]
            if len(xyz) != 3:
                return None
            species.append(specie.strip())
            coords.append(xyz)
        return Structure(lattice, species, coords)
    except Exception:
        return None


def query_oqmd(chemical_system: str, cache_dir: Path, *, timeout: int, sleep_seconds: float, retries: int) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = chemical_system.replace("-", "_")
    cache_path = cache_dir / f"{safe}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    params = urllib.parse.urlencode({"composition": chemical_system, "limit": 1000})
    url = f"{OQMD_BASE}?{params}"
    last_error = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
            if sleep_seconds:
                time.sleep(sleep_seconds)
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(min(2.0 * (attempt + 1), 10.0))
    payload = {"data": [], "meta": {"query_error": last_error, "query": url}}
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def match_candidates_to_oqmd(
    candidates: pd.DataFrame,
    entries: dict[str, dict[str, Any]],
    *,
    cache_dir: Path,
    timeout: int,
    sleep_seconds: float,
    retries: int,
    workers: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matcher = StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5,
        primitive_cell=True,
        scale=True,
        attempt_supercell=True,
    )
    unique_candidates = candidates.drop_duplicates("material_id").copy()
    rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    systems = sorted(str(system) for system in unique_candidates["chemical_system"].dropna().unique())
    payloads: dict[str, dict[str, Any]] = {}

    def fetch(system: str) -> tuple[str, dict[str, Any]]:
        return (
            system,
            query_oqmd(system, cache_dir, timeout=timeout, sleep_seconds=sleep_seconds, retries=retries),
        )

    if systems:
        print(f"Querying OQMD for {len(systems)} chemical systems with {workers} workers", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(fetch, system): system for system in systems}
        for done, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
            system, payload = future.result()
            payloads[system] = payload
            if done % 25 == 0 or done == len(systems):
                print(f"OQMD queries complete: {done}/{len(systems)}", flush=True)

    grouped = list(unique_candidates.groupby("chemical_system"))
    for group_pos, (chemical_system, group) in enumerate(grouped, start=1):
        payload = payloads.get(str(chemical_system), {"data": [], "meta": {"query_error": "missing_payload"}})
        records = payload.get("data", []) or []
        source_rows.append(
            {
                "source": "OQMD",
                "chemical_system": chemical_system,
                "api_records_returned": len(records),
                "api_query_error": payload.get("meta", {}).get("query_error", ""),
                "api_timestamp": payload.get("meta", {}).get("time_stamp", ""),
                "evidence_status": "queried_public_api" if records else "queried_public_api_no_records_or_error",
            }
        )
        oqmd_by_formula: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            try:
                reduced = Composition(record["composition"]).reduced_formula
            except Exception:
                continue
            oqmd_by_formula.setdefault(reduced, []).append(record)

        for _, cand in group.iterrows():
            material_id = str(cand["material_id"])
            entry = entries.get(material_id)
            if entry is None:
                rows.append(
                    {
                        "material_id": material_id,
                        "formula": cand["formula"],
                        "chemical_system": chemical_system,
                        "match_confidence": "missing_wbm_structure_private_input",
                        "oqmd_match_count": 0,
                        "oqmd_entry_ids": "",
                        "oqmd_stability_min": math.nan,
                        "oqmd_stable_exact": "",
                        "formula_only_candidate_count": 0,
                        "wbm_stable_DFT": bool(cand["stable_DFT_wbm"]),
                        "wbm_e_above_hull": float(cand["e_above_hull_wbm"]),
                    }
                )
                continue
            wbm_structure = Structure.from_dict(entry["structure"])
            reduced = wbm_structure.composition.reduced_formula
            formula_records = oqmd_by_formula.get(reduced, [])
            matches: list[dict[str, Any]] = []
            for record in formula_records:
                oqmd_structure = parse_oqmd_structure(record)
                if oqmd_structure is None:
                    continue
                try:
                    if matcher.fit(wbm_structure, oqmd_structure):
                        matches.append(record)
                except Exception:
                    continue
            stabilities = [float(record["stability"]) for record in matches if record.get("stability") is not None]
            stability_min = min(stabilities) if stabilities else math.nan
            rows.append(
                {
                    "material_id": material_id,
                    "formula": cand["formula"],
                    "chemical_system": chemical_system,
                    "match_confidence": "exact_structure_match" if matches else ("formula_only_no_structure_match" if formula_records else "no_formula_match"),
                    "oqmd_match_count": len(matches),
                    "oqmd_entry_ids": ";".join(str(record.get("entry_id", "")) for record in matches),
                    "oqmd_stability_min": stability_min,
                    "oqmd_stable_exact": bool(stability_min <= 0.0) if stabilities else "",
                    "formula_only_candidate_count": len(formula_records),
                    "wbm_stable_DFT": bool(cand["stable_DFT_wbm"]),
                    "wbm_e_above_hull": float(cand["e_above_hull_wbm"]),
                }
            )
        if group_pos % 50 == 0 or group_pos == len(grouped):
            print(f"OQMD structure matching complete: {group_pos}/{len(grouped)} systems", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(source_rows)


def summarize_seed_rows(candidate_rows: pd.DataFrame, matches: pd.DataFrame, *, alpha: float, budget: int) -> pd.DataFrame:
    joined = candidate_rows.merge(matches, on=["material_id", "formula", "chemical_system"], how="left")
    rows: list[dict[str, Any]] = []
    for seed, group in joined.groupby("seed"):
        raw_exact = group[group["match_confidence"].eq("exact_structure_match")].copy()
        parc_exact = raw_exact[raw_exact["parc_release_flag"].astype(bool)].copy()
        raw_ftr = float((~parc_bool(raw_exact["oqmd_stable_exact"])).mean()) if len(raw_exact) else math.nan
        parc_ftr = float((~parc_bool(parc_exact["oqmd_stable_exact"])).mean()) if len(parc_exact) else math.nan
        raw_n = int(len(raw_exact))
        parc_n = int(len(parc_exact))
        rows.append(
            {
                "domain": "materials_discovery",
                "source": "ALIGNN-FF",
                "external_label_source": "OQMD public API",
                "match_confidence": "exact_structure_match",
                "seed": int(seed),
                "K": budget,
                "alpha": alpha,
                "released": int(group["parc_release_flag"].sum()),
                "n_raw_topK_exact_matches": raw_n,
                "n_released_exact_matches": parc_n,
                "independent_FTR": parc_ftr,
                "raw_topK_independent_FTR": raw_ftr,
                "coverage_raw_topK": raw_n / float(budget) if budget else math.nan,
                "coverage_released": parc_n / float(group["parc_release_flag"].sum()) if group["parc_release_flag"].sum() else 0.0,
                "PARC_vs_raw_delta": raw_ftr - parc_ftr if math.isfinite(raw_ftr) and math.isfinite(parc_ftr) else math.nan,
                "evidence_status": "completed_independent_oqmd_exact_structure_diagnostic",
            }
        )
    return pd.DataFrame(rows)


def parc_bool(series: pd.Series) -> pd.Series:
    return series.map(lambda value: bool(value) if value != "" and pd.notna(value) else False).astype(bool)


def aggregate_primary(seed_rows: pd.DataFrame, candidate_rows: pd.DataFrame, matches: pd.DataFrame, *, min_coverage_primary: float) -> pd.DataFrame:
    joined_unique = candidate_rows.drop_duplicates("material_id").merge(
        matches, on=["material_id", "formula", "chemical_system"], how="left"
    )
    exact = joined_unique[joined_unique["match_confidence"].eq("exact_structure_match")]
    if len(exact):
        discordance = float((exact["wbm_stable_DFT"].astype(bool) != parc_bool(exact["oqmd_stable_exact"])).mean())
    else:
        discordance = math.nan
    mean_raw_cov = float(seed_rows["coverage_raw_topK"].mean()) if len(seed_rows) else 0.0
    mean_release_cov = float(seed_rows["coverage_released"].mean()) if len(seed_rows) else 0.0
    evidence_status = (
        "completed_independent_oqmd_exact_structure_evidence"
        if min(mean_raw_cov, mean_release_cov) >= min_coverage_primary
        else "completed_independent_oqmd_exact_structure_diagnostic_low_coverage"
    )
    return pd.DataFrame(
        [
            {
                "domain": "materials_discovery",
                "source": "ALIGNN-FF",
                "external_label_source": "OQMD public API",
                "match_confidence": "exact_structure_match",
                "K": int(seed_rows["K"].iloc[0]) if len(seed_rows) else "",
                "alpha": float(seed_rows["alpha"].iloc[0]) if len(seed_rows) else "",
                "n_seeds": int(seed_rows["seed"].nunique()) if len(seed_rows) else 0,
                "n_unique_raw_topK_candidates": int(candidate_rows["material_id"].nunique()),
                "n_unique_exact_structure_matches": int(len(exact)),
                "n_released_matched_mean": float(seed_rows["n_released_exact_matches"].mean()) if len(seed_rows) else math.nan,
                "independent_FTR": float(seed_rows["independent_FTR"].mean()) if len(seed_rows) else math.nan,
                "coverage_of_independent_source": mean_release_cov,
                "raw_topK_independent_FTR": float(seed_rows["raw_topK_independent_FTR"].mean()) if len(seed_rows) else math.nan,
                "raw_topK_coverage_of_independent_source": mean_raw_cov,
                "PARC_vs_raw_delta": float(seed_rows["PARC_vs_raw_delta"].mean()) if len(seed_rows) else math.nan,
                "discordance_rate": discordance,
                "evidence_status": evidence_status,
                "completed_positive_result": bool(
                    evidence_status == "completed_independent_oqmd_exact_structure_evidence"
                    and float(seed_rows["independent_FTR"].mean()) <= float(seed_rows["alpha"].iloc[0])
                )
                if len(seed_rows)
                else False,
                "blocker": "" if len(exact) else "no exact OQMD structure matches",
            }
        ]
    )


def write_closeout(out_dir: Path, primary: pd.DataFrame, source_rows: pd.DataFrame) -> None:
    row = primary.iloc[0]
    closeout = f"""# Materials Independent DFT Validation Closeout

Evidence status: `{row['evidence_status']}`.

This milestone attempts A2 independent DFT-source validation with a real public
OQMD query and exact-structure matching. It does not fabricate an independent
join table and does not use OQMD labels for PARC selection.

## Completed Actions

- Reconstructed the frozen ALIGNN-FF `alpha=0.10, K={row['K']}` PARC rows from
  public WBM/Matbench labels and public ALIGNN-FF predictions.
- Loaded private WBM raw ComputedStructureEntry files only to recover candidate
  structures for matching.
- Queried OQMD by chemical system after release reconstruction.
- Counted independent FTR only for exact reduced-formula plus StructureMatcher
  matches. Formula-only hits are reported as diagnostics only.

## Headline Diagnostics

- Unique raw top-K candidates evaluated for matching: `{row['n_unique_raw_topK_candidates']}`.
- Unique exact OQMD structure matches: `{row['n_unique_exact_structure_matches']}`.
- Mean released exact-match coverage: `{row['coverage_of_independent_source']:.3f}`.
- Mean raw top-K exact-match coverage: `{row['raw_topK_coverage_of_independent_source']:.3f}`.
- Mean OQMD independent FTR on matched released candidates: `{row['independent_FTR']:.3f}`.
- Mean OQMD independent FTR on matched raw top-K candidates: `{row['raw_topK_independent_FTR']:.3f}`.

## Interpretation

If coverage is low, this is a completed independent-source diagnostic rather
than a primary independent validation result. The A2 gate is promoted to
completed evidence only when exact-match coverage is high enough under the
predeclared threshold. This package therefore hardens provenance and identifies
the remaining independent-source coverage gap without overstating the result.
"""
    (out_dir / "MATERIALS_INDEPENDENT_DFT_VALIDATION_CLOSEOUT.md").write_text(closeout, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--private-dir", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM_SUMMARY))
    parser.add_argument("--alignn-predictions", default=str(DEFAULT_ALIGNN))
    parser.add_argument("--megnet-predictions", default=str(DEFAULT_MEGNET))
    parser.add_argument("--wbm-step1", default=str(DEFAULT_STEP1))
    parser.add_argument("--wbm-step-dir", default=str(DEFAULT_STEP_DIR))
    parser.add_argument("--K", type=int, default=300)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--oqmd-workers", type=int, default=8)
    parser.add_argument("--min-coverage-primary", type=float, default=0.60)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    private_dir = Path(args.private_dir)
    cache_dir = private_dir / "oqmd_cache"
    private_dir.mkdir(parents=True, exist_ok=True)

    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    frame = load_frame(args)
    seed_wbm, candidate_rows = reconstruct_release_rows(
        frame,
        alpha=args.alpha,
        rho=args.rho,
        budget=args.K,
        seeds=seeds,
    )
    needed_ids = set(candidate_rows["material_id"].astype(str))
    entries = load_step_entries_for_ids(needed_ids, step1=Path(args.wbm_step1), step_dir=Path(args.wbm_step_dir))
    matches, source_rows = match_candidates_to_oqmd(
        candidate_rows,
        entries,
        cache_dir=cache_dir,
        timeout=args.timeout,
        sleep_seconds=args.sleep_seconds,
        retries=args.retries,
        workers=args.oqmd_workers,
    )
    seed_rows = summarize_seed_rows(candidate_rows, matches, alpha=args.alpha, budget=args.K)
    primary = aggregate_primary(seed_rows, candidate_rows, matches, min_coverage_primary=args.min_coverage_primary)

    # Public-safe outputs.
    source_summary = pd.DataFrame(
        [
            {
                "source": "OQMD",
                "label_type": "computed stability / formation energy",
                "candidate_join_requirement": "exact reduced formula plus pymatgen StructureMatcher",
                "local_label_file_available": False,
                "public_api_queried": True,
                "n_chemical_system_queries": int(source_rows["chemical_system"].nunique()) if len(source_rows) else 0,
                "n_queries_with_records": int((source_rows["api_records_returned"].astype(int) > 0).sum()) if len(source_rows) else 0,
                "expected_strength": "independent public DFT source with structure-level records",
                "main_risk": "coverage may be limited because WBM candidates are designed as novel substituted structures",
                "feasibility_status": "completed_exact_structure_matching_diagnostic",
            },
            {
                "source": "Materials Project",
                "label_type": "computed stability / energy above hull",
                "candidate_join_requirement": "MP API key or public structure/prototype snapshot",
                "local_label_file_available": False,
                "public_api_queried": False,
                "n_chemical_system_queries": 0,
                "n_queries_with_records": 0,
                "expected_strength": "high provenance, strong community familiarity",
                "main_risk": "API key unavailable in this run; WBM hull reference is MP-derived and dependence must be disclosed",
                "feasibility_status": "blocked_missing_MP_API_key_or_snapshot",
            },
        ]
    )
    source_summary.to_csv(out_dir / "table_independent_dft_join_summary.csv", index=False)
    primary.to_csv(out_dir / "table_independent_dft_primary_results.csv", index=False)
    seed_rows.to_csv(out_dir / "table_independent_dft_seed_rows.csv", index=False)
    matches.to_csv(out_dir / "table_independent_dft_candidate_matches.csv", index=False)
    source_rows.to_csv(out_dir / "table_independent_dft_oqmd_query_summary.csv", index=False)

    exact = matches[matches["match_confidence"].eq("exact_structure_match")]
    discordance = (
        float((exact["wbm_stable_DFT"].astype(bool) != parc_bool(exact["oqmd_stable_exact"])).mean()) if len(exact) else math.nan
    )
    pd.DataFrame(
        [
            {
                "comparison": "WBM_vs_OQMD_exact_structure_matches",
                "n_exact_matches": int(len(exact)),
                "discordance_rate": discordance,
                "evidence_status": primary.iloc[0]["evidence_status"],
                "interpretation": "computed on exact-structure OQMD matches only; formula-only hits excluded",
            }
        ]
    ).to_csv(out_dir / "table_independent_dft_discordance.csv", index=False)
    pd.DataFrame(
        [
            {
                "match_confidence": "exact_structure_match",
                "role": "primary_if_coverage_sufficient_else_completed_diagnostic",
                "n_candidates": int(matches["match_confidence"].eq("exact_structure_match").sum()),
                "evidence_status": primary.iloc[0]["evidence_status"],
            },
            {
                "match_confidence": "formula_only_no_structure_match",
                "role": "sensitivity_only",
                "n_candidates": int(matches["match_confidence"].eq("formula_only_no_structure_match").sum()),
                "evidence_status": "completed_diagnostic_not_used_for_independent_FTR",
            },
            {
                "match_confidence": "no_formula_match",
                "role": "coverage_gap",
                "n_candidates": int(matches["match_confidence"].eq("no_formula_match").sum()),
                "evidence_status": "completed_query_no_independent_label",
            },
        ]
    ).to_csv(out_dir / "table_independent_dft_match_confidence_sensitivity.csv", index=False)

    (out_dir / "independent_source_inventory.md").write_text(
        "# Independent DFT Source Inventory\n\n"
        "OQMD was queried through its public formation-energy API after PARC row reconstruction. "
        "Materials Project remains blocked in this run because no API key or local public snapshot is available. "
        "Raw WBM structures are private inputs used only for matching and are not redistributed in the public-safe bundle.\n",
        encoding="utf-8",
    )
    (out_dir / "structure_matching_protocol.md").write_text(
        "# Structure Matching Protocol\n\n"
        "Primary A2 matching requires exact reduced formula plus pymatgen `StructureMatcher` fit with "
        "`ltol=0.2`, `stol=0.3`, `angle_tol=5`, `primitive_cell=True`, `scale=True`, and "
        "`attempt_supercell=True`. Formula-only OQMD hits are sensitivity diagnostics and do not enter "
        "independent FTR.\n",
        encoding="utf-8",
    )
    write_closeout(out_dir, primary, source_rows)
    write_manifest(out_dir)


if __name__ == "__main__":
    main()
