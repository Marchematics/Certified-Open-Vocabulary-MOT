#!/usr/bin/env python3
"""Run verified-positive contamination sensitivity for PARC release rows.

The formal PARC guarantee assumes that verified positives removed from the
calibration null superset are genuinely positive.  This diagnostic deliberately
breaks that assumption before release by adding a predeclared fraction of false
calibration candidates to the observed-positive set, then recomputes the same
block e-values and SCS release rule.  Rows with nonzero contamination are
assumption-violation diagnostics, not formal guarantees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from scripts import build_materials_threshold_robustness as materials_threshold
from scripts.run_verified_positive_removal_load_bearing_ablation import (
    bool_series,
    compute_evalues_from_null,
    empty_reason,
    observed_positive_mask,
    scs_release_count,
    split_ids,
)


DEFAULT_SEEDS = list(range(20))
DEFAULT_CONTAMINATION_RATES = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10]
CONTAMINATION_MODES = ["random", "adversarial"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_csv_list(value: str, cast):
    return [cast(item) for item in str(value).split(",") if str(item).strip()]


def contaminate_calibration_observed(
    *,
    cal: pd.DataFrame,
    cal_observed_true: np.ndarray,
    label_col: str,
    score_col: str,
    epsilon: float,
    mode: str,
    seed: int,
) -> tuple[np.ndarray, int, int, float]:
    """Return calibration observed mask after adding false verified positives."""

    observed = np.asarray(cal_observed_true, dtype=bool).copy()
    n_true_observed = int(observed.sum())
    false_local = np.flatnonzero(~cal[label_col].to_numpy(dtype=bool))
    n_inject = int(round(float(epsilon) * max(1, n_true_observed)))
    if n_inject <= 0 or len(false_local) == 0:
        return observed, n_true_observed, 0, 0.0

    n_inject = min(n_inject, len(false_local))
    if mode == "adversarial":
        scores = cal[score_col].to_numpy(dtype=float)
        chosen = false_local[np.argsort(scores[false_local])[::-1][:n_inject]]
    elif mode == "random":
        rng = np.random.default_rng(seed + 104729)
        chosen = rng.choice(false_local, size=n_inject, replace=False)
    else:
        raise ValueError(f"unknown contamination mode: {mode}")

    observed[chosen] = True
    realized = n_inject / max(1, n_true_observed + n_inject)
    return observed, n_true_observed, int(n_inject), float(realized)


def run_target_row(
    *,
    frame: pd.DataFrame,
    target_row: str,
    domain: str,
    dataset: str,
    proposal_source: str,
    unit: str,
    block_col: str,
    score_col: str,
    label_col: str,
    rho: float,
    alpha: float,
    budget: int,
    seeds: list[int],
    contamination_rates: list[float],
    contamination_modes: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []
    work = frame.reset_index(drop=True).copy()
    labels = work[label_col].to_numpy(dtype=bool)
    scores = work[score_col].to_numpy(dtype=float)
    block_values = work[block_col].astype(str)

    for seed in seeds:
        base_observed = observed_positive_mask(labels, scores, rho=rho, seed=seed)
        cal_blocks, test_blocks = split_ids(block_values.tolist(), seed)
        cal_mask = block_values.isin(cal_blocks).to_numpy()
        test_mask = block_values.isin(test_blocks).to_numpy()
        cal = work.loc[cal_mask].copy()
        test = work.loc[test_mask].sort_values(score_col, ascending=False).copy()
        cal_base_observed = base_observed[cal_mask]

        for epsilon in contamination_rates:
            for mode in contamination_modes:
                cal_observed, n_true_observed, n_false_injected, realized_contam = (
                    contaminate_calibration_observed(
                        cal=cal,
                        cal_observed_true=cal_base_observed,
                        label_col=label_col,
                        score_col=score_col,
                        epsilon=epsilon,
                        mode=mode,
                        seed=seed,
                    )
                )
                cal_null_mask = ~cal_observed
                evalues, diag = compute_evalues_from_null(
                    test,
                    cal,
                    block_col=block_col,
                    score_col=score_col,
                    cal_block_ids=list(cal_blocks),
                    cal_null_mask=cal_null_mask,
                    alpha=alpha,
                )
                pool = test.head(budget).copy()
                pool_e = evalues[: len(pool)]
                released, tau, margin, best_ratio = scs_release_count(pool_e, alpha=alpha, budget=budget)
                selected = pool.iloc[np.argsort(pool_e)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                actual_ftr = float((~selected[label_col].astype(bool)).mean()) if released else 0.0
                raw_ftr = float((~pool[label_col].astype(bool)).mean()) if len(pool) else 0.0
                max_observed_e = float(np.max(pool_e)) if len(pool_e) else 0.0

                rows.append(
                    {
                        "domain": domain,
                        "dataset": dataset,
                        "unit": unit,
                        "target_row": target_row,
                        "proposal_source": proposal_source,
                        "block_definition": block_col,
                        "rho": rho,
                        "alpha": alpha,
                        "K": budget,
                        "seed": seed,
                        "contamination_mode": mode,
                        "epsilon_false_verified_positive": float(epsilon),
                        "observed_true_positives_in_calibration": n_true_observed,
                        "false_candidates_injected_as_verified_positive": n_false_injected,
                        "realized_verified_positive_contamination_rate": realized_contam,
                        "removed_from_calibration_null": int(cal_observed.sum()),
                        "released": int(released),
                        "actual_FTR": actual_ftr,
                        "violates_alpha": bool(actual_ftr > alpha),
                        "raw_topK_actual_FTR": raw_ftr,
                        "best_mass_ratio": best_ratio,
                        "self_consistency_margin": margin,
                        "tau_k": tau if released else "",
                        "max_observed_e": max_observed_e,
                        "required_e": float(diag["required_e"]) if diag["required_e"] is not None else math.nan,
                        "emax_effective": diag["emax_effective"],
                        "block_coverage": diag["block_coverage"],
                        "n_cal_blocks": diag["n_cal_blocks"],
                        "n_nonempty_null_cal_blocks": diag["n_nonempty_null_cal_blocks"],
                        "empty_reason": empty_reason(released, diag, max_observed_e),
                        "evidence_status": (
                            "formal_assumption_intact_reference"
                            if float(epsilon) == 0.0
                            else "assumption_violation_sensitivity_not_formal_guarantee"
                        ),
                    }
                )
    return pd.DataFrame(rows)


def ctc_rows(args: argparse.Namespace) -> pd.DataFrame:
    frame = pd.read_csv(args.ctc_universe, low_memory=False)
    frame["_full_true"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
    rows = []
    for budget in [100, 300]:
        rows.append(
            run_target_row(
                frame=frame,
                target_row=f"ctc_learned_strict_alpha010_K{budget}",
                domain="biomedical_cell_tracking",
                dataset="Cell Tracking Challenge learned-hybrid held-out sequence",
                proposal_source="ctc_learned_hybrid_appearance_sequence_disjoint",
                unit="cell_link",
                block_col="video_id",
                score_col="score",
                label_col="_full_true",
                rho=0.10,
                alpha=0.10,
                budget=budget,
                seeds=args.seeds,
                contamination_rates=args.contamination_rates,
                contamination_modes=args.contamination_modes,
            )
        )
    return pd.concat(rows, ignore_index=True)


def materials_rows(args: argparse.Namespace) -> pd.DataFrame:
    frame, _meta = materials_threshold.load_frame(args)
    specs = [
        {
            "target_row": "materials_cgcnn_exact_stable_alpha010_K100",
            "source": "cgcnn_ensemble_learned_materials_model",
            "score_col": "cgcnn_score",
            "label_col": "stable_exact",
            "budget": 100,
            "frame": frame,
        },
        {
            "target_row": "materials_alignn_exact_stable_alpha010_K300",
            "source": "alignn_ff_modern_learned_materials_model",
            "score_col": "alignn_score",
            "label_col": "stable_exact",
            "budget": 300,
            "frame": frame,
        },
        {
            "target_row": "materials_alignn_exact_stable_alpha010_K500",
            "source": "alignn_ff_modern_learned_materials_model",
            "score_col": "alignn_score",
            "label_col": "stable_exact",
            "budget": 500,
            "frame": frame,
        },
    ]
    rows = []
    for spec in specs:
        rows.append(
            run_target_row(
                frame=spec["frame"],
                target_row=spec["target_row"],
                domain="materials_discovery",
                dataset="Matbench Discovery WBM unique prototypes",
                proposal_source=spec["source"],
                unit="stable_inorganic_crystal_candidate",
                block_col="composition_family_pair",
                score_col=spec["score_col"],
                label_col=spec["label_col"],
                rho=0.10,
                alpha=0.10,
                budget=spec["budget"],
                seeds=args.seeds,
                contamination_rates=args.contamination_rates,
                contamination_modes=args.contamination_modes,
            )
        )
    return pd.concat(rows, ignore_index=True)


def summarize(seed_rows: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "domain",
        "dataset",
        "unit",
        "target_row",
        "proposal_source",
        "block_definition",
        "rho",
        "alpha",
        "K",
        "contamination_mode",
        "epsilon_false_verified_positive",
    ]
    rows: list[dict] = []
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["released"].astype(int) > 0).sum()),
                "release_rate": float((group["released"].astype(int) > 0).mean()),
                "mean_release": float(group["released"].astype(float).mean()),
                "min_release": int(group["released"].astype(int).min()),
                "max_release": int(group["released"].astype(int).max()),
                "actual_FTR_mean": float(group["actual_FTR"].astype(float).mean()),
                "actual_FTR_max": float(group["actual_FTR"].astype(float).max()),
                "violation_rate": float(group["violates_alpha"].astype(bool).mean()),
                "raw_topK_actual_FTR_mean": float(group["raw_topK_actual_FTR"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_e"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
                "observed_true_positives_in_calibration_mean": float(
                    group["observed_true_positives_in_calibration"].astype(float).mean()
                ),
                "false_candidates_injected_as_verified_positive_mean": float(
                    group["false_candidates_injected_as_verified_positive"].astype(float).mean()
                ),
                "realized_verified_positive_contamination_rate_mean": float(
                    group["realized_verified_positive_contamination_rate"].astype(float).mean()
                ),
                "dominant_empty_reason": (
                    group["empty_reason"].dropna().mode().iloc[0]
                    if not group["empty_reason"].dropna().empty
                    else ""
                ),
                "evidence_status": (
                    "formal_assumption_intact_reference"
                    if float(row["epsilon_false_verified_positive"]) == 0.0
                    else "assumption_violation_sensitivity_not_formal_guarantee"
                ),
                "paper_role": "verification_assumption_boundary_diagnostic",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def write_closeout(path: Path, summary: pd.DataFrame, seed_rows: pd.DataFrame) -> None:
    nonzero = summary[summary["epsilon_false_verified_positive"].astype(float) > 0].copy()
    violation_rows = nonzero[nonzero["violation_rate"].astype(float) > 0]
    first_violation = "none_observed"
    if not violation_rows.empty:
        first = violation_rows.sort_values(["epsilon_false_verified_positive", "target_row"]).iloc[0]
        first_violation = (
            f"{first['target_row']} / {first['contamination_mode']} at "
            f"epsilon={float(first['epsilon_false_verified_positive']):.3f}"
        )
    text = (
        "# Verified-Positive Contamination Sensitivity\n\n"
        "Status: completed assumption-boundary diagnostic.\n\n"
        "This experiment deliberately violates the one-sided verified-positive reliability "
        "assumption by injecting false calibration candidates into the observed-positive set "
        "before null-superset removal. Nonzero-contamination rows are not formal PARC "
        "guarantees; they are stress tests that show when release should be interpreted as "
        "requiring refusal, audit, or stronger verification.\n\n"
        f"- Target rows: {summary['target_row'].nunique()}\n"
        f"- Seed-level rows: {len(seed_rows)}\n"
        f"- Contamination rates: {', '.join(str(x) for x in sorted(summary['epsilon_false_verified_positive'].unique()))}\n"
        f"- Contamination modes: {', '.join(sorted(summary['contamination_mode'].unique()))}\n"
        f"- First alpha-violation diagnostic row: {first_violation}\n\n"
        "## Claim Boundary\n\n"
        "- Allowed: verification-assumption boundary diagnostic; shows how release/refusal changes under controlled assumption violation.\n"
        "- Forbidden: robustness theorem under contaminated positives; prospective discovery; completed external audit.\n"
    )
    path.write_text(text, encoding="utf-8")


def update_manifest(out_dir: Path) -> None:
    rows = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(out_dir).as_posix()}")
    (out_dir / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ctc-universe",
        default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1/candidate_universe.csv",
    )
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    parser.add_argument("--out-dir", default="outputs/milestones/verification_assumption_sensitivity")
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument(
        "--contamination-rates",
        default=",".join(str(rate) for rate in DEFAULT_CONTAMINATION_RATES),
    )
    parser.add_argument("--contamination-modes", default=",".join(CONTAMINATION_MODES))
    args = parser.parse_args()
    args.seeds = parse_csv_list(args.seeds, int)
    args.contamination_rates = parse_csv_list(args.contamination_rates, float)
    args.contamination_modes = parse_csv_list(args.contamination_modes, str)

    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seed_rows = pd.concat([ctc_rows(args), materials_rows(args)], ignore_index=True)
    summary = summarize(seed_rows)

    seed_path = out_dir / "table_verified_positive_contamination_sensitivity_seed_rows.csv"
    summary_path = out_dir / "table_verified_positive_contamination_sensitivity_summary.csv"
    figure_path = out_dir / "figure_verified_positive_contamination_sensitivity_source.csv"
    closeout_path = out_dir / "VERIFICATION_ASSUMPTION_SENSITIVITY_CLOSEOUT.md"
    provenance_path = out_dir / "provenance.json"

    seed_rows.to_csv(seed_path, index=False)
    summary.to_csv(summary_path, index=False)
    summary[
        [
            "domain",
            "target_row",
            "K",
            "contamination_mode",
            "epsilon_false_verified_positive",
            "release_rate",
            "mean_release",
            "actual_FTR_mean",
            "actual_FTR_max",
            "violation_rate",
            "best_mass_ratio_mean",
            "evidence_status",
        ]
    ].to_csv(figure_path, index=False)
    write_closeout(closeout_path, summary, seed_rows)
    provenance = {
        "status": "completed",
        "role": "verification_assumption_boundary_diagnostic",
        "runtime_sec": time.perf_counter() - started,
        "target_rows": sorted(summary["target_row"].unique().tolist()),
        "seeds": args.seeds,
        "contamination_rates": args.contamination_rates,
        "contamination_modes": args.contamination_modes,
        "inputs": {
            "ctc_universe_sha256": sha256_file(Path(args.ctc_universe)),
            "wbm_summary_sha256": sha256_file(Path(args.wbm_summary)),
            "cgcnn_predictions_sha256": sha256_file(Path(args.cgcnn_predictions)),
            "alignn_predictions_sha256": sha256_file(Path(args.alignn_predictions)),
        },
        "outputs": {
            "seed_rows": str(seed_path),
            "summary": str(summary_path),
            "figure_source": str(figure_path),
            "closeout": str(closeout_path),
        },
        "claim_boundary": "Nonzero contamination rows are assumption-violation diagnostics, not formal guarantees.",
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
