#!/usr/bin/env python3
"""Apply public-label exclusion to an A3 unlabeled materials candidate pool."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_materials_prospective_dft_followup_protocol import PUBLIC_LABEL_COLUMNS, NOVELTY_COLUMNS
from materials_prospective_dft_pipeline import (
    CANDIDATE_COLUMNS,
    DEFAULT_OUT,
    RAW_POOL_COLUMNS,
    empty_frame,
    public_safe_inputs,
    refresh_manifest,
    status_frame,
    write_with_provenance,
)


def _match_public_labels(pool: pd.DataFrame, index: pd.DataFrame) -> pd.Series:
    matches = pd.Series(False, index=pool.index)
    for col in ["candidate_id", "structure_sha256", "formula"]:
        if col in pool.columns and col in index.columns:
            index_values = set(index[col].dropna().astype(str))
            matches = matches | pool[col].astype(str).isin(index_values)
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-pool", default=None)
    parser.add_argument("--public-label-index", default=None, help="CSV with public labelled candidate ids, structure hashes or formulas.")
    parser.add_argument("--out", "--out-dir", dest="out_dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = "python scripts/filter_public_labeled_materials_candidates.py"

    raw_pool_path = Path(args.raw_pool) if args.raw_pool else out_dir / "raw_generated_candidate_pool.csv"
    inputs = public_safe_inputs(raw_pool=raw_pool_path if raw_pool_path.exists() else None, public_label_index=Path(args.public_label_index) if args.public_label_index else None)

    if not raw_pool_path.exists():
        candidates = empty_frame(CANDIDATE_COLUMNS)
        public_report = empty_frame(PUBLIC_LABEL_COLUMNS)
        novelty = empty_frame(NOVELTY_COLUMNS)
        status_text = "blocked_missing_raw_candidate_pool"
        reason = "run build_unlabeled_materials_candidate_pool.py with an external candidate pool first"
    else:
        pool = pd.read_csv(raw_pool_path)
        if args.public_label_index is None:
            candidates = empty_frame(CANDIDATE_COLUMNS)
            public_report = empty_frame(PUBLIC_LABEL_COLUMNS)
            novelty = empty_frame(NOVELTY_COLUMNS)
            status_text = "blocked_missing_public_label_index"
            reason = "public WBM/MP/OQMD/Alexandria/GNoME crossmatch index is required before DFT selection"
        else:
            index = pd.read_csv(args.public_label_index)
            matches = _match_public_labels(pool, index)
            has_structure = pool["has_structure_ref"].astype(bool) if "has_structure_ref" in pool.columns else pd.Series(False, index=pool.index)
            duplicate = pool["candidate_id"].duplicated(keep=False) if "candidate_id" in pool.columns else pd.Series(True, index=pool.index)
            input_keep = pool["keep_for_followup"].map(lambda x: str(x).strip().lower() in {"1", "true", "yes", "y", "t"}) if "keep_for_followup" in pool.columns else pd.Series(True, index=pool.index)
            has_formula = pool["formula"].notna() & pool["formula"].astype(str).str.strip().ne("") if "formula" in pool.columns else pd.Series(False, index=pool.index)
            keep = input_keep & (~matches) & has_structure & (~duplicate) & has_formula
            filtered = pool.copy()
            filtered["public_label_status"] = matches.map(lambda x: "excluded_public_label_index_match" if bool(x) else "no_public_label_index_match")
            filtered["novelty_status"] = "public_label_index_checked_structure_matcher_external_or_not_applicable"
            filtered["keep_for_followup"] = keep
            reasons = []
            for ok, was_input_keep, matched, is_dup, has_ref, formula_ok in zip(keep, input_keep, matches, duplicate, has_structure, has_formula):
                if ok:
                    reasons.append("")
                    continue
                parts = []
                if not bool(was_input_keep):
                    parts.append("input_candidate_not_followup_eligible")
                if bool(matched):
                    parts.append("public_label_index_match")
                if bool(is_dup):
                    parts.append("duplicate_candidate_id")
                if not bool(has_ref):
                    parts.append("missing_structure_ref")
                if not bool(formula_ok):
                    parts.append("missing_formula")
                reasons.append("|".join(parts) or "not_followup_eligible")
            filtered["exclusion_reason"] = reasons
            filtered["evidence_status"] = "candidate_pool_public_label_excluded_pending_alignnff_scores"
            extra = [c for c in ["structure_ref", "structure_sha256", "has_structure_ref"] if c in filtered.columns]
            candidates = filtered[CANDIDATE_COLUMNS + extra]
            public_report = pd.DataFrame(
                {
                    "candidate_id": filtered["candidate_id"],
                    "formula": filtered["formula"],
                    "WBM_label_available": matches,
                    "Materials_Project_label_available": False,
                    "OQMD_label_available": False,
                    "Alexandria_label_available": False,
                    "GNoME_label_available": False,
                    "keep_for_followup": keep,
                    "exclusion_reason": filtered["exclusion_reason"],
                    "evidence_status": filtered["evidence_status"],
                }
            )[PUBLIC_LABEL_COLUMNS]
            novelty = pd.DataFrame(
                {
                    "candidate_id": filtered["candidate_id"],
                    "formula": filtered["formula"],
                    "composition_key": filtered.get("block_id", ""),
                    "structure_matcher_status": "external_public_label_index_checked",
                    "matched_public_source": matches.map(lambda x: "public_label_index" if bool(x) else ""),
                    "matched_public_id": "",
                    "pool_duplicate_status": duplicate.map(lambda x: "duplicate_candidate_id" if bool(x) else "unique_candidate_id"),
                    "keep_for_followup": keep,
                    "evidence_status": filtered["evidence_status"],
                }
            )[NOVELTY_COLUMNS]
            ready = int(keep.sum()) > 0
            status_text = "ready_for_alignnff_scoring" if ready else "blocked_no_public_label_free_candidates"
            reason = "public-label exclusion applied; scoring still required"

    status = status_frame(
        [
            {
                "stage": "public_label_exclusion",
                "status": status_text,
                "n_candidates_after_filter": int(len(candidates)),
                "n_keep_for_followup": int(candidates["keep_for_followup"].astype(bool).sum()) if not candidates.empty else 0,
                "completed_positive_result": False,
                "blocks_DFT_submission": status_text != "ready_for_alignnff_scoring",
                "reason": reason,
            }
        ]
    )

    write_with_provenance(out_dir / "candidate_universe_frozen.csv", candidates, command, inputs)
    write_with_provenance(out_dir / "PUBLIC_LABEL_EXCLUSION_REPORT.csv", public_report, command, inputs)
    write_with_provenance(out_dir / "NOVELTY_CROSSMATCH_REPORT.csv", novelty, command, inputs)
    write_with_provenance(out_dir / "table_public_label_filter_status.csv", status, command, inputs)
    refresh_manifest(out_dir)
    print(f"wrote {out_dir / 'candidate_universe_frozen.csv'}")


if __name__ == "__main__":
    main()
