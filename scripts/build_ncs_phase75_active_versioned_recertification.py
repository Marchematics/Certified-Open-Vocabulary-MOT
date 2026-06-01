#!/usr/bin/env python3
"""Build Phase75 active versioned recertification artifacts.

Phase74 showed that passive risk-gated current-MP recertification still
refuses.  Phase75 asks whether a small amount of targeted, calibration-side
one-sided t1 support can restore a non-empty self-consistent t1 release.

This is public-label recertification emulation.  It is not DFT evidence and it
is not prospective materials discovery.
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

from run_materials_discovery_parc_flagship import gamma_star_from_p, scs_release_count


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE69 = ROOT / "outputs/milestones/ncs_phase69_durability_budgeted_parc"
OUT = ROOT / "outputs/milestones/ncs_phase75_active_versioned_recertification"

ALPHA = 0.10
SEEDS = list(range(20))
K_GRID = [20, 50, 100, 150, 300, 500]
BUDGET_FRACTIONS = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 1.00]
POLICIES = [
    "random_t1_audit",
    "score_targeted_t1_audit",
    "low_risk_score_targeted_t1_audit",
    "system_margin_distribution_low_risk_then_score",
    "blockmax_gain_t1_audit",
    "mass_gain_t1_audit",
    "diversity_mass_gain_t1_audit",
]
SUPPORT_MODES = {
    "t1_10pct_support": 0.10,
    "t1_full_calibration_block_support": 1.00,
}
PRIMARY_RISK_MODEL = "system_margin_distribution"
SCOPE = (
    "active_versioned_recertification;"
    "current_MP_t1_public_label_emulation;"
    "t1_labels_used_only_as_calibration_side_one_sided_positives;"
    "test_side_t1_labels_used_only_after_release_for_FTR;"
    "audit_policy_frozen_before_release;"
    "nullsuperset_denominator_recomputed_after_audit;"
    "self_consistency_recalculated;"
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


def split_blocks(block_ids: list[str], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def load_queue() -> pd.DataFrame:
    path = PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"
    queue = pd.read_csv(path)
    queue = queue[queue["K"].eq(500)].copy()
    queue = queue.rename(columns={"material_id": "candidate_id"})
    queue["candidate_id"] = queue["candidate_id"].astype(str)
    queue = queue.sort_values(["raw_rank", "candidate_id"]).drop_duplicates("candidate_id").reset_index(drop=True)
    queue["block_id"] = queue["chemical_system"].astype(str)
    queue["score_for_recertification"] = pd.to_numeric(queue["alignn_score"], errors="coerce")
    queue["raw_rank"] = pd.to_numeric(queue["raw_rank"], errors="coerce")
    queue["t0_stable"] = queue["stable_exact_t0"].astype(bool)
    queue["t1_stable"] = queue["stable_exact_t1_current_mp"].astype(bool)
    return attach_risk_scores(queue)


def attach_risk_scores(queue: pd.DataFrame) -> pd.DataFrame:
    scores = pd.read_csv(PHASE69 / "table_crossfit_durability_risk_scores.csv")
    scores = scores[scores["risk_model"].eq(PRIMARY_RISK_MODEL)].copy()
    system_risk = scores.groupby("chemical_system", sort=False)["crossfit_durability_risk"].mean()
    out = queue.copy()
    out["risk_model"] = PRIMARY_RISK_MODEL
    out["crossfit_system_durability_risk"] = out["chemical_system"].map(system_risk)
    out["risk_score_available"] = out["crossfit_system_durability_risk"].notna()
    # Missing risk scores are treated as high risk for low-risk policies, but
    # remain available to non-risk policies.
    max_risk = float(out["crossfit_system_durability_risk"].max(skipna=True))
    out["_risk_sort"] = out["crossfit_system_durability_risk"].fillna(max_risk + 1.0)
    return out


def evalues_from_maxima(scores: np.ndarray, maxima: np.ndarray) -> tuple[np.ndarray, dict[str, object]]:
    if len(maxima) == 0:
        return np.zeros(len(scores), dtype=float), {
            "nonempty_calibration_null_blocks": 0,
            "p_min_effective": 1.0,
            "gamma": math.nan,
        }
    p_min = 1.0 / (len(maxima) + 1.0)
    gamma = gamma_star_from_p(p_min)
    if gamma is None:
        evalues = np.zeros(len(scores), dtype=float)
    else:
        maxima_sorted = np.sort(maxima.astype(float))
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores.astype(float), side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        evalues = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return evalues.astype(float), {
        "nonempty_calibration_null_blocks": int(len(maxima)),
        "p_min_effective": p_min,
        "gamma": gamma if gamma is not None else math.nan,
    }


def recompute_evalues(
    frame: pd.DataFrame,
    *,
    cal_blocks: set[str],
    followup_blocks: set[str],
    observed_positive: np.ndarray,
) -> tuple[pd.DataFrame, dict[str, object]]:
    block_series = frame["block_id"].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    followup_mask = block_series.isin(followup_blocks).to_numpy()
    cal_null = frame.loc[cal_mask & ~observed_positive, ["block_id", "score_for_recertification"]]
    maxima = (
        cal_null.groupby("block_id", sort=False)["score_for_recertification"].max().astype(float).to_numpy()
        if len(cal_null)
        else np.asarray([], dtype=float)
    )
    followup = frame.loc[followup_mask].sort_values("score_for_recertification", ascending=False).copy()
    evalues, diag = evalues_from_maxima(followup["score_for_recertification"].to_numpy(dtype=float), maxima)
    followup["_active_t1_evalue"] = evalues
    diag.update(
        {
            "calibration_blocks": int(len(cal_blocks)),
            "followup_blocks": int(len(followup_blocks)),
            "block_coverage": float(len(maxima) / len(cal_blocks)) if cal_blocks else 0.0,
            "denominator_recomputed_after_audit": True,
            "evalues_recomputed_after_audit": True,
        }
    )
    return followup, diag


def blockmax_order(cal: pd.DataFrame, max_inspect: int) -> list[int]:
    if max_inspect <= 0 or len(cal) == 0:
        return []
    ranked = cal.reset_index(drop=True).copy()
    ranked["_local_idx"] = np.arange(len(ranked))
    ranked = ranked.sort_values(["block_id", "score_for_recertification", "candidate_id"], ascending=[True, False, True])
    groups = [group["_local_idx"].astype(int).tolist() for _block, group in ranked.groupby("block_id", sort=True)]
    picked: list[int] = []
    while len(picked) < max_inspect and any(groups):
        front: list[int] = []
        next_groups: list[list[int]] = []
        for group in groups:
            if group:
                front.append(group.pop(0))
            if group:
                next_groups.append(group)
        front = sorted(
            front,
            key=lambda idx: (-float(cal.iloc[idx]["score_for_recertification"]), str(cal.iloc[idx]["candidate_id"])),
        )
        for idx in front:
            if len(picked) < max_inspect:
                picked.append(int(idx))
        groups = next_groups
    return picked[:max_inspect]


def mass_gain_order(cal: pd.DataFrame, test: pd.DataFrame, *, max_inspect: int, k: int, diversity: bool) -> list[int]:
    if max_inspect <= 0 or len(cal) == 0:
        return []
    work = cal.reset_index(drop=True).copy()
    work["_local_idx"] = np.arange(len(work))
    work = work.sort_values(["block_id", "score_for_recertification", "candidate_id"], ascending=[True, False, True])
    block_lists: dict[str, list[int]] = {
        str(block): group["_local_idx"].astype(int).tolist() for block, group in work.groupby("block_id", sort=True)
    }
    block_order = sorted(block_lists)
    cal_scores = cal["score_for_recertification"].to_numpy(dtype=float)
    pool_scores = test.head(k)["score_for_recertification"].to_numpy(dtype=float)
    current_maxima = np.asarray([cal_scores[block_lists[block][0]] for block in block_order if block_lists[block]], dtype=float)
    current_e, _diag = evalues_from_maxima(pool_scores, current_maxima)
    _r, _tau, _margin, current_mass = scs_release_count(current_e, alpha=ALPHA, budget=k)
    gains: list[tuple[float, float, str, int]] = []
    for block in block_order:
        ids = block_lists[block]
        if not ids:
            continue
        idx = int(ids[0])
        new_maxima = []
        for other in block_order:
            other_ids = block_lists[other]
            if not other_ids:
                continue
            pointer = 1 if other == block else 0
            if pointer < len(other_ids):
                new_maxima.append(float(cal_scores[other_ids[pointer]]))
        new_e, _ = evalues_from_maxima(pool_scores, np.asarray(new_maxima, dtype=float))
        _r2, _tau2, _margin2, new_mass = scs_release_count(new_e, alpha=ALPHA, budget=k)
        penalty = 0.001 * len(gains) if diversity else 0.0
        gains.append((float(new_mass - current_mass - penalty), float(cal_scores[idx]), block, idx))
    gains.sort(reverse=True)
    picked = [int(item[3]) for item in gains[:max_inspect]]
    picked_set = set(picked)
    if len(picked) < max_inspect:
        fallback = cal.sort_values(["score_for_recertification", "candidate_id"], ascending=[False, True]).index.astype(int).tolist()
        for idx in fallback:
            if idx not in picked_set:
                picked.append(int(idx))
                picked_set.add(int(idx))
                if len(picked) >= max_inspect:
                    break
    return picked[:max_inspect]


def policy_order(cal: pd.DataFrame, test: pd.DataFrame, *, policy: str, max_inspect: int, seed: int, k: int) -> list[int]:
    if max_inspect <= 0 or len(cal) == 0:
        return []
    max_inspect = min(max_inspect, len(cal))
    local = cal.reset_index(drop=True).copy()
    if policy == "random_t1_audit":
        rng = np.random.default_rng(seed + 7501 + k)
        return rng.choice(np.arange(len(local)), size=max_inspect, replace=False).astype(int).tolist()
    if policy == "score_targeted_t1_audit":
        return local.sort_values(["score_for_recertification", "candidate_id"], ascending=[False, True]).index.astype(int).tolist()[:max_inspect]
    if policy == "low_risk_score_targeted_t1_audit":
        local["_score_rank"] = local["score_for_recertification"].rank(method="average", pct=True)
        local["_risk_rank"] = local["_risk_sort"].rank(method="average", pct=True, ascending=True)
        local["_low_risk_score"] = local["_score_rank"] - 0.25 * local["_risk_rank"]
        return local.sort_values(["_low_risk_score", "score_for_recertification", "candidate_id"], ascending=[False, False, True]).index.astype(int).tolist()[:max_inspect]
    if policy == "system_margin_distribution_low_risk_then_score":
        return local.sort_values(["_risk_sort", "score_for_recertification", "candidate_id"], ascending=[True, False, True]).index.astype(int).tolist()[:max_inspect]
    if policy == "blockmax_gain_t1_audit":
        return blockmax_order(local, max_inspect)
    if policy == "mass_gain_t1_audit":
        return mass_gain_order(local, test.reset_index(drop=True), max_inspect=max_inspect, k=k, diversity=False)
    if policy == "diversity_mass_gain_t1_audit":
        return mass_gain_order(local, test.reset_index(drop=True), max_inspect=max_inspect, k=k, diversity=True)
    raise ValueError(f"unknown active recertification policy: {policy}")


def run_seed_rows(queue: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    block_values = queue["block_id"].astype(str)
    max_fraction = max(BUDGET_FRACTIONS)
    for seed in SEEDS:
        cal_blocks, followup_blocks = split_blocks(block_values.tolist(), seed)
        cal_mask = block_values.isin(cal_blocks).to_numpy()
        followup_mask = block_values.isin(followup_blocks).to_numpy()
        cal = queue.loc[cal_mask].copy().reset_index(drop=True)
        test = queue.loc[followup_mask].sort_values("score_for_recertification", ascending=False).copy().reset_index(drop=True)
        for k in K_GRID:
            max_inspect = int(round(len(cal) * max_fraction))
            orders = {
                policy: policy_order(cal, test, policy=policy, max_inspect=max_inspect, seed=seed, k=k)
                for policy in POLICIES
            }
            for support_mode, support_cap in SUPPORT_MODES.items():
                for policy in POLICIES:
                    for budget_requested in BUDGET_FRACTIONS:
                        budget_effective = min(float(budget_requested), float(support_cap))
                        n_inspect = int(round(len(cal) * budget_effective))
                        chosen = orders[policy][:n_inspect] if n_inspect > 0 else []
                        audit_mask_local = np.zeros(len(cal), dtype=bool)
                        if chosen:
                            audit_mask_local[np.asarray(chosen, dtype=int)] = True

                        full_observed = np.zeros(len(queue), dtype=bool)
                        cal_indices = np.flatnonzero(cal_mask)
                        observed_local = audit_mask_local & cal["t1_stable"].to_numpy(dtype=bool)
                        full_observed[cal_indices] = observed_local

                        followup, diag = recompute_evalues(
                            queue,
                            cal_blocks=cal_blocks,
                            followup_blocks=followup_blocks,
                            observed_positive=full_observed,
                        )
                        pool = followup.head(k).copy()
                        pool_e = pool["_active_t1_evalue"].to_numpy(dtype=float)
                        released, tau, margin, evidence_mass = scs_release_count(pool_e, alpha=ALPHA, budget=k)
                        if released:
                            order = np.argsort(pool_e)[::-1]
                            selected = pool.iloc[order[:released]].copy()
                            ftr_t1 = float((~selected["t1_stable"].astype(bool)).mean())
                            ftr_t0 = float((~selected["t0_stable"].astype(bool)).mean())
                            false_t1 = int((~selected["t1_stable"].astype(bool)).sum())
                            false_t0 = int((~selected["t0_stable"].astype(bool)).sum())
                        else:
                            selected = pool.iloc[[]].copy()
                            ftr_t1 = math.nan
                            ftr_t0 = math.nan
                            false_t1 = 0
                            false_t0 = 0
                        required = k / (ALPHA * released) if released else math.inf
                        rows.append(
                            {
                                "domain": "materials_discovery",
                                "source": "WBM_ALIGNN_FF_current_MP_t1_recertification",
                                "K": int(k),
                                "alpha": ALPHA,
                                "seed": int(seed),
                                "support_mode": support_mode,
                                "support_cap_fraction": float(support_cap),
                                "audit_policy": policy,
                                "audit_budget_fraction_requested": float(budget_requested),
                                "audit_budget_fraction_effective": float(budget_effective),
                                "calibration_candidates": int(len(cal)),
                                "audit_candidates_inspected": int(audit_mask_local.sum()),
                                "verified_t1_positives_found": int(observed_local.sum()),
                                "verified_positive_yield": float(observed_local.sum() / audit_mask_local.sum()) if audit_mask_local.sum() else 0.0,
                                "release_size": int(released),
                                "release_false_t1": false_t1,
                                "release_false_t0": false_t0,
                                "release_FTR_t1": ftr_t1,
                                "release_FTR_t0": ftr_t0,
                                "safe_release_t1": bool(released > 0 and ftr_t1 <= ALPHA),
                                "self_consistency_pass": bool(released > 0 and margin >= 0),
                                "raw_topK_t1_FTR": float((~pool["t1_stable"].astype(bool)).mean()) if len(pool) else math.nan,
                                "raw_topK_t0_FTR": float((~pool["t0_stable"].astype(bool)).mean()) if len(pool) else math.nan,
                                "max_evalue": float(pool_e.max()) if len(pool_e) else 0.0,
                                "required_evalue_threshold": required,
                                "selected_e_min": float(np.sort(pool_e)[::-1][:released].min()) if released else 0.0,
                                "self_consistency_margin": margin,
                                "evidence_mass": evidence_mass,
                                "tau_k": tau if released else "",
                                "policy_uses_t1_test_labels": False,
                                "t1_labels_used_only_for_calibration_audit": True,
                                "heldout_t1_used_for_selection": False,
                                "denominator_recomputed_after_audit": True,
                                "evalues_recomputed_after_audit": True,
                                "random_transition_control_included": True,
                                "evidence_scope": SCOPE,
                                **diag,
                            }
                        )
    return pd.DataFrame(rows)


def summarize(seed_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = [
        "K",
        "alpha",
        "support_mode",
        "audit_policy",
        "audit_budget_fraction_requested",
        "audit_budget_fraction_effective",
    ]
    rows: list[dict[str, object]] = []
    for key, group in seed_rows.groupby(group_cols, dropna=False, sort=True):
        row = dict(zip(group_cols, key))
        nonempty = int(group["release_size"].gt(0).sum())
        safe = int(group["safe_release_t1"].astype(bool).sum())
        nonempty_ftr = group.loc[group["release_size"].gt(0), "release_FTR_t1"].astype(float)
        mean_ftr = float(nonempty_ftr.mean()) if len(nonempty_ftr) else math.nan
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "nonempty_seeds": nonempty,
                "safe_seeds": safe,
                "mean_release_size": float(group["release_size"].astype(float).mean()),
                "median_release_size": float(group["release_size"].astype(float).median()),
                "max_release_size": int(group["release_size"].astype(int).max()),
                "total_released": int(group["release_size"].astype(int).sum()),
                "total_false_t1": int(group["release_false_t1"].astype(int).sum()),
                "mean_FTR_t1_if_nonempty": mean_ftr,
                "mean_FTR_t1_empty_zero": float(group["release_FTR_t1"].fillna(0).astype(float).mean()),
                "mean_FTR_t0_if_nonempty": float(group.loc[group["release_size"].gt(0), "release_FTR_t0"].astype(float).mean()) if nonempty else math.nan,
                "mean_raw_topK_t1_FTR": float(group["raw_topK_t1_FTR"].astype(float).mean()),
                "mean_verified_t1_positives": float(group["verified_t1_positives_found"].astype(float).mean()),
                "mean_verified_positive_yield": float(group["verified_positive_yield"].astype(float).mean()),
                "mean_max_evalue": float(group["max_evalue"].astype(float).mean()),
                "mean_required_evalue_threshold_if_released": float(group.loc[group["release_size"].gt(0), "required_evalue_threshold"].astype(float).mean()) if nonempty else math.nan,
                "mean_self_consistency_margin": float(group["self_consistency_margin"].astype(float).mean()),
                "mean_evidence_mass": float(group["evidence_mass"].astype(float).mean()),
                "self_consistency_pass_any_seed": bool(group["self_consistency_pass"].astype(bool).any()),
                "evidence_scope": SCOPE,
            }
        )
        rows.append(row)
    comparison = pd.DataFrame(rows).sort_values(group_cols)

    # Same-budget random control.
    random_lookup = comparison[comparison["audit_policy"].eq("random_t1_audit")][
        ["K", "support_mode", "audit_budget_fraction_requested", "nonempty_seeds", "safe_seeds", "mean_release_size"]
    ].rename(
        columns={
            "nonempty_seeds": "random_same_budget_nonempty_seeds",
            "safe_seeds": "random_same_budget_safe_seeds",
            "mean_release_size": "random_same_budget_mean_release_size",
        }
    )
    comparison = comparison.merge(
        random_lookup,
        on=["K", "support_mode", "audit_budget_fraction_requested"],
        how="left",
    )
    comparison["random_same_budget_refuses"] = comparison["random_same_budget_nonempty_seeds"].fillna(0).eq(0)
    comparison["go_strong"] = (
        comparison["audit_policy"].ne("random_t1_audit")
        & comparison["self_consistency_pass_any_seed"].astype(bool)
        & comparison["nonempty_seeds"].ge(18)
        & comparison["safe_seeds"].ge(18)
        & comparison["mean_FTR_t1_if_nonempty"].le(ALPHA)
        & comparison["mean_release_size"].ge(20)
        & comparison["audit_budget_fraction_requested"].le(0.05)
        & comparison["random_same_budget_refuses"].astype(bool)
    )
    comparison["go_medium"] = (
        comparison["audit_policy"].ne("random_t1_audit")
        & comparison["self_consistency_pass_any_seed"].astype(bool)
        & comparison["nonempty_seeds"].ge(18)
        & comparison["mean_FTR_t1_if_nonempty"].le(0.15)
        & comparison["mean_release_size"].ge(10)
    )
    comparison["claim_status"] = np.where(
        comparison["go_strong"],
        "constructive_active_recertification_positive",
        np.where(comparison["go_medium"], "active_recertification_medium_signal", "active_recertification_refusal_or_unsafe"),
    )

    transition_rows: list[dict[str, object]] = []
    for key, group in comparison.groupby(["K", "support_mode", "audit_policy"], dropna=False, sort=True):
        k, support_mode, policy = key
        ordered = group.sort_values("audit_budget_fraction_requested")
        strong = ordered[ordered["go_strong"].astype(bool)]
        medium = ordered[ordered["go_medium"].astype(bool)]
        any_nonempty = ordered[ordered["nonempty_seeds"].gt(0)]
        transition_rows.append(
            {
                "K": int(k),
                "support_mode": support_mode,
                "audit_policy": policy,
                "first_go_strong_budget_fraction": float(strong["audit_budget_fraction_requested"].iloc[0]) if len(strong) else math.nan,
                "first_go_medium_budget_fraction": float(medium["audit_budget_fraction_requested"].iloc[0]) if len(medium) else math.nan,
                "first_any_nonempty_budget_fraction": float(any_nonempty["audit_budget_fraction_requested"].iloc[0]) if len(any_nonempty) else math.nan,
                "best_nonempty_seeds": int(ordered["nonempty_seeds"].max()),
                "best_safe_seeds": int(ordered["safe_seeds"].max()),
                "best_mean_release_size": float(ordered["mean_release_size"].max()),
                "evidence_scope": SCOPE,
            }
        )
    transition = pd.DataFrame(transition_rows)

    random_rows: list[dict[str, object]] = []
    for (k, support_mode), group in transition.groupby(["K", "support_mode"], dropna=False, sort=True):
        random_row = group[group["audit_policy"].eq("random_t1_audit")].iloc[0]
        for _, row in group[group["audit_policy"].ne("random_t1_audit")].iterrows():
            for metric in ["first_go_strong_budget_fraction", "first_go_medium_budget_fraction", "first_any_nonempty_budget_fraction"]:
                active_budget = row[metric]
                random_budget = random_row[metric]
                multiplier = (
                    float(random_budget / active_budget)
                    if pd.notna(active_budget) and pd.notna(random_budget) and float(active_budget) > 0
                    else math.inf
                    if pd.notna(active_budget) and pd.isna(random_budget)
                    else math.nan
                )
                random_rows.append(
                    {
                        "K": int(k),
                        "support_mode": support_mode,
                        "audit_policy": row["audit_policy"],
                        "transition_metric": metric,
                        "active_budget_fraction": active_budget,
                        "random_budget_fraction": random_budget,
                        "random_budget_multiplier": multiplier,
                        "random_same_transition_absent": bool(pd.notna(active_budget) and pd.isna(random_budget)),
                        "evidence_scope": SCOPE,
                    }
                )
    random_control = pd.DataFrame(random_rows)

    release_ftr = comparison[
        [
            "K",
            "alpha",
            "support_mode",
            "audit_policy",
            "audit_budget_fraction_requested",
            "audit_budget_fraction_effective",
            "nonempty_seeds",
            "safe_seeds",
            "mean_release_size",
            "mean_FTR_t1_if_nonempty",
            "mean_FTR_t1_empty_zero",
            "mean_raw_topK_t1_FTR",
            "go_strong",
            "go_medium",
            "claim_status",
            "evidence_scope",
        ]
    ].copy()

    self_consistency = seed_rows[
        [
            "K",
            "alpha",
            "support_mode",
            "audit_policy",
            "audit_budget_fraction_requested",
            "audit_budget_fraction_effective",
            "seed",
            "release_size",
            "max_evalue",
            "required_evalue_threshold",
            "self_consistency_margin",
            "self_consistency_pass",
            "denominator_recomputed_after_audit",
            "evalues_recomputed_after_audit",
            "policy_uses_t1_test_labels",
            "heldout_t1_used_for_selection",
            "evidence_scope",
        ]
    ].copy()
    return comparison, transition, random_control, release_ftr, self_consistency


def write_text(comparison: pd.DataFrame) -> None:
    positives = comparison[comparison["go_strong"].astype(bool)]
    mediums = comparison[comparison["go_medium"].astype(bool)]
    status = "completed_active_recertification_go_strong" if len(positives) else "completed_active_recertification_no_go"
    if len(positives):
        row = positives.sort_values(["audit_budget_fraction_requested", "K", "mean_release_size"], ascending=[True, True, False]).iloc[0]
        summary = (
            f"Strong row: policy `{row['audit_policy']}`, K `{int(row['K'])}`, support `{row['support_mode']}`, "
            f"budget `{row['audit_budget_fraction_requested']}`, nonempty `{int(row['nonempty_seeds'])}/20`, "
            f"safe `{int(row['safe_seeds'])}/20`, mean FTR `{row['mean_FTR_t1_if_nonempty']}`."
        )
    elif len(mediums):
        row = mediums.sort_values(["audit_budget_fraction_requested", "K", "mean_release_size"], ascending=[True, True, False]).iloc[0]
        status = "completed_active_recertification_go_medium"
        summary = (
            f"Medium row: policy `{row['audit_policy']}`, K `{int(row['K'])}`, support `{row['support_mode']}`, "
            f"budget `{row['audit_budget_fraction_requested']}`, nonempty `{int(row['nonempty_seeds'])}/20`, "
            f"mean FTR `{row['mean_FTR_t1_if_nonempty']}`."
        )
    else:
        summary = "No active t1 recertification policy passes the GO-medium or GO-strong gate on the frozen grid."
    readme = f"""# Phase75 Active Versioned Recertification

Status: `{status}`.

Phase75 tests whether targeted calibration-side current-MP t1 one-sided
support can restore a non-empty self-consistent versioned release after passive
Phase74 recertification refuses.

{summary}

Scope and guardrails:

- t1 public labels are used only to emulate calibration-side one-sided support;
- test-side t1 labels are used only after SCS release to evaluate FTR;
- each policy is frozen before release and never reads held-out t1 labels;
- null-superset denominators and e-values are recomputed after audit;
- random transition controls are included for every K/support/budget row;
- no DFT evidence;
- no prospective materials discovery.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")


def update_artifact_index(status: str) -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase75_active_versioned_recertification",
        "path": "outputs/milestones/ncs_phase75_active_versioned_recertification/",
        "evidence_state": status,
        "manifest": "outputs/milestones/ncs_phase75_active_versioned_recertification/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase75_active_versioned_recertification",
        "notes": "Active current-MP public-label recertification grid; not DFT evidence.",
    }
    df = pd.read_csv(path)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(path, index=False)


def update_claim_table(status: str, comparison: pd.DataFrame) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase75 Active Versioned Recertification"
    trailing = ""
    if marker in text:
        before, after = text.split(marker, 1)
        next_idx = after.find("\n## ")
        trailing = after[next_idx:] if next_idx >= 0 else ""
        text = before.rstrip() + "\n"
    positives = comparison[comparison["go_strong"].astype(bool)]
    mediums = comparison[comparison["go_medium"].astype(bool)]
    if len(positives):
        row = positives.sort_values(["audit_budget_fraction_requested", "K", "mean_release_size"], ascending=[True, True, False]).iloc[0]
        claim = (
            f"Phase75 recovers a GO-strong active current-MP recertification row: "
            f"`{row['audit_policy']}`, K `{int(row['K'])}`, support `{row['support_mode']}`, "
            f"budget `{row['audit_budget_fraction_requested']}`, nonempty `{int(row['nonempty_seeds'])}/20`, "
            f"safe `{int(row['safe_seeds'])}/20`, mean t1 FTR `{row['mean_FTR_t1_if_nonempty']}`. "
            "This is public-label recertification emulation, not DFT evidence."
        )
    elif len(mediums):
        row = mediums.sort_values(["audit_budget_fraction_requested", "K", "mean_release_size"], ascending=[True, True, False]).iloc[0]
        claim = (
            f"Phase75 finds a GO-medium active recertification row (`{row['audit_policy']}`, "
            f"K `{int(row['K'])}`, budget `{row['audit_budget_fraction_requested']}`) but no strict "
            "GO-strong materials constructive positive."
        )
    else:
        claim = (
            "Phase75 closes the active versioned recertification route on the frozen grid: targeted "
            "calibration-side t1 support does not restore a GO-medium/GO-strong current-MP release."
        )
    addition = f"""

## Phase75 Active Versioned Recertification

Status: `{status}`.

{claim}

Allowed scope: versioned public-label recertification emulation. Forbidden
claims: prospective materials discovery, DFT validation, label-free durability
prediction, or current-MP alpha control unless the GO-strong row is explicitly
reported with its public-label scope.
"""
    path.write_text(text.rstrip() + addition + trailing, encoding="utf-8")


def update_evidence_ledger(status: str, comparison: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "PARC-ACTIVE-RECERT-001"]
    artifact = OUT / "table_active_recertification_policy_comparison.csv"
    positive = "yes" if comparison["go_strong"].astype(bool).any() else "partial" if comparison["go_medium"].astype(bool).any() else "no"
    rows.append(
        {
            "claim_id": "PARC-ACTIVE-RECERT-001",
            "claim_text": "Active current-MP t1 recertification tests whether targeted calibration-side one-sided support restores self-consistent release after passive refusal.",
            "evidence_type": "active_versioned_recertification",
            "positive_evidence": positive,
            "scope": status,
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase75-active-versioned-recertification",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_DFT_evidence_prospective_discovery_or_label_free_predictor",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "claim_id",
                "claim_text",
                "evidence_type",
                "positive_evidence",
                "scope",
                "artifact_path",
                "hash",
                "validation_command",
                "status",
                "overclaim_guardrail",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    queue = load_queue()
    seed_rows = run_seed_rows(queue)
    comparison, transition, random_control, release_ftr, self_consistency = summarize(seed_rows)
    status = (
        "completed_active_recertification_go_strong"
        if comparison["go_strong"].astype(bool).any()
        else "completed_active_recertification_go_medium"
        if comparison["go_medium"].astype(bool).any()
        else "completed_active_recertification_no_go"
    )

    comparison.to_csv(OUT / "table_active_recertification_budget_frontier.csv", index=False)
    comparison.to_csv(OUT / "table_active_recertification_policy_comparison.csv", index=False)
    self_consistency.to_csv(OUT / "table_active_recertification_self_consistency.csv", index=False)
    random_control.to_csv(OUT / "table_active_recertification_random_transition_control.csv", index=False)
    release_ftr.to_csv(OUT / "table_active_recertification_release_ftr.csv", index=False)
    pd.concat(
        [
            comparison.assign(panel="budget_frontier"),
            transition.assign(panel="release_transition"),
            random_control.assign(panel="random_transition_control"),
            release_ftr.assign(panel="release_ftr"),
        ],
        ignore_index=True,
        sort=False,
    ).to_csv(OUT / "figure_active_recertification_frontier_inputs.csv", index=False)
    transition.to_csv(OUT / "table_active_recertification_release_transition.csv", index=False)
    write_text(comparison)

    provenance = {
        "status": status,
        "phase": "phase75",
        "source_phase51": rel(PHASE51),
        "source_phase69": rel(PHASE69),
        "source_phase51_t1_table_sha256": sha256_file(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
        "source_phase69_crossfit_risk_sha256": sha256_file(PHASE69 / "table_crossfit_durability_risk_scores.csv"),
        "candidate_universe_rows": int(len(queue)),
        "K_grid": K_GRID,
        "budget_fraction_grid": BUDGET_FRACTIONS,
        "policies": POLICIES,
        "support_modes": SUPPORT_MODES,
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    update_artifact_index(status)
    update_claim_table(status, comparison)
    update_evidence_ledger(status, comparison)
    write_root_manifest()
    print(json.dumps({"status": status, "seed_rows": int(len(seed_rows)), "out_dir": rel(OUT)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
