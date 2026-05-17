#!/usr/bin/env python3
"""Freeze prospective DFT follow-up arms from scored candidates and PARC release ids."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from materials_prospective_dft_pipeline import (
    DEFAULT_OUT,
    SELECTION_EXTENDED_COLUMNS,
    empty_frame,
    public_safe_inputs,
    refresh_manifest,
    safe_bool,
    sort_by_score,
    status_frame,
    write_with_provenance,
)


def release_ids_from(scored: pd.DataFrame, release_file: Path | None) -> set[str]:
    if release_file is not None:
        release = pd.read_csv(release_file)
        if "candidate_id" not in release.columns:
            return set()
        if "parc_release_flag" in release.columns:
            return set(release[release["parc_release_flag"].map(safe_bool)]["candidate_id"].astype(str))
        return set(release["candidate_id"].astype(str))
    if "parc_release_flag" in scored.columns:
        return set(scored[scored["parc_release_flag"].map(safe_bool)]["candidate_id"].astype(str))
    return set()


def rows_for_arm(df: pd.DataFrame, arm: str, target_n: int, reserve_n: int, rule: str) -> list[dict]:
    rows: list[dict] = []
    for pos, (_, row) in enumerate(df.head(target_n + reserve_n).iterrows(), start=1):
        primary = pos <= target_n
        rows.append(
            {
                "candidate_id": row["candidate_id"],
                "arm": arm,
                "arm_rank": pos if primary else "",
                "reserve_rank": "" if primary else pos - target_n,
                "selection_rule": rule,
                "selected_for_dft": primary,
                "dft_job_id": "",
                "evidence_status": "selection_frozen_before_DFT_outcomes",
                "primary_or_reserve": "primary" if primary else "reserve",
                "source_rank": row.get("raw_rank", ""),
                "frozen_model_score": row.get("frozen_model_score", ""),
                "structure_ref": row.get("structure_ref", ""),
                "structure_sha256": row.get("structure_sha256", ""),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", default=None)
    parser.add_argument("--parc-release-file", default=None, help="CSV with candidate_id values in the frozen PARC release set.")
    parser.add_argument("--out", "--out-dir", dest="out_dir", default=str(DEFAULT_OUT))
    parser.add_argument("--K", type=int, default=500)
    parser.add_argument("--n-release", type=int, default=40)
    parser.add_argument("--n-raw-only", type=int, default=40)
    parser.add_argument("--n-raw-matched", type=int, default=40)
    parser.add_argument("--reserve-n", type=int, default=20)
    parser.add_argument("--min-analyzable-n", type=int, default=25)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = "python scripts/select_prospective_dft_arms_from_pool.py"
    score_path = Path(args.scores) if args.scores else out_dir / "candidate_scores_alignnff.csv"
    release_path = Path(args.parc_release_file) if args.parc_release_file else None
    inputs = public_safe_inputs(scores=score_path if score_path.exists() else None, parc_release_file=release_path)

    if not score_path.exists():
        selection = empty_frame(SELECTION_EXTENDED_COLUMNS)
        status_text = "blocked_missing_scores"
        reason = "run score_unlabeled_pool_alignnff.py before arm selection"
    else:
        scored = pd.read_csv(score_path)
        if scored.empty or "candidate_id" not in scored.columns or "frozen_model_score" not in scored.columns:
            selection = empty_frame(SELECTION_EXTENDED_COLUMNS)
            status_text = "blocked_empty_or_invalid_score_table"
            reason = "scored candidate table must be nonempty with candidate_id and frozen_model_score"
        else:
            eligible = scored.copy()
            if "keep_for_followup" in eligible.columns:
                eligible = eligible[eligible["keep_for_followup"].map(safe_bool)]
            if "score_status" in eligible.columns:
                eligible = eligible[eligible["score_status"].eq("score_present")]
            ranked = sort_by_score(eligible, "frozen_model_score").reset_index(drop=True)
            ranked["raw_rank"] = range(1, len(ranked) + 1)
            raw_topK = ranked.head(args.K)
            release_ids = release_ids_from(ranked, release_path)
            release = raw_topK[raw_topK["candidate_id"].astype(str).isin(release_ids)]
            raw_only = raw_topK[~raw_topK["candidate_id"].astype(str).isin(release_ids)]
            raw_topR = raw_topK.head(max(len(release), 0))
            if len(raw_topR) > 0 and set(raw_topR["candidate_id"].astype(str)).issubset(set(release["candidate_id"].astype(str))):
                raw_matched = raw_topR.iloc[0:0]
                raw_matched_rule = "raw_topR_identical_to_PARC_release_omitted_nonredundant"
            else:
                raw_matched = raw_topR
                raw_matched_rule = "top_n_from_raw_prefix_matched_to_PARC_release_size_when_nonredundant"
            rows: list[dict] = []
            rows.extend(rows_for_arm(release, "PARC-release", args.n_release, args.reserve_n, "top_n_from_PARC_certified_release_by_frozen_utility"))
            rows.extend(rows_for_arm(raw_only, "raw-only rejected tail", args.n_raw_only, args.reserve_n, "top_n_from_raw_topK_minus_PARC_release_by_frozen_utility"))
            rows.extend(rows_for_arm(raw_matched, "raw top-R matched", args.n_raw_matched, args.reserve_n, raw_matched_rule))
            selection = pd.DataFrame(rows, columns=SELECTION_EXTENDED_COLUMNS)
            primary_counts = selection[selection["primary_or_reserve"].eq("primary")].groupby("arm").size().to_dict() if not selection.empty else {}
            ready = (
                primary_counts.get("PARC-release", 0) >= args.min_analyzable_n
                and primary_counts.get("raw-only rejected tail", 0) >= args.min_analyzable_n
            )
            status_text = "selection_frozen_ready_for_DFT_export" if ready else "blocked_insufficient_release_or_raw_only_arm"
            reason = "nonempty frozen arms written; export DFT jobs next" if ready else "requires at least the minimum analyzable PARC-release and raw-only primary arms"

    status = status_frame(
        [
            {
                "stage": "selection_freeze",
                "status": status_text,
                "n_selection_rows": int(len(selection)),
                "n_primary_selected": int(selection["selected_for_dft"].map(safe_bool).sum()) if not selection.empty else 0,
                "n_reserve": int(selection["primary_or_reserve"].eq("reserve").sum()) if not selection.empty else 0,
                "completed_positive_result": False,
                "blocks_DFT_submission": status_text != "selection_frozen_ready_for_DFT_export",
                "reason": reason,
            }
        ]
    )

    write_with_provenance(out_dir / "selection_frozen.csv", selection, command, inputs)
    write_with_provenance(out_dir / "table_selection_freeze_status.csv", status, command, inputs)
    refresh_manifest(out_dir)
    print(f"wrote {out_dir / 'selection_frozen.csv'}")


if __name__ == "__main__":
    main()
