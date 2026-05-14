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


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


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
        if ratio > best_ratio:
            best_ratio = ratio
        if margin > best_margin:
            best_margin = margin
            best_tau = tau
        if sorted_e[k - 1] >= tau:
            released = k
    if released:
        tau = M / (alpha * released)
        margin = float(sorted_e[released - 1] - tau)
        return released, tau, margin, best_ratio
    return 0, best_tau, best_margin, best_ratio


def split_video_ids(video_ids: list[int], seed: int, tune_ratio: float, cal_ratio: float) -> dict[int, str]:
    ordered = sorted(set(int(video_id) for video_id in video_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    tune_end = int(round(len(ordered) * tune_ratio))
    cal_end = tune_end + int(round(len(ordered) * cal_ratio))
    mapping = {}
    for idx, video_id in enumerate(ordered):
        if idx < tune_end:
            mapping[video_id] = "tune"
        elif idx < cal_end:
            mapping[video_id] = "cal"
        else:
            mapping[video_id] = "test"
    return mapping


def observed_true_mask(full_true: pd.Series, scores: pd.Series, rho: float, seed: int, strategy: str) -> np.ndarray:
    true_indices = np.flatnonzero(full_true.to_numpy(dtype=bool))
    observed = np.zeros(len(full_true), dtype=bool)
    if rho >= 1.0:
        observed[true_indices] = True
        return observed
    if rho <= 0.0 or len(true_indices) == 0:
        return observed
    n_observed = int(round(len(true_indices) * rho))
    if strategy == "top_score":
        score_values = scores.to_numpy(dtype=float)
        order = true_indices[np.argsort(score_values[true_indices])[::-1]]
        chosen = order[:n_observed]
    else:
        rng = np.random.default_rng(seed + int(round(rho * 10000)) * 100003)
        chosen = rng.choice(true_indices, size=n_observed, replace=False)
    observed[chosen] = True
    return observed


def compute_evalues(test: pd.DataFrame, cal: pd.DataFrame, cal_video_ids: list[int], alpha: float) -> tuple[np.ndarray, dict]:
    null_cal = cal[cal["_partial_null"].astype(bool)].copy()
    if null_cal.empty:
        maxima = np.asarray([], dtype=float)
    else:
        maxima = null_cal.groupby("video_id")["score"].max().astype(float).to_numpy()
    n_nonempty = int(len(maxima))
    n_empty = max(0, len(cal_video_ids) - n_nonempty)
    p_min_block = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    p_min_effective = min(1.0, p_min_block)
    gamma = gamma_star_from_p(p_min_effective)
    emax_eff = emax_from_p(gamma, p_min_effective)
    required_emax = 1.0 / alpha if alpha > 0 else None
    if gamma is None or len(test) == 0 or len(maxima) == 0:
        return np.zeros(len(test), dtype=float), {
            "n_cal_total": len(cal_video_ids),
            "n_nonempty": n_nonempty,
            "n_empty": n_empty,
            "p_min_effective": p_min_effective,
            "gamma": gamma,
            "emax_effective": emax_eff,
            "required_emax": required_emax,
            "release_feasible_resolution": False,
        }
    maxima_sorted = np.sort(maxima)
    scores = test["score"].astype(float).to_numpy()
    exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
    p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
    p_any = np.minimum(1.0, p_block)
    evalues = gamma * (p_any ** (gamma - 1.0))
    return evalues.astype(float), {
        "n_cal_total": len(cal_video_ids),
        "n_nonempty": n_nonempty,
        "n_empty": n_empty,
        "p_min_effective": p_min_effective,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_emax": required_emax,
        "release_feasible_resolution": bool(emax_eff is not None and required_emax is not None and emax_eff >= required_emax),
    }


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

    fig, ax1 = plt.subplots(figsize=(5.2, 3.2))
    for rho, group in grouped.groupby("rho"):
        ax1.plot(group["M"], group["released_mean"], marker="o", label=f"rho={rho:g}")
    ax1.set_xscale("log")
    ax1.set_xlabel("Requested candidate budget M")
    ax1.set_ylabel("Mean PARC released links")
    ax1.grid(True, alpha=0.25)
    ax1.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(out_dir / "figure_ctc_release_vs_M.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for M, group in grouped[grouped["M"].isin([100, 300, 500])].groupby("M"):
        ax.plot(group["rho"], group["released_mean"], marker="o", label=f"M={M}")
    ax.set_xlabel("Observed positive fraction rho")
    ax.set_ylabel("Mean PARC released links at alpha=0.20")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "figure_ctc_partial_verification_power.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", default="outputs/ctc_link_certification/universe_gt_tra_noisy_w90_win5/candidate_universe.csv")
    parser.add_argument("--out-dir", default="outputs/ctc_link_certification/partial_verification_sweep")
    parser.add_argument("--rhos", default="0.05,0.10,0.25,0.50,1.00")
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--budgets", default="100,300,500")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    parser.add_argument("--tune-ratio", type=float, default=1 / 6)
    parser.add_argument("--cal-ratio", type=float, default=1 / 2)
    parser.add_argument("--observed-positive-strategy", choices=["random", "top_score"], default="random")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    universe = pd.read_csv(args.candidate_universe)
    universe["video_id"] = universe["video_id"].astype(int)
    universe["_full_false"] = bool_series(universe["is_unmatched"])
    universe["_full_true"] = ~universe["_full_false"]
    universe = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)

    rhos = parse_list(args.rhos, float)
    alphas = parse_list(args.alphas, float)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)

    rows: list[dict] = []
    per_dataset_rows: list[dict] = []
    for rho in rhos:
        for seed in seeds:
            observed = observed_true_mask(
                universe["_full_true"],
                universe["score"],
                rho=rho,
                seed=seed,
                strategy=args.observed_positive_strategy,
            )
            work = universe.copy()
            work["_observed_positive"] = observed
            work["_partial_null"] = ~work["_observed_positive"]
            split_map = split_video_ids(work["video_id"].tolist(), seed=seed, tune_ratio=args.tune_ratio, cal_ratio=args.cal_ratio)
            work["_split"] = work["video_id"].map(split_map)
            cal = work[work["_split"] == "cal"].copy()
            test = work[work["_split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
            cal_video_ids = sorted(cal["video_id"].unique().tolist())
            for alpha in alphas:
                evalues, diag = compute_evalues(test, cal, cal_video_ids=cal_video_ids, alpha=alpha)
                test = test.copy()
                test["_evalue"] = evalues
                max_observed_e = float(np.max(evalues)) if len(evalues) else None
                for M in budgets:
                    pool = test.head(M).copy()
                    pool_e = pool["_evalue"].to_numpy(dtype=float)
                    released, tau, margin, best_mass_ratio = scs_release_count(pool_e, alpha=alpha, M=M)
                    selected = pool.iloc[np.argsort(pool_e)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                    actual_ftr = float(selected["_full_false"].mean()) if released else 0.0
                    partial_utr = float(selected["_partial_null"].mean()) if released else 0.0
                    raw_ftr = float(pool["_full_false"].mean()) if len(pool) else 0.0
                    raw_partial_unsupported = float(pool["_partial_null"].mean()) if len(pool) else 0.0
                    reason = empty_reason(released, diag, max_observed_e)
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
                            "raw_topM_partial_unsupported_rate": raw_partial_unsupported,
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
                            "empty_reason": reason,
                        }
                    )
                    for dataset, group in selected.groupby("ctc_dataset") if released else []:
                        per_dataset_rows.append(
                            {
                                "rho": rho,
                                "observed_positive_strategy": args.observed_positive_strategy,
                                "alpha": alpha,
                                "seed": seed,
                                "M": M,
                                "ctc_dataset": dataset,
                                "released": int(len(group)),
                                "actual_FTR": float(group["_full_false"].mean()) if len(group) else 0.0,
                                "partial_UTR_seen_by_PARC": float(group["_partial_null"].mean()) if len(group) else 0.0,
                            }
                        )

    sweep = pd.DataFrame(rows)
    sweep_path = out_dir / "table_ctc_partial_verification_sweep.csv"
    sweep.to_csv(sweep_path, index=False)
    per_dataset = pd.DataFrame(per_dataset_rows)
    per_dataset_path = out_dir / "table_ctc_partial_verification_per_dataset_raw.csv"
    per_dataset.to_csv(per_dataset_path, index=False)

    main = sweep[(sweep["rho"] == 1.0) & (sweep["alpha"] == 0.20)].groupby("M").agg(
        seeds=("seed", "nunique"),
        nonempty_seeds=("released", lambda s: int((s > 0).sum())),
        released_mean=("released", "mean"),
        released_std=("released", lambda s: float(s.std(ddof=0))),
        actual_FTR_mean=("actual_FTR", "mean"),
        actual_FTR_max=("actual_FTR", "max"),
        raw_topM_actual_FTR=("raw_topM_actual_FTR", "mean"),
        partial_UTR_mean=("partial_UTR_seen_by_PARC", "mean"),
    ).reset_index()
    main.insert(0, "alpha", 0.20)
    main.insert(0, "observed_positive_strategy", args.observed_positive_strategy)
    main.to_csv(out_dir / "table_ctc_main_alpha020.csv", index=False)

    dataset_meta = universe.groupby("ctc_dataset").agg(
        candidates=("path_id", "count"),
        gt_supported=("_full_true", "sum"),
        blocks=("video_id", "nunique"),
    ).reset_index()
    pds = per_dataset[(per_dataset["rho"] == 1.0) & (per_dataset["alpha"] == 0.20) & (per_dataset["M"].isin([300, 500]))]
    if not pds.empty:
        breakdown = pds.groupby(["ctc_dataset", "M"]).agg(
            parc_nonempty_seeds=("released", "count"),
            mean_release_size=("released", "mean"),
            actual_FTR_mean=("actual_FTR", "mean"),
            actual_FTR_max=("actual_FTR", "max"),
        ).reset_index()
    else:
        breakdown = pd.DataFrame(columns=["ctc_dataset", "M", "parc_nonempty_seeds", "mean_release_size", "actual_FTR_mean", "actual_FTR_max"])
    raw_rows = []
    for M in [300, 500]:
        pool = universe.head(M).copy()
        for dataset, group in pool.groupby("ctc_dataset"):
            raw_rows.append({"ctc_dataset": dataset, "M": M, "raw_topM_FTR": float(group["_full_false"].mean()), "raw_topM_count": int(len(group))})
    raw_breakdown = pd.DataFrame(raw_rows)
    breakdown = dataset_meta.merge(breakdown, on="ctc_dataset", how="left").merge(raw_breakdown, on=["ctc_dataset", "M"], how="left")
    breakdown.to_csv(out_dir / "table_ctc_per_dataset_breakdown.csv", index=False)

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
            "main_alpha020": str(out_dir / "table_ctc_main_alpha020.csv"),
            "per_dataset_breakdown": str(out_dir / "table_ctc_per_dataset_breakdown.csv"),
            "figure_release_vs_M": str(out_dir / "figure_ctc_release_vs_M.pdf"),
            "figure_partial_verification_power": str(out_dir / "figure_ctc_partial_verification_power.pdf"),
        },
    }
    with (out_dir / "CTC_PARTIAL_VERIFICATION_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
