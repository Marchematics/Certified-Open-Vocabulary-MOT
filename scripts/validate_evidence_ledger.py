#!/usr/bin/env python3
"""Validate the NCS evidence-scope ledger."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
REQUIRED = {
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
}
FORBIDDEN_POSITIVE_SCOPES = {"pending", "protocol_only", "diagnostic_only", "failed_gate"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not LEDGER.exists():
        print(f"missing ledger: {LEDGER}", file=sys.stderr)
        return 1
    with LEDGER.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            print(f"missing ledger columns: {sorted(missing)}", file=sys.stderr)
            return 1
        rows = list(reader)
    if not rows:
        print("ledger is empty", file=sys.stderr)
        return 1
    seen: set[str] = set()
    for row in rows:
        claim_id = row["claim_id"]
        if claim_id in seen:
            print(f"duplicate claim_id: {claim_id}", file=sys.stderr)
            return 1
        seen.add(claim_id)
        if not row["overclaim_guardrail"].strip():
            print(f"missing overclaim guardrail: {claim_id}", file=sys.stderr)
            return 1
        artifact = ROOT / row["artifact_path"]
        if not artifact.exists() or not artifact.is_file():
            print(f"missing artifact for {claim_id}: {artifact}", file=sys.stderr)
            return 1
        digest = sha256_file(artifact)
        if digest != row["hash"]:
            print(f"hash mismatch for {claim_id}: expected {row['hash']} got {digest}", file=sys.stderr)
            return 1
        if row["positive_evidence"] == "yes" and row["scope"] in FORBIDDEN_POSITIVE_SCOPES:
            print(f"positive evidence has forbidden scope: {claim_id}", file=sys.stderr)
            return 1
        if row["status"] != "PASS":
            print(f"ledger row not PASS: {claim_id}", file=sys.stderr)
            return 1
    print(f"validated {len(rows)} evidence-ledger rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
