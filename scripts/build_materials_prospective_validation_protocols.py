#!/usr/bin/env python3
"""Build A1/A2 materials prospective-validation protocol and feasibility cards.

This milestone does not run new DFT and does not claim a new prospective
materials result. It freezes the protocol requirements and records what is
already feasible from the public-safe WBM/Matbench artifacts in this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WBM = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
DEFAULT_ALIGNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
DEFAULT_CGCNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
DEFAULT_MEGNET = Path("/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_optional(path: Path) -> str:
    return sha256_file(path) if path.exists() else "missing"


def date_from_name(path_or_url: str) -> str:
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", path_or_url)
    return match.group(1) if match else ""


def inspect_wbm_columns(path: Path) -> dict:
    if not path.exists():
        return {
            "local_file_available": False,
            "n_columns": 0,
            "has_material_id": False,
            "has_formula": False,
            "has_stability_label": False,
            "has_label_release_date": False,
            "has_calculation_timestamp": False,
            "date_like_columns": "",
        }
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    date_like = [col for col in columns if any(token in col.lower() for token in ["date", "time", "created", "updated", "version"])]
    return {
        "local_file_available": True,
        "n_columns": len(columns),
        "has_material_id": "material_id" in columns,
        "has_formula": "formula" in columns,
        "has_stability_label": "e_above_hull_mp2020_corrected_ppd_mp" in columns,
        "has_label_release_date": bool(date_like),
        "has_calculation_timestamp": bool(date_like),
        "date_like_columns": ";".join(date_like),
    }


def build_temporal_protocol(args: argparse.Namespace, wbm_info: dict) -> pd.DataFrame:
    model_dates = {
        "ALIGNN-FF": date_from_name(str(args.alignn_predictions)),
        "CGCNN": date_from_name(str(args.cgcnn_predictions)),
        "MEGNet": date_from_name(str(args.megnet_predictions)),
    }
    return pd.DataFrame(
        [
            {
                "protocol_id": "A1_temporal_quasi_prospective_materials_split",
                "candidate_universe": "WBM / Matbench Discovery unique prototypes",
                "freeze_rule": "select t0 before revealing future DFT labels",
                "allowed_calibration_labels": "DFT-stable positives public at or before t0",
                "forbidden_information": "future DFT labels cannot affect scores, gamma, K, blocks, source choice, or release rule",
                "models": "ALIGNN-FF;CGCNN;MEGNet",
                "model_prediction_dates_in_filenames": json.dumps(model_dates, sort_keys=True),
                "primary_alpha": 0.10,
                "primary_K": "300 or 500 for ALIGNN-FF; 100 for CGCNN",
                "primary_endpoint": "PARC FTR on post-t0 follow-up labels",
                "consequence_endpoint": "unstable follow-ups prevented relative to raw top-K",
                "local_timestamp_columns_available": bool(wbm_info["has_label_release_date"]),
                "feasibility_status": (
                    "ready_if_external_label_timestamp_or_release_snapshot_is_supplied"
                    if not wbm_info["has_label_release_date"]
                    else "locally_executable_with_timestamp_columns"
                ),
                "evidence_status": "protocol_feasibility_not_completed_evidence",
            }
        ]
    )


def build_temporal_feasibility(args: argparse.Namespace, wbm_info: dict) -> pd.DataFrame:
    rows = [
        {
            "check_name": "local_wbm_summary_available",
            "observed": wbm_info["local_file_available"],
            "required_for_A1": True,
            "interpretation": "candidate table and DFT label columns are locally available" if wbm_info["local_file_available"] else "missing local WBM summary",
        },
        {
            "check_name": "stable_label_available",
            "observed": wbm_info["has_stability_label"],
            "required_for_A1": True,
            "interpretation": "e_above_hull label exists for held-out evaluation",
        },
        {
            "check_name": "label_release_timestamp_available",
            "observed": wbm_info["has_label_release_date"],
            "required_for_A1": True,
            "interpretation": (
                "temporal split can be executed locally"
                if wbm_info["has_label_release_date"]
                else "local WBM summary has no timestamp/release-date column; A1 needs an external snapshot or timestamp table"
            ),
        },
        {
            "check_name": "model_prediction_files_available",
            "observed": all(Path(p).exists() for p in [args.alignn_predictions, args.cgcnn_predictions, args.megnet_predictions]),
            "required_for_A1": True,
            "interpretation": "local model prediction files are available for frozen queue replay",
        },
        {
            "check_name": "pre_existing_quasi_prospective_replay_available",
            "observed": (ROOT / "outputs/milestones/materials_computational_followup_trial/table_materials_computational_trial_summary.csv").exists(),
            "required_for_A1": False,
            "interpretation": "Phase21 public-label replay exists but is not a timestamped temporal split",
        },
    ]
    return pd.DataFrame(rows)


def build_independent_dft_protocol() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protocol_id": "A2_independent_public_DFT_source_cross_validation",
                "candidate_universe": "WBM / Matbench Discovery candidates with material_id/formula/prototype keys",
                "calibration_source": "WBM / Matbench public DFT stable positives",
                "evaluation_source": "independent public DFT database labels joined after release decision",
                "candidate_join_keys": "material_id if shared; otherwise reduced_formula + structure/prototype hash when available",
                "primary_endpoint": "PARC release FTR under independent-source stable/unstable label",
                "consequence_endpoint": "unstable follow-ups prevented under independent label source",
                "leakage_rule": "independent labels cannot affect scores, source choice, blocks, K, gamma, or release rule",
                "primary_alpha": 0.10,
                "evidence_status": "protocol_feasibility_not_completed_evidence",
            }
        ]
    )


def build_independent_source_feasibility() -> pd.DataFrame:
    rows = [
        {
            "source": "Materials Project",
            "label_type": "computed stability / energy above hull",
            "candidate_join_requirement": "MP material_id mapping or structure/prototype matching",
            "local_label_file_available": False,
            "expected_strength": "high provenance, strong community familiarity",
            "main_risk": "overlap/systematic dependence with WBM hull reference must be disclosed",
            "feasibility_status": "external_mapping_required",
        },
        {
            "source": "OQMD",
            "label_type": "computed stability / formation energy",
            "candidate_join_requirement": "formula plus structure/prototype matching",
            "local_label_file_available": False,
            "expected_strength": "independent public DFT source",
            "main_risk": "schema alignment and duplicate structure resolution",
            "feasibility_status": "external_mapping_required",
        },
        {
            "source": "Alexandria",
            "label_type": "computed materials stability labels",
            "candidate_join_requirement": "structure/prototype matching",
            "local_label_file_available": False,
            "expected_strength": "large independent public source",
            "main_risk": "requires local curated join table before release evaluation",
            "feasibility_status": "external_mapping_required",
        },
        {
            "source": "GNoME-derived public candidates",
            "label_type": "computed stability / discovery-candidate validation",
            "candidate_join_requirement": "structure/prototype matching and license-compatible labels",
            "local_label_file_available": False,
            "expected_strength": "frontier-scale discovery context",
            "main_risk": "provenance and train/test overlap must be audited carefully",
            "feasibility_status": "external_mapping_required",
        },
    ]
    return pd.DataFrame(rows)


def build_cards() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "card_id": "A1_temporal_split_materials_protocol",
                "card_type": "preregistered_protocol_feasibility",
                "domain": "materials_discovery",
                "validation_mode": "time_split_public_DFT_labels",
                "status": "protocol_ready_external_timestamp_required",
                "completed_positive_result": False,
                "blocks_submission": False,
                "reason": "local WBM summary has candidate labels but no public label-release timestamp column",
            },
            {
                "card_id": "A2_independent_DFT_crossvalidation_protocol",
                "card_type": "preregistered_protocol_feasibility",
                "domain": "materials_discovery",
                "validation_mode": "independent_public_DFT_source",
                "status": "protocol_ready_external_mapping_required",
                "completed_positive_result": False,
                "blocks_submission": False,
                "reason": "requires a public source join table before evaluation; no independent-source labels are fabricated",
            },
            {
                "card_id": "A3_new_DFT_followup_pilot",
                "card_type": "optional_future_pilot",
                "domain": "materials_discovery",
                "validation_mode": "new_computational_DFT",
                "status": "optional_not_started",
                "completed_positive_result": False,
                "blocks_submission": False,
                "reason": "high-upside pilot only; not a current NMI gate",
            },
        ]
    )


def write_markdown(out_dir: Path, temporal: pd.DataFrame, independent: pd.DataFrame) -> None:
    temporal_row = temporal.iloc[0]
    independent_row = independent.iloc[0]
    closeout = f"""# Materials Prospective Validation Protocol Closeout

Evidence status: protocol feasibility only.

This milestone freezes A1/A2 designs without claiming a completed prospective
materials result. It introduces no new DFT, no new human labels, and no protocol-only positive row is promoted.

## A1 Temporal Split

- Protocol: `{temporal_row['protocol_id']}`
- Status: `{temporal_row['feasibility_status']}`
- Reason: the local WBM summary contains stable-label fields but no
  label-release timestamp column. A real A1 run needs an external release
  snapshot or timestamp table before it can be evaluated.

## A2 Independent DFT Source

- Protocol: `{independent_row['protocol_id']}`
- Status: `protocol_ready_external_mapping_required`
- Reason: an independent public DFT label source must be joined after the
  release decision. The repository does not fabricate independent-source
  labels from WBM summaries.

## A3

A new DFT follow-up pilot remains optional and is not a current submission
gate.
"""
    (out_dir / "MATERIALS_PROSPECTIVE_VALIDATION_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    a1 = """# A1 Temporal Materials Split Protocol

This is a preregistered protocol, not a completed result.

Goal: simulate a materials release decision made at time `t0`, before later DFT
labels are available.

Rules:
- only DFT-stable positives public at or before `t0` may enter PARC calibration;
- future labels cannot affect proposal scores, source choice, gamma, K, blocks,
  seed selection, or the release rule;
- after PARC releases/refuses, post-`t0` labels evaluate realized FTR and
  unstable follow-ups prevented;
- the result must be reported as quasi-prospective computational validation,
  not experimental synthesis.
"""
    (out_dir / "A1_TEMPORAL_SPLIT_PREREGISTRATION.md").write_text(a1, encoding="utf-8")

    a2 = """# A2 Independent DFT Source Cross-Validation Protocol

This is a preregistered protocol, not a completed result.

Goal: evaluate a frozen WBM/Matbench release decision against an independent
public DFT label source after PARC release/refusal.

Rules:
- WBM/Matbench labels can provide one-sided calibration positives;
- the independent source can only be joined after the release decision;
- candidate joins must be reproducible by material identifier or
  structure/prototype matching;
- source disagreements are reported as label-source sensitivity, not hidden
  errors.
"""
    (out_dir / "A2_INDEPENDENT_DFT_CROSSVALIDATION_PREREGISTRATION.md").write_text(a2, encoding="utf-8")


def write_provenance(path: Path, inputs: dict[str, str], started: float, role: str) -> None:
    payload = {
        "artifact": path.name,
        "role": role,
        "command": "python scripts/build_materials_prospective_validation_protocols.py",
        "runtime_sec": round(time.time() - started, 3),
        "input_sha256": inputs,
        "output_sha256": sha256_file(path),
    }
    path.with_suffix(path.suffix + ".provenance.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="outputs/milestones/materials_prospective_validation_protocols")
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM))
    parser.add_argument("--alignn-predictions", default=str(DEFAULT_ALIGNN))
    parser.add_argument("--cgcnn-predictions", default=str(DEFAULT_CGCNN))
    parser.add_argument("--megnet-predictions", default=str(DEFAULT_MEGNET))
    args = parser.parse_args()

    started = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wbm_info = inspect_wbm_columns(Path(args.wbm_summary))
    input_hashes = {
        "wbm_summary_sha256": sha256_optional(Path(args.wbm_summary)),
        "alignn_predictions_sha256": sha256_optional(Path(args.alignn_predictions)),
        "cgcnn_predictions_sha256": sha256_optional(Path(args.cgcnn_predictions)),
        "megnet_predictions_sha256": sha256_optional(Path(args.megnet_predictions)),
        "materials_trial_summary_sha256": sha256_optional(
            ROOT / "outputs/milestones/materials_computational_followup_trial/table_materials_computational_trial_summary.csv"
        ),
    }
    temporal = build_temporal_protocol(args, wbm_info)
    temporal_feas = build_temporal_feasibility(args, wbm_info)
    independent = build_independent_dft_protocol()
    independent_feas = build_independent_source_feasibility()
    cards = build_cards()
    go_no_go = pd.DataFrame(
        [
            {
                "item": "A1_temporal_split",
                "decision": "do_not_promote_until_timestamp_or_snapshot_supplied",
                "submission_gate": "not_required_for_current_submission",
                "evidence_status": "protocol_feasibility_not_completed_evidence",
            },
            {
                "item": "A2_independent_DFT_source",
                "decision": "do_not_promote_until_independent_join_table_supplied",
                "submission_gate": "not_required_for_current_submission",
                "evidence_status": "protocol_feasibility_not_completed_evidence",
            },
            {
                "item": "A3_new_DFT_followup",
                "decision": "optional_pilot_only",
                "submission_gate": "not_required_for_current_submission",
                "evidence_status": "not_started_optional",
            },
        ]
    )
    outputs = {
        "table_materials_temporal_split_protocol.csv": temporal,
        "table_materials_temporal_split_feasibility.csv": temporal_feas,
        "table_materials_independent_dft_protocol.csv": independent,
        "table_materials_independent_dft_source_feasibility.csv": independent_feas,
        "table_materials_prospective_validation_cards.csv": cards,
        "table_materials_prospective_validation_go_no_go.csv": go_no_go,
    }
    for name, frame in outputs.items():
        frame.to_csv(out_dir / name, index=False)
    write_markdown(out_dir, temporal, independent)

    for name in outputs:
        write_provenance(out_dir / name, input_hashes, started, name.removesuffix(".csv"))
    for name, role in [
        ("MATERIALS_PROSPECTIVE_VALIDATION_CLOSEOUT.md", "closeout"),
        ("A1_TEMPORAL_SPLIT_PREREGISTRATION.md", "a1_preregistration"),
        ("A2_INDEPENDENT_DFT_CROSSVALIDATION_PREREGISTRATION.md", "a2_preregistration"),
    ]:
        write_provenance(out_dir / name, input_hashes, started, role)
    write_manifest(out_dir)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
