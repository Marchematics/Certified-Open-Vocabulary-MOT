#!/usr/bin/env python3
"""Parse a private MatterGen smoke-generation run into public-safe metadata.

This script records that MatterGen produced real candidate structures without
publishing the raw CIF/EXTXYZ files.  It intentionally stops before
public-label exclusion, CHGNet/MACE scoring, PARC selection, or DFT job export.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


DEFAULT_OUT = Path("outputs/milestones/mattergen_parc_prospective_dft_followup")

RAW_CANDIDATE_COLUMNS = [
    "candidate_id",
    "generator",
    "generator_mode",
    "formula",
    "reduced_formula",
    "chemical_system",
    "anonymous_formula",
    "n_sites",
    "space_group",
    "structure_ref",
    "structure_sha256",
    "generation_rank",
    "generation_status",
]

PUBLIC_FREE_COLUMNS = RAW_CANDIDATE_COLUMNS + [
    "public_label_status",
    "public_label_sources_checked",
    "structure_match_status",
    "eligible_for_A3_v4",
]

SCORE_COLUMNS = [
    "candidate_id",
    "formula",
    "structure_ref",
    "structure_sha256",
    "score_model",
    "score_model_version",
    "score_status",
    "energy_per_atom",
    "formation_energy_proxy",
    "predicted_e_above_hull_proxy",
    "score",
    "raw_rank",
]

CONSENSUS_COLUMNS = [
    "candidate_id",
    "formula",
    "structure_ref",
    "structure_sha256",
    "chgnet_score",
    "mace_score",
    "consensus_score",
    "consensus_rule",
    "score_status",
    "raw_rank",
]

SELECTION_COLUMNS = [
    "arm",
    "candidate_id",
    "selected_for_dft",
    "dft_job_id",
    "selection_rank",
    "endpoint_id",
    "selection_rule",
    "score_rank",
    "parc_release_flag",
    "raw_topK_member",
    "reserve_order",
    "evidence_status",
    "primary_or_reserve",
    "frozen_model_score",
    "structure_ref",
    "structure_sha256",
]

DFT_JOB_COLUMNS = [
    "dft_job_id",
    "candidate_id",
    "arm",
    "endpoint_id",
    "structure_ref",
    "structure_sha256",
    "dft_engine",
    "input_status",
    "failure_policy",
    "selected_before_DFT_outcome",
    "outcome_available",
    "outcome_file",
    "evidence_status",
]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def empty_csv(path: Path, columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)


def private_ref(stage: str, member: str) -> str:
    return f"private_mattergen_{stage}::generated_crystals_cif.zip::{member}"


def parse_cif_member(stage: str, name: str, payload: bytes, rank: int) -> tuple[dict[str, object] | None, str]:
    try:
        text = payload.decode("utf-8")
        structure = Structure.from_str(text, fmt="cif")
    except Exception as exc:  # pragma: no cover - exercised by real generation failures
        return None, f"{type(exc).__name__}: {exc}"

    composition = structure.composition
    try:
        space_group = SpacegroupAnalyzer(structure, symprec=0.1).get_space_group_symbol()
    except Exception:
        space_group = "unresolved"
    elements = sorted(str(element) for element in composition.elements)
    row = {
        "candidate_id": f"mattergen_{stage}_{rank:05d}",
        "generator": "MatterGen",
        "generator_mode": "mattergen_base_unconditional_smoke",
        "formula": composition.formula,
        "reduced_formula": composition.reduced_formula,
        "chemical_system": "-".join(elements),
        "anonymous_formula": composition.anonymized_formula,
        "n_sites": len(structure),
        "space_group": space_group,
        "structure_ref": private_ref(stage, name),
        "structure_sha256": sha256_bytes(payload),
        "generation_rank": rank,
        "generation_status": "pymatgen_readable_smoke_candidate",
    }
    return row, "ok"


def update_freeze_status(root: Path, n_rows: int) -> None:
    pd.DataFrame(
        [
            {
                "gate": "candidate_generation",
                "required_for_dft": True,
                "status": "completed_smoke_generation_only",
                "n_rows": n_rows,
                "completed_positive_result": False,
            },
            {
                "gate": "public_label_exclusion",
                "required_for_dft": True,
                "status": "blocked_smoke_candidates_not_public_label_filtered",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "consensus_scoring",
                "required_for_dft": True,
                "status": "blocked_no_public_label_free_pool",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "PARC_release_selection",
                "required_for_dft": True,
                "status": "blocked_no_consensus_scores",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "DFT_manifest",
                "required_for_dft": True,
                "status": "blocked_no_frozen_selection",
                "n_rows": 0,
                "completed_positive_result": False,
            },
        ]
    ).to_csv(root / "table_v4_freeze_status.csv", index=False)

    go = pd.read_csv(root / "table_v4_go_no_go.csv")
    go["status"] = "not_evaluated_smoke_generation_only"
    go["released"] = 0
    go["raw_only_tail"] = 0
    go["dft_jobs_exported"] = 0
    go["completed_positive_result"] = False
    go.to_csv(root / "table_v4_go_no_go.csv", index=False)


def update_closeout(root: Path, n_rows: int, parse_failed: int) -> None:
    closeout = f"""# MatterGen--PARC A3-v4 Closeout

Status: protocol/environment gate plus MatterGen smoke-generation gate. No
public-label-free candidate universe, no consensus scoring, no PARC selection,
no DFT job manifest and no DFT outcomes are included.

## Completed gate

- MatterGen generated a 100-candidate smoke batch in the private generation
  workspace.
- `{n_rows}` candidates were pymatgen-readable and recorded as public-safe
  metadata in `raw_mattergen_candidates.csv`.
- `{parse_failed}` generated CIF members failed parsing.
- Raw CIF/EXTXYZ files are not included in the public-safe bundle; only
  candidate metadata, private references and structure SHA-256 hashes are
  recorded.

## Interpretation

This is not a prospective positive result. It only shows that MatterGen
candidate generation can produce real structures in the local environment. The
A3-v4 trial advances beyond this gate only after public-label exclusion,
CHGNet/MACE consensus scoring, and a nonempty PARC release selection are frozen
before any DFT outcomes.
"""
    (root / "A3_V4_MATTERGEN_PARC_DFT_CLOSEOUT.md").write_text(closeout, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-dir", required=True)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--stage", default="smoke_100")
    parser.add_argument("--requested-candidates", type=int, default=100)
    parser.add_argument("--pretrained-name", default="mattergen_base")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--num-batches", type=int, default=5)
    args = parser.parse_args()

    generation_dir = Path(args.generation_dir)
    root = Path(args.out_dir)
    root.mkdir(parents=True, exist_ok=True)
    zip_path = generation_dir / "generated_crystals_cif.zip"
    extxyz_path = generation_dir / "generated_crystals.extxyz"
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing MatterGen CIF zip: {zip_path}")

    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    with ZipFile(zip_path) as archive:
        members = sorted(name for name in archive.namelist() if name.endswith(".cif"))
        for rank, name in enumerate(members):
            payload = archive.read(name)
            row, status = parse_cif_member(args.stage, name, payload, rank)
            if row is None:
                failures.append({"member": name, "status": status})
            else:
                rows.append(row)

    pd.DataFrame(rows, columns=RAW_CANDIDATE_COLUMNS).to_csv(
        root / "raw_mattergen_candidates.csv", index=False
    )
    empty_csv(root / "candidate_universe_public_label_free.csv", PUBLIC_FREE_COLUMNS)
    empty_csv(root / "candidate_scores_chgnet.csv", SCORE_COLUMNS)
    empty_csv(root / "candidate_scores_mace.csv", SCORE_COLUMNS)
    empty_csv(root / "candidate_scores_consensus.csv", CONSENSUS_COLUMNS)
    empty_csv(root / "selection_frozen_v4.csv", SELECTION_COLUMNS)
    empty_csv(root / "dft_job_manifest_v4.csv", DFT_JOB_COLUMNS)

    generation_status = "completed_smoke_generation_only"
    pd.DataFrame(
        [
            {
                "stage": args.stage,
                "generator": "MatterGen",
                "pretrained_name": args.pretrained_name,
                "generator_mode": "unconditional_smoke",
                "requested_candidates": args.requested_candidates,
                "batch_size": args.batch_size,
                "num_batches": args.num_batches,
                "private_output_ref": f"<PRIVATE_MATTERGEN_GENERATION_DIR>/{args.stage}",
                "generated_cif_zip_present": zip_path.exists(),
                "generated_extxyz_present": extxyz_path.exists(),
                "generated_cif_zip_sha256": sha256_file(zip_path),
                "generated_extxyz_sha256": sha256_file(extxyz_path) if extxyz_path.exists() else "",
                "public_artifact_scope": "metadata_and_hashes_only_no_raw_structures",
                "status": generation_status,
            }
        ]
    ).to_csv(root / "mattergen_generation_manifest.csv", index=False)

    pd.DataFrame(
        [
            {
                "stage": args.stage,
                "requested_candidates": args.requested_candidates,
                "cif_members": len(rows) + len(failures),
                "pymatgen_readable": len(rows),
                "parse_failed": len(failures),
                "valid_fraction": len(rows) / max(1, len(rows) + len(failures)),
                "status": generation_status,
            }
        ]
    ).to_csv(root / "mattergen_candidate_parse_report.csv", index=False)

    unique_hashes = len({str(row["structure_sha256"]) for row in rows})
    unique_formulas = len({str(row["reduced_formula"]) for row in rows})
    unique_systems = len({str(row["chemical_system"]) for row in rows})
    pd.DataFrame(
        [
            {
                "stage": args.stage,
                "parsed_candidates": len(rows),
                "unique_structure_hashes": unique_hashes,
                "duplicate_structure_hashes": len(rows) - unique_hashes,
                "unique_reduced_formulas": unique_formulas,
                "unique_chemical_systems": unique_systems,
                "dedup_scope": "hash_metadata_only_not_structurematcher_public_label_filter",
                "status": "smoke_dedup_metadata_only",
            }
        ]
    ).to_csv(root / "mattergen_candidate_dedup_report.csv", index=False)

    (root / "mattergen_generation_environment.json").write_text(
        json.dumps(
            {
                "stage": args.stage,
                "generator": "MatterGen",
                "pretrained_name": args.pretrained_name,
                "sampling_config_source": "official_mattergen_repo_sampling_conf",
                "private_generation_dir": "<PRIVATE_MATTERGEN_GENERATION_DIR>",
                "public_artifact_scope": "metadata_and_hashes_only",
                "raw_structures_committed": False,
                "public_label_exclusion_completed": False,
                "consensus_scoring_completed": False,
                "parc_selection_completed": False,
                "dft_manifest_exported": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    update_freeze_status(root, len(rows))
    update_closeout(root, len(rows), len(failures))
    write_manifest(root)


if __name__ == "__main__":
    main()
