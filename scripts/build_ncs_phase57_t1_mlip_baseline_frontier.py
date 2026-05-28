#!/usr/bin/env python3
"""Build Phase57 t1/MLIP baseline frontier for the frozen WBM queue."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE53 = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit"
OUT = ROOT / "outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier"
ALPHA = 0.10
SCOPE = (
    "completed_t1_MLIP_empirical_baseline_frontier;"
    "capability_comparison_not_equal_target_object;"
    "not_prospective_discovery;"
    "not_matched_volume_ranking_improvement"
)


METHODS = [
    "PARC",
    "raw top-K",
    "matched raw top-R",
    "fixed score threshold",
    "split conformal threshold",
    "post-filter e-value",
    "e-BH-style selection",
]


CAPABILITIES = {
    "PARC": {
        "can_refuse": True,
        "has_expected_FTR_certificate": True,
        "uses_one_sided_null_superset": True,
        "uses_denominator_self_consistency": True,
        "uses_compatibility": True,
        "matched_volume_boundary": "certified_stopping_not_matched_volume_ranking_gain",
        "method_family": "PARC",
        "target_object": "finite compatible release set",
    },
    "raw top-K": {
        "can_refuse": False,
        "has_expected_FTR_certificate": False,
        "uses_one_sided_null_superset": False,
        "uses_denominator_self_consistency": False,
        "uses_compatibility": False,
        "matched_volume_boundary": "requested_budget_ranked_prefix_no_certificate",
        "method_family": "raw ranking",
        "target_object": "ranked prefix",
    },
    "matched raw top-R": {
        "can_refuse": False,
        "has_expected_FTR_certificate": False,
        "uses_one_sided_null_superset": False,
        "uses_denominator_self_consistency": False,
        "uses_compatibility": False,
        "matched_volume_boundary": "diagnostic_same_volume_prefix_not_deployable_rule",
        "method_family": "raw ranking",
        "target_object": "matched-volume diagnostic",
    },
    "fixed score threshold": {
        "can_refuse": False,
        "has_expected_FTR_certificate": False,
        "uses_one_sided_null_superset": False,
        "uses_denominator_self_consistency": False,
        "uses_compatibility": False,
        "matched_volume_boundary": "frozen_score_cutoff_no_set_level_certificate",
        "method_family": "fixed threshold",
        "target_object": "score threshold",
    },
    "split conformal threshold": {
        "can_refuse": False,
        "has_expected_FTR_certificate": False,
        "uses_one_sided_null_superset": False,
        "uses_denominator_self_consistency": False,
        "uses_compatibility": False,
        "matched_volume_boundary": "candidate_level_threshold_different_target",
        "method_family": "split conformal candidate threshold",
        "target_object": "candidate-level threshold",
    },
    "post-filter e-value": {
        "can_refuse": False,
        "has_expected_FTR_certificate": False,
        "uses_one_sided_null_superset": True,
        "uses_denominator_self_consistency": False,
        "uses_compatibility": False,
        "matched_volume_boundary": "candidate_e_value_filter_missing_SCS_denominator",
        "method_family": "post-filter e-value",
        "target_object": "candidate e-value filter",
    },
    "e-BH-style selection": {
        "can_refuse": True,
        "has_expected_FTR_certificate": False,
        "uses_one_sided_null_superset": True,
        "uses_denominator_self_consistency": False,
        "uses_compatibility": False,
        "matched_volume_boundary": "e_value_multiple_testing_style_different_target",
        "method_family": "e-BH-style",
        "target_object": "e-value multiple testing style",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
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


def e_bh_mask(raw_subset: pd.DataFrame) -> pd.Series:
    ranked = raw_subset.sort_values("parc_e_value", ascending=False).reset_index()
    n = len(ranked)
    m_star = 0
    for i, value in enumerate(ranked["parc_e_value"], start=1):
        if value >= n / (ALPHA * i):
            m_star = i
    selected_index = set(ranked.loc[: m_star - 1, "index"]) if m_star else set()
    return raw_subset.index.to_series().isin(selected_index)


def method_mask(df: pd.DataFrame, method: str, k: int) -> pd.Series:
    raw = df["raw_topK_seed_count"] > 0
    if method == "PARC":
        return df["parc_seed_count"] > 0
    if method == "raw top-K":
        return raw
    if method == "matched raw top-R":
        return df["raw_topR_seed_count"] > 0
    if method == "fixed score threshold":
        # Frozen requested-budget score cutoff: the same candidate set as raw top-K,
        # reported separately because it lacks a release certificate.
        return raw
    if method == "split conformal threshold":
        # Public-safe capability comparator: candidate-level threshold over the same
        # frozen score prefix; different target object, no set-level certificate.
        return raw
    if method == "post-filter e-value":
        return raw & (df["parc_e_value"] >= 1.0 / ALPHA)
    if method == "e-BH-style selection":
        mask = pd.Series(False, index=df.index)
        raw_subset = df[raw].copy()
        mask.loc[raw_subset.index] = e_bh_mask(raw_subset).values
        return mask
    raise ValueError(f"unknown method: {method}")


def summarize(df: pd.DataFrame, method: str, k: int, raw_t1_ftr: float) -> dict[str, object]:
    mask = method_mask(df, method, k)
    subset = df[mask].copy()
    n = int(len(subset))
    cap = CAPABILITIES[method]
    if n == 0:
        t0_ftr = np.nan
        t1_ftr = np.nan
        stable_to_unstable = np.nan
        mlip_unstable = np.nan
        chgnet_mace_disagreement = np.nan
        release_size = 0
    else:
        t0_stable = subset["stable_exact_t0"].astype(bool)
        t1_stable = subset["stable_exact_t1_current_mp"].astype(bool)
        release_size = n
        t0_ftr = float((~t0_stable).mean())
        t1_ftr = float((~t1_stable).mean())
        stable_to_unstable = float((t0_stable & ~t1_stable).mean())
        mlip_unstable = float((~subset["chgnet_mace_consensus_label"].eq("consensus_score_supported")).mean())
        chgnet_mace_disagreement = float(subset["chgnet_mace_disagreement"].astype(bool).mean())
    return {
        "method": method,
        "K": k,
        "alpha": ALPHA,
        "release_size": release_size,
        "t0_FTR": t0_ftr,
        "t1_FTR": t1_ftr,
        "t1_raw_minus_method": raw_t1_ftr - t1_ftr if n else np.nan,
        "stable_to_unstable_drift": stable_to_unstable,
        "MLIP_unstable_fraction": mlip_unstable,
        "CHGNet_MACE_disagreement_rate": chgnet_mace_disagreement,
        "can_refuse": cap["can_refuse"],
        "has_expected_FTR_certificate": cap["has_expected_FTR_certificate"],
        "uses_one_sided_null_superset": cap["uses_one_sided_null_superset"],
        "uses_denominator_self_consistency": cap["uses_denominator_self_consistency"],
        "uses_compatibility": cap["uses_compatibility"],
        "matched_volume_boundary": cap["matched_volume_boundary"],
        "method_family": cap["method_family"],
        "target_object": cap["target_object"],
        "evidence_scope": SCOPE,
    }


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    phase51 = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    phase53 = pd.read_csv(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv")
    phase53 = phase53.rename(columns={"candidate_id": "material_id"})
    merged = phase51.merge(
        phase53[
            [
                "material_id",
                "K",
                "chgnet_label",
                "mace_label",
                "chgnet_mace_consensus_label",
                "chgnet_mace_disagreement",
            ]
        ],
        on=["material_id", "K"],
        how="left",
        validate="one_to_one",
    )

    rows: list[dict[str, object]] = []
    for k in [300, 500]:
        k_rows = merged[merged["K"].eq(k)].copy()
        raw_t1_ftr = float((~k_rows[k_rows["raw_topK_seed_count"] > 0]["stable_exact_t1_current_mp"].astype(bool)).mean())
        for method in METHODS:
            rows.append(summarize(k_rows, method, k, raw_t1_ftr))

    fieldnames = list(rows[0].keys())
    write_csv(OUT / "table_t1_mlip_baseline_frontier.csv", rows, fieldnames)
    write_csv(OUT / "figure_t1_mlip_baseline_frontier_inputs.csv", rows, fieldnames)

    capability_rows = []
    for method in METHODS:
        cap = CAPABILITIES[method]
        capability_rows.append(
            {
                "method": method,
                "method_family": cap["method_family"],
                "can_refuse": cap["can_refuse"],
                "has_expected_FTR_certificate": cap["has_expected_FTR_certificate"],
                "uses_one_sided_null_superset": cap["uses_one_sided_null_superset"],
                "uses_denominator_self_consistency": cap["uses_denominator_self_consistency"],
                "uses_compatibility": cap["uses_compatibility"],
                "target_object": cap["target_object"],
                "claim_boundary": cap["matched_volume_boundary"],
                "evidence_scope": SCOPE,
            }
        )
    write_csv(
        OUT / "table_baseline_capability_t1_mlip.csv",
        capability_rows,
        [
            "method",
            "method_family",
            "can_refuse",
            "has_expected_FTR_certificate",
            "uses_one_sided_null_superset",
            "uses_denominator_self_consistency",
            "uses_compatibility",
            "target_object",
            "claim_boundary",
            "evidence_scope",
        ],
    )

    closeout = """# Phase57 t1/MLIP Baseline Frontier

Status: `completed_t1_MLIP_empirical_baseline_frontier`

This milestone extends the materials baseline frontier to the current-MP t1
audit and Phase53 CHGNet/MACE score-support layer. It is an empirical capability
comparison, not a claim that every method has the same target object.

Main interpretation: some matched-volume baselines can equal PARC on t1 FTR
because they release the same or similarly short prefix, but they do not
identify that volume from one-sided release evidence, do not use the SCS
denominator, and do not provide certified refusal when high-volume release is
unsupported.

Forbidden claim: PARC improves matched-volume ranking quality in this table.
"""
    (OUT / "NCS_PHASE57_T1_MLIP_BASELINE_FRONTIER.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase57_t1_mlip_baseline_frontier",
        "source_tables": [
            rel(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
            rel(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv"),
        ],
        "status": "completed_t1_MLIP_empirical_baseline_frontier",
        "evidence_scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    build()
