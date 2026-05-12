#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from pycocotools import mask as mask_utils


def _truthy_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.lower().isin(["true", "1", "yes"])


def _decode_rle(row: pd.Series) -> np.ndarray:
    size = json.loads(str(row["mask_rle_size"]))
    rle = {"size": size, "counts": str(row["mask_rle_counts"]).encode("ascii")}
    return mask_utils.decode(rle).astype(bool)


def _mask_iou(row_a: pd.Series, row_b: pd.Series) -> float:
    mask_a = _decode_rle(row_a)
    mask_b = _decode_rle(row_b)
    inter = np.logical_and(mask_a, mask_b).sum()
    union = np.logical_or(mask_a, mask_b).sum()
    return float(inter / union) if union else 0.0


def _build_conflict_graph(mask_nodes: pd.DataFrame, candidate_path_ids: set[str], threshold: float) -> dict[str, set[str]]:
    subset = mask_nodes[mask_nodes["path_id"].astype(str).isin(candidate_path_ids)].copy()
    graph: dict[str, set[str]] = {path_id: set() for path_id in candidate_path_ids}
    if subset.empty:
        return graph
    for _, group in subset.groupby("image_id", dropna=False):
        if group["path_id"].nunique() < 2:
            continue
        rows = list(group.iterrows())
        for idx_a in range(len(rows)):
            _, row_a = rows[idx_a]
            path_a = str(row_a["path_id"])
            for idx_b in range(idx_a + 1, len(rows)):
                _, row_b = rows[idx_b]
                path_b = str(row_b["path_id"])
                if path_a == path_b:
                    continue
                if _mask_iou(row_a, row_b) >= threshold:
                    graph.setdefault(path_a, set()).add(path_b)
                    graph.setdefault(path_b, set()).add(path_a)
    return graph


def _greedy_disjoint(ordered_paths: list[str], graph: dict[str, set[str]], limit: int | None = None) -> list[str]:
    selected: list[str] = []
    blocked: set[str] = set()
    for path_id in ordered_paths:
        if path_id in blocked:
            continue
        selected.append(path_id)
        blocked.update(graph.get(path_id, set()))
        if limit is not None and len(selected) >= limit:
            break
    return selected


def _conflict_aware_scs(
    evalues: pd.DataFrame,
    graph: dict[str, set[str]],
    alpha: float,
    m: int,
) -> tuple[list[str], float | None, float | None, int, float | None]:
    ordered = evalues.sort_values("e_value", ascending=False).copy()
    ordered_paths = ordered["path_id"].astype(str).tolist()
    e_map = dict(zip(ordered["path_id"].astype(str), pd.to_numeric(ordered["e_value"], errors="coerce").fillna(0.0)))
    best_mass_ratio = 0.0
    best_unconstrained_k = 0
    best_tau = None
    best_margin = None
    best_selected: list[str] = []
    max_k = min(m, len(ordered_paths))
    for k in range(max_k, 0, -1):
        tau = m / (alpha * k)
        eligible = [path_id for path_id in ordered_paths if e_map.get(path_id, 0.0) >= tau]
        disjoint = _greedy_disjoint(eligible, graph, limit=k)
        if len(eligible) >= k:
            e_at_k = float(pd.Series([e_map[p] for p in eligible]).sort_values(ascending=False).iloc[k - 1])
            best_mass_ratio = max(best_mass_ratio, alpha * k * e_at_k / m)
            best_unconstrained_k = max(best_unconstrained_k, k)
        if len(disjoint) >= k:
            selected = disjoint[:k]
            min_e = min(e_map[p] for p in selected) if selected else None
            return selected, tau, (min_e - tau if min_e is not None else None), best_unconstrained_k, best_mass_ratio
        if best_tau is None:
            best_tau = tau
            best_margin = (max([e_map[p] for p in eligible], default=0.0) - tau) if eligible else -tau
    return best_selected, best_tau, best_margin, best_unconstrained_k, best_mass_ratio


def _label_metrics(selected: pd.DataFrame, m: int) -> dict[str, object]:
    released = int(len(selected))
    if released == 0:
        return {
            "released": 0,
            "official_supported": 0,
            "unsupported": 0,
            "utr": 0.0,
            "conservative_ftr": 0.0,
            "recall_proxy": 0.0,
        }
    supported = _truthy_series(selected.get("is_matched_to_gt", pd.Series(False, index=selected.index))) | _truthy_series(
        selected.get("is_verified_positive", pd.Series(False, index=selected.index))
    )
    unsupported = selected[~supported]
    label = selected.get("label", pd.Series("", index=selected.index)).fillna("").astype(str)
    unsupported_label = unsupported.get("label", pd.Series("", index=unsupported.index)).fillna("").astype(str)
    conservative_false = int(unsupported_label.isin(["actually_false", "uncertain"]).sum()) + int((unsupported_label.str.strip() == "").sum())
    return {
        "released": released,
        "official_supported": int(supported.sum()),
        "unsupported": int(len(unsupported)),
        "utr": float(len(unsupported) / released),
        "conservative_ftr": float(conservative_false / released),
        "recall_proxy": float(released / max(1, m)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze LVVIS SAM mask-conflict certification.")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--mask-nodes", required=True)
    parser.add_argument("--evalue-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--thresholds", default="0.3,0.5,0.7")
    parser.add_argument("--m", type=int, default=150)
    parser.add_argument("--method", default="parc_track_gamma_tuned_uniform_scs")
    args = parser.parse_args()

    universe = pd.read_csv(args.universe)
    mask_nodes = pd.read_csv(args.mask_nodes)
    universe["path_id"] = universe["path_id"].astype(str)
    mask_nodes["path_id"] = mask_nodes["path_id"].astype(str)
    if "is_verified_positive" not in universe:
        universe["is_verified_positive"] = universe.get("verified_positive_for_calibration", "no")
    alphas = [float(v) for v in args.alphas.split(",") if v]
    seeds = [int(v) for v in args.seeds.split(",") if v]
    thresholds = [float(v) for v in args.thresholds.split(",") if v]
    evalue_dir = Path(args.evalue_dir)

    rows: list[dict[str, object]] = []
    for alpha in alphas:
        alpha_token = str(alpha).replace(".", "p")
        for seed in seeds:
            epath = evalue_dir / f"candidate_evalues_alpha{alpha_token}_seed{seed}.csv"
            if not epath.exists():
                rows.append({"alpha1": alpha, "seed": seed, "status": "missing_evalues", "candidate_evalues": str(epath)})
                continue
            evalues = pd.read_csv(epath)
            evalues = evalues[evalues["method"].astype(str).eq(args.method)].copy()
            evalues["path_id"] = evalues["path_id"].astype(str)
            evalues["e_value"] = pd.to_numeric(evalues["e_value"], errors="coerce").fillna(0.0)
            # Limit graph construction to paths that can matter for M=150 after sorting by e-value.
            candidate_paths = set(evalues.sort_values("e_value", ascending=False).head(max(args.m * 4, args.m))["path_id"].astype(str))
            for threshold in thresholds:
                graph = _build_conflict_graph(mask_nodes, candidate_paths, threshold)
                selected_ids, tau, margin, best_unconstrained_k, best_mass_ratio = _conflict_aware_scs(
                    evalues[evalues["path_id"].isin(candidate_paths)].copy(),
                    graph,
                    alpha=alpha,
                    m=args.m,
                )
                selected = universe[universe["path_id"].isin(selected_ids)].copy()
                metrics = _label_metrics(selected, args.m)
                edge_count = sum(len(v) for v in graph.values()) // 2
                conflicted_paths = sum(1 for v in graph.values() if v)
                rows.append(
                    {
                        "dataset": "LVVIS",
                        "task": "LVVIS_SAM_mask_path_certification",
                        "paper_scope": "SAM_box_prompt_mask_benchmark_without_official_mask_gt",
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": args.m,
                        "mask_iou_threshold": threshold,
                        "mask_rows": int(len(mask_nodes)),
                        "mask_paths": int(mask_nodes["path_id"].nunique()),
                        "candidate_graph_paths": int(len(candidate_paths)),
                        "conflict_edges": int(edge_count),
                        "conflicted_paths": int(conflicted_paths),
                        "tau_k": tau,
                        "self_consistency_margin": margin,
                        "best_unconstrained_k": int(best_unconstrained_k),
                        "best_mass_ratio": float(best_mass_ratio),
                        "empty_reason": "" if metrics["released"] else "mask_conflict_or_high_e_mass_refusal",
                        "status": "completed",
                        **metrics,
                    }
                )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(json.dumps({"status": "completed", "out": str(out), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
