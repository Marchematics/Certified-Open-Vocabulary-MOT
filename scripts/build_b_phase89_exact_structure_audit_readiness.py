#!/usr/bin/env python3
"""Build Phase89 exact-structure audit readiness package for B.

Phase89 prepares the stronger B-line audit that Phase88 could not support:
raw-structure ingest, exact/near-exact matching, and current-reference
adjudication. The default run performs only lightweight endpoint/readiness
checks and writes reproducible plans. It never commits raw third-party
structures.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
PHASE87 = ROOT / "outputs/milestones/b_phase87_minimal_claim_registry"
PHASE88 = ROOT / "outputs/milestones/b_phase88_current_reference_smoke"
OUT = ROOT / "outputs/milestones/b_phase89_exact_structure_audit_readiness"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

GNOME_BY_ID_ZIP_URL = "https://storage.googleapis.com/gdm_materials_discovery/gnome_data/by_id.zip"
LOCAL_CACHE = ROOT / "cache/b_phase89/gnome/by_id.zip"

SCOPE = (
    "b_line_exact_structure_audit_readiness;"
    "readiness_and_protocol_only;"
    "raw_structure_cache_not_versioned;"
    "current_reference_verdicts_pending;"
    "not_completed_positive_evidence;"
    "not_A_paper_main_evidence;"
    "not_prospective_discovery;"
    "not_new_DFT_evidence"
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
        if "cache" in path.parts or "third_party" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def head_url(url: str) -> dict[str, object]:
    row: dict[str, object] = {
        "url": url,
        "reachable": False,
        "status_code": "",
        "content_length_bytes": "",
        "content_type": "",
        "accept_ranges": "",
        "error": "",
    }
    try:
        response = requests.head(url, timeout=30, allow_redirects=True)
        row.update(
            {
                "reachable": response.ok,
                "status_code": response.status_code,
                "content_length_bytes": response.headers.get("content-length", ""),
                "content_type": response.headers.get("content-type", ""),
                "accept_ranges": response.headers.get("accept-ranges", ""),
            }
        )
    except Exception as exc:  # pragma: no cover - network failure is recorded
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def optional_download(url: str, target: Path) -> dict[str, object]:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    bytes_written = 0
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    bytes_written += len(chunk)
    tmp.replace(target)
    return {
        "local_cache_path": rel(target),
        "downloaded": True,
        "bytes": bytes_written,
        "sha256": sha256_file(target),
        "versioned_in_git": False,
    }


def write_readiness(download_gnome_zip: bool) -> None:
    registry = pd.read_csv(PHASE87 / "table_phase87_minimal_claim_registry.csv")
    smoke = pd.read_csv(PHASE88 / "table_phase88_current_reference_smoke_summary.csv")

    endpoint = head_url(GNOME_BY_ID_ZIP_URL)
    endpoint_rows = [
        {
            "source": "gnome_by_id_zip",
            **endpoint,
            "local_cache_path": rel(LOCAL_CACHE),
            "local_cache_exists": LOCAL_CACHE.exists(),
            "local_cache_sha256": sha256_file(LOCAL_CACHE) if LOCAL_CACHE.exists() else "",
            "raw_data_versioned_in_git": False,
            "evidence_scope": SCOPE,
        },
        {
            "source": "materials_project_current_api",
            "url": "redacted_env_MP_API_KEY",
            "reachable": bool(os.environ.get("MP_API_KEY")),
            "status_code": "not_live_queried_phase89",
            "content_length_bytes": "",
            "content_type": "",
            "accept_ranges": "",
            "error": "" if os.environ.get("MP_API_KEY") else "MP_API_KEY_missing",
            "local_cache_path": "",
            "local_cache_exists": False,
            "local_cache_sha256": "",
            "raw_data_versioned_in_git": False,
            "evidence_scope": SCOPE,
        },
    ]

    if download_gnome_zip:
        download = optional_download(GNOME_BY_ID_ZIP_URL, LOCAL_CACHE)
        endpoint_rows[0].update(
            {
                "local_cache_exists": True,
                "local_cache_sha256": download["sha256"],
                "content_length_bytes": download["bytes"],
            }
        )

    pd.DataFrame(endpoint_rows).to_csv(OUT / "table_phase89_endpoint_and_cache_status.csv", index=False)

    source_rows = []
    for source, group in registry.groupby("source_family"):
        source_smoke = smoke[smoke["source_family"].eq(source)]
        matched = int(source_smoke["low_cost_smoke_matched_rows"].iloc[0]) if len(source_smoke) else 0
        source_rows.append(
            {
                "source_family": source,
                "registry_rows": len(group),
                "phase88_low_cost_matched_rows": matched,
                "exact_raw_structure_available_now": bool(source == "gnome_public_stable_materials" and LOCAL_CACHE.exists()),
                "exact_structure_next_action": (
                    "extract_registry_ids_from_by_id_zip_then_structure_match"
                    if source == "gnome_public_stable_materials"
                    else "acquire_wbm_raw_structures_or_keep_existing_snapshot_as_smoke_only"
                ),
                "current_reference_next_action": "query_current_MP_by_formula_prefilter_then_StructureMatcher",
                "claim_status_after_phase89": "readiness_only",
                "evidence_scope": SCOPE,
            }
        )
    pd.DataFrame(source_rows).to_csv(OUT / "table_phase89_source_readiness.csv", index=False)


def write_plans() -> None:
    registry = pd.read_csv(PHASE87 / "table_phase87_minimal_claim_registry.csv")
    gnome = registry[registry["source_family"].eq("gnome_public_stable_materials")]
    pd.DataFrame(
        [
            {
                "claim_uid": row.claim_uid,
                "material_id": str(row.claim_uid).split("::", 1)[1],
                "source_family": row.source_family,
                "raw_structure_source": GNOME_BY_ID_ZIP_URL,
                "local_cache_path": rel(LOCAL_CACHE),
                "planned_extraction_status": "pending_local_cache",
                "redistribution_policy": "do_not_commit_raw_structure;derived_hashes_only",
                "evidence_scope": SCOPE,
            }
            for row in gnome.itertuples(index=False)
        ]
    ).to_csv(OUT / "table_phase89_gnome_structure_ingest_manifest.csv", index=False)

    pd.DataFrame(
        [
            {
                "step": 1,
                "operation": "raw_structure_ingest",
                "implementation": "download GNoME by_id.zip into cache/b_phase89/gnome/by_id.zip, extract only registry material ids",
                "output": "derived structure hashes and temporary local structures outside git",
                "guardrail": "do_not_commit_raw_structures",
            },
            {
                "step": 2,
                "operation": "mp_prefilter",
                "implementation": "query current Materials Project by chemical system/formula candidates using MP_API_KEY from env only",
                "output": "candidate MP entry ids and redacted query log",
                "guardrail": "do_not_store_credentials",
            },
            {
                "step": 3,
                "operation": "structure_match",
                "implementation": "pymatgen StructureMatcher with frozen tolerances; formula-only matches remain ambiguous",
                "output": "exact_match, near_match, ambiguous, no_match adjudication table",
                "guardrail": "do_not_count_formula_only_matches_as_exact_decay",
            },
            {
                "step": 4,
                "operation": "current_reference_verdict",
                "implementation": "compute current stability only for matched/adjudicated structures",
                "output": "SCDR/TDB/EDMB candidates only after exact/near-exact adjudication",
                "guardrail": "do_not_report_source_level_decay_before_match_gate",
            },
        ]
    ).to_csv(OUT / "table_phase89_exact_match_execution_plan.csv", index=False)

    pd.DataFrame(
        [
            {
                "command_id": "download_gnome_zip",
                "command": "python scripts/build_b_phase89_exact_structure_audit_readiness.py --download-gnome-zip",
                "writes_raw_data": "cache/b_phase89/gnome/by_id.zip",
                "git_tracked": False,
            },
            {
                "command_id": "reproduce_readiness_only",
                "command": "make reproduce-b-phase89-exact-structure-audit-readiness",
                "writes_raw_data": "no",
                "git_tracked": True,
            },
        ]
    ).to_csv(OUT / "table_phase89_execution_commands.csv", index=False)


def write_docs_and_gate() -> None:
    gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase89_exact_structure_audit_readiness",
                "status": "readiness_and_protocol_only_current_verdicts_pending",
                "positive_evidence": "no",
                "allowed_current_claim": "Phase89 prepares exact-structure audit readiness and local raw-structure cache commands for the B line.",
                "forbidden_current_claim": "Do not claim completed exact matching, claim decay, source-level SCDR/TDB/EDMB/CAR, A-paper evidence, prospective discovery, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase89_claim_gate.csv", index=False)

    readme = f"""# Phase89 Exact-Structure Audit Readiness

Status: `readiness_and_protocol_only_current_verdicts_pending`.

Phase89 prepares the B-line exact-structure audit. The default command performs
readiness checks and writes ingestion/matching/adjudication plans. It does not
download raw structures unless `--download-gnome-zip` is explicitly provided.

Raw GNoME structures are intentionally cached under `cache/` and excluded from
git. Public artifacts contain only manifests, derived hashes when available,
and guardrails.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase89 Exact-Structure Audit Protocol

Inputs:

- Phase87 frozen registry.
- Phase88 low-cost current-reference smoke.
- GNoME by-id zip endpoint: `{GNOME_BY_ID_ZIP_URL}`.
- Materials Project current API credentials read from environment only.

Current phase boundary:

- No current-reference verdicts are produced.
- No exact-structure claim-decay metric is produced.
- Formula-only or id-only links are not counted as exact matches.

Next executable step:

```bash
python scripts/build_b_phase89_exact_structure_audit_readiness.py --download-gnome-zip
```

The downloaded zip remains outside version control.
"""
    (OUT / "PHASE89_EXACT_STRUCTURE_AUDIT_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def update_artifact_index() -> None:
    row = {
        "milestone": "b_phase89_exact_structure_audit_readiness",
        "path": "outputs/milestones/b_phase89_exact_structure_audit_readiness/",
        "evidence_state": "readiness_and_protocol_only_current_verdicts_pending",
        "manifest": "outputs/milestones/b_phase89_exact_structure_audit_readiness/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase89_exact_structure_audit_readiness",
        "notes": "B-line exact-structure audit readiness and raw-cache execution plan; no decay claim.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "B-PHASE89-EXACT-STRUCTURE-READINESS-001",
        "claim_text": "Phase89 prepares exact-structure audit readiness for B without producing current-reference verdicts.",
        "evidence_type": "readiness_protocol",
        "positive_evidence": "no",
        "scope": "protocol_only;current_verdicts_pending;not_exact_decay",
        "artifact_path": "outputs/milestones/b_phase89_exact_structure_audit_readiness/table_phase89_claim_gate.csv",
        "hash": sha256_file(OUT / "table_phase89_claim_gate.csv"),
        "validation_command": "make reproduce-b-phase89-exact-structure-audit-readiness",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_completed_exact_matching_or_decay",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """
## Phase89 B-Line Exact-Structure Audit Readiness

Status: `readiness_and_protocol_only_current_verdicts_pending`.

Phase89 prepares the B-line exact-structure audit by checking GNoME raw-zip
access, defining local cache rules, freezing the extraction and matching plan,
and keeping current-reference verdicts pending. It is not claim-decay evidence.
"""
    marker = "## Phase89 B-Line Exact-Structure Audit Readiness"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        if next_idx >= 0:
            text = before + "\n" + section + after[next_idx:]
        else:
            text = before + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-gnome-zip", action="store_true")
    args = parser.parse_args()

    if not PHASE87.exists() or not PHASE88.exists():
        raise FileNotFoundError("Phase87 and Phase88 B-line artifacts are required")
    OUT.mkdir(parents=True, exist_ok=True)
    write_readiness(download_gnome_zip=args.download_gnome_zip)
    write_plans()
    write_docs_and_gate()
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase89-b] wrote {rel(OUT)}")
    print("[phase89-b] status=readiness_and_protocol_only_current_verdicts_pending")


if __name__ == "__main__":
    main()
