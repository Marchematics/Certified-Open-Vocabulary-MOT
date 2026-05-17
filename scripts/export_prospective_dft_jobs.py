#!/usr/bin/env python3
"""Export a public-safe DFT job manifest for frozen prospective arms."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from materials_prospective_dft_pipeline import (
    DEFAULT_OUT,
    DFT_JOB_COLUMNS,
    SELECTION_EXTENDED_COLUMNS,
    empty_frame,
    public_safe_inputs,
    refresh_manifest,
    safe_bool,
    selected_primary,
    status_frame,
    write_with_provenance,
)


def slug(text: str) -> str:
    return text.lower().replace(" ", "-").replace("_", "-")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", default=None)
    parser.add_argument("--out", "--out-dir", dest="out_dir", default=str(DEFAULT_OUT))
    parser.add_argument("--dft-engine", default="VASP-or-equivalent-MP-compatible-engine")
    parser.add_argument("--input-set", default="MPRelaxSet-compatible")
    parser.add_argument("--functional", default="PBE-GGA")
    parser.add_argument("--encut-ev", default="520")
    parser.add_argument("--kpoint-policy", default="MPRelaxSet default or fixed equivalent recorded per job")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = "python scripts/export_prospective_dft_jobs.py"
    selection_path = Path(args.selection) if args.selection else out_dir / "selection_frozen.csv"
    inputs = public_safe_inputs(selection=selection_path if selection_path.exists() else None)

    if not selection_path.exists():
        selection = empty_frame(SELECTION_EXTENDED_COLUMNS)
        jobs = empty_frame(DFT_JOB_COLUMNS)
        status_text = "blocked_missing_selection"
        reason = "run select_prospective_dft_arms_from_pool.py before exporting DFT jobs"
    else:
        selection = pd.read_csv(selection_path)
        primary = selected_primary(selection)
        if primary.empty:
            jobs = empty_frame(DFT_JOB_COLUMNS)
            status_text = "blocked_empty_primary_selection"
            reason = "DFT jobs are exported only for frozen primary arm candidates"
        else:
            rows: list[dict] = []
            updated = selection.copy()
            for idx, row in primary.iterrows():
                source_rank = pd.to_numeric(row.get("source_rank", ""), errors="coerce")
                rank_value = int(source_rank) if pd.notna(source_rank) else len(rows) + 1
                job_id = f"dft-{slug(str(row['arm']))}-{rank_value:04d}"
                rows.append(
                    {
                        "dft_job_id": job_id,
                        "candidate_id": row["candidate_id"],
                        "arm": row["arm"],
                        "dft_engine": args.dft_engine,
                        "input_set": args.input_set,
                        "functional": args.functional,
                        "encut_ev": args.encut_ev,
                        "kpoint_policy": args.kpoint_policy,
                        "electronic_convergence_ev": "1e-5",
                        "force_convergence_ev_per_angstrom": "0.02",
                        "spin_policy": "same frozen magnetic-element rule for all arms",
                        "relaxation_policy": "full cell plus ionic relaxation",
                        "static_calculation_policy": "final static calculation after relaxation",
                        "failure_policy": "one standard rerun; unresolved failures count as not-certified-stable in conservative primary analysis",
                        "evidence_status": "DFT_job_manifest_frozen_before_outcomes",
                    }
                )
                updated.loc[idx, "dft_job_id"] = job_id
            selection = updated
            jobs = pd.DataFrame(rows, columns=DFT_JOB_COLUMNS)
            status_text = "DFT_manifest_ready"
            reason = "public-safe DFT job manifest written; raw DFT inputs are generated outside the public bundle"

    status = status_frame(
        [
            {
                "stage": "dft_job_export",
                "status": status_text,
                "n_jobs": int(len(jobs)),
                "n_arms": int(jobs["arm"].nunique()) if not jobs.empty else 0,
                "completed_positive_result": False,
                "blocks_DFT_submission": status_text != "DFT_manifest_ready",
                "reason": reason,
            }
        ]
    )

    dft_inputs = out_dir / "dft_inputs"
    dft_inputs.mkdir(parents=True, exist_ok=True)
    (dft_inputs / "README.md").write_text(
        "This public-safe package stores the frozen DFT job manifest only. "
        "Raw DFT input decks are generated from private structure files outside the public bundle.\n",
        encoding="utf-8",
    )
    (out_dir / "dft_outputs").mkdir(parents=True, exist_ok=True)
    (out_dir / "dft_outputs" / "README.md").write_text(
        "Raw DFT outputs are excluded unless separately sanitized and released.\n",
        encoding="utf-8",
    )
    write_with_provenance(out_dir / "selection_frozen.csv", selection, command, inputs)
    write_with_provenance(out_dir / "dft_job_manifest.csv", jobs, command, inputs)
    write_with_provenance(out_dir / "table_dft_job_export_status.csv", status, command, inputs)
    refresh_manifest(out_dir)
    print(f"wrote {out_dir / 'dft_job_manifest.csv'}")


if __name__ == "__main__":
    main()
