#!/usr/bin/env python3
"""Build NCS Phase52 uncertainty diagnostics for the materials t1 audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE49 = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition"
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
OUT = ROOT / "outputs/milestones/ncs_phase52_materials_t1_uncertainty"
EVIDENCE_SCOPE = (
    "completed_current_MP_hull_shift_utility_audit;"
    "not_strict_alpha_temporal_certificate;"
    "not_prospective_discovery;"
    "no_t1_label_used_for_selection"
)


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


def bool_label(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def policy_column(k: int, policy: str) -> str:
    return {
        "PARC": f"K{k}_PARC_release_seed_count",
        "raw_topK": f"K{k}_raw_topK_requested_budget_seed_count",
        "raw_topR": f"K{k}_raw_topR_matched_release_size_seed_count",
    }[policy]


def policy_counts(joined: pd.DataFrame, k: int, policy: str) -> pd.DataFrame:
    subset = joined[joined[policy_column(k, policy)].fillna(0) > 0].copy()
    subset["t1_false"] = ~subset["stable_exact_t1_current_mp"].map(bool_label)
    subset["stable_to_unstable"] = subset["drift_class"].eq("stable_to_unstable")
    grouped = (
        subset.groupby("chemical_system", as_index=True)
        .agg(
            n=("material_id", "nunique"),
            false_n=("t1_false", "sum"),
            stable_to_unstable_n=("stable_to_unstable", "sum"),
        )
        .astype(float)
    )
    return grouped


def rates_from_counts(counts: pd.DataFrame, sampled_chemsys: list[str]) -> dict[str, float]:
    if counts.empty:
        return {"ftr": np.nan, "drift": np.nan}
    sampled = counts.reindex(sampled_chemsys).fillna(0.0)
    n = sampled["n"].sum()
    if n <= 0:
        return {"ftr": np.nan, "drift": np.nan}
    return {
        "ftr": float(sampled["false_n"].sum() / n),
        "drift": float(sampled["stable_to_unstable_n"].sum() / n),
    }


def bootstrap_metrics(joined: pd.DataFrame, n_bootstrap: int = 2000) -> list[dict[str, object]]:
    rng = np.random.default_rng(20260528)
    rows: list[dict[str, object]] = []
    for k in [300, 500]:
        counts = {policy: policy_counts(joined, k, policy) for policy in ["PARC", "raw_topK"]}
        chemsys = sorted(set(counts["PARC"].index).union(set(counts["raw_topK"].index)))
        observed = {
            policy: rates_from_counts(counts[policy], chemsys) for policy in ["PARC", "raw_topK"]
        }
        boot_values = {
            "FTR_t1_raw_minus_PARC": [],
            "stable_to_unstable_raw_minus_PARC": [],
            "DCR": [],
        }
        for _ in range(n_bootstrap):
            sample = list(rng.choice(chemsys, size=len(chemsys), replace=True))
            parc = rates_from_counts(counts["PARC"], sample)
            raw = rates_from_counts(counts["raw_topK"], sample)
            boot_values["FTR_t1_raw_minus_PARC"].append(raw["ftr"] - parc["ftr"])
            boot_values["stable_to_unstable_raw_minus_PARC"].append(raw["drift"] - parc["drift"])
            boot_values["DCR"].append(parc["drift"] / raw["drift"] if raw["drift"] else np.nan)

        estimates = {
            "FTR_t1_raw_minus_PARC": observed["raw_topK"]["ftr"] - observed["PARC"]["ftr"],
            "stable_to_unstable_raw_minus_PARC": observed["raw_topK"]["drift"] - observed["PARC"]["drift"],
            "DCR": observed["PARC"]["drift"] / observed["raw_topK"]["drift"],
        }
        for metric, values in boot_values.items():
            arr = np.array(values, dtype=float)
            arr = arr[~np.isnan(arr)]
            rows.append(
                {
                    "metric": metric,
                    "K": k,
                    "estimate": estimates[metric],
                    "ci_low_95": float(np.percentile(arr, 2.5)),
                    "ci_high_95": float(np.percentile(arr, 97.5)),
                    "bootstrap_unit": "chemical_system",
                    "n_bootstrap": n_bootstrap,
                    "metric_status": "computed",
                    "evidence_scope": EVIDENCE_SCOPE,
                }
            )

        rows.append(
            {
                "metric": "MLIP_consensus_raw_minus_PARC",
                "K": k,
                "estimate": "",
                "ci_low_95": "",
                "ci_high_95": "",
                "bootstrap_unit": "chemical_system",
                "n_bootstrap": n_bootstrap,
                "metric_status": "not_evaluable_no_CHGNet_MACE_consensus_scores_for_WBM_queue",
                "evidence_scope": EVIDENCE_SCOPE,
            }
        )
    return rows


def ftr_for_ids(joined: pd.DataFrame, ids: set[str]) -> float:
    subset = joined[joined["material_id"].isin(ids)]
    if subset.empty:
        return float("nan")
    return float((~subset["stable_exact_t1_current_mp"].map(bool_label)).sum() / len(subset))


def stratified_random_ftrs(audit: pd.DataFrame, joined: pd.DataFrame, k: int, n_permutations: int = 2000) -> list[float]:
    rng = np.random.default_rng(20260528 + k)
    raw = audit[(audit["K"].eq(k)) & (audit["raw_topK_seed_count"] > 0)].copy()
    parc = audit[(audit["K"].eq(k)) & (audit["parc_seed_count"] > 0)].copy()
    raw["rank_bin"] = pd.qcut(raw["raw_rank"].rank(method="first"), q=5, labels=False, duplicates="drop")
    parc = parc.merge(raw[["material_id", "rank_bin"]], on="material_id", how="left")
    parc["rank_bin"] = parc["rank_bin"].fillna(0).astype(int)
    target_counts = parc["rank_bin"].value_counts().to_dict()
    raw_by_bin = {int(bin_id): group["material_id"].tolist() for bin_id, group in raw.groupby("rank_bin")}
    all_raw_ids = raw["material_id"].tolist()
    ftrs: list[float] = []
    for _ in range(n_permutations):
        sampled: list[str] = []
        for bin_id, count in target_counts.items():
            pool = raw_by_bin.get(int(bin_id), all_raw_ids)
            replace = len(pool) < count
            sampled.extend(rng.choice(pool, size=count, replace=replace).tolist())
        ftrs.append(ftr_for_ids(joined, set(sampled)))
    return ftrs


def randomization_tests(joined: pd.DataFrame, n_permutations: int = 2000) -> list[dict[str, object]]:
    audit = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    rows: list[dict[str, object]] = []
    for k in [300, 500]:
        parc_ids = set(joined.loc[joined[policy_column(k, "PARC")].fillna(0) > 0, "material_id"])
        raw_ids = set(joined.loc[joined[policy_column(k, "raw_topK")].fillna(0) > 0, "material_id"])
        rawr_ids = set(joined.loc[joined[policy_column(k, "raw_topR")].fillna(0) > 0, "material_id"])
        parc_ftr = ftr_for_ids(joined, parc_ids)
        raw_ftr = ftr_for_ids(joined, raw_ids)
        rawr_ftr = ftr_for_ids(joined, rawr_ids)
        random_ftrs = np.array(stratified_random_ftrs(audit, joined, k, n_permutations=n_permutations))
        random_mean = float(np.nanmean(random_ftrs))
        p_one = float((np.sum(random_ftrs <= parc_ftr) + 1) / (len(random_ftrs) + 1))
        p_two = min(1.0, 2.0 * min(p_one, 1.0 - p_one))
        for comparison, observed, note in [
            ("PARC_vs_full_raw_topK", raw_ftr - parc_ftr, "full raw top-K burden minus PARC burden"),
            ("PARC_vs_matched_raw_topR", rawr_ftr - parc_ftr, "matched raw prefix minus PARC burden"),
            (
                "PARC_vs_stratified_random_raw_topK_subset",
                random_mean - parc_ftr,
                "rank-bin matched random raw-topK subset mean minus PARC burden",
            ),
        ]:
            rows.append(
                {
                    "K": k,
                    "comparison": comparison,
                    "metric": "FTR_t1_difference",
                    "observed_difference": observed,
                    "p_value_one_sided": p_one,
                    "p_value_two_sided": p_two,
                    "n_permutations": n_permutations,
                    "stratification": "raw_rank_bin_matched_to_PARC;chemical_system_bootstrap_reported_separately",
                    "interpretation_note": note,
                    "evidence_scope": EVIDENCE_SCOPE,
                }
            )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    joined = pd.read_csv(PHASE49 / "table_t0_t1_label_join.csv")
    boot_rows = bootstrap_metrics(joined)
    write_csv(
        OUT / "table_t1_bootstrap_ci.csv",
        boot_rows,
        [
            "metric",
            "K",
            "estimate",
            "ci_low_95",
            "ci_high_95",
            "bootstrap_unit",
            "n_bootstrap",
            "metric_status",
            "evidence_scope",
        ],
    )
    rand_rows = randomization_tests(joined)
    write_csv(
        OUT / "table_t1_randomization_tests.csv",
        rand_rows,
        [
            "K",
            "comparison",
            "metric",
            "observed_difference",
            "p_value_one_sided",
            "p_value_two_sided",
            "n_permutations",
            "stratification",
            "interpretation_note",
            "evidence_scope",
        ],
    )
    closeout = """# NCS Phase52 Materials t1 Uncertainty

Status: `completed_block_bootstrap_and_randomization_diagnostic`

This milestone adds chemical-system block bootstrap intervals and frozen
rank-bin randomization tests for the current-MP t1 hull-shift audit. The
statistics support a version-shift utility claim only. They do not convert the
t1 audit into strict alpha=0.10 temporal control or prospective discovery.

The `MLIP_consensus_raw_minus_PARC` row is deliberately marked not evaluable
because candidate-level CHGNet/MACE consensus scores are not available for the
WBM queue in the public-safe cache.
"""
    (OUT / "NCS_PHASE52_MATERIALS_T1_UNCERTAINTY.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase52_materials_t1_uncertainty",
        "source_phase49": rel(PHASE49),
        "source_phase51": rel(PHASE51),
        "n_bootstrap": 2000,
        "n_permutations": 2000,
        "evidence_scope": EVIDENCE_SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
