#!/usr/bin/env python3
"""Run simulated active-audit budget frontiers for PARC release decisions.

The audit simulation uses existing full labels only as an oracle for what an
audit would return and for post-release evaluation. Negative audit results are
not added to the PARC null as verified negatives; an inspected candidate either
becomes a one-sided verified positive or remains unverified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_materials_threshold_robustness as materials_threshold  # noqa: E402
from run_verified_positive_removal_load_bearing_ablation import (  # noqa: E402
    bool_series,
    compute_evalues_from_null,
    empty_reason,
    scs_release_count,
    split_ids,
)


DEFAULT_BUDGET_FRACTIONS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
DEFAULT_POLICIES = ["random", "top_score", "block_balanced_top_score", "diversity_round_robin"]
DEFAULT_SEEDS = list(range(20))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_float_list(value: str) -> list[float]:
    return [float(item) for item in str(value).split(",") if item.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(item) for item in str(value).split(",") if item.strip()]


def parse_str_list(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def select_audit_mask(
    cal: pd.DataFrame,
    *,
    policy: str,
    n_inspect: int,
    score_col: str,
    block_col: str,
    seed: int,
) -> np.ndarray:
    selected = np.zeros(len(cal), dtype=bool)
    if n_inspect <= 0 or len(cal) == 0:
        return selected
    n_inspect = min(n_inspect, len(cal))
    if policy == "random":
        rng = np.random.default_rng(seed + 1009)
        chosen = rng.choice(np.arange(len(cal)), size=n_inspect, replace=False)
        selected[chosen] = True
        return selected
    if policy == "top_score":
        chosen = np.argsort(cal[score_col].to_numpy(dtype=float))[::-1][:n_inspect]
        selected[chosen] = True
        return selected
    if policy == "block_balanced_top_score":
        ranked = cal.reset_index(drop=True).copy()
        ranked["_local_idx"] = np.arange(len(ranked))
        ranked = ranked.sort_values([block_col, score_col], ascending=[True, False])
        groups = []
        for _block, group in ranked.groupby(block_col, sort=True):
            groups.append(group["_local_idx"].tolist())
        picked: list[int] = []
        while len(picked) < n_inspect and any(groups):
            next_groups = []
            for group in groups:
                if group and len(picked) < n_inspect:
                    picked.append(group.pop(0))
                if group:
                    next_groups.append(group)
            groups = next_groups
        selected[picked[:n_inspect]] = True
        return selected
    if policy == "diversity_round_robin":
        ranked = cal.reset_index(drop=True).copy()
        ranked["_local_idx"] = np.arange(len(ranked))
        ranked["_diversity_key"] = ranked[block_col].astype(str).str.split("|").str[0]
        ranked = ranked.sort_values(["_diversity_key", score_col], ascending=[True, False])
        groups = []
        for _key, group in ranked.groupby("_diversity_key", sort=True):
            groups.append(group["_local_idx"].tolist())
        picked: list[int] = []
        while len(picked) < n_inspect and any(groups):
            next_groups = []
            for group in groups:
                if group and len(picked) < n_inspect:
                    picked.append(group.pop(0))
                if group:
                    next_groups.append(group)
            groups = next_groups
        selected[picked[:n_inspect]] = True
        return selected
    raise ValueError(f"Unknown audit policy: {policy}")


def run_target_row(
    *,
    frame: pd.DataFrame,
    target_row_prefix: str,
    domain: str,
    dataset: str,
    proposal_source: str,
    unit: str,
    block_col: str,
    score_col: str,
    label_col: str,
    alpha: float,
    budgets: list[int],
    seeds: list[int],
    budget_fractions: list[float],
    policies: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []
    work = frame.reset_index(drop=True).copy()
    block_values = work[block_col].astype(str)
    for seed in seeds:
        cal_blocks, test_blocks = split_ids(block_values.tolist(), seed)
        cal_mask = block_values.isin(cal_blocks).to_numpy()
        test_mask = block_values.isin(test_blocks).to_numpy()
        cal = work.loc[cal_mask].reset_index(drop=True).copy()
        test = work.loc[test_mask].sort_values(score_col, ascending=False).reset_index(drop=True).copy()
        for policy in policies:
            for budget_fraction in budget_fractions:
                n_inspect = int(round(len(cal) * budget_fraction))
                audit_mask = select_audit_mask(
                    cal,
                    policy=policy,
                    n_inspect=n_inspect,
                    score_col=score_col,
                    block_col=block_col,
                    seed=seed,
                )
                cal_observed_positive = audit_mask & cal[label_col].to_numpy(dtype=bool)
                cal_null_mask = ~cal_observed_positive
                evalues, diag = compute_evalues_from_null(
                    test,
                    cal,
                    block_col=block_col,
                    score_col=score_col,
                    cal_block_ids=list(cal_blocks),
                    cal_null_mask=cal_null_mask,
                    alpha=alpha,
                )
                max_observed_e = float(np.max(evalues)) if len(evalues) else 0.0
                for budget in budgets:
                    pool = test.head(budget).copy()
                    pool_e = evalues[: len(pool)]
                    released, tau, margin, best_ratio = scs_release_count(pool_e, alpha=alpha, budget=budget)
                    order = np.argsort(pool_e)[::-1]
                    selected = pool.iloc[order[:released]].copy() if released else pool.iloc[[]].copy()
                    actual_ftr = float((~selected[label_col].astype(bool)).mean()) if released else 0.0
                    raw_ftr = float((~pool[label_col].astype(bool)).mean()) if len(pool) else 0.0
                    rows.append(
                        {
                            "domain": domain,
                            "dataset": dataset,
                            "unit": unit,
                            "target_row": f"{target_row_prefix}_K{budget}",
                            "proposal_source": proposal_source,
                            "block_definition": block_col,
                            "alpha": alpha,
                            "K": budget,
                            "seed": seed,
                            "audit_policy": policy,
                            "audit_budget_fraction": budget_fraction,
                            "calibration_candidates": len(cal),
                            "audit_candidates_inspected": int(audit_mask.sum()),
                            "verified_positives_found": int(cal_observed_positive.sum()),
                            "verified_positive_yield": float(cal_observed_positive.sum() / audit_mask.sum()) if audit_mask.sum() else 0.0,
                            "released": int(released),
                            "actual_FTR": actual_ftr,
                            "alpha_violation": bool(released > 0 and actual_ftr > alpha),
                            "raw_topK_actual_FTR": raw_ftr,
                            "max_observed_e": max_observed_e,
                            "selected_e_min": float(pool_e[order[:released]].min()) if released else 0.0,
                            "selected_e_mean": float(pool_e[order[:released]].mean()) if released else 0.0,
                            "selected_e_max": float(pool_e.max()) if released else 0.0,
                            "required_e": float(diag["required_e"]) if diag["required_e"] is not None else math.nan,
                            "emax_effective": diag["emax_effective"],
                            "best_mass_ratio": best_ratio,
                            "self_consistency_margin": margin,
                            "tau_k": tau if released else "",
                            "n_cal_blocks": diag["n_cal_blocks"],
                            "n_nonempty_null_cal_blocks": diag["n_nonempty_null_cal_blocks"],
                            "block_coverage": diag["block_coverage"],
                            "empty_reason": empty_reason(released, diag, max_observed_e),
                            "safe_release": bool(released > 0 and actual_ftr <= alpha),
                            "evidence_status": "completed_simulated_audit_frontier",
                        }
                    )
    return pd.DataFrame(rows)


def summarize(seed_rows: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "domain",
        "dataset",
        "unit",
        "target_row",
        "proposal_source",
        "block_definition",
        "alpha",
        "K",
        "audit_policy",
        "audit_budget_fraction",
    ]
    rows = []
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        released = group["released"].astype(float)
        true_release = group["released"].astype(float) * (1.0 - group["actual_FTR"].astype(float))
        inspected = group["audit_candidates_inspected"].astype(float)
        mean_true_release = float(true_release.mean())
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["released"].astype(int) > 0).sum()),
                "release_rate": float((group["released"].astype(int) > 0).mean()),
                "safe_release_rate": float(group["safe_release"].astype(bool).mean()),
                "mean_release": float(released.mean()),
                "min_release": int(group["released"].astype(int).min()),
                "max_release": int(group["released"].astype(int).max()),
                "actual_FTR_mean": float(group["actual_FTR"].astype(float).mean()),
                "actual_FTR_max": float(group["actual_FTR"].astype(float).max()),
                "alpha_violation_rate": float(group["alpha_violation"].astype(bool).mean()),
                "refusal_rate": float((group["released"].astype(int) == 0).mean()),
                "raw_topK_actual_FTR_mean": float(group["raw_topK_actual_FTR"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_e"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
                "audit_candidates_inspected_mean": float(inspected.mean()),
                "verified_positives_found_mean": float(group["verified_positives_found"].astype(float).mean()),
                "verified_positive_yield_mean": float(group["verified_positive_yield"].astype(float).mean()),
                "cost_per_release_mean": float(inspected.mean() / released.mean()) if released.mean() > 0 else math.inf,
                "cost_per_true_release_mean": float(inspected.mean() / mean_true_release) if mean_true_release > 0 else math.inf,
                "dominant_empty_reason": (
                    group["empty_reason"].dropna().mode().iloc[0]
                    if not group["empty_reason"].dropna().empty
                    else ""
                ),
                "evidence_status": "completed_simulated_audit_frontier",
                "paper_role": "methodological_frontier_candidate_not_prospective_discovery",
            }
        )
        rows.append(row)
    summary = pd.DataFrame(rows)
    first_rows = []
    for key, group in summary.groupby(["target_row", "audit_policy"], dropna=False):
        target_row, audit_policy = key
        ordered = group.sort_values("audit_budget_fraction")
        safe = ordered[
            (ordered["safe_release_rate"].astype(float) > 0.0)
            & (ordered["actual_FTR_mean"].astype(float) <= ordered["alpha"].astype(float))
        ]
        first_budget = float(safe.iloc[0]["audit_budget_fraction"]) if not safe.empty else math.nan
        first_rows.append(
            {"target_row": target_row, "audit_policy": audit_policy, "first_safe_release_budget_fraction": first_budget}
        )
    return summary.merge(pd.DataFrame(first_rows), on=["target_row", "audit_policy"], how="left")


def ctc_rows(args: argparse.Namespace, budget_fractions: list[float], policies: list[str], seeds: list[int]) -> pd.DataFrame:
    frame = pd.read_csv(args.ctc_universe, low_memory=False)
    frame["_full_true"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
    return run_target_row(
        frame=frame,
        target_row_prefix="ctc_learned_strict_alpha010",
        domain="biomedical_cell_tracking",
        dataset="Cell Tracking Challenge learned-hybrid held-out sequence",
        proposal_source="ctc_learned_hybrid_appearance_sequence_disjoint",
        unit="cell_link",
        block_col="video_id",
        score_col="score",
        label_col="_full_true",
        alpha=0.10,
        budgets=[100, 300],
        seeds=seeds,
        budget_fractions=budget_fractions,
        policies=policies,
    )


def materials_rows(args: argparse.Namespace, budget_fractions: list[float], policies: list[str], seeds: list[int]) -> pd.DataFrame:
    frame, _meta = materials_threshold.load_frame(args)
    specs = [
        {
            "target_row_prefix": "materials_cgcnn_exact_stable_alpha010",
            "source": "cgcnn_ensemble_learned_materials_model",
            "score_col": "cgcnn_score",
            "budgets": [100],
        },
        {
            "target_row_prefix": "materials_alignn_exact_stable_alpha010",
            "source": "alignn_ff_modern_learned_materials_model",
            "score_col": "alignn_score",
            "budgets": [300, 500],
        },
    ]
    rows = []
    for spec in specs:
        rows.append(
            run_target_row(
                frame=frame,
                target_row_prefix=spec["target_row_prefix"],
                domain="materials_discovery",
                dataset="Matbench Discovery WBM unique prototypes",
                proposal_source=spec["source"],
                unit="stable_inorganic_crystal_candidate",
                block_col="composition_family_pair",
                score_col=spec["score_col"],
                label_col="stable_exact",
                alpha=0.10,
                budgets=spec["budgets"],
                seeds=seeds,
                budget_fractions=budget_fractions,
                policies=policies,
            )
        )
    return pd.concat(rows, ignore_index=True)


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_protocol_files(out_dir: Path, budget_fractions: list[float], policies: list[str], seeds: list[int]) -> None:
    (out_dir / "AUDIT_BUDGET_FRONTIER_PREREGISTRATION.md").write_text(
        "# Audit Budget Release Frontier Preregistration\n\n"
        "Status: frozen before inspecting the simulated-audit results table for manuscript claims.\n\n"
        "This milestone tests how much one-sided verification is needed to move a frozen candidate "
        "universe from refusal to certified release. The experiment is a simulated audit over existing "
        "held-out labels; it introduces no new human labels, no new DFT, and no prospective materials "
        "discovery claim.\n\n"
        "## Frozen Grid\n\n"
        f"- Audit policies: {', '.join(policies)}\n"
        f"- Audit budget fractions of calibration candidates inspected: {', '.join(map(str, budget_fractions))}\n"
        f"- Seeds: {', '.join(map(str, seeds))}\n"
        "- Primary alpha: 0.10\n"
        "- Candidate rows: CTC learned K=100/300; materials CGCNN K=100; materials ALIGNN-FF K=300/500.\n\n"
        "Hidden full labels are used only to simulate whether an inspected item becomes a verified "
        "positive and to evaluate post-release FTR. Unverified items are never treated as negative labels.\n",
        encoding="utf-8",
    )
    (out_dir / "audit_policy.yaml").write_text(
        "policies:\n"
        "  random: uniform random calibration candidates\n"
        "  top_score: highest-score calibration candidates first\n"
        "  block_balanced_top_score: one high-score candidate per block in round-robin order\n"
        "  diversity_round_robin: round-robin over coarse diversity keys before repeating\n"
        "hidden_label_use: simulated_audit_return_and_posthoc_evaluation_only\n"
        "claim_boundary: not_prospective_materials_discovery\n",
        encoding="utf-8",
    )
    pd.DataFrame({"audit_budget_fraction": budget_fractions}).to_csv(out_dir / "budget_grid.csv", index=False)
    tasks = []
    for target_row, domain, budget in [
        ("ctc_learned_strict_alpha010_K100", "biomedical_cell_tracking", 100),
        ("ctc_learned_strict_alpha010_K300", "biomedical_cell_tracking", 300),
        ("materials_cgcnn_exact_stable_alpha010_K100", "materials_discovery", 100),
        ("materials_alignn_exact_stable_alpha010_K300", "materials_discovery", 300),
        ("materials_alignn_exact_stable_alpha010_K500", "materials_discovery", 500),
    ]:
        tasks.append({"target_row": target_row, "domain": domain, "alpha": 0.10, "K": budget, "seeds": len(seeds)})
    pd.DataFrame(tasks).to_csv(out_dir / "domain_task_manifest.csv", index=False)


def write_closeout(out_dir: Path, summary: pd.DataFrame, seed_rows: pd.DataFrame, runtime_sec: float) -> None:
    random_first = (
        summary[summary["audit_policy"].eq("random")]
        .groupby("target_row", dropna=False)["first_safe_release_budget_fraction"]
        .min()
        .reset_index()
        .rename(columns={"first_safe_release_budget_fraction": "random_first_safe"})
    )
    best = (
        summary.groupby(["target_row", "audit_policy"], dropna=False)["first_safe_release_budget_fraction"]
        .min()
        .reset_index()
    )
    best = best.dropna(subset=["first_safe_release_budget_fraction"])
    best = best.sort_values(["target_row", "first_safe_release_budget_fraction"]).groupby("target_row").head(1)
    best = best.merge(random_first, on="target_row", how="left")
    transitions = []
    for _, row in best.iterrows():
        random_budget = row["random_first_safe"]
        ratio = (
            float(random_budget / row["first_safe_release_budget_fraction"])
            if pd.notna(random_budget) and row["first_safe_release_budget_fraction"] > 0
            else math.nan
        )
        transitions.append(
            f"- {row['target_row']}: first safe release under `{row['audit_policy']}` at "
            f"{row['first_safe_release_budget_fraction']}; random/best budget ratio {ratio if not math.isnan(ratio) else 'NA'}."
        )
    transition_text = "\n".join(transitions) if transitions else "- No safe-release transition found in the frozen budget grid."
    (out_dir / "AUDIT_BUDGET_FRONTIER_CLOSEOUT.md").write_text(
        "# Audit Budget Release Frontier Closeout\n\n"
        "Status: completed simulated-audit frontier.\n\n"
        f"- Seed rows: {len(seed_rows)}\n"
        f"- Summary rows: {len(summary)}\n"
        f"- Runtime seconds: {runtime_sec:.2f}\n\n"
        "## Claim Boundary\n\n"
        "This is a simulated audit-budget experiment over existing labels. It is not prospective "
        "materials discovery, does not modify A3 selection or DFT manifests, and does not create new "
        "human or DFT labels. The result may support an audit-governance method claim if reported as "
        "a frontier over verification cost and release/refusal behavior. The transition summary below "
        "uses the exploratory summary-table criterion from this raw frontier (`safe_release_rate > 0` "
        "and mean FTR within alpha). Use the phase41 headline package for strict seed-stable "
        "paper-facing transitions.\n\n"
        "## Exploratory Transition Summary\n\n"
        f"{transition_text}\n",
        encoding="utf-8",
    )


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
    parser.add_argument("--budget-fractions", default=",".join(str(item) for item in DEFAULT_BUDGET_FRACTIONS))
    parser.add_argument("--policies", default=",".join(DEFAULT_POLICIES))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--out-dir", default="outputs/milestones/audit_budget_release_frontier")
    args = parser.parse_args()

    started = time.perf_counter()
    budget_fractions = parse_float_list(args.budget_fractions)
    policies = parse_str_list(args.policies)
    seeds = parse_int_list(args.seeds)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_protocol_files(out_dir, budget_fractions, policies, seeds)

    seed_rows = pd.concat(
        [ctc_rows(args, budget_fractions, policies, seeds), materials_rows(args, budget_fractions, policies, seeds)],
        ignore_index=True,
    )
    summary = summarize(seed_rows)
    figure_source = summary[
        [
            "domain",
            "target_row",
            "audit_policy",
            "audit_budget_fraction",
            "release_rate",
            "safe_release_rate",
            "mean_release",
            "actual_FTR_mean",
            "alpha",
            "cost_per_true_release_mean",
            "first_safe_release_budget_fraction",
        ]
    ].copy()
    seed_path = out_dir / "table_audit_budget_frontier_seed_rows.csv"
    summary_path = out_dir / "table_audit_budget_frontier_summary.csv"
    figure_path = out_dir / "figure_audit_budget_frontier_source.csv"
    seed_rows.to_csv(seed_path, index=False)
    summary.to_csv(summary_path, index=False)
    figure_source.to_csv(figure_path, index=False)
    runtime_sec = time.perf_counter() - started
    write_closeout(out_dir, summary, seed_rows, runtime_sec)
    provenance = {
        "status": "completed",
        "evidence_status": "completed_simulated_audit_frontier",
        "runtime_sec": runtime_sec,
        "target_rows": int(summary["target_row"].nunique()),
        "seed_rows": int(len(seed_rows)),
        "summary_rows": int(len(summary)),
        "budget_fractions": budget_fractions,
        "audit_policies": policies,
        "inputs": {
            "ctc_universe_sha256": sha256_file(Path(args.ctc_universe)),
            "wbm_summary_sha256": sha256_file(Path(args.wbm_summary)),
            "cgcnn_predictions_sha256": sha256_file(Path(args.cgcnn_predictions)),
            "alignn_predictions_sha256": sha256_file(Path(args.alignn_predictions)),
        },
        "claim_boundary": "simulated audit frontier; not prospective materials discovery; A3 unchanged",
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
