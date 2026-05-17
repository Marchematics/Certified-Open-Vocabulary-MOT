#!/usr/bin/env python3
"""Build a quasi-prospective materials computational follow-up trial.

This script freezes a public-label computational decision replay: model scores,
composition-family block splits, observed stable positives in pre-release
calibration blocks, requested follow-up budgets, and PARC release/refusal rules
are fixed before evaluating the held-out follow-up labels. It does not run new
DFT and must not be described as experimental synthesis or true prospective
materials discovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_materials_discovery_parc_flagship import add_blocks, gamma_star_from_p, emax_from_p, scs_release_count  # noqa: E402


DEFAULT_SEEDS = list(range(20))
DEFAULT_K = [100, 300, 500, 1000, 5000]
DEFAULT_ALPHA = [0.10, 0.20]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_list(value: str, cast):
    return [cast(item) for item in str(value).split(",") if str(item).strip()]


def split_blocks(block_ids: list[str | int], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def num(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.1f}"


def load_materials_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, list[dict], dict]:
    summary_cols = [
        "material_id",
        "formula",
        "e_form_per_atom_mp2020_corrected",
        "e_above_hull_mp2020_corrected_ppd_mp",
        "wyckoff_spglib",
        "unique_prototype",
    ]
    summary = pd.read_csv(args.wbm_summary, usecols=summary_cols)
    frame = summary.copy()
    specs = [
        {
            "proposal_source": "alignn_ff_modern_learned_materials_model",
            "path": Path(args.alignn_predictions),
            "column": args.alignn_pred_col,
            "model_family": "ALIGNN-FF",
        },
        {
            "proposal_source": "cgcnn_ensemble_learned_materials_model",
            "path": Path(args.cgcnn_predictions),
            "column": args.cgcnn_pred_col,
            "model_family": "CGCNN 10-member ensemble",
        },
        {
            "proposal_source": "megnet_weak_learned_materials_model",
            "path": Path(args.megnet_predictions),
            "column": args.megnet_pred_col,
            "model_family": "MEGNet",
        },
    ]
    input_hashes = {"wbm_summary_sha256": sha256_file(Path(args.wbm_summary))}
    completed_specs: list[dict] = []
    for spec in specs:
        if not spec["path"].exists():
            continue
        pred = pd.read_csv(spec["path"], usecols=["material_id", spec["column"]])
        frame = frame.merge(pred, on="material_id", how="inner")
        input_hashes[f"{spec['proposal_source']}_sha256"] = sha256_file(spec["path"])
        completed_specs.append(spec)
    frame = frame[frame["unique_prototype"].astype(bool)].copy()
    frame = add_blocks(frame)
    frame["stable_DFT"] = frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= 0.0
    hull_reference = (
        frame["e_form_per_atom_mp2020_corrected"].astype(float)
        - frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    )
    for spec in completed_specs:
        score_col = f"{spec['proposal_source']}_score"
        frame[score_col] = -(frame[spec["column"]].astype(float) - hull_reference)
        spec["score_col"] = score_col
    return frame.reset_index(drop=True), completed_specs, input_hashes


def observed_positive_mask_in_calibration(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    cal_blocks: set[str],
    rho: float,
) -> np.ndarray:
    observed = np.zeros(len(frame), dtype=bool)
    block_series = frame[block_col].astype(str)
    eligible = np.flatnonzero(block_series.isin(cal_blocks).to_numpy() & frame["stable_DFT"].to_numpy(dtype=bool))
    if len(eligible) == 0 or rho <= 0:
        return observed
    n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
    scores = frame[score_col].to_numpy(dtype=float)
    chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
    observed[chosen] = True
    return observed


def compute_evalues(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    observed_positive: np.ndarray,
    cal_blocks: set[str],
    followup_blocks: set[str],
    alpha: float,
) -> tuple[pd.DataFrame, dict]:
    block_series = frame[block_col].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    followup_mask = block_series.isin(followup_blocks).to_numpy()
    cal_null = frame.loc[cal_mask & ~observed_positive, [block_col, score_col]].copy()
    maxima = (
        cal_null.groupby(block_col, sort=False)[score_col].max().astype(float).to_numpy()
        if len(cal_null)
        else np.asarray([], dtype=float)
    )
    n_nonempty = int(len(maxima))
    n_total = int(len(cal_blocks))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required = 1.0 / alpha if alpha > 0 else math.nan
    followup = frame.loc[followup_mask].sort_values(score_col, ascending=False).copy()
    if gamma is None or len(followup) == 0 or len(maxima) == 0:
        followup["_evalue"] = np.zeros(len(followup), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = followup[score_col].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        followup["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return followup, {
        "calibration_blocks": n_total,
        "followup_blocks": int(len(followup_blocks)),
        "nonempty_calibration_null_blocks": n_nonempty,
        "block_coverage": n_nonempty / n_total if n_total else 0.0,
        "observed_positives": int(observed_positive.sum()),
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_e": required,
    }


def evaluate_queue(pool: pd.DataFrame, selected: pd.DataFrame, released: int) -> dict:
    selected_ids = set(selected["material_id"].astype(str))
    raw_tail = pool[~pool["material_id"].astype(str).isin(selected_ids)].copy()
    raw_prefix = pool.head(released).copy() if released else pool.iloc[[]].copy()
    raw_unstable = int((~pool["stable_DFT"].astype(bool)).sum()) if len(pool) else 0
    parc_unstable = int((~selected["stable_DFT"].astype(bool)).sum()) if released else 0
    raw_tail_unstable = int((~raw_tail["stable_DFT"].astype(bool)).sum()) if len(raw_tail) else 0
    raw_prefix_unstable = int((~raw_prefix["stable_DFT"].astype(bool)).sum()) if released else 0
    return {
        "raw_topK_size": int(len(pool)),
        "PARC_release_size": int(released),
        "raw_only_tail_size": int(len(raw_tail)),
        "raw_topR_matched_size": int(len(raw_prefix)),
        "raw_topK_unstable": raw_unstable,
        "PARC_unstable": parc_unstable,
        "raw_only_tail_unstable": raw_tail_unstable,
        "raw_topR_matched_unstable": raw_prefix_unstable,
        "raw_topK_FTR": float((~pool["stable_DFT"].astype(bool)).mean()) if len(pool) else 0.0,
        "PARC_FTR": float((~selected["stable_DFT"].astype(bool)).mean()) if released else 0.0,
        "raw_only_tail_FTR": float((~raw_tail["stable_DFT"].astype(bool)).mean()) if len(raw_tail) else 0.0,
        "raw_topR_matched_FTR": float((~raw_prefix["stable_DFT"].astype(bool)).mean()) if released else 0.0,
        "raw_DFT_efficiency_per100": 100.0 * float(pool["stable_DFT"].astype(bool).mean()) if len(pool) else 0.0,
        "PARC_DFT_efficiency_per100": 100.0 * float(selected["stable_DFT"].astype(bool).mean()) if released else 0.0,
        "raw_tail_DFT_efficiency_per100": 100.0 * float(raw_tail["stable_DFT"].astype(bool).mean()) if len(raw_tail) else 0.0,
        "unstable_followups_prevented": raw_unstable - parc_unstable,
        "stable_hits_released": int(selected["stable_DFT"].astype(bool).sum()) if released else 0,
    }


def run_trial(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    frame, specs, input_hashes = load_materials_frame(args)
    seeds = parse_list(args.seeds, int)
    budgets = parse_list(args.budgets, int)
    alphas = parse_list(args.alphas, float)
    rho = float(args.rho)
    block_col = "composition_family_pair"
    rows: list[dict] = []
    release_cards: list[dict] = []
    for seed in seeds:
        cal_blocks, followup_blocks = split_blocks(frame[block_col].astype(str).tolist(), seed)
        for spec in specs:
            score_col = spec["score_col"]
            observed = observed_positive_mask_in_calibration(
                frame, score_col=score_col, block_col=block_col, cal_blocks=cal_blocks, rho=rho
            )
            for alpha in alphas:
                followup, diag = compute_evalues(
                    frame,
                    score_col=score_col,
                    block_col=block_col,
                    observed_positive=observed,
                    cal_blocks=cal_blocks,
                    followup_blocks=followup_blocks,
                    alpha=alpha,
                )
                max_observed_e = float(followup["_evalue"].max()) if len(followup) else 0.0
                for budget in budgets:
                    pool = followup.head(budget).copy()
                    evalues = pool["_evalue"].to_numpy(dtype=float)
                    released, tau, margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
                    selected = (
                        pool.iloc[np.argsort(evalues)[::-1][:released]].copy()
                        if released
                        else pool.iloc[[]].copy()
                    )
                    metrics = evaluate_queue(pool, selected, released)
                    decision = (
                        "certified_release"
                        if released and metrics["PARC_FTR"] <= alpha
                        else ("certified_refusal" if released == 0 else "boundary_release")
                    )
                    row = {
                        "domain": "materials_discovery",
                        "dataset": "Matbench Discovery WBM unique prototypes",
                        "unit": "stable_inorganic_crystal_candidate",
                        "proposal_source": spec["proposal_source"],
                        "model_family": spec["model_family"],
                        "trial_type": "quasi_prospective_public_DFT_label_followup",
                        "label_reveal_timing": "followup_partition_DFT_labels_used_only_after_PAR C_decision".replace("PAR C", "PARC"),
                        "verification_mode": "pre_release_top_score_DFT_stable_positives_in_calibration_blocks",
                        "block_definition": block_col,
                        "rho": rho,
                        "alpha": alpha,
                        "K": budget,
                        "seed": seed,
                        "decision": decision,
                        "max_observed_e": max_observed_e,
                        "required_e": diag["required_e"],
                        "best_mass_ratio": best_ratio,
                        "self_consistency_margin": margin,
                        "release_threshold_tau": tau,
                        **diag,
                        **metrics,
                        "evidence_status": "completed_quasi_prospective_public_DFT_label_trial",
                    }
                    rows.append(row)
                    if seed == int(args.primary_seed):
                        release_cards.append(row)
    seed_rows = pd.DataFrame(rows)
    card_rows = pd.DataFrame(release_cards)
    summary_rows: list[dict] = []
    group_cols = [
        "domain",
        "dataset",
        "unit",
        "proposal_source",
        "model_family",
        "trial_type",
        "verification_mode",
        "block_definition",
        "rho",
        "alpha",
        "K",
    ]
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        out = dict(zip(group_cols, key))
        out.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["PARC_release_size"].astype(int) > 0).sum()),
                "mean_release": float(group["PARC_release_size"].astype(float).mean()),
                "min_release": int(group["PARC_release_size"].astype(int).min()),
                "max_release": int(group["PARC_release_size"].astype(int).max()),
                "PARC_FTR_mean": float(group["PARC_FTR"].astype(float).mean()),
                "PARC_FTR_max": float(group["PARC_FTR"].astype(float).max()),
                "raw_topK_FTR_mean": float(group["raw_topK_FTR"].astype(float).mean()),
                "raw_only_tail_FTR_mean": float(group["raw_only_tail_FTR"].astype(float).mean()),
                "raw_topR_matched_FTR_mean": float(group["raw_topR_matched_FTR"].astype(float).mean()),
                "raw_topK_unstable_mean": float(group["raw_topK_unstable"].astype(float).mean()),
                "PARC_unstable_mean": float(group["PARC_unstable"].astype(float).mean()),
                "raw_only_tail_unstable_mean": float(group["raw_only_tail_unstable"].astype(float).mean()),
                "unstable_followups_prevented_mean": float(
                    group["unstable_followups_prevented"].astype(float).mean()
                ),
                "PARC_DFT_efficiency_per100_mean": float(
                    group["PARC_DFT_efficiency_per100"].astype(float).mean()
                ),
                "raw_DFT_efficiency_per100_mean": float(
                    group["raw_DFT_efficiency_per100"].astype(float).mean()
                ),
                "raw_tail_DFT_efficiency_per100_mean": float(
                    group["raw_tail_DFT_efficiency_per100"].astype(float).mean()
                ),
                "observed_positives_mean": float(group["observed_positives"].astype(float).mean()),
                "calibration_blocks_mean": float(group["calibration_blocks"].astype(float).mean()),
                "followup_blocks_mean": float(group["followup_blocks"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_e"].astype(float).mean()),
                "evidence_status": "completed_quasi_prospective_public_DFT_label_trial",
            }
        )
        if out["non_empty_seeds"] >= 18 and out["PARC_FTR_mean"] <= out["alpha"]:
            out["trial_status"] = "GO_certified_computational_followup_queue"
        elif out["mean_release"] == 0:
            out["trial_status"] = "certified_refusal_or_low_power"
        else:
            out["trial_status"] = "boundary_or_partial_release"
        out["interpretation"] = (
            "certified_stopping_decision_not_reranking"
            if out["mean_release"] > 0
            else "unsupported_followup_budget_refused"
        )
        summary_rows.append(out)
    summary = pd.DataFrame(summary_rows)
    protocol = {
        "trial_name": "PARC-guided computational follow-up for materials candidates",
        "trial_type": "quasi_prospective_public_DFT_label_followup",
        "scope": (
            "Retrospective public-label replay with frozen model/K/alpha/split/release rules; "
            "not new DFT, not experimental synthesis, not true prospective discovery."
        ),
        "candidate_queue": "raw top-K WBM unique prototypes ranked by frozen public model predictions",
        "validation": "held-out follow-up partition public DFT stability labels revealed after PARC decision",
        "block_definition": block_col,
        "rho": rho,
        "alphas": alphas,
        "budgets": budgets,
        "seeds": seeds,
        "primary_seed_for_release_cards": int(args.primary_seed),
        "input_hashes": input_hashes,
    }
    return seed_rows, summary, card_rows, protocol


def plot_trial(summary: pd.DataFrame, out_csv: Path, out_pdf: Path) -> None:
    alpha010 = summary[np.isclose(summary["alpha"].astype(float), 0.10)].copy()
    alpha010.to_csv(out_csv, index=False)
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.2))

    alignn = alpha010[alpha010["model_family"] == "ALIGNN-FF"].copy()
    bars = alignn[alignn["K"].isin([500, 5000])].sort_values("K")
    ax = axes[0, 0]
    x = np.arange(len(bars))
    width = 0.26
    ax.bar(x - width, bars["raw_topK_unstable_mean"], width=width, label="Raw unstable", color="#d95f02")
    ax.bar(x, bars["PARC_unstable_mean"], width=width, label="PARC unstable", color="#1b9e77")
    ax.bar(x + width, bars["unstable_followups_prevented_mean"], width=width, label="Prevented", color="#7570b3")
    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}" for k in bars["K"]])
    ax.set_ylabel("Candidates per split")
    ax.set_title("a  Follow-up queue composition")
    ax.legend(fontsize=6, frameon=False)

    ax = axes[0, 1]
    rate_rows = alignn[(alignn["mean_release"] > 0) & (alignn["K"].isin([300, 500, 1000]))].sort_values("K")
    x = np.arange(len(rate_rows))
    ax.plot(x, 100.0 - 100.0 * rate_rows["PARC_FTR_mean"], marker="o", label="PARC-release stable rate")
    ax.plot(
        x,
        100.0 - 100.0 * rate_rows["raw_only_tail_FTR_mean"],
        marker="s",
        label="Raw-only rejected tail stable rate",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}" for k in rate_rows["K"]])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Stable candidates per 100 follow-ups")
    ax.set_title("b  Released queue vs rejected tail")
    ax.legend(fontsize=6, frameon=False)

    ax = axes[1, 0]
    models = sorted(alpha010["model_family"].unique().tolist())
    budgets = sorted(alpha010["K"].astype(int).unique().tolist())
    mat = np.zeros((len(models), len(budgets)))
    for i, model in enumerate(models):
        for j, budget in enumerate(budgets):
            row = alpha010[(alpha010["model_family"] == model) & (alpha010["K"] == budget)]
            if len(row):
                status = str(row["trial_status"].iloc[0])
                mat[i, j] = 2 if status.startswith("GO_") else (1 if "boundary" in status else 0)
    cmap = matplotlib.colors.ListedColormap(["#d9d9d9", "#fee08b", "#1b9e77"])
    ax.imshow(mat, cmap=cmap, vmin=0, vmax=2, aspect="auto")
    for i, model in enumerate(models):
        for j, budget in enumerate(budgets):
            row = alpha010[(alpha010["model_family"] == model) & (alpha010["K"] == budget)]
            if len(row):
                ax.text(
                    j,
                    i,
                    f"{int(row['non_empty_seeds'].iloc[0])}/20\nFTR {row['PARC_FTR_mean'].iloc[0]:.3f}",
                    ha="center",
                    va="center",
                    fontsize=5.8,
                )
    ax.set_xticks(np.arange(len(budgets)))
    ax.set_xticklabels([str(k) for k in budgets])
    ax.set_yticks(np.arange(len(models)))
    ax.set_yticklabels(models)
    ax.set_xlabel("K")
    ax.set_title("c  Release/refusal frontier")

    ax = axes[1, 1]
    eff = alignn[alignn["K"].isin([300, 500, 1000])].sort_values("K")
    ax.plot(eff["K"], eff["PARC_DFT_efficiency_per100_mean"], marker="o", label="PARC-release")
    ax.plot(eff["K"], eff["raw_DFT_efficiency_per100_mean"], marker="s", label="Raw top-K")
    ax.set_xscale("log")
    ax.set_ylim(0, 105)
    ax.set_xlabel("K")
    ax.set_ylabel("Stable candidates per 100 computations")
    ax.set_title("d  Computational follow-up efficiency")
    ax.legend(fontsize=6, frameon=False)

    fig.suptitle("PARC-guided computational follow-up trial for materials candidates", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(out_pdf)
    plt.close(fig)


def write_release_cards(summary: pd.DataFrame, out_path: Path) -> None:
    alpha010 = summary[np.isclose(summary["alpha"].astype(float), 0.10)].copy()
    cards = []
    for _, row in alpha010.iterrows():
        cards.append(
            {
                "domain": "materials_discovery",
                "workflow": "computational_DFT_followup_queue",
                "candidate_universe": row["dataset"],
                "proposal_source": row["proposal_source"],
                "verification_source": "pre-release observed public DFT-stable positives in calibration blocks",
                "followup_validation_source": "held-out follow-up partition public DFT stability labels",
                "risk_level_alpha": row["alpha"],
                "requested_K": row["K"],
                "PARC_decision": row["trial_status"],
                "released_candidates_mean": row["mean_release"],
                "realized_FTR_mean": row["PARC_FTR_mean"],
                "raw_topK_FTR_mean": row["raw_topK_FTR_mean"],
                "unstable_followups_prevented_mean": row["unstable_followups_prevented_mean"],
                "DFT_efficiency_per100_mean": row["PARC_DFT_efficiency_per100_mean"],
                "scope_limitations": (
                    "quasi-prospective replay using public DFT labels; not new DFT; not experimental synthesis"
                ),
            }
        )
    pd.DataFrame(cards).to_csv(out_path, index=False)


def write_closeout(out_dir: Path, summary: pd.DataFrame, protocol: dict) -> None:
    alignn500 = summary[
        (summary["model_family"] == "ALIGNN-FF")
        & np.isclose(summary["alpha"].astype(float), 0.10)
        & (summary["K"].astype(int) == 500)
    ].iloc[0]
    alignn5000 = summary[
        (summary["model_family"] == "ALIGNN-FF")
        & np.isclose(summary["alpha"].astype(float), 0.10)
        & (summary["K"].astype(int) == 5000)
    ].iloc[0]
    text = f"""# Materials Computational Follow-Up Trial Closeout

This milestone implements a quasi-prospective computational decision trial for materials candidates. PARC decides which candidates from a frozen model-ranked queue enter a computational follow-up queue under one-sided partial verification. Held-out public DFT labels in the follow-up partition are used only after the release/refusal decision to evaluate queue quality.

## Status

- Evidence status: `completed_quasi_prospective_public_DFT_label_trial`.
- No new human labels.
- No new DFT calculations.
- Not experimental synthesis and not true prospective discovery.
- Follow-up labels are public DFT labels revealed after the frozen release/refusal replay.

## Primary Headline

At `alpha=0.10, K=500`, ALIGNN-FF raw top-K admits {num(alignn500['raw_topK_unstable_mean'])} unstable candidates per split ({pct(alignn500['raw_topK_FTR_mean'])} raw FTR). PARC releases {num(alignn500['mean_release'])} candidates with {num(alignn500['PARC_unstable_mean'])} unstable candidates ({pct(alignn500['PARC_FTR_mean'])} FTR), preventing {num(alignn500['unstable_followups_prevented_mean'])} unstable computational follow-ups per split.

At `alpha=0.10, K=5000`, ALIGNN-FF raw top-K admits {num(alignn5000['raw_topK_unstable_mean'])} unstable candidates per split ({pct(alignn5000['raw_topK_FTR_mean'])} raw FTR). PARC refuses the unsupported high-volume request, preventing {num(alignn5000['unstable_followups_prevented_mean'])} unstable computational follow-ups under the release/refusal interpretation.

## Interpretation

The trial supports a release-governance claim rather than a ranking-improvement claim: PARC identifies where to stop releasing candidates from a frozen scientific queue. The raw top-R matched prefix is reported separately to distinguish certified stopping from reranking.

## Protocol

`MATERIALS_COMPUTATIONAL_TRIAL_PROTOCOL.json` records the frozen model sources, budgets, alpha levels, block definition, partial-verification rule, and input hashes.

## Main Artifacts

- `table_materials_computational_trial_summary.csv`
- `table_materials_computational_trial_seed_results.csv`
- `table_materials_computational_trial_release_cards.csv`
- `figure_materials_computational_trial_main.csv`
- `figure_materials_computational_trial_main.pdf`
"""
    (out_dir / "MATERIALS_COMPUTATIONAL_TRIAL_CLOSEOUT.md").write_text(text, encoding="utf-8")
    (out_dir / "MATERIALS_COMPUTATIONAL_TRIAL_PROTOCOL.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True), encoding="utf-8"
    )


def write_provenance(path: Path, artifact: Path, report: dict, role: str) -> None:
    payload = {
        "status": "completed",
        "evidence_status": "completed_quasi_prospective_public_DFT_label_trial",
        "role": role,
        "artifact": artifact.name,
        "command": "python scripts/build_materials_computational_trial.py",
        "scope": "quasi-prospective public-DFT computational follow-up replay; no new labels/DFT",
        "input_hashes": report["input_hashes"],
        "output_sha256": sha256_file(artifact),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/materials_computational_followup_trial")
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--megnet-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    parser.add_argument("--megnet-pred-col", default="e_form_per_atom_megnet")
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--budgets", default=",".join(str(k) for k in DEFAULT_K))
    parser.add_argument("--alphas", default=",".join(str(alpha) for alpha in DEFAULT_ALPHA))
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--primary-seed", type=int, default=0)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_rows, summary, release_cards, protocol = run_trial(args)
    seed_rows.to_csv(out_dir / "table_materials_computational_trial_seed_results.csv", index=False)
    summary.to_csv(out_dir / "table_materials_computational_trial_summary.csv", index=False)
    release_cards.to_csv(out_dir / "table_materials_computational_trial_primary_seed_release_cards.csv", index=False)
    write_release_cards(summary, out_dir / "table_materials_computational_trial_release_cards.csv")
    plot_trial(
        summary,
        out_dir / "figure_materials_computational_trial_main.csv",
        out_dir / "figure_materials_computational_trial_main.pdf",
    )
    write_closeout(out_dir, summary, protocol)
    report = {
        "status": "completed",
        "evidence_status": "completed_quasi_prospective_public_DFT_label_trial",
        "runtime_sec": time.perf_counter() - started,
        "input_hashes": protocol["input_hashes"],
        "summary_rows": int(len(summary)),
        "seed_rows": int(len(seed_rows)),
        "scope": protocol["scope"],
    }
    (out_dir / "materials_computational_trial_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    for name, role in [
        ("table_materials_computational_trial_seed_results.csv", "seed_results"),
        ("table_materials_computational_trial_summary.csv", "summary"),
        ("table_materials_computational_trial_primary_seed_release_cards.csv", "primary_seed_release_cards"),
        ("table_materials_computational_trial_release_cards.csv", "release_cards"),
        ("figure_materials_computational_trial_main.csv", "figure_source"),
        ("figure_materials_computational_trial_main.pdf", "figure_pdf"),
        ("MATERIALS_COMPUTATIONAL_TRIAL_CLOSEOUT.md", "closeout"),
        ("MATERIALS_COMPUTATIONAL_TRIAL_PROTOCOL.json", "protocol"),
        ("materials_computational_trial_summary.json", "summary_json"),
    ]:
        artifact = out_dir / name
        write_provenance(artifact.with_suffix(artifact.suffix + ".provenance.json"), artifact, report, role)
    write_manifest(out_dir)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
