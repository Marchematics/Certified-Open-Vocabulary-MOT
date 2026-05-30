#!/usr/bin/env python3
"""Build Phase87 minimal frozen claim registry for the B-line audit.

Phase87 ingests a small, frozen registry from two primary public claim surfaces:
Matbench Discovery/WBM and GNoME.  It does not query current references and
does not compute claim-decay metrics.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
PHASE86 = ROOT / "outputs/milestones/b_phase86_claim_decay_access_preflight"
WBM_SNAPSHOT = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_wbm_snapshot.csv"
OUT = ROOT / "outputs/milestones/b_phase87_minimal_claim_registry"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

GNOME_SUMMARY_URL = "https://storage.googleapis.com/gdm_materials_discovery/gnome_data/stable_materials_summary.csv"
GNOME_LICENSE_URL = "https://storage.googleapis.com/gdm_materials_discovery/LICENSE"

SCOPE = (
    "b_line_minimal_claim_registry;"
    "two_primary_sources;"
    "claim_registry_frozen;"
    "current_reference_verdicts_pending;"
    "not_completed_positive_evidence;"
    "not_A_paper_main_evidence;"
    "not_prospective_discovery;"
    "not_new_DFT_evidence"
)

REGISTRY_COLUMNS = [
    "claim_uid",
    "source_family",
    "paper_or_leaderboard_id",
    "source_snapshot_date",
    "original_rank_or_priority",
    "original_claim_text",
    "original_structure_hash",
    "structure_hash_basis",
    "reduced_formula",
    "chemical_system",
    "spacegroup_symbol",
    "spacegroup_number",
    "prototype_or_wyckoff_label",
    "original_energy_or_margin",
    "license_class",
    "redistribution_allowed",
    "ingest_status",
    "current_reference_query_ready",
    "query_readiness_note",
    "source_url_or_path",
    "evidence_scope",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


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


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def chem_system_from_formula_like(elements_text: str, fallback_formula: str) -> str:
    if elements_text and isinstance(elements_text, str):
        stripped = elements_text.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            parts = [
                part.strip(" '\"")
                for part in stripped.strip("[]").split(",")
                if part.strip(" '\"")
            ]
            if parts:
                return "-".join(sorted(parts))
        if "," in stripped:
            parts = [part.strip() for part in stripped.split(",") if part.strip()]
            if parts:
                return "-".join(sorted(parts))
    try:
        from pymatgen.core import Composition

        return "-".join(sorted(Composition(fallback_formula).chemical_system.split("-")))
    except Exception:
        return ""


def build_wbm_registry(n: int = 150) -> tuple[pd.DataFrame, dict[str, str]]:
    source_hash = sha256_file(WBM_SNAPSHOT)
    wbm = pd.read_csv(WBM_SNAPSHOT)
    stable = wbm[wbm["stable_exact_t0"].astype(bool)].head(n).copy()
    rows = []
    for rank, row in enumerate(stable.itertuples(index=False), start=1):
        material_id = str(row.material_id)
        formula = str(row.formula)
        wyckoff = str(row.wyckoff_spglib)
        hash_basis = "|".join(
            [
                "WBM_PUBLIC_SAFE_SNAPSHOT_PROXY",
                material_id,
                formula,
                wyckoff,
                str(row.e_above_hull_mp2020_corrected_ppd_mp),
            ]
        )
        rows.append(
            {
                "claim_uid": f"matbench_discovery_wbm::{material_id}",
                "source_family": "matbench_discovery_wbm",
                "paper_or_leaderboard_id": "Matbench_Discovery_WBM_public_safe_snapshot",
                "source_snapshot_date": "2023-12-13_wbm_summary_via_existing_public_safe_snapshot",
                "original_rank_or_priority": rank,
                "original_claim_text": "WBM stable_exact_t0 public DFT label; e_above_hull <= 0",
                "original_structure_hash": sha256_text(hash_basis),
                "structure_hash_basis": "proxy_hash_material_id_formula_wyckoff_ehull;raw_structure_not_redistributed",
                "reduced_formula": formula,
                "chemical_system": str(row.chemical_system),
                "spacegroup_symbol": "",
                "spacegroup_number": "",
                "prototype_or_wyckoff_label": wyckoff,
                "original_energy_or_margin": row.e_above_hull_mp2020_corrected_ppd_mp,
                "license_class": "CC-BY-4.0_source_claim;local_public_safe_derived_snapshot",
                "redistribution_allowed": "derived_registry_only",
                "ingest_status": "ingested_from_existing_public_safe_snapshot",
                "current_reference_query_ready": "formula_and_material_id_ready_structure_proxy_only",
                "query_readiness_note": "direct_figshare_download_blocked_in_current_environment; raw structure hash requires future structure-file ingest",
                "source_url_or_path": rel(WBM_SNAPSHOT),
                "evidence_scope": SCOPE,
            }
        )
    meta = {
        "source_rows_available": str(len(wbm)),
        "stable_rows_available": str(int(wbm["stable_exact_t0"].astype(bool).sum())),
        "source_sha256": source_hash,
    }
    return pd.DataFrame(rows, columns=REGISTRY_COLUMNS), meta


def iter_gnome_rows(n: int = 150) -> Iterable[dict[str, str]]:
    with requests.get(GNOME_SUMMARY_URL, stream=True, timeout=30) as response:
        response.raise_for_status()
        text_stream = io.TextIOWrapper(response.raw, encoding="utf-8", newline="")
        reader = csv.DictReader(text_stream)
        for idx, row in enumerate(reader):
            if idx >= n:
                break
            yield row


def build_gnome_registry(n: int = 150) -> tuple[pd.DataFrame, dict[str, str]]:
    rows = []
    for rank, row in enumerate(iter_gnome_rows(n), start=1):
        material_id = str(row.get("MaterialId", "")).strip()
        reduced_formula = str(row.get("Reduced Formula", "")).strip()
        composition = str(row.get("Composition", "")).strip()
        elements = str(row.get("Elements", "")).strip()
        sg_symbol = str(row.get("Space Group", "")).strip()
        sg_number = str(row.get("Space Group Number", "")).strip()
        data_dir = str(row.get("Data Directory", "")).strip()
        hash_basis = "|".join(
            [
                "GNOME_STABLE_MATERIALS_SUMMARY_RECORD",
                material_id,
                composition,
                reduced_formula,
                sg_symbol,
                sg_number,
                data_dir,
                str(row.get("Corrected Energy", "")).strip(),
                str(row.get("Decomposition Energy Per Atom", "")).strip(),
            ]
        )
        rows.append(
            {
                "claim_uid": f"gnome_public_stable_materials::{material_id}",
                "source_family": "gnome_public_stable_materials",
                "paper_or_leaderboard_id": "GNoME_stable_materials_summary",
                "source_snapshot_date": "public_bucket_stable_materials_summary_accessed_2026-05-31",
                "original_rank_or_priority": rank,
                "original_claim_text": "GNoME public stable-materials summary row",
                "original_structure_hash": sha256_text(hash_basis),
                "structure_hash_basis": "summary_record_hash;raw_structure_available_in_large_by_id_zip_not_ingested",
                "reduced_formula": reduced_formula,
                "chemical_system": chem_system_from_formula_like(elements, reduced_formula),
                "spacegroup_symbol": sg_symbol,
                "spacegroup_number": sg_number,
                "prototype_or_wyckoff_label": "",
                "original_energy_or_margin": row.get("Decomposition Energy Per Atom", ""),
                "license_class": "CC-BY-NC-4.0_data_terms",
                "redistribution_allowed": "derived_registry_only_no_raw_structure_redistribution",
                "ingest_status": "ingested_summary_row_raw_structure_pending",
                "current_reference_query_ready": "formula_material_id_and_summary_ready_structure_zip_pending",
                "query_readiness_note": "raw structure files not redistributed; by_id.zip ingest required for exact structure matching",
                "source_url_or_path": GNOME_SUMMARY_URL,
                "evidence_scope": SCOPE,
            }
        )
    meta = {
        "summary_url": GNOME_SUMMARY_URL,
        "rows_streamed": str(len(rows)),
        "license_url": GNOME_LICENSE_URL,
    }
    return pd.DataFrame(rows, columns=REGISTRY_COLUMNS), meta


def write_registry() -> pd.DataFrame:
    wbm, wbm_meta = build_wbm_registry()
    gnome, gnome_meta = build_gnome_registry()
    registry = pd.concat([wbm, gnome], ignore_index=True)
    registry.to_csv(OUT / "table_phase87_minimal_claim_registry.csv", index=False)

    summary_rows = []
    for source, frame, meta in [
        ("matbench_discovery_wbm", wbm, wbm_meta),
        ("gnome_public_stable_materials", gnome, gnome_meta),
    ]:
        summary_rows.append(
            {
                "source_family": source,
                "registry_rows": len(frame),
                "minimum_required_rows": 150,
                "meets_minimum_row_gate": len(frame) >= 150,
                "exact_raw_structure_hash_available": False,
                "hash_basis": ";".join(sorted(frame["structure_hash_basis"].unique())),
                "current_reference_query_ready": ";".join(sorted(frame["current_reference_query_ready"].unique())),
                "ingest_status": ";".join(sorted(frame["ingest_status"].unique())),
                "metadata": json.dumps(meta, sort_keys=True),
                "evidence_scope": SCOPE,
            }
        )
    pd.DataFrame(summary_rows).to_csv(OUT / "table_phase87_ingest_summary.csv", index=False)
    return registry


def write_query_manifest(registry: pd.DataFrame) -> None:
    rows = []
    for row in registry.itertuples(index=False):
        for ref in ["materials_project_current", "oqmd_current"]:
            rows.append(
                {
                    "query_uid": sha256_text(f"{row.claim_uid}|{ref}")[:16],
                    "claim_uid": row.claim_uid,
                    "reference_source": ref,
                    "reference_version": "MP_2025.09.25" if ref == "materials_project_current" else "OQMD_current_version_pending",
                    "query_date": "pending_phase88",
                    "query_method": "formula_or_id_prefilter_then_structure_match_when_raw_structure_available",
                    "matched_entry_ids": "",
                    "match_status": "not_queried_phase87",
                    "current_stability_verdict": "",
                    "current_e_above_hull_mev_atom": "",
                    "ambiguity_status": "pending",
                    "evidence_scope": SCOPE,
                }
            )
    pd.DataFrame(rows).to_csv(OUT / "table_phase87_current_reference_query_manifest.csv", index=False)


def write_gate_and_docs(registry: pd.DataFrame) -> None:
    summary = pd.read_csv(OUT / "table_phase87_ingest_summary.csv")
    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase87_minimal_claim_registry",
                "status": "minimal_registry_frozen_current_reference_verdicts_pending",
                "positive_evidence": "no",
                "total_registry_rows": len(registry),
                "primary_sources_meeting_row_gate": int(summary["meets_minimum_row_gate"].sum()),
                "exact_raw_structure_hash_available_all_sources": False,
                "allowed_current_claim": "Phase87 freezes a two-source minimal external AI-materials claim registry before current-reference verdicts.",
                "forbidden_current_claim": "Do not claim claim decay, current-reference instability, exact structure matching completeness, legal redistribution of raw structures, A-paper evidence, prospective discovery, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase87_claim_gate.csv", index=False)

    readme = f"""# Phase87 Minimal Claim Registry

Status: `minimal_registry_frozen_current_reference_verdicts_pending`.

Phase87 freezes a two-source minimal B-line claim registry:

- Matbench Discovery / WBM rows: {int((registry['source_family'] == 'matbench_discovery_wbm').sum())}
- GNoME public stable-materials rows: {int((registry['source_family'] == 'gnome_public_stable_materials').sum())}

This artifact does not query current references and does not compute claim
decay.  The registry uses derived/proxy hashes rather than redistributing raw
third-party structures.  Exact structure matching requires a later raw
structure ingest step where permitted.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase87 Minimal Claim Registry Protocol

Allowed current output:

- frozen two-source minimal claim registry;
- source-level ingest summary;
- current-reference query manifest with pending verdicts.

Forbidden current output:

- SCDR, TDB@100, EDMB, CAR, or any claim-decay metric;
- claim that public AI materials claims fail current references;
- exact structure matching completeness;
- redistribution of raw structures from third-party sources;
- A-paper main evidence;
- prospective discovery or new DFT evidence.

Next step:

Phase88 may query current MP/OQMD references using the frozen registry.  It
must not alter Phase87 claim ontology after seeing current-reference verdicts.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "PHASE87_MINIMAL_CLAIM_REGISTRY_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def upsert_artifact_index() -> None:
    row = {
        "milestone": "b_phase87_minimal_claim_registry",
        "path": rel(OUT) + "/",
        "evidence_state": "minimal_registry_frozen_current_reference_verdicts_pending_not_positive_evidence",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase87_minimal_claim_registry",
    }
    index = pd.read_csv(ROOT / "outputs/artifact_index.csv")
    index = index[index["milestone"] != row["milestone"]]
    index = pd.concat([index, pd.DataFrame([row])[index.columns]], ignore_index=True)
    index.to_csv(ROOT / "outputs/artifact_index.csv", index=False)


def upsert_ledger() -> None:
    row = {
        "claim_id": "B-PHASE87-MINIMAL-REGISTRY-001",
        "claim_text": "Phase87 freezes a two-source minimal external AI-materials claim registry before current-reference verdicts are produced.",
        "evidence_type": "external_claim_registry",
        "positive_evidence": "no",
        "scope": "minimal_registry_frozen;current_reference_verdicts_pending;not_A_paper_main_evidence",
        "artifact_path": rel(OUT / "table_phase87_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_phase87_claim_gate.csv"),
        "validation_command": "make reproduce-b-phase87-minimal-claim-registry",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_decay_current_reference_instability_exact_structure_matching_completeness_A_paper_evidence_prospective_discovery_or_new_DFT",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase87 Minimal External Claim Registry\n\nStatus: `minimal_registry_frozen_current_reference_verdicts_pending`.\n\nPhase87 freezes a two-source B-line claim registry for Matbench Discovery/WBM\nand GNoME public stable-materials rows.  Current status is registry only: no\ncurrent-reference verdicts have been produced, exact raw-structure matching is\nnot complete, and no claim-decay result is allowed.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase87 Minimal External Claim Registry"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not PHASE86.exists():
        raise FileNotFoundError(f"Phase86 preflight missing: {PHASE86}")
    registry = write_registry()
    write_query_manifest(registry)
    write_gate_and_docs(registry)
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase87] wrote {OUT.relative_to(ROOT)}")
    print("[phase87] status=minimal_registry_frozen_current_reference_verdicts_pending")


if __name__ == "__main__":
    main()
