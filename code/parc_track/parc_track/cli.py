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
            help="Output directory under /home/waas/paper_experiments.",
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
        default="/home/waas/paper_experiments/outputs/phase2/dataset_fetch_ovtb.json",
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
        help="Output root under /home/waas/paper_experiments; defaults to outputs/.",
    )
    tpami = report_subparsers.add_parser("tpami-core", help="Freeze TPAMI-core tables, LaTeX exports, and summary docs.")
    tpami.add_argument("--config", required=True, help="Path to Phase-3 paper export YAML config.")
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
    else:
        parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
