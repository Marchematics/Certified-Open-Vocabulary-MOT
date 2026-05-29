#!/usr/bin/env python3
"""Build Phase70 DFT v2 execution checkpoint artifacts.

This checkpoint monitors the local VASP execution layer for the blinded Phase68
DFT v2 package. It extracts queue status and final energies where available, but
it deliberately does not construct e_above_hull or stable_exact outcomes.

VASP_DONE / completed queue status is therefore execution progress only, not a
materials-stability validation signal.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE68 = ROOT / "outputs/milestones/ncs_phase68_dft_v2_pilot"
OUT = ROOT / "outputs/milestones/ncs_phase70_dft_v2_checkpoint"
RUN_ROOT = Path("/root/vasp_runs/ncs_phase68_dft_v2_pilot_nonspin_fixedcell_safe")
STATUS_CSV = RUN_ROOT / "vasp_queue_status.csv"
JOBS = RUN_ROOT / "jobs"
FAILURE_GATE = 0.10
SCOPE = (
    "DFT_v2_execution_checkpoint;"
    "local_VASP_nonspin_fixedcell_safe;"
    "final_energy_only_no_reference_hull;"
    "no_e_above_hull;"
    "no_stable_exact;"
    "not_DFT_validation_evidence;"
    "not_prospective_materials_discovery"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def parse_job_meta(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    rows: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if "\t" in line:
            key, value = line.split("\t", 1)
            rows[key] = value
    return rows


def parse_outcar(path: Path) -> tuple[float | None, bool, bool]:
    if not path.exists():
        return None, False, False
    text = path.read_text(errors="replace")
    energies = re.findall(r"free\s+energy\s+TOTEN\s+=\s+([-+0-9.Ee]+)\s+eV", text)
    final_energy = float(energies[-1]) if energies else None
    reached = "reached required accuracy - stopping structural energy minimisation" in text
    timing = "General timing and accounting informations for this job" in text
    return final_energy, reached, timing


def load_status() -> pd.DataFrame:
    if STATUS_CSV.exists():
        return pd.read_csv(STATUS_CSV)
    return pd.DataFrame(columns=["blinded_job_id", "status", "exit_code", "elapsed_seconds"])


def build_blinded_status() -> pd.DataFrame:
    manifest = pd.read_csv(PHASE68 / "dft_v2_blinded_transfer_manifest.csv")
    status = load_status()
    status_map = status.set_index("blinded_job_id").to_dict("index") if len(status) else {}
    rows: list[dict[str, object]] = []
    for row in manifest.to_dict("records"):
        job_id = str(row["blinded_job_id"])
        job_dir = JOBS / job_id
        meta = parse_job_meta(job_dir / "JOB_META.tsv")
        status_row = status_map.get(job_id, {})
        raw_status = str(status_row.get("status", ""))
        if raw_status in {"completed", "failed"}:
            execution_status = raw_status
        elif (job_dir / "VASP_RUNNING").exists():
            execution_status = "running"
        elif job_dir.exists():
            execution_status = "pending"
        else:
            execution_status = "not_materialized"
        final_energy, reached_accuracy, has_timing = parse_outcar(job_dir / "OUTCAR")
        n_sites = int(row["n_sites"])
        final_per_atom = final_energy / n_sites if final_energy is not None and n_sites else math.nan
        rows.append(
            {
                "blinded_job_id": job_id,
                "formula": row["formula"],
                "n_sites": n_sites,
                "execution_status": execution_status,
                "exit_code": status_row.get("exit_code", ""),
                "elapsed_seconds": status_row.get("elapsed_seconds", ""),
                "stage": meta.get("stage", "unknown"),
                "final_energy_eV": final_energy if final_energy is not None else "",
                "final_energy_per_atom_eV": final_per_atom if math.isfinite(final_per_atom) else "",
                "reached_required_accuracy": bool(reached_accuracy),
                "outcar_has_timing_footer": bool(has_timing),
                "e_above_hull_available": False,
                "stable_exact_available": False,
                "claim_status": "execution_progress_only_not_stability_outcome",
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def checkpoint_summary(blinded: pd.DataFrame) -> pd.DataFrame:
    total = int(len(blinded))
    completed = int(blinded["execution_status"].eq("completed").sum())
    failed = int(blinded["execution_status"].eq("failed").sum())
    running = int(blinded["execution_status"].eq("running").sum())
    pending = int(blinded["execution_status"].eq("pending").sum())
    finished = completed + failed
    early_failure_rate = failed / finished if finished else math.nan
    manifest_failure_rate_so_far = failed / total if total else math.nan
    return pd.DataFrame(
        [
            {
                "total_manifest_jobs": total,
                "completed_jobs": completed,
                "failed_jobs": failed,
                "running_jobs": running,
                "pending_jobs": pending,
                "finished_jobs": finished,
                "early_failure_rate_over_finished_jobs": early_failure_rate,
                "manifest_failure_rate_so_far": manifest_failure_rate_so_far,
                "workflow_gate_threshold": FAILURE_GATE,
                "early_failure_rate_exceeds_gate": bool(math.isfinite(early_failure_rate) and early_failure_rate > FAILURE_GATE),
                "e_above_hull_outcomes_available": False,
                "stable_exact_outcomes_available": False,
                "checkpoint_interpretation": "no_claim_ready_DFT_signal;monitor_failure_rate_before_any_efficacy_claim",
                "evidence_scope": SCOPE,
            }
        ]
    )


def completed_energy_table(blinded: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "blinded_job_id",
        "formula",
        "n_sites",
        "execution_status",
        "final_energy_eV",
        "final_energy_per_atom_eV",
        "reached_required_accuracy",
        "outcar_has_timing_footer",
        "e_above_hull_available",
        "stable_exact_available",
        "claim_status",
        "evidence_scope",
    ]
    completed = blinded[blinded["execution_status"].eq("completed")].copy()
    return completed[cols]


def quarantined_arm_table(blinded: pd.DataFrame) -> pd.DataFrame:
    arm = pd.read_csv(PHASE68 / "dft_v2_analysis_arm_key.csv")
    merged = blinded.merge(arm[["blinded_job_id", "dft_v2_arm"]], on="blinded_job_id", how="left")
    rows: list[dict[str, object]] = []
    for arm_name, group in merged.groupby("dft_v2_arm", dropna=False, sort=True):
        total = int(len(group))
        completed = int(group["execution_status"].eq("completed").sum())
        failed = int(group["execution_status"].eq("failed").sum())
        running = int(group["execution_status"].eq("running").sum())
        pending = int(group["execution_status"].eq("pending").sum())
        finished = completed + failed
        failure_finished = failed / finished if finished else math.nan
        rows.append(
            {
                "dft_v2_arm": arm_name,
                "planned_jobs": total,
                "completed_jobs": completed,
                "failed_jobs": failed,
                "running_jobs": running,
                "pending_jobs": pending,
                "finished_jobs": finished,
                "failure_rate_over_finished_jobs": failure_finished,
                "failure_rate_over_planned_jobs_so_far": failed / total if total else math.nan,
                "quarantine_status": "unblinded_execution_QC_only_not_efficacy_claim",
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def outcome_readiness() -> pd.DataFrame:
    fields = [
        ("final_energy_per_atom", True, "extracted_from_completed_VASP_OUTCAR"),
        ("e_above_hull_ev_per_atom", False, "requires_reference_hull_postprocessing"),
        ("stable_exact", False, "requires_e_above_hull_ev_per_atom"),
        ("stable_25mev", False, "requires_e_above_hull_ev_per_atom"),
        ("sanity_control_direction", False, "requires_stable_exact_for_sanity_controls"),
        ("primary_conservative_FTR", False, "requires_stable_exact_and_failure_policy_application"),
    ]
    return pd.DataFrame(
        [
            {
                "outcome_field": name,
                "available_at_checkpoint": available,
                "blocker_or_source": source,
                "claim_status": "not_claim_ready" if not available or name == "final_energy_per_atom" else "ready",
                "evidence_scope": SCOPE,
            }
            for name, available, source in fields
        ]
    )


def write_text(summary: pd.DataFrame) -> None:
    row = summary.iloc[0]
    text = f"""# Phase70 DFT v2 Checkpoint

Status: `execution_checkpoint_no_stability_outcomes`.

The local VASP queue for the blinded Phase68 DFT v2 package is running under a
nonspin fixed-cell safe execution layer. This checkpoint records execution
progress and final energies where available. It does not compute
`e_above_hull_ev_per_atom` or `stable_exact`.

Current checkpoint:

- total manifest jobs: `{int(row['total_manifest_jobs'])}`
- completed jobs: `{int(row['completed_jobs'])}`
- failed jobs: `{int(row['failed_jobs'])}`
- running jobs inferred from local `VASP_RUNNING` markers: `{int(row['running_jobs'])}`
- finished-job failure rate: `{row['early_failure_rate_over_finished_jobs']}`
- workflow gate threshold: `{row['workflow_gate_threshold']}`

Interpretation:

`VASP_DONE` / `completed` means a single-structure calculation has VASP output
and a final energy can be extracted. It is not a stability outcome. DFT v2
cannot support a prospective materials-discovery claim, release-vs-tail utility
claim, or alpha claim until the reference-hull outcome layer generates
`e_above_hull_ev_per_atom` and `stable_exact` and the numeric workflow gates pass.
"""
    (OUT / "DFT_V2_CHECKPOINT.md").write_text(text, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase70_dft_v2_checkpoint"]
    rows.append(
        {
            "milestone": "ncs_phase70_dft_v2_checkpoint",
            "path": "outputs/milestones/ncs_phase70_dft_v2_checkpoint/",
            "evidence_state": "execution_checkpoint_no_stability_outcomes",
            "manifest": "outputs/milestones/ncs_phase70_dft_v2_checkpoint/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase70_dft_v2_checkpoint",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["milestone", "path", "evidence_state", "manifest", "public_bundle_check"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def update_claim_table() -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase70 DFT v2 Checkpoint"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    addition = """

## Phase70 DFT v2 Checkpoint

Status: `execution_checkpoint_no_stability_outcomes`.

Phase70 monitors the local VASP execution layer for the blinded Phase68 DFT v2
package. It extracts final energies for completed VASP jobs and reports
workflow failure rates, but no `e_above_hull` or `stable_exact` outcomes are
available. The allowed claim is execution progress only. DFT v2 remains outside
the main positive evidence chain until reference-hull postprocessing and the
frozen workflow/efficacy gates pass.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(summary: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "MAT-DFTV2-CHECKPOINT-001"]
    artifact = OUT / "table_dft_v2_execution_checkpoint_summary.csv"
    rows.append(
        {
            "claim_id": "MAT-DFTV2-CHECKPOINT-001",
            "claim_text": "DFT v2 local VASP execution is monitored as an execution checkpoint without stable_exact outcomes.",
            "evidence_type": "DFT_execution_checkpoint",
            "positive_evidence": "no",
            "scope": "execution_progress_only_not_DFT_validation",
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase70-dft-v2-checkpoint",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_stability_DFT_validation_or_prospective_discovery",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    blinded = build_blinded_status()
    summary = checkpoint_summary(blinded)
    energies = completed_energy_table(blinded)
    arm_qc = quarantined_arm_table(blinded)
    readiness = outcome_readiness()

    blinded.to_csv(OUT / "table_dft_v2_blinded_execution_status.csv", index=False)
    summary.to_csv(OUT / "table_dft_v2_execution_checkpoint_summary.csv", index=False)
    energies.to_csv(OUT / "table_dft_v2_completed_energy_extract.csv", index=False)
    arm_qc.to_csv(OUT / "table_dft_v2_quarantined_arm_failure_checkpoint.csv", index=False)
    readiness.to_csv(OUT / "table_dft_v2_outcome_readiness.csv", index=False)
    provenance = {
        "status": "execution_checkpoint_no_stability_outcomes",
        "run_root_label": RUN_ROOT.name,
        "run_root_scope": "local execution path withheld from public bundle",
        "phase68_manifest_sha256": sha256_file(PHASE68 / "MANIFEST_SHA256.txt"),
        "completed_jobs": int(summary.iloc[0]["completed_jobs"]),
        "failed_jobs": int(summary.iloc[0]["failed_jobs"]),
        "running_jobs": int(summary.iloc[0]["running_jobs"]),
        "e_above_hull_outcomes_available": False,
        "stable_exact_outcomes_available": False,
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    write_text(summary)
    update_artifact_index()
    update_claim_table()
    update_evidence_ledger(summary)
    write_manifest(OUT)
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
