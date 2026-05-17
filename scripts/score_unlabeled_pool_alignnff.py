#!/usr/bin/env python3
"""Attach frozen ALIGNN-FF scores to the prospective unlabeled pool."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from materials_prospective_dft_pipeline import (
    DEFAULT_OUT,
    SCORE_COLUMNS,
    empty_frame,
    public_safe_inputs,
    refresh_manifest,
    sort_by_score,
    status_frame,
    write_with_provenance,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default=None)
    parser.add_argument("--scores", default=None, help="CSV with candidate_id and frozen ALIGNN-FF score.")
    parser.add_argument("--score-column", default="frozen_model_score")
    parser.add_argument("--out", "--out-dir", dest="out_dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = "python scripts/score_unlabeled_pool_alignnff.py"
    candidate_path = Path(args.candidates) if args.candidates else out_dir / "candidate_universe_frozen.csv"
    score_path = Path(args.scores) if args.scores else None
    inputs = public_safe_inputs(candidates=candidate_path if candidate_path.exists() else None, scores=score_path)

    if not candidate_path.exists() or score_path is None:
        scored = empty_frame(SCORE_COLUMNS)
        status_text = "blocked_missing_candidate_universe_or_scores"
        reason = "candidate universe and external frozen ALIGNN-FF scores are required"
    else:
        candidates = pd.read_csv(candidate_path)
        scores = pd.read_csv(score_path)
        if "candidate_id" not in candidates.columns or "candidate_id" not in scores.columns or args.score_column not in scores.columns:
            scored = empty_frame(SCORE_COLUMNS)
            status_text = "blocked_score_schema_mismatch"
            reason = "scores file must contain candidate_id and the requested score column"
        else:
            merged = candidates.merge(scores[["candidate_id", args.score_column]], on="candidate_id", how="left", suffixes=("", "_score_file"))
            score_file_col = f"{args.score_column}_score_file" if f"{args.score_column}_score_file" in merged.columns else args.score_column
            if score_file_col in merged.columns:
                merged["frozen_model_score"] = merged[score_file_col]
            merged = sort_by_score(merged, "frozen_model_score")
            merged["raw_rank"] = range(1, len(merged) + 1)
            merged["score_status"] = merged["frozen_model_score"].notna().map(lambda x: "score_present" if bool(x) else "missing_score")
            merged["evidence_status"] = "candidate_pool_scored_pending_PARC_selection"
            for col in SCORE_COLUMNS:
                if col not in merged.columns:
                    merged[col] = ""
            scored = merged[SCORE_COLUMNS]
            ready = int(scored["score_status"].eq("score_present").sum()) > 0
            status_text = "ready_for_PARC_selection" if ready else "blocked_no_valid_scores"
            reason = "frozen ALIGNN-FF scores joined; PARC release file still required"

    status = status_frame(
        [
            {
                "stage": "alignnff_scoring",
                "status": status_text,
                "n_scored_candidates": int(len(scored)),
                "n_score_present": int(scored["score_status"].eq("score_present").sum()) if not scored.empty else 0,
                "completed_positive_result": False,
                "blocks_DFT_submission": status_text != "ready_for_PARC_selection",
                "reason": reason,
            }
        ]
    )

    write_with_provenance(out_dir / "candidate_scores_alignnff.csv", scored, command, inputs)
    write_with_provenance(out_dir / "table_alignnff_score_status.csv", status, command, inputs)
    refresh_manifest(out_dir)
    print(f"wrote {out_dir / 'candidate_scores_alignnff.csv'}")


if __name__ == "__main__":
    main()
