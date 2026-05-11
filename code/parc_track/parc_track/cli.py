from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters.datasets import fetch_ovtb_from_config, inspect_bdd100k_zip, inspect_dataset_from_config
from .phase2 import (
    export_release_audit_candidates,
    run_phase2_propose,
    run_real_certify,
    run_real_coverage_sweep,
    run_real_high_e_diagnostics,
    run_real_mini,
    sample_audit_candidates,
    summarize_audit,
)
from .phase3 import (
    export_matrix_release_audit_candidates,
    run_cross_generator_report,
    run_idsw_eval,
    run_ovtb_matrix,
    run_tpami_report,
    run_tuned_m_selection,
)
from .phase4 import (
    run_alpha_frontier,
    run_failure_manifest,
    run_confidence_calibration_baselines,
    run_ijcv_stability_bundle,
    run_mondrian_ablation,
    run_mot_metrics,
    run_ncalib_sensitivity,
    run_owlv2_top_audit_sample,
    run_per_class_breakdown,
    run_phase4_sprint,
    run_prop5_validation,
    run_runtime_report,
    run_score_ablation,
    run_second_rater_sample,
)
from .ovtrack_adapter import convert_ovtrack_predictions, inspect_ovtrack_public_outputs, write_ovtrack_matrix_config
from .phase5_trackeval import run_trackeval_grid, run_trackeval_motchallenge
from .phase6_metric_scope import run_metric_scope_report
from .phase7 import inspect_third_dataset, run_anytime_demo, run_burst_milestone, run_stability_v2
from .phase8 import (
    convert_published_tracker,
    export_published_tracker_release_audit,
    inspect_published_tracker_sources,
    run_published_tracker_matrix,
    run_published_tracker_report,
    scaffold_published_tracker_experiments,
)
from .phase9 import (
    run_audit_benchmark_industrialization,
    run_certification_api_package,
    run_ovvis_mask_scaffold,
    run_reliability_stress_suite,
    run_tpami_reliability_bundle,
    run_tpami_reliability_bundle_v2,
)
from .phase10 import (
    run_phase10_nonexchangeability_reruns,
    run_phase10_null_inflation_reruns,
    run_phase10_rerun_suite,
)
from .reports import build_phase1b_report
from .smoke import run_smoke
from .sweeps import run_sweep


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parc-track")
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke = subparsers.add_parser("smoke", help="Run synthetic PARC-Track smoke experiment.")
    smoke.add_argument("--config", required=True, help="Path to smoke YAML config.")

    sweep = subparsers.add_parser("sweep", help="Run synthetic PARC-Track stress sweeps.")
    sweep_subparsers = sweep.add_subparsers(dest="sweep_name", required=True)
    for name in (
        "calibration-size",
        "verified-positive",
        "score-overlap",
        "gamma-calibration",
        "selector-weighting",
    ):
        sub = sweep_subparsers.add_parser(name, help=f"Run {name} sweep.")
        sub.add_argument("--config", required=True, help="Path to base YAML config.")
        sub.add_argument(
            "--preset",
            choices=("quick", "paper"),
            default="quick",
            help="quick uses 5 seeds and fewer test videos; paper uses the configured test split and 50 seeds.",
        )
        sub.add_argument(
            "--output-dir",
            default=None,
            help="Output directory under ..",
        )

    catalog = subparsers.add_parser("catalog-bdd", help="Inspect a BDD100K zip archive.")
    catalog.add_argument("--zip", required=True, help="Path to BDD100K zip archive.")

    dataset = subparsers.add_parser("dataset", help="Fetch or inspect real tracking-layout datasets.")
    dataset_subparsers = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_fetch = dataset_subparsers.add_parser("fetch", help="Best-effort dataset download/setup.")
    fetch_subparsers = dataset_fetch.add_subparsers(dest="fetch_name", required=True)
    fetch_ovtb = fetch_subparsers.add_parser("ovtb", help="Prepare or report missing OVT-B files.")
    fetch_ovtb.add_argument("--config", required=True, help="Path to OVT-B inspect YAML config.")
    fetch_ovtb.add_argument(
        "--out",
        default="./outputs/phase2/dataset_fetch_ovtb.json",
        help="Path for the fetch/setup report.",
    )
    dataset_inspect = dataset_subparsers.add_parser("inspect", help="Validate tracking-layout contract.")
    dataset_inspect.add_argument("--config", required=True, help="Path to dataset inspect YAML config.")
    dataset_inspect.add_argument("--out", required=True, help="Path for dataset adapter report JSON.")

    audit = subparsers.add_parser("audit", help="Sample and summarize high-score unmatched audits.")
    audit_subparsers = audit.add_subparsers(dest="audit_command", required=True)
    audit_sample = audit_subparsers.add_parser("sample", help="Export high-score unmatched audit candidates.")
    audit_sample.add_argument("--config", required=True, help="Path to Phase-2 audit YAML config.")
    audit_sample.add_argument("--dataset", required=True, help="Dataset name to audit, e.g. OVT-B.")
    audit_sample.add_argument("--out", required=True, help="Path for audit candidate CSV.")
    audit_summarize = audit_subparsers.add_parser("summarize", help="Summarize manual audit labels.")
    audit_summarize.add_argument("--candidates", required=True, help="Audit candidate CSV.")
    audit_summarize.add_argument("--labels", required=True, help="Audit label CSV.")
    audit_summarize.add_argument("--out", required=True, help="Path for audit summary CSV.")

    real_mini = subparsers.add_parser("real-mini", help="Run the Phase-2 minimal real PARC scaffold.")
    real_mini.add_argument("--config", required=True, help="Path to Phase-2 real mini YAML config.")
    real_mini.add_argument("--out", required=True, help="Path for real mini summary JSON.")

    phase2 = subparsers.add_parser("phase2", help="Server-friendly Phase-2 proposal commands.")
    phase2_subparsers = phase2.add_subparsers(dest="phase2_command", required=True)
    phase2_propose = phase2_subparsers.add_parser("propose", help="Generate a real candidate universe from config.")
    phase2_propose.add_argument("--config", required=True, help="Path to Phase-2 proposal YAML config.")

    phase3 = subparsers.add_parser("phase3", help="Server-friendly Phase-3 matrix and audit commands.")
    phase3_subparsers = phase3.add_subparsers(dest="phase3_command", required=True)
    phase3_matrix = phase3_subparsers.add_parser("matrix", help="Run alpha/seed/M matrix from config.")
    phase3_matrix.add_argument("--config", required=True, help="Path to Phase-3 matrix YAML config.")
    phase3_release_audit = phase3_subparsers.add_parser(
        "export-release-audit",
        help="Export matrix released unsupported paths for audit.",
    )
    phase3_release_audit.add_argument("--config", required=True, help="Path to Phase-3 matrix YAML config.")
    phase3_release_audit.add_argument("--out", default=None, help="Combined release-audit CSV path.")
    phase3_release_audit.add_argument("--labels-out", default=None, help="Label-template CSV path.")
    phase3_release_audit.add_argument(
        "--unsupported-only",
        action="store_true",
        help="Export only released paths unsupported by official GT and verified positives.",
    )
    phase3_cross = phase3_subparsers.add_parser(
        "cross-generator-report",
        help="Build GroundingDINO/OWLv2 cross-generator table from matrix CSVs.",
    )
    phase3_cross.add_argument("--config", required=True, help="Path to cross-generator report YAML config.")

    real = subparsers.add_parser("real", help="Run real-data PARC scaffolds.")
    real_subparsers = real.add_subparsers(dest="real_command", required=True)
    real_certify = real_subparsers.add_parser("certify", help="Run full-universe Phase-2d certification scaffold.")
    real_certify.add_argument("--config", required=True, help="Path to Phase-2 real certification YAML config.")
    real_certify.add_argument(
        "--out",
        default=None,
        help="Optional JSON summary path; defaults to the config output.summary path.",
    )
    real_coverage = real_subparsers.add_parser("coverage-sweep", help="Run Phase-2e calibration coverage feasibility sweep.")
    real_coverage.add_argument("--config", required=True, help="Path to Phase-2 real certification YAML config.")
    real_coverage.add_argument(
        "--out",
        default=None,
        help="Coverage sweep CSV path; defaults to the config output.coverage_sweep path.",
    )
    real_high_e = real_subparsers.add_parser("high-e-diagnostics", help="Run Phase-2g high-evidence mass diagnostics.")
    real_high_e.add_argument("--config", required=True, help="Path to Phase-2 real certification YAML config.")
    real_release_audit = real_subparsers.add_parser(
        "export-release-audit",
        help="Export released real-data candidates for one-sided audit review.",
    )
    real_release_audit.add_argument("--config", required=True, help="Path to Phase-2 real certification YAML config.")
    real_release_audit.add_argument(
        "--method",
        default=None,
        help="Method name to export; defaults to parc_track_gamma_tuned_uniform_scs when available.",
    )
    real_release_audit.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Candidate budget M to export; defaults to the released row with the largest release count.",
    )
    real_release_audit.add_argument("--out", default=None, help="Release audit candidate CSV path.")
    real_release_audit.add_argument("--labels-out", default=None, help="Release audit label template CSV path.")
    real_release_audit.add_argument("--viewer", default=None, help="Release audit viewer directory.")
    real_release_audit.add_argument(
        "--unsupported-only",
        action="store_true",
        help="Export only released candidates that are unmatched to official GT and not verified positives.",
    )
    real_ovtb_matrix = real_subparsers.add_parser(
        "ovtb-matrix",
        help="Run the Phase-3 OVT-B alpha/seed/M matrix with expanded diagnostic baselines.",
    )
    real_ovtb_matrix.add_argument("--config", required=True, help="Path to Phase-3 OVT-B matrix YAML config.")
    real_tune_m = real_subparsers.add_parser("tune-m", help="Select candidate budget M using tune split only.")
    real_tune_m.add_argument("--config", required=True, help="Path to Phase-3 OVT-B matrix YAML config.")
    real_tune_m.add_argument("--out", default=None, help="Optional tuned_m_selection.csv output path.")
    real_idsw = real_subparsers.add_parser("idsw-eval", help="Evaluate CLEAR-MOT IDSW events and bound tightness.")
    real_idsw.add_argument("--config", required=True, help="Path to Phase-3 IDSW evaluator YAML config.")

    report = subparsers.add_parser("report", help="Build paper-facing reports and figures.")
    report_subparsers = report.add_subparsers(dest="report_name", required=True)
    phase1b = report_subparsers.add_parser("phase1b", help="Build Phase-1b summary figures and tables.")
    phase1b.add_argument("--config", required=True, help="Path to base YAML config.")
    phase1b.add_argument(
        "--output-root",
        default=None,
        help="Output root under .; defaults to outputs/.",
    )
    tpami = report_subparsers.add_parser("tpami-core", help="Freeze TPAMI-core tables, LaTeX exports, and summary docs.")
    tpami.add_argument("--config", required=True, help="Path to Phase-3 paper export YAML config.")

    phase4 = subparsers.add_parser("phase4", help="Run IJCV sprint experiments and diagnostics.")
    phase4_subparsers = phase4.add_subparsers(dest="phase4_command", required=True)
    for name in (
        "sprint",
        "prop5",
        "score-ablation",
        "owlv2-top-audit",
        "alpha-frontier",
        "ncalib-sensitivity",
        "runtime",
        "per-class",
        "second-rater",
        "failure-cases",
        "confidence-calibration",
        "mondrian-ablation",
        "ijcv-stability",
        "motmetrics",
    ):
        sub = phase4_subparsers.add_parser(name, help=f"Run Phase-4 {name}.")
        sub.add_argument("--output-dir", default=None, help="Output directory under ..")

    trackeval_cmd = subparsers.add_parser("trackeval", help="Export MOTChallenge format and run TrackEval.")
    trackeval_subparsers = trackeval_cmd.add_subparsers(dest="trackeval_command", required=True)
    trackeval_one = trackeval_subparsers.add_parser("run", help="Run one TrackEval MOTChallenge export/eval.")
    trackeval_one.add_argument("--dataset", default="OVT-B", choices=("OVT-B", "TAO"))
    trackeval_one.add_argument("--generator", default="GroundingDINO")
    trackeval_one.add_argument("--alpha", type=float, default=0.10)
    trackeval_one.add_argument("--seed", type=int, default=0)
    trackeval_one.add_argument("--budget", type=int, default=150)
    trackeval_one.add_argument("--scope", choices=("standard", "supported", "release_size"), default="standard")
    trackeval_one.add_argument("--output-dir", default=None)
    trackeval_grid = trackeval_subparsers.add_parser("grid", help="Run the OVT-B TrackEval grid.")
    trackeval_grid.add_argument("--dataset", default="OVT-B", choices=("OVT-B", "TAO"))
    trackeval_grid.add_argument("--scope", choices=("standard", "supported", "release_size"), default="standard")
    trackeval_grid.add_argument("--output-dir", default=None)
    phase6 = subparsers.add_parser("phase6", help="Run IJCV metric-scope and controllability reports.")
    phase6_subparsers = phase6.add_subparsers(dest="phase6_command", required=True)
    phase6_metric = phase6_subparsers.add_parser("metric-scope", help="Run Phase-6 metric-scope report bundle.")
    phase6_metric.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase7 = subparsers.add_parser("phase7", help="Run Phase-7 stability and third-dataset diagnostics.")
    phase7_subparsers = phase7.add_subparsers(dest="phase7_command", required=True)
    phase7_anytime = phase7_subparsers.add_parser("anytime", help="Run OVT-B anytime-valid release diagnostic.")
    phase7_anytime.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase7_third = phase7_subparsers.add_parser("third-dataset", help="Inspect third dataset readiness.")
    third_subparsers = phase7_third.add_subparsers(dest="third_dataset_command", required=True)
    third_inspect = third_subparsers.add_parser("inspect", help="Inspect BURST/LV-VIS third dataset layout.")
    third_inspect.add_argument("--dataset", default="BURST", choices=("BURST", "LV-VIS", "LVVIS"))
    third_inspect.add_argument("--root", default=None, help="Optional dataset root override.")
    third_inspect.add_argument("--ann-file", default=None, help="Optional annotation JSON override.")
    third_inspect.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase7_stability = phase7_subparsers.add_parser("stability-v2", help="Freeze IJCV stability v2 bundle.")
    phase7_stability.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase7_burst = phase7_subparsers.add_parser("burst-freeze", help="Freeze BURST v1 scaffold outputs.")
    phase7_burst.add_argument("--output-dir", default=None, help="Milestone output directory under ..")
    phase7_burst.add_argument("--source-dir", default=None, help="BURST phase output directory.")
    phase7_burst.add_argument("--third-dataset-dir", default=None, help="Third-dataset adapter output directory.")
    phase7_ovtrack_probe = phase7_subparsers.add_parser(
        "ovtrack-public-report",
        help="Check local OVTrack/OVT-B/TETA repos for public prediction files.",
    )
    phase7_ovtrack_probe.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase7_ovtrack_convert = phase7_subparsers.add_parser(
        "ovtrack-convert",
        help="Convert TAO/TETA COCO-VID OVTrack predictions to PARC candidate schema.",
    )
    phase7_ovtrack_convert.add_argument("--pred", required=True, help="OVTrack prediction JSON.")
    phase7_ovtrack_convert.add_argument(
        "--ann",
        default="./data/OVT-B/ovtb_ann.json",
        help="OVT-B/TAO-format annotation JSON.",
    )
    phase7_ovtrack_convert.add_argument(
        "--out-dir",
        default="./outputs/phase7_ovtrack_ovtb",
        help="Output directory for candidate_universe/scores/nodes.",
    )
    phase7_ovtrack_convert.add_argument("--dataset", default="OVT-B", help="Dataset name to write into candidate_universe.")
    phase7_ovtrack_convert.add_argument(
        "--dataset-root",
        default="./data/OVT-B",
        help="Dataset root used to resolve relative frame paths.",
    )
    phase7_ovtrack_convert.add_argument("--frame-subdir", default="OVT-B", help="Frame subdirectory below dataset root.")
    phase7_ovtrack_convert.add_argument(
        "--config-out",
        default="./configs/phase7_ovtrack_ovtb_matrix.yaml",
        help="Matrix config path to write after conversion.",
    )

    phase8 = subparsers.add_parser("phase8", help="Run published OVMOT tracker certification experiments.")
    phase8_subparsers = phase8.add_subparsers(dest="phase8_command", required=True)
    phase8_pub = phase8_subparsers.add_parser("published-trackers", help="Inspect, convert, certify, and report published trackers.")
    pub_subparsers = phase8_pub.add_subparsers(dest="published_tracker_command", required=True)
    pub_inspect = pub_subparsers.add_parser("inspect", help="Inspect local tracker repos and prediction availability.")
    pub_inspect.add_argument("--output-dir", default=None, help="Output root under ..")
    pub_scaffold = pub_subparsers.add_parser("scaffold", help="Create all tracker/dataset run manifests and matrix configs.")
    pub_scaffold.add_argument("--output-dir", default=None, help="Output root under ..")
    pub_convert = pub_subparsers.add_parser("convert", help="Convert one tracker prediction file to PARC candidate schema.")
    pub_convert.add_argument("--tracker", required=True, choices=("ovtrack", "ovtb_baseline", "ovtr"))
    pub_convert.add_argument("--dataset", required=True, choices=("ovtb", "tao"))
    pub_convert.add_argument("--pred", required=True, help="Official prediction JSON/PKL.")
    pub_convert.add_argument("--out-dir", default=None, help="Pair output directory.")
    pub_convert.add_argument("--ann", default=None, help="Dataset annotation override.")
    pub_convert.add_argument("--dataset-root", default=None, help="Dataset root override.")
    pub_convert.add_argument("--frame-subdir", default=None, help="Frame subdir override.")
    pub_convert.add_argument("--config-out", default=None, help="Matrix config path to write.")
    pub_matrix = pub_subparsers.add_parser("matrix", help="Run M-effective-aware PARC wrapper matrix for converted tracker candidates.")
    pub_matrix.add_argument("--config", required=True, help="Published tracker matrix YAML.")
    pub_audit = pub_subparsers.add_parser("export-release-audit", help="Export deduplicated released-unsupported paths for audit.")
    pub_audit.add_argument("--config", required=True, help="Published tracker matrix YAML.")
    pub_audit.add_argument("--out", default=None, help="Release audit CSV.")
    pub_audit.add_argument("--labels-out", default=None, help="Label template CSV.")
    pub_audit.add_argument("--unsupported-only", action="store_true", help="Only export unsupported released paths.")
    pub_report = pub_subparsers.add_parser("report", help="Aggregate completed published tracker matrices.")
    pub_report.add_argument("--output-dir", default=None, help="Output root under ..")

    phase9 = subparsers.add_parser("phase9", help="Run TPAMI-scale reliability fortress artifacts.")
    phase9_subparsers = phase9.add_subparsers(dest="phase9_command", required=True)
    phase9_audit = phase9_subparsers.add_parser("audit-benchmark", help="Build 2000-row audit benchmark scaffold.")
    phase9_audit.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase9_audit.add_argument("--total", type=int, default=2000, help="Total audit rows to target.")
    phase9_audit.add_argument("--second-rater-total", type=int, default=300, help="Blind second-rater template size.")
    phase9_stress = phase9_subparsers.add_parser("stress", help="Build reliability stress-test design/projection tables.")
    phase9_stress.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase9_ovvis = phase9_subparsers.add_parser("ovvis-scaffold", help="Build OVVIS box-to-mask scaffold.")
    phase9_ovvis.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase9_ovvis.add_argument("--limit", type=int, default=500, help="Maximum mask paths in scaffold.")
    phase9_api = phase9_subparsers.add_parser("certification-api", help="Build public PARC API fixture and docs.")
    phase9_api.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase9_bundle = phase9_subparsers.add_parser("reliability-bundle", help="Freeze TPAMI reliability fortress bundle.")
    phase9_bundle.add_argument("--output-dir", default=None, help="Milestone output directory under ..")
    phase9_bundle_v2 = phase9_subparsers.add_parser("reliability-bundle-v2", help="Freeze TPAMI reliability fortress v2 bundle.")
    phase9_bundle_v2.add_argument("--output-dir", default=None, help="Milestone output directory under ..")
    phase10 = subparsers.add_parser("phase10", help="Run actual reruns for TPAMI reliability fortress.")
    phase10_subparsers = phase10.add_subparsers(dest="phase10_command", required=True)
    phase10_nonex = phase10_subparsers.add_parser("nonexchangeability", help="Run severe custom-split non-exchangeability reruns.")
    phase10_nonex.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase10_null = phase10_subparsers.add_parser("null-inflation", help="Run verified-positive removal-ratio reruns.")
    phase10_null.add_argument("--output-dir", default=None, help="Output directory under ..")
    phase10_suite = phase10_subparsers.add_parser("suite", help="Run both Phase-10 actual rerun suites.")
    phase10_suite.add_argument("--output-dir", default=None, help="Output directory under ..")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "smoke":
        summary = run_smoke(Path(args.config))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "sweep":
        summary = run_sweep(
            args.sweep_name,
            Path(args.config),
            preset=args.preset,
            output_dir=args.output_dir,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "catalog-bdd":
        entry = inspect_bdd100k_zip(args.zip)
        print(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False))
    elif args.command == "dataset":
        if args.dataset_command == "fetch":
            if args.fetch_name == "ovtb":
                summary = fetch_ovtb_from_config(Path(args.config), out_path=args.out)
                print(json.dumps(summary, indent=2, ensure_ascii=False))
            else:
                parser.error(f"unknown dataset fetch target: {args.fetch_name}")
        elif args.dataset_command == "inspect":
            summary = inspect_dataset_from_config(Path(args.config), out_path=args.out)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            parser.error(f"unknown dataset command: {args.dataset_command}")
    elif args.command == "audit":
        if args.audit_command == "sample":
            summary = sample_audit_candidates(Path(args.config), args.dataset, args.out)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.audit_command == "summarize":
            summary = summarize_audit(args.candidates, args.labels, args.out)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            parser.error(f"unknown audit command: {args.audit_command}")
    elif args.command == "real-mini":
        summary = run_real_mini(Path(args.config), args.out)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "phase2":
        if args.phase2_command == "propose":
            summary = run_phase2_propose(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            parser.error(f"unknown phase2 command: {args.phase2_command}")
    elif args.command == "phase3":
        if args.phase3_command == "matrix":
            summary = run_ovtb_matrix(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.phase3_command == "export-release-audit":
            summary = export_matrix_release_audit_candidates(
                Path(args.config),
                unsupported_only=args.unsupported_only,
                out_csv=args.out,
                labels_out=args.labels_out,
            )
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.phase3_command == "cross-generator-report":
            summary = run_cross_generator_report(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            parser.error(f"unknown phase3 command: {args.phase3_command}")
    elif args.command == "real":
        if args.real_command == "certify":
            summary = run_real_certify(Path(args.config), args.out)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.real_command == "coverage-sweep":
            summary = run_real_coverage_sweep(Path(args.config), args.out)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.real_command == "high-e-diagnostics":
            summary = run_real_high_e_diagnostics(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.real_command == "export-release-audit":
            summary = export_release_audit_candidates(
                Path(args.config),
                method=args.method,
                budget=args.budget,
                out_csv=args.out,
                labels_out=args.labels_out,
                viewer_path=args.viewer,
                unsupported_only=args.unsupported_only,
            )
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.real_command == "ovtb-matrix":
            summary = run_ovtb_matrix(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.real_command == "tune-m":
            summary = run_tuned_m_selection(Path(args.config), args.out)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.real_command == "idsw-eval":
            summary = run_idsw_eval(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            parser.error(f"unknown real command: {args.real_command}")
    elif args.command == "report":
        if args.report_name == "phase1b":
            summary = build_phase1b_report(Path(args.config), output_root=args.output_root)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.report_name == "tpami-core":
            summary = run_tpami_report(Path(args.config))
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            parser.error(f"unknown report: {args.report_name}")
    elif args.command == "phase4":
        if args.phase4_command == "sprint":
            summary = run_phase4_sprint(args.output_dir)
        elif args.phase4_command == "prop5":
            summary = run_prop5_validation(args.output_dir)
        elif args.phase4_command == "score-ablation":
            summary = run_score_ablation(args.output_dir)
        elif args.phase4_command == "owlv2-top-audit":
            summary = run_owlv2_top_audit_sample(args.output_dir)
        elif args.phase4_command == "alpha-frontier":
            summary = run_alpha_frontier(args.output_dir)
        elif args.phase4_command == "ncalib-sensitivity":
            summary = run_ncalib_sensitivity(args.output_dir)
        elif args.phase4_command == "runtime":
            summary = run_runtime_report(args.output_dir)
        elif args.phase4_command == "per-class":
            summary = run_per_class_breakdown(args.output_dir)
        elif args.phase4_command == "second-rater":
            summary = run_second_rater_sample(args.output_dir)
        elif args.phase4_command == "failure-cases":
            summary = run_failure_manifest(args.output_dir)
        elif args.phase4_command == "confidence-calibration":
            summary = run_confidence_calibration_baselines(args.output_dir)
        elif args.phase4_command == "mondrian-ablation":
            summary = run_mondrian_ablation(args.output_dir)
        elif args.phase4_command == "ijcv-stability":
            summary = run_ijcv_stability_bundle(args.output_dir)
        elif args.phase4_command == "motmetrics":
            summary = run_mot_metrics(args.output_dir)
        else:
            parser.error(f"unknown phase4 command: {args.phase4_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "trackeval":
        if args.trackeval_command == "run":
            summary = run_trackeval_motchallenge(
                dataset=args.dataset,
                generator=args.generator,
                alpha=args.alpha,
                seed=args.seed,
                budget=args.budget,
                out_dir=args.output_dir,
                scope=args.scope,
            )
        elif args.trackeval_command == "grid":
            summary = run_trackeval_grid(args.output_dir, dataset=args.dataset, scope=args.scope)
        else:
            parser.error(f"unknown trackeval command: {args.trackeval_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "phase6":
        if args.phase6_command == "metric-scope":
            summary = run_metric_scope_report(args.output_dir)
        else:
            parser.error(f"unknown phase6 command: {args.phase6_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "phase7":
        if args.phase7_command == "anytime":
            summary = run_anytime_demo(args.output_dir)
        elif args.phase7_command == "third-dataset":
            if args.third_dataset_command == "inspect":
                summary = inspect_third_dataset(
                    dataset=args.dataset,
                    out_dir=args.output_dir,
                    root=args.root,
                    ann_file=args.ann_file,
                )
            else:
                parser.error(f"unknown phase7 third-dataset command: {args.third_dataset_command}")
        elif args.phase7_command == "stability-v2":
            summary = run_stability_v2(args.output_dir)
        elif args.phase7_command == "burst-freeze":
            summary = run_burst_milestone(
                output_dir=args.output_dir,
                source_dir=args.source_dir,
                third_dataset_dir=args.third_dataset_dir,
            )
        elif args.phase7_command == "ovtrack-public-report":
            summary = inspect_ovtrack_public_outputs(args.output_dir)
        elif args.phase7_command == "ovtrack-convert":
            summary = convert_ovtrack_predictions(
                pred_path=args.pred,
                ann_file=args.ann,
                out_dir=args.out_dir,
                dataset_name=args.dataset,
                dataset_root=args.dataset_root,
                frame_subdir=args.frame_subdir,
            )
            config_summary = write_ovtrack_matrix_config(args.out_dir, args.config_out, ann_file=args.ann)
            summary["matrix_config"] = config_summary["config"]
        else:
            parser.error(f"unknown phase7 command: {args.phase7_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "phase8":
        if args.phase8_command == "published-trackers":
            if args.published_tracker_command == "inspect":
                summary = inspect_published_tracker_sources(args.output_dir)
            elif args.published_tracker_command == "scaffold":
                summary = scaffold_published_tracker_experiments(args.output_dir)
            elif args.published_tracker_command == "convert":
                summary = convert_published_tracker(
                    tracker=args.tracker,
                    dataset=args.dataset,
                    pred_path=args.pred,
                    out_dir=args.out_dir,
                    ann_file=args.ann,
                    dataset_root=args.dataset_root,
                    frame_subdir=args.frame_subdir,
                    config_out=args.config_out,
                )
            elif args.published_tracker_command == "matrix":
                summary = run_published_tracker_matrix(Path(args.config))
            elif args.published_tracker_command == "export-release-audit":
                summary = export_published_tracker_release_audit(
                    Path(args.config),
                    out_csv=args.out,
                    labels_out=args.labels_out,
                    unsupported_only=args.unsupported_only,
                )
            elif args.published_tracker_command == "report":
                summary = run_published_tracker_report(args.output_dir)
            else:
                parser.error(f"unknown phase8 published-trackers command: {args.published_tracker_command}")
        else:
            parser.error(f"unknown phase8 command: {args.phase8_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "phase9":
        if args.phase9_command == "audit-benchmark":
            summary = run_audit_benchmark_industrialization(
                args.output_dir,
                total=args.total,
                second_rater_total=args.second_rater_total,
            )
        elif args.phase9_command == "stress":
            summary = run_reliability_stress_suite(args.output_dir)
        elif args.phase9_command == "ovvis-scaffold":
            summary = run_ovvis_mask_scaffold(args.output_dir, limit=args.limit)
        elif args.phase9_command == "certification-api":
            summary = run_certification_api_package(args.output_dir)
        elif args.phase9_command == "reliability-bundle":
            summary = run_tpami_reliability_bundle(args.output_dir)
        elif args.phase9_command == "reliability-bundle-v2":
            summary = run_tpami_reliability_bundle_v2(args.output_dir)
        else:
            parser.error(f"unknown phase9 command: {args.phase9_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.command == "phase10":
        if args.phase10_command == "nonexchangeability":
            summary = run_phase10_nonexchangeability_reruns(args.output_dir)
        elif args.phase10_command == "null-inflation":
            summary = run_phase10_null_inflation_reruns(args.output_dir)
        elif args.phase10_command == "suite":
            summary = run_phase10_rerun_suite(args.output_dir)
        else:
            parser.error(f"unknown phase10 command: {args.phase10_command}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
