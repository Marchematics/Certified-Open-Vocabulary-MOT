from __future__ import annotations

import hashlib
import json
import math
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .adapters.datasets import ensure_data_output, load_yaml, write_json
from .phase2 import (
    AUDIT_LABEL_COLUMNS,
    _best_mass_summary,
    _block_evalues,
    _load_universe_with_labels,
    _method_specs_for_real_certify,
    _scs_release_count,
    _split_video_ids,
    gamma_star_from_p,
)
from .phase3 import _label_metrics, run_ovtb_matrix


DATA_ROOT = Path("/home/waas/paper_experiments")
PARC_METHOD = "parc_track_gamma_tuned_uniform_scs"


def _safe_name(value: Any) -> str:
    return str(value).replace("/", "_").replace(" ", "_").replace(".", "p").replace("+", "plus")


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def _sha256(path: str | Path) -> str | None:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_if_exists(src: str | Path, dst_dir: Path, dst_name: str | None = None) -> Path | None:
    src = Path(src)
    if not src.exists() or not src.is_file():
        return None
    dst = ensure_data_output(dst_dir / (dst_name or src.name))
    shutil.copy2(src, dst)
    return dst


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    out = ensure_data_output(path)
    with out.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return out


def _base_entries() -> list[dict[str, Any]]:
    return [
        {
            "dataset": "OVT-B",
            "generator": "GroundingDINO",
            "config": DATA_ROOT / "configs/phase3_ovtb_full_matrix.yaml",
            "matrix": DATA_ROOT / "outputs/phase3_ovtb_full/ovtb_alpha_seed_m_matrix.csv",
            "output_dir": DATA_ROOT / "outputs/phase3_ovtb_full",
            "candidate_universe": DATA_ROOT / "outputs/phase2_full/candidate_universe.csv",
            "candidate_nodes": DATA_ROOT / "outputs/phase2_full/candidate_nodes.csv",
            "ann_file": DATA_ROOT / "data/OVT-B/ovtb_ann.json",
        },
        {
            "dataset": "TAO",
            "generator": "GroundingDINO",
            "config": DATA_ROOT / "configs/phase3_tao_full_matrix.yaml",
            "matrix": DATA_ROOT / "outputs/phase3_tao_full/tao_alpha_seed_m_matrix.csv",
            "output_dir": DATA_ROOT / "outputs/phase3_tao_full",
            "candidate_universe": DATA_ROOT / "outputs/phase3_tao_full/candidate_universe.csv",
            "candidate_nodes": DATA_ROOT / "outputs/phase3_tao_full/candidate_nodes.csv",
            "ann_file": DATA_ROOT / "data/TAO/annotations/trainval.json",
        },
        {
            "dataset": "OVT-B",
            "generator": "OWLv2",
            "config": DATA_ROOT / "configs/phase3_ovtb_owlv2_matrix.yaml",
            "matrix": DATA_ROOT / "outputs/phase3_ovtb_owlv2/ovtb_alpha_seed_m_matrix.csv",
            "output_dir": DATA_ROOT / "outputs/phase3_ovtb_owlv2",
            "candidate_universe": DATA_ROOT / "outputs/phase3_ovtb_owlv2/candidate_universe.csv",
            "candidate_nodes": DATA_ROOT / "outputs/phase3_ovtb_owlv2/candidate_nodes.csv",
            "ann_file": DATA_ROOT / "data/OVT-B/ovtb_ann.json",
        },
        {
            "dataset": "TAO",
            "generator": "OWLv2",
            "config": DATA_ROOT / "configs/phase3_tao_owlv2_matrix.yaml",
            "matrix": DATA_ROOT / "outputs/phase3_tao_owlv2/tao_alpha_seed_m_matrix.csv",
            "output_dir": DATA_ROOT / "outputs/phase3_tao_owlv2",
            "candidate_universe": DATA_ROOT / "outputs/phase3_tao_owlv2/candidate_universe.csv",
            "candidate_nodes": DATA_ROOT / "outputs/phase3_tao_owlv2/candidate_nodes.csv",
            "ann_file": DATA_ROOT / "data/TAO/annotations/trainval.json",
        },
    ]


def _entry_for(dataset: str, generator: str = "GroundingDINO") -> dict[str, Any]:
    for entry in _base_entries():
        if entry["dataset"].lower() == dataset.lower() and entry["generator"].lower() == generator.lower():
            return entry
    raise ValueError(f"unknown dataset/generator entry: {dataset}/{generator}")


def _load_cfg(entry: dict[str, Any]) -> dict[str, Any]:
    return load_yaml(entry["config"])


def _method_evalues(entry: dict[str, Any], alpha: float, seed: int, method: str = PARC_METHOD) -> pd.DataFrame:
    name = f"alpha{_safe_name(alpha)}_seed{seed}"
    path = Path(entry["output_dir"]) / f"candidate_evalues_{name}.csv"
    if not path.exists() and alpha not in (0.05, 0.10, 0.20):
        # E-values do not depend on alpha; intermediate frontier points reuse the
        # alpha=0.10 calibration file and only change the SCS threshold.
        path = Path(entry["output_dir"]) / f"candidate_evalues_alpha0p1_seed{seed}.csv"
    frame = _read_csv(path)
    if frame.empty:
        return frame
    return frame[frame["method"].astype(str) == method].copy()


def _matrix_parc_rows(entry: dict[str, Any]) -> pd.DataFrame:
    frame = _read_csv(entry["matrix"])
    if frame.empty:
        return frame
    return frame[frame["method"].astype(str) == PARC_METHOD].copy()


def _test_pool(cfg: dict[str, Any], universe: pd.DataFrame, seed: int, budget: int) -> pd.DataFrame:
    run_cfg = json.loads(json.dumps(cfg))
    run_cfg.setdefault("splits", {})["seed"] = int(seed)
    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), run_cfg)
    frame = universe.copy()
    frame["split"] = frame["video_id"].astype(int).map(split_map)
    return frame[frame["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).head(int(budget))


def run_prop5_validation(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_prop5")
    rows = []
    seed_rows = []
    for entry in _base_entries():
        matrix = _matrix_parc_rows(entry)
        for alpha in [0.10, 0.20]:
            actual_nonempty = 0
            predicted_nonempty = 0
            ratios = []
            margins = []
            for seed in [0, 1, 2]:
                evalues = _method_evalues(entry, alpha, seed)
                if evalues.empty:
                    continue
                cfg = _load_cfg(entry)
                universe = _load_universe_with_labels(cfg)
                pool = _test_pool(cfg, universe, seed, budget)
                rank = pool[["path_id", "candidate_rank", "score"]].copy()
                values_frame = rank.merge(evalues[["path_id", "e_value"]], on="path_id", how="left")
                values = values_frame["e_value"].fillna(0.0).astype(float).tolist()
                best = _best_mass_summary(values, alpha, budget)
                pred = bool(best["best_mass_ratio"] >= 1.0)
                row = matrix[
                    (pd.to_numeric(matrix["alpha1"], errors="coerce") == alpha)
                    & (pd.to_numeric(matrix["seed"], errors="coerce") == seed)
                    & (pd.to_numeric(matrix["candidate_budget_M"], errors="coerce") == budget)
                ]
                released = int(pd.to_numeric(row["released"], errors="coerce").fillna(0).iloc[0]) if not row.empty else 0
                actual = released > 0
                actual_nonempty += int(actual)
                predicted_nonempty += int(pred)
                ratios.append(float(best["best_mass_ratio"]))
                margins.append(float(best["best_margin"]))
                seed_rows.append(
                    {
                        "dataset": entry["dataset"],
                        "generator": entry["generator"],
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": budget,
                        "best_mass_ratio": best["best_mass_ratio"],
                        "best_margin": best["best_margin"],
                        "predicted_nonempty": pred,
                        "actual_released": released,
                        "actual_nonempty": actual,
                        "prediction_correct": pred == actual,
                    }
                )
            rows.append(
                {
                    "dataset": entry["dataset"],
                    "generator": entry["generator"],
                    "alpha1": alpha,
                    "candidate_budget_M": budget,
                    "predicted_nonempty_seeds": predicted_nonempty,
                    "actual_nonempty_seeds": actual_nonempty,
                    "mean_best_mass_ratio": float(np.mean(ratios)) if ratios else None,
                    "min_best_mass_ratio": float(np.min(ratios)) if ratios else None,
                    "max_best_mass_ratio": float(np.max(ratios)) if ratios else None,
                    "mean_best_margin": float(np.mean(margins)) if margins else None,
                    "all_seed_predictions_correct": predicted_nonempty == actual_nonempty,
                }
            )
    seed_csv = ensure_data_output(output_dir / "prop5_validation_by_seed.csv")
    table_csv = ensure_data_output(output_dir / "table_prop5_validation.csv")
    pd.DataFrame(seed_rows).to_csv(seed_csv, index=False)
    pd.DataFrame(rows).to_csv(table_csv, index=False)
    summary = {"status": "completed", "table": str(table_csv), "seed_table": str(seed_csv), "rows": len(rows)}
    write_json(output_dir / "prop5_validation_summary.json", summary)
    return summary


def _score_variant(frame: pd.DataFrame, variant: str) -> pd.Series:
    objectness = pd.to_numeric(frame.get("objectness", frame["score"]), errors="coerce").fillna(0.0)
    semantic = pd.to_numeric(frame.get("semantic_margin", frame["score"]), errors="coerce").fillna(0.0)
    path_len = pd.to_numeric(frame.get("path_length", 1.0), errors="coerce").fillna(1.0)
    temporal = pd.to_numeric(frame.get("temporal_stability", path_len), errors="coerce").fillna(1.0)
    assoc = pd.to_numeric(frame.get("association_score", 0.0), errors="coerce").fillna(0.0)
    length_norm = np.clip(path_len / 8.0, 0.0, 1.0)
    temporal_norm = np.clip(temporal / 8.0, 0.0, 1.0)
    if variant == "detector_only":
        return objectness
    if variant == "detector_temporal":
        return 0.82 * objectness + 0.18 * temporal_norm
    if variant == "detector_association":
        return 0.82 * objectness + 0.18 * assoc
    if variant == "weighted_components":
        return 0.55 * objectness + 0.15 * semantic + 0.15 * temporal_norm + 0.15 * assoc
    raise ValueError(f"unknown score variant: {variant}")


def _write_variant_universe(entry: dict[str, Any], variant: str, output_dir: Path) -> Path:
    universe = pd.read_csv(entry["candidate_universe"])
    out = universe.copy()
    out["score_original"] = pd.to_numeric(out["score"], errors="coerce")
    out["score"] = _score_variant(out, variant)
    out["score_source"] = f"score_ablation_{variant}"
    out = out.sort_values(["score", "score_original", "path_length"], ascending=[False, False, False]).reset_index(drop=True)
    out["candidate_rank"] = np.arange(1, len(out) + 1)
    path = ensure_data_output(output_dir / "candidate_universe.csv")
    out.to_csv(path, index=False)
    return path


def _candidate_label(frame: pd.DataFrame) -> pd.Series:
    matched = frame.get("is_matched_to_gt", pd.Series(False, index=frame.index)).astype(bool)
    verified = frame.get("is_verified_positive", pd.Series(False, index=frame.index)).astype(bool)
    return (matched | verified).astype(int)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-values))


def _logit_scores(scores: pd.Series) -> np.ndarray:
    arr = pd.to_numeric(scores, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    arr = np.clip(arr, 1e-4, 1.0 - 1e-4)
    return np.log(arr / (1.0 - arr))


def _nll(prob: np.ndarray, y: np.ndarray) -> float:
    prob = np.clip(prob, 1e-6, 1.0 - 1e-6)
    return float(-(y * np.log(prob) + (1.0 - y) * np.log(1.0 - prob)).mean())


def _temperature_calibrator(cal: pd.DataFrame) -> tuple[float, float]:
    y = _candidate_label(cal).to_numpy(dtype=float)
    logits = _logit_scores(cal["score"])
    candidates = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]
    best_t = min(candidates, key=lambda temp: _nll(_sigmoid(logits / temp), y))
    return float(best_t), _nll(_sigmoid(logits / best_t), y)


def _platt_calibrator(cal: pd.DataFrame) -> tuple[float, float, float]:
    y = _candidate_label(cal).to_numpy(dtype=float)
    x = pd.to_numeric(cal["score"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    a = 1.0
    b = float(np.log((y.mean() + 1e-3) / (1.0 - y.mean() + 1e-3)))
    for _ in range(400):
        pred = _sigmoid(a * x + b)
        grad_a = float(((pred - y) * x).mean())
        grad_b = float((pred - y).mean())
        a -= 0.5 * grad_a
        b -= 0.5 * grad_b
    return float(a), float(b), _nll(_sigmoid(a * x + b), y)


def run_confidence_calibration_baselines(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase5_confidence_calibration")
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        cfg = _load_cfg(entry)
        universe = _load_universe_with_labels(cfg)
        for seed in [0, 1, 2]:
            split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), {**cfg, "splits": {**cfg.get("splits", {}), "seed": seed}})
            frame = universe.copy()
            frame["split"] = frame["video_id"].astype(int).map(split_map)
            cal = frame[frame["split"] == "cal"].copy()
            test_pool = frame[frame["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).head(int(budget)).copy()
            if cal.empty or test_pool.empty:
                continue
            temp, temp_nll = _temperature_calibrator(cal)
            platt_a, platt_b, platt_nll = _platt_calibrator(cal)
            raw_prob = pd.to_numeric(test_pool["score"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            temp_prob = _sigmoid(_logit_scores(test_pool["score"]) / temp)
            platt_prob = _sigmoid(platt_a * raw_prob + platt_b)
            prob_map = {
                "raw_confidence_threshold": raw_prob,
                "temperature_scaled_threshold": temp_prob,
                "platt_threshold": platt_prob,
                "platt_top_m_no_risk": platt_prob,
            }
            for alpha in [0.10, 0.20]:
                for method, prob in prob_map.items():
                    pool = test_pool.copy()
                    pool["calibrated_probability"] = prob
                    if method.endswith("top_m_no_risk"):
                        selected = pool.sort_values(["calibrated_probability", "score"], ascending=[False, False]).head(int(budget))
                    else:
                        selected = pool[pool["calibrated_probability"] >= 1.0 - float(alpha)].copy()
                    metrics = _label_metrics(selected, budget)
                    rows.append(
                        {
                            "dataset": entry["dataset"],
                            "generator": entry["generator"],
                            "method": method,
                            "alpha1": alpha,
                            "seed": seed,
                            "candidate_budget_M": budget,
                            "temperature": temp,
                            "temperature_cal_nll": temp_nll,
                            "platt_a": platt_a,
                            "platt_b": platt_b,
                            "platt_cal_nll": platt_nll,
                            "risk_certificate": "none_confidence_baseline",
                            **metrics,
                        }
                    )
    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_confidence_calibration_baselines.csv")
    table.to_csv(out_csv, index=False)
    summary_csv = ensure_data_output(output_dir / "table_confidence_calibration_baselines_meanstd.csv")
    if not table.empty:
        (
            table.groupby(["dataset", "generator", "method", "alpha1"], dropna=False)
            .agg(
                released_mean=("released", "mean"),
                released_std=("released", "std"),
                utr_mean=("utr", "mean"),
                conservative_ftr_mean=("conservative_ftr_uncertain_and_unlabeled_false", "mean"),
                nonempty_rate=("released", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) > 0).mean())),
            )
            .reset_index()
            .to_csv(summary_csv, index=False)
        )
    else:
        pd.DataFrame().to_csv(summary_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "summary": str(summary_csv), "rows": len(table)}
    write_json(output_dir / "confidence_calibration_baselines_summary.json", result)
    return result


def _write_cell_variant_universe(entry: dict[str, Any], variant: str, output_dir: Path) -> Path:
    universe = pd.read_csv(entry["candidate_universe"])
    out = universe.copy()
    if variant == "global":
        out["cell_id"] = "global"
    elif variant == "category":
        out["cell_id"] = "cat:" + out["category_id"].astype(str)
    elif variant == "query_cluster":
        cluster = out.get("query_cluster", out.get("query", pd.Series("unknown", index=out.index))).fillna("unknown").astype(str)
        out["cell_id"] = "query:" + cluster
    elif variant == "category_occ":
        occ = out.get("occ_bin", pd.Series("unknown", index=out.index)).fillna("unknown").astype(str)
        out["cell_id"] = "cat:" + out["category_id"].astype(str) + "|occ:" + occ
    else:
        raise ValueError(f"unknown Mondrian variant: {variant}")
    path = ensure_data_output(output_dir / "candidate_universe.csv")
    out.to_csv(path, index=False)
    return path


def _assign_cell_variant(frame: pd.DataFrame, variant: str) -> pd.Series:
    if variant == "global":
        return pd.Series("global", index=frame.index)
    if variant == "category":
        return "cat:" + frame["category_id"].astype(str)
    if variant == "query_cluster":
        cluster = frame.get("query_cluster", frame.get("query", pd.Series("unknown", index=frame.index))).fillna("unknown").astype(str)
        return "query:" + cluster
    if variant == "category_occ":
        occ = frame.get("occ_bin", pd.Series("unknown", index=frame.index)).fillna("unknown").astype(str)
        return "cat:" + frame["category_id"].astype(str) + "|occ:" + occ
    raise ValueError(f"unknown Mondrian variant: {variant}")


def _cell_aware_evalues(
    test: pd.DataFrame,
    cal: pd.DataFrame,
    alpha: float,
    grid_size: int = 1,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    null_cal = cal[cal["is_unmatched"].astype(bool) & ~cal["is_verified_positive"].astype(bool)].copy()
    if not null_cal.empty:
        grouped = (
            null_cal.assign(video_id=null_cal["video_id"].astype(int), cell_id=null_cal["cell_id"].astype(str), score=null_cal["score"].astype(float))
            .groupby(["cell_id", "video_id"], dropna=False)["score"]
            .max()
            .reset_index()
        )
        maxima_by_cell = {
            str(cell): values["score"].astype(float).tolist()
            for cell, values in grouped.groupby("cell_id", dropna=False)
        }
    else:
        maxima_by_cell = {}
    rows = []
    n_ranks = []
    pmins = []
    for _, row in test.iterrows():
        cell = str(row["cell_id"])
        maxima = maxima_by_cell.get(cell, [])
        n_rank = len(maxima)
        if n_rank:
            exceed = sum(1 for value in maxima if value >= float(row["score"]))
            p_block = (1.0 + exceed) / (n_rank + 1.0)
            p_any = min(1.0, p_block * grid_size)
            p_min = min(1.0, grid_size / (n_rank + 1.0))
            gamma = gamma_star_from_p(p_min) or 0.5
            gamma = max(0.10, min(0.50, gamma))
            e_value = gamma * (p_any ** (gamma - 1.0)) if p_any > 0 else 0.0
        else:
            p_block = 1.0
            p_any = 1.0
            p_min = 1.0
            gamma = 0.5
            e_value = 0.0
        n_ranks.append(n_rank)
        pmins.append(p_min)
        rows.append(
            {
                "path_id": row["path_id"],
                "cell_id": cell,
                "score": float(row["score"]),
                "n_rank_cell": n_rank,
                "p_block": p_block,
                "p_any": p_any,
                "p_min_cell": p_min,
                "gamma_cell": gamma,
                "e_value": e_value,
            }
        )
    diag = {
        "n_rank_cell_mean": float(np.mean(n_ranks)) if n_ranks else 0.0,
        "n_rank_cell_min": int(min(n_ranks)) if n_ranks else 0,
        "n_rank_cell_max": int(max(n_ranks)) if n_ranks else 0,
        "p_min_cell_mean": float(np.mean(pmins)) if pmins else 1.0,
    }
    return pd.DataFrame(rows), diag


def run_mondrian_ablation(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_root = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase5_mondrian_ablation")
    variants = ["global", "category", "query_cluster", "category_occ"]
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        cfg = _load_cfg(entry)
        universe_base = _load_universe_with_labels(cfg)
        for variant in variants:
            for seed in [0, 1, 2]:
                split_map = _split_video_ids(universe_base["video_id"].astype(int).tolist(), {**cfg, "splits": {**cfg.get("splits", {}), "seed": seed}})
                frame = universe_base.copy()
                frame["split"] = frame["video_id"].astype(int).map(split_map)
                frame["cell_id"] = _assign_cell_variant(frame, variant)
                cal = frame[frame["split"] == "cal"].copy()
                test = frame[frame["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).head(150).copy()
                eframe, diag = _cell_aware_evalues(test, cal, alpha=0.10)
                merged = test.merge(eframe[["path_id", "e_value"]], on="path_id", how="left")
                values = merged["e_value"].fillna(0.0).astype(float).tolist()
                for alpha in [0.10, 0.20]:
                    k, tau, margin = _scs_release_count(values, alpha1=alpha, candidate_budget_m=150)
                    selected = merged.sort_values("e_value", ascending=False).head(k).copy() if k else merged.iloc[[]].copy()
                    metrics = _label_metrics(selected, 150)
                    mass = _best_mass_summary(values, alpha1=alpha, candidate_budget_m=150)
                    rows.append(
                        {
                            "dataset": entry["dataset"],
                            "generator": entry["generator"],
                            "mondrian_variant": variant,
                            "alpha1": alpha,
                            "seed": seed,
                            "candidate_budget_M": 150,
                            "tau_k": tau if k else None,
                            "self_consistency_margin": margin if k else None,
                            "best_mass_ratio": mass["best_mass_ratio"],
                            **diag,
                            **metrics,
                        }
                    )
    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_root / "table_mondrian_ablation.csv")
    table.to_csv(out_csv, index=False)
    summary_csv = ensure_data_output(output_root / "table_mondrian_ablation_summary.csv")
    if not table.empty:
        (
            table.groupby(["dataset", "generator", "mondrian_variant", "alpha1"], dropna=False)
            .agg(
                released_mean=("released", "mean"),
                released_std=("released", "std"),
                utr_mean=("utr", "mean"),
                conservative_ftr_mean=("conservative_ftr_uncertain_and_unlabeled_false", "mean"),
                margin_mean=("self_consistency_margin", "mean"),
                nonempty_rate=("released", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) > 0).mean())),
                n_rank_cell_mean=("n_rank_cell_mean", "mean"),
                n_rank_cell_min=("n_rank_cell_min", "mean"),
            )
            .reset_index()
            .to_csv(summary_csv, index=False)
        )
    else:
        pd.DataFrame().to_csv(summary_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "summary": str(summary_csv), "rows": len(table)}
    write_json(output_root / "mondrian_ablation_summary.json", result)
    return result


def run_score_ablation(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_root = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_score_ablation")
    variants = ["detector_only", "detector_temporal", "detector_association", "weighted_components"]
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        base_cfg = _load_cfg(entry)
        for variant in variants:
            variant_dir = ensure_data_output(output_root / f"{entry['dataset'].lower()}_{variant}")
            universe_path = _write_variant_universe(entry, variant, variant_dir)
            cfg = json.loads(json.dumps(base_cfg))
            cfg.setdefault("matrix", {})["alpha1"] = [0.10, 0.20]
            cfg["matrix"]["seeds"] = [0, 1, 2]
            cfg["matrix"]["candidate_budget_M"] = [150]
            cfg.setdefault("selector", {})["candidate_budget_sweep"] = [150]
            cfg.setdefault("input", {})["candidate_universe"] = str(universe_path)
            cfg.setdefault("output", {})["output_dir"] = str(variant_dir)
            cfg["output"]["candidate_nodes"] = str(entry["candidate_nodes"])
            cfg_path = _write_yaml(variant_dir / "score_ablation_config.yaml", cfg)
            result = run_ovtb_matrix(cfg_path)
            matrix = _read_csv(result["matrix_csv"])
            parc = matrix[matrix["method"].astype(str) == PARC_METHOD].copy()
            parc["dataset"] = entry["dataset"]
            parc["score_variant"] = variant
            rows.append(parc)
    table = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    out_csv = ensure_data_output(output_root / "table_score_ablation.csv")
    table.to_csv(out_csv, index=False)
    summary_csv = ensure_data_output(output_root / "table_score_ablation_summary.csv")
    if not table.empty:
        summary = (
            table.groupby(["dataset", "score_variant", "alpha1"], dropna=False)
            .agg(
                released_mean=("released", "mean"),
                nonempty_rate=("released", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) > 0).mean())),
                utr_mean=("utr", "mean"),
                conservative_ftr_mean=("conservative_ftr_uncertain_and_unlabeled_false", "mean"),
                margin_mean=("self_consistency_margin", "mean"),
            )
            .reset_index()
        )
    else:
        summary = pd.DataFrame()
    summary.to_csv(summary_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "summary": str(summary_csv), "rows": len(table)}
    write_json(output_root / "score_ablation_summary.json", result)
    return result


def run_owlv2_top_audit_sample(out_dir: str | Path | None = None, per_dataset: int = 50) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_owlv2_top_audit")
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "OWLv2"]:
        universe = pd.read_csv(entry["candidate_universe"])
        top = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).head(150).copy()
        sample = top.sample(n=min(per_dataset, len(top)), random_state=20260509) if len(top) else top
        rows.append(sample)
    candidates = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    candidates_csv = ensure_data_output(output_dir / "owlv2_top150_mini_audit_candidates.csv")
    labels_csv = ensure_data_output(output_dir / "owlv2_top150_mini_audit_labels.csv")
    candidates.to_csv(candidates_csv, index=False)
    labels = candidates[[col for col in ["dataset", "video_id", "path_id", "query", "category_id", "score", "candidate_rank", "is_matched_to_gt", "matched_iou"] if col in candidates]].copy()
    for column in AUDIT_LABEL_COLUMNS:
        if column not in labels:
            labels[column] = ""
    labels["label"] = ""
    labels["verified_positive_for_calibration"] = "no"
    labels["reason"] = ""
    labels["confidence"] = ""
    labels["auditor"] = ""
    labels.to_csv(labels_csv, index=False)
    summary = {
        "status": "completed",
        "candidates": str(candidates_csv),
        "labels_template": str(labels_csv),
        "rows": len(candidates),
        "per_dataset": per_dataset,
    }
    write_json(output_dir / "owlv2_top150_mini_audit_manifest.json", summary)
    return summary


def _select_from_evalues(entry: dict[str, Any], alpha: float, seed: int, budget: int, method: str = PARC_METHOD) -> pd.DataFrame:
    cfg = _load_cfg(entry)
    universe = _load_universe_with_labels(cfg)
    pool = _test_pool(cfg, universe, seed, budget)
    evalues = _method_evalues(entry, alpha, seed, method)
    if evalues.empty or pool.empty:
        return pool.iloc[[]].copy()
    frame = pool.merge(evalues[["path_id", "e_value"]], on="path_id", how="left")
    frame["e_value"] = frame["e_value"].fillna(0.0).astype(float)
    k, _, _ = _scs_release_count(frame["e_value"].tolist(), alpha1=alpha, candidate_budget_m=budget)
    return frame.sort_values("e_value", ascending=False).head(k).copy() if k else frame.iloc[[]].copy()


def run_alpha_frontier(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_frontier")
    alphas = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    rows = []
    for entry in _base_entries():
        for alpha in alphas:
            for seed in [0, 1, 2]:
                selected = _select_from_evalues(entry, alpha, seed, budget)
                metrics = _label_metrics(selected, budget)
                evalues = _method_evalues(entry, 0.10 if alpha not in [0.05, 0.20] else alpha, seed)
                max_e = float(pd.to_numeric(evalues.get("e_value", pd.Series(dtype=float)), errors="coerce").max()) if not evalues.empty else None
                rows.append(
                    {
                        "dataset": entry["dataset"],
                        "generator": entry["generator"],
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": budget,
                        "strategy": "coverage_conditional_parc",
                        "max_observed_e_reference": max_e,
                        **metrics,
                    }
                )
    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_alpha_frontier.csv")
    table.to_csv(out_csv, index=False)
    summary_csv = ensure_data_output(output_dir / "table_alpha_frontier_meanstd.csv")
    (
        table.groupby(["dataset", "generator", "alpha1", "strategy"], dropna=False)
        .agg(
            released_mean=("released", "mean"),
            nonempty_rate=("released", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) > 0).mean())),
            utr_mean=("utr", "mean"),
            conservative_ftr_mean=("conservative_ftr_uncertain_and_unlabeled_false", "mean"),
        )
        .reset_index()
        .to_csv(summary_csv, index=False)
    )
    result = {"status": "completed", "table": str(out_csv), "summary": str(summary_csv), "rows": len(table)}
    write_json(output_dir / "alpha_frontier_summary.json", result)
    return result


def run_ncalib_sensitivity(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_ncalib")
    n_values = [100, 200, 500, None]
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        cfg = _load_cfg(entry)
        universe = _load_universe_with_labels(cfg)
        for seed in [0, 1, 2]:
            split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), {**cfg, "splits": {**cfg.get("splits", {}), "seed": seed}})
            frame = universe.copy()
            frame["split"] = frame["video_id"].astype(int).map(split_map)
            cal = frame[frame["split"] == "cal"].copy()
            test = frame[frame["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).head(budget).copy()
            cal_video_ids_all = sorted(cal["video_id"].astype(int).unique().tolist())
            for n in n_values:
                selected_ids = cal_video_ids_all if n is None else cal_video_ids_all[: min(int(n), len(cal_video_ids_all))]
                _, pre_diag = _block_evalues(
                    test,
                    cal[cal["video_id"].astype(int).isin(selected_ids)],
                    selected_ids,
                    grid_size=1,
                    gamma=0.5,
                    remove_verified=True,
                    empty_block_policy="coverage_conditional",
                    alpha1=0.10,
                )
                gamma = pre_diag.get("gamma_star_eff") or 0.5
                eframe, diag = _block_evalues(
                    test,
                    cal[cal["video_id"].astype(int).isin(selected_ids)],
                    selected_ids,
                    grid_size=1,
                    gamma=gamma,
                    remove_verified=True,
                    empty_block_policy="coverage_conditional",
                    alpha1=0.10,
                )
                values = eframe["e_value"].fillna(0.0).astype(float).tolist()
                k, tau, margin = _scs_release_count(values, alpha1=0.10, candidate_budget_m=budget)
                rows.append(
                    {
                        "dataset": entry["dataset"],
                        "generator": entry["generator"],
                        "seed": seed,
                        "n_calib_requested": "full" if n is None else n,
                        "n_rank_denominator": diag.get("n_rank_denominator"),
                        "p_min_effective": diag.get("p_min_effective"),
                        "gamma_star_eff": diag.get("gamma_star_eff"),
                        "gamma_used": gamma,
                        "emax_effective": diag.get("emax_effective"),
                        "emax_gamma05": pre_diag.get("emax_effective"),
                        "candidate_budget_M": budget,
                        "released": int(k),
                        "tau_k": tau if k else None,
                        "self_consistency_margin": margin if k else None,
                    }
                )
    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_ncalib_sensitivity.csv")
    table.to_csv(out_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "rows": len(table)}
    write_json(output_dir / "ncalib_sensitivity_summary.json", result)
    return result


def run_runtime_report(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_runtime")
    rows = []
    for entry in _base_entries():
        matrix = _read_csv(entry["matrix"])
        if matrix.empty:
            continue
        runtime_col = "runtime_sec" if "runtime_sec" in matrix else None
        rows.append(
            {
                "dataset": entry["dataset"],
                "generator": entry["generator"],
                "matrix_csv": str(entry["matrix"]),
                "rows": len(matrix),
                "runtime_sec_sum": float(pd.to_numeric(matrix[runtime_col], errors="coerce").fillna(0).sum()) if runtime_col else None,
                "runtime_sec_mean": float(pd.to_numeric(matrix[runtime_col], errors="coerce").mean()) if runtime_col else None,
                "candidate_universe_rows": int(len(_read_csv(entry["candidate_universe"]))),
            }
        )
    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_runtime_report.csv")
    table.to_csv(out_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "rows": len(table)}
    write_json(output_dir / "runtime_report_summary.json", result)
    return result


def run_per_class_breakdown(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_per_class")
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        for alpha in [0.10, 0.20]:
            for seed in [0, 1, 2]:
                selected = _select_from_evalues(entry, alpha, seed, budget)
                if selected.empty:
                    continue
                supported = selected["is_matched_to_gt"].astype(bool) | selected["is_verified_positive"].astype(bool)
                selected = selected.copy()
                selected["supported_for_utr"] = supported
                group_cols = ["query", "category_id"]
                grouped = (
                    selected.groupby(group_cols, dropna=False)
                    .agg(
                        released=("path_id", "count"),
                        supported=("supported_for_utr", "sum"),
                        score_mean=("score", "mean"),
                        e_value_mean=("e_value", "mean"),
                    )
                    .reset_index()
                )
                grouped["unsupported"] = grouped["released"] - grouped["supported"]
                grouped["utr"] = grouped["unsupported"] / grouped["released"].clip(lower=1)
                grouped["dataset"] = entry["dataset"]
                grouped["generator"] = entry["generator"]
                grouped["alpha1"] = alpha
                grouped["seed"] = seed
                grouped["candidate_budget_M"] = budget
                rows.append(grouped)
    table = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    out_csv = ensure_data_output(output_dir / "table_per_class_breakdown.csv")
    table.to_csv(out_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "rows": len(table)}
    write_json(output_dir / "per_class_breakdown_summary.json", result)
    return result


def run_second_rater_sample(out_dir: str | Path | None = None, total: int = 100) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_second_rater")
    sources = [
        DATA_ROOT / "outputs/phase2/audit_labels.csv",
        DATA_ROOT / "outputs/phase3_tao_full/audit_labels.csv",
    ]
    frames = []
    for source in sources:
        frame = _read_csv(source)
        if not frame.empty:
            frames.append(frame)
    all_labels = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    if not all_labels.empty:
        sample = all_labels.sample(n=min(total, len(all_labels)), random_state=20260509)
    else:
        sample = all_labels
    out_csv = ensure_data_output(output_dir / "second_rater_sample.csv")
    template_csv = ensure_data_output(output_dir / "second_rater_labels_template.csv")
    sample.to_csv(out_csv, index=False)
    template = sample[[col for col in ["dataset", "video_id", "path_id", "query", "label", "verified_positive_for_calibration"] if col in sample]].copy()
    template = template.rename(columns={"label": "first_pass_label"})
    template["second_rater_label"] = ""
    template["second_rater_verified_positive_for_calibration"] = ""
    template["second_rater_reason"] = ""
    template["second_rater_confidence"] = ""
    template.to_csv(template_csv, index=False)
    result = {"status": "completed", "sample": str(out_csv), "template": str(template_csv), "rows": len(sample)}
    write_json(output_dir / "second_rater_sample_manifest.json", result)
    return result


def run_failure_manifest(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_failure_cases")
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        for alpha in [0.10, 0.20]:
            for seed in [0, 1, 2]:
                selected = _select_from_evalues(entry, alpha, seed, budget)
                if selected.empty:
                    continue
                bad = selected[
                    selected.get("label", pd.Series("", index=selected.index)).isin(["actually_false", "uncertain"])
                    | (~(selected["is_matched_to_gt"].astype(bool) | selected["is_verified_positive"].astype(bool)))
                ].copy()
                if not bad.empty:
                    bad["dataset"] = entry["dataset"]
                    bad["generator"] = entry["generator"]
                    bad["alpha1"] = alpha
                    bad["seed"] = seed
                    rows.append(bad.head(10))
    table = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    out_csv = ensure_data_output(output_dir / "failure_case_manifest.csv")
    table.to_csv(out_csv, index=False)
    result = {"status": "completed", "manifest": str(out_csv), "rows": len(table)}
    write_json(output_dir / "failure_case_manifest_summary.json", result)
    return result


def _load_gt_annotations(ann_file: Path, video_filter: set[int] | None = None) -> tuple[pd.DataFrame, dict[int, int]]:
    with ann_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    image_to_frame = {int(img["id"]): int(img.get("frame_index", img.get("frame_id", 0))) for img in data.get("images", [])}
    rows = []
    for ann in data.get("annotations", []):
        video_id = int(ann.get("video_id", -1))
        if video_filter is not None and video_id not in video_filter:
            continue
        bbox = ann.get("bbox", [0, 0, 0, 0])
        rows.append(
            {
                "video_id": video_id,
                "frame_index": image_to_frame.get(int(ann["image_id"]), 0),
                "track_id": int(ann.get("track_id", ann.get("id", 0))),
                "category_id": int(ann.get("category_id", -1)),
                "x": float(bbox[0]),
                "y": float(bbox[1]),
                "w": float(bbox[2]),
                "h": float(bbox[3]),
            }
        )
    return pd.DataFrame(rows), image_to_frame


def _iou_matrix(gt: pd.DataFrame, pred: pd.DataFrame) -> np.ndarray:
    if gt.empty or pred.empty:
        return np.empty((len(gt), len(pred)))
    g = gt[["x", "y", "w", "h"]].to_numpy(dtype=float)
    p = pred[["x", "y", "w", "h"]].to_numpy(dtype=float)
    gx2 = g[:, 0] + g[:, 2]
    gy2 = g[:, 1] + g[:, 3]
    px2 = p[:, 0] + p[:, 2]
    py2 = p[:, 1] + p[:, 3]
    out = np.zeros((len(g), len(p)), dtype=float)
    for i in range(len(g)):
        xx1 = np.maximum(g[i, 0], p[:, 0])
        yy1 = np.maximum(g[i, 1], p[:, 1])
        xx2 = np.minimum(gx2[i], px2)
        yy2 = np.minimum(gy2[i], py2)
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        union = g[i, 2] * g[i, 3] + p[:, 2] * p[:, 3] - inter
        out[i] = np.where(union > 0, inter / union, 0.0)
    return out


def _mot_eval_for_entry(entry: dict[str, Any], method: str, alpha: float, seed: int, budget: int) -> dict[str, Any]:
    try:
        import motmetrics as mm
    except Exception as exc:  # pragma: no cover
        return {"status": "motmetrics_missing", "error": str(exc)}
    selected = _select_from_evalues(entry, alpha, seed, budget) if method == "PARC" else pd.DataFrame()
    cfg = _load_cfg(entry)
    universe = _load_universe_with_labels(cfg)
    if method == "confidence_top_m":
        selected = _test_pool(cfg, universe, seed, budget).copy()
    if selected.empty:
        return {"num_predictions": 0, "idf1": None, "mota": None, "motp": None, "num_switches": None, "HOTA": None, "hota_note": "requires_trackeval"}
    selected_ids = set(selected["path_id"].astype(str))
    nodes = pd.read_csv(entry["candidate_nodes"])
    nodes = nodes[nodes["path_id"].astype(str).isin(selected_ids)].copy()
    if nodes.empty:
        return {"num_predictions": 0, "idf1": None, "mota": None, "motp": None, "num_switches": None, "HOTA": None, "hota_note": "requires_trackeval"}
    nodes = nodes.rename(columns={"bbox_x": "x", "bbox_y": "y", "bbox_w": "w", "bbox_h": "h"})
    video_ids = set(nodes["video_id"].astype(int).unique().tolist())
    gt, _ = _load_gt_annotations(Path(entry["ann_file"]), video_filter=video_ids)
    if entry["dataset"] == "TAO":
        # Supported subset: only evaluate categories that occur in selected predictions.
        cats = set(selected["category_id"].astype(int).unique().tolist())
        gt = gt[gt["category_id"].astype(int).isin(cats)].copy()
    accs = []
    names = []
    for video_id, vpred in nodes.groupby("video_id"):
        pred_id_map = {path_id: idx + 1 for idx, path_id in enumerate(sorted(vpred["path_id"].astype(str).unique().tolist()))}
        vpred = vpred.copy()
        vpred["pred_num_id"] = vpred["path_id"].astype(str).map(pred_id_map)
        vgt = gt[gt["video_id"].astype(int) == int(video_id)]
        if vgt.empty and vpred.empty:
            continue
        acc = mm.MOTAccumulator(auto_id=True)
        frames = sorted(set(vgt["frame_index"].astype(int).tolist()) | set(vpred["frame_index"].astype(int).tolist()))
        for frame_idx in frames:
            fg = vgt[vgt["frame_index"].astype(int) == int(frame_idx)]
            fp = vpred[vpred["frame_index"].astype(int) == int(frame_idx)].copy()
            gt_ids = fg["track_id"].astype(str).tolist()
            pred_ids = fp["pred_num_id"].astype(int).tolist()
            dists = 1.0 - _iou_matrix(fg, fp)
            if dists.size:
                dists[dists > 0.5] = np.nan
            acc.update(gt_ids, pred_ids, dists)
        accs.append(acc)
        names.append(str(video_id))
    mh = mm.metrics.create()
    summary = mh.compute_many(accs, names=names, metrics=["idf1", "mota", "motp", "num_switches", "precision", "recall"], generate_overall=True)
    overall = summary.loc["OVERALL"].to_dict() if "OVERALL" in summary.index else {}
    return {
        "num_predictions": int(len(nodes)),
        "idf1": float(overall.get("idf1")) if pd.notna(overall.get("idf1")) else None,
        "mota": float(overall.get("mota")) if pd.notna(overall.get("mota")) else None,
        "motp": float(overall.get("motp")) if pd.notna(overall.get("motp")) else None,
        "num_switches": float(overall.get("num_switches")) if pd.notna(overall.get("num_switches")) else None,
        "precision": float(overall.get("precision")) if pd.notna(overall.get("precision")) else None,
        "recall": float(overall.get("recall")) if pd.notna(overall.get("recall")) else None,
        "HOTA": None,
        "hota_note": "requires_trackeval",
    }


def run_mot_metrics(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_metrics")
    rows = []
    for entry in [e for e in _base_entries() if e["generator"] == "GroundingDINO"]:
        for method in ["PARC", "confidence_top_m"]:
            for alpha in [0.10, 0.20]:
                for seed in [0, 1, 2]:
                    start = time.perf_counter()
                    metrics = _mot_eval_for_entry(entry, method, alpha, seed, budget)
                    metrics["runtime_sec"] = time.perf_counter() - start
                    rows.append(
                        {
                            "dataset": entry["dataset"],
                            "generator": entry["generator"],
                            "method": method,
                            "alpha1": alpha,
                            "seed": seed,
                            "candidate_budget_M": budget,
                            **metrics,
                        }
                    )
    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_motmetrics.csv")
    table.to_csv(out_csv, index=False)
    result = {"status": "completed", "table": str(out_csv), "rows": len(table), "hota_status": "requires_trackeval"}
    write_json(output_dir / "motmetrics_summary.json", result)
    return result


def _normalize_yes_no(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return "yes"
    if text in {"0", "false", "no", "n"}:
        return "no"
    return ""


def _cohen_kappa(left: list[str], right: list[str]) -> float | None:
    if not left or len(left) != len(right):
        return None
    labels = sorted(set(left) | set(right))
    if not labels:
        return None
    n = len(left)
    observed = sum(1 for a, b in zip(left, right) if a == b) / n
    expected = 0.0
    for label in labels:
        expected += (left.count(label) / n) * (right.count(label) / n)
    if math.isclose(1.0 - expected, 0.0):
        return 1.0 if math.isclose(observed, 1.0) else None
    return float((observed - expected) / (1.0 - expected))


def _bootstrap_mean_ci(values: pd.Series, n_boot: int = 1000, seed: int = 20260509) -> dict[str, float | None]:
    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(arr) == 0:
        return {"mean": None, "std": None, "ci95_low": None, "ci95_high": None, "n": 0}
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    if len(arr) == 1:
        return {"mean": mean, "std": std, "ci95_low": mean, "ci95_high": mean, "n": int(len(arr))}
    rng = np.random.default_rng(seed)
    boot = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return {
        "mean": mean,
        "std": std,
        "ci95_low": float(np.quantile(boot, 0.025)),
        "ci95_high": float(np.quantile(boot, 0.975)),
        "n": int(len(arr)),
    }


def run_second_rater_agreement(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_second_rater")
    labels_path = output_dir / "second_rater_labels.csv"
    template_path = output_dir / "second_rater_labels_template.csv"
    source_path = labels_path if labels_path.exists() else template_path
    frame = _read_csv(source_path)
    if frame.empty:
        result = {"status": "missing_second_rater_template", "source": str(source_path)}
        write_json(output_dir / "second_rater_agreement_summary.json", result)
        pd.DataFrame([result]).to_csv(ensure_data_output(output_dir / "second_rater_agreement.csv"), index=False)
        pd.DataFrame().to_csv(ensure_data_output(output_dir / "second_rater_disagreements.csv"), index=False)
        return result

    second = frame.get("second_rater_label", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    first = frame.get("first_pass_label", frame.get("label", pd.Series("", index=frame.index))).fillna("").astype(str).str.strip()
    valid_labels = {"actually_true", "actually_false", "uncertain"}
    labeled_mask = second.isin(valid_labels) & first.isin(valid_labels)
    labeled = frame[labeled_mask].copy()
    n_sample = int(len(frame))
    n_labeled = int(len(labeled))
    if n_labeled:
        first_labels = labeled.get("first_pass_label", labeled.get("label")).astype(str).tolist()
        second_labels = labeled["second_rater_label"].astype(str).tolist()
        label_agreement = float(np.mean([a == b for a, b in zip(first_labels, second_labels)]))
        label_kappa = _cohen_kappa(first_labels, second_labels)
        first_verified = labeled.get("verified_positive_for_calibration", pd.Series("", index=labeled.index)).map(_normalize_yes_no).tolist()
        second_verified = labeled.get(
            "second_rater_verified_positive_for_calibration",
            pd.Series("", index=labeled.index),
        ).map(_normalize_yes_no).tolist()
        verified_valid = [(a, b) for a, b in zip(first_verified, second_verified) if a and b]
        verified_agreement = float(np.mean([a == b for a, b in verified_valid])) if verified_valid else None
        verified_kappa = _cohen_kappa([a for a, _ in verified_valid], [b for _, b in verified_valid]) if verified_valid else None
        status = "completed"
    else:
        label_agreement = None
        label_kappa = None
        verified_agreement = None
        verified_kappa = None
        status = "requires_independent_second_rater"

    disagreements = labeled[
        labeled.get("first_pass_label", labeled.get("label", pd.Series("", index=labeled.index))).astype(str)
        != labeled["second_rater_label"].astype(str)
    ].copy() if n_labeled else pd.DataFrame()
    disagreements_csv = ensure_data_output(output_dir / "second_rater_disagreements.csv")
    disagreements.to_csv(disagreements_csv, index=False)

    summary = {
        "status": status,
        "source": str(source_path),
        "n_sample": n_sample,
        "n_second_rater_labeled": n_labeled,
        "label_agreement": label_agreement,
        "cohen_kappa_label": label_kappa,
        "verified_positive_agreement": verified_agreement,
        "cohen_kappa_verified_positive": verified_kappa,
        "n_disagreements": int(len(disagreements)),
        "disagreements": str(disagreements_csv),
        "note": "Second-rater agreement is only an independent audit statistic when second_rater_label is filled by a separate annotator.",
    }
    summary_csv = ensure_data_output(output_dir / "second_rater_agreement.csv")
    pd.DataFrame([summary]).to_csv(summary_csv, index=False)
    write_json(output_dir / "second_rater_agreement_summary.json", summary)
    return summary


def run_statistical_confidence_tables(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_statistical_confidence")
    source = DATA_ROOT / "outputs/milestones/ijcv_cross_dataset_v6/table_cross_dataset_certification.csv"
    frame = _read_csv(source)
    if frame.empty:
        result = {"status": "missing_main_certification_table", "source": str(source)}
        write_json(output_dir / "statistical_confidence_summary.json", result)
        return result

    group_cols = ["dataset", "protocol", "method", "alpha1", "candidate_budget_M"]
    metric_cols = [
        "released",
        "utr",
        "audited_ftr_supported_plus_labeled",
        "conservative_ftr_uncertain_and_unlabeled_false",
        "self_consistency_margin",
    ]
    ci_rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(group_cols, dropna=False):
        base = dict(zip(group_cols, keys))
        for metric in metric_cols:
            if metric not in group:
                continue
            stats = _bootstrap_mean_ci(group[metric])
            ci_rows.append({"metric": metric, **base, **stats})
    ci_table = pd.DataFrame(ci_rows)
    ci_csv = ensure_data_output(output_dir / "table_main_bootstrap_ci.csv")
    ci_table.to_csv(ci_csv, index=False)

    worst = frame.copy()
    for column in ["released", "unsupported_actually_false", "unsupported_uncertain", "unsupported_unlabeled", "unsupported"]:
        if column not in worst:
            worst[column] = 0
        worst[column] = pd.to_numeric(worst[column], errors="coerce").fillna(0.0)
    denom = worst["released"].replace(0, np.nan)
    worst["unsupported_audited_count"] = (
        pd.to_numeric(worst.get("unsupported_actually_true", 0), errors="coerce").fillna(0.0)
        + worst["unsupported_actually_false"]
        + worst["unsupported_uncertain"]
    )
    worst["unsupported_audit_coverage"] = np.where(
        worst["unsupported"] > 0,
        worst["unsupported_audited_count"] / worst["unsupported"],
        1.0,
    )
    worst["worst_case_cons_ftr_all_unaudited_false"] = (
        worst["unsupported_actually_false"] + worst["unsupported_uncertain"] + worst["unsupported_unlabeled"]
    ) / denom
    worst["worst_case_cons_ftr_all_unaudited_false"] = worst["worst_case_cons_ftr_all_unaudited_false"].fillna(0.0)
    worst["passes_alpha_worst_case"] = worst["worst_case_cons_ftr_all_unaudited_false"] <= pd.to_numeric(
        worst["alpha1"], errors="coerce"
    ).fillna(0.0)
    keep_cols = [
        "dataset",
        "protocol",
        "method",
        "alpha1",
        "seed",
        "candidate_budget_M",
        "released",
        "unsupported",
        "unsupported_audit_coverage",
        "audited_ftr_supported_plus_labeled",
        "conservative_ftr_uncertain_and_unlabeled_false",
        "worst_case_cons_ftr_all_unaudited_false",
        "passes_alpha_worst_case",
    ]
    worst_csv = ensure_data_output(output_dir / "table_worst_case_cons_ftr.csv")
    worst[keep_cols].to_csv(worst_csv, index=False)

    caveat_path = ensure_data_output(output_dir / "audited_ftr_caveat.md")
    caveat_path.write_text(
        "Audited FTR is an empirical diagnostic on the supported-plus-audited released subset. "
        "It is not a verified upper bound on actual FTR. The formal certificate is the "
        "self-consistent e-value guarantee; conservative and worst-case FTR columns are reported "
        "to make the audit coverage assumptions explicit.\n",
        encoding="utf-8",
    )
    result = {
        "status": "completed",
        "source": str(source),
        "bootstrap_ci": str(ci_csv),
        "worst_case_ftr": str(worst_csv),
        "caveat": str(caveat_path),
        "rows": int(len(frame)),
    }
    write_json(output_dir / "statistical_confidence_summary.json", result)
    return result


def run_ijcv_stability_bundle(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/milestones/ijcv_stability_v1")
    stats_dir = ensure_data_output(output_dir / "statistical_confidence")
    second_dir = ensure_data_output(output_dir / "second_rater")

    # Generate fresh summary tables into their source directories, then copy the paper-facing files.
    second_summary = run_second_rater_agreement(DATA_ROOT / "outputs/phase4_second_rater")
    stats_summary = run_statistical_confidence_tables(DATA_ROOT / "outputs/phase4_statistical_confidence")

    copied: list[Path] = []
    sources = [
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_sample.csv",
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_labels_template.csv",
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_agreement.csv",
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_disagreements.csv",
        DATA_ROOT / "outputs/phase4_statistical_confidence/table_main_bootstrap_ci.csv",
        DATA_ROOT / "outputs/phase4_statistical_confidence/table_worst_case_cons_ftr.csv",
        DATA_ROOT / "outputs/phase4_statistical_confidence/audited_ftr_caveat.md",
        DATA_ROOT / "outputs/phase5_mondrian_ablation/table_mondrian_ablation_summary.csv",
        DATA_ROOT / "outputs/phase5_mondrian_ablation/table_mondrian_ablation.csv",
        DATA_ROOT / "outputs/phase4_per_class/table_per_class_breakdown.csv",
        DATA_ROOT / "outputs/phase4_runtime/table_runtime_report.csv",
        DATA_ROOT / "outputs/phase4_prop5_three_generator/table_prop5_three_generator.csv",
        DATA_ROOT / "outputs/phase4_prop5_three_generator/prop5_three_generator_by_seed.csv",
        DATA_ROOT / "outputs/phase6_metric_scope/table_hota_scope_meanstd.csv",
        DATA_ROOT / "outputs/phase6_metric_scope/table_alpha_controllability_meanstd.csv",
        DATA_ROOT / "outputs/phase6_metric_scope/table_tao_m_scaling_meanstd.csv",
        DATA_ROOT / "outputs/phase6_metric_scope/table_size_matched_baseline_meanstd.csv",
        DATA_ROOT / "docs/parc_track_formal_spec.md",
    ]
    for src in sources:
        dst = _copy_if_exists(src, output_dir)
        if dst is not None:
            copied.append(dst)

    # Keep an explicit subfolder copy for the two newly generated audit/statistics groups.
    for src in [
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_agreement.csv",
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_disagreements.csv",
    ]:
        dst = _copy_if_exists(src, second_dir)
        if dst is not None:
            copied.append(dst)
    for src in [
        DATA_ROOT / "outputs/phase4_statistical_confidence/table_main_bootstrap_ci.csv",
        DATA_ROOT / "outputs/phase4_statistical_confidence/table_worst_case_cons_ftr.csv",
        DATA_ROOT / "outputs/phase4_statistical_confidence/audited_ftr_caveat.md",
    ]:
        dst = _copy_if_exists(src, stats_dir)
        if dst is not None:
            copied.append(dst)

    manifest_rows = [{"file": str(path.relative_to(output_dir)), "sha256": _sha256(path), "bytes": path.stat().st_size} for path in copied]
    manifest_sha = ensure_data_output(output_dir / "MANIFEST_SHA256.txt")
    manifest_sha.write_text(
        "\n".join(f"{row['sha256']}  {row['file']}" for row in manifest_rows if row["sha256"]) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "ijcv_stability_v1",
        "contains_raw_data": False,
        "contains_model_weights": False,
        "contains_hf_cache": False,
        "second_rater_status": second_summary.get("status"),
        "second_rater_labeled": second_summary.get("n_second_rater_labeled"),
        "statistical_confidence_status": stats_summary.get("status"),
        "main_results_protocol": "fixed_M150_with_tune_fallback_and_best_M_diagnostic_separated",
        "idsw_status": "appendix_extension_not_full_certificate",
        "files": manifest_rows,
    }
    write_json(output_dir / "manifest.json", manifest)
    report = ensure_data_output(output_dir / "RUN_REPORT.md")
    report.write_text(
        "# IJCV Stability v1\n\n"
        "- Scope: second-rater status, bootstrap CI, worst-case Cons.FTR, Mondrian/per-class/runtime/Prop.5/metric-scope evidence.\n"
        f"- Second-rater status: `{second_summary.get('status')}` with `{second_summary.get('n_second_rater_labeled')}` labeled rows.\n"
        "- Audit note: audited FTR is an empirical audited-subset diagnostic, not an actual-FTR upper bound.\n"
        "- Raw videos, raw annotations, model weights, HF cache, and frame caches are excluded.\n",
        encoding="utf-8",
    )
    copied.extend([manifest_sha, output_dir / "manifest.json", report])

    packages = ensure_data_output(DATA_ROOT / "outputs/packages")
    package_path = packages / "ijcv_stability_v1.tar.gz"
    with tarfile.open(package_path, "w:gz") as tar:
        tar.add(output_dir, arcname=output_dir.name)
    package_sha = _sha256(package_path)
    (package_path.with_suffix(package_path.suffix + ".sha256")).write_text(
        f"{package_sha}  {package_path.name}\n",
        encoding="utf-8",
    )
    summary = {
        "status": "completed",
        "output_dir": str(output_dir),
        "manifest": str(output_dir / "manifest.json"),
        "package": str(package_path),
        "package_sha256": package_sha,
        "second_rater": second_summary,
        "statistical_confidence": stats_summary,
        "copied_files": len(copied),
    }
    write_json(output_dir / "ijcv_stability_summary.json", summary)
    return summary


def run_phase4_sprint(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_root = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase4_sprint")
    results = {
        "prop5": run_prop5_validation(output_root / "prop5"),
        "score_ablation": run_score_ablation(output_root / "score_ablation"),
        "owlv2_top_audit": run_owlv2_top_audit_sample(output_root / "owlv2_top_audit"),
        "alpha_frontier": run_alpha_frontier(output_root / "alpha_frontier"),
        "ncalib_sensitivity": run_ncalib_sensitivity(output_root / "ncalib_sensitivity"),
        "runtime": run_runtime_report(output_root / "runtime"),
        "per_class": run_per_class_breakdown(output_root / "per_class"),
        "second_rater": run_second_rater_sample(output_root / "second_rater"),
        "failure_cases": run_failure_manifest(output_root / "failure_cases"),
        "motmetrics": run_mot_metrics(output_root / "motmetrics"),
    }
    write_json(output_root / "phase4_sprint_summary.json", {"status": "completed", "results": results})
    return {"status": "completed", "output_root": str(output_root), "results": results}
