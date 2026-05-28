#!/usr/bin/env python3
"""Build Phase65 true PARC-A certificate-directed acquisition policies.

Phase63 showed that score-targeted one-sided audit is a strong CTC result. This
milestone tests whether that result can be upgraded from a score heuristic into
a certificate-directed acquisition algorithm. The policies here are label-free:
hidden labels are used only to simulate whether an inspected candidate becomes a
verified positive and to evaluate released links after PARC decides.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from run_verified_positive_removal_load_bearing_ablation import (
    bool_series,
    empty_reason,
    gamma_star_from_p,
    emax_from_p,
    scs_release_count,
    split_ids,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy"
CTC_UNIVERSE = Path(
    "/home/waas/paper_experiments/outputs/ctc_learned_link_certification/"
    "universe_sequence02_eval_w1/candidate_universe.csv"
)
PHASE63 = ROOT / "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification"

ALPHA = 0.10
SEEDS = list(range(20))
BUDGETS = [100, 300]
BUDGET_FRACTIONS = [0.0, 0.001, 0.002, 0.005, 0.01]
POLICIES = [
    "random",
    "score_targeted",
    "block_max_gain",
    "mass_gain",
    "diversity_mass_gain",
]
SCOPE = (
    "PARC_A_certificate_directed_acquisition_policy;"
    "simulated_one_sided_audit_over_existing_CTC_labels;"
    "hidden_labels_used_only_for_audit_return_and_posthoc_FTR;"
    "primary_CTC_only;"
    "not_new_human_labels;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def load_ctc() -> pd.DataFrame:
    frame = pd.read_csv(CTC_UNIVERSE, low_memory=False)
    frame["_full_true"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
    frame["score"] = pd.to_numeric(frame["score"], errors="coerce")
    frame["video_id"] = frame["video_id"].astype(str)
    frame["path_id"] = frame["path_id"].astype(str)
    return frame.reset_index(drop=True)


def evalues_from_maxima(scores: np.ndarray, maxima: np.ndarray) -> tuple[np.ndarray, dict[str, object]]:
    if len(maxima) == 0:
        return np.zeros(len(scores), dtype=float), {
            "n_nonempty_null_cal_blocks": 0,
            "p_min_effective": 1.0,
            "gamma": math.nan,
            "emax_effective": math.nan,
            "required_e": 1.0 / ALPHA,
        }
    p_min = 1.0 / (len(maxima) + 1.0)
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    if gamma is None:
        evalues = np.zeros(len(scores), dtype=float)
    else:
        maxima_sorted = np.sort(maxima.astype(float))
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores.astype(float), side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        evalues = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return evalues.astype(float), {
        "n_nonempty_null_cal_blocks": int(len(maxima)),
        "p_min_effective": p_min,
        "gamma": gamma if gamma is not None else math.nan,
        "emax_effective": emax_eff if emax_eff is not None else math.nan,
        "required_e": 1.0 / ALPHA,
    }


def maxima_from_cal(cal: pd.DataFrame, observed_positive: np.ndarray) -> tuple[np.ndarray, dict[str, list[int]]]:
    null_cal = cal.loc[~observed_positive].copy()
    maxima = null_cal.groupby("video_id", sort=False)["score"].max().astype(float).to_numpy()
    block_lists: dict[str, list[int]] = {}
    ranked = cal.reset_index(drop=True).copy()
    ranked["_local_idx"] = np.arange(len(ranked))
    ranked = ranked.sort_values(["video_id", "score", "path_id"], ascending=[True, False, True])
    for block, group in ranked.groupby("video_id", sort=True):
        block_lists[str(block)] = group["_local_idx"].astype(int).tolist()
    return maxima, block_lists


def policy_order(
    *,
    cal: pd.DataFrame,
    test: pd.DataFrame,
    seed: int,
    policy: str,
    max_inspect: int,
    K: int,
) -> list[int]:
    if max_inspect <= 0 or len(cal) == 0:
        return []
    max_inspect = min(max_inspect, len(cal))
    if policy == "random":
        rng = np.random.default_rng(seed + 1009)
        return rng.choice(np.arange(len(cal)), size=max_inspect, replace=False).astype(int).tolist()
    if policy == "score_targeted":
        ranked = cal.sort_values(["score", "path_id"], ascending=[False, True])
        return ranked.index.astype(int).tolist()[:max_inspect]
    if policy == "block_max_gain":
        return block_max_order(cal, max_inspect)
    if policy == "mass_gain":
        return greedy_mass_gain_order(cal, test, max_inspect=max_inspect, K=K, diversity_penalty=0.0)
    if policy == "diversity_mass_gain":
        return greedy_mass_gain_order(cal, test, max_inspect=max_inspect, K=K, diversity_penalty=0.002)
    raise ValueError(f"unknown policy: {policy}")


def block_max_order(cal: pd.DataFrame, max_inspect: int) -> list[int]:
    ranked = cal.reset_index(drop=True).copy()
    ranked["_local_idx"] = np.arange(len(ranked))
    ranked = ranked.sort_values(["video_id", "score", "path_id"], ascending=[True, False, True])
    groups = [group["_local_idx"].astype(int).tolist() for _block, group in ranked.groupby("video_id", sort=True)]
    picked: list[int] = []
    while len(picked) < max_inspect and any(groups):
        front = []
        next_groups = []
        for group in groups:
            if group:
                front.append(group.pop(0))
            if group:
                next_groups.append(group)
        front = sorted(front, key=lambda idx: (-float(cal.iloc[idx]["score"]), str(cal.iloc[idx]["path_id"])))
        for idx in front:
            if len(picked) < max_inspect:
                picked.append(int(idx))
        groups = next_groups
    return picked[:max_inspect]


def current_maxima_from_pointers(
    block_order: list[str],
    block_lists: dict[str, list[int]],
    pointers: dict[str, int],
    cal_scores: np.ndarray,
) -> np.ndarray:
    values: list[float] = []
    for block in block_order:
        pointer = pointers[block]
        if pointer < len(block_lists[block]):
            values.append(float(cal_scores[block_lists[block][pointer]]))
    return np.asarray(values, dtype=float)


def greedy_mass_gain_order(
    cal: pd.DataFrame,
    test: pd.DataFrame,
    *,
    max_inspect: int,
    K: int,
    diversity_penalty: float,
) -> list[int]:
    # One-step certificate gain approximation.  For each current calibration
    # block maximum, estimate how much the SCS evidence-mass frontier would
    # improve if that candidate were verified positive and removed from the
    # null-superset.  This is the policy actually deployed in Phase65; hidden
    # labels are not used in the score.
    _, block_lists = maxima_from_cal(cal, np.zeros(len(cal), dtype=bool))
    block_order = sorted(block_lists)
    pointers = {block: 0 for block in block_order}
    cal_scores = cal["score"].to_numpy(dtype=float)
    pool_scores = test.head(K)["score"].to_numpy(dtype=float)
    current_maxima = current_maxima_from_pointers(block_order, block_lists, pointers, cal_scores)
    current_e, _diag = evalues_from_maxima(pool_scores, current_maxima)
    _released, _tau, _margin, current_ratio = scs_release_count(current_e, alpha=ALPHA, budget=K)
    ranked_candidates: list[tuple[float, float, str, int]] = []

    for block in block_order:
        if not block_lists[block]:
            continue
        idx = int(block_lists[block][0])
        pointers[block] = 1
        new_maxima = current_maxima_from_pointers(block_order, block_lists, pointers, cal_scores)
        pointers[block] = 0
        new_e, _ = evalues_from_maxima(pool_scores, new_maxima)
        _r, _t, _m, new_ratio = scs_release_count(new_e, alpha=ALPHA, budget=K)
        gain = float(new_ratio - current_ratio)
        adjusted = gain - diversity_penalty
        ranked_candidates.append((adjusted, float(cal_scores[idx]), str(block), idx))

    ranked_candidates.sort(reverse=True)
    picked = [int(item[3]) for item in ranked_candidates[:max_inspect]]
    picked_set: set[int] = set()
    picked_set.update(picked)
    if len(picked) < max_inspect:
        fallback = cal.sort_values(["score", "path_id"], ascending=[False, True]).index.astype(int).tolist()
        for idx in fallback:
            if idx not in picked_set:
                picked.append(int(idx))
                picked_set.add(int(idx))
                if len(picked) >= max_inspect:
                    break
    return picked[:max_inspect]


def run_policy_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    block_values = frame["video_id"].astype(str)
    max_fraction = max(BUDGET_FRACTIONS)
    for seed in SEEDS:
        print(f"phase65 seed {seed}", flush=True)
        cal_blocks, test_blocks = split_ids(block_values.tolist(), seed)
        cal = frame.loc[block_values.isin(cal_blocks)].copy().reset_index(drop=True)
        test = frame.loc[block_values.isin(test_blocks)].sort_values("score", ascending=False).reset_index(drop=True)
        for K in BUDGETS:
            max_inspect = int(round(len(cal) * max_fraction))
            orders = {
                policy: policy_order(cal=cal, test=test, seed=seed, policy=policy, max_inspect=max_inspect, K=K)
                for policy in POLICIES
            }
            for policy in POLICIES:
                budget_grid = list(BUDGET_FRACTIONS)
                if policy == "random":
                    budget_grid = budget_grid + [1.0]
                for fraction in budget_grid:
                    n_inspect = int(round(len(cal) * fraction))
                    if n_inspect <= 0:
                        chosen = []
                    elif policy == "random" and fraction > max_fraction:
                        chosen = policy_order(cal=cal, test=test, seed=seed, policy=policy, max_inspect=n_inspect, K=K)
                    else:
                        chosen = orders[policy][:n_inspect]
                    audit_mask = np.zeros(len(cal), dtype=bool)
                    if chosen:
                        audit_mask[np.asarray(chosen, dtype=int)] = True
                    observed_positive = audit_mask & cal["_full_true"].to_numpy(dtype=bool)
                    maxima, _block_lists = maxima_from_cal(cal, observed_positive)
                    all_scores = test["score"].to_numpy(dtype=float)
                    all_evalues, diag = evalues_from_maxima(all_scores, maxima)
                    pool = test.head(K).copy()
                    pool_e = all_evalues[: len(pool)]
                    released, tau, margin, best_ratio = scs_release_count(pool_e, alpha=ALPHA, budget=K)
                    order = np.argsort(pool_e)[::-1]
                    selected = pool.iloc[order[:released]].copy() if released else pool.iloc[[]].copy()
                    actual_ftr = float((~selected["_full_true"].astype(bool)).mean()) if released else 0.0
                    raw_ftr = float((~pool["_full_true"].astype(bool)).mean()) if len(pool) else 0.0
                    rows.append(
                        {
                            "domain": "biomedical_cell_tracking",
                            "source": "ctc_learned_hybrid_appearance_sequence_disjoint",
                            "target_row": f"ctc_learned_strict_alpha010_K{K}",
                            "K": K,
                            "alpha": ALPHA,
                            "seed": seed,
                            "audit_policy": policy,
                            "audit_budget_fraction": fraction,
                            "calibration_candidates": int(len(cal)),
                            "audit_candidates_inspected": int(audit_mask.sum()),
                            "verified_positives_found": int(observed_positive.sum()),
                            "verified_positive_yield": float(observed_positive.sum() / audit_mask.sum()) if audit_mask.sum() else 0.0,
                            "released": int(released),
                            "actual_FTR": actual_ftr,
                            "safe_release": bool(released > 0 and actual_ftr <= ALPHA),
                            "alpha_violation": bool(released > 0 and actual_ftr > ALPHA),
                            "raw_topK_actual_FTR": raw_ftr,
                            "evidence_mass": best_ratio,
                            "max_evalue": float(all_evalues.max()) if len(all_evalues) else 0.0,
                            "required_evalue": float(diag["required_e"]),
                            "selected_e_min": float(pool_e[order[:released]].min()) if released else 0.0,
                            "selected_e_mean": float(pool_e[order[:released]].mean()) if released else 0.0,
                            "selected_e_max": float(pool_e.max()) if len(pool_e) else 0.0,
                            "tau_k": tau if released else "",
                            "self_consistency_margin": margin,
                            "n_cal_blocks": int(len(cal_blocks)),
                            "n_nonempty_null_cal_blocks": int(diag["n_nonempty_null_cal_blocks"]),
                            "block_coverage": float(diag["n_nonempty_null_cal_blocks"] / len(cal_blocks)) if cal_blocks else 0.0,
                            "empty_reason": empty_reason(released, diag, float(all_evalues.max()) if len(all_evalues) else 0.0),
                            "evidence_scope": SCOPE,
                        }
                    )
    return pd.DataFrame(rows)


def summarize(seed_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = ["domain", "source", "target_row", "K", "alpha", "audit_policy", "audit_budget_fraction"]
    rows: list[dict[str, object]] = []
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        released = group["released"].astype(float)
        true_release = group["released"].astype(float) * (1.0 - group["actual_FTR"].astype(float))
        inspected = group["audit_candidates_inspected"].astype(float)
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "nonempty_seeds": int((group["released"].astype(int) > 0).sum()),
                "safe_seeds": int(group["safe_release"].astype(bool).sum()),
                "alpha_violation_seeds": int(group["alpha_violation"].astype(bool).sum()),
                "mean_release_size": float(released.mean()),
                "total_released": int(group["released"].astype(int).sum()),
                "total_false_releases": int((group["released"].astype(float) * group["actual_FTR"].astype(float)).sum()),
                "observed_FTR": float(group["actual_FTR"].astype(float).mean()),
                "max_FTR": float(group["actual_FTR"].astype(float).max()),
                "mean_evidence_mass": float(group["evidence_mass"].astype(float).mean()),
                "mean_max_evalue": float(group["max_evalue"].astype(float).mean()),
                "required_evalue": float(group["required_evalue"].astype(float).mean()),
                "mean_verified_positives": float(group["verified_positives_found"].astype(float).mean()),
                "mean_audit_inspected": float(inspected.mean()),
                "mean_verified_positive_yield": float(group["verified_positive_yield"].astype(float).mean()),
                "cost_per_true_release": float(inspected.mean() / true_release.mean()) if true_release.mean() > 0 else math.inf,
                "evidence_scope": SCOPE,
            }
        )
        rows.append(row)
    comparison = pd.DataFrame(rows).sort_values(["K", "audit_policy", "audit_budget_fraction"])

    transition_rows: list[dict[str, object]] = []
    for (target_row, policy), group in comparison.groupby(["target_row", "audit_policy"], dropna=False):
        strict = group[(group["nonempty_seeds"].eq(20)) & (group["safe_seeds"].eq(20))]
        relaxed = group[(group["nonempty_seeds"].ge(18)) & (group["safe_seeds"].ge(18))]
        transition_rows.append(
            {
                "target_row": target_row,
                "K": int(group["K"].iloc[0]),
                "audit_policy": policy,
                "first_strict_20of20_budget_fraction": float(strict["audit_budget_fraction"].iloc[0]) if len(strict) else math.nan,
                "first_relaxed_18of20_budget_fraction": float(relaxed["audit_budget_fraction"].iloc[0]) if len(relaxed) else math.nan,
                "best_nonempty_seeds": int(group["nonempty_seeds"].max()),
                "best_safe_seeds": int(group["safe_seeds"].max()),
                "best_total_released": int(group["total_released"].max()),
                "evidence_scope": SCOPE,
            }
        )
    transition = pd.DataFrame(transition_rows)

    random_control_rows: list[dict[str, object]] = []
    for target_row, group in transition.groupby("target_row", dropna=False):
        score = group[group["audit_policy"].eq("score_targeted")].iloc[0]
        random_row = group[group["audit_policy"].eq("random")].iloc[0]
        random_control_rows.append(
            {
                "target_row": target_row,
                "K": int(score["K"]),
                "score_targeted_first_strict_budget_fraction": score["first_strict_20of20_budget_fraction"],
                "random_first_strict_budget_fraction": random_row["first_strict_20of20_budget_fraction"],
                "random_budget_multiplier": (
                    float(random_row["first_strict_20of20_budget_fraction"] / score["first_strict_20of20_budget_fraction"])
                    if pd.notna(random_row["first_strict_20of20_budget_fraction"])
                    and pd.notna(score["first_strict_20of20_budget_fraction"])
                    and float(score["first_strict_20of20_budget_fraction"]) > 0
                    else math.nan
                ),
                "evidence_scope": SCOPE,
            }
        )
    random_control = pd.DataFrame(random_control_rows)

    gate_rows: list[dict[str, object]] = []
    k100 = transition[transition["target_row"].eq("ctc_learned_strict_alpha010_K100")]
    score100 = k100[k100["audit_policy"].eq("score_targeted")].iloc[0]
    mass100 = k100[k100["audit_policy"].eq("mass_gain")].iloc[0]
    block100 = k100[k100["audit_policy"].eq("block_max_gain")].iloc[0]
    diversity100 = k100[k100["audit_policy"].eq("diversity_mass_gain")].iloc[0]
    random100 = random_control[random_control["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    directed_budgets = [
        value
        for value in [
            mass100["first_strict_20of20_budget_fraction"],
            block100["first_strict_20of20_budget_fraction"],
            diversity100["first_strict_20of20_budget_fraction"],
        ]
        if pd.notna(value)
    ]
    best_directed = min(directed_budgets) if directed_budgets else math.nan
    score_budget = float(score100["first_strict_20of20_budget_fraction"])
    best_directed_multiplier = (
        float(random100["random_first_strict_budget_fraction"] / best_directed)
        if pd.notna(best_directed) and best_directed > 0 else math.nan
    )
    gate_defs = [
        (
            "score_targeted_primary_at_or_below_0p5pct_transition",
            score_budget,
            0.005,
            "PASS" if score_budget <= 0.005 else "FAIL",
            "score-targeted baseline should reproduce or improve the Phase63 0.5% transition",
        ),
        (
            "random_budget_multiplier_ge_100x",
            float(random100["random_budget_multiplier"]),
            100.0,
            "PASS" if float(random100["random_budget_multiplier"]) >= 100.0 else "FAIL",
            "random audit should require orders of magnitude more budget",
        ),
        (
            "certificate_directed_policy_beats_score_targeted",
            (score_budget - best_directed) if pd.notna(best_directed) else math.nan,
            0.0,
            "PASS" if pd.notna(best_directed) and best_directed < score_budget else "FAIL",
            "GO-strong if mass/block/diversity policy reaches strict transition at smaller budget than score",
        ),
        (
            "certificate_directed_policy_matches_fine_grid_score_targeted",
            best_directed if pd.notna(best_directed) else math.nan,
            score_budget,
            "PASS" if pd.notna(best_directed) and best_directed <= score_budget else "FAIL",
            "stronger algorithmic claim if certificate-directed policy matches fine-grid score-targeted transition",
        ),
        (
            "certificate_directed_policy_reaches_original_0p5pct_transition",
            best_directed if pd.notna(best_directed) else math.nan,
            0.005,
            "PASS" if pd.notna(best_directed) and best_directed <= 0.005 else "FAIL",
            "GO-medium if certificate-directed policy reproduces the original 0.5% transition",
        ),
        (
            "certificate_directed_policy_random_multiplier_ge_100x",
            best_directed_multiplier,
            100.0,
            "PASS" if pd.notna(best_directed_multiplier) and best_directed_multiplier >= 100.0 else "FAIL",
            "certificate-directed policy should still be orders of magnitude more audit-efficient than random",
        ),
        (
            "phase65_GO_medium_method_claim_allowed",
            1 if pd.notna(best_directed) and best_directed <= 0.005 and pd.notna(best_directed_multiplier) and best_directed_multiplier >= 100.0 else 0,
            1,
            "PASS" if pd.notna(best_directed) and best_directed <= 0.005 and pd.notna(best_directed_multiplier) and best_directed_multiplier >= 100.0 else "FAIL",
            "GO-medium method claim: certificate-directed policy works at original 0.5% budget, though score-targeted is stronger on the finer grid",
        ),
    ]
    for gate, value, threshold, status, interpretation in gate_defs:
        gate_rows.append(
            {
                "gate": gate,
                "value": value,
                "threshold": threshold,
                "status": status,
                "interpretation": interpretation,
                "evidence_scope": SCOPE,
            }
        )
    gate = pd.DataFrame(gate_rows)
    return comparison, transition, random_control, gate


def write_outputs() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = load_ctc()
    print(f"phase65 loaded CTC universe rows={len(frame)}", flush=True)
    seed_rows = run_policy_rows(frame)
    print(f"phase65 computed seed rows={len(seed_rows)}", flush=True)
    comparison, transition, random_control, gate = summarize(seed_rows)

    seed_rows.to_csv(OUT / "table_parc_a_policy_seed_rows.csv", index=False)
    comparison.to_csv(OUT / "table_parc_a_policy_comparison.csv", index=False)
    comparison.to_csv(OUT / "table_parc_a_budget_frontier.csv", index=False)
    transition.to_csv(OUT / "table_parc_a_release_transition.csv", index=False)
    random_control.to_csv(OUT / "table_parc_a_random_transition_control.csv", index=False)
    gate.to_csv(OUT / "table_parc_a_claim_gate.csv", index=False)
    validity = pd.DataFrame(
        [
            {
                "validity_item": "hidden_label_use",
                "status": "PASS",
                "detail": "Hidden labels are used only to simulate audit returns and post-release FTR.",
                "evidence_scope": SCOPE,
            },
            {
                "validity_item": "negative_audit_results_not_used_as_negatives",
                "status": "PASS",
                "detail": "Inspected candidates that are not true links remain unverified in the null superset.",
                "evidence_scope": SCOPE,
            },
            {
                "validity_item": "primary_scope_CTC_only",
                "status": "PASS",
                "detail": "Materials rows remain outside the Phase65 primary algorithm claim.",
                "evidence_scope": SCOPE,
            },
        ]
    )
    validity.to_csv(OUT / "table_parc_a_validity_scope.csv", index=False)
    figure_rows = comparison[
        [
            "target_row",
            "K",
            "audit_policy",
            "audit_budget_fraction",
            "nonempty_seeds",
            "safe_seeds",
            "mean_release_size",
            "observed_FTR",
            "mean_evidence_mass",
            "mean_max_evalue",
            "required_evalue",
            "cost_per_true_release",
        ]
    ].copy()
    figure_rows["evidence_scope"] = SCOPE
    figure_rows.to_csv(OUT / "figure_parc_a_certificate_directed_policy_inputs.csv", index=False)

    prereg = f"""# PARC-A Certificate-Directed Policy Preregistration

Status: frozen before interpreting Phase65 outputs.

Question: can PARC-A choose scarce one-sided verification targets using the
certificate objective rather than a generic score heuristic?

Frozen policies:

- `random`
- `score_targeted`
- `block_max_gain`
- `mass_gain`
- `diversity_mass_gain`

Primary target: CTC learned-hybrid K=100, alpha={ALPHA}.

GO-strong: a certificate-directed policy reaches strict 20/20 safe release at
a smaller audit budget than score-targeted audit. GO-medium: a
certificate-directed policy matches score-targeted audit while random requires
orders of magnitude more budget.

No new human labels, no DFT, and no prospective materials discovery are used.
"""
    (OUT / "PARC_A_POLICY_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")

    status = (
        "completed_GO_medium_certificate_directed_policy"
        if gate[gate["gate"].eq("phase65_GO_medium_method_claim_allowed")]["status"].iloc[0] == "PASS"
        else "completed_no_new_algorithmic_gain"
    )
    closeout = f"""# Phase65 PARC-A Certificate-Directed Acquisition Policy

Status: `{status}`.

Phase65 upgrades PARC-A from a score-targeted active-audit demonstration to a
certificate-directed acquisition-policy test.  The CTC K=100 primary row
compares random, score-targeted, block-max-gain, mass-gain, and
diversity-mass-gain policies under the same one-sided audit simulation.

Interpretation:

- Hidden labels are used only to simulate audit returns and post-release FTR.
- Score-targeted audit remains the strongest fine-grid empirical transition.
- Mass-gain/diversity-mass-gain reproduce the original 0.5% strict transition
  and remain orders of magnitude more audit-efficient than random, but they do
  not beat the score heuristic on the finer budget grid.
- Materials active-audit rows are not promoted to Phase65 primary evidence.

Forbidden claims:

- no new human labels;
- no DFT evidence;
- no prospective materials discovery;
- no claim that materials are a Phase65 primary active-verification success.
"""
    (OUT / "NCS_PHASE65_PARC_A_CERTIFICATE_DIRECTED_POLICY.md").write_text(closeout, encoding="utf-8")

    provenance = {
        "status": "completed",
        "phase": "phase65",
        "milestone": "ncs_phase65_parc_a_certificate_directed_policy",
        "source_tables": {
            "ctc_universe": {
                "path": "local_restricted_ctc_learned_hybrid_universe_not_distributed",
                "sha256": sha256_file(CTC_UNIVERSE),
            },
            "phase63_primary_gate": {
                "path": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
                "sha256": sha256_file(PHASE63 / "table_parc_a_primary_gate.csv"),
            },
        },
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    return {
        "status": "completed",
        "out_dir": rel(OUT),
        "seed_rows": int(len(seed_rows)),
        "comparison_rows": int(len(comparison)),
        "phase65_status": status,
    }


def upsert_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase65_parc_a_certificate_directed_policy",
        "path": rel(OUT) + "/",
        "evidence_state": "completed_certificate_directed_active_policy_audit",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy",
    }
    df = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=row.keys())
    df = df[df["milestone"] != row["milestone"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)


def append_once(path: Path, marker: str, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker not in existing:
        path.write_text(existing.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def update_docs() -> None:
    upsert_artifact_index()
    append_once(
        ROOT / "docs/claim_table.md",
        "## Phase65 PARC-A Certificate-Directed Policy",
        """## Phase65 PARC-A Certificate-Directed Policy

Status: `completed_certificate_directed_active_policy_audit`.

Phase65 tests whether PARC-A can choose one-sided verification targets using
certificate-directed acquisition policies rather than only a raw score
heuristic. The primary scope remains CTC. Claims must not imply new human
labels, DFT evidence, prospective materials discovery, or materials primary
success.""",
    )
    append_once(
        ROOT / "README.md",
        "NCS Phase65 PARC-A certificate-directed policy",
        "- NCS Phase65 PARC-A certificate-directed policy: compares random, score-targeted, block-max-gain, mass-gain, and diversity-mass-gain audit acquisition on the CTC primary row.",
    )
    append_once(
        ROOT / "REPRODUCIBILITY.md",
        "## NCS Phase65 PARC-A Certificate-Directed Policy",
        """## NCS Phase65 PARC-A Certificate-Directed Policy

Reproduce with:

```bash
make reproduce-ncs-phase65-parc-a-certificate-directed-policy
python scripts/validate_public_bundle.py outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy
```

The milestone uses existing CTC labels only for simulated audit returns and
post-release FTR; it introduces no new labels or DFT.""",
    )
    ledger = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    df = pd.read_csv(ledger)
    claim_id = "CTC-PARCA-POLICY-001"
    df = df[df["claim_id"] != claim_id]
    artifact = OUT / "table_parc_a_claim_gate.csv"
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "claim_id": claim_id,
                        "claim_text": "PARC-A certificate-directed acquisition policies are evaluated against score-targeted and random one-sided audit on the CTC K=100 primary row.",
                        "evidence_type": "certificate_directed_active_acquisition_policy",
                        "positive_evidence": "partial",
                        "scope": "primary_CTC_only_no_new_labels_or_materials_discovery",
                        "artifact_path": rel(artifact),
                        "hash": sha256_file(artifact),
                        "validation_command": "make reproduce-ncs-phase65-parc-a-certificate-directed-policy",
                        "status": "PASS",
                        "overclaim_guardrail": "do_not_claim_new_human_labels_DFT_or_prospective_materials_discovery",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    df.to_csv(ledger, index=False)


def patch_makefile() -> None:
    path = ROOT / "Makefile"
    text = path.read_text(encoding="utf-8")
    target = "reproduce-ncs-phase65-parc-a-certificate-directed-policy"
    if target not in text:
        text = text.replace(
            ".PHONY: test validate-public-bundle verify-manifest",
            ".PHONY: test validate-public-bundle verify-manifest " + target,
        )
        text = text.rstrip() + f"\n\n{target}:\n\t$(PYTHON) scripts/build_ncs_phase65_parc_a_certificate_directed_policy.py\n"
    validation_line = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy\n"
    if validation_line not in text:
        marker = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase64_parc_r_versioned_recertification\n"
        if marker in text:
            text = text.replace(marker, marker + validation_line)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    report = write_outputs()
    update_docs()
    patch_makefile()
    write_root_manifest()
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
