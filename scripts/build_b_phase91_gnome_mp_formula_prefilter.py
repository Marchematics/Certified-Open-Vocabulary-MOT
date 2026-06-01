#!/usr/bin/env python3
"""Build B Phase91 GNoME -> Materials Project formula/chemsys prefilter.

This phase uses the current Materials Project API only to identify candidate
MP records by chemical system and exact reduced formula for the frozen GNoME
registry rows ingested in Phase90.  It intentionally does not report MP
stability verdicts, does not perform structure matching, and does not claim
decay.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from mp_api.client import MPRester
from pymatgen.core import Composition


ROOT = Path(__file__).resolve().parents[1]
PHASE90 = ROOT / "outputs/milestones/b_phase90_gnome_raw_structure_ingest"
OUT = ROOT / "outputs/milestones/b_phase91_gnome_mp_formula_prefilter"
CACHE = ROOT / "cache/b_phase91/mp_formula_prefilter_cache.json"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "b_line_gnome_mp_formula_prefilter;"
    "mp_current_reference_candidate_search;"
    "formula_and_chemsys_only;"
    "exact_structure_matching_pending;"
    "current_stability_verdicts_not_reported;"
    "not_claim_decay_evidence;"
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


def composition_key(formula: str) -> str:
    try:
        comp = Composition(str(formula))
        return comp.reduced_composition.alphabetical_formula
    except Exception:
        return ""


def doc_to_record(doc: Any) -> dict[str, Any]:
    symmetry = getattr(doc, "symmetry", None)
    symmetry_number = ""
    symmetry_symbol = ""
    if symmetry is not None:
        symmetry_number = getattr(symmetry, "number", "") or ""
        symmetry_symbol = getattr(symmetry, "symbol", "") or ""
    return {
        "mp_material_id": str(getattr(doc, "material_id", "")),
        "mp_formula_pretty": str(getattr(doc, "formula_pretty", "")),
        "mp_chemsys": str(getattr(doc, "chemsys", "")),
        "mp_nsites": getattr(doc, "nsites", ""),
        "mp_symmetry_number": symmetry_number,
        "mp_symmetry_symbol": symmetry_symbol,
    }


def query_mp_by_chemsys(chemsys_values: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not os.environ.get("MP_API_KEY"):
        raise RuntimeError("MP_API_KEY is required for first-run Phase91 MP prefilter")
    cache: dict[str, list[dict[str, Any]]] = {}
    fields = ["material_id", "formula_pretty", "chemsys", "nsites", "symmetry"]
    with MPRester(os.environ["MP_API_KEY"]) as mpr:
        for chemsys in chemsys_values:
            docs = mpr.materials.summary.search(chemsys=chemsys, fields=fields)
            cache[chemsys] = [doc_to_record(doc) for doc in docs]
    return cache


def load_or_query_cache(chemsys_values: list[str]) -> dict[str, list[dict[str, Any]]]:
    if CACHE.exists():
        existing = json.loads(CACHE.read_text(encoding="utf-8"))
    else:
        existing = {}
    missing = [chemsys for chemsys in chemsys_values if chemsys not in existing]
    if missing:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        existing.update(query_mp_by_chemsys(missing))
        CACHE.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
    return existing


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    gnome = pd.read_csv(PHASE90 / "table_phase90_gnome_raw_structure_ingest.csv")
    parsed = gnome[gnome["parse_status"].eq("parsed")].copy()
    chemsys_values = sorted(parsed["pymatgen_chemical_system"].dropna().astype(str).unique())
    cache = load_or_query_cache(chemsys_values)

    candidate_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for _, row in parsed.iterrows():
        claim_uid = str(row["claim_uid"])
        chemsys = str(row["pymatgen_chemical_system"])
        formula = str(row["pymatgen_reduced_formula"])
        gnome_key = composition_key(formula)
        candidates = cache.get(chemsys, [])
        exact_ids = []
        for cand in candidates:
            mp_key = composition_key(str(cand["mp_formula_pretty"]))
            exact_formula = bool(gnome_key and mp_key and gnome_key == mp_key)
            if exact_formula:
                exact_ids.append(str(cand["mp_material_id"]))
            candidate_rows.append(
                {
                    "claim_uid": claim_uid,
                    "material_id": row["material_id"],
                    "gnome_reduced_formula": formula,
                    "gnome_chemical_system": chemsys,
                    "gnome_n_sites": row["pymatgen_n_sites"],
                    **cand,
                    "exact_reduced_formula_match": exact_formula,
                    "formula_prefilter_only": True,
                    "structure_matching_completed": False,
                    "current_stability_verdict_reported": False,
                    "evidence_scope": SCOPE,
                }
            )
        summary_rows.append(
            {
                "claim_uid": claim_uid,
                "material_id": row["material_id"],
                "gnome_reduced_formula": formula,
                "gnome_chemical_system": chemsys,
                "mp_chemsys_candidate_count": len(candidates),
                "mp_exact_formula_candidate_count": len(exact_ids),
                "mp_exact_formula_candidate_ids_first10": ";".join(exact_ids[:10]),
                "query_status": "queried_current_mp_summary_no_stability_fields",
                "formula_prefilter_complete": True,
                "structure_matching_completed": False,
                "current_stability_verdict_reported": False,
                "claim_decay_evidence": False,
                "evidence_scope": SCOPE,
            }
        )

    candidates_df = pd.DataFrame(candidate_rows)
    summary_df = pd.DataFrame(summary_rows)
    return summary_df, candidates_df


def write_outputs(summary: pd.DataFrame, candidates: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "table_phase91_gnome_mp_formula_prefilter.csv", index=False)
    candidates.to_csv(OUT / "table_phase91_mp_formula_prefilter_candidates.csv", index=False)

    overview = pd.DataFrame(
        [
            {
                "source_family": "gnome_public_stable_materials",
                "gnome_rows": len(summary),
                "rows_with_mp_chemsys_candidates": int(summary["mp_chemsys_candidate_count"].gt(0).sum()),
                "rows_with_exact_formula_candidates": int(summary["mp_exact_formula_candidate_count"].gt(0).sum()),
                "total_mp_candidate_records": len(candidates),
                "structure_matching_completed": False,
                "current_stability_verdicts_reported": False,
                "claim_status": "mp_formula_prefilter_completed_exact_matching_pending",
                "evidence_scope": SCOPE,
            }
        ]
    )
    overview.to_csv(OUT / "table_phase91_mp_formula_prefilter_summary.csv", index=False)

    gate = pd.DataFrame(
        [
            {
                "claim_gate": "b_phase91_gnome_mp_formula_prefilter",
                "status": "mp_formula_prefilter_completed_exact_matching_pending",
                "positive_evidence": "no",
                "allowed_current_claim": "Phase91 identifies current-MP chemical-system and exact-formula candidate records for frozen GNoME rows.",
                "forbidden_current_claim": "Do not claim exact structure matching, current stability verdicts, source-level claim decay, A-paper evidence, prospective discovery, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase91_claim_gate.csv", index=False)

    next_steps = pd.DataFrame(
        [
            {
                "step": "fetch_candidate_mp_structures",
                "input": "table_phase91_mp_formula_prefilter_candidates.csv",
                "status": "pending",
                "guardrail": "do not report stability verdicts before exact/near-exact structure matching",
            },
            {
                "step": "structure_matcher",
                "input": "GNoME raw structures plus MP formula-prefilter candidates",
                "status": "pending",
                "guardrail": "formula-only candidates cannot count as claim-decay evidence",
            },
        ]
    )
    next_steps.to_csv(OUT / "table_phase91_next_match_steps.csv", index=False)


def write_docs(summary: pd.DataFrame, candidates: pd.DataFrame) -> None:
    rows_with_exact = int(summary["mp_exact_formula_candidate_count"].gt(0).sum())
    readme = f"""# B Phase91 GNoME -> MP Formula Prefilter

Status: `mp_formula_prefilter_completed_exact_matching_pending`.

Phase91 queries current Materials Project summary records by chemical system
for the frozen GNoME registry rows and records exact reduced-formula candidate
IDs.  It does not request or report MP stability fields, does not perform
structure matching, and does not claim decay.

Summary:

- GNoME rows: `{len(summary)}`;
- rows with at least one exact-formula MP candidate: `{rows_with_exact}`;
- MP candidate records written: `{len(candidates)}`;
- exact structure matching: pending;
- current stability verdicts: not reported.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase91 Protocol: GNoME MP Formula Prefilter

Inputs:

- Phase90 derived GNoME structure metadata;
- current Materials Project API summary search by chemical system.

Allowed outputs:

- MP material IDs, formula, chemical system, site count and symmetry metadata;
- exact reduced-formula candidate counts.

Forbidden outputs:

- current MP stability verdicts;
- exact or near-exact structure matches;
- source-level claim decay;
- A-paper main evidence;
- prospective discovery;
- new DFT evidence.
"""
    (OUT / "PHASE91_GNOME_MP_FORMULA_PREFILTER_PROTOCOL.md").write_text(protocol, encoding="utf-8")


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


def update_artifact_index() -> None:
    row = {
        "milestone": "b_phase91_gnome_mp_formula_prefilter",
        "path": "outputs/milestones/b_phase91_gnome_mp_formula_prefilter/",
        "evidence_state": "mp_formula_prefilter_completed_exact_matching_pending",
        "manifest": "outputs/milestones/b_phase91_gnome_mp_formula_prefilter/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase91_gnome_mp_formula_prefilter",
        "notes": "B-line GNoME MP formula prefilter; no stability verdicts or exact matching.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "B-PHASE91-GNOME-MP-FORMULA-PREFILTER-001",
        "claim_text": "Phase91 identifies current-MP formula-prefilter candidates for frozen GNoME rows without reporting stability verdicts.",
        "evidence_type": "formula_prefilter_artifact",
        "positive_evidence": "no",
        "scope": "formula_and_chemsys_only;exact_matching_pending;stability_verdicts_not_reported",
        "artifact_path": "outputs/milestones/b_phase91_gnome_mp_formula_prefilter/table_phase91_mp_formula_prefilter_summary.csv",
        "hash": sha256_file(OUT / "table_phase91_mp_formula_prefilter_summary.csv"),
        "validation_command": "make reproduce-b-phase91-gnome-mp-formula-prefilter",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_exact_structure_matching_current_stability_or_claim_decay_from_formula_prefilter",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase91 B-Line GNoME MP Formula Prefilter\n\nStatus: `mp_formula_prefilter_completed_exact_matching_pending`.\n\nPhase91 queries current Materials Project summary records by chemical system\nfor frozen GNoME rows and writes formula-prefilter candidate IDs. It does not\nreport current stability verdicts, does not perform exact structure matching,\nand is not source-level claim-decay evidence, A-paper evidence, prospective\ndiscovery, or new DFT evidence.\n"""
    marker = "## Phase91 B-Line GNoME MP Formula Prefilter"
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
    if not PHASE90.exists():
        raise FileNotFoundError("Phase90 artifacts are required")
    summary, candidates = build_tables()
    write_outputs(summary, candidates)
    write_docs(summary, candidates)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase91-b] wrote {rel(OUT)}")
    print("[phase91-b] status=mp_formula_prefilter_completed_exact_matching_pending")


if __name__ == "__main__":
    main()
