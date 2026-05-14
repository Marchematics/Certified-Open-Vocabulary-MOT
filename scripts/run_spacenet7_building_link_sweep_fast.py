#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_list(value: str, cast):
    return [cast(item) for item in value.split(",") if item.strip()]


def bool_array(series: pd.Series) -> np.ndarray:
    return series.astype(str).str.lower().isin(["true", "1", "yes"]).to_numpy(dtype=bool)


def gamma_star_from_p(p_value: float | None) -> float | None:
    if p_value is None or p_value <= 0.0 or p_value >= 1.0:
        return None
    gamma = -1.0 / math.log(p_value)
    return gamma if 0.0 < gamma < 1.0 else None


def emax_from_p(gamma: float | None, p_value: float | None) -> float | None:
    if gamma is None or p_value is None or p_value <= 0.0 or p_value > 1.0:
        return None
    return gamma * (p_value ** (gamma - 1.0))


def scs_release_count(evalues: np.ndarray, alpha: float, M: int) -> tuple[int, float, float, float]:
    if len(evalues) == 0:
        return 0, math.inf, -math.inf, 0.0
    sorted_e = np.sort(evalues.astype(float))[::-1]
    best_ratio = 0.0
    best_margin = -math.inf
    best_tau = math.inf
    released = 0
    for k in range(1, len(sorted_e) + 1):
        tau = M / (alpha * k)
        margin = float(sorted_e[k - 1] - tau)
        ratio = float(alpha * k * sorted_e[k - 1] / M)
        best_ratio = max(best_ratio, ratio)
        if margin > best_margin:
            best_margin = margin
            best_tau = tau
        if sorted_e[k - 1] >= tau:
            released = k
    if released:
        tau = M / (alpha * released)
        return released, tau, float(sorted_e[released - 1] - tau), best_ratio
    return 0, best_tau, best_margin, best_ratio


def split_blocks(block_ids: np.ndarray, seed: int, tune_ratio: float, cal_ratio: float) -> tuple[np.ndarray, np.ndarray, list[int]]:
    ordered = sorted(set(int(v) for v in block_ids.tolist()))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    tune_end = int(round(len(ordered) * tune_ratio))
    cal_end = tune_end + int(round(len(ordered) * cal_ratio))
    cal_blocks = set(ordered[tune_end:cal_end])
    test_blocks = set(ordered[cal_end:])
    cal_mask = np.fromiter((int(v) in cal_blocks for v in block_ids), dtype=bool, count=len(block_ids))
    test_mask = np.fromiter((int(v) in test_blocks for v in block_ids), dtype=bool, count=len(block_ids))
    return cal_mask, test_mask, sorted(cal_blocks)


def observed_true_mask(full_true: np.ndarray, scores: np.ndarray, rho: float, seed: int, strategy: str) -> np.ndarray:
    true_indices = np.flatnonzero(full_true)
    observed = np.zeros(len(full_true), dtype=bool)
    if rho >= 1.0:
        observed[true_indices] = True
        return observed
    if rho <= 0.0 or len(true_indices) == 0:
        return observed
    n_observed = max(1, int(round(len(true_indices) * rho)))
    if strategy == "top_score":
        order = true_indices[np.argsort(scores[true_indices])[::-1]]
        chosen = order[:n_observed]
    else:
        rng = np.random.default_rng(seed + int(round(rho * 10000)) * 100003)
        chosen = rng.choice(true_indices, size=n_observed, replace=False)
    observed[chosen] = True
    return observed


def compute_test_evalues(
    scores: np.ndarray,
    block_ids: np.ndarray,
    cal_null_mask: np.ndarray,
    test_indices: np.ndarray,
    cal_blocks: list[int],
    alpha: float,
) -> tuple[np.ndarray, dict]:
    if cal_null_mask.any():
        cal_df = pd.DataFrame({"video_id": block_ids[cal_null_mask], "score": scores[cal_null_mask]})
        maxima = cal_df.groupby("video_id", sort=False)["score"].max().to_numpy(dtype=float)
    else:
        maxima = np.asarray([], dtype=float)
    n_nonempty = int(len(maxima))
    n_empty = max(0, len(cal_blocks) - n_nonempty)
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required_emax = 1.0 / alpha if alpha > 0 else None
    diag = {
        "n_cal_total": len(cal_blocks),
        "n_nonempty": n_nonempty,
        "n_empty": n_empty,
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_emax": required_emax,
    }
    if gamma is None or len(test_indices) == 0 or len(maxima) == 0:
        return np.zeros(len(test_indices), dtype=float), diag
    maxima_sorted = np.sort(maxima)
    test_scores = scores[test_indices]
    exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, test_scores, side="left")
    p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
    p_any = np.minimum(1.0, p_block)
    return (gamma * (p_any ** (gamma - 1.0))).astype(float), diag


def empty_reason(released: int, diag: dict, max_observed_e: float | None) -> str:
    if released:
        return ""
    required = diag.get("required_emax")
    emax = diag.get("emax_effective")
    if required is not None and (emax is None or float(emax) < float(required)):
        return "resolution_below_required_emax"
    if required is not None and (max_observed_e is None or float(max_observed_e) < float(required)):
        return "observed_e_below_required_emax"
    return "insufficient_high_e_mass_for_uniform_scs"


def plot_outputs(out_dir: Path, sweep: pd.DataFrame) -> None:
    alpha02 = sweep[sweep["alpha"] == 0.20].copy()
    grouped = alpha02.groupby(["rho", "M"]).agg(
        released_mean=("released", "mean"),
        actual_ftr_mean=("actual_FTR", "mean"),
        raw_ftr_mean=("raw_topM_actual_FTR", "mean"),
    ).reset_index()
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for rho, group in grouped.groupby("rho"):
        ax.plot(group["M"], group["released_mean"], marker="o", label=f"rho={rho:g}")
    ax.set_xscale("log")
    ax.set_xlabel("Requested building-link budget M")
    ax.set_ylabel("Mean PARC released links")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(out_dir / "figure_spacenet7_release_vs_M.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", default="outputs/spacenet7_building_links/universe_geometry_w35_aoi18/candidate_universe.csv")
    parser.add_argument("--out-dir", default="outputs/spacenet7_building_links/partial_verification_sweep_topscore_aoi18")
    parser.add_argument("--rhos", default="0.10,0.25,0.50,1.00")
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--budgets", default="100,300,500,5000")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    parser.add_argument("--tune-ratio", type=float, default=1 / 6)
    parser.add_argument("--cal-ratio", type=float, default=1 / 2)
    parser.add_argument("--observed-positive-strategy", choices=["random", "top_score"], default="top_score")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    usecols = ["video_id", "score", "is_unmatched", "aoi", "candidate_rank"]
    universe = pd.read_csv(args.candidate_universe, usecols=usecols)
    universe = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)
    block_ids = universe["video_id"].astype(int).to_numpy()
    scores = universe["score"].astype(float).to_numpy()
    full_false = bool_array(universe["is_unmatched"])
    full_true = ~full_false
    aois = universe["aoi"].astype(str).to_numpy()

    rhos = parse_list(args.rhos, float)
    alphas = parse_list(args.alphas, float)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)

    rows: list[dict] = []
    per_aoi_rows: list[dict] = []
    for rho in rhos:
        for seed in seeds:
            observed = observed_true_mask(full_true, scores, rho, seed, args.observed_positive_strategy)
            partial_null = ~observed
            cal_mask, test_mask, cal_blocks = split_blocks(block_ids, seed, args.tune_ratio, args.cal_ratio)
            test_indices = np.flatnonzero(test_mask)
            cal_null_mask = cal_mask & partial_null
            for alpha in alphas:
                test_evalues, diag = compute_test_evalues(scores, block_ids, cal_null_mask, test_indices, cal_blocks, alpha)
                max_observed_e = float(np.max(test_evalues)) if len(test_evalues) else None
                for M in budgets:
                    pool_indices = test_indices[: min(M, len(test_indices))]
                    pool_e = test_evalues[: len(pool_indices)]
                    released, tau, margin, best_mass_ratio = scs_release_count(pool_e, alpha, M)
                    if released:
                        selected_local = np.argsort(pool_e)[::-1][:released]
                        selected_indices = pool_indices[selected_local]
                        actual_ftr = float(full_false[selected_indices].mean())
                        partial_utr = float(partial_null[selected_indices].mean())
                    else:
                        selected_indices = np.asarray([], dtype=int)
                        actual_ftr = 0.0
                        partial_utr = 0.0
                    raw_ftr = float(full_false[pool_indices].mean()) if len(pool_indices) else 0.0
                    raw_partial = float(partial_null[pool_indices].mean()) if len(pool_indices) else 0.0
                    rows.append(
                        {
                            "rho": rho,
                            "observed_positive_strategy": args.observed_positive_strategy,
                            "alpha": alpha,
                            "seed": seed,
                            "M": M,
                            "released": int(released),
                            "actual_FTR": actual_ftr,
                            "partial_UTR_seen_by_PARC": partial_utr,
                            "raw_topM_actual_FTR": raw_ftr,
                            "raw_topM_partial_unsupported_rate": raw_partial,
                            "n_cal_blocks": int(diag["n_cal_total"]),
                            "n_nonempty_null_cal_blocks": int(diag["n_nonempty"]),
                            "p_min_effective": diag["p_min_effective"],
                            "gamma": diag["gamma"],
                            "emax_effective": diag["emax_effective"],
                            "required_emax": diag["required_emax"],
                            "max_observed_e": max_observed_e,
                            "best_mass_ratio": best_mass_ratio,
                            "tau_k": tau if released else "",
                            "self_consistency_margin": margin if released else "",
                            "empty_reason": empty_reason(released, diag, max_observed_e),
                        }
                    )
                    if released:
                        selected_aois, counts = np.unique(aois[selected_indices], return_counts=True)
                        for aoi, count in zip(selected_aois.tolist(), counts.tolist(), strict=False):
                            mask = aois[selected_indices] == aoi
                            per_aoi_rows.append(
                                {
                                    "rho": rho,
                                    "observed_positive_strategy": args.observed_positive_strategy,
                                    "alpha": alpha,
                                    "seed": seed,
                                    "M": M,
                                    "aoi": aoi,
                                    "released": int(count),
                                    "actual_FTR": float(full_false[selected_indices][mask].mean()) if count else 0.0,
                                    "partial_UTR_seen_by_PARC": float(partial_null[selected_indices][mask].mean()) if count else 0.0,
                                }
                            )

    sweep = pd.DataFrame(rows)
    sweep_path = out_dir / "table_spacenet7_partial_verification_sweep.csv"
    sweep.to_csv(sweep_path, index=False)
    pd.DataFrame(per_aoi_rows).to_csv(out_dir / "table_spacenet7_per_aoi_release_raw.csv", index=False)
    main = sweep[sweep["alpha"] == 0.20].groupby(["rho", "M"]).agg(
        seeds=("seed", "nunique"),
        nonempty_seeds=("released", lambda s: int((s > 0).sum())),
        released_mean=("released", "mean"),
        released_std=("released", lambda s: float(s.std(ddof=0))),
        actual_FTR_mean=("actual_FTR", "mean"),
        actual_FTR_max=("actual_FTR", "max"),
        raw_topM_actual_FTR=("raw_topM_actual_FTR", "mean"),
        partial_UTR_mean=("partial_UTR_seen_by_PARC", "mean"),
        best_mass_ratio_mean=("best_mass_ratio", "mean"),
    ).reset_index()
    main.insert(0, "alpha", 0.20)
    main.insert(0, "observed_positive_strategy", args.observed_positive_strategy)
    main.to_csv(out_dir / "table_spacenet7_main_alpha020.csv", index=False)
    plot_outputs(out_dir, sweep)

    report = {
        "status": "completed",
        "candidate_universe": str(args.candidate_universe),
        "rows": int(len(sweep)),
        "rho_grid": rhos,
        "observed_positive_strategy": args.observed_positive_strategy,
        "alpha_grid": alphas,
        "M_grid": budgets,
        "seeds": seeds,
        "tables": {
            "partial_verification_sweep": str(sweep_path),
            "main_alpha020": str(out_dir / "table_spacenet7_main_alpha020.csv"),
            "figure_release_vs_M": str(out_dir / "figure_spacenet7_release_vs_M.pdf"),
        },
    }
    with (out_dir / "SPACENET7_PARTIAL_VERIFICATION_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
