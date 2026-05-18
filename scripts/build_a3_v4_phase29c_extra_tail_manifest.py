#!/usr/bin/env python3
"""Freeze Phase29c A3-v4 raw-top100 extra-tail manifest before DFT outcomes.

This script does not modify selection_frozen_v4.csv. It checks that no DFT
outcome is present, records whether local DFT execution can be launched, and
exports the 25 score-ranked formal raw-top100 candidates that were not in the
full PARC release arm.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"
ENDPOINT_ID = "v4a_strict_exact_K100"


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


def write_root_manifest() -> None:
    rows: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def assert_no_dft_outcomes() -> dict[str, object]:
    manifest_paths = [OUT / "dft_job_manifest_v4.csv", OUT / "dft_job_manifest_v4_addendum.csv"]
    rows = 0
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue
        df = pd.read_csv(manifest_path)
        rows += len(df)
        if "outcome_available" in df.columns and df["outcome_available"].astype(bool).any():
            raise RuntimeError(f"{manifest_path} contains outcome_available=True; refusing to freeze Phase29c.")
        if "outcome_file" in df.columns and df["outcome_file"].fillna("").astype(str).str.strip().ne("").any():
            raise RuntimeError(f"{manifest_path} contains non-empty outcome_file; refusing to freeze Phase29c.")
    outcome_patterns = [
        "dft_results*.csv",
        "dft_results*.json",
        "dft_outputs",
        "vasp_outputs",
        "qe_outputs",
        "relax_outputs",
    ]
    found: list[str] = []
    for pattern in outcome_patterns:
        for path in OUT.glob(pattern):
            if path.is_dir():
                if any(path.rglob("*")):
                    found.append(path.relative_to(ROOT).as_posix())
            elif path.is_file() and path.stat().st_size > 0:
                found.append(path.relative_to(ROOT).as_posix())
    if found:
        raise RuntimeError(f"Found possible DFT outcome artifacts before Phase29c: {found}")
    return {"manifest_rows_checked": rows, "outcome_available": False, "outcome_artifacts_found": 0}


def executable_status() -> tuple[str, str, list[str]]:
    candidates = ["vasp_std", "vasp_gam", "pw.x", "sbatch", "qsub", "mpirun"]
    found = [cmd for cmd in candidates if shutil.which(cmd)]
    if any(cmd in found for cmd in ["vasp_std", "vasp_gam", "pw.x"]):
        return "launch_ready_engine_detected", "A local DFT executable was detected; launch should be performed by the private compute wrapper.", found
    return "blocked_no_local_DFT_engine_or_scheduler", "No local VASP/QE executable or scheduler command was found in PATH; no DFT process was started.", found


def row_value(row: pd.Series, key: str, default: object = "") -> object:
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return value


def build_extra_tail() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    outcome_scan = assert_no_dft_outcomes()
    selection_path = OUT / "selection_frozen_v4.csv"
    selection_hash = sha256_file(selection_path)
    strict = pd.read_csv(OUT / "candidate_universe_strict_public_label_free.csv")
    scores = pd.read_csv(OUT / "consensus_scores_4039.csv")
    release = pd.read_csv(OUT / "dft_job_manifest_v4_addendum.csv")
    release_ids = set(release[release["arm"].eq("PARC-release-full")]["candidate_id"].astype(str))

    formal = strict.merge(scores, on=["candidate_id", "formula", "structure_ref", "structure_sha256"], how="inner")
    formal = formal.sort_values(["consensus_score", "candidate_id"], ascending=[False, True]).copy()
    formal["formal_raw_score_rank"] = range(1, len(formal) + 1)
    top100 = formal.head(100).copy()
    extra = top100[~top100["candidate_id"].astype(str).isin(release_ids)].copy()
    extra = extra.sort_values(["formal_raw_score_rank", "candidate_id"]).copy()

    timestamp = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []
    for idx, (_, row) in enumerate(extra.iterrows(), start=1):
        rows.append(
            {
                "phase29c_manifest_id": "phase29c_raw_top100_extra_tail_pre_outcome",
                "dft_job_id": f"a3v4-phase29c-raw-top100-extra-tail-{idx:04d}",
                "candidate_id": row["candidate_id"],
                "arm": "raw_top100_extra_tail",
                "comparator_role": "pre-outcome extra-tail candidates from formal score-ranked raw top100 not in PARC release",
                "endpoint_id": ENDPOINT_ID,
                "dft_priority_rank": idx,
                "formal_raw_score_rank": int(row["formal_raw_score_rank"]),
                "original_raw_rank": int(row_value(row, "raw_rank", 0)),
                "parc_release_flag": False,
                "selected_for_release": False,
                "raw_top100_member": True,
                "public_label_exclusion_status": row_value(row, "public_label_exclusion_status", "available_source_strict_public_label_free"),
                "structure_match_public": bool(row_value(row, "structure_match_public", False)),
                "structure_ref": row_value(row, "structure_ref"),
                "structure_sha256": row_value(row, "structure_sha256"),
                "formula": row_value(row, "formula"),
                "score_chgnet": float(row_value(row, "chgnet_score", 0.0)),
                "score_mace": float(row_value(row, "mace_score", 0.0)),
                "score_consensus": float(row_value(row, "consensus_score", 0.0)),
                "block_id": row_value(row, "chemical_system", row_value(row, "block_id")),
                "dft_engine": "VASP-or-equivalent-MP-compatible-engine",
                "input_status": "ready_for_private_DFT_input_export_phase29c_extra_tail",
                "failure_policy": "conservative_failed_DFT_counted_not_certified_stable",
                "selected_before_DFT_outcome": True,
                "outcome_available": False,
                "outcome_file": "",
                "selection_frozen_v4_sha256": selection_hash,
                "construction_inputs": "strict_public_label_free_universe;consensus_score;formal_raw_score_rank;release_addendum_candidate_ids",
                "construction_timestamp": timestamp,
                "evidence_status": "pre_outcome_phase29c_extra_tail_manifest_not_DFT_evidence",
            }
        )

    manifest = pd.DataFrame(rows)
    launch_status, launch_reason, found_commands = executable_status()
    launch = pd.DataFrame(
        [
            {
                "launch_target": "PARC-release-full",
                "requested_jobs": int(len(release_ids)),
                "launch_status": launch_status,
                "processes_started": 0 if launch_status.startswith("blocked") else "",
                "detected_commands": "|".join(found_commands),
                "outcome_available_before_launch_attempt": False,
                "claim_scope": "launch_status_only_not_DFT_evidence",
                "reason": launch_reason,
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "gate": "DFT_outcome_scan",
                "status": "no_DFT_outcomes_detected",
                "n_rows": int(outcome_scan["manifest_rows_checked"]),
                "completed_positive_result": False,
                "blocks_primary_claim": False,
                "reason": "No outcome files and no manifest outcome fields were populated before Phase29c.",
            },
            {
                "gate": "PARC_release_launch_attempt",
                "status": launch_status,
                "n_rows": int(len(release_ids)),
                "completed_positive_result": False,
                "blocks_primary_claim": True,
                "reason": launch_reason,
            },
            {
                "gate": "raw_top100_extra_tail_manifest",
                "status": "frozen_pre_outcome" if len(manifest) >= 25 else "blocked_insufficient_extra_tail",
                "n_rows": int(len(manifest)),
                "completed_positive_result": False,
                "blocks_primary_claim": False,
                "reason": "25 extra-tail candidates exist in the formal score-ranked raw top100 and were frozen before DFT outcomes." if len(manifest) >= 25 else "Fewer than 25 extra-tail candidates were available.",
            },
            {
                "gate": "selection_integrity",
                "status": "selection_frozen_v4_unmodified_input",
                "n_rows": int(len(pd.read_csv(selection_path))),
                "completed_positive_result": False,
                "blocks_primary_claim": False,
                "reason": f"selection_frozen_v4_sha256={selection_hash}",
            },
        ]
    )
    return manifest, launch, summary


def update_docs() -> None:
    claim_path = ROOT / "docs" / "claim_table.md"
    claim_text = claim_path.read_text(encoding="utf-8")
    marker = "| A3-v4 Phase29c raw-top100 extra-tail manifest is frozen before outcomes but remains non-evidence. |"
    if marker not in claim_text:
        row = (
            marker
            + " `outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv`; "
            + "`table_phase29c_raw_top100_extra_tail_summary.csv` | "
            + "`python scripts/build_a3_v4_phase29c_extra_tail_manifest.py` | "
            + "Phase29c uses only strict public-label-free status, frozen consensus score and release-addendum candidate ids. "
            + "It records that local DFT execution was not started because no DFT engine/scheduler was available; no DFT outcome or prospective discovery claim is made. |\n"
        )
        claim_text = claim_text.replace("| Phase33 finalizes the NMI presubmission go/no-go package.", row + "| Phase33 finalizes the NMI presubmission go/no-go package.")
        claim_path.write_text(claim_text, encoding="utf-8")

    artifact_path = ROOT / "outputs" / "artifact_index.csv"
    artifact = pd.read_csv(artifact_path)
    if "mattergen_a3_v4_phase29c_extra_tail_manifest" not in set(artifact["milestone"].astype(str)):
        artifact.loc[len(artifact)] = {
            "milestone": "mattergen_a3_v4_phase29c_extra_tail_manifest",
            "path": "outputs/milestones/mattergen_parc_prospective_dft_followup/",
            "evidence_state": "completed_pre_DFT_extra_tail_manifest_not_positive_evidence",
            "manifest": "outputs/milestones/mattergen_parc_prospective_dft_followup/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/mattergen_parc_prospective_dft_followup",
        }
        artifact.to_csv(artifact_path, index=False)

    makefile = ROOT / "Makefile"
    make = makefile.read_text(encoding="utf-8")
    if "reproduce-a3-v4-phase29c-extra-tail-manifest" not in make:
        make = make.replace(
            "reproduce-a3-v4-dft-manifest-addendum:\n\t$(PYTHON) scripts/build_a3_v4_dft_manifest_addendum.py\n",
            "reproduce-a3-v4-dft-manifest-addendum:\n\t$(PYTHON) scripts/build_a3_v4_dft_manifest_addendum.py\n\n"
            "reproduce-a3-v4-phase29c-extra-tail-manifest:\n\t$(PYTHON) scripts/build_a3_v4_phase29c_extra_tail_manifest.py\n",
        )
        make = make.replace(
            "reproduce-a3-v4-dft-manifest-addendum",
            "reproduce-a3-v4-dft-manifest-addendum reproduce-a3-v4-phase29c-extra-tail-manifest",
            1,
        )
        makefile.write_text(make, encoding="utf-8")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    if "A3-v4 Phase29c extra-tail manifest" not in readme_text:
        readme_text += (
            "\n- A3-v4 Phase29c extra-tail manifest: 25 formal raw-top100 extra-tail candidates are frozen before DFT outcomes. "
            "Local DFT execution was not started in this environment because no DFT engine/scheduler was detected; no DFT outcome or prospective materials claim is made.\n"
        )
        readme.write_text(readme_text, encoding="utf-8")

    repro = ROOT / "REPRODUCIBILITY.md"
    repro_text = repro.read_text(encoding="utf-8")
    if "reproduce-a3-v4-phase29c-extra-tail-manifest" not in repro_text:
        repro_text += (
            "\n## A3-v4 Phase29c extra-tail manifest\n\n"
            "Run `make reproduce-a3-v4-phase29c-extra-tail-manifest` after the Phase29b addendum to rebuild the pre-outcome formal raw-top100 extra-tail manifest. "
            "This does not modify `selection_frozen_v4.csv` and is not completed DFT evidence.\n"
        )
        repro.write_text(repro_text, encoding="utf-8")


def main() -> None:
    manifest, launch, summary = build_extra_tail()
    manifest.to_csv(OUT / "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv", index=False)
    launch.to_csv(OUT / "table_phase29c_dft_launch_status.csv", index=False)
    summary.to_csv(OUT / "table_phase29c_raw_top100_extra_tail_summary.csv", index=False)
    closeout = (
        "# A3-v4 Phase29c Raw-Top100 Extra-Tail Manifest Closeout\n\n"
        "Status: pre-outcome raw-top100 extra-tail manifest frozen. This is not DFT evidence.\n\n"
        "## Outcome status\n\n"
        "No DFT outcome files or populated outcome fields were detected before this manifest was built.\n\n"
        "## Launch status\n\n"
        "The environment did not expose a local VASP/QE executable or scheduler command, so no DFT process was started here. "
        "The 75 PARC-release-full jobs remain frozen for private compute execution after the pre-outcome tags.\n\n"
        "## Extra-tail manifest\n\n"
        "`dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv` contains 25 candidates from the formal score-ranked raw top100 that are not in the PARC-release-full arm. "
        "Construction used only frozen consensus scores, public-label exclusion status and release-addendum candidate ids. `selection_frozen_v4.csv` was not modified.\n\n"
        "## Claim boundary\n\n"
        "Phase29c is a manifest-control artifact. DFT failures must be counted conservatively as not-certified-stable / false for FTR when outcomes are later analyzed. "
        "Until outcomes are returned, the claim table must continue to state that there is no prospective DFT evidence.\n"
    )
    (OUT / "A3_V4_PHASE29C_RAW_TOP100_EXTRA_TAIL_CLOSEOUT.md").write_text(closeout, encoding="utf-8")
    update_docs()
    write_manifest(OUT)
    write_root_manifest()


if __name__ == "__main__":
    main()
