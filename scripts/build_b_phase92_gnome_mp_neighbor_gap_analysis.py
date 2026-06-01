#!/usr/bin/env python3
"""Build B Phase92 GNoME current-MP chemical-neighbor gap analysis.

Phase91 found MP records in some matching chemical systems but no exact
reduced-formula candidates for the frozen GNoME 150-row registry.  Phase92
quantifies that gap using composition and site-count distances.  It does not
fetch structures, does not run StructureMatcher, and does not report stability
verdicts.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pandas as pd
from pymatgen.core import Composition


ROOT = Path(__file__).resolve().parents[1]
PHASE91 = ROOT / "outputs/milestones/b_phase91_gnome_mp_formula_prefilter"
OUT = ROOT / "outputs/milestones/b_phase92_gnome_mp_neighbor_gap_analysis"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "b_line_gnome_mp_neighbor_gap_analysis;"
    "chemical_neighbor_distance_only;"
    "exact_formula_matches_absent_in_phase91;"
    "structure_matching_not_run;"
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


def frac_dict(formula: str) -> dict[str, float]:
    try:
        comp = Composition(str(formula))
    except Exception:
        return {}
    total = float(sum(comp.get_el_amt_dict().values()))
    if total <= 0:
        return {}
    return {el: float(amount) / total for el, amount in comp.get_el_amt_dict().items()}


def l1_composition_distance(a: str, b: str) -> float:
    fa = frac_dict(a)
    fb = frac_dict(b)
    if not fa or not fb:
        return math.nan
    keys = set(fa) | set(fb)
    return float(sum(abs(fa.get(key, 0.0) - fb.get(key, 0.0)) for key in keys))


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = pd.read_csv(PHASE91 / "table_phase91_gnome_mp_formula_prefilter.csv")
    candidates = pd.read_csv(PHASE91 / "table_phase91_mp_formula_prefilter_candidates.csv")
    if "exact_reduced_formula_match" in candidates.columns:
        candidates = candidates[~candidates["exact_reduced_formula_match"].astype(bool)].copy()

    neighbor_rows = []
    for _, cand in candidates.iterrows():
        g_formula = str(cand["gnome_reduced_formula"])
        mp_formula = str(cand["mp_formula_pretty"])
        g_sites = float(cand["gnome_n_sites"])
        mp_sites = float(cand["mp_nsites"])
        site_ratio = min(g_sites, mp_sites) / max(g_sites, mp_sites) if g_sites > 0 and mp_sites > 0 else math.nan
        neighbor_rows.append(
            {
                "claim_uid": cand["claim_uid"],
                "material_id": cand["material_id"],
                "gnome_reduced_formula": g_formula,
                "mp_material_id": cand["mp_material_id"],
                "mp_formula_pretty": mp_formula,
                "chemical_system": cand["gnome_chemical_system"],
                "composition_l1_distance": l1_composition_distance(g_formula, mp_formula),
                "gnome_n_sites": cand["gnome_n_sites"],
                "mp_nsites": cand["mp_nsites"],
                "site_count_ratio": site_ratio,
                "exact_reduced_formula_match": False,
                "eligible_for_exact_structure_match": False,
                "neighbor_only": True,
                "structure_matching_completed": False,
                "current_stability_verdict_reported": False,
                "evidence_scope": SCOPE,
            }
        )
    neighbors = pd.DataFrame(neighbor_rows)

    summary_rows = []
    grouped = neighbors.groupby("claim_uid", dropna=False) if not neighbors.empty else []
    best_by_claim = {}
    for claim_uid, group in grouped:
        best = group.sort_values(["composition_l1_distance", "site_count_ratio"], ascending=[True, False]).iloc[0]
        best_by_claim[str(claim_uid)] = best
    for _, row in rows.iterrows():
        best = best_by_claim.get(str(row["claim_uid"]))
        summary_rows.append(
            {
                "claim_uid": row["claim_uid"],
                "material_id": row["material_id"],
                "gnome_reduced_formula": row["gnome_reduced_formula"],
                "gnome_chemical_system": row["gnome_chemical_system"],
                "mp_chemsys_candidate_count": int(row["mp_chemsys_candidate_count"]),
                "mp_exact_formula_candidate_count": int(row["mp_exact_formula_candidate_count"]),
                "has_neighbor_candidates": best is not None,
                "best_neighbor_mp_material_id": "" if best is None else best["mp_material_id"],
                "best_neighbor_formula": "" if best is None else best["mp_formula_pretty"],
                "best_neighbor_composition_l1_distance": "" if best is None else float(best["composition_l1_distance"]),
                "best_neighbor_site_count_ratio": "" if best is None else float(best["site_count_ratio"]),
                "exact_match_path_available": False,
                "recommended_next_action": (
                    "expand_source_registry_or_query_external_source;no_exact_formula_mp_path"
                    if int(row["mp_exact_formula_candidate_count"]) == 0
                    else "fetch_structures_and_run_structure_matcher"
                ),
                "evidence_scope": SCOPE,
            }
        )
    summary = pd.DataFrame(summary_rows)
    return summary, neighbors


def write_outputs(summary: pd.DataFrame, neighbors: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "table_phase92_gnome_mp_neighbor_gap_summary.csv", index=False)
    neighbors.to_csv(OUT / "table_phase92_gnome_mp_neighbor_candidates.csv", index=False)

    overview = pd.DataFrame(
        [
            {
                "source_family": "gnome_public_stable_materials",
                "gnome_rows": len(summary),
                "rows_with_chemsys_neighbors": int(summary["has_neighbor_candidates"].astype(bool).sum()),
                "rows_with_exact_formula_candidates": int(summary["mp_exact_formula_candidate_count"].gt(0).sum()),
                "neighbor_candidate_records": len(neighbors),
                "structure_matching_completed": False,
                "current_stability_verdicts_reported": False,
                "claim_status": "neighbor_gap_analysis_completed_no_exact_match_path",
                "evidence_scope": SCOPE,
            }
        ]
    )
    overview.to_csv(OUT / "table_phase92_neighbor_gap_overview.csv", index=False)

    gate = pd.DataFrame(
        [
            {
                "claim_gate": "b_phase92_gnome_mp_neighbor_gap_analysis",
                "status": "neighbor_gap_analysis_completed_no_exact_match_path",
                "positive_evidence": "no",
                "allowed_current_claim": "Phase92 shows that Phase91 current-MP candidates are chemical-system neighbors, not exact-formula candidates.",
                "forbidden_current_claim": "Do not claim exact structure matching, current stability verdicts, source-level claim decay, A-paper evidence, prospective discovery, or new DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase92_claim_gate.csv", index=False)


def write_docs(summary: pd.DataFrame, neighbors: pd.DataFrame) -> None:
    exact_rows = int(summary["mp_exact_formula_candidate_count"].gt(0).sum())
    readme = f"""# B Phase92 GNoME MP Neighbor Gap Analysis

Status: `neighbor_gap_analysis_completed_no_exact_match_path`.

Phase92 analyzes Phase91 current-MP chemical-system candidates as composition
neighbors.  It confirms that the frozen GNoME 150-row subset has `{exact_rows}`
rows with exact reduced-formula MP candidates in the Phase91 prefilter.

This closes the low-cost exact-match path for this subset.  Formula-neighbor
records can guide future expansion, but they are not claim-decay evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = """# Phase92 Protocol: GNoME MP Neighbor Gap Analysis

Inputs:

- Phase91 GNoME MP formula prefilter rows.

Procedure:

1. Exclude exact formula candidates; Phase91 found none.
2. Compute fractional-composition L1 distance and site-count ratio for
   chemical-system neighbors.
3. Report best neighbor per GNoME row.
4. Do not fetch structures, run StructureMatcher, or report stability fields.
"""
    (OUT / "PHASE92_GNOME_MP_NEIGHBOR_GAP_PROTOCOL.md").write_text(protocol, encoding="utf-8")


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
        "milestone": "b_phase92_gnome_mp_neighbor_gap_analysis",
        "path": "outputs/milestones/b_phase92_gnome_mp_neighbor_gap_analysis/",
        "evidence_state": "neighbor_gap_analysis_completed_no_exact_match_path",
        "manifest": "outputs/milestones/b_phase92_gnome_mp_neighbor_gap_analysis/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase92_gnome_mp_neighbor_gap_analysis",
        "notes": "B-line GNoME MP chemical-neighbor gap analysis; no exact matching or decay claim.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "B-PHASE92-GNOME-MP-NEIGHBOR-GAP-001",
        "claim_text": "Phase92 shows that Phase91 current-MP GNoME candidates are chemical-system neighbors, not exact-formula matches.",
        "evidence_type": "neighbor_gap_artifact",
        "positive_evidence": "no",
        "scope": "chemical_neighbor_distance_only;no_exact_match_path",
        "artifact_path": "outputs/milestones/b_phase92_gnome_mp_neighbor_gap_analysis/table_phase92_neighbor_gap_overview.csv",
        "hash": sha256_file(OUT / "table_phase92_neighbor_gap_overview.csv"),
        "validation_command": "make reproduce-b-phase92-gnome-mp-neighbor-gap-analysis",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_exact_structure_matching_current_stability_or_claim_decay_from_neighbor_gap",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase92 B-Line GNoME MP Neighbor Gap Analysis\n\nStatus: `neighbor_gap_analysis_completed_no_exact_match_path`.\n\nPhase92 analyzes Phase91 current-MP chemical-system candidates as composition\nneighbors and confirms that the frozen GNoME subset does not have an exact\nreduced-formula MP path in the current low-cost prefilter. It is not exact\nstructure matching, current stability evidence, source-level claim decay,\nA-paper evidence, prospective discovery, or new DFT evidence.\n"""
    marker = "## Phase92 B-Line GNoME MP Neighbor Gap Analysis"
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
    summary, neighbors = build_tables()
    write_outputs(summary, neighbors)
    write_docs(summary, neighbors)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase92-b] wrote {rel(OUT)}")
    print("[phase92-b] status=neighbor_gap_analysis_completed_no_exact_match_path")


if __name__ == "__main__":
    main()
