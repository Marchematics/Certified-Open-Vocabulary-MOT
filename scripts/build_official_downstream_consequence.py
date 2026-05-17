#!/usr/bin/env python3
"""Build official-GT downstream consequence metrics for CTC and SpaceNet 7.

The package is deliberately no-new-label: it uses frozen candidate universes
and official/held-out ground-truth identities already available in the local
experiment workspace. It does not run the official CTC challenge evaluator or
claim a new tracking benchmark score. Instead, it reports official-GT lineage
and map-artifact edit-burden proxies for the release/refusal decisions that
PARC would pass downstream.
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
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_materials_discovery_parc_flagship import gamma_star_from_p, emax_from_p, scs_release_count  # noqa: E402


DEFAULT_SEEDS = list(range(20))
DEFAULT_BUDGETS = [100, 300, 500, 1000, 5000]


def parse_list(value: str, cast):
    return [cast(item) for item in str(value).split(",") if str(item).strip()]


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_blocks(block_ids: list[str | int], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def observed_positive_mask(labels: np.ndarray, scores: np.ndarray, cal_mask: np.ndarray, rho: float) -> np.ndarray:
    observed = np.zeros(len(labels), dtype=bool)
    eligible = np.flatnonzero(labels.astype(bool) & cal_mask)
    if rho <= 0.0 or len(eligible) == 0:
        return observed
    n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
    chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
    observed[chosen] = True
    return observed


def compute_top_evalues(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    label_col: str,
    cal_blocks: set[str],
    test_blocks: set[str],
    rho: float,
    alpha: float,
    max_budget: int,
) -> tuple[pd.DataFrame, dict]:
    block_series = frame[block_col].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    test_mask = block_series.isin(test_blocks).to_numpy()
    scores = frame[score_col].to_numpy(dtype=float)
    labels = frame[label_col].to_numpy(dtype=bool)
    observed = observed_positive_mask(labels, scores, cal_mask, rho)

    cal_null = frame.loc[cal_mask & ~observed, [block_col, score_col]].copy()
    maxima = (
        cal_null.groupby(block_col, sort=False)[score_col].max().astype(float).to_numpy()
        if len(cal_null)
        else np.asarray([], dtype=float)
    )
    n_nonempty = int(len(maxima))
    n_cal = int(len(cal_blocks))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required = 1.0 / alpha if alpha > 0 else math.nan

    # Only the top requested raw queue is needed for downstream consequence
    # metrics, so avoid a full sort of multi-million-row SpaceNet partitions.
    test = frame.loc[test_mask].nlargest(max_budget, score_col).copy()
    if gamma is None or len(test) == 0 or len(maxima) == 0:
        test["_evalue"] = np.zeros(len(test), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        top_scores = test[score_col].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, top_scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        test["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))

    return test, {
        "n_cal_blocks": n_cal,
        "n_test_blocks": int(len(test_blocks)),
        "n_nonempty_null_cal_blocks": n_nonempty,
        "observed_positives": int(observed.sum()),
        "block_coverage": n_nonempty / n_cal if n_cal else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_e": required,
        "max_observed_e": float(test["_evalue"].max()) if len(test) else 0.0,
    }


def prepare_fast_block_index(frame: pd.DataFrame, *, score_col: str, block_col: str) -> dict:
    block_values = frame[block_col].astype(str).to_numpy()
    unique_blocks, block_codes = np.unique(block_values, return_inverse=True)
    scores = frame[score_col].to_numpy(dtype=float)
    by_block: dict[int, np.ndarray] = {}
    for code in range(len(unique_blocks)):
        idx = np.flatnonzero(block_codes == code)
        by_block[code] = idx[np.argsort(scores[idx])[::-1]]
    return {
        "unique_blocks": unique_blocks,
        "block_codes": block_codes,
        "block_to_code": {str(block): int(code) for code, block in enumerate(unique_blocks)},
        "scores": scores,
        "global_order": np.argsort(scores)[::-1],
        "by_block": by_block,
    }


def compute_top_evalues_indexed(
    frame: pd.DataFrame,
    *,
    index: dict,
    label_col: str,
    cal_blocks: set[str],
    test_blocks: set[str],
    rho: float,
    alpha: float,
    max_budget: int,
) -> tuple[pd.DataFrame, dict]:
    scores: np.ndarray = index["scores"]
    block_codes: np.ndarray = index["block_codes"]
    block_to_code: dict[str, int] = index["block_to_code"]
    labels = frame[label_col].to_numpy(dtype=bool)
    cal_codes = [block_to_code[str(block)] for block in cal_blocks if str(block) in block_to_code]
    test_codes = [block_to_code[str(block)] for block in test_blocks if str(block) in block_to_code]
    cal_code_mask = np.zeros(len(index["unique_blocks"]), dtype=bool)
    test_code_mask = np.zeros(len(index["unique_blocks"]), dtype=bool)
    cal_code_mask[cal_codes] = True
    test_code_mask[test_codes] = True
    cal_row_mask = cal_code_mask[block_codes]

    observed = np.zeros(len(frame), dtype=bool)
    eligible = np.flatnonzero(labels & cal_row_mask)
    if len(eligible) and rho > 0:
        n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
        if n_observed >= len(eligible):
            chosen = eligible
        else:
            top_unsorted = np.argpartition(scores[eligible], -n_observed)[-n_observed:]
            chosen = eligible[top_unsorted]
        observed[chosen] = True

    maxima: list[float] = []
    for code in cal_codes:
        ordered = index["by_block"][code]
        keep = ordered[~observed[ordered]]
        if len(keep):
            maxima.append(float(scores[keep[0]]))
    maxima_arr = np.asarray(maxima, dtype=float)
    n_nonempty = int(len(maxima_arr))
    n_cal = int(len(cal_codes))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required = 1.0 / alpha if alpha > 0 else math.nan

    global_order: np.ndarray = index["global_order"]
    top_mask = test_code_mask[block_codes[global_order]]
    top_indices = global_order[top_mask][:max_budget]
    test = frame.iloc[top_indices].copy()
    if gamma is None or len(test) == 0 or len(maxima_arr) == 0:
        test["_evalue"] = np.zeros(len(test), dtype=float)
    else:
        maxima_sorted = np.sort(maxima_arr)
        top_scores = scores[top_indices]
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, top_scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        test["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))

    return test, {
        "n_cal_blocks": n_cal,
        "n_test_blocks": int(len(test_codes)),
        "n_nonempty_null_cal_blocks": n_nonempty,
        "observed_positives": int(observed.sum()),
        "block_coverage": n_nonempty / n_cal if n_cal else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_e": required,
        "max_observed_e": float(test["_evalue"].max()) if len(test) else 0.0,
    }


def _uf_find(parent: dict[str, str], node: str) -> str:
    parent.setdefault(node, node)
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node


def _uf_union(parent: dict[str, str], a: str, b: str) -> None:
    ra = _uf_find(parent, a)
    rb = _uf_find(parent, b)
    if ra != rb:
        parent[rb] = ra


def ctc_lineage_metrics(selected: pd.DataFrame, label_col: str) -> dict:
    if len(selected) == 0:
        return {
            "selected_links": 0,
            "false_lineage_edges": 0,
            "false_edge_fraction": 0.0,
            "successor_conflicts": 0,
            "predecessor_conflicts": 0,
            "corrupted_lineage_components": 0,
            "aogm_edge_edit_burden_proxy": 0,
            "tra_edge_quality_proxy": 1.0,
        }
    true = selected[label_col].astype(bool)
    false_links = int((~true).sum())

    source_key = (
        selected["ctc_dataset"].astype(str)
        + ":"
        + selected["sequence_id"].astype(str)
        + ":"
        + selected["frame_start"].astype(str)
        + ":"
        + selected["source_gt_label"].astype(str)
    )
    target_key = (
        selected["ctc_dataset"].astype(str)
        + ":"
        + selected["sequence_id"].astype(str)
        + ":"
        + selected["frame_end"].astype(str)
        + ":"
        + selected["target_gt_label"].astype(str)
    )
    selected = selected.copy()
    selected["_source_key"] = source_key
    selected["_target_key"] = target_key
    selected["_is_true"] = true.to_numpy(dtype=bool)

    successor_conflicts = int(
        selected.groupby("_source_key")["_target_key"].nunique().sub(1).clip(lower=0).sum()
    )
    predecessor_conflicts = int(
        selected.groupby("_target_key")["_source_key"].nunique().sub(1).clip(lower=0).sum()
    )

    parent: dict[str, str] = {}
    false_roots: set[str] = set()
    for src, dst in selected[["_source_key", "_target_key"]].itertuples(index=False, name=None):
        _uf_union(parent, src, dst)
    for src, is_true in selected[["_source_key", "_is_true"]].itertuples(index=False, name=None):
        if not bool(is_true):
            false_roots.add(_uf_find(parent, src))
    corrupted_components = len(false_roots)
    burden = false_links + successor_conflicts + predecessor_conflicts + corrupted_components
    denom = burden + int(len(selected))
    return {
        "selected_links": int(len(selected)),
        "false_lineage_edges": false_links,
        "false_edge_fraction": float((~true).mean()),
        "successor_conflicts": successor_conflicts,
        "predecessor_conflicts": predecessor_conflicts,
        "corrupted_lineage_components": int(corrupted_components),
        "aogm_edge_edit_burden_proxy": int(burden),
        "tra_edge_quality_proxy": float(1.0 - burden / denom) if denom else 1.0,
    }


def spacenet_map_metrics(selected: pd.DataFrame, label_col: str) -> dict:
    if len(selected) == 0:
        return {
            "selected_links": 0,
            "false_persistence_links": 0,
            "false_link_fraction": 0.0,
            "source_split_conflicts": 0,
            "target_merge_conflicts": 0,
            "false_persistence_chains": 0,
            "merged_building_components": 0,
            "map_edit_burden_proxy": 0,
            "persistence_map_quality_proxy": 1.0,
        }
    true = selected[label_col].astype(bool)
    false_links = int((~true).sum())
    selected = selected.copy()
    selected["_source_node"] = (
        selected["aoi"].astype(str)
        + ":"
        + selected["frame_start"].astype(str)
        + ":"
        + selected["source_building_id"].astype(str)
    )
    selected["_target_node"] = (
        selected["aoi"].astype(str)
        + ":"
        + selected["frame_end"].astype(str)
        + ":"
        + selected["target_building_id"].astype(str)
    )
    selected["_true"] = true.to_numpy(dtype=bool)
    source_splits = int(selected.groupby("_source_node")["_target_node"].nunique().sub(1).clip(lower=0).sum())
    target_merges = int(selected.groupby("_target_node")["_source_node"].nunique().sub(1).clip(lower=0).sum())

    parent: dict[str, str] = {}
    for src, dst in selected[["_source_node", "_target_node"]].itertuples(index=False, name=None):
        _uf_union(parent, src, dst)
    false_roots: set[str] = set()
    for src, is_true in selected[["_source_node", "_true"]].itertuples(index=False, name=None):
        if not bool(is_true):
            false_roots.add(_uf_find(parent, src))
    false_chains = len(false_roots)
    burden = false_links + source_splits + target_merges + false_chains
    denom = burden + int(len(selected))
    return {
        "selected_links": int(len(selected)),
        "false_persistence_links": false_links,
        "false_link_fraction": float((~true).mean()),
        "source_split_conflicts": source_splits,
        "target_merge_conflicts": target_merges,
        "false_persistence_chains": int(false_chains),
        "merged_building_components": int(false_chains),
        "map_edit_burden_proxy": int(burden),
        "persistence_map_quality_proxy": float(1.0 - burden / denom) if denom else 1.0,
    }


def metric_delta(raw: dict, parc: dict, prefix: str) -> dict:
    return {
        f"prevented_{prefix}_false_links": raw[f"false_{prefix}_links"] - parc[f"false_{prefix}_links"],
    }


def select_parc(pool: pd.DataFrame, budget: int, alpha: float) -> tuple[pd.DataFrame, int, float]:
    pool = pool.head(budget).copy()
    evalues = pool["_evalue"].to_numpy(dtype=float)
    released, _tau, _margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
    if released:
        selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy()
    else:
        selected = pool.iloc[[]].copy()
    return selected, int(released), float(best_ratio)


def run_ctc(args: argparse.Namespace, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = [
        {
            "proposal_source": "ctc_learned_hybrid",
            "path": Path(args.ctc_learned_universe),
            "source_scope": "sequence-disjoint learned appearance linker",
        },
        {
            "proposal_source": "ctc_noisy_geometric_linker",
            "path": Path(args.ctc_geometric_universe),
            "source_scope": "GT/TRA node universe with noisy geometric link scores",
        },
        {
            "proposal_source": "ctc_random_score_negative_control",
            "path": Path(args.ctc_random_universe),
            "source_scope": "same held-out CTC universe with randomized ranking",
        },
    ]
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)
    alpha = float(args.ctc_alpha)
    max_budget = max(budgets)
    rows: list[dict] = []
    input_hashes: dict[str, str] = {}
    for spec in specs:
        path = spec["path"]
        if not path.exists():
            continue
        input_hashes[spec["proposal_source"]] = sha256_file(path)
        usecols = [
            "score",
            "video_id",
            "is_unmatched",
            "ctc_dataset",
            "sequence_id",
            "frame_start",
            "frame_end",
            "source_gt_label",
            "target_gt_label",
        ]
        frame = pd.read_csv(path, usecols=usecols, low_memory=False)
        frame["_true_link"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
        unique_blocks = sorted(frame["video_id"].astype(str).unique().tolist())
        for seed in seeds:
            cal_blocks, test_blocks = split_blocks(unique_blocks, seed)
            test, diag = compute_top_evalues(
                frame,
                score_col="score",
                block_col="video_id",
                label_col="_true_link",
                cal_blocks=cal_blocks,
                test_blocks=test_blocks,
                rho=float(args.rho),
                alpha=alpha,
                max_budget=max_budget,
            )
            for budget in budgets:
                raw_pool = test.head(budget).copy()
                selected, released, best_ratio = select_parc(raw_pool, budget, alpha)
                raw = ctc_lineage_metrics(raw_pool, "_true_link")
                parc = ctc_lineage_metrics(selected, "_true_link")
                oracle = ctc_lineage_metrics(raw_pool[raw_pool["_true_link"].astype(bool)].head(released), "_true_link")
                rows.append(
                    {
                        "domain": "biomedical_cell_tracking",
                        "dataset": "Cell Tracking Challenge",
                        "proposal_source": spec["proposal_source"],
                        "source_scope": spec["source_scope"],
                        "metric_family": "official_GT_lineage_edge_metrics",
                        "alpha": alpha,
                        "K": budget,
                        "seed": seed,
                        "PARC_released": released,
                        "non_empty": int(released > 0),
                        "raw_selected_links": raw["selected_links"],
                        "raw_false_lineage_edges": raw["false_lineage_edges"],
                        "raw_false_edge_fraction": raw["false_edge_fraction"],
                        "raw_successor_conflicts": raw["successor_conflicts"],
                        "raw_predecessor_conflicts": raw["predecessor_conflicts"],
                        "raw_corrupted_lineage_components": raw["corrupted_lineage_components"],
                        "raw_aogm_edge_edit_burden_proxy": raw["aogm_edge_edit_burden_proxy"],
                        "raw_tra_edge_quality_proxy": raw["tra_edge_quality_proxy"],
                        "PARC_false_lineage_edges": parc["false_lineage_edges"],
                        "PARC_false_edge_fraction": parc["false_edge_fraction"],
                        "PARC_corrupted_lineage_components": parc["corrupted_lineage_components"],
                        "PARC_aogm_edge_edit_burden_proxy": parc["aogm_edge_edit_burden_proxy"],
                        "PARC_tra_edge_quality_proxy": parc["tra_edge_quality_proxy"],
                        "oracle_aogm_edge_edit_burden_proxy": oracle["aogm_edge_edit_burden_proxy"],
                        "prevented_false_lineage_edges": raw["false_lineage_edges"] - parc["false_lineage_edges"],
                        "prevented_corrupted_lineage_components": raw["corrupted_lineage_components"]
                        - parc["corrupted_lineage_components"],
                        "prevented_aogm_edge_edit_burden_proxy": raw["aogm_edge_edit_burden_proxy"]
                        - parc["aogm_edge_edit_burden_proxy"],
                        "best_mass_ratio": best_ratio,
                        "max_observed_e": diag["max_observed_e"],
                        "required_e": diag["required_e"],
                        "block_coverage": diag["block_coverage"],
                        "observed_positives": diag["observed_positives"],
                        "evidence_status": "completed_official_GT_downstream_consequence",
                    }
                )
    seed_rows = pd.DataFrame(rows)
    summary = summarize(seed_rows, ["domain", "dataset", "proposal_source", "source_scope", "metric_family", "alpha", "K"])
    summary["interpretation"] = np.where(
        summary["prevented_false_lineage_edges_mean"].astype(float) > 0,
        "PARC_prevents_false_lineage_edges_from_entering_graph",
        "raw_queue_clean_or_no_lineage_damage_at_this_budget",
    )
    summary["claim_scope"] = (
        "official CTC GT lineage-edge consequence; TRA/AOGM values are edge-edit proxies, not official challenge scores"
    )
    (out_dir / "ctc_input_hashes.json").write_text(json.dumps(input_hashes, indent=2, sort_keys=True), encoding="utf-8")
    return seed_rows, summary


def run_spacenet(args: argparse.Namespace, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = Path(args.spacenet_geometry_universe)
    cols = [
        "score",
        "deterministic_noise",
        "video_id",
        "aoi",
        "source_building_id",
        "target_building_id",
        "frame_start",
        "frame_end",
        "is_unmatched",
    ]
    frame = pd.read_csv(path, usecols=cols, low_memory=False)
    frame["_true_link"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
    specs = [
        ("spacenet_geometry_linker", "score", "structured geometry building-link source"),
        ("spacenet_identity_preserving_random_score_control", "deterministic_noise", "same candidate universe with deterministic randomized ranking"),
    ]
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)
    alpha = float(args.spacenet_alpha)
    max_budget = max(budgets)
    rows: list[dict] = []
    unique_blocks = sorted(frame["video_id"].astype(str).unique().tolist())
    for source, score_col, scope in specs:
        work = frame
        fast_index = prepare_fast_block_index(work, score_col=score_col, block_col="video_id")
        for seed in seeds:
            cal_blocks, test_blocks = split_blocks(unique_blocks, seed)
            test, diag = compute_top_evalues_indexed(
                work,
                index=fast_index,
                label_col="_true_link",
                cal_blocks=cal_blocks,
                test_blocks=test_blocks,
                rho=float(args.rho),
                alpha=alpha,
                max_budget=max_budget,
            )
            for budget in budgets:
                raw_pool = test.head(budget).copy()
                selected, released, best_ratio = select_parc(raw_pool, budget, alpha)
                raw = spacenet_map_metrics(raw_pool, "_true_link")
                parc = spacenet_map_metrics(selected, "_true_link")
                rows.append(
                    {
                        "domain": "earth_observation",
                        "dataset": "SpaceNet 7 official building identities",
                        "proposal_source": source,
                        "source_scope": scope,
                        "metric_family": "official_GT_building_persistence_map_metrics",
                        "alpha": alpha,
                        "K": budget,
                        "seed": seed,
                        "PARC_released": released,
                        "non_empty": int(released > 0),
                        "raw_selected_links": raw["selected_links"],
                        "raw_false_persistence_links": raw["false_persistence_links"],
                        "raw_false_link_fraction": raw["false_link_fraction"],
                        "raw_source_split_conflicts": raw["source_split_conflicts"],
                        "raw_target_merge_conflicts": raw["target_merge_conflicts"],
                        "raw_false_persistence_chains": raw["false_persistence_chains"],
                        "raw_map_edit_burden_proxy": raw["map_edit_burden_proxy"],
                        "raw_persistence_map_quality_proxy": raw["persistence_map_quality_proxy"],
                        "PARC_false_persistence_links": parc["false_persistence_links"],
                        "PARC_false_link_fraction": parc["false_link_fraction"],
                        "PARC_false_persistence_chains": parc["false_persistence_chains"],
                        "PARC_map_edit_burden_proxy": parc["map_edit_burden_proxy"],
                        "PARC_persistence_map_quality_proxy": parc["persistence_map_quality_proxy"],
                        "prevented_false_persistence_links": raw["false_persistence_links"]
                        - parc["false_persistence_links"],
                        "prevented_false_persistence_chains": raw["false_persistence_chains"]
                        - parc["false_persistence_chains"],
                        "prevented_map_edit_burden_proxy": raw["map_edit_burden_proxy"]
                        - parc["map_edit_burden_proxy"],
                        "best_mass_ratio": best_ratio,
                        "max_observed_e": diag["max_observed_e"],
                        "required_e": diag["required_e"],
                        "block_coverage": diag["block_coverage"],
                        "observed_positives": diag["observed_positives"],
                        "evidence_status": "completed_official_GT_downstream_consequence",
                    }
                )
    seed_rows = pd.DataFrame(rows)
    summary = summarize(seed_rows, ["domain", "dataset", "proposal_source", "source_scope", "metric_family", "alpha", "K"])
    summary["interpretation"] = np.where(
        summary["prevented_false_persistence_links_mean"].astype(float) > 0,
        "PARC_prevents_false_persistence_links_from_entering_map",
        "raw_queue_clean_or_no_map_damage_at_this_budget",
    )
    summary["claim_scope"] = "official SpaceNet building identities; map metrics are link-derived persistence artifacts"
    (out_dir / "spacenet_input_hashes.json").write_text(
        json.dumps({"spacenet_geometry_universe_sha256": sha256_file(path)}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return seed_rows, summary


def summarize(seed_rows: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    skip = set(group_cols + ["seed", "evidence_status"])
    numeric_cols = [
        col
        for col in seed_rows.columns
        if col not in skip and pd.api.types.is_numeric_dtype(seed_rows[col])
    ]
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_cols, key))
        row["seeds"] = int(group["seed"].nunique())
        row["non_empty_seeds"] = int(group["non_empty"].astype(int).sum())
        for col in numeric_cols:
            if col == "non_empty":
                continue
            row[col + "_mean"] = float(group[col].astype(float).mean())
            row[col + "_max"] = float(group[col].astype(float).max())
        row["evidence_status"] = "completed_official_GT_downstream_consequence"
        rows.append(row)
    return pd.DataFrame(rows)


def build_headline(ctc: pd.DataFrame, spacenet: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ctc_noisy = ctc[
        (ctc["proposal_source"] == "ctc_noisy_geometric_linker")
        & (ctc["K"] == 5000)
    ].iloc[0]
    ctc_random = ctc[
        (ctc["proposal_source"] == "ctc_random_score_negative_control")
        & (ctc["K"] == 5000)
    ].iloc[0]
    sn_random = spacenet[
        (spacenet["proposal_source"] == "spacenet_identity_preserving_random_score_control")
        & (spacenet["K"] == 5000)
    ].iloc[0]
    sn_geometry = spacenet[
        (spacenet["proposal_source"] == "spacenet_geometry_linker")
        & (spacenet["K"] == 5000)
    ].iloc[0]
    rows.extend(
        [
            {
                "domain": "CTC",
                "downstream_artifact": "cell lineage graph",
                "source": "noisy geometric K=5000",
                "raw_consequence": f"{ctc_noisy['raw_false_lineage_edges_mean']:.1f} false lineage edges per seed",
                "PARC_decision": "certified refusal",
                "consequence_prevented": f"{ctc_noisy['prevented_aogm_edge_edit_burden_proxy_mean']:.1f} edge-edit burden proxy units per seed",
                "headline_value": float(ctc_noisy["prevented_false_lineage_edges_mean"]),
                "evidence_status": "completed_official_GT_downstream_consequence",
            },
            {
                "domain": "CTC",
                "downstream_artifact": "cell lineage graph",
                "source": "random-score K=5000",
                "raw_consequence": f"{ctc_random['raw_false_lineage_edges_mean']:.1f} false lineage edges per seed",
                "PARC_decision": "certified refusal",
                "consequence_prevented": f"{ctc_random['prevented_aogm_edge_edit_burden_proxy_mean']:.1f} edge-edit burden proxy units per seed",
                "headline_value": float(ctc_random["prevented_false_lineage_edges_mean"]),
                "evidence_status": "completed_official_GT_downstream_consequence",
            },
            {
                "domain": "SpaceNet 7",
                "downstream_artifact": "building-persistence map",
                "source": "geometry K=5000",
                "raw_consequence": f"{sn_geometry['raw_false_persistence_links_mean']:.1f} false persistence links per seed",
                "PARC_decision": "certified low-power/refusal frontier",
                "consequence_prevented": f"{sn_geometry['prevented_map_edit_burden_proxy_mean']:.1f} map-edit burden proxy units per seed",
                "headline_value": float(sn_geometry["prevented_false_persistence_links_mean"]),
                "evidence_status": "completed_official_GT_downstream_consequence",
            },
            {
                "domain": "SpaceNet 7",
                "downstream_artifact": "building-persistence map",
                "source": "identity-preserving random-score K=5000",
                "raw_consequence": f"{sn_random['raw_false_persistence_links_mean']:.1f} false persistence links per seed",
                "PARC_decision": "certified refusal",
                "consequence_prevented": f"{sn_random['prevented_map_edit_burden_proxy_mean']:.1f} map-edit burden proxy units per seed",
                "headline_value": float(sn_random["prevented_false_persistence_links_mean"]),
                "evidence_status": "completed_official_GT_downstream_consequence",
            },
        ]
    )
    return pd.DataFrame(rows)


def build_figure_source(ctc: pd.DataFrame, spacenet: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    ctc_keep = ctc[
        (ctc["proposal_source"].isin(["ctc_noisy_geometric_linker", "ctc_random_score_negative_control"]))
        & (ctc["K"].isin([300, 5000]))
    ]
    for row in ctc_keep.itertuples(index=False):
        label = str(row.proposal_source).replace("ctc_", "").replace("_", " ") + f" K={int(row.K)}"
        rows.extend(
            [
                {
                    "panel": "a_ctc_lineage",
                    "group": label,
                    "metric": "raw_false_lineage_edges",
                    "value": float(row.raw_false_lineage_edges_mean),
                    "unit": "false lineage edges per seed",
                    "display_label": "Raw false lineage edges",
                },
                {
                    "panel": "a_ctc_lineage",
                    "group": label,
                    "metric": "prevented_false_lineage_edges",
                    "value": float(row.prevented_false_lineage_edges_mean),
                    "unit": "false lineage edges per seed",
                    "display_label": "Prevented false lineage edges",
                },
                {
                    "panel": "b_ctc_edit_burden",
                    "group": label,
                    "metric": "prevented_aogm_edge_edit_burden_proxy",
                    "value": float(row.prevented_aogm_edge_edit_burden_proxy_mean),
                    "unit": "edge-edit burden proxy per seed",
                    "display_label": "Prevented edge-edit burden proxy",
                },
            ]
        )
    sn_keep = spacenet[
        (spacenet["proposal_source"].isin(["spacenet_geometry_linker", "spacenet_identity_preserving_random_score_control"]))
        & (spacenet["K"].isin([300, 5000]))
    ]
    for row in sn_keep.itertuples(index=False):
        label = str(row.proposal_source).replace("spacenet_", "").replace("_", " ") + f" K={int(row.K)}"
        rows.extend(
            [
                {
                    "panel": "c_spacenet_map",
                    "group": label,
                    "metric": "raw_false_persistence_links",
                    "value": float(row.raw_false_persistence_links_mean),
                    "unit": "false persistence links per seed",
                    "display_label": "Raw false persistence links",
                },
                {
                    "panel": "c_spacenet_map",
                    "group": label,
                    "metric": "prevented_false_persistence_links",
                    "value": float(row.prevented_false_persistence_links_mean),
                    "unit": "false persistence links per seed",
                    "display_label": "Prevented false persistence links",
                },
                {
                    "panel": "d_spacenet_edit_burden",
                    "group": label,
                    "metric": "prevented_map_edit_burden_proxy",
                    "value": float(row.prevented_map_edit_burden_proxy_mean),
                    "unit": "map-edit burden proxy per seed",
                    "display_label": "Prevented map-edit burden proxy",
                },
            ]
        )
    return pd.DataFrame(rows)


def plot_figure(source: pd.DataFrame, out_pdf: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 6.6))
    panels = [
        ("a_ctc_lineage", "CTC false lineage edges"),
        ("b_ctc_edit_burden", "CTC edge-edit burden proxy"),
        ("c_spacenet_map", "SpaceNet false persistence links"),
        ("d_spacenet_edit_burden", "SpaceNet map-edit burden proxy"),
    ]
    colors = {
        "raw_false_lineage_edges": "#d95f02",
        "prevented_false_lineage_edges": "#1b9e77",
        "prevented_aogm_edge_edit_burden_proxy": "#7570b3",
        "raw_false_persistence_links": "#d95f02",
        "prevented_false_persistence_links": "#1b9e77",
        "prevented_map_edit_burden_proxy": "#7570b3",
    }
    for ax, (panel, title) in zip(axes.ravel(), panels):
        data = source[source["panel"] == panel].copy()
        groups = list(dict.fromkeys(data["group"].tolist()))
        metrics = list(dict.fromkeys(data["metric"].tolist()))
        x = np.arange(len(groups))
        width = 0.75 / max(1, len(metrics))
        for idx, metric in enumerate(metrics):
            vals = [
                float(data[(data["group"] == group) & (data["metric"] == metric)]["value"].iloc[0])
                if not data[(data["group"] == group) & (data["metric"] == metric)].empty
                else 0.0
                for group in groups
            ]
            ax.bar(x + (idx - (len(metrics) - 1) / 2) * width, vals, width, label=metric.replace("_", " "), color=colors.get(metric))
        ax.set_title(title)
        ax.set_xticks(x, groups, rotation=25, ha="right", fontsize=7)
        ax.set_ylabel(data["unit"].iloc[0] if len(data) else "value")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def write_provenance(path: Path, role: str, inputs: dict[str, str], command: str, started: float) -> None:
    payload = {
        "artifact": path.name,
        "role": role,
        "input_sha256": inputs,
        "command": command,
        "runtime_sec": round(time.time() - started, 3),
        "output_sha256": sha256_file(path),
    }
    path.with_suffix(path.suffix + ".provenance.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_closeout(out_dir: Path, headline: pd.DataFrame, ctc: pd.DataFrame, spacenet: pd.DataFrame) -> str:
    ctc_noisy = ctc[(ctc["proposal_source"] == "ctc_noisy_geometric_linker") & (ctc["K"] == 5000)].iloc[0]
    sn_random = spacenet[
        (spacenet["proposal_source"] == "spacenet_identity_preserving_random_score_control") & (spacenet["K"] == 5000)
    ].iloc[0]
    return f"""# Official Downstream Consequence Closeout

Evidence status: completed official-GT downstream consequence diagnostics.

Scope:
- No new human labels are introduced.
- CTC uses official/held-out lineage identities to compute link-level lineage consequences.
- SpaceNet 7 uses official building identities to compute map-level persistence consequences.
- CTC TRA/AOGM values are edge-edit burden proxies, not official challenge leaderboard scores.
- SpaceNet map metrics are link-derived persistence artifacts, not a new geospatial challenge score.

Headline results:
- CTC noisy high-volume K=5000 raw queue inserts {ctc_noisy['raw_false_lineage_edges_mean']:.1f} false lineage edges per seed and {ctc_noisy['raw_aogm_edge_edit_burden_proxy_mean']:.1f} edge-edit burden proxy units; PARC refuses and prevents {ctc_noisy['prevented_false_lineage_edges_mean']:.1f} false lineage edges per seed.
- SpaceNet identity-preserving random-score K=5000 raw queue inserts {sn_random['raw_false_persistence_links_mean']:.1f} false persistence links per seed and {sn_random['raw_map_edit_burden_proxy_mean']:.1f} map-edit burden proxy units; PARC prevents {sn_random['prevented_false_persistence_links_mean']:.1f} false persistence links per seed.

Paper-facing interpretation:
PARC changes the downstream scientific artifact: a cell-lineage graph or a building-persistence map. These diagnostics do not claim improved upstream prediction. They quantify which raw candidate edges are kept out of downstream artifacts when release evidence is insufficient.

Primary artifacts:
- `table_ctc_official_lineage_metric_summary.csv`
- `table_spacenet_map_metric_summary.csv`
- `table_official_downstream_consequence_summary.csv`
- `figure_official_downstream_consequence.csv`
- `figure_official_downstream_consequence.pdf`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="outputs/milestones/official_downstream_consequence")
    parser.add_argument("--rho", default="0.10")
    parser.add_argument("--ctc-alpha", default="0.10")
    parser.add_argument("--spacenet-alpha", default="0.20")
    parser.add_argument("--budgets", default="100,300,500,1000,5000")
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument(
        "--ctc-learned-universe",
        default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1/candidate_universe.csv",
    )
    parser.add_argument(
        "--ctc-geometric-universe",
        default="/home/waas/paper_experiments/outputs/ctc_link_certification/universe_gt_tra_noisy_w90_win5/candidate_universe.csv",
    )
    parser.add_argument(
        "--ctc-random-universe",
        default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1_random_control/candidate_universe.csv",
    )
    parser.add_argument(
        "--spacenet-geometry-universe",
        default="/home/waas/paper_experiments/outputs/spacenet7_building_links/universe_geometry_w35_aoi18/candidate_universe.csv",
    )
    args = parser.parse_args()
    started = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ctc_seed, ctc_summary = run_ctc(args, out_dir)
    spacenet_seed, spacenet_summary = run_spacenet(args, out_dir)
    headline = build_headline(ctc_summary, spacenet_summary)
    figure_source = build_figure_source(ctc_summary, spacenet_summary)

    artifacts = {
        "table_ctc_official_lineage_metric_seed_rows.csv": (ctc_seed, "ctc_seed_rows"),
        "table_ctc_official_lineage_metric_summary.csv": (ctc_summary, "ctc_summary"),
        "table_spacenet_map_metric_seed_rows.csv": (spacenet_seed, "spacenet_seed_rows"),
        "table_spacenet_map_metric_summary.csv": (spacenet_summary, "spacenet_summary"),
        "table_official_downstream_consequence_summary.csv": (headline, "headline_summary"),
        "figure_official_downstream_consequence.csv": (figure_source, "figure_source"),
    }
    for name, (frame, _role) in artifacts.items():
        frame.to_csv(out_dir / name, index=False)
    plot_figure(figure_source, out_dir / "figure_official_downstream_consequence.pdf")

    protocol = {
        "evidence_status": "completed_official_GT_downstream_consequence",
        "scope": "no new human labels; official/held-out GT consequence metrics; not official CTC leaderboard scoring",
        "rho": float(args.rho),
        "ctc_alpha": float(args.ctc_alpha),
        "spacenet_alpha": float(args.spacenet_alpha),
        "budgets": parse_list(args.budgets, int),
        "seeds": parse_list(args.seeds, int),
        "ctc_metric_note": "TRA/AOGM-style values are edge-edit burden proxies computed from official lineage identities",
        "spacenet_metric_note": "map metrics are same-building persistence artifact proxies computed from official building identities",
    }
    protocol_path = out_dir / "OFFICIAL_DOWNSTREAM_CONSEQUENCE_PROTOCOL.json"
    protocol_path.write_text(json.dumps(protocol, indent=2, sort_keys=True), encoding="utf-8")
    closeout_path = out_dir / "OFFICIAL_DOWNSTREAM_CONSEQUENCE_CLOSEOUT.md"
    closeout_path.write_text(build_closeout(out_dir, headline, ctc_summary, spacenet_summary), encoding="utf-8")

    inputs = {
        "ctc_learned_universe": sha256_file(Path(args.ctc_learned_universe)),
        "ctc_geometric_universe": sha256_file(Path(args.ctc_geometric_universe)),
        "ctc_random_universe": sha256_file(Path(args.ctc_random_universe)),
        "spacenet_geometry_universe": sha256_file(Path(args.spacenet_geometry_universe)),
    }
    command = "python scripts/build_official_downstream_consequence.py"
    for name, (_frame, role) in artifacts.items():
        write_provenance(out_dir / name, role, inputs, command, started)
    write_provenance(out_dir / "figure_official_downstream_consequence.pdf", "figure", inputs, command, started)
    write_provenance(protocol_path, "protocol", inputs, command, started)
    write_provenance(closeout_path, "closeout", inputs, command, started)
    write_manifest(out_dir)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
