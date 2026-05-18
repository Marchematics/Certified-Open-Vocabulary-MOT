#!/usr/bin/env python3
"""Build A1/A2 materials validation against the local alex-mp public snapshot.

This milestone intentionally separates completed evidence from unsupported
promotion:

* A2 uses exact reduced-formula plus StructureMatcher joins to alex-mp labels.
* A1 is a quasi-temporal external-snapshot replay: WBM/Matbench public labels
  and predictions define the frozen PARC row, while the later alex-mp snapshot
  evaluates exact-structure matched candidates.
* Formula-only rows are reported as coverage diagnostics and never enter the
  independent FTR.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import math
import sys
import warnings
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Composition, Structure

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_materials_discovery_parc_flagship import (  # noqa: E402
    compute_evalues,
    load_materials_inputs,
    observed_positive_mask,
    scs_release_count,
    split_blocks,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs/milestones/materials_alex_mp_a1_a2_validation"
DEFAULT_PRIVATE = Path("/home/waas/paper_experiments/private/materials_independent_dft_validation")
DEFAULT_WBM_SUMMARY = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
DEFAULT_ALIGNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
DEFAULT_MEGNET = Path("/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
DEFAULT_STEP1 = Path(
    "/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2"
)
DEFAULT_STEP_DIR = Path("/home/waas/paper_experiments/private/wbm_raw_full")
DEFAULT_ALEX_ZIP = Path("/home/waas/paper_experiments/private/mattergen_repo/data-release/alex-mp/alex_mp_20.zip")


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


def reduced_formula(value: Any) -> str:
    try:
        return Composition(str(value)).reduced_formula
    except Exception:
        return str(value)


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


def reconstruct_candidate_rows(
    frame: pd.DataFrame, *, alpha: float, rho: float, budget: int, seeds: list[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
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
        selected_ids: set[str] = set()
        if released:
            selected_pos = np.argsort(pool["_evalue"].to_numpy(dtype=float))[::-1][:released]
            selected_ids = set(pool.iloc[selected_pos]["material_id"].astype(str))
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
            candidate_rows.append(
                {
                    "seed": seed,
                    "material_id": row["material_id"],
                    "formula": row["formula"],
                    "reduced_formula": reduced_formula(row["formula"]),
                    "chemical_system": row["chemical_system"],
                    "raw_rank": rank,
                    "parc_release_flag": str(row["material_id"]) in selected_ids,
                    "evalue": float(row["_evalue"]),
                    "score": float(row["primary_score"]),
                    "stable_DFT_wbm": bool(row["stable_DFT"]),
                    "e_above_hull_wbm": float(row["e_above_hull_mp2020_corrected_ppd_mp"]),
                    "composition_family_pair": row["composition_family_pair"],
                }
            )
    return pd.DataFrame(seed_rows), pd.DataFrame(candidate_rows)


def wbm_step_path(material_id: str, step1: Path, step_dir: Path) -> Path:
    step = int(str(material_id).split("-")[1])
    return step1 if step == 1 else step_dir / f"step_{step}.json.bz2"


def load_wbm_structures(material_ids: set[str], *, step1: Path, step_dir: Path) -> dict[str, Structure]:
    by_step: dict[int, set[int]] = {}
    for mid in material_ids:
        parts = str(mid).split("-")
        if len(parts) == 3 and parts[0] == "wbm":
            by_step.setdefault(int(parts[1]), set()).add(int(parts[2]) - 1)

    out: dict[str, Structure] = {}
    for step, indexes in sorted(by_step.items()):
        path = step1 if step == 1 else step_dir / f"step_{step}.json.bz2"
        if not path.exists():
            continue
        with bz2.open(path, "rt", encoding="utf-8") as handle:
            entries = json.load(handle)["entries"]
        for idx in sorted(indexes):
            if 0 <= idx < len(entries):
                material_id = f"wbm-{step}-{idx + 1}"
                try:
                    out[material_id] = Structure.from_dict(entries[idx]["structure"])
                except Exception:
                    continue
    return out


def load_alex_formula_rows(alex_zip: Path, formulas: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[pd.DataFrame] = []
    inventory_rows = []
    with zipfile.ZipFile(alex_zip) as archive:
        for name in ["alex_mp_20/val.csv", "alex_mp_20/train.csv"]:
            total = 0
            retained = 0
            with archive.open(name) as handle:
                for chunk in pd.read_csv(
                    handle,
                    usecols=["material_id", "reduced_formula", "chemical_system", "cif", "energy_above_hull"],
                    chunksize=50_000,
                ):
                    total += len(chunk)
                    hit = chunk[chunk["reduced_formula"].astype(str).isin(formulas)].copy()
                    retained += len(hit)
                    if len(hit):
                        hit["alex_source_file"] = name
                        rows.append(hit)
            inventory_rows.append(
                {
                    "source_file": name,
                    "rows_scanned": total,
                    "formula_candidate_rows_retained": retained,
                    "role": "exact_structure_match_candidate_source",
                }
            )
        if "ref.csv" in archive.namelist():
            with archive.open("ref.csv") as handle:
                ref_total = 0
                ref_retained = 0
                for chunk in pd.read_csv(handle, usecols=["structure_id", "reduced_formula", "chemical_system", "energy_above_hull"], chunksize=100_000):
                    ref_total += len(chunk)
                    ref_retained += int(chunk["reduced_formula"].astype(str).isin(formulas).sum())
                inventory_rows.append(
                    {
                        "source_file": "ref.csv",
                        "rows_scanned": ref_total,
                        "formula_candidate_rows_retained": ref_retained,
                        "role": "formula_only_reference_inventory_not_used_for_primary_FTR",
                    }
                )
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), pd.DataFrame(inventory_rows)


def match_to_alex(candidate_rows: pd.DataFrame, structures: dict[str, Structure], alex_rows: pd.DataFrame) -> pd.DataFrame:
    matcher = StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5,
        primitive_cell=True,
        scale=True,
        attempt_supercell=True,
    )
    unique = candidate_rows.drop_duplicates("material_id").copy()
    alex_by_formula = {formula: group for formula, group in alex_rows.groupby("reduced_formula")} if len(alex_rows) else {}
    out_rows: list[dict[str, Any]] = []
    warnings.filterwarnings("ignore")
    for _, cand in unique.iterrows():
        material_id = str(cand["material_id"])
        formula = str(cand["formula"])
        red = str(cand["reduced_formula"])
        wbm_structure = structures.get(material_id)
        formula_records = alex_by_formula.get(red, pd.DataFrame())
        matches: list[dict[str, Any]] = []
        if wbm_structure is not None and len(formula_records):
            for _, record in formula_records.iterrows():
                try:
                    alex_structure = Structure.from_str(str(record["cif"]), fmt="cif")
                    if matcher.fit(wbm_structure, alex_structure):
                        matches.append(record.to_dict())
                except Exception:
                    continue
        stabilities = [float(record["energy_above_hull"]) for record in matches if pd.notna(record.get("energy_above_hull"))]
        min_hull = min(stabilities) if stabilities else math.nan
        out_rows.append(
            {
                "material_id": material_id,
                "formula": formula,
                "reduced_formula": red,
                "chemical_system": cand["chemical_system"],
                "match_confidence": "exact_structure_match"
                if matches
                else ("formula_only_no_structure_match" if len(formula_records) else "no_formula_match"),
                "alex_match_count": len(matches),
                "alex_material_ids": ";".join(str(record.get("material_id", "")) for record in matches),
                "alex_min_e_above_hull": min_hull,
                "alex_stable_exact": bool(min_hull <= 0.0) if stabilities else "",
                "alex_source_files": ";".join(sorted(set(str(record.get("alex_source_file", "")) for record in matches))),
                "formula_only_candidate_count": int(len(formula_records)),
                "wbm_stable_DFT": bool(cand["stable_DFT_wbm"]),
                "wbm_e_above_hull": float(cand["e_above_hull_wbm"]),
            }
        )
    return pd.DataFrame(out_rows)


def strict_bool(series: pd.Series) -> pd.Series:
    return series.map(lambda value: bool(value) if value != "" and pd.notna(value) else False).astype(bool)


def summarize_seed_rows(candidate_rows: pd.DataFrame, matches: pd.DataFrame, *, alpha: float, budget: int) -> pd.DataFrame:
    joined = candidate_rows.merge(
        matches,
        on=["material_id", "formula", "reduced_formula", "chemical_system"],
        how="left",
    )
    rows: list[dict[str, Any]] = []
    for seed, group in joined.groupby("seed"):
        exact = group[group["match_confidence"].eq("exact_structure_match")].copy()
        parc_exact = exact[exact["parc_release_flag"].astype(bool)].copy()
        raw_ftr = float((~strict_bool(exact["alex_stable_exact"])).mean()) if len(exact) else math.nan
        parc_ftr = float((~strict_bool(parc_exact["alex_stable_exact"])).mean()) if len(parc_exact) else math.nan
        released = int(group["parc_release_flag"].sum())
        rows.append(
            {
                "domain": "materials_discovery",
                "source": "ALIGNN-FF",
                "external_label_source": "alex-mp v20 local public snapshot",
                "match_confidence": "exact_structure_match",
                "seed": int(seed),
                "K": budget,
                "alpha": alpha,
                "released": released,
                "n_raw_topK_exact_matches": int(len(exact)),
                "n_released_exact_matches": int(len(parc_exact)),
                "independent_FTR": parc_ftr,
                "raw_topK_independent_FTR": raw_ftr,
                "coverage_raw_topK": len(exact) / float(budget) if budget else math.nan,
                "coverage_released": len(parc_exact) / float(released) if released else 0.0,
                "PARC_vs_raw_delta": raw_ftr - parc_ftr if math.isfinite(raw_ftr) and math.isfinite(parc_ftr) else math.nan,
                "evidence_status": "completed_alex_mp_exact_structure_external_snapshot",
            }
        )
    return pd.DataFrame(rows)


def aggregate_primary(seed_rows: pd.DataFrame, candidate_rows: pd.DataFrame, matches: pd.DataFrame, *, alpha: float) -> pd.DataFrame:
    unique_joined = candidate_rows.drop_duplicates("material_id").merge(
        matches,
        on=["material_id", "formula", "reduced_formula", "chemical_system"],
        how="left",
    )
    exact = unique_joined[unique_joined["match_confidence"].eq("exact_structure_match")]
    discordance = (
        float((exact["wbm_stable_DFT"].astype(bool) != strict_bool(exact["alex_stable_exact"])).mean()) if len(exact) else math.nan
    )
    mean_independent_ftr = float(seed_rows["independent_FTR"].dropna().mean()) if seed_rows["independent_FTR"].notna().any() else math.nan
    mean_raw_ftr = float(seed_rows["raw_topK_independent_FTR"].dropna().mean()) if seed_rows["raw_topK_independent_FTR"].notna().any() else math.nan
    release_cov = float(seed_rows["coverage_released"].mean()) if len(seed_rows) else 0.0
    raw_cov = float(seed_rows["coverage_raw_topK"].mean()) if len(seed_rows) else 0.0
    positive = bool(math.isfinite(mean_independent_ftr) and mean_independent_ftr <= alpha and release_cov >= 0.20)
    status = (
        "completed_independent_alex_mp_exact_structure_positive_medium_coverage"
        if positive
        else "completed_independent_alex_mp_exact_structure_diagnostic"
    )
    return pd.DataFrame(
        [
            {
                "domain": "materials_discovery",
                "source": "ALIGNN-FF",
                "external_label_source": "alex-mp v20 local public snapshot",
                "match_confidence": "exact_structure_match",
                "K": int(seed_rows["K"].iloc[0]) if len(seed_rows) else "",
                "alpha": float(alpha),
                "n_seeds": int(seed_rows["seed"].nunique()) if len(seed_rows) else 0,
                "n_unique_raw_topK_candidates": int(candidate_rows["material_id"].nunique()),
                "n_unique_exact_structure_matches": int(len(exact)),
                "n_released_matched_mean": float(seed_rows["n_released_exact_matches"].mean()) if len(seed_rows) else math.nan,
                "independent_FTR": mean_independent_ftr,
                "coverage_of_independent_source": release_cov,
                "raw_topK_independent_FTR": mean_raw_ftr,
                "raw_topK_coverage_of_independent_source": raw_cov,
                "PARC_vs_raw_delta": float(seed_rows["PARC_vs_raw_delta"].dropna().mean()) if seed_rows["PARC_vs_raw_delta"].notna().any() else math.nan,
                "discordance_rate": discordance,
                "evidence_status": status,
                "completed_positive_result": positive,
                "claim_scope": "exact-structure matched alex-mp external snapshot only; formula-only hits excluded",
            }
        ]
    )


def write_closeout(out_dir: Path, primary: pd.DataFrame) -> None:
    row = primary.iloc[0]
    text = f"""# Materials alex-mp A1/A2 Validation Closeout

Evidence status: `{row['evidence_status']}`.

This milestone completes a local alex-mp exact-structure validation pass for the
materials flagship. It is not a new DFT calculation and it is not experimental
synthesis evidence.

## What Is Completed

- Reconstructed the frozen ALIGNN-FF `K={row['K']}`, `alpha={row['alpha']}` PARC
  row from the public WBM/Matbench labels and public model-prediction files.
- Used the later `alex_mp_20` local public snapshot as an external DFT label
  source for exact-structure matched candidates.
- Counted independent FTR only for exact reduced-formula plus StructureMatcher
  matches.
- Reported formula-only and no-formula rows as coverage diagnostics only.

## Headline Numbers

- Unique raw/PARC candidates considered: `{row['n_unique_raw_topK_candidates']}`.
- Unique exact alex-mp structure matches: `{row['n_unique_exact_structure_matches']}`.
- Mean released exact-match coverage: `{row['coverage_of_independent_source']:.3f}`.
- Mean raw top-K exact-match coverage: `{row['raw_topK_coverage_of_independent_source']:.3f}`.
- Mean independent FTR on matched PARC releases: `{row['independent_FTR']:.3f}`.
- Mean independent FTR on matched raw top-K candidates: `{row['raw_topK_independent_FTR']:.3f}`.
- Mean PARC-vs-raw FTR delta on matched rows: `{row['PARC_vs_raw_delta']:.3f}`.

## Interpretation

This is completed A2 evidence for the exact-match subset and a completed A1
quasi-temporal external-snapshot replay because the evaluation labels come from
the later alex-mp public snapshot rather than the WBM label table used to define
PARC calibration. The claim remains scoped to the exact-structure matched
subset; it must not be described as full-coverage independent validation.
"""
    (out_dir / "MATERIALS_ALEX_MP_A1_A2_VALIDATION_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--private-dir", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--alex-zip", default=str(DEFAULT_ALEX_ZIP))
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM_SUMMARY))
    parser.add_argument("--alignn-predictions", default=str(DEFAULT_ALIGNN))
    parser.add_argument("--megnet-predictions", default=str(DEFAULT_MEGNET))
    parser.add_argument("--wbm-step1", default=str(DEFAULT_STEP1))
    parser.add_argument("--wbm-step-dir", default=str(DEFAULT_STEP_DIR))
    parser.add_argument("--K", type=int, default=300)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(args.private_dir).mkdir(parents=True, exist_ok=True)
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]

    frame = load_frame(args)
    seed_wbm, candidate_rows = reconstruct_candidate_rows(frame, alpha=args.alpha, rho=args.rho, budget=args.K, seeds=seeds)
    structures = load_wbm_structures(
        set(candidate_rows["material_id"].astype(str)),
        step1=Path(args.wbm_step1),
        step_dir=Path(args.wbm_step_dir),
    )
    alex_rows, alex_inventory = load_alex_formula_rows(Path(args.alex_zip), set(candidate_rows["reduced_formula"].astype(str)))
    matches = match_to_alex(candidate_rows, structures, alex_rows)
    seed_rows = summarize_seed_rows(candidate_rows, matches, alpha=args.alpha, budget=args.K)
    primary = aggregate_primary(seed_rows, candidate_rows, matches, alpha=args.alpha)

    primary.to_csv(out_dir / "table_alex_mp_a2_primary_results.csv", index=False)
    seed_rows.to_csv(out_dir / "table_alex_mp_a2_seed_rows.csv", index=False)
    matches.to_csv(out_dir / "table_alex_mp_a2_candidate_matches.csv", index=False)
    alex_inventory.to_csv(out_dir / "table_alex_mp_source_inventory.csv", index=False)
    seed_wbm.to_csv(out_dir / "table_wbm_reconstructed_release_seed_rows.csv", index=False)

    temporal = primary.copy()
    temporal.insert(2, "trial", "A1_quasi_temporal_external_snapshot_replay")
    temporal["t0_calibration_source"] = "WBM/Matbench public labels and ALIGNN-FF predictions"
    temporal["t1_evaluation_source"] = "alex-mp v20 local public snapshot"
    temporal["temporal_claim_scope"] = (
        "quasi-temporal external-snapshot replay; exact-structure matched subset only; "
        "not a full timestamped public-label t0/t1 split"
    )
    temporal.to_csv(out_dir / "table_alex_mp_a1_temporal_external_snapshot_primary.csv", index=False)
    temporal[
        [
            "domain",
            "source",
            "trial",
            "K",
            "alpha",
            "independent_FTR",
            "raw_topK_independent_FTR",
            "PARC_vs_raw_delta",
            "coverage_of_independent_source",
            "temporal_claim_scope",
        ]
    ].to_csv(out_dir / "table_alex_mp_a1_raw_vs_parc.csv", index=False)

    pd.DataFrame(
        [
            {
                "match_confidence": "exact_structure_match",
                "role": "primary_A2_and_A1_exact_match_subset",
                "n_candidates": int(matches["match_confidence"].eq("exact_structure_match").sum()),
                "evidence_status": primary.iloc[0]["evidence_status"],
            },
            {
                "match_confidence": "formula_only_no_structure_match",
                "role": "coverage_diagnostic_not_used_for_FTR",
                "n_candidates": int(matches["match_confidence"].eq("formula_only_no_structure_match").sum()),
                "evidence_status": "completed_diagnostic_not_used_for_independent_FTR",
            },
            {
                "match_confidence": "no_formula_match",
                "role": "coverage_gap",
                "n_candidates": int(matches["match_confidence"].eq("no_formula_match").sum()),
                "evidence_status": "completed_query_no_external_label",
            },
        ]
    ).to_csv(out_dir / "table_alex_mp_match_confidence_sensitivity.csv", index=False)

    exact = matches[matches["match_confidence"].eq("exact_structure_match")]
    discordance = float((exact["wbm_stable_DFT"].astype(bool) != strict_bool(exact["alex_stable_exact"])).mean()) if len(exact) else math.nan
    pd.DataFrame(
        [
            {
                "comparison": "WBM_vs_alex_mp_exact_structure_matches",
                "n_exact_matches": int(len(exact)),
                "discordance_rate": discordance,
                "interpretation": "exact-structure matched subset only; discordance partly reflects label-source/hull differences",
            }
        ]
    ).to_csv(out_dir / "table_alex_mp_label_discordance.csv", index=False)

    (out_dir / "README.md").write_text(
        "# Materials alex-mp A1/A2 Validation\n\n"
        "Completed exact-structure external-snapshot validation for the materials row. "
        "This milestone uses alex-mp v20 labels only after PARC row reconstruction and "
        "does not use formula-only matches for independent FTR.\n",
        encoding="utf-8",
    )
    (out_dir / "PROTOCOL.md").write_text(
        "# Protocol\n\n"
        "Reconstruct ALIGNN-FF WBM PARC rows at `alpha=0.10`, `rho=0.10`, `K=300`, "
        "then match unique raw/PARC candidates to alex-mp v20 by exact reduced formula "
        "plus pymatgen StructureMatcher. Evaluate independent FTR only on exact matches. "
        "Use alex-mp as a later external public snapshot for A1 quasi-temporal replay and "
        "as an independent DFT source for A2.\n",
        encoding="utf-8",
    )
    write_closeout(out_dir, primary)
    write_manifest(out_dir)


if __name__ == "__main__":
    main()
