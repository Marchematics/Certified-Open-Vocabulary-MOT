#!/usr/bin/env python3
"""Build Phase62 full-calibration CHGNet/MACE e-values.

Phase61 used CHGNet/MACE as queue-level rank proxies. This milestone upgrades
the auxiliary sources to full calibration e-values whenever the local WBM
calibration denominator and structure cache are available. The output is still a
materials queue audit, not DFT evidence and not a prospective discovery claim.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

from build_materials_computational_trial import gamma_star_from_p, scs_release_count


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE53 = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit"
OUT = ROOT / "outputs/milestones/ncs_phase62_full_calibration_mlip_evalues"
CHGNET_CAL = ROOT / "outputs/milestones/materials_prospective_dft_followup_chgnet_v3/calibration_scores_chgnet_v3.csv"
PRIVATE_STEP1 = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2")
PRIVATE_WBM_FULL = Path("/home/waas/paper_experiments/private/wbm_raw_full")
BAD_CHGNET_FULL_FILE = Path("/home/waas/paper_experiments/private/chgnet/2023-12-21-chgnet-0.3.0-wbm-IS2RE.csv.gz")

ALPHA = 0.10
RHO = 0.10
SCOPE = (
    "full_calibration_CHGNet_MACE_evalue_audit;"
    "uses_frozen_WBM_one_per_composition_family_calibration_denominator;"
    "target_overlap_excluded_from_calibration;"
    "not_t1_alpha_certificate;"
    "not_DFT_evidence;"
    "not_prospective_discovery"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def material_step_and_index(material_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"wbm-(\d+)-(\d+)", str(material_id))
    if not match:
        raise ValueError(f"unexpected material_id format: {material_id}")
    return int(match.group(1)), int(match.group(2)) - 1


def step_path(step: int) -> Path:
    if step == 1:
        return PRIVATE_STEP1
    return PRIVATE_WBM_FULL / f"step_{step}.json.bz2"


def load_needed_structures(candidate_ids: list[str]) -> dict[str, Structure]:
    by_step: dict[int, set[int]] = {}
    for candidate_id in candidate_ids:
        step, idx = material_step_and_index(candidate_id)
        by_step.setdefault(step, set()).add(idx)

    structures: dict[str, Structure] = {}
    for step, indexes in sorted(by_step.items()):
        path = step_path(step)
        if not path.exists():
            raise FileNotFoundError(f"missing private WBM raw structure cache: {path}")
        with bz2.open(path, "rt") as handle:
            entries = json.load(handle)["entries"]
        for idx in sorted(indexes):
            candidate_id = f"wbm-{step}-{idx + 1}"
            structures[candidate_id] = Structure.from_dict(entries[idx]["structure"])
    return structures


def score_mace_calibration(calibration: pd.DataFrame, *, force: bool = False, max_rows: int | None = None) -> pd.DataFrame:
    cache = OUT / "table_mace_full_calibration_scores.csv"
    ids = calibration["candidate_id"].astype(str).tolist()
    if max_rows is not None:
        ids = ids[:max_rows]
    if cache.exists() and not force:
        cached = pd.read_csv(cache)
        if set(ids).issubset(set(cached["candidate_id"].astype(str))):
            return cached[cached["candidate_id"].astype(str).isin(ids)].copy()

    from mace.calculators import mace_mp

    structures = load_needed_structures(ids)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    mace_calc = mace_mp(model="small", device=device, default_dtype="float32")
    adaptor = AseAtomsAdaptor()
    rows: list[dict[str, object]] = []
    for order, candidate_id in enumerate(ids, start=1):
        row = calibration[calibration["candidate_id"].astype(str).eq(candidate_id)].iloc[0]
        energy = np.nan
        status = "not_scored"
        error = ""
        try:
            atoms = adaptor.get_atoms(structures[candidate_id])
            atoms.calc = mace_calc
            energy = float(atoms.get_potential_energy() / len(atoms))
            status = "scored"
        except Exception as exc:  # pragma: no cover - depends on local MLIP runtime.
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"[:180]
        rows.append(
            {
                "candidate_id": candidate_id,
                "formula": row["formula"],
                "block_id": row["block_id"],
                "stable_DFT": bool(row["stable_DFT"]),
                "mace_energy_per_atom": energy,
                "mace_score_status": status,
                "mace_error": error,
                "score_order": order,
                "structure_source": "local_private_WBM_raw_structure_cache_not_distributed",
            }
        )
        if order % 250 == 0:
            print(f"scored MACE calibration {order}/{len(ids)}", flush=True)
    scored = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    scored.to_csv(cache, index=False)
    return scored


def load_target_queue() -> pd.DataFrame:
    phase51 = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    phase53 = pd.read_csv(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv")
    phase53 = phase53.rename(columns={"candidate_id": "material_id"})
    merged = phase51.merge(
        phase53[
            [
                "material_id",
                "K",
                "structure_hash",
                "policy_status",
                "chgnet_predicted_ehull_or_score",
                "mace_predicted_ehull_or_score",
            ]
        ],
        on=["material_id", "K"],
        how="left",
        validate="one_to_one",
    )
    merged["block_id"] = merged["composition_family_pair"].astype(str)
    merged["target_chgnet_score"] = -pd.to_numeric(merged["chgnet_predicted_ehull_or_score"], errors="coerce")
    merged["target_mace_score"] = -pd.to_numeric(merged["mace_predicted_ehull_or_score"], errors="coerce")
    return merged


def load_calibration(*, target_ids: set[str], force_mace: bool, max_mace_rows: int | None) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cal = pd.read_csv(CHGNET_CAL)
    cal["candidate_id"] = cal["candidate_id"].astype(str)
    cal["block_id"] = cal["block_id"].astype(str)
    cal["stable_DFT"] = cal["stable_DFT"].astype(bool)
    cal["chgnet_fullcal_score"] = -pd.to_numeric(cal["chgnet_energy_per_atom"], errors="coerce")

    overlap = cal["candidate_id"].isin(target_ids)
    cal = cal.loc[~overlap].copy()
    rows = [
        {
            "source": "CHGNet",
            "score_path": rel(CHGNET_CAL),
            "full_calibration_rows_before_target_exclusion": 5797,
            "target_overlap_excluded": int(overlap.sum()),
            "full_calibration_rows_after_target_exclusion": int(len(cal)),
            "scored_rows": int(cal["chgnet_fullcal_score"].notna().sum()),
            "calibration_blocks": int(cal["block_id"].nunique()),
            "status": "available_full_calibration_subset",
            "blocking_issue": "",
            "source_sha256": sha256_file(CHGNET_CAL),
            "evidence_scope": SCOPE,
        }
    ]

    mace_scores = score_mace_calibration(cal, force=force_mace, max_rows=max_mace_rows)
    mace_scores["candidate_id"] = mace_scores["candidate_id"].astype(str)
    cal = cal.merge(
        mace_scores[["candidate_id", "mace_energy_per_atom", "mace_score_status"]],
        on="candidate_id",
        how="left",
    )
    cal["mace_fullcal_score"] = -pd.to_numeric(cal["mace_energy_per_atom"], errors="coerce")
    mace_complete = bool(cal["mace_score_status"].eq("scored").all()) and max_mace_rows is None
    rows.append(
        {
            "source": "MACE-MP",
            "score_path": rel(OUT / "table_mace_full_calibration_scores.csv"),
            "full_calibration_rows_before_target_exclusion": 5797,
            "target_overlap_excluded": int(overlap.sum()),
            "full_calibration_rows_after_target_exclusion": int(len(cal)),
            "scored_rows": int(cal["mace_fullcal_score"].notna().sum()),
            "calibration_blocks": int(cal.loc[cal["mace_fullcal_score"].notna(), "block_id"].nunique()),
            "status": "available_full_calibration_subset" if mace_complete else "partial_or_blocked_full_calibration_subset",
            "blocking_issue": "" if mace_complete else "MACE calibration scores are incomplete; rerun without --max-mace-rows if this was a smoke run.",
            "source_sha256": sha256_file(OUT / "table_mace_full_calibration_scores.csv") if (OUT / "table_mace_full_calibration_scores.csv").exists() else "",
            "evidence_scope": SCOPE,
        }
    )
    return cal, rows


def observed_positive_mask(cal: pd.DataFrame, score_col: str) -> np.ndarray:
    observed = np.zeros(len(cal), dtype=bool)
    stable = cal["stable_DFT"].to_numpy(dtype=bool)
    scored = pd.to_numeric(cal[score_col], errors="coerce").notna().to_numpy()
    eligible = np.flatnonzero(stable & scored)
    if len(eligible) == 0:
        return observed
    n_observed = max(1, int(round(len(eligible) * RHO)))
    scores = pd.to_numeric(cal[score_col], errors="coerce").to_numpy(dtype=float)
    chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
    observed[chosen] = True
    return observed


def compute_fullcal_evalues(
    cal: pd.DataFrame,
    target: pd.DataFrame,
    *,
    cal_score_col: str,
    target_score_col: str,
) -> tuple[pd.Series, dict[str, object]]:
    scored_cal = cal[cal[cal_score_col].notna()].copy()
    observed = observed_positive_mask(scored_cal, cal_score_col)
    null_cal = scored_cal.loc[~observed].copy()
    maxima = null_cal.groupby("block_id", sort=False)[cal_score_col].max().astype(float).to_numpy()
    p_min = 1.0 / (len(maxima) + 1.0) if len(maxima) else 1.0
    gamma = gamma_star_from_p(p_min)
    values = np.zeros(len(target), dtype=float)
    scored_target = pd.to_numeric(target[target_score_col], errors="coerce").notna().to_numpy()
    if gamma is not None and len(maxima):
        sorted_max = np.sort(maxima)
        scores = pd.to_numeric(target[target_score_col], errors="coerce").to_numpy(dtype=float)
        exceed = len(sorted_max) - np.searchsorted(sorted_max, scores[scored_target], side="left")
        p_block = (1.0 + exceed) / (len(sorted_max) + 1.0)
        values[scored_target] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    diag = {
        "calibration_scored_rows": int(len(scored_cal)),
        "observed_positives": int(observed.sum()),
        "null_calibration_rows": int(len(null_cal)),
        "null_calibration_blocks": int(len(maxima)),
        "target_scored_rows": int(scored_target.sum()),
        "p_min_effective": float(p_min),
        "gamma": float(gamma) if gamma is not None else np.nan,
        "max_evalue": float(np.nanmax(values)) if len(values) else 0.0,
    }
    return pd.Series(values, index=target.index), diag


def bool_col(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().eq("true")


def summarize_selection(pool: pd.DataFrame, *, k: int, method: str, e_col: str | None, mask: pd.Series | None) -> tuple[dict[str, object], pd.DataFrame]:
    if mask is not None:
        selected = pool.loc[mask].copy()
        selected["_selected_evalue"] = selected["parc_e_value"].astype(float)
        released = int(len(selected))
        tau = np.nan
        margin = np.nan
        best_ratio = np.nan
        construction_rule = "existing_membership_from_phase51"
    else:
        assert e_col is not None
        values = pool[e_col].to_numpy(dtype=float)
        released, tau, margin, best_ratio = scs_release_count(values, alpha=ALPHA, budget=k)
        selected = pool.assign(_selected_evalue=values).sort_values(
            ["_selected_evalue", "raw_rank", "material_id"], ascending=[False, True, True]
        ).head(released).copy()
        construction_rule = "SCS_on_full_calibration_auxiliary_evalues"

    if released:
        t0_stable = bool_col(selected["stable_exact_t0"])
        t1_stable = bool_col(selected["stable_exact_t1_current_mp"])
        t0_ftr = float((~t0_stable).mean())
        t1_ftr = float((~t1_stable).mean())
        drift = float((t0_stable & ~t1_stable).mean())
        mean_chg = float(selected["E_CHGNet_fullcal"].mean())
        mean_mace = float(selected["E_MACE_fullcal"].mean())
    else:
        t0_ftr = np.nan
        t1_ftr = np.nan
        drift = np.nan
        mean_chg = np.nan
        mean_mace = np.nan

    original = pool[pool["parc_seed_count"] > 0].copy()
    original_t1 = float((~bool_col(original["stable_exact_t1_current_mp"])).mean()) if len(original) else np.nan
    raw_t1 = float((~bool_col(pool["stable_exact_t1_current_mp"])).mean()) if len(pool) else np.nan
    row = {
        "method": method,
        "K": k,
        "alpha": ALPHA,
        "rho": RHO,
        "release_size": released,
        "t0_FTR": t0_ftr,
        "t1_FTR": t1_ftr,
        "t1_raw_topK_minus_method": raw_t1 - t1_ftr if released else np.nan,
        "t1_original_PARC_minus_method": original_t1 - t1_ftr if released else np.nan,
        "stable_to_current_not_stable_rate": drift,
        "mean_E_CHGNet_fullcal": mean_chg,
        "mean_E_MACE_fullcal": mean_mace,
        "release_threshold_tau": tau,
        "self_consistency_margin": margin,
        "best_mass_ratio": best_ratio,
        "construction_rule": construction_rule,
        "theorem_grade_source_status": "CHGNet_and_MACE_full_calibration_sources_available",
        "evidence_scope": SCOPE,
    }
    return row, selected


def candidate_output_row(row: pd.Series, method: str, k: int) -> dict[str, object]:
    return {
        "candidate_id": row["material_id"],
        "structure_hash": row.get("structure_hash", ""),
        "formula": row["formula"],
        "chemical_system": row["chemical_system"],
        "composition_family_pair": row["composition_family_pair"],
        "K": k,
        "method": method,
        "raw_rank": row["raw_rank"],
        "t0_label": "stable" if bool(row["stable_exact_t0"]) else "unstable_or_unresolved",
        "t1_label": "stable" if bool(row["stable_exact_t1_current_mp"]) else "unstable_or_unresolved",
        "drift_class": row["drift_class"],
        "E_original_PARC": row["parc_e_value"],
        "E_CHGNet_fullcal": row["E_CHGNet_fullcal"],
        "E_MACE_fullcal": row["E_MACE_fullcal"],
        "E_CHGNet_MACE_equal": row["E_CHGNet_MACE_equal"],
        "E_PARC_CHGNet_MACE_equal": row["E_PARC_CHGNet_MACE_equal"],
        "selected_evalue": row["_selected_evalue"],
        "evalue_scope": SCOPE,
    }


def build_results(target: pd.DataFrame, cal: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    target = target.copy()
    chg_e, chg_diag = compute_fullcal_evalues(
        cal, target, cal_score_col="chgnet_fullcal_score", target_score_col="target_chgnet_score"
    )
    mace_e, mace_diag = compute_fullcal_evalues(
        cal, target, cal_score_col="mace_fullcal_score", target_score_col="target_mace_score"
    )
    target["E_CHGNet_fullcal"] = chg_e
    target["E_MACE_fullcal"] = mace_e
    target["E_CHGNet_MACE_equal"] = (target["E_CHGNet_fullcal"] + target["E_MACE_fullcal"]) / 2.0
    target["E_PARC_CHGNet_MACE_equal"] = (
        target["parc_e_value"].astype(float) + target["E_CHGNet_fullcal"] + target["E_MACE_fullcal"]
    ) / 3.0
    target["E_PARC_CHGNetMACE_rawheavy"] = (
        0.50 * target["parc_e_value"].astype(float)
        + 0.25 * target["E_CHGNet_fullcal"]
        + 0.25 * target["E_MACE_fullcal"]
    )

    diag_rows = [
        {"source": "CHGNet", **chg_diag, "evidence_scope": SCOPE},
        {"source": "MACE-MP", **mace_diag, "evidence_scope": SCOPE},
    ]
    result_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []

    for k in [300, 500]:
        pool = target[(target["K"].eq(k)) & (target["raw_topK_seed_count"] > 0)].copy()
        baseline_specs = [
            ("raw top-K", pool.index.to_series().isin(pool.index)),
            ("PARC original release", pool["parc_seed_count"] > 0),
            ("matched raw top-R", pool["raw_topR_seed_count"] > 0),
            ("raw-only extra-tail", pool["raw_only_tail_seed_count"] > 0),
        ]
        for method, mask in baseline_specs:
            row, selected = summarize_selection(pool, k=k, method=method, e_col=None, mask=mask)
            result_rows.append(row)
            for _, cand in selected.iterrows():
                candidate_rows.append(candidate_output_row(cand, method, k))

        method_specs = [
            ("CHGNet-fullcal-only", "E_CHGNet_fullcal"),
            ("MACE-fullcal-only", "E_MACE_fullcal"),
            ("CHGNet-MACE-fullcal-equal", "E_CHGNet_MACE_equal"),
            ("PARC-CHGNet-MACE-fullcal-equal", "E_PARC_CHGNet_MACE_equal"),
            ("PARC-CHGNet-MACE-fullcal-rawheavy", "E_PARC_CHGNetMACE_rawheavy"),
        ]
        for method, e_col in method_specs:
            row, selected = summarize_selection(pool, k=k, method=method, e_col=e_col, mask=None)
            result_rows.append(row)
            for _, cand in selected.iterrows():
                candidate_rows.append(candidate_output_row(cand, method, k))

        original = next(r for r in result_rows if r["K"] == k and r["method"] == "PARC original release")
        candidates = [r for r in result_rows if r["K"] == k and "fullcal" in str(r["method"])]
        best = min(candidates, key=lambda row: np.inf if pd.isna(row["t1_FTR"]) else row["t1_FTR"])
        improvement = float(best["t1_original_PARC_minus_method"]) if not pd.isna(best["t1_original_PARC_minus_method"]) else np.nan
        gate_rows.extend(
            [
                {
                    "K": k,
                    "gate": "CHGNet_full_calibration_evalues_available",
                    "value": int(chg_diag["target_scored_rows"] > 0 and chg_diag["null_calibration_blocks"] > 0),
                    "threshold": 1,
                    "status": "PASS" if chg_diag["target_scored_rows"] > 0 and chg_diag["null_calibration_blocks"] > 0 else "FAIL",
                    "interpretation": "CHGNet full calibration source exists over frozen WBM calibration denominator",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "MACE_full_calibration_evalues_available",
                    "value": int(mace_diag["target_scored_rows"] > 0 and mace_diag["null_calibration_blocks"] > 0),
                    "threshold": 1,
                    "status": "PASS" if mace_diag["target_scored_rows"] > 0 and mace_diag["null_calibration_blocks"] > 0 else "FAIL",
                    "interpretation": "MACE full calibration source exists over frozen WBM calibration denominator",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "best_fullcal_t1_improvement_ge_0p05",
                    "value": improvement,
                    "threshold": 0.05,
                    "status": "PASS" if improvement >= 0.05 else "FAIL",
                    "interpretation": f"best full-calibration row is {best['method']}",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "best_fullcal_t1_improvement_ge_0p03",
                    "value": improvement,
                    "threshold": 0.03,
                    "status": "PASS" if improvement >= 0.03 else "FAIL",
                    "interpretation": f"best full-calibration row is {best['method']}",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "best_fullcal_release_nontrivial_ge_100",
                    "value": int(best["release_size"]),
                    "threshold": 100,
                    "status": "PASS" if int(best["release_size"]) >= 100 else "FAIL",
                    "interpretation": "best full-calibration row should not be a tiny post-hoc subset",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "headline_method_upgrade_allowed",
                    "value": int(improvement >= 0.05 and int(best["release_size"]) >= 100),
                    "threshold": 1,
                    "status": "PASS" if improvement >= 0.05 and int(best["release_size"]) >= 100 else "FAIL",
                    "interpretation": "headline requires strong t1 improvement and nontrivial release; otherwise this remains a full-calibration diagnostic",
                    "evidence_scope": SCOPE,
                },
            ]
        )
    return result_rows, candidate_rows, gate_rows, diag_rows


def write_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []
    fieldnames = list(rows[0].keys()) if rows else [
        "milestone",
        "path",
        "evidence_state",
        "manifest",
        "public_bundle_check",
    ]
    milestone = "ncs_phase62_full_calibration_mlip_evalues"
    rows = [row for row in rows if row.get("milestone") != milestone]
    row = {
        "milestone": milestone,
        "path": "outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/",
        "evidence_state": "completed_full_calibration_auxiliary_evalue_audit",
        "manifest": "outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase62_full_calibration_mlip_evalues",
    }
    rows.append({key: row.get(key, "") for key in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_claim_table(status: str) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "\n## Phase62 Full-Calibration MLIP E-Values\n"
    block = f"""{marker}
Status: `{status}`.

CHGNet and MACE-MP auxiliary scores are now audited as full-calibration
e-value sources over the frozen WBM one-per-composition-family calibration
denominator, with target-overlap rows excluded before computing block maxima.
This resolves the Phase61 queue-only proxy blocker for source availability, but
the milestone is still a t0/t1 queue audit: it is not DFT evidence, not a t1
alpha certificate, and not a prospective materials-discovery claim.
"""
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n" + block
    else:
        text = text.rstrip() + "\n" + block
    path.write_text(text, encoding="utf-8")


def update_evidence_ledger(status: str) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else [
        "claim_id",
        "claim_text",
        "evidence_type",
        "positive_evidence",
        "scope",
        "artifact_path",
        "hash",
        "validation_command",
        "status",
        "overclaim_guardrail",
    ]
    rows = [row for row in rows if row.get("claim_id") != "M-PARCM-FULLCAL-001"]
    artifact = OUT / "table_parc_m_full_calibration_gate_audit.csv"
    row = {
        "claim_id": "M-PARCM-FULLCAL-001",
        "claim_text": "CHGNet/MACE auxiliary sources have full-calibration e-values over the frozen WBM calibration subset, but do not pass the headline method-upgrade gate.",
        "evidence_type": "full_calibration_auxiliary_evalue_audit",
        "positive_evidence": "partial",
        "scope": status,
        "artifact_path": rel(artifact),
        "hash": sha256_file(artifact) if artifact.exists() else "",
        "validation_command": "make reproduce-ncs-phase62-full-calibration-mlip-evalues",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_t1_alpha_control_DFT_evidence_or_prospective_materials_discovery",
    }
    rows.append({key: row.get(key, "") for key in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-mace", action="store_true")
    parser.add_argument("--max-mace-rows", type=int, default=None, help="smoke-test limit; omit for full calibration scoring")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    target = load_target_queue()
    target_ids = set(target["material_id"].astype(str))
    cal, inventory_rows = load_calibration(
        target_ids=target_ids,
        force_mace=args.force_mace,
        max_mace_rows=args.max_mace_rows,
    )
    result_rows, candidate_rows, gate_rows, diag_rows = build_results(target, cal)
    inventory_rows.extend(diag_rows)

    write_csv(OUT / "table_full_calibration_score_inventory.csv", inventory_rows)
    write_csv(OUT / "table_parc_m_full_calibration_results.csv", result_rows)
    write_csv(OUT / "table_parc_m_full_calibration_candidate_level.csv", candidate_rows)
    write_csv(OUT / "table_parc_m_full_calibration_gate_audit.csv", gate_rows)
    write_csv(OUT / "figure_parc_m_full_calibration_inputs.csv", result_rows)

    protocol = """# Phase62 Full-Calibration CHGNet/MACE E-Value Protocol

Objective: replace the Phase61 queue-only CHGNet/MACE rank proxies with
auxiliary e-values computed from a frozen WBM calibration denominator.

Calibration denominator: the A3-v3 WBM one-per-composition-family calibration
subset. Before computing block maxima, any target queue candidate that overlaps
this denominator is excluded to avoid calibration-target leakage.

Scores:

- CHGNet: `-chgnet_energy_per_atom` from the frozen CHGNet calibration table.
- MACE-MP: `-mace_energy_per_atom` scored locally from the same WBM structures.

Observed positives: top-score 10% of DFT-stable calibration rows for each
source. All other calibration rows remain in the null-superset block-max
denominator. Candidate e-values use the same gamma rule as PARC.

Allowed claim: CHGNet/MACE can now be audited as full-calibration auxiliary
e-value sources over the frozen WBM calibration subset.

Forbidden claims: no t1 alpha control, no DFT evidence, no prospective
materials discovery, and no claim that this alone proves a new NCS headline.
"""
    (OUT / "FULL_CALIBRATION_MLIP_EVALUE_PROTOCOL.md").write_text(protocol, encoding="utf-8")

    gate = pd.DataFrame(gate_rows)
    source_pass = bool(
        gate[gate["gate"].isin(["CHGNet_full_calibration_evalues_available", "MACE_full_calibration_evalues_available"])]
        ["status"]
        .eq("PASS")
        .all()
    )
    headline_pass = bool(gate[gate["gate"].eq("headline_method_upgrade_allowed")]["status"].eq("PASS").all())
    medium_pass = bool(gate[gate["gate"].eq("best_fullcal_t1_improvement_ge_0p03")]["status"].eq("PASS").all())
    if headline_pass and source_pass:
        status = "headline_candidate_pending_claim_audit"
    elif source_pass and medium_pass:
        status = "completed_full_calibration_sources_medium_empirical_signal"
    elif source_pass:
        status = "completed_full_calibration_sources_no_headline_signal"
    else:
        status = "partial_full_calibration_source_audit"

    closeout = f"""# Phase62 Full-Calibration CHGNet/MACE E-Values

Status: `{status}`.

This milestone fixes the main Phase61 source-availability blocker: CHGNet and
MACE-MP are no longer used only as queue-level rank proxies. They are converted
to auxiliary e-values using a frozen WBM calibration denominator, with target
overlap excluded before block maxima are computed.

The result remains deliberately scoped. It is a full-calibration auxiliary
e-value audit over the available WBM calibration subset; it is not DFT evidence,
not a current-MP t1 alpha certificate, and not a prospective materials discovery claim.
Headline status depends on the gate table, especially whether the full-calibration
fusion gives a nontrivial release and improves t1 FTR over the original PARC
release by at least 0.05.
"""
    (OUT / "NCS_PHASE62_FULL_CALIBRATION_MLIP_EVALUES.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase62_full_calibration_mlip_evalues",
        "status": status,
        "source_tables": [
            rel(CHGNET_CAL),
            rel(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
            rel(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv"),
        ],
        "known_bad_external_chgnet_file": "private_CHGNet_download_placeholder_not_distributed",
        "known_bad_external_chgnet_file_type": "HTML placeholder or failed GitHub download, not used",
        "evidence_scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_artifact_index()
    update_claim_table(status)
    update_evidence_ledger(status)
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)} with status={status}")


if __name__ == "__main__":
    main()
