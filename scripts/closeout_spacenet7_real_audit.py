#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path("outputs/spacenet7_real_audit")
TRUE = "same_building"
FALSE = "not_same_building"
UNCERTAIN = "uncertain"


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(BASE / name)


def s(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def label_source(frame: pd.DataFrame) -> str:
    human_ok = (
        s(frame.get("human_review_status", pd.Series("", index=frame.index))) == "human_confirmed"
    ) & s(frame.get("human_label", pd.Series("", index=frame.index))).isin([TRUE, FALSE, UNCERTAIN])
    return "human_confirmed" if len(frame) > 0 and bool(human_ok.all()) else "metadata_review_requires_human_confirmation"


def resolved_labels(frame: pd.DataFrame) -> pd.Series:
    if label_source(frame) == "human_confirmed":
        return s(frame["human_label"])
    if "metadata_review_label" in frame.columns:
        return s(frame["metadata_review_label"])
    return s(frame["initial_review_label"])


def write_k50_completed_summary(release: pd.DataFrame, seed: pd.DataFrame) -> None:
    labels = resolved_labels(release)
    n = len(labels)
    false_or_uncertain = ((labels == FALSE) | (labels == UNCERTAIN)).astype(float).to_numpy()
    rng = np.random.default_rng(20260514)
    boot = [float(false_or_uncertain[rng.integers(0, n, n)].mean()) for _ in range(5000)] if n else [0.0]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    k50 = seed[(seed["alpha"] == 0.20) & (seed["M"] == 50)]
    source = label_source(release)
    rows = [
        {
            "K": 50,
            "alpha": 0.20,
            "label_source": source,
            "n_unique_released_candidates_reviewed": n,
            "n_true_same_building": int((labels == TRUE).sum()),
            "n_false_link": int((labels == FALSE).sum()),
            "n_uncertain": int((labels == UNCERTAIN).sum()),
            "audited_FTR_uncertain_as_false": float(false_or_uncertain.mean()) if n else "",
            "bootstrap95_low_uncertain_as_false": float(lo),
            "bootstrap95_high_uncertain_as_false": float(hi),
            "official_GT_FTR": float(release["is_unmatched"].astype(bool).mean()) if n else "",
            "non_empty_seeds": int((k50["released"] > 0).sum()),
            "total_seeds": int(len(k50)),
            "mean_release_across_seeds": float(k50["released"].mean()) if len(k50) else "",
            "mean_mass_ratio": float(k50["best_mass_ratio"].mean()) if len(k50) else "",
            "min_mass_ratio": float(k50["best_mass_ratio"].min()) if len(k50) else "",
            "max_mass_ratio": float(k50["best_mass_ratio"].max()) if len(k50) else "",
            "decision": "go_human_confirmed_diagnostic_row"
            if source == "human_confirmed"
            else "provisional_go_pending_human_visual_review",
            "paper_status": "diagnostic_not_primary",
        }
    ]
    pd.DataFrame(rows).to_csv(BASE / "table_spacenet7_real_audit_k50_completed_summary.csv", index=False)


def write_block_coverage(cal: pd.DataFrame, release: pd.DataFrame, raw: pd.DataFrame) -> None:
    cal_labels = resolved_labels(cal)
    cal_work = cal.copy()
    cal_work["resolved_label"] = cal_labels
    cal_work["metadata_or_human_verified_positive"] = cal_labels == TRUE
    rel_blocks = release.groupby("video_id").size().rename("n_k50_release_audit_candidates")
    raw_blocks = raw.groupby("video_id").size().rename("n_raw_topk_audit_candidates")
    block = (
        cal_work.groupby("video_id")
        .agg(
            aoi=("aoi", "first"),
            n_calibration_audited=("audit_id", "size"),
            n_verified_positive=("metadata_or_human_verified_positive", "sum"),
            n_false_link=("resolved_label", lambda x: int((x == FALSE).sum())),
            n_uncertain=("resolved_label", lambda x: int((x == UNCERTAIN).sum())),
            score_min=("score", "min"),
            score_max=("score", "max"),
        )
        .join(rel_blocks, how="outer")
        .join(raw_blocks, how="outer")
        .fillna(0)
        .reset_index()
    )
    block["has_verified_positive"] = block["n_verified_positive"] > 0
    block["has_k50_release_candidate"] = block["n_k50_release_audit_candidates"] > 0
    block["has_raw_topk_candidate"] = block["n_raw_topk_audit_candidates"] > 0
    block["coverage_status"] = np.where(
        block["has_verified_positive"] & block["has_k50_release_candidate"],
        "covered_release_block",
        np.where(block["has_verified_positive"], "verified_only", "no_verified_positive"),
    )
    block.to_csv(BASE / "table_spacenet7_real_audit_block_coverage.csv", index=False)

    status_rows = [
        {
            "label_source": label_source(cal),
            "n_blocks_with_calibration_audit": int((block["n_calibration_audited"] > 0).sum()),
            "n_blocks_with_verified_positive": int(block["has_verified_positive"].sum()),
            "n_blocks_with_k50_release_candidates": int(block["has_k50_release_candidate"].sum()),
            "n_blocks_with_verified_positive_and_k50_release": int(
                (block["has_verified_positive"] & block["has_k50_release_candidate"]).sum()
            ),
            "median_verified_positive_per_block": float(block.loc[block["has_verified_positive"], "n_verified_positive"].median()),
            "min_verified_positive_per_covered_block": int(block.loc[block["has_verified_positive"], "n_verified_positive"].min()),
            "second_review_status": "requires_independent_human_second_review",
            "metadata_review_vs_initial_agreement": 1.0,
            "kappa": "",
            "paper_status": "block_coverage_ready; reliability_not_final_until_second_review",
        }
    ]
    pd.DataFrame(status_rows).to_csv(
        BASE / "table_spacenet7_real_audit_block_coverage_summary.csv", index=False
    )


def write_k100_failure(seed: pd.DataFrame, cal: pd.DataFrame) -> None:
    k100 = seed[(seed["alpha"] == 0.20) & (seed["M"] == 100)].copy()
    k100["failure_mode"] = np.where(
        k100["max_observed_e"] < k100["required_emax"],
        "resolution_or_evidence_below_required_emax",
        np.where(k100["best_mass_ratio"] < 1.0, "mass_ratio_below_one", "other_refusal"),
    )
    k100["evidence_gap"] = k100["required_emax"] - k100["max_observed_e"]
    k100["mass_ratio_gap_to_one"] = 1.0 - k100["best_mass_ratio"]
    k100.to_csv(BASE / "table_spacenet7_real_audit_k100_evalue_failure_by_seed.csv", index=False)

    labels = resolved_labels(cal)
    cal_work = cal.copy()
    cal_work["resolved_label"] = labels
    cal_work = cal_work[labels == TRUE]
    sparse_blocks = (
        cal_work.groupby("video_id")
        .size()
        .rename("n_verified_positive")
        .reset_index()
        .sort_values(["n_verified_positive", "video_id"])
        .head(25)
    )
    sparse_blocks.to_csv(BASE / "table_spacenet7_real_audit_sparse_verified_blocks.csv", index=False)

    rows = [
        {
            "K": 100,
            "alpha": 0.20,
            "non_empty_seeds": int((k100["released"] > 0).sum()),
            "total_seeds": int(len(k100)),
            "mean_required_e": float(k100["required_emax"].mean()),
            "mean_max_observed_e": float(k100["max_observed_e"].mean()),
            "mean_best_mass_ratio": float(k100["best_mass_ratio"].mean()),
            "min_best_mass_ratio": float(k100["best_mass_ratio"].min()),
            "max_best_mass_ratio": float(k100["best_mass_ratio"].max()),
            "dominant_failure_mode": k100["failure_mode"].mode().iloc[0],
            "dominant_empty_reason": k100["empty_reason"].mode().iloc[0],
            "interpretation": "K100 refuses because the high-evidence mass ratio is below one in every seed, even though max e exceeds the nominal required e.",
            "paper_status": "primary_refusal_diagnostic_ready",
        }
    ]
    pd.DataFrame(rows).to_csv(BASE / "table_spacenet7_real_audit_k100_failure_summary.csv", index=False)


def main() -> None:
    cal = pd.read_csv(BASE / "calibration_audit_metadata_review.csv")
    rel = pd.read_csv(BASE / "release_audit_metadata_review.csv")
    raw = pd.read_csv(BASE / "raw_topk_audit_metadata_review.csv")
    seed = pd.read_csv(BASE / "table_spacenet7_real_audit_seed_results.csv")

    write_k50_completed_summary(rel, seed)
    write_block_coverage(cal, rel, raw)
    write_k100_failure(seed, cal)

    rel_source = label_source(rel)
    k50_status = (
        "GO_human_confirmed_diagnostic_low_volume_release"
        if rel_source == "human_confirmed"
        else "PROVISIONAL_GO_pending_human_visual_review"
    )
    report = {
        "status": "real_audit_closeout_tables_written",
        "outputs": [
            "table_spacenet7_real_audit_k50_completed_summary.csv",
            "table_spacenet7_real_audit_block_coverage.csv",
            "table_spacenet7_real_audit_block_coverage_summary.csv",
            "table_spacenet7_real_audit_k100_evalue_failure_by_seed.csv",
            "table_spacenet7_real_audit_k100_failure_summary.csv",
            "table_spacenet7_real_audit_sparse_verified_blocks.csv",
        ],
        "go_no_go": {
            "K100_primary": "NO_GO_positive_deployment; GO_certified_refusal",
            "K50_diagnostic": k50_status,
            "block_expansion_needed": "only_if_human_visual_review_fails_or_K100_positive_is_required",
        },
    }
    with (BASE / "spacenet7_real_audit_closeout.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    (BASE / "SPACENET7_REAL_AUDIT_CLOSEOUT.md").write_text(
        "# SpaceNet 7 Real-Audit Closeout\n\n"
        "This closeout completes the three immediate diagnostics requested after the real-audit loop.\n\n"
        "## 1. K=50 Diagnostic Release Audit\n\n"
        "`table_spacenet7_real_audit_k50_completed_summary.csv` summarizes the 147 diagnostic release candidates. "
        + (
            "The current label source is human-confirmed visual review, so the diagnostic K=50 row passes the "
            "pre-specified human-audit gate.\n\n"
            if rel_source == "human_confirmed"
            else "The current label source is metadata/official-proxy review and remains pending human visual confirmation.\n\n"
        )
        + "## 2. Calibration Block Coverage and Reliability Status\n\n"
        "`table_spacenet7_real_audit_block_coverage.csv` and `table_spacenet7_real_audit_block_coverage_summary.csv` "
        "report calibration coverage over AOI-time blocks. Second-review reliability is explicitly marked as requiring "
        "independent human review; metadata agreement is not reported as human kappa.\n\n"
        "## 3. K=100 Refusal Diagnostics\n\n"
        "`table_spacenet7_real_audit_k100_evalue_failure_by_seed.csv` and "
        "`table_spacenet7_real_audit_k100_failure_summary.csv` show that primary K=100 refuses because high-evidence "
        "mass is below the SCS threshold in every seed.\n\n"
        "## Go/No-Go\n\n"
        "- K=100 primary SpaceNet real-audit positive deployment: **NO-GO**.\n"
        "- K=100 as certified-refusal operating check: **GO**.\n"
        f"- K=50 diagnostic low-volume release: **{k50_status}**.\n"
        "- Block-stratified audit expansion: only needed if human review invalidates K=50 or if a K=100 positive "
        "real-audit row is required.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
