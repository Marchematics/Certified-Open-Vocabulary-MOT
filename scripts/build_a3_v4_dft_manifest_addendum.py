#!/usr/bin/env python3
"""Build Phase29b A3-v4 pre-outcome DFT comparator manifest addendum.

This addendum does not modify selection_frozen_v4.csv. It reconstructs the
pre-outcome full PARC release arm and matched raw-topR arm from frozen scores,
formal public-label exclusion status and PARC release flags only.
"""

from __future__ import annotations

import hashlib
import json
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
    manifest_path = OUT / "dft_job_manifest_v4.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    jobs = pd.read_csv(manifest_path)
    if "outcome_available" in jobs.columns and jobs["outcome_available"].astype(bool).any():
        raise RuntimeError("Existing dft_job_manifest_v4.csv contains outcome_available=True; refusing to build primary addendum.")
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
        raise RuntimeError(f"Found possible DFT outcome artifacts before addendum: {found}")
    return {
        "existing_manifest_rows": int(len(jobs)),
        "existing_manifest_outcome_available": False,
        "possible_outcome_artifacts_found": 0,
    }


def load_formal_raw() -> pd.DataFrame:
    strict = pd.read_csv(OUT / "candidate_universe_strict_public_label_free.csv")
    raw = pd.read_csv(OUT / f"table_mattergen_smoke_raw_topK_{ENDPOINT_ID}.csv")
    eligible_ids = set(strict["candidate_id"].astype(str))
    formal_raw = raw[raw["candidate_id"].astype(str).isin(eligible_ids)].copy()
    if formal_raw.empty:
        raise RuntimeError("No formal raw rows available for Phase29b addendum.")
    return formal_raw


def row_value(row: pd.Series, key: str, default: object = "") -> object:
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return value


def build_arm_rows(
    *,
    arm: str,
    role: str,
    frame: pd.DataFrame,
    selection_hash: str,
    timestamp: str,
    max_rows: int | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    selected = frame if max_rows is None else frame.head(max_rows)
    for idx, (_, row) in enumerate(selected.iterrows(), start=1):
        slug = arm.lower().replace("_", "-").replace(" ", "-")
        rows.append(
            {
                "manifest_addendum_id": "phase29b_pre_outcome_comparator_manifest",
                "dft_job_id": f"a3v4-phase29b-{slug}-{idx:04d}",
                "candidate_id": row["candidate_id"],
                "arm": arm,
                "comparator_role": role,
                "endpoint_id": ENDPOINT_ID,
                "dft_priority_rank": idx,
                "raw_rank": int(row_value(row, "raw_rank", idx)),
                "release_rank": int(row_value(row, "release_rank", idx)),
                "parc_release_flag": bool(row_value(row, "parc_release_flag", False)),
                "selected_for_release": bool(row_value(row, "parc_release_flag", False)),
                "raw_topK_member": True,
                "public_label_exclusion_status": row_value(row, "public_label_exclusion_status", "available_source_strict_public_label_free"),
                "structure_match_public": bool(row_value(row, "structure_match_public", False)),
                "structure_ref": row_value(row, "structure_ref"),
                "structure_sha256": row_value(row, "structure_sha256"),
                "formula": row_value(row, "formula"),
                "score_consensus": float(row_value(row, "consensus_score", row_value(row, "frozen_model_score", 0.0))),
                "e_value": float(row_value(row, "_evalue", 0.0)),
                "required_e": 10.0,
                "block_id": row_value(row, "block_id"),
                "dft_engine": "VASP-or-equivalent-MP-compatible-engine",
                "input_status": "ready_for_private_DFT_input_export_addendum",
                "failure_policy": "conservative_failed_DFT_counted_not_certified_stable",
                "selected_before_DFT_outcome": True,
                "outcome_available": False,
                "outcome_file": "",
                "selection_frozen_v4_sha256": selection_hash,
                "construction_inputs": "frozen_score;raw_rank;parc_release_flag;public_label_exclusion_status",
                "construction_timestamp": timestamp,
                "evidence_status": "pre_outcome_manifest_addendum_not_DFT_evidence",
            }
        )
    return rows


def build_addendum() -> tuple[pd.DataFrame, pd.DataFrame]:
    outcome_scan = assert_no_dft_outcomes()
    selection_path = OUT / "selection_frozen_v4.csv"
    selection_hash = sha256_file(selection_path)
    formal_raw = load_formal_raw()

    released = formal_raw[formal_raw["parc_release_flag"].astype(bool)].copy()
    released = released.sort_values(["_evalue", "frozen_model_score", "candidate_id"], ascending=[False, False, True]).copy()
    released["release_rank"] = range(1, len(released) + 1)
    raw_ranked = formal_raw.sort_values(["frozen_model_score", "candidate_id"], ascending=[False, True]).copy()
    raw_topr = raw_ranked.head(len(released)).copy()
    raw_topr["release_rank"] = range(1, len(raw_topr) + 1)
    raw_only = raw_ranked[~raw_ranked["candidate_id"].astype(str).isin(set(released["candidate_id"].astype(str)))].copy()

    if len(released) == 0:
        raise RuntimeError("No released candidates available for addendum.")

    timestamp = datetime.now(timezone.utc).isoformat()
    arm_rows: list[dict[str, object]] = []
    arm_rows += build_arm_rows(
        arm="PARC-release-full",
        role="full PARC release arm; compute-all-if-resources-allow",
        frame=released,
        selection_hash=selection_hash,
        timestamp=timestamp,
    )
    arm_rows += build_arm_rows(
        arm="raw_topR_matched",
        role="matched raw prefix with same size as full PARC DFT arm; identical candidate set here",
        frame=raw_topr,
        selection_hash=selection_hash,
        timestamp=timestamp,
        max_rows=len(released),
    )
    if len(raw_only) >= 25:
        raw_only = raw_only.copy()
        raw_only["release_rank"] = range(1, len(raw_only) + 1)
        arm_rows += build_arm_rows(
            arm="raw_only_rejected_tail",
            role="optional stretch comparator",
            frame=raw_only,
            selection_hash=selection_hash,
            timestamp=timestamp,
            max_rows=len(released),
        )

    addendum = pd.DataFrame(arm_rows)
    release_ids = set(addendum[addendum["arm"].eq("PARC-release-full")]["candidate_id"].astype(str))
    raw_topr_ids = set(addendum[addendum["arm"].eq("raw_topR_matched")]["candidate_id"].astype(str))
    raw_only_ids = set(addendum[addendum["arm"].eq("raw_only_rejected_tail")]["candidate_id"].astype(str))
    raw_topr_identical = release_ids == raw_topr_ids

    summary = pd.DataFrame(
        [
            {
                "gate": "DFT_outcome_scan",
                "status": "no_DFT_outcomes_detected",
                "n_rows": outcome_scan["existing_manifest_rows"],
                "blocks_primary_claim": False,
                "completed_positive_result": False,
                "reason": "Existing manifest has outcome_available=False and no DFT result files were detected before addendum construction.",
            },
            {
                "gate": "selection_integrity",
                "status": "selection_frozen_v4_unmodified_input",
                "n_rows": int(len(pd.read_csv(selection_path))),
                "blocks_primary_claim": False,
                "completed_positive_result": False,
                "reason": f"selection_frozen_v4_sha256={selection_hash}",
            },
            {
                "gate": "PARC_release_full_arm",
                "status": "pre_outcome_full_release_arm_exported",
                "n_rows": int(len(release_ids)),
                "blocks_primary_claim": False,
                "completed_positive_result": False,
                "reason": "Full formal PARC release arm exported for possible DFT if compute allows.",
            },
            {
                "gate": "raw_topR_matched_arm",
                "status": "exported_but_identical_to_full_release" if raw_topr_identical else "exported_distinct_matched_raw_prefix",
                "n_rows": int(len(raw_topr_ids)),
                "blocks_primary_claim": bool(raw_topr_identical),
                "completed_positive_result": False,
                "reason": "Matched raw_topR uses only frozen raw rank and public-label-free status; in this endpoint it is identical to the full PARC release set.",
            },
            {
                "gate": "raw_only_rejected_tail_arm",
                "status": "absent_no_raw_only_tail" if len(raw_only_ids) == 0 else "optional_stretch_exported",
                "n_rows": int(len(raw_only_ids)),
                "blocks_primary_claim": len(raw_only_ids) == 0,
                "completed_positive_result": False,
                "reason": "PARC released the full formal K=100 prefix, so no raw-only rejected-tail comparator is available." if len(raw_only_ids) == 0 else "Optional raw-only stretch arm exported before outcomes.",
            },
        ]
    )
    return addendum, summary


def update_docs() -> None:
    claim_path = ROOT / "docs" / "claim_table.md"
    claim_text = claim_path.read_text(encoding="utf-8")
    marker = "| A3-v4 Phase29b DFT comparator manifest addendum is frozen before outcomes but remains non-evidence. |"
    if marker not in claim_text:
        row = (
            marker
            + " `outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_addendum.csv`; "
            + "`table_phase29b_dft_manifest_addendum_summary.csv` | "
            + "`python scripts/build_a3_v4_dft_manifest_addendum.py` | "
            + "Addendum uses only frozen scores, ranks, release status and public-label exclusion status. "
            + "raw_topR is identical to the full PARC release set in this endpoint, raw-only tail is absent, and no DFT outcome is claimed. |\n"
        )
        claim_text = claim_text.replace("| Phase33 finalizes the NMI presubmission go/no-go package.", row + "| Phase33 finalizes the NMI presubmission go/no-go package.")
        claim_path.write_text(claim_text, encoding="utf-8")

    artifact_path = ROOT / "outputs" / "artifact_index.csv"
    artifact = pd.read_csv(artifact_path)
    if "mattergen_a3_v4_dft_manifest_addendum" not in set(artifact["milestone"].astype(str)):
        artifact.loc[len(artifact)] = {
            "milestone": "mattergen_a3_v4_dft_manifest_addendum",
            "path": "outputs/milestones/mattergen_parc_prospective_dft_followup/",
            "evidence_state": "completed_pre_DFT_manifest_addendum_not_positive_evidence",
            "manifest": "outputs/milestones/mattergen_parc_prospective_dft_followup/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/mattergen_parc_prospective_dft_followup",
        }
        artifact.to_csv(artifact_path, index=False)

    makefile = ROOT / "Makefile"
    make = makefile.read_text(encoding="utf-8")
    if "reproduce-a3-v4-dft-manifest-addendum" not in make:
        make = make.replace(
            "reproduce-a3-v4-formal-selection-gate:\n\t$(PYTHON) scripts/build_a3_v4_formal_selection_gate.py\n",
            "reproduce-a3-v4-formal-selection-gate:\n\t$(PYTHON) scripts/build_a3_v4_formal_selection_gate.py\n\n"
            "reproduce-a3-v4-dft-manifest-addendum:\n\t$(PYTHON) scripts/build_a3_v4_dft_manifest_addendum.py\n",
        )
        make = make.replace(
            "reproduce-a3-v4-formal-selection-gate",
            "reproduce-a3-v4-formal-selection-gate reproduce-a3-v4-dft-manifest-addendum",
            1,
        )
        makefile.write_text(make, encoding="utf-8")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    if "A3-v4 Phase29b manifest addendum" not in readme_text:
        readme_text += (
            "\n- A3-v4 Phase29b manifest addendum: a pre-outcome DFT manifest addendum exports the full PARC release arm "
            "and a matched raw_topR arm. The matched arm is identical to the release set here and no DFT outcome or positive prospective materials claim is made.\n"
        )
        readme.write_text(readme_text, encoding="utf-8")

    repro = ROOT / "REPRODUCIBILITY.md"
    repro_text = repro.read_text(encoding="utf-8")
    if "reproduce-a3-v4-dft-manifest-addendum" not in repro_text:
        repro_text += (
            "\n## A3-v4 DFT manifest addendum\n\n"
            "Run `make reproduce-a3-v4-dft-manifest-addendum` after the formal selection gate to rebuild the pre-outcome comparator manifest addendum. "
            "The addendum does not modify `selection_frozen_v4.csv` and is not completed DFT evidence.\n"
        )
        repro.write_text(repro_text, encoding="utf-8")


def main() -> None:
    addendum, summary = build_addendum()
    addendum.to_csv(OUT / "dft_job_manifest_v4_addendum.csv", index=False)
    summary.to_csv(OUT / "table_phase29b_dft_manifest_addendum_summary.csv", index=False)
    closeout = (
        "# A3-v4 Phase29b DFT Manifest Addendum Closeout\n\n"
        "Status: pre-outcome DFT comparator manifest addendum frozen. This is not DFT evidence.\n\n"
        "## What changed\n\n"
        "- `selection_frozen_v4.csv` was not modified.\n"
        "- `dft_job_manifest_v4_addendum.csv` exports the full PARC release arm and a matched raw_topR arm using only frozen scores, ranks, release status and public-label exclusion status.\n"
        "- The matched raw_topR arm is identical to the full PARC release set at this endpoint because PARC released the full formal K=100 prefix.\n"
        "- No raw-only rejected-tail arm is available; therefore the addendum cannot support a fixed-budget raw-vs-PARC utility claim.\n"
        "- No DFT outcomes were detected or used.\n\n"
        "## Claim scope\n\n"
        "The addendum is a pre-DFT manifest-control artifact. It may support transparent DFT execution logistics after the frozen tag, but it is not prospective materials discovery evidence and must not be promoted to a primary positive claim before DFT gates are met.\n"
    )
    (OUT / "A3_V4_DFT_MANIFEST_ADDENDUM_CLOSEOUT.md").write_text(closeout, encoding="utf-8")
    update_docs()
    write_manifest(OUT)
    write_root_manifest()


if __name__ == "__main__":
    main()
