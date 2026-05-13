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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repo", default="/home/waas/paper_experiments/github/Certified-Open-Vocabulary-MOT")
    parser.add_argument("--image-root", default="/home/waas/paper_experiments/data/iWildCam2022/subset_images/train")
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--budget", type=int, default=150)
    parser.add_argument("--audit-samples", type=int, default=500)
    args = parser.parse_args()

    repo = Path(args.repo)
    sys.path.insert(0, str(repo / "code/parc_track"))
    os.environ.setdefault("PARC_TRACK_EXTRA_OUTPUT_ROOTS", "/home/waas/paper_experiments")
    from parc_track.phase2 import run_real_certify

    candidate_dir = Path(args.candidate_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    universe_path = candidate_dir / "candidate_universe.csv"
    audit_labels_path = candidate_dir / "audit_labels.csv"
    ann_path = candidate_dir / "iwildcam_pseudo_tracking_annotations.json"
    if not universe_path.exists():
        raise FileNotFoundError(universe_path)
    universe = pd.read_csv(universe_path)
    if universe.empty:
        raise RuntimeError("candidate universe is empty")

    alphas = [float(item) for item in args.alphas.split(",") if item.strip()]
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    support_semantics = "image_level_animal_presence_support"
    summary_frames = []
    run_rows = []
    for alpha in alphas:
        for seed in seeds:
            run_dir = out_dir / f"alpha{safe_token(alpha)}_seed{seed}"
            config_path = run_dir / "config.yaml"
            cfg = {
                "dataset": {
                    "name": "iWildCam2022",
                    "root": str(Path(args.image_root)),
                    "ann_file": str(ann_path),
                    "annotation_format": "coco_video",
                    "support_semantics": support_semantics,
                },
                "input": {
                    "candidate_universe": str(universe_path),
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
                "selector": {"candidate_budget_M": int(args.budget)},
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
            frame["dataset"] = "iWildCam2022"
            frame["generator"] = "GroundingDINO-SwinT-animal"
            frame["target"] = "animal_present"
            frame["support_semantics"] = support_semantics
            frame["certified_risk_level_alpha"] = alpha
            frame["seed"] = seed
            frame["candidate_budget_M_main"] = int(args.budget)
            frame["runtime_sec_total"] = runtime
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

    combined = pd.concat(summary_frames, ignore_index=True, sort=False) if summary_frames else pd.DataFrame()
    combined_out = out_dir / "table_iwildcam_animal_certification.csv"
    combined.to_csv(combined_out, index=False)
    pd.DataFrame(run_rows).to_csv(out_dir / "iwildcam_animal_certification_runs.csv", index=False)

    raw_rows = []
    for seed in seeds:
        for alpha in alphas:
            pool = universe.sort_values("score", ascending=False).head(int(args.budget)).copy()
            unsupported = pool["is_unmatched"].astype(str).str.lower().isin(["true", "1", "yes"])
            raw_rows.append(
                {
                    "dataset": "iWildCam2022",
                    "generator": "GroundingDINO-SwinT-animal",
                    "target": "animal_present",
                    "policy": "raw_topM_no_risk",
                    "certified_risk_level_alpha": alpha,
                    "seed": seed,
                    "candidate_budget_M": int(args.budget),
                    "released": int(len(pool)),
                    "official_supported": int((~unsupported).sum()),
                    "unsupported": int(unsupported.sum()),
                    "UTR": float(unsupported.mean()) if len(pool) else 0.0,
                    "empirical_audited_FTR": "",
                    "conservative_label_uncertainty_FTR": float(unsupported.mean()) if len(pool) else 0.0,
                    "has_alpha_control": False,
                    "support_semantics": support_semantics,
                }
            )
    pd.DataFrame(raw_rows).to_csv(out_dir / "table_iwildcam_animal_raw_topm_proxy.csv", index=False)

    unmatched = universe[universe["is_unmatched"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
    unmatched = unmatched.sort_values("score", ascending=False)
    audit = unmatched.head(int(args.audit_samples)).copy()
    audit_cols = [
        "dataset",
        "video_id",
        "path_id",
        "query",
        "category_id",
        "score",
        "objectness",
        "semantic_margin",
        "temporal_stability",
        "association_score",
        "matched_gt_id",
        "matched_iou",
        "temporal_overlap",
        "is_unmatched",
        "cell_id",
        "novelty_bin",
        "query_cluster",
        "occ_bin",
        "domain_bin",
        "frame_start",
        "frame_end",
        "location_id",
        "support_semantics",
    ]
    audit_candidates = audit[[col for col in audit_cols if col in audit.columns]].copy()
    audit_candidates.to_csv(out_dir / "audit_candidates_iwildcam_animal.csv", index=False)
    labels = audit_candidates[["dataset", "video_id", "path_id"]].copy()
    labels["label"] = ""
    labels["reason"] = ""
    labels["auditor"] = ""
    labels["confidence"] = ""
    labels["review_status"] = ""
    labels["verified_positive_for_calibration"] = "no"
    labels.to_csv(out_dir / "audit_labels_iwildcam_animal_template.csv", index=False)

    report = {
        "status": "completed",
        "dataset": "iWildCam2022",
        "target": "animal_present",
        "support_semantics": support_semantics,
        "candidate_universe": str(universe_path),
        "candidate_rows": int(len(universe)),
        "official_supported_candidate_rows": int((~universe["is_unmatched"].astype(str).str.lower().isin(["true", "1", "yes"])).sum()),
        "unsupported_candidate_rows": int(universe["is_unmatched"].astype(str).str.lower().isin(["true", "1", "yes"]).sum()),
        "alphas": alphas,
        "seeds": seeds,
        "candidate_budget_M": int(args.budget),
        "certification_table": str(combined_out),
        "raw_topm_table": str(out_dir / "table_iwildcam_animal_raw_topm_proxy.csv"),
        "audit_candidates": str(out_dir / "audit_candidates_iwildcam_animal.csv"),
        "audit_template": str(out_dir / "audit_labels_iwildcam_animal_template.csv"),
        "audit_candidate_rows": int(len(audit_candidates)),
    }
    with (out_dir / "RUN_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
