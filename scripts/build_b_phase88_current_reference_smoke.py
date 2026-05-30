#!/usr/bin/env python3
"""Build Phase88 low-cost current-reference smoke for the B-line audit.

This phase deliberately avoids live exact-structure queries. It reuses the
frozen Phase87 registry and the already-frozen WBM t0/t1 local join to produce a
low-cost current-reference smoke. The output is not a claim-decay result.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE87 = ROOT / "outputs/milestones/b_phase87_minimal_claim_registry"
T0_T1_JOIN = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_t1_label_join.csv"
OUT = ROOT / "outputs/milestones/b_phase88_current_reference_smoke"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "b_line_current_reference_smoke;"
    "low_cost_existing_snapshot_join;"
    "formula_or_id_level_only;"
    "not_exact_structure_claim_decay;"
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
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def wbm_material_id(claim_uid: str) -> str:
    return claim_uid.split("::", 1)[1]


def build_smoke_rows() -> pd.DataFrame:
    registry = pd.read_csv(PHASE87 / "table_phase87_minimal_claim_registry.csv")
    join = pd.read_csv(T0_T1_JOIN)
    join = join.set_index("material_id", drop=False)
    rows = []
    for row in registry.itertuples(index=False):
        if row.source_family == "matbench_discovery_wbm":
            mid = wbm_material_id(str(row.claim_uid))
            if mid in join.index:
                matched = join.loc[mid]
                stable_t1 = bool(matched["stable_exact_t1_current_mp"])
                verdict = "stable_current_reference_smoke" if stable_t1 else "unstable_current_reference_smoke"
                status = "matched_existing_t1_snapshot_by_wbm_material_id"
                e_hull = matched["e_above_hull_t1_current_mp"]
                drift = matched["drift_class"]
                label_source = matched["t1_label_source"]
            else:
                verdict = ""
                status = "not_matched_existing_t1_snapshot"
                e_hull = ""
                drift = "unresolved"
                label_source = "none"
            rows.append(
                {
                    "claim_uid": row.claim_uid,
                    "source_family": row.source_family,
                    "reference_source": "materials_project_current",
                    "reference_version": "MP_2025.09.25_existing_phase49_snapshot",
                    "match_basis": "wbm_material_id_existing_t0_t1_join_not_raw_structure_match",
                    "match_status": status,
                    "current_stability_verdict": verdict,
                    "current_e_above_hull": e_hull,
                    "drift_class": drift,
                    "current_label_source": label_source,
                    "smoke_claim_allowed": "WBM subset has an existing-snapshot current-reference smoke verdict.",
                    "claim_forbidden": "Do not claim exact-structure claim decay, source-level SCDR, GNoME current decay, OQMD verdict, A-paper evidence, prospective discovery, or new DFT.",
                    "evidence_scope": SCOPE,
                }
            )
        else:
            rows.append(
                {
                    "claim_uid": row.claim_uid,
                    "source_family": row.source_family,
                    "reference_source": "materials_project_current",
                    "reference_version": "MP_2025.09.25_not_queried_phase88",
                    "match_basis": "none_raw_structure_zip_pending",
                    "match_status": "not_queried_low_cost_phase88",
                    "current_stability_verdict": "",
                    "current_e_above_hull": "",
                    "drift_class": "pending_raw_structure_ingest",
                    "current_label_source": "none",
                    "smoke_claim_allowed": "GNoME rows remain pending because low-cost phase88 does not ingest raw structures or query live current references.",
                    "claim_forbidden": "Do not claim GNoME current-reference decay or exact matching from summary rows.",
                    "evidence_scope": SCOPE,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "table_phase88_current_reference_smoke_rows.csv", index=False)
    return frame


def write_summary(frame: pd.DataFrame) -> None:
    rows = []
    for source, group in frame.groupby("source_family"):
        queried = group["match_status"].str.startswith("matched_existing").sum()
        unstable = group["current_stability_verdict"].eq("unstable_current_reference_smoke").sum()
        stable = group["current_stability_verdict"].eq("stable_current_reference_smoke").sum()
        rows.append(
            {
                "source_family": source,
                "registry_rows": len(group),
                "low_cost_smoke_matched_rows": int(queried),
                "stable_current_reference_smoke_rows": int(stable),
                "unstable_current_reference_smoke_rows": int(unstable),
                "smoke_unstable_fraction_among_matched": float(unstable / queried) if queried else "",
                "exact_raw_structure_hash_available": False,
                "current_claim_status": "weak_smoke_only" if queried else "pending",
                "evidence_scope": SCOPE,
            }
        )
    pd.DataFrame(rows).to_csv(OUT / "table_phase88_current_reference_smoke_summary.csv", index=False)

    gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase88_current_reference_smoke",
                "status": "low_cost_smoke_completed_not_claim_decay",
                "positive_evidence": "weak_smoke_only",
                "sources_with_smoke_rows": int((pd.DataFrame(rows)["low_cost_smoke_matched_rows"].astype(int) > 0).sum()),
                "total_smoke_matched_rows": int(pd.DataFrame(rows)["low_cost_smoke_matched_rows"].astype(int).sum()),
                "allowed_current_claim": "Phase88 produces a low-cost WBM existing-snapshot current-reference smoke; GNoME remains pending raw-structure ingest.",
                "forbidden_current_claim": "Do not claim exact-structure claim decay, source-level SCDR, GNoME/OQMD verdicts, A-paper evidence, prospective discovery, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase88_smoke_claim_gate.csv", index=False)


def write_docs() -> None:
    readme = f"""# Phase88 Current-Reference Smoke

Status: `low_cost_smoke_completed_not_claim_decay`.

Phase88 is a low-cost B-line smoke test. It reuses the frozen Phase87 registry
and the existing WBM t0/t1 local join. It does not perform live MP/OQMD queries,
does not ingest GNoME raw structures, and does not perform exact-structure
matching.

Allowed claim:

- WBM registry rows have existing-snapshot current-reference smoke verdicts.
- GNoME rows remain pending until raw structure ingest or a permitted exact
  matching route is implemented.

Forbidden claims:

- exact-structure claim decay;
- source-level SCDR/TDB/EDMB/CAR;
- GNoME or OQMD current-reference verdicts;
- A-paper evidence;
- prospective discovery or new DFT evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase88 Low-Cost Current-Reference Smoke Protocol

Input registry:

- `{rel(PHASE87 / 'table_phase87_minimal_claim_registry.csv')}`

Reference smoke route:

- WBM rows are joined to `{rel(T0_T1_JOIN)}` by WBM material id.
- GNoME rows are not queried in this low-cost phase because summary rows do not
  provide raw structures for exact matching.
- OQMD is not queried in this phase.

Decision boundary:

This phase is designed only to decide whether B should proceed to a stronger
exact-structure audit. It is not a paper-facing claim-decay result.
"""
    (OUT / "PHASE88_CURRENT_REFERENCE_SMOKE_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def update_artifact_index() -> None:
    row = {
        "milestone": "b_phase88_current_reference_smoke",
        "path": "outputs/milestones/b_phase88_current_reference_smoke/",
        "evidence_state": "low_cost_smoke_completed_not_claim_decay",
        "manifest": "outputs/milestones/b_phase88_current_reference_smoke/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase88_current_reference_smoke",
        "notes": "Low-cost WBM current-reference smoke using existing t0/t1 snapshot; GNoME/OQMD verdicts pending.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "B-PHASE88-CURRENT-REFERENCE-SMOKE-001",
        "claim_text": "Phase88 produces a low-cost existing-snapshot WBM current-reference smoke without exact-structure claim-decay claims.",
        "evidence_type": "low_cost_smoke",
        "positive_evidence": "weak_smoke_only",
        "scope": "WBM_existing_snapshot_only;not_exact_structure;not_SCDR;not_A_paper",
        "artifact_path": "outputs/milestones/b_phase88_current_reference_smoke/table_phase88_smoke_claim_gate.csv",
        "hash": sha256_file(OUT / "table_phase88_smoke_claim_gate.csv"),
        "validation_command": "make reproduce-b-phase88-current-reference-smoke",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_exact_structure_claim_decay",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """
## Phase88 B-Line Current-Reference Smoke

Status: `low_cost_smoke_completed_not_claim_decay`.

Phase88 performs a low-cost current-reference smoke using the frozen Phase87
registry and the existing WBM t0/t1 snapshot. It provides WBM existing-snapshot
smoke verdicts only. GNoME and OQMD remain pending, exact raw-structure matching
is not complete, and no source-level claim-decay metric is allowed.
"""
    marker = "## Phase88 B-Line Current-Reference Smoke"
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
    if not (PHASE87 / "table_phase87_minimal_claim_registry.csv").exists():
        raise FileNotFoundError("Phase87 registry is required before Phase88")
    if not T0_T1_JOIN.exists():
        raise FileNotFoundError("Existing t0/t1 join is required for low-cost WBM smoke")
    OUT.mkdir(parents=True, exist_ok=True)
    frame = build_smoke_rows()
    write_summary(frame)
    write_docs()
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase88-b] wrote {rel(OUT)}")
    print("[phase88-b] status=low_cost_smoke_completed_not_claim_decay")


if __name__ == "__main__":
    main()
