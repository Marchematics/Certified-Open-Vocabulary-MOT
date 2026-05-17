#!/usr/bin/env python3
"""Normalize an external unlabeled crystal candidate pool for A3.

This command is intentionally input-driven.  With no external candidate pool it
writes an explicit blocked status and an empty schema; with a supplied pool it
records public-safe structure references and hashes, but never copies raw
structure files into the public bundle.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from materials_prospective_dft_pipeline import (
    DEFAULT_OUT,
    RAW_POOL_COLUMNS,
    empty_frame,
    normalize_raw_pool,
    public_safe_inputs,
    refresh_manifest,
    status_frame,
    write_with_provenance,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-pool", default=None, help="CSV/CSV.GZ containing unlabeled candidate formulas and structure refs.")
    parser.add_argument("--out", "--out-dir", dest="out_dir", default=str(DEFAULT_OUT))
    parser.add_argument("--primary-model", default="ALIGNN-FF")
    parser.add_argument("--score-column", default=None)
    parser.add_argument("--min-candidates", type=int, default=500)
    parser.add_argument("--target-candidates", type=int, default=2000)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = "python scripts/build_unlabeled_materials_candidate_pool.py"

    if args.candidate_pool is None:
        pool = empty_frame(RAW_POOL_COLUMNS)
        status = status_frame(
            [
                {
                    "stage": "unlabeled_candidate_pool",
                    "status": "blocked_missing_external_unlabeled_pool",
                    "n_candidates": 0,
                    "n_with_structure_ref": 0,
                    "min_candidates": args.min_candidates,
                    "target_candidates": args.target_candidates,
                    "completed_positive_result": False,
                    "blocks_DFT_submission": True,
                    "reason": "supply an external public-label-free generated crystal pool; no candidates were fabricated",
                }
            ]
        )
        inputs = public_safe_inputs(candidate_pool=None, primary_model=args.primary_model)
    else:
        pool_path = Path(args.candidate_pool)
        raw = pd.read_csv(pool_path)
        pool = normalize_raw_pool(raw, primary_model=args.primary_model, score_column=args.score_column)
        n_with_structure = int(pool["has_structure_ref"].astype(bool).sum())
        n_candidates = int(len(pool))
        n_followup_eligible = int(pool["keep_for_followup"].astype(bool).sum())
        ready = n_followup_eligible >= args.min_candidates and n_with_structure >= args.min_candidates
        status = status_frame(
            [
                {
                    "stage": "unlabeled_candidate_pool",
                    "status": "ready_for_public_label_filter" if ready else "insufficient_candidates_or_structure_refs",
                    "n_candidates": n_candidates,
                    "n_with_structure_ref": n_with_structure,
                    "n_followup_eligible_before_public_label_filter": n_followup_eligible,
                    "min_candidates": args.min_candidates,
                    "target_candidates": args.target_candidates,
                    "completed_positive_result": False,
                    "blocks_DFT_submission": not ready,
                    "reason": "normalized external candidate pool; public-label exclusion and scoring still required",
                }
            ]
        )
        inputs = public_safe_inputs(candidate_pool=pool_path, primary_model=args.primary_model, score_column=args.score_column or "")

    write_with_provenance(out_dir / "raw_generated_candidate_pool.csv", pool, command, inputs)
    write_with_provenance(out_dir / "table_unlabeled_pool_build_status.csv", status, command, inputs)
    refresh_manifest(out_dir)
    print(f"wrote {out_dir / 'raw_generated_candidate_pool.csv'}")


if __name__ == "__main__":
    main()
