#!/usr/bin/env python3
"""Build Phase90 GNoME raw-structure ingest artifacts for B.

This phase consumes the local GNoME `by_id.zip` cache prepared in Phase89,
extracts only derived metadata for the frozen 150-row claim registry, and
does not write raw CIF structures to tracked artifacts.

It is deliberately not a claim-decay result: no current Materials Project
verdicts are queried and no exact/near-exact MP matching is performed here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from pymatgen.core import Structure


ROOT = Path(__file__).resolve().parents[1]
PHASE87 = ROOT / "outputs/milestones/b_phase87_minimal_claim_registry"
PHASE89 = ROOT / "outputs/milestones/b_phase89_exact_structure_audit_readiness"
OUT = ROOT / "outputs/milestones/b_phase90_gnome_raw_structure_ingest"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"
GNOME_ZIP = ROOT / "cache/b_phase89/gnome/by_id.zip"

SCOPE = (
    "b_line_gnome_raw_structure_ingest;"
    "derived_metadata_only;"
    "raw_cif_not_versioned;"
    "exact_matching_pending;"
    "current_reference_verdicts_pending;"
    "not_claim_decay_evidence;"
    "not_A_paper_main_evidence;"
    "not_prospective_discovery;"
    "not_new_DFT_evidence"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def load_gnome_registry() -> pd.DataFrame:
    registry = pd.read_csv(PHASE87 / "table_phase87_minimal_claim_registry.csv")
    gnome = registry[registry["source_family"].eq("gnome_public_stable_materials")].copy()
    gnome["material_id"] = gnome["claim_uid"].astype(str).str.split("::").str[-1]
    return gnome


def structure_row(row: pd.Series, archive: ZipFile, names: set[str]) -> dict[str, object]:
    material_id = str(row["material_id"])
    member = f"by_id/{material_id}.CIF"
    base = {
        "claim_uid": row["claim_uid"],
        "material_id": material_id,
        "zip_member": member,
        "raw_cif_present_in_local_cache": member in names,
        "raw_cif_sha256": "",
        "parse_status": "missing_from_local_cache",
        "pymatgen_reduced_formula": "",
        "pymatgen_chemical_system": "",
        "pymatgen_n_sites": "",
        "pymatgen_volume": "",
        "registry_reduced_formula": row.get("reduced_formula", ""),
        "registry_chemical_system": row.get("chemical_system", ""),
        "formula_consistency": "not_checked",
        "evidence_scope": SCOPE,
    }
    if member not in names:
        return base

    data = archive.read(member)
    base["raw_cif_sha256"] = sha256_bytes(data)
    try:
        structure = Structure.from_str(data.decode("utf-8"), fmt="cif")
    except Exception as exc:  # pragma: no cover - recorded in artifact
        base["parse_status"] = f"parse_failed:{type(exc).__name__}"
        return base

    reduced = structure.composition.reduced_formula
    chem_system = "-".join(sorted(element.symbol for element in structure.composition.elements))
    base.update(
        {
            "parse_status": "parsed",
            "pymatgen_reduced_formula": reduced,
            "pymatgen_chemical_system": chem_system,
            "pymatgen_n_sites": int(len(structure)),
            "pymatgen_volume": float(structure.volume),
            "formula_consistency": (
                "matches_registry_formula"
                if str(row.get("reduced_formula", "")).replace(" ", "") == reduced
                else "registry_formula_not_identical_or_unavailable"
            ),
        }
    )
    return base


def write_ingest_tables() -> pd.DataFrame:
    if not GNOME_ZIP.exists():
        raise FileNotFoundError(f"missing GNoME raw structure cache: {rel(GNOME_ZIP)}")

    gnome = load_gnome_registry()
    with ZipFile(GNOME_ZIP) as archive:
        names = set(archive.namelist())
        rows = [structure_row(row, archive, names) for _, row in gnome.iterrows()]

    table = pd.DataFrame(rows)
    table.to_csv(OUT / "table_phase90_gnome_raw_structure_ingest.csv", index=False)

    summary = pd.DataFrame(
        [
            {
                "source_family": "gnome_public_stable_materials",
                "registry_rows": int(len(table)),
                "raw_cif_present_rows": int(table["raw_cif_present_in_local_cache"].astype(bool).sum()),
                "parsed_rows": int(table["parse_status"].eq("parsed").sum()),
                "unique_chemical_systems": int(table.loc[table["parse_status"].eq("parsed"), "pymatgen_chemical_system"].nunique()),
                "raw_cif_committed_to_git": False,
                "current_reference_verdicts_available": False,
                "exact_structure_matching_completed": False,
                "claim_status": "derived_structure_ingest_completed_current_verdicts_pending",
                "evidence_scope": SCOPE,
            }
        ]
    )
    summary.to_csv(OUT / "table_phase90_gnome_ingest_summary.csv", index=False)

    next_steps = pd.DataFrame(
        [
            {
                "step": "mp_formula_prefilter",
                "input": "table_phase90_gnome_raw_structure_ingest.csv",
                "output": "candidate MP current-reference structures by chemical system/formula",
                "status": "pending",
                "guardrail": "do_not_query_or_report current-reference verdicts in Phase90",
            },
            {
                "step": "structure_matcher_exact_or_near_exact",
                "input": "raw GNoME structures from local cache plus MP candidate structures",
                "output": "exact_match / near_match / ambiguous / no_match adjudication",
                "status": "pending",
                "guardrail": "formula-only links cannot count as exact claim decay",
            },
            {
                "step": "current_reference_claim_decay_metrics",
                "input": "adjudicated exact/near-exact rows only",
                "output": "SCDR/TDB/EDMB/CAR metrics if coverage gates pass",
                "status": "pending",
                "guardrail": "no source-level decay claim until matching and verdict gates pass",
            },
        ]
    )
    next_steps.to_csv(OUT / "table_phase90_next_match_steps.csv", index=False)
    return table


def write_docs(table: pd.DataFrame) -> None:
    parsed = int(table["parse_status"].eq("parsed").sum())
    present = int(table["raw_cif_present_in_local_cache"].astype(bool).sum())
    readme = f"""# Phase90 GNoME Raw-Structure Ingest

Status: `derived_structure_ingest_completed_current_verdicts_pending`.

Phase90 reads the local GNoME `by_id.zip` cache and extracts only derived,
public-safe structure metadata for the frozen B-line 150-row GNoME registry.
It does not write raw CIF files into git-tracked artifacts.

Summary:

- registry rows: `{len(table)}`;
- raw CIF members present in local cache: `{present}`;
- pymatgen-parsed structures: `{parsed}`;
- current-reference verdicts: pending;
- exact MP structure matching: pending.

Allowed current claim:

Phase90 completes derived raw-structure ingest for the frozen GNoME registry and
prepares the next exact-matching stage.

This is not claim-decay evidence.

Forbidden current claims:

- completed exact-structure matching;
- source-level claim decay;
- GNoME current-reference instability;
- A-paper evidence;
- prospective discovery;
- new DFT evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase90 Protocol: GNoME Raw-Structure Ingest

Inputs:

- frozen registry: `{rel(PHASE87 / 'table_phase87_minimal_claim_registry.csv')}`;
- raw cache outside version control: `{rel(GNOME_ZIP)}`;
- Phase89 readiness plan: `{rel(PHASE89 / 'table_phase89_exact_match_execution_plan.csv')}`.

Procedure:

1. Select only `gnome_public_stable_materials` rows from the frozen registry.
2. For each material ID, read `by_id/<material_id>.CIF` from the local zip.
3. Hash the raw CIF bytes and parse with pymatgen.
4. Write only derived metadata and hashes.
5. Do not query Materials Project current-reference labels in this phase.

This phase is a necessary ingest step for B-line exact-structure claim-decay
auditing, but it is not claim-decay evidence.
"""
    (OUT / "PHASE90_GNOME_RAW_STRUCTURE_INGEST_PROTOCOL.md").write_text(protocol, encoding="utf-8")

    gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase90_gnome_raw_structure_ingest",
                "status": "derived_structure_ingest_completed_current_verdicts_pending",
                "positive_evidence": "no",
                "allowed_current_claim": "Phase90 completes public-safe derived GNoME raw-structure ingest for the frozen B-line registry.",
                "forbidden_current_claim": "Do not claim completed exact matching, claim decay, current-reference instability, A-paper evidence, prospective discovery, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase90_claim_gate.csv", index=False)


def update_artifact_index() -> None:
    row = {
        "milestone": "b_phase90_gnome_raw_structure_ingest",
        "path": "outputs/milestones/b_phase90_gnome_raw_structure_ingest/",
        "evidence_state": "derived_structure_ingest_completed_current_verdicts_pending",
        "manifest": "outputs/milestones/b_phase90_gnome_raw_structure_ingest/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase90_gnome_raw_structure_ingest",
        "notes": "B-line GNoME derived raw-structure ingest; no exact matching or decay claim.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "B-PHASE90-GNOME-STRUCTURE-INGEST-001",
        "claim_text": "Phase90 completes derived raw-structure ingest for frozen GNoME registry rows without current-reference verdicts.",
        "evidence_type": "derived_ingest_artifact",
        "positive_evidence": "no",
        "scope": "derived_metadata_only;current_verdicts_pending;not_exact_decay",
        "artifact_path": "outputs/milestones/b_phase90_gnome_raw_structure_ingest/table_phase90_gnome_ingest_summary.csv",
        "hash": sha256_file(OUT / "table_phase90_gnome_ingest_summary.csv"),
        "validation_command": "make reproduce-b-phase90-gnome-raw-structure-ingest",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_completed_exact_matching_or_decay",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase90 B-Line GNoME Raw-Structure Ingest\n\nStatus: `derived_structure_ingest_completed_current_verdicts_pending`.\n\nPhase90 completes public-safe derived raw-structure ingest for the frozen\nGNoME registry rows by reading the local `by_id.zip` cache, hashing raw CIF\nbytes, and extracting pymatgen structure metadata. Raw CIF files remain outside\ngit-tracked artifacts. Exact MP matching and current-reference verdicts remain\npending, so Phase90 is not claim-decay evidence.\n"""
    marker = "## Phase90 B-Line GNoME Raw-Structure Ingest"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        text = before + "\n" + section + (after[next_idx:] if next_idx >= 0 else "")
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    if not PHASE87.exists() or not PHASE89.exists():
        raise FileNotFoundError("Phase87 and Phase89 artifacts are required")
    OUT.mkdir(parents=True, exist_ok=True)
    table = write_ingest_tables()
    write_docs(table)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    print(f"[phase90-b] wrote {rel(OUT)}")
    print("[phase90-b] status=derived_structure_ingest_completed_current_verdicts_pending")


if __name__ == "__main__":
    main()
