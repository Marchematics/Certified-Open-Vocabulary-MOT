#!/usr/bin/env python3
"""Run Phase86 access preflight for the B-line claim-decay audit.

Phase86 is a light preflight: dependency inventory, source endpoint smoke
checks, Materials Project version capture when an API key is available, and
empty claim/current-reference registry templates.  It does not ingest claim
rows and does not compute any claim-decay metric.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE85 = ROOT / "outputs/milestones/b_phase85_external_ai_materials_claim_decay_pilot"
OUT = ROOT / "outputs/milestones/b_phase86_claim_decay_access_preflight"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "b_line_claim_decay_access_preflight;"
    "source_access_smoke_only;"
    "claim_registry_empty;"
    "current_reference_verdicts_pending;"
    "not_completed_positive_evidence;"
    "not_A_paper_main_evidence;"
    "not_prospective_discovery;"
    "not_new_DFT_evidence"
)

ENDPOINTS = [
    {
        "source_id": "matbench_discovery_wbm",
        "endpoint_role": "project_page",
        "url": "https://matbench-discovery.materialsproject.org/",
    },
    {
        "source_id": "gnome_public_stable_materials",
        "endpoint_role": "public_repository",
        "url": "https://github.com/google-deepmind/materials_discovery",
    },
    {
        "source_id": "alexandria_hull_or_claim_surface",
        "endpoint_role": "project_page",
        "url": "https://alexandria.icams.rub.de/",
    },
    {
        "source_id": "materials_project_current",
        "endpoint_role": "api_docs",
        "url": "https://api.materialsproject.org/docs",
    },
    {
        "source_id": "oqmd_current",
        "endpoint_role": "project_page",
        "url": "https://oqmd.org/",
    },
]

CLAIM_REGISTRY_COLUMNS = [
    "claim_uid",
    "source_family",
    "paper_or_leaderboard_id",
    "source_snapshot_date",
    "original_rank_or_priority",
    "original_claim_text",
    "original_structure_hash",
    "reduced_formula",
    "chemical_system",
    "spacegroup_symbol",
    "prototype_or_wyckoff_label",
    "license_class",
    "redistribution_allowed",
    "ingest_status",
    "evidence_scope",
]

CURRENT_REFERENCE_COLUMNS = [
    "query_uid",
    "claim_uid",
    "reference_source",
    "reference_version",
    "query_date",
    "query_method",
    "matched_entry_ids",
    "match_status",
    "current_stability_verdict",
    "current_e_above_hull_mev_atom",
    "ambiguity_status",
    "evidence_scope",
]


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


def dependency_inventory() -> pd.DataFrame:
    rows = []
    for module in ["requests", "pymatgen", "mp_api", "ase", "pandas"]:
        rows.append(
            {
                "dependency": module,
                "available": importlib.util.find_spec(module) is not None,
                "required_for": {
                    "requests": "endpoint_smoke_checks",
                    "pymatgen": "future_structure_canonicalization",
                    "mp_api": "materials_project_version_and_queries",
                    "ase": "future_structure_io",
                    "pandas": "registry_tables",
                }[module],
                "evidence_scope": SCOPE,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "table_phase86_local_dependency_status.csv", index=False)
    return df


def endpoint_smoke_checks() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    try:
        import requests
    except Exception as exc:  # pragma: no cover - defensive path
        requests = None
        import_error = repr(exc)
    else:
        import_error = ""

    for item in ENDPOINTS:
        row: dict[str, Any] = {
            **item,
            "check_type": "http_head_then_get_fallback",
            "status": "not_run",
            "http_status": "",
            "error_type": "",
            "note": "",
            "evidence_scope": SCOPE,
        }
        if requests is None:
            row.update({"status": "blocked_missing_requests", "error_type": import_error})
            rows.append(row)
            continue
        try:
            response = requests.head(item["url"], timeout=8, allow_redirects=True)
            if response.status_code >= 400 or response.status_code == 405:
                response = requests.get(item["url"], timeout=8, stream=True)
            row["http_status"] = response.status_code
            row["status"] = "reachable" if response.status_code < 400 else "http_error"
            row["note"] = "source reachability smoke only; not data license approval"
        except Exception as exc:  # network failure is recorded, not fatal
            row["status"] = "blocked_or_unreachable"
            row["error_type"] = exc.__class__.__name__
            row["note"] = "network/API smoke failed; do not infer source unusability without retry"
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "table_phase86_source_access_smoke.csv", index=False)
    return df


def mp_version_status() -> pd.DataFrame:
    row = {
        "reference_source": "materials_project_current",
        "api_key_present": bool(os.environ.get("MP_API_KEY")),
        "database_version": "",
        "status": "not_run",
        "error_type": "",
        "note": "API key value is never written to artifacts",
        "evidence_scope": SCOPE,
    }
    if not row["api_key_present"]:
        row["status"] = "blocked_missing_MP_API_KEY"
    else:
        try:
            from mp_api.client import MPRester

            with MPRester(os.environ["MP_API_KEY"]) as mpr:
                version = mpr.get_database_version()
            row["database_version"] = str(version)
            row["status"] = "version_captured"
        except Exception as exc:
            row["status"] = "version_query_failed"
            row["error_type"] = exc.__class__.__name__
            row["note"] = "MP version query failed; retry before current-reference audit"
    df = pd.DataFrame([row])
    df.to_csv(OUT / "table_phase86_mp_version_status.csv", index=False)
    return df


def write_templates() -> None:
    pd.DataFrame(columns=CLAIM_REGISTRY_COLUMNS).to_csv(OUT / "claim_registry_template.csv", index=False)
    pd.DataFrame(columns=CURRENT_REFERENCE_COLUMNS).to_csv(OUT / "current_reference_query_manifest_template.csv", index=False)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Phase86 claim registry row schema",
        "type": "object",
        "required": [
            "claim_uid",
            "source_family",
            "source_snapshot_date",
            "original_claim_text",
            "original_structure_hash",
            "reduced_formula",
            "ingest_status",
        ],
        "properties": {
            "claim_uid": {"type": "string"},
            "source_family": {
                "type": "string",
                "enum": [
                    "matbench_discovery_wbm",
                    "gnome_public_stable_materials",
                    "alexandria_hull_or_claim_surface",
                ],
            },
            "original_claim_text": {"type": "string"},
            "original_structure_hash": {"type": "string"},
            "redistribution_allowed": {"type": ["boolean", "string"]},
            "ingest_status": {
                "type": "string",
                "enum": ["pending", "ingested", "blocked_license", "blocked_access", "ambiguous"],
            },
        },
        "additionalProperties": True,
    }
    (OUT / "claim_registry_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")


def write_plan_and_claim_gate() -> None:
    plan = pd.DataFrame(
        [
            {
                "step": 1,
                "action": "confirm source access and terms",
                "input": "table_phase86_source_access_smoke.csv",
                "output": "source-specific ingest decision",
                "status": "preflight_only",
                "evidence_scope": SCOPE,
            },
            {
                "step": 2,
                "action": "build frozen claim registry from public source IDs and structure hashes",
                "input": "claim_registry_template.csv",
                "output": "future_claim_registry.csv",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
            {
                "step": 3,
                "action": "query current references without changing claim ontology",
                "input": "current_reference_query_manifest_template.csv",
                "output": "future_current_reference_verdicts.csv",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
            {
                "step": 4,
                "action": "compute SCDR TDB EDMB and CAR gates",
                "input": "future_current_reference_verdicts.csv",
                "output": "future_phase87_gate_decision",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
        ]
    )
    plan.to_csv(OUT / "table_phase86_ingest_preflight_plan.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase86_claim_decay_access_preflight",
                "status": "access_preflight_completed_claim_registry_empty",
                "positive_evidence": "no",
                "allowed_current_claim": "Phase86 records source access/dependency preflight and empty registry templates for the B-line claim-decay audit.",
                "forbidden_current_claim": "Do not claim source decay, current-reference instability, successful ingestion, legal redistribution approval, PARC validation, A-paper evidence, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase86_claim_gate.csv", index=False)


def write_docs(access: pd.DataFrame, mp_status: pd.DataFrame) -> None:
    reachable_n = int(access["status"].eq("reachable").sum())
    mp_status_value = str(mp_status.iloc[0]["status"])
    readme = f"""# Phase86 Claim-Decay Access Preflight

Status: `access_preflight_completed_claim_registry_empty`.

Phase86 checks whether the frozen Phase85 B-line sources are reachable and
whether local dependencies for claim-registry construction are present.  It
does not ingest claims and does not compute any current-reference verdict.

Endpoint smoke summary:

- reachable endpoints: {reachable_n} / {len(access)}
- Materials Project version status: `{mp_status_value}`

No API key, raw third-party structure file, or current-reference verdict is
published by this artifact.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase86 Access Preflight Protocol

Phase86 follows Phase85 and precedes any claim-decay computation.

Allowed outputs:

- source endpoint reachability smoke;
- local dependency inventory;
- Materials Project database version if query succeeds;
- empty claim-registry and current-reference query templates;
- ingest preflight plan.

Forbidden outputs:

- SCDR, TDB@100, EDMB, CAR or any source-specific claim-decay result;
- statement that a source's public AI claims fail current references;
- legal approval to redistribute third-party raw structures;
- A-paper main evidence;
- new DFT evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "PHASE86_ACCESS_PREFLIGHT_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def upsert_artifact_index() -> None:
    row = {
        "milestone": "b_phase86_claim_decay_access_preflight",
        "path": rel(OUT) + "/",
        "evidence_state": "access_preflight_completed_claim_registry_empty_not_positive_evidence",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase86_claim_decay_access_preflight",
    }
    index = pd.read_csv(ARTIFACT_INDEX)
    index = index[index["milestone"] != row["milestone"]]
    index = pd.concat([index, pd.DataFrame([row])[index.columns]], ignore_index=True)
    index.to_csv(ARTIFACT_INDEX, index=False)


def upsert_ledger() -> None:
    row = {
        "claim_id": "B-PHASE86-ACCESS-PREFLIGHT-001",
        "claim_text": "Phase86 records source-access and dependency preflight for the B-line claim-decay audit before any current-reference verdicts are produced.",
        "evidence_type": "source_access_preflight",
        "positive_evidence": "no",
        "scope": "claim_registry_empty;current_reference_verdicts_pending;not_A_paper_main_evidence",
        "artifact_path": rel(OUT / "table_phase86_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_phase86_claim_gate.csv"),
        "validation_command": "make reproduce-b-phase86-claim-decay-access-preflight",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_decay_rate_source_failure_successful_ingestion_legal_redistribution_approval_A_paper_evidence_or_new_DFT",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase86 Claim-Decay Access Preflight\n\nStatus: `access_preflight_completed_claim_registry_empty`.\n\nPhase86 records dependency status, source endpoint smoke checks, Materials\nProject version status when available, and empty claim/current-reference\nregistry templates for the B-line external AI-materials claim-decay audit.  It\nis preflight only: no claim rows have been ingested, no current-reference\nverdicts have been produced, and no decay result is allowed.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase86 Claim-Decay Access Preflight"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dependency_inventory()
    access = endpoint_smoke_checks()
    mp_status = mp_version_status()
    write_templates()
    write_plan_and_claim_gate()
    write_docs(access, mp_status)
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase86] wrote {OUT.relative_to(ROOT)}")
    print("[phase86] status=access_preflight_completed_claim_registry_empty")


if __name__ == "__main__":
    main()
