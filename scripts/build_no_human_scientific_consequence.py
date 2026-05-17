#!/usr/bin/env python3
"""Build no-human scientific consequence diagnostics.

This package uses only public prediction CSVs, official/held-out labels, and
candidate-level universes already present in the local experiment workspace. It
does not add human labels and does not promote protocol-only rows.
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

from run_materials_discovery_parc_flagship import (  # noqa: E402
    add_blocks,
    gamma_star_from_p,
    emax_from_p,
    scs_release_count,
)


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
    return [cast(item) for item in value.split(",") if str(item).strip()]


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def split_blocks(block_ids: list[str | int], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def observed_positive_mask(labels: np.ndarray, scores: np.ndarray, rho: float) -> np.ndarray:
    observed = np.zeros(len(labels), dtype=bool)
    positives = np.flatnonzero(labels.astype(bool))
    if rho <= 0.0 or len(positives) == 0:
        return observed
    n_observed = int(round(len(positives) * min(rho, 1.0)))
    if n_observed <= 0:
        return observed
    chosen = positives[np.argsort(scores[positives])[::-1]][:n_observed]
    observed[chosen] = True
    return observed


def compute_evalues(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    observed_positive: np.ndarray,
    cal_blocks: set[str],
    test_blocks: set[str],
    alpha: float,
) -> tuple[pd.DataFrame, dict]:
    block_series = frame[block_col].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    test_mask = block_series.isin(test_blocks).to_numpy()
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
    test = frame.loc[test_mask].sort_values(score_col, ascending=False).copy()
    if gamma is None or len(test) == 0 or len(maxima) == 0:
        test["_evalue"] = np.zeros(len(test), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = test[score_col].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        test["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return test, {
        "n_cal_blocks": n_total,
        "n_nonempty_null_cal_blocks": n_nonempty,
        "block_coverage": n_nonempty / n_total if n_total else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_e": required,
    }


def summarize_groups(rows: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    out: list[dict] = []
    for key, group in rows.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["released"].astype(int) > 0).sum()),
                "mean_release": float(group["released"].astype(float).mean()),
                "min_release": int(group["released"].astype(int).min()),
                "max_release": int(group["released"].astype(int).max()),
                "PARC_FTR_mean": float(group["PARC_FTR"].astype(float).mean()),
                "PARC_FTR_max": float(group["PARC_FTR"].astype(float).max()),
                "raw_topK_FTR_mean": float(group["raw_topK_FTR"].astype(float).mean()),
                "raw_topR_FTR_mean": float(group["raw_topR_FTR"].astype(float).mean()),
                "raw_only_tail_FTR_mean": float(group["raw_only_tail_FTR"].astype(float).mean()),
                "raw_unstable_count_mean": float(group["raw_unstable_count"].astype(float).mean()),
                "PARC_unstable_count_mean": float(group["PARC_unstable_count"].astype(float).mean()),
                "prevented_unstable_followups_mean": float(
                    group["prevented_unstable_followups"].astype(float).mean()
                ),
                "DFT_efficiency_mean": float(group["DFT_efficiency"].astype(float).mean()),
                "raw_DFT_efficiency_mean": float(group["raw_DFT_efficiency"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_e"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
            }
        )
        out.append(row)
    return pd.DataFrame(out)


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
    source_specs: list[dict] = []
    input_hashes = {"wbm_summary_sha256": sha256_file(Path(args.wbm_summary))}
    candidates = [
        {
            "proposal_source": "cgcnn_ensemble_learned_materials_model",
            "path": Path(args.cgcnn_predictions),
            "column": args.cgcnn_pred_col,
            "model_family": "CGCNN 10-member ensemble",
            "availability_status": "available_completed",
        },
        {
            "proposal_source": "alignn_ff_modern_learned_materials_model",
            "path": Path(args.alignn_predictions),
            "column": args.alignn_pred_col,
            "model_family": "ALIGNN-FF",
            "availability_status": "available_completed",
        },
        {
            "proposal_source": "megnet_weak_learned_materials_model",
            "path": Path(args.megnet_predictions),
            "column": args.megnet_pred_col,
            "model_family": "MEGNet",
            "availability_status": "available_completed",
        },
    ]
    missing_models = ["CHGNet", "M3GNet", "MACE", "ORB", "SevenNet", "EquiformerV2", "MatterSim"]
    for spec in candidates:
        if not spec["path"].exists():
            source_specs.append({**spec, "availability_status": "missing_public_prediction_file"})
            continue
        pred = pd.read_csv(spec["path"], usecols=["material_id", spec["column"]])
        frame = frame.merge(pred, on="material_id", how="inner")
        input_hashes[f"{spec['proposal_source']}_sha256"] = sha256_file(spec["path"])
        source_specs.append(spec)
    for model in missing_models:
        source_specs.append(
            {
                "proposal_source": model.lower() + "_not_available_locally",
                "path": "",
                "column": "",
                "model_family": model,
                "availability_status": "missing_public_prediction_file_no_completed_row",
            }
        )
    frame = frame[frame["unique_prototype"].astype(bool)].copy()
    frame = add_blocks(frame)
    hull_reference = (
        frame["e_form_per_atom_mp2020_corrected"].astype(float)
        - frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    )
    frame["stable_DFT"] = frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= 0.0
    for spec in source_specs:
        if spec["availability_status"] != "available_completed":
            continue
        score_col = spec["proposal_source"] + "_score"
        frame[score_col] = -(frame[spec["column"]].astype(float) - hull_reference)
        spec["score_col"] = score_col
    return frame.reset_index(drop=True), source_specs, input_hashes


def run_materials_followup(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    frame, source_specs, hashes = load_materials_frame(args)
    seeds = parse_list(args.seeds, int)
    budgets = parse_list(args.budgets, int)
    alphas = parse_list(args.alphas, float)
    rho = float(args.rho)
    rows: list[dict] = []
    labels = frame["stable_DFT"].to_numpy(dtype=bool)
    for spec in source_specs:
        if spec["availability_status"] != "available_completed":
            continue
        score_col = spec["score_col"]
        scores = frame[score_col].to_numpy(dtype=float)
        observed = observed_positive_mask(labels, scores, rho)
        for seed in seeds:
            cal_blocks, test_blocks = split_blocks(frame["composition_family_pair"].astype(str).tolist(), seed)
            for alpha in alphas:
                test, diag = compute_evalues(
                    frame,
                    score_col=score_col,
                    block_col="composition_family_pair",
                    observed_positive=observed,
                    cal_blocks=cal_blocks,
                    test_blocks=test_blocks,
                    alpha=alpha,
                )
                max_observed_e = float(test["_evalue"].max()) if len(test) else 0.0
                for budget in budgets:
                    pool = test.head(budget).copy()
                    evalues = pool["_evalue"].to_numpy(dtype=float)
                    released, _tau, margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
                    selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                    raw_prefix = pool.head(released).copy() if released else pool.iloc[[]].copy()
                    selected_ids = set(selected["material_id"].astype(str))
                    raw_tail = pool[~pool["material_id"].astype(str).isin(selected_ids)].copy()
                    raw_unstable = int((~pool["stable_DFT"].astype(bool)).sum()) if len(pool) else 0
                    parc_unstable = int((~selected["stable_DFT"].astype(bool)).sum()) if released else 0
                    rows.append(
                        {
                            "domain": "materials_discovery",
                            "dataset": "Matbench Discovery WBM unique prototypes",
                            "unit": "stable_inorganic_crystal_candidate",
                            "proposal_source": spec["proposal_source"],
                            "model_family": spec["model_family"],
                            "verification_mode": "masked_DFT_stable_positives_hidden_label_followup",
                            "block_definition": "composition_family_pair",
                            "rho": rho,
                            "alpha": alpha,
                            "K": budget,
                            "seed": seed,
                            "released": int(released),
                            "PARC_FTR": float((~selected["stable_DFT"].astype(bool)).mean()) if released else 0.0,
                            "raw_topK_FTR": float((~pool["stable_DFT"].astype(bool)).mean()) if len(pool) else 0.0,
                            "raw_topR_FTR": float((~raw_prefix["stable_DFT"].astype(bool)).mean()) if released else 0.0,
                            "raw_only_tail_FTR": float((~raw_tail["stable_DFT"].astype(bool)).mean()) if len(raw_tail) else 0.0,
                            "raw_unstable_count": raw_unstable,
                            "PARC_unstable_count": parc_unstable,
                            "prevented_unstable_followups": raw_unstable - parc_unstable,
                            "DFT_efficiency": float(selected["stable_DFT"].astype(bool).mean()) if released else 0.0,
                            "raw_DFT_efficiency": float(pool["stable_DFT"].astype(bool).mean()) if len(pool) else 0.0,
                            "max_observed_e": max_observed_e,
                            "required_e": diag["required_e"],
                            "best_mass_ratio": best_ratio,
                            "self_consistency_margin": margin,
                            "block_coverage": diag["block_coverage"],
                            "evidence_status": "completed_public_DFT_label_followup",
                        }
                    )
    seed_rows = pd.DataFrame(rows)
    summary = summarize_groups(
        seed_rows,
        ["domain", "dataset", "unit", "proposal_source", "model_family", "verification_mode", "block_definition", "rho", "alpha", "K"],
    )
    summary["release_status"] = summary.apply(
        lambda row: (
            "certified_release_low_FTR"
            if int(row["non_empty_seeds"]) >= 18 and float(row["PARC_FTR_mean"]) <= float(row["alpha"])
            else ("certified_refusal_or_low_power" if float(row["mean_release"]) == 0 else "boundary_or_partial_release")
        ),
        axis=1,
    )
    summary["evidence_status"] = "completed_public_DFT_label_followup"
    availability = pd.DataFrame(
        [
            {
                "proposal_source": spec["proposal_source"],
                "model_family": spec["model_family"],
                "availability_status": spec["availability_status"],
                "paper_status": (
                    "completed_evidence"
                    if spec["availability_status"] == "available_completed"
                    else "not_run_missing_public_prediction_file"
                ),
            }
            for spec in source_specs
        ]
    )
    return seed_rows, summary, availability, hashes


def _lineage_metrics(selected: pd.DataFrame, label_col: str) -> dict:
    if len(selected) == 0:
        return {
            "selected_links": 0,
            "false_links": 0,
            "false_link_fraction": 0.0,
            "successor_conflicts": 0,
            "predecessor_conflicts": 0,
            "component_corruption_proxy": 0,
            "manual_correction_burden_proxy": 0,
        }
    true = selected[label_col].astype(bool)
    source = selected["source_gt_label"].astype(str)
    target = selected["target_gt_label"].astype(str)
    valid_source = source.ne("nan") & source.ne("-1")
    valid_target = target.ne("nan") & target.ne("-1")
    successor_conflicts = int(
        selected.loc[valid_source].groupby(["ctc_dataset", "sequence_id", "source_gt_label"])["target_gt_label"]
        .nunique()
        .sub(1)
        .clip(lower=0)
        .sum()
    )
    predecessor_conflicts = int(
        selected.loc[valid_target].groupby(["ctc_dataset", "sequence_id", "target_gt_label"])["source_gt_label"]
        .nunique()
        .sub(1)
        .clip(lower=0)
        .sum()
    )
    false_links = int((~true).sum())
    return {
        "selected_links": int(len(selected)),
        "false_links": false_links,
        "false_link_fraction": float((~true).mean()),
        "successor_conflicts": successor_conflicts,
        "predecessor_conflicts": predecessor_conflicts,
        "component_corruption_proxy": false_links + successor_conflicts + predecessor_conflicts,
        "manual_correction_burden_proxy": false_links + successor_conflicts + predecessor_conflicts,
    }


def run_ctc_lineage_consequence(args: argparse.Namespace) -> pd.DataFrame:
    specs = [
        {
            "source": "ctc_learned_hybrid",
            "path": Path(args.ctc_learned_universe),
            "block_col": "video_id",
            "label_col": "_true_link",
        },
        {
            "source": "ctc_noisy_geometric_linker",
            "path": Path(args.ctc_geometric_universe),
            "block_col": "video_id",
            "label_col": "_true_link",
        },
        {
            "source": "ctc_random_score_negative_control",
            "path": Path(args.ctc_random_universe),
            "block_col": "video_id",
            "label_col": "_true_link",
        },
    ]
    rows: list[dict] = []
    seeds = parse_list(args.seeds, int)
    for spec in specs:
        if not spec["path"].exists():
            continue
        frame = pd.read_csv(spec["path"], low_memory=False)
        frame["_true_link"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
        labels = frame["_true_link"].to_numpy(dtype=bool)
        scores = frame["score"].to_numpy(dtype=float)
        observed = observed_positive_mask(labels, scores, rho=float(args.rho))
        for seed in seeds:
            cal_blocks, test_blocks = split_blocks(frame[spec["block_col"]].astype(str).tolist(), seed)
            test, diag = compute_evalues(
                frame,
                score_col="score",
                block_col=spec["block_col"],
                observed_positive=observed,
                cal_blocks=cal_blocks,
                test_blocks=test_blocks,
                alpha=0.10,
            )
            for budget in [100, 300, 5000]:
                pool = test.head(budget).copy()
                evalues = pool["_evalue"].to_numpy(dtype=float)
                released, _tau, _margin, best_ratio = scs_release_count(evalues, alpha=0.10, budget=budget)
                selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                raw_metrics = _lineage_metrics(pool, "_true_link")
                parc_metrics = _lineage_metrics(selected, "_true_link")
                oracle = pool[pool["_true_link"].astype(bool)].head(released).copy() if released else pool.iloc[[]].copy()
                oracle_metrics = _lineage_metrics(oracle, "_true_link")
                rows.append(
                    {
                        "domain": "biomedical_cell_tracking",
                        "dataset": "Cell Tracking Challenge",
                        "proposal_source": spec["source"],
                        "K": budget,
                        "alpha": 0.10,
                        "seed": seed,
                        "PARC_released": int(released),
                        "raw_selected_links": raw_metrics["selected_links"],
                        "raw_false_links": raw_metrics["false_links"],
                        "raw_false_link_fraction": raw_metrics["false_link_fraction"],
                        "raw_successor_conflicts": raw_metrics["successor_conflicts"],
                        "raw_predecessor_conflicts": raw_metrics["predecessor_conflicts"],
                        "raw_component_corruption_proxy": raw_metrics["component_corruption_proxy"],
                        "PARC_false_links": parc_metrics["false_links"],
                        "PARC_false_link_fraction": parc_metrics["false_link_fraction"],
                        "PARC_component_corruption_proxy": parc_metrics["component_corruption_proxy"],
                        "oracle_component_corruption_proxy": oracle_metrics["component_corruption_proxy"],
                        "prevented_false_links": raw_metrics["false_links"] - parc_metrics["false_links"],
                        "prevented_component_corruption_proxy": raw_metrics["component_corruption_proxy"]
                        - parc_metrics["component_corruption_proxy"],
                        "best_mass_ratio": best_ratio,
                        "max_observed_e": float(test["_evalue"].max()) if len(test) else 0.0,
                        "required_e": diag["required_e"],
                        "evidence_status": "completed_official_GT_lineage_consequence",
                    }
                )
    seed_rows = pd.DataFrame(rows)
    return summarize_ctc_lineage(seed_rows)


def summarize_ctc_lineage(seed_rows: pd.DataFrame) -> pd.DataFrame:
    out: list[dict] = []
    group_cols = ["domain", "dataset", "proposal_source", "K", "alpha"]
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        for col in [
            "PARC_released",
            "raw_false_links",
            "raw_false_link_fraction",
            "raw_component_corruption_proxy",
            "PARC_false_links",
            "PARC_false_link_fraction",
            "PARC_component_corruption_proxy",
            "prevented_false_links",
            "prevented_component_corruption_proxy",
            "best_mass_ratio",
        ]:
            row[col + "_mean"] = float(group[col].astype(float).mean())
        row["seeds"] = int(group["seed"].nunique())
        row["non_empty_seeds"] = int((group["PARC_released"].astype(int) > 0).sum())
        row["interpretation"] = (
            "PARC_prevents_false_lineage_edges"
            if row["prevented_false_links_mean"] > 0
            else "raw_queue_already_clean_or_no_release"
        )
        row["evidence_status"] = "completed_official_GT_lineage_consequence"
        out.append(row)
    return pd.DataFrame(out)


def run_spacenet_map_consequence(args: argparse.Namespace) -> pd.DataFrame:
    specs = [
        ("geometry_linker", Path(args.spacenet_geometry_universe)),
        ("randomized_linker", Path(args.spacenet_random_universe)),
    ]
    rows = []
    for source, path in specs:
        if not path.exists():
            continue
        usecols = [col for col in pd.read_csv(path, nrows=0).columns if col in {"score", "is_unmatched", "aoi", "video_id", "source_building_id", "target_building_id"}]
        frame = pd.read_csv(path, usecols=usecols, low_memory=False).sort_values("score", ascending=False)
        frame["_true_link"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
        for budget in [100, 300, 500, 1000, 5000]:
            selected = frame.head(budget).copy()
            false_links = int((~selected["_true_link"].astype(bool)).sum())
            if {"source_building_id", "target_building_id", "aoi"}.issubset(selected.columns):
                false_chains = int(
                    selected.groupby(["aoi", "source_building_id"])["target_building_id"].nunique().sub(1).clip(lower=0).sum()
                )
            else:
                false_chains = false_links
            rows.append(
                {
                    "domain": "earth_observation",
                    "dataset": "SpaceNet 7 official building identities",
                    "proposal_source": source,
                    "K": budget,
                    "raw_false_persistence_links": false_links,
                    "raw_false_link_fraction": float((~selected["_true_link"].astype(bool)).mean()),
                    "raw_false_persistence_chain_proxy": false_chains,
                    "official_GT_evaluation": "completed",
                    "PARC_context": (
                        "existing SpaceNet sweep reports release/refusal; this table quantifies raw map damage using official GT"
                    ),
                    "evidence_status": "completed_official_GT_map_consequence",
                }
            )
    return pd.DataFrame(rows)


def plot_materials_heatmap(summary: pd.DataFrame, out_csv: Path, out_pdf: Path) -> None:
    alpha = 0.10
    frame = summary[summary["alpha"].astype(float).eq(alpha)].copy()
    frame["cell_value"] = frame["mean_release"].round(1)
    frame.to_csv(out_csv, index=False)
    piv = frame.pivot_table(index="proposal_source", columns="K", values="mean_release", aggfunc="mean").fillna(0.0)
    fig, ax = plt.subplots(figsize=(8.0, 2.8 + 0.35 * len(piv)))
    im = ax.imshow(piv.to_numpy(dtype=float), aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(piv.columns)), [str(c) for c in piv.columns])
    ax.set_yticks(range(len(piv.index)), [str(i).replace("_", " ") for i in piv.index])
    ax.set_xlabel("Requested follow-up queue K")
    ax.set_title("Materials model-zoo certified release size (alpha=0.10)")
    for i in range(len(piv.index)):
        for j in range(len(piv.columns)):
            val = piv.iloc[i, j]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7, color="black")
    fig.colorbar(im, ax=ax, label="mean PARC release")
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def plot_followup_efficiency(summary: pd.DataFrame, out_csv: Path, out_pdf: Path) -> None:
    frame = summary[(summary["alpha"].astype(float).eq(0.10)) & (summary["K"].isin([300, 500, 1000]))].copy()
    frame.to_csv(out_csv, index=False)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for source, group in frame.groupby("proposal_source"):
        group = group.sort_values("K")
        ax.plot(group["K"], group["prevented_unstable_followups_mean"], marker="o", label=source.replace("_", " "))
    ax.set_xscale("log")
    ax.set_xlabel("Raw follow-up queue K")
    ax.set_ylabel("Prevented unstable follow-ups per seed")
    ax.set_title("PARC as a certified stopping rule for materials follow-up")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_provenance(path: Path, artifact: Path, report: dict, role: str) -> None:
    provenance = {
        "status": "completed",
        "evidence_status": "completed_no_new_human_labels",
        "role": role,
        "artifact": artifact.name,
        "command": "python scripts/build_no_human_scientific_consequence.py",
        "scope": "computational/official-GT consequence diagnostics; no new human labels",
        "input_hashes": report["input_hashes"],
        "output_sha256": sha256_file(artifact),
        "notes": [
            "Materials rows are retrospective hidden-label computational follow-up, not experimental synthesis.",
            "CTC and SpaceNet consequence rows use official/held-out benchmark labels only.",
            "Missing modern materials-model prediction files are recorded as not-run rows, not completed evidence.",
        ],
    }
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")


def write_closeout(out_dir: Path, report: dict) -> None:
    text = (
        "# No-Human Scientific Consequence Closeout\n\n"
        "This milestone adds completed computational/official-GT consequence diagnostics only. "
        "It introduces no new human labels and does not promote protocol-only rows.\n\n"
        "## Completed Evidence\n\n"
        "- Materials computational follow-up queue: public WBM/Matbench labels and public model prediction CSVs.\n"
        "- Materials model-zoo release frontier: completed for local CGCNN, ALIGNN-FF, and MEGNet prediction files.\n"
        "- CTC lineage consequence: official GT link labels quantify false lineage-edge and component-corruption proxies.\n"
        "- SpaceNet map consequence: official GT building identities quantify raw false-persistence links.\n\n"
        "## Not Run\n\n"
        "CHGNet, M3GNet, MACE, ORB, SevenNet, EquiformerV2, and MatterSim rows are recorded as missing local public prediction files; no completed results are fabricated for them.\n\n"
        "## Scope\n\n"
        "Materials follow-up is retrospective/hidden-label computational follow-up, not experimental synthesis. CTC and SpaceNet consequences use official benchmark labels, not new manual review.\n\n"
        f"Summary: `{report['summary_json']}`\n"
    )
    (out_dir / "NO_HUMAN_SCIENTIFIC_CONSEQUENCE_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/no_human_scientific_consequence")
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--megnet-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    parser.add_argument("--megnet-pred-col", default="e_form_per_atom_megnet")
    parser.add_argument("--ctc-learned-universe", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1/candidate_universe.csv")
    parser.add_argument("--ctc-random-universe", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1_random_control/candidate_universe.csv")
    parser.add_argument("--ctc-geometric-universe", default="/home/waas/paper_experiments/outputs/ctc_link_certification/universe_gt_tra_noisy_w90_win5/candidate_universe.csv")
    parser.add_argument("--spacenet-geometry-universe", default="/home/waas/paper_experiments/outputs/spacenet7_building_links/universe_geometry_w35_aoi18/candidate_universe.csv")
    parser.add_argument("--spacenet-random-universe", default="/home/waas/paper_experiments/outputs/spacenet7_building_links/universe_randomized_linker_aoi18_light/candidate_universe.csv")
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--budgets", default=",".join(str(k) for k in DEFAULT_K))
    parser.add_argument("--alphas", default=",".join(str(a) for a in DEFAULT_ALPHA))
    parser.add_argument("--rho", type=float, default=0.10)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    material_seed, material_summary, model_availability, input_hashes = run_materials_followup(args)
    material_seed.to_csv(out_dir / "table_materials_computational_followup_seed_rows.csv", index=False)
    material_summary.to_csv(out_dir / "table_materials_computational_followup.csv", index=False)
    model_availability.to_csv(out_dir / "table_materials_model_prediction_availability.csv", index=False)
    material_summary.to_csv(out_dir / "table_materials_model_zoo_release_frontier.csv", index=False)
    plot_materials_heatmap(
        material_summary,
        out_dir / "figure_materials_model_zoo_release_map.csv",
        out_dir / "figure_materials_model_zoo_release_map.pdf",
    )
    plot_followup_efficiency(
        material_summary,
        out_dir / "figure_materials_followup_efficiency.csv",
        out_dir / "figure_materials_followup_efficiency.pdf",
    )

    ctc = run_ctc_lineage_consequence(args)
    ctc.to_csv(out_dir / "table_ctc_lineage_consequence.csv", index=False)
    spacenet = run_spacenet_map_consequence(args)
    spacenet.to_csv(out_dir / "table_spacenet_map_consequence.csv", index=False)

    report = {
        "status": "completed",
        "evidence_status": "completed_no_new_human_labels",
        "runtime_sec": time.perf_counter() - started,
        "summary_json": "no_human_scientific_consequence_summary.json",
        "material_followup_rows": int(len(material_summary)),
        "material_seed_rows": int(len(material_seed)),
        "ctc_consequence_rows": int(len(ctc)),
        "spacenet_consequence_rows": int(len(spacenet)),
        "input_hashes": input_hashes,
        "scope": "computational/official-GT consequence diagnostics; no new human labels",
    }
    summary_path = out_dir / "no_human_scientific_consequence_summary.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_closeout(out_dir, report)
    for name, role in [
        ("table_materials_computational_followup.csv", "materials_followup_summary"),
        ("table_materials_computational_followup_seed_rows.csv", "materials_followup_seed_rows"),
        ("table_materials_model_zoo_release_frontier.csv", "materials_model_zoo_frontier"),
        ("table_materials_model_prediction_availability.csv", "materials_model_availability"),
        ("table_ctc_lineage_consequence.csv", "ctc_lineage_consequence"),
        ("table_spacenet_map_consequence.csv", "spacenet_map_consequence"),
        ("figure_materials_model_zoo_release_map.csv", "materials_model_zoo_figure_source"),
        ("figure_materials_model_zoo_release_map.pdf", "materials_model_zoo_figure"),
        ("figure_materials_followup_efficiency.csv", "materials_followup_figure_source"),
        ("figure_materials_followup_efficiency.pdf", "materials_followup_figure"),
        ("NO_HUMAN_SCIENTIFIC_CONSEQUENCE_CLOSEOUT.md", "closeout"),
        ("no_human_scientific_consequence_summary.json", "summary_json"),
    ]:
        artifact = out_dir / name
        if artifact.exists():
            write_provenance(artifact.with_suffix(artifact.suffix + ".provenance.json"), artifact, report, role)
    write_manifest(out_dir)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
