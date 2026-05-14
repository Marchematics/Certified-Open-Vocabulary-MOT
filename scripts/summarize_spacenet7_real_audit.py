#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


LABEL_TRUE = "same_building"
LABEL_FALSE = "not_same_building"
LABEL_UNCERTAIN = "uncertain"


def clean_str(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def resolved_review(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    out = frame.copy()
    human_status = clean_str(out.get("human_review_status", pd.Series("", index=out.index)))
    human_label = clean_str(out.get("human_label", pd.Series("", index=out.index)))
    human_verified = clean_str(out.get("human_verified_positive_for_calibration", pd.Series("", index=out.index))).str.lower()
    use_human = (human_status == "human_confirmed") & human_label.isin([LABEL_TRUE, LABEL_FALSE, LABEL_UNCERTAIN])
    if bool(use_human.all()) and len(out) > 0:
        out["resolved_label"] = human_label
        out["resolved_verified_positive_for_calibration"] = np.where(human_verified == "yes", "yes", "no")
        out["resolved_source"] = "human_confirmed"
        return out, "human_confirmed"

    out["resolved_label"] = clean_str(out["initial_review_label"])
    out["resolved_verified_positive_for_calibration"] = clean_str(
        out["initial_verified_positive_for_calibration"]
    ).str.lower()
    out["resolved_source"] = "initial_official_proxy_requires_human_confirmation"
    return out, "initial_official_proxy_requires_human_confirmation"


def ftr_summary(frame: pd.DataFrame) -> dict:
    n = len(frame)
    if n == 0:
        return {
            "n_audited": 0,
            "n_true_same_building": 0,
            "n_false_link": 0,
            "n_uncertain": 0,
            "audited_FTR_uncertain_as_false": "",
            "audited_FTR_uncertain_excluded": "",
            "bootstrap_CI_low_uncertain_as_false": "",
            "bootstrap_CI_high_uncertain_as_false": "",
        }
    labels = clean_str(frame["resolved_label"])
    n_true = int((labels == LABEL_TRUE).sum())
    n_false = int((labels == LABEL_FALSE).sum())
    n_uncertain = int((labels == LABEL_UNCERTAIN).sum())
    values = ((labels == LABEL_FALSE) | (labels == LABEL_UNCERTAIN)).astype(float).to_numpy()
    rng = np.random.default_rng(20260514)
    if n > 1:
        boot = [float(values[rng.integers(0, n, n)].mean()) for _ in range(5000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
    else:
        lo = hi = float(values.mean())
    denom_excl = n_true + n_false
    return {
        "n_audited": n,
        "n_true_same_building": n_true,
        "n_false_link": n_false,
        "n_uncertain": n_uncertain,
        "audited_FTR_uncertain_as_false": float((n_false + n_uncertain) / n),
        "audited_FTR_uncertain_excluded": float(n_false / denom_excl) if denom_excl else "",
        "bootstrap_CI_low_uncertain_as_false": float(lo),
        "bootstrap_CI_high_uncertain_as_false": float(hi),
    }


def simple_kappa(a: pd.Series, b: pd.Series) -> float | str:
    a = clean_str(a)
    b = clean_str(b)
    mask = a.isin([LABEL_TRUE, LABEL_FALSE, LABEL_UNCERTAIN]) & b.isin([LABEL_TRUE, LABEL_FALSE, LABEL_UNCERTAIN])
    if int(mask.sum()) == 0:
        return ""
    labels = [LABEL_TRUE, LABEL_FALSE, LABEL_UNCERTAIN]
    a = a[mask]
    b = b[mask]
    po = float((a == b).mean())
    pe = 0.0
    for label in labels:
        pe += float((a == label).mean()) * float((b == label).mean())
    if pe >= 1.0:
        return 1.0
    return float((po - pe) / (1.0 - pe))


def write_calibration_summary(out_dir: Path, cal: pd.DataFrame, manifest: pd.DataFrame) -> None:
    cal_resolved, label_source = resolved_review(cal)
    labels = clean_str(cal_resolved["resolved_label"])
    verified = clean_str(cal_resolved["resolved_verified_positive_for_calibration"]).str.lower() == "yes"
    official_positive = ~cal_resolved["is_unmatched"].astype(bool)
    verified_by_block = cal_resolved[verified].groupby("video_id").size()
    human_status = clean_str(cal_resolved.get("human_review_status", pd.Series("", index=cal_resolved.index)))
    human_labels = clean_str(cal_resolved.get("human_label", pd.Series("", index=cal_resolved.index)))
    has_human = bool(((human_status == "human_confirmed") & human_labels.ne("")).any())
    rows = [
        {
            "status": "review_ready" if label_source != "human_confirmed" else "human_confirmed",
            "label_source": label_source,
            "n_audited": int(len(cal_resolved)),
            "n_verified_positive": int(verified.sum()),
            "n_true_same_building": int((labels == LABEL_TRUE).sum()),
            "n_false_link": int((labels == LABEL_FALSE).sum()),
            "n_uncertain": int((labels == LABEL_UNCERTAIN).sum()),
            "n_disagreement_with_initial": int((human_status == "human_confirmed").sum() - (human_labels == cal_resolved["initial_review_label"].fillna("")).sum())
            if has_human
            else "",
            "n_adjudicated_positive": int(verified.sum()) if label_source == "human_confirmed" else "",
            "verified_positive_precision_vs_official_GT": float((official_positive[verified]).mean()) if int(verified.sum()) else "",
            "kappa_vs_initial_if_human_confirmed": simple_kappa(cal_resolved["initial_review_label"], cal_resolved.get("human_label", pd.Series("", index=cal_resolved.index)))
            if has_human
            else "",
            "num_blocks_covered": int(cal_resolved["video_id"].nunique()),
            "num_blocks_total_in_audit_manifest": int(manifest["video_id"].nunique()),
            "median_verified_positive_per_block": float(verified_by_block.median()) if len(verified_by_block) else 0.0,
            "min_verified_positive_per_covered_block": int(verified_by_block.min()) if len(verified_by_block) else 0,
            "paper_status": "requires_human_confirmation" if label_source != "human_confirmed" else "paper_ready_if_protocol_accepted",
        }
    ]
    pd.DataFrame(rows).to_csv(out_dir / "table_spacenet7_real_audit_calibration_summary.csv", index=False)


def write_primary_refusal(out_dir: Path, seed_results: pd.DataFrame, cal: pd.DataFrame, rel: pd.DataFrame) -> None:
    primary = seed_results[(seed_results["alpha"] == 0.20) & (seed_results["M"] == 100)].copy()
    cal_resolved, label_source = resolved_review(cal)
    verified = clean_str(cal_resolved["resolved_verified_positive_for_calibration"]).str.lower() == "yes"
    verified_by_block = cal_resolved[verified].groupby("video_id").size().sort_values()
    failure_blocks = ";".join([f"{int(k)}:{int(v)}" for k, v in verified_by_block.head(10).items()])
    rows = [
        {
            "K": 100,
            "alpha": 0.20,
            "label_source": label_source,
            "non_empty_seeds": int((primary["released"] > 0).sum()),
            "total_seeds": int(len(primary)),
            "mean_max_observed_e": float(primary["max_observed_e"].mean()),
            "max_observed_e": float(primary["max_observed_e"].max()),
            "required_e": float(primary["required_emax"].mean()),
            "mean_best_mass_ratio": float(primary["best_mass_ratio"].mean()),
            "min_best_mass_ratio": float(primary["best_mass_ratio"].min()),
            "max_best_mass_ratio": float(primary["best_mass_ratio"].max()),
            "dominant_empty_reason": primary["empty_reason"].mode().iloc[0] if len(primary) else "",
            "num_blocks_with_verified_positive": int(cal_resolved.loc[verified, "video_id"].nunique()),
            "num_blocks_with_release_candidates": int(rel["video_id"].nunique()),
            "n_cal_blocks_mean_across_seed_splits": float(primary["n_cal_blocks"].mean()) if len(primary) else "",
            "n_nonempty_null_cal_blocks_mean_across_seed_splits": float(primary["n_nonempty_null_cal_blocks"].mean()) if len(primary) else "",
            "lowest_verified_positive_blocks": failure_blocks,
            "interpretation": "primary_refusal_under_real_audit_initial_review; mass_ratio_below_one_for_K100",
            "paper_status": "requires_human_confirmation",
        }
    ]
    pd.DataFrame(rows).to_csv(out_dir / "table_spacenet7_real_audit_primary_refusal_diagnostics.csv", index=False)


def write_release_and_raw(out_dir: Path, release: pd.DataFrame, raw: pd.DataFrame, seed_results: pd.DataFrame) -> None:
    release_resolved, release_source = resolved_review(release)
    raw_resolved, raw_source = resolved_review(raw)
    k50 = seed_results[(seed_results["alpha"] == 0.20) & (seed_results["M"] == 50)].copy()
    rel_sum = ftr_summary(release_resolved)
    rel_sum.update(
        {
            "K": 50,
            "alpha": 0.20,
            "label_source": release_source,
            "num_unique_released_candidates": int(len(release_resolved)),
            "official_GT_FTR": float(release_resolved["is_unmatched"].astype(bool).mean()) if len(release_resolved) else "",
            "raw_topK_official_FTR_from_seed_table": float(k50["raw_topM_official_GT_FTR"].mean()) if len(k50) else "",
            "non_empty_seeds": int((k50["released"] > 0).sum()) if len(k50) else "",
            "total_seeds": int(len(k50)),
            "mean_release_across_seeds": float(k50["released"].mean()) if len(k50) else "",
            "setting_status": "diagnostic_predefined_budget_after_primary_refusal",
            "paper_status": "requires_human_confirmation" if release_source != "human_confirmed" else "diagnostic_human_audit_ready",
        }
    )
    pd.DataFrame([rel_sum]).to_csv(out_dir / "table_spacenet7_real_audit_k50_release_audit.csv", index=False)

    raw_sum = ftr_summary(raw_resolved)
    raw_sum.update(
        {
            "label_source": raw_source,
            "sample_design": "high_score_nonreleased_raw_pool_after_excluding_diagnostic_release_candidates",
            "official_GT_FTR": float(raw_resolved["is_unmatched"].astype(bool).mean()) if len(raw_resolved) else "",
            "score_min": float(raw_resolved["score"].min()) if len(raw_resolved) else "",
            "score_max": float(raw_resolved["score"].max()) if len(raw_resolved) else "",
            "num_blocks": int(raw_resolved["video_id"].nunique()),
            "paper_status": "requires_human_confirmation" if raw_source != "human_confirmed" else "human_audit_ready",
        }
    )
    pd.DataFrame([raw_sum]).to_csv(out_dir / "table_spacenet7_real_audit_raw_topK_audit.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/spacenet7_real_audit")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    cal = pd.read_csv(out_dir / "calibration_audit_review_prefill.csv")
    rel = pd.read_csv(out_dir / "release_audit_review_prefill.csv")
    raw = pd.read_csv(out_dir / "raw_topk_audit_review_prefill.csv")
    manifest = pd.read_csv(out_dir / "audit_manifest.csv")
    seed_results = pd.read_csv(out_dir / "table_spacenet7_real_audit_seed_results.csv")

    write_calibration_summary(out_dir, cal, manifest)
    write_primary_refusal(out_dir, seed_results, cal, rel)
    write_release_and_raw(out_dir, rel, raw, seed_results)

    report = {
        "status": "summary_tables_written",
        "tables": [
            "table_spacenet7_real_audit_calibration_summary.csv",
            "table_spacenet7_real_audit_primary_refusal_diagnostics.csv",
            "table_spacenet7_real_audit_k50_release_audit.csv",
            "table_spacenet7_real_audit_raw_topK_audit.csv",
        ],
        "paper_status": "requires_human_confirmation_until_human_fields_are_completed",
    }
    with (out_dir / "spacenet7_real_audit_summary_tables.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    run_report = out_dir / "RUN_REPORT.md"
    if run_report.exists():
        text = run_report.read_text(encoding="utf-8")
        marker = "## Summary Tables\n"
        summary_section = (
            "## Summary Tables\n\n"
            "- Calibration audit summary: `table_spacenet7_real_audit_calibration_summary.csv`\n"
            "- Primary K=100 refusal diagnostics: `table_spacenet7_real_audit_primary_refusal_diagnostics.csv`\n"
            "- K=50 diagnostic release audit: `table_spacenet7_real_audit_k50_release_audit.csv`\n"
            "- Raw top-K/high-score audit: `table_spacenet7_real_audit_raw_topK_audit.csv`\n\n"
            "All summary tables remain marked `requires_human_confirmation` until the `human_*` fields are completed.\n"
        )
        if marker in text:
            text = text.split(marker, 1)[0].rstrip() + "\n\n" + summary_section
        else:
            text = text.rstrip() + "\n\n" + summary_section
        run_report.write_text(text, encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
