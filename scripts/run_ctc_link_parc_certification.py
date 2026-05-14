#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

import pandas as pd
import yaml


def safe_token(value: float | int | str) -> str:
    return str(value).replace(".", "p").replace("/", "_").replace(" ", "_")


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def raw_topm_rows(universe: pd.DataFrame, budgets: list[int], alphas: list[float], seeds: list[int]) -> pd.DataFrame:
    rows = []
    universe = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    for budget in budgets:
        pool = universe.head(int(budget)).copy()
        unsupported = bool_series(pool["is_unmatched"]) if "is_unmatched" in pool else pd.Series([], dtype=bool)
        false_rate = float(unsupported.mean()) if len(pool) else 0.0
        large_displacement = (
            (pool.get("link_distance_score", pd.Series([1.0] * len(pool))).astype(float) < 0.45).mean()
            if len(pool)
            else 0.0
        )
        for alpha in alphas:
            for seed in seeds:
                rows.append(
                    {
                        "dataset": "CTC",
                        "generator": "ST-segmentation-linker",
                        "policy": "raw_topM_no_risk",
                        "certified_risk_level_alpha": alpha,
                        "seed": seed,
                        "candidate_budget_M": budget,
                        "released": int(len(pool)),
                        "actual_FTR_against_full_GT": false_rate,
                        "conservative_label_uncertainty_FTR": false_rate,
                        "official_supported": int((~unsupported).sum()) if len(pool) else 0,
                        "unsupported": int(unsupported.sum()) if len(pool) else 0,
                        "biological_large_displacement_proxy_rate": float(large_displacement),
                        "has_alpha_control": False,
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", default="outputs/ctc_link_certification/universe")
    parser.add_argument("--out-dir", default="outputs/ctc_link_certification/certification")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--alphas", default="0.05,0.10,0.20")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    parser.add_argument("--budgets", default="100,300,500")
    parser.add_argument(
        "--drop-heavy-run-artifacts",
        action="store_true",
        help="Remove per-run e-value and normalized-universe CSVs after the summary has been read.",
    )
    args = parser.parse_args()

    repo = Path(args.repo)
    sys.path.insert(0, str(repo / "code/parc_track"))
    os.environ.setdefault("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(Path.cwd()))
    from parc_track.phase2 import run_real_certify

    candidate_dir = Path(args.candidate_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    universe_path = candidate_dir / "candidate_universe.csv"
    audit_labels_path = candidate_dir / "audit_labels.csv"
    ann_path = candidate_dir / "ctc_link_pseudo_annotations.json"
    if not universe_path.exists():
        raise FileNotFoundError(universe_path)
    universe = pd.read_csv(universe_path)
    if universe.empty:
        raise RuntimeError("CTC link candidate universe is empty")

    alphas = [float(item) for item in args.alphas.split(",") if item.strip()]
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    budgets = [int(item) for item in args.budgets.split(",") if item.strip()]

    summary_frames: list[pd.DataFrame] = []
    run_rows: list[dict[str, object]] = []
    for alpha in alphas:
        for seed in seeds:
            run_dir = out_dir / f"alpha{safe_token(alpha)}_seed{seed}"
            config_path = run_dir / "config.yaml"
            cfg = {
                "dataset": {
                    "name": "CTC-link",
                    "root": str(candidate_dir),
                    "ann_file": str(ann_path),
                    "annotation_format": "ctc_link_pseudo",
                    "support_semantics": "ctc_stseg_links_supported_by_full_gt_tracking_truth",
                },
                "input": {
                    "candidate_universe": str(universe_path),
                    "candidate_nodes": str(candidate_dir / "candidate_nodes.csv"),
                    "audit_labels": str(audit_labels_path),
                },
                "output": {
                    "candidate_evalues": str(run_dir / "candidate_evalues.csv"),
                    "cell_effective_n": str(run_dir / "cell_effective_n.csv"),
                    "per_video_candidate_coverage": str(run_dir / "per_video_candidate_coverage.csv"),
                    "real_cert_summary": str(run_dir / "real_cert_summary.csv"),
                    "summary": str(run_dir / "summary.json"),
                    "normalized_candidate_universe": str(run_dir / "normalized_candidate_universe.csv"),
                },
                "risk": {"alpha1": alpha},
                "selector": {"candidate_budgets": budgets},
                "release_grid": {"times_sec": [2.0]},
                "calibration": {"empty_block_policy": "coverage_conditional"},
                "splits": {"strategy": "random", "seed": seed, "tune_ratio": 1 / 6, "cal_ratio": 1 / 2},
            }
            write_yaml(config_path, cfg)
            start = time.perf_counter()
            summary = run_real_certify(config_path)
            runtime = time.perf_counter() - start
            cert_csv = Path(summary["real_cert_summary_csv"])
            frame = pd.read_csv(cert_csv)
            frame["dataset"] = "CTC"
            frame["generator"] = "ST-segmentation-linker"
            frame["task"] = "cell_link_certification"
            frame["certified_risk_level_alpha"] = alpha
            frame["seed"] = seed
            frame["runtime_sec_total"] = runtime
            frame["actual_FTR_against_full_GT"] = frame["utr"]
            frame["conservative_label_uncertainty_FTR"] = frame[
                "conservative_ftr_uncertain_and_unlabeled_false"
            ]
            summary_frames.append(frame)
            run_rows.append(
                {
                    "alpha": alpha,
                    "seed": seed,
                    "config": str(config_path),
                    "summary": str(run_dir / "summary.json"),
                    "real_cert_summary": str(cert_csv),
                    "runtime_sec": runtime,
                }
            )
            if args.drop_heavy_run_artifacts:
                for heavy_path in [
                    run_dir / "candidate_evalues.csv",
                    run_dir / "normalized_candidate_universe.csv",
                    run_dir / "per_video_candidate_coverage.csv",
                ]:
                    if heavy_path.exists():
                        heavy_path.unlink()

    combined = pd.concat(summary_frames, ignore_index=True, sort=False) if summary_frames else pd.DataFrame()
    if not combined.empty:
        combined["safe_refusal_reason"] = combined.apply(
            lambda row: row.get("empty_diagnostic", "")
            if int(row.get("released", 0) or 0) == 0
            else "",
            axis=1,
        )
    combined_out = out_dir / "table_ctc_link_certification.csv"
    combined.to_csv(combined_out, index=False)
    pd.DataFrame(run_rows).to_csv(out_dir / "ctc_link_certification_runs.csv", index=False)
    raw = raw_topm_rows(universe, budgets=budgets, alphas=alphas, seeds=seeds)
    raw.to_csv(out_dir / "table_ctc_link_raw_topm.csv", index=False)

    parc = combined[combined["method"] == "parc_track_gamma_tuned_uniform_scs"].copy() if not combined.empty else combined
    summary_cols = [
        "certified_risk_level_alpha",
        "candidate_budget_M",
        "seeds",
        "nonempty_seeds",
        "released_mean",
        "released_std",
        "actual_FTR_mean",
        "actual_FTR_max",
        "raw_topM_actual_FTR",
        "mean_best_mass_ratio",
        "mean_max_observed_e",
        "dominant_empty_reason",
    ]
    summary_rows = []
    if parc is not None and not parc.empty:
        for (alpha, budget), group in parc.groupby(["certified_risk_level_alpha", "candidate_budget_M"]):
            raw_match = raw[
                (raw["certified_risk_level_alpha"].astype(float) == float(alpha))
                & (raw["candidate_budget_M"].astype(int) == int(budget))
            ]
            released = group["released"].astype(int)
            ftr = group["actual_FTR_against_full_GT"].fillna(0.0).astype(float)
            empty_reasons = group.loc[released == 0, "empty_diagnostic"].fillna("").astype(str)
            dominant = empty_reasons.value_counts().idxmax() if not empty_reasons.empty else ""
            summary_rows.append(
                {
                    "certified_risk_level_alpha": float(alpha),
                    "candidate_budget_M": int(budget),
                    "seeds": int(group["seed"].nunique()),
                    "nonempty_seeds": int((released > 0).sum()),
                    "released_mean": float(released.mean()),
                    "released_std": float(released.std(ddof=0)),
                    "actual_FTR_mean": float(ftr.mean()),
                    "actual_FTR_max": float(ftr.max()),
                    "raw_topM_actual_FTR": float(raw_match["actual_FTR_against_full_GT"].mean())
                    if not raw_match.empty
                    else None,
                    "mean_best_mass_ratio": float(
                        ((float(alpha) * group["best_margin_k"].astype(float) * group["best_margin_tau"].astype(float))
                         / int(budget)).mean()
                    )
                    if "best_margin_k" in group and "best_margin_tau" in group
                    else None,
                    "mean_max_observed_e": float(group["max_observed_e"].fillna(0.0).astype(float).mean()),
                    "dominant_empty_reason": dominant,
                }
            )
    pd.DataFrame(summary_rows, columns=summary_cols).to_csv(out_dir / "table_ctc_link_frontier_summary.csv", index=False)

    report = {
        "status": "completed",
        "task": "CTC link-level certification pilot",
        "candidate_universe": str(universe_path),
        "candidate_rows": int(len(universe)),
        "video_blocks": int(universe["video_id"].nunique()),
        "official_supported_candidate_rows": int((~bool_series(universe["is_unmatched"])).sum()),
        "unsupported_candidate_rows": int(bool_series(universe["is_unmatched"]).sum()),
        "alphas": alphas,
        "seeds": seeds,
        "candidate_budget_M_grid": budgets,
        "certification_table": str(combined_out),
        "raw_topm_table": str(out_dir / "table_ctc_link_raw_topm.csv"),
        "frontier_summary": str(out_dir / "table_ctc_link_frontier_summary.csv"),
        "run_manifest": str(out_dir / "ctc_link_certification_runs.csv"),
    }
    with (out_dir / "CTC_LINK_RUN_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
