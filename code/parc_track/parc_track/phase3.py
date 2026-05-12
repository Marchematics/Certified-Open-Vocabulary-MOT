from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil
import time
from typing import Any

import pandas as pd
import yaml

from .adapters.datasets import ensure_data_output, inspect_dataset_from_config, load_yaml, write_json
from .phase2 import (
    AUDIT_LABEL_COLUMNS,
    RELEASE_AUDIT_COLUMNS,
    _block_evalues,
    _candidate_budgets,
    _coverage_diag_for_method,
    _empty_block_policy,
    _load_universe_with_labels,
    _method_specs_for_real_certify,
    _scs_release_count,
    _split_video_ids,
    emax_from_p,
    run_real_certify,
)


DATA_ROOT = Path(".")


def _safe_name(value: Any) -> str:
    return str(value).replace("/", "_").replace(" ", "_").replace(".", "p")


def _dataset_slug(cfg: dict[str, Any]) -> str:
    name = str(cfg.get("dataset", {}).get("name", "ovtb")).strip().lower()
    if "tao" in name:
        return "tao"
    if "ovt" in name or "ovtb" in name:
        return "ovtb"
    return "".join(ch if ch.isalnum() else "_" for ch in name).strip("_") or "dataset"


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    out = ensure_data_output(path)
    with out.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return out


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def _label_metrics(selected: pd.DataFrame, candidate_budget_m: int, runtime_sec: float = 0.0) -> dict[str, Any]:
    released = int(len(selected))
    if released == 0:
        return {
            "released": 0,
            "official_supported": 0,
            "unsupported": 0,
            "utr": 0.0,
            "audited_ftr_on_labeled_released": None,
            "conservative_ftr_uncertain_and_unlabeled_false": None,
            "recall_proxy": 0.0,
            "runtime_sec": runtime_sec,
        }
    supported = selected["is_matched_to_gt"].astype(bool) | selected["is_verified_positive"].astype(bool)
    unsupported = selected[~supported]
    labeled = selected[selected["label"].isin(["actually_true", "actually_false"])].copy()
    false_count = int((labeled["label"] == "actually_false").sum())
    unsupported_false = int((unsupported["label"] == "actually_false").sum())
    unsupported_uncertain = int((unsupported["label"] == "uncertain").sum())
    unsupported_unlabeled = int((unsupported["label"].fillna("").astype(str).str.strip() == "").sum())
    conservative_false = unsupported_false + unsupported_uncertain + unsupported_unlabeled
    return {
        "released": released,
        "official_supported": int(supported.sum()),
        "unsupported": int(len(unsupported)),
        "utr": float(len(unsupported) / released),
        "audited_ftr_on_labeled_released": float(false_count / len(labeled)) if len(labeled) else None,
        "conservative_ftr_uncertain_and_unlabeled_false": float(conservative_false / released),
        "recall_proxy": float(released / max(1, candidate_budget_m)),
        "runtime_sec": runtime_sec,
    }


def _select_bh(pvalues: list[float], alpha1: float, candidate_budget_m: int) -> list[int]:
    ordered = sorted(range(len(pvalues)), key=lambda idx: pvalues[idx])
    selected_k = 0
    for rank, idx in enumerate(ordered, start=1):
        if pvalues[idx] <= alpha1 * rank / max(1, candidate_budget_m):
            selected_k = rank
    return ordered[:selected_k]


def _select_e_self_consistent(evalues: list[float], alpha1: float, candidate_budget_m: int) -> tuple[list[int], float | None, float | None]:
    k, tau, margin = _scs_release_count(evalues, alpha1=alpha1, candidate_budget_m=candidate_budget_m)
    ordered = sorted(range(len(evalues)), key=lambda idx: evalues[idx], reverse=True)
    return ordered[:k], tau if k else None, margin if k else None


def _additional_baseline_rows(
    cfg: dict[str, Any],
    evalue_path: Path,
    alpha1: float,
    seed: int,
    budgets: list[int],
) -> list[dict[str, Any]]:
    universe = _load_universe_with_labels(cfg)
    if universe.empty:
        return []
    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), cfg)
    universe["split"] = universe["video_id"].astype(int).map(split_map)
    cal = universe[universe["split"] == "cal"].copy()
    test = universe[universe["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    null_scores = cal.loc[cal["is_unmatched"].astype(bool) & ~cal["is_verified_positive"].astype(bool), "score"].astype(float).tolist()
    if not null_scores:
        null_scores = cal["score"].astype(float).tolist() or [1.0]

    evalues = _read_csv_if_exists(evalue_path)
    parc_e_map: dict[str, float] = {}
    if not evalues.empty and "method" in evalues:
        parc = evalues[evalues["method"].astype(str) == "parc_track_gamma_tuned_uniform_scs"].copy()
        if not parc.empty:
            parc_e_map = dict(zip(parc["path_id"], pd.to_numeric(parc["e_value"], errors="coerce").fillna(0.0)))

    rows: list[dict[str, Any]] = []
    for budget in budgets:
        pool = test.head(int(budget)).copy()
        scores = pool["score"].astype(float).tolist()
        p_track = []
        for score in scores:
            exceed = sum(1 for value in null_scores if float(value) >= float(score))
            p_track.append((1.0 + exceed) / (len(null_scores) + 1.0))
        gamma = 0.5
        track_e = [gamma * (p ** (gamma - 1.0)) if p > 0 else 0.0 for p in p_track]
        parc_e = [float(parc_e_map.get(path_id, 0.0)) for path_id in pool["path_id"]]
        score_threshold = float(pd.Series(null_scores, dtype=float).quantile(max(0.0, min(1.0, 1.0 - alpha1))))

        selectors: list[tuple[str, list[int], float | None, float | None, str]] = []
        selectors.append(
            (
                "confidence_threshold",
                [idx for idx, score in enumerate(scores) if score >= score_threshold],
                None,
                None,
                "score_threshold_from_calibration_null_quantile",
            )
        )
        selectors.append(("tracklet_p_bh", _select_bh(p_track, alpha1, budget), None, None, "tracklet_level_p_bh"))
        e_idx, e_tau, e_margin = _select_e_self_consistent(track_e, alpha1, budget)
        selectors.append(("tracklet_e_bh", e_idx, e_tau, e_margin, "tracklet_level_e_self_consistency"))
        pe_idx, pe_tau, pe_margin = _select_e_self_consistent(parc_e, alpha1, budget)
        selectors.append(("post_filter_e_bh", pe_idx, pe_tau, pe_margin, "block_evalue_post_filter"))
        selectors.append(("greedy_score_no_risk", list(range(len(pool))), None, None, "top_m_by_score_no_risk_control"))

        for method, selected_idx, tau, margin, note in selectors:
            start = time.perf_counter()
            selected = pool.iloc[selected_idx].copy() if selected_idx else pool.iloc[[]].copy()
            metrics = _label_metrics(selected, budget, runtime_sec=time.perf_counter() - start)
            rows.append(
                {
                    "method": method,
                    "method_family": "diagnostic_baseline",
                    "alpha1": alpha1,
                    "seed": seed,
                    "candidate_budget_M": int(budget),
                    "tau_k": tau,
                    "self_consistency_margin": margin,
                    "empty_diagnostic": "" if metrics["released"] else "baseline_selected_empty",
                    "baseline_note": note,
                    **metrics,
                }
            )
    return rows


def _normalize_cert_rows(frame: pd.DataFrame, alpha1: float, seed: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    out["seed"] = seed
    out["alpha1"] = alpha1
    out["method_family"] = "certified_or_core_baseline"
    if "runtime_sec" not in out:
        out["runtime_sec"] = None
    if "recall_proxy" not in out:
        out["recall_proxy"] = pd.to_numeric(out.get("released", 0), errors="coerce").fillna(0.0) / out[
            "candidate_budget_M"
        ].clip(lower=1)
    if "conservative_ftr_uncertain_and_unlabeled_false" not in out:
        out["conservative_ftr_uncertain_and_unlabeled_false"] = None
    return out


def _combined_audit_labels(cfg: dict[str, Any], output_dir: Path) -> str:
    input_cfg = cfg.get("input", {})
    label_paths = [input_cfg.get("audit_labels")] + list(input_cfg.get("extra_audit_labels", []) or [])
    frames = []
    for value in label_paths:
        if not value:
            continue
        path = Path(value)
        if path.exists() and path.stat().st_size > 0:
            frame = pd.read_csv(path)
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return str(input_cfg.get("audit_labels", ""))
    combined = pd.concat(frames, ignore_index=True, sort=False)
    for column in ["dataset", "video_id", "path_id"]:
        if column not in combined:
            combined[column] = ""
    combined = combined.drop_duplicates(["dataset", "video_id", "path_id"], keep="last")
    out = ensure_data_output(output_dir / "combined_audit_labels.csv")
    combined.to_csv(out, index=False)
    return str(out)


def run_ovtb_matrix(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    matrix = cfg.get("matrix", {})
    alphas = [float(value) for value in matrix.get("alpha1", [cfg.get("risk", {}).get("alpha1", 0.10)])]
    seeds = [int(value) for value in matrix.get("seeds", [cfg.get("splits", {}).get("seed", 0)])]
    budgets = [int(value) for value in matrix.get("candidate_budget_M", _candidate_budgets(cfg))]
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", DATA_ROOT / "outputs/phase3_ovtb"))
    config_dir = ensure_data_output(output_dir / "run_configs")
    combined_labels = _combined_audit_labels(cfg, output_dir)
    rows: list[pd.DataFrame] = []

    for alpha1 in alphas:
        for seed in seeds:
            run_cfg = json.loads(json.dumps(cfg))
            run_cfg.setdefault("risk", {})["alpha1"] = alpha1
            run_cfg.setdefault("splits", {})["seed"] = seed
            run_cfg.setdefault("selector", {})["candidate_budget_sweep"] = budgets
            if combined_labels:
                run_cfg.setdefault("input", {})["audit_labels"] = combined_labels
            run_name = f"alpha{_safe_name(alpha1)}_seed{seed}"
            run_cfg.setdefault("output", {})
            run_cfg["output"].update(
                {
                    "summary": str(output_dir / f"real_cert_{run_name}.json"),
                    "real_cert_summary": str(output_dir / f"real_cert_{run_name}.csv"),
                    "candidate_evalues": str(output_dir / f"candidate_evalues_{run_name}.csv"),
                    "cell_effective_n": str(output_dir / f"cell_effective_n_{run_name}.csv"),
                    "per_video_candidate_coverage": str(output_dir / f"per_video_candidate_coverage_{run_name}.csv"),
                }
            )
            run_cfg_path = _write_yaml(config_dir / f"{run_name}.yaml", run_cfg)
            run_real_certify(run_cfg_path)
            cert = _normalize_cert_rows(pd.read_csv(run_cfg["output"]["real_cert_summary"]), alpha1, seed)
            extra = pd.DataFrame(
                _additional_baseline_rows(
                    run_cfg,
                    Path(run_cfg["output"]["candidate_evalues"]),
                    alpha1=alpha1,
                    seed=seed,
                    budgets=budgets,
                )
            )
            rows.append(pd.concat([cert, extra], ignore_index=True, sort=False))

    combined = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    dataset_slug = _dataset_slug(cfg)
    matrix_csv = ensure_data_output(output_dir / f"{dataset_slug}_alpha_seed_m_matrix.csv")
    combined.to_csv(matrix_csv, index=False)
    legacy_matrix_csv = output_dir / "ovtb_alpha_seed_m_matrix.csv"
    if dataset_slug != "ovtb":
        combined.to_csv(ensure_data_output(legacy_matrix_csv), index=False)

    baseline_csv = ensure_data_output(output_dir / "table_baseline_expanded.csv")
    combined.to_csv(baseline_csv, index=False)
    alpha_csv = ensure_data_output(output_dir / "table_alpha_sweep.csv")
    alpha_cols = ["method", "alpha1", "candidate_budget_M"]
    if not combined.empty:
        grouped = (
            combined.groupby(alpha_cols, dropna=False)
            .agg(
                released_mean=("released", "mean"),
                released_std=("released", "std"),
                utr_mean=("utr", "mean"),
                conservative_ftr_mean=("conservative_ftr_uncertain_and_unlabeled_false", "mean"),
                margin_mean=("self_consistency_margin", "mean"),
                nonempty_rate=("released", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) > 0).mean())),
            )
            .reset_index()
        )
    else:
        grouped = pd.DataFrame()
    grouped.to_csv(alpha_csv, index=False)

    summary = {
        "status": "completed",
        "matrix_csv": str(matrix_csv),
        "baseline_csv": str(baseline_csv),
        "alpha_sweep_csv": str(alpha_csv),
        "rows": int(len(combined)),
        "alphas": alphas,
        "seeds": seeds,
        "candidate_budget_M": budgets,
    }
    write_json(output_dir / "ovtb_matrix_summary.json", summary)
    return summary


def export_matrix_release_audit_candidates(
    config_path: str | Path,
    unsupported_only: bool = True,
    out_csv: str | Path | None = None,
    labels_out: str | Path | None = None,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    matrix = cfg.get("matrix", {})
    audit_cfg = cfg.get("release_audit", {})
    alphas = [float(value) for value in audit_cfg.get("alpha1", matrix.get("alpha1", [cfg.get("risk", {}).get("alpha1", 0.10)]))]
    seeds = [int(value) for value in audit_cfg.get("seeds", matrix.get("seeds", [cfg.get("splits", {}).get("seed", 0)]))]
    budget = int(audit_cfg.get("candidate_budget_M", 150))
    method = str(audit_cfg.get("method", "parc_track_gamma_tuned_uniform_scs"))
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", DATA_ROOT / "outputs/phase3_ovtb"))
    combined_labels = _combined_audit_labels(cfg, output_dir)
    run_cfg_base = json.loads(json.dumps(cfg))
    if combined_labels:
        run_cfg_base.setdefault("input", {})["audit_labels"] = combined_labels

    universe = _load_universe_with_labels(run_cfg_base)
    if universe.empty:
        raise RuntimeError("cannot export release audit: candidate universe is empty or missing")
    rows: list[dict[str, Any]] = []
    manifest_runs: list[dict[str, Any]] = []
    for alpha1 in alphas:
        for seed in seeds:
            run_name = f"alpha{_safe_name(alpha1)}_seed{seed}"
            evalue_path = output_dir / f"candidate_evalues_{run_name}.csv"
            if not evalue_path.exists():
                manifest_runs.append(
                    {
                        "alpha1": alpha1,
                        "seed": seed,
                        "status": "missing_candidate_evalues",
                        "candidate_evalues": str(evalue_path),
                    }
                )
                continue
            evalues = pd.read_csv(evalue_path)
            if evalues.empty or "method" not in evalues:
                manifest_runs.append({"alpha1": alpha1, "seed": seed, "status": "empty_candidate_evalues"})
                continue
            method_evalues = evalues[evalues["method"].astype(str) == method].copy()
            if method_evalues.empty:
                manifest_runs.append({"alpha1": alpha1, "seed": seed, "status": "missing_method", "method": method})
                continue
            run_cfg = json.loads(json.dumps(run_cfg_base))
            run_cfg.setdefault("risk", {})["alpha1"] = alpha1
            run_cfg.setdefault("splits", {})["seed"] = seed
            split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), run_cfg)
            scoped = universe.copy()
            scoped["split"] = scoped["video_id"].astype(int).map(split_map)
            test = scoped[scoped["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
            pool = test.head(budget).copy()
            method_evalues["e_value"] = pd.to_numeric(method_evalues["e_value"], errors="coerce").fillna(0.0)
            for column in ("p_any", "p_block"):
                if column in method_evalues:
                    method_evalues[column] = pd.to_numeric(method_evalues[column], errors="coerce")
                else:
                    method_evalues[column] = None
            value_map = method_evalues.set_index("path_id")[["e_value", "p_any", "p_block"]].to_dict(orient="index")
            pool_values = [float(value_map.get(path_id, {}).get("e_value", 0.0)) for path_id in pool["path_id"]]
            k, tau, margin = _scs_release_count(pool_values, alpha1=alpha1, candidate_budget_m=budget)
            selected_positions = sorted(range(len(pool_values)), key=lambda idx: pool_values[idx], reverse=True)[:k]
            selected = pool.iloc[selected_positions].copy() if selected_positions else pool.iloc[[]].copy()
            released_total = int(len(selected))
            if unsupported_only and not selected.empty:
                selected = selected[
                    (~selected["is_matched_to_gt"].astype(bool)) & (~selected["is_verified_positive"].astype(bool))
                ].copy()
            exported = 0
            needs_audit = 0
            for release_rank, (_, row) in enumerate(selected.iterrows(), start=1):
                path_id = str(row["path_id"])
                ev = value_map.get(path_id, {})
                label = str(row.get("label", "") or "").strip()
                row_needs_audit = label not in {"actually_true", "actually_false", "uncertain"}
                needs_audit += int(row_needs_audit)
                audit_row = {
                    "dataset": row.get("dataset", cfg.get("dataset", {}).get("name", "")),
                    "video_id": row.get("video_id", ""),
                    "path_id": path_id,
                    "query": row.get("query", ""),
                    "category_id": row.get("category_id", ""),
                    "score": row.get("score", ""),
                    "objectness": row.get("objectness", row.get("score", "")),
                    "semantic_margin": row.get("semantic_margin", row.get("score", "")),
                    "temporal_stability": row.get("temporal_stability", ""),
                    "association_score": row.get("association_score", ""),
                    "matched_gt_id": row.get("matched_gt_id", ""),
                    "matched_iou": row.get("matched_iou", ""),
                    "temporal_overlap": row.get("temporal_overlap", ""),
                    "is_unmatched": row.get("is_unmatched", ""),
                    "cell_id": row.get("cell_id", ""),
                    "novelty_bin": row.get("novelty_bin", ""),
                    "query_cluster": row.get("query_cluster", ""),
                    "occ_bin": row.get("occ_bin", ""),
                    "domain_bin": row.get("domain_bin", ""),
                    "frame_start": row.get("frame_start", ""),
                    "frame_end": row.get("frame_end", ""),
                    "clip_path": "",
                    "montage_path": "",
                    "method": method,
                    "candidate_budget_M": budget,
                    "selected_rank": release_rank,
                    "e_value": ev.get("e_value", ""),
                    "p_any": ev.get("p_any", ""),
                    "p_block": ev.get("p_block", ""),
                    "tau_k": tau if k else "",
                    "self_consistency_margin": margin if k else "",
                    "release_source": str(evalue_path),
                    "alpha1": alpha1,
                    "seed": seed,
                    "audit_label": label,
                    "needs_audit": row_needs_audit,
                    "verified_positive_for_calibration": row.get("verified_positive_for_calibration", ""),
                }
                rows.append(audit_row)
                exported += 1
            manifest_runs.append(
                {
                    "alpha1": alpha1,
                    "seed": seed,
                    "status": "completed",
                    "method": method,
                    "candidate_budget_M": budget,
                    "released_total": released_total,
                    "exported_rows": exported,
                    "needs_audit_rows": needs_audit,
                    "unsupported_only": unsupported_only,
                    "tau_k": tau if k else None,
                    "self_consistency_margin": margin if k else None,
                    "candidate_evalues": str(evalue_path),
                }
            )

    default_name = "release_audit_fixed_M150_unsupported.csv" if unsupported_only else "release_audit_fixed_M150.csv"
    out = ensure_data_output(out_csv or audit_cfg.get("out", output_dir / default_name))
    base_columns = RELEASE_AUDIT_COLUMNS + ["alpha1", "seed", "audit_label", "needs_audit", "verified_positive_for_calibration"]
    pd.DataFrame(rows, columns=base_columns).to_csv(out, index=False)
    labels_path = ensure_data_output(labels_out or audit_cfg.get("labels_out", out.with_name(out.stem + "_labels.csv")))
    label_rows = []
    for row in rows:
        if not row.get("needs_audit"):
            continue
        label_rows.append(
            {
                "dataset": row["dataset"],
                "video_id": row["video_id"],
                "path_id": row["path_id"],
                "label": "",
                "reason": "",
                "auditor": "",
                "confidence": "",
                "review_status": "",
                "verified_positive_for_calibration": "",
            }
        )
    pd.DataFrame(label_rows, columns=AUDIT_LABEL_COLUMNS).to_csv(labels_path, index=False)
    manifest_path = ensure_data_output(out.with_name(out.stem + "_manifest.json"))
    manifest = {
        "status": "completed",
        "config": str(config_path),
        "method": method,
        "candidate_budget_M": budget,
        "alphas": alphas,
        "seeds": seeds,
        "unsupported_only": unsupported_only,
        "release_audit_csv": str(out),
        "label_template_csv": str(labels_path),
        "rows": int(len(rows)),
        "needs_audit_rows": int(len(label_rows)),
        "runs": manifest_runs,
    }
    write_json(manifest_path, manifest)
    manifest["manifest"] = str(manifest_path)
    return manifest


def run_cross_generator_report(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", DATA_ROOT / "outputs/milestones/cross_generator"))
    generators = cfg.get("generators", [])
    fixed_m = int(cfg.get("reporting", {}).get("fixed_M", 150))
    method = str(cfg.get("reporting", {}).get("method", "parc_track_gamma_tuned_uniform_scs"))
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for entry in generators:
        matrix_path = Path(entry.get("matrix_csv", ""))
        if not matrix_path.exists():
            missing.append(str(matrix_path))
            continue
        frame = pd.read_csv(matrix_path)
        if frame.empty:
            continue
        scoped = frame[
            (frame["method"].astype(str) == method)
            & (pd.to_numeric(frame["candidate_budget_M"], errors="coerce") == fixed_m)
        ].copy()
        if scoped.empty:
            continue
        scoped["alpha1_num"] = pd.to_numeric(scoped["alpha1"], errors="coerce")
        for alpha, group in scoped.groupby("alpha1_num", dropna=True):
            released = pd.to_numeric(group["released"], errors="coerce").fillna(0.0)
            supported = pd.to_numeric(group.get("official_supported", 0), errors="coerce").fillna(0.0)
            margins = pd.to_numeric(group.get("self_consistency_margin", None), errors="coerce")
            rows.append(
                {
                    "Dataset": entry.get("dataset", ""),
                    "Generator": entry.get("generator", ""),
                    "Alpha": float(alpha),
                    "Non-empty seeds": int((released > 0).sum()),
                    "Seeds": int(group["seed"].nunique()) if "seed" in group else int(len(group)),
                    "Released": float(released.mean()),
                    "Rel./M": float((released / max(fixed_m, 1)).mean()),
                    "Supported": float(supported.mean()),
                    "Supp./M": float((supported / max(fixed_m, 1)).mean()),
                    "UTR": float(pd.to_numeric(group.get("utr", 0), errors="coerce").fillna(0.0).mean()),
                    "Audited FTR": float(
                        pd.to_numeric(group.get("audited_ftr_on_labeled_released", 0), errors="coerce").dropna().mean()
                    )
                    if pd.to_numeric(group.get("audited_ftr_on_labeled_released", pd.Series(dtype=float)), errors="coerce").dropna().size
                    else None,
                    "Conservative FTR": float(
                        pd.to_numeric(
                            group.get("conservative_ftr_uncertain_and_unlabeled_false", 0),
                            errors="coerce",
                        )
                        .fillna(0.0)
                        .mean()
                    ),
                    "Margin": float(margins.dropna().mean()) if margins.dropna().size else None,
                    "Matrix CSV": str(matrix_path),
                }
            )
    table = pd.DataFrame(
        rows,
        columns=[
            "Dataset",
            "Generator",
            "Alpha",
            "Non-empty seeds",
            "Seeds",
            "Released",
            "Rel./M",
            "Supported",
            "Supp./M",
            "UTR",
            "Audited FTR",
            "Conservative FTR",
            "Margin",
            "Matrix CSV",
        ],
    )
    table_csv = ensure_data_output(output_dir / "table_cross_generator.csv")
    table.to_csv(table_csv, index=False)
    table_tex = _to_latex(table_csv, output_dir / "table_cross_generator.tex")
    manifest = {
        "status": "completed" if not missing else "completed_with_missing_inputs",
        "config": str(config_path),
        "table_cross_generator_csv": str(table_csv),
        "table_cross_generator_tex": table_tex,
        "rows": int(len(table)),
        "missing_inputs": missing,
        "fixed_M": fixed_m,
        "method": method,
    }
    write_json(output_dir / "cross_generator_manifest.json", manifest)
    return manifest


def _core_method_ids() -> list[str]:
    return [str(spec["method"]) for spec in _method_specs_for_real_certify()]


def _diagnostic_method_ids() -> list[str]:
    return [
        "confidence_threshold",
        "tracklet_p_bh",
        "tracklet_e_bh",
        "post_filter_e_bh",
        "greedy_score_no_risk",
    ]


def _select_m_from_tune_split(
    cfg: dict[str, Any],
    alpha1: float,
    seed: int,
    budgets: list[int],
    method: dict[str, Any],
) -> dict[str, Any]:
    universe = _load_universe_with_labels(cfg)
    if universe.empty:
        return {
            "selection_status": "missing_candidate_universe",
            "selected_M_by_tune": int(cfg.get("tune_selection", {}).get("fallback_M", 150)),
        }
    split_cfg = json.loads(json.dumps(cfg))
    split_cfg.setdefault("splits", {})["seed"] = seed
    outer = _split_video_ids(universe["video_id"].astype(int).tolist(), split_cfg)
    universe["outer_split"] = universe["video_id"].astype(int).map(outer)
    tune = universe[universe["outer_split"] == "tune"].copy()
    tune_videos = sorted(tune["video_id"].astype(int).unique().tolist())
    fallback_m = int(cfg.get("tune_selection", {}).get("fallback_M", 150))
    if len(tune_videos) < 4:
        return {
            "selection_status": "insufficient_tune_videos",
            "selected_M_by_tune": fallback_m,
            "tune_video_count": len(tune_videos),
        }
    internal_cal_ratio = float(cfg.get("tune_selection", {}).get("internal_cal_ratio", 0.50))
    internal_cfg = {"splits": {"tune_ratio": 0.0, "cal_ratio": internal_cal_ratio, "seed": seed + 7919}}
    internal = _split_video_ids(tune_videos, internal_cfg)
    tune["inner_split"] = tune["video_id"].astype(int).map(internal)
    tune_cal = tune[tune["inner_split"] == "cal"].copy()
    tune_val = tune[tune["inner_split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    cal_video_ids = sorted(tune_cal["video_id"].astype(int).unique().tolist())
    grid_size = len(cfg.get("release_grid", {}).get("times_sec", [2.0]))
    policy = _empty_block_policy(cfg)
    pre_diag = _coverage_diag_for_method(
        cal=tune_cal,
        cal_video_ids=cal_video_ids,
        grid_size=grid_size,
        remove_verified=bool(method["remove_verified"]),
        empty_block_policy=policy,
        alpha1=alpha1,
    )
    gamma = 0.5 if method["gamma_mode"] == "fixed_0.5" else (pre_diag["gamma_star_eff"] or 0.5)
    evalues, diag = _block_evalues(
        test=tune_val,
        cal=tune_cal,
        cal_video_ids=cal_video_ids,
        grid_size=grid_size,
        gamma=float(gamma),
        remove_verified=bool(method["remove_verified"]),
        empty_block_policy=policy,
        alpha1=alpha1,
    )
    e_map = dict(zip(evalues["path_id"], pd.to_numeric(evalues["e_value"], errors="coerce").fillna(0.0))) if not evalues.empty else {}
    candidates = []
    for budget in budgets:
        pool = tune_val.head(int(budget)).copy()
        values = [float(e_map.get(path_id, 0.0)) for path_id in pool["path_id"]]
        released, tau, margin = _scs_release_count(values, alpha1=alpha1, candidate_budget_m=int(budget))
        candidates.append(
            {
                "M": int(budget),
                "released": int(released),
                "tau": tau,
                "margin": margin,
                "max_e": max(values) if values else None,
            }
        )
    feasible = [row for row in candidates if int(row["released"]) > 0 and row["margin"] is not None and float(row["margin"]) >= 0.0]
    if feasible:
        best = sorted(feasible, key=lambda row: (int(row["released"]), float(row["margin"]), -int(row["M"])), reverse=True)[0]
        status = "selected_feasible_release_max"
    else:
        best_margin = max(candidates, key=lambda row: float(row["margin"]) if row["margin"] is not None else -1e18) if candidates else {"M": fallback_m, "released": 0, "tau": None, "margin": None, "max_e": None}
        best = {"M": fallback_m, "released": 0, "tau": best_margin.get("tau"), "margin": best_margin.get("margin"), "max_e": best_margin.get("max_e")}
        status = "no_feasible_M_on_tune_fallback"
    return {
        "selection_status": status,
        "selected_M_by_tune": int(best["M"]),
        "selection_metric": "feasible_first_release_max",
        "selection_protocol": "tune_split_only_internal_cal_val",
        "tune_video_count": len(tune_videos),
        "tune_internal_cal_videos": len(cal_video_ids),
        "tune_internal_val_videos": int(tune_val["video_id"].astype(int).nunique()) if not tune_val.empty else 0,
        "tune_released": int(best.get("released") or 0),
        "tune_margin": best.get("margin"),
        "tune_tau": best.get("tau"),
        "tune_max_e": best.get("max_e"),
        "gamma": gamma,
        "p_min_effective": diag.get("p_min_effective"),
        "emax_effective": diag.get("emax_effective"),
        "n_covered": diag.get("n_covered"),
        "n_rank_denominator": diag.get("n_rank_denominator"),
    }


def run_tuned_m_selection(config_path: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    matrix = cfg.get("matrix", {})
    alphas = [float(value) for value in matrix.get("alpha1", [cfg.get("risk", {}).get("alpha1", 0.10)])]
    seeds = [int(value) for value in matrix.get("seeds", [cfg.get("splits", {}).get("seed", 0)])]
    budgets = [int(value) for value in matrix.get("candidate_budget_M", _candidate_budgets(cfg))]
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", DATA_ROOT / "outputs/phase3_ovtb"))
    out = ensure_data_output(out_path or cfg.get("tune_selection", {}).get("out", output_dir / "tuned_m_selection.csv"))
    rows: list[dict[str, Any]] = []
    parc_selection: dict[tuple[float, int], dict[str, Any]] = {}
    for alpha1 in alphas:
        for seed in seeds:
            for method in _method_specs_for_real_certify():
                selected = _select_m_from_tune_split(cfg, alpha1=alpha1, seed=seed, budgets=budgets, method=method)
                row = {
                    "alpha": alpha1,
                    "alpha1": alpha1,
                    "seed": seed,
                    "method": method["method"],
                    "selected_M": selected["selected_M_by_tune"],
                    "selected_M_by_tune": selected["selected_M_by_tune"],
                    **selected,
                }
                rows.append(row)
                if method["method"] == "parc_track_gamma_tuned_uniform_scs":
                    parc_selection[(alpha1, seed)] = row
            shared = parc_selection.get((alpha1, seed))
            for method_id in _diagnostic_method_ids():
                selected_m = int(shared["selected_M_by_tune"]) if shared else int(cfg.get("tune_selection", {}).get("fallback_M", 150))
                shared_status = str(shared.get("selection_status", "missing_parc_selection")) if shared else "missing_parc_selection"
                rows.append(
                    {
                        "alpha": alpha1,
                        "alpha1": alpha1,
                        "seed": seed,
                        "method": method_id,
                        "selected_M": selected_m,
                        "selected_M_by_tune": selected_m,
                        "selection_metric": "shared_parc_feasible_first_release_max",
                        "selection_protocol": "shared_parc_tune_split_only",
                        "selection_status": f"shared_from_parc_full:{shared_status}",
                        "tune_released": shared.get("tune_released") if shared else None,
                        "tune_margin": shared.get("tune_margin") if shared else None,
                    }
                )
    pd.DataFrame(rows).to_csv(out, index=False)
    summary = {"status": "completed", "tuned_m_selection_csv": str(out), "rows": len(rows), "alphas": alphas, "seeds": seeds, "budgets": budgets}
    write_json(out.with_suffix(".json"), summary)
    return summary



def _read_idsw_events(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"video_id", "frame_index", "gt_id", "pred_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"IDSW event file missing columns: {sorted(missing)}")
    if "variant" not in frame:
        frame["variant"] = "tracker"
    frame["pred_id"] = frame["pred_id"].fillna("").astype(str)
    return frame


def evaluate_clear_mot_idsw(events: pd.DataFrame, fps: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for (variant, video_id), group in events.sort_values(["frame_index", "gt_id"]).groupby(["variant", "video_id"]):
        last_pred: dict[str, str] = {}
        idsw = 0
        for _, row in group.iterrows():
            pred_id = str(row["pred_id"]).strip()
            if not pred_id or pred_id.lower() in {"none", "nan", "empty"}:
                continue
            gt_id = str(row["gt_id"])
            old = last_pred.get(gt_id)
            if old is not None and old != pred_id:
                idsw += 1
            last_pred[gt_id] = pred_id
        frames = int(pd.to_numeric(group["frame_index"], errors="coerce").max() or 0) + 1
        minutes = max(frames / max(fps, 1e-12) / 60.0, 1e-12)
        badlink = float(group["badlink_ub"].sum()) if "badlink_ub" in group else float(idsw)
        misscont = float(group["misscont_ub"].sum()) if "misscont_ub" in group else 0.0
        gap = float(group["gap_sensor"].sum()) if "gap_sensor" in group else 0.0
        ub = badlink + misscont + gap
        actual_per_min = idsw / minutes
        ub_per_min = ub / minutes
        rows.append(
            {
                "variant": variant,
                "video_id": video_id,
                "actual_idsw": idsw,
                "minutes": minutes,
                "actual_idsw_per_min": actual_per_min,
                "badlink_ub": badlink,
                "misscont_ub": misscont,
                "gap_sensor": gap,
                "certified_ub": ub,
                "certified_ub_per_min": ub_per_min,
                "tightness": ub / idsw if idsw > 0 else None,
                "tightness_denominator_zero": idsw == 0,
                "IDF1": float(group["IDF1"].mean()) if "IDF1" in group else None,
                "HOTA": float(group["HOTA"].mean()) if "HOTA" in group else None,
            }
        )
    per_video = pd.DataFrame(rows)
    if per_video.empty:
        return per_video, pd.DataFrame()
    summary = (
        per_video.groupby("variant", dropna=False)
        .agg(
            videos=("video_id", "nunique"),
            actual_idsw=("actual_idsw", "sum"),
            actual_idsw_per_min=("actual_idsw_per_min", "mean"),
            badlink_ub=("badlink_ub", "sum"),
            misscont_ub=("misscont_ub", "sum"),
            gap_sensor=("gap_sensor", "sum"),
            certified_ub=("certified_ub", "sum"),
            certified_ub_per_min=("certified_ub_per_min", "mean"),
            tightness_median=("tightness", "median"),
            tightness_mean=("tightness", "mean"),
            zero_denominator_videos=("tightness_denominator_zero", "sum"),
            IDF1=("IDF1", "mean"),
            HOTA=("HOTA", "mean"),
        )
        .reset_index()
    )
    return per_video, summary


def run_idsw_eval(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    events_path = Path(cfg.get("input", {}).get("idsw_events", ""))
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", DATA_ROOT / "outputs/phase3_idsw"))
    if not events_path.exists():
        summary = {"status": "requires_idsw_events", "reason": f"missing {events_path}", "events": str(events_path)}
        write_json(output_dir / "idsw_eval_summary.json", summary)
        return summary
    fps = float(cfg.get("evaluator", {}).get("fps", 30.0))
    per_video, summary_frame = evaluate_clear_mot_idsw(_read_idsw_events(events_path), fps=fps)
    per_video_csv = ensure_data_output(output_dir / "idsw_per_video.csv")
    summary_csv = ensure_data_output(output_dir / "idsw_summary.csv")
    per_video.to_csv(per_video_csv, index=False)
    summary_frame.to_csv(summary_csv, index=False)
    summary = {
        "status": "completed",
        "idsw_per_video_csv": str(per_video_csv),
        "idsw_summary_csv": str(summary_csv),
        "rows": int(len(per_video)),
    }
    write_json(output_dir / "idsw_eval_summary.json", summary)
    return summary


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_latex(csv_path: Path, out_path: Path) -> str | None:
    if not csv_path.exists():
        return None
    frame = pd.read_csv(csv_path)
    out = ensure_data_output(out_path)
    with out.open("w", encoding="utf-8") as handle:
        handle.write(frame.to_latex(index=False, escape=False))
    return str(out)


def _mean_std(series: pd.Series) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return ""
    mean = float(values.mean())
    std = float(values.std()) if len(values) > 1 else 0.0
    return f"{mean:.4g} ± {std:.4g}"


def _derive_matrix_tables(matrix_path: Path, output_dir: Path, cfg: dict[str, Any]) -> list[Path]:
    if not matrix_path.exists():
        return []
    frame = pd.read_csv(matrix_path)
    if frame.empty:
        return []
    reporting = cfg.get("reporting", {})
    fixed_m = int(reporting.get("fixed_main_M", 150))
    main_alpha = float(reporting.get("main_alpha1", 0.10))
    derived: list[Path] = []

    # This is intentionally labeled fixed-M. It is paper-safe before a true tune-selected M file exists.
    fixed = frame[
        (pd.to_numeric(frame["candidate_budget_M"], errors="coerce") == fixed_m)
        & ((pd.to_numeric(frame["alpha1"], errors="coerce") - main_alpha).abs() < 1e-12)
    ].copy()
    fixed["selection_protocol"] = "fixed_M_protocol_not_tune_selected"
    fixed_out = ensure_data_output(output_dir / "table_main_fixed_m.csv")
    fixed.to_csv(fixed_out, index=False)
    derived.append(fixed_out)

    tune_selection_path = reporting.get("tuned_m_selection")
    tuned_out = ensure_data_output(output_dir / "table_main_tuned_m.csv")
    if tune_selection_path and Path(tune_selection_path).exists():
        selection = pd.read_csv(tune_selection_path)
        rows = []
        for _, sel in selection.iterrows():
            alpha = float(sel["alpha1"])
            seed = int(sel["seed"])
            method = str(sel["method"])
            selected_m = int(sel["selected_M_by_tune"])
            match = frame[
                ((pd.to_numeric(frame["alpha1"], errors="coerce") - alpha).abs() < 1e-12)
                & (pd.to_numeric(frame["seed"], errors="coerce") == seed)
                & (frame["method"].astype(str) == method)
                & (pd.to_numeric(frame["candidate_budget_M"], errors="coerce") == selected_m)
            ].copy()
            if not match.empty:
                status = str(sel.get("selection_status", ""))
                protocol = "tune_fallback_M" if "fallback" in status else "tune_selected_M"
                match["selection_protocol"] = protocol
                for column in (
                    "selected_M",
                    "selected_M_by_tune",
                    "selection_metric",
                    "selection_status",
                    "tune_released",
                    "tune_margin",
                    "tune_tau",
                    "tune_max_e",
                    "tune_video_count",
                    "tune_internal_cal_videos",
                    "tune_internal_val_videos",
                ):
                    if column in sel:
                        match[column] = sel[column]
                rows.append(match)
        tuned = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    else:
        tuned = fixed.copy()
        tuned["selection_protocol"] = "requires_tune_selection_using_fixed_M_placeholder"
        tuned["selection_warning"] = (
            "Do not present as tuned-M main result until reporting.tuned_m_selection points to a tune-derived selection file."
        )
    tuned.to_csv(tuned_out, index=False)
    derived.append(tuned_out)

    best_rows = []
    metric = pd.to_numeric(frame["released"], errors="coerce").fillna(0)
    tmp = frame.copy()
    tmp["_released_num"] = metric
    tmp["_cons_ftr"] = pd.to_numeric(tmp.get("conservative_ftr_uncertain_and_unlabeled_false"), errors="coerce").fillna(1e9)
    for (alpha, seed, method), group in tmp.groupby(["alpha1", "seed", "method"], dropna=False):
        best = group.sort_values(["_released_num", "_cons_ftr", "candidate_budget_M"], ascending=[False, True, True]).iloc[0].copy()
        best["best_M_on_test_grid"] = best["candidate_budget_M"]
        best["diagnostic_only"] = True
        best_rows.append(best)
    best_diag = pd.DataFrame(best_rows).drop(columns=[c for c in ["_released_num", "_cons_ftr"] if c in pd.DataFrame(best_rows)], errors="ignore")
    best_out = ensure_data_output(output_dir / "table_best_m_diagnostic.csv")
    best_diag.to_csv(best_out, index=False)
    derived.append(best_out)

    empty_cols = [
        "alpha1",
        "seed",
        "method",
        "candidate_budget_M",
        "n_cal_total",
        "n_covered",
        "n_rank_denominator",
        "p_min_effective",
        "gamma",
        "gamma_star_eff",
        "emax_effective",
        "max_observed_e",
        "best_margin",
        "empty_diagnostic",
    ]
    empty = frame[pd.to_numeric(frame["released"], errors="coerce").fillna(0) == 0].copy()
    empty_out = ensure_data_output(output_dir / "table_seed_empty_diagnostics.csv")
    empty[[c for c in empty_cols if c in empty.columns]].to_csv(empty_out, index=False)
    derived.append(empty_out)

    agg = (
        frame.groupby(["method", "alpha1", "candidate_budget_M"], dropna=False)
        .agg(
            released=("released", _mean_std),
            utr=("utr", _mean_std),
            conservative_ftr=("conservative_ftr_uncertain_and_unlabeled_false", _mean_std),
            margin=("self_consistency_margin", _mean_std),
            nonempty_rate=("released", lambda s: f"{float((pd.to_numeric(s, errors='coerce').fillna(0) > 0).mean()):.3f}"),
        )
        .reset_index()
    )
    alpha_out = ensure_data_output(output_dir / "table_alpha_sweep_meanstd.csv")
    agg.to_csv(alpha_out, index=False)
    derived.append(alpha_out)

    baseline = frame[
        (pd.to_numeric(frame["candidate_budget_M"], errors="coerce") == fixed_m)
        & ((pd.to_numeric(frame["alpha1"], errors="coerce") - main_alpha).abs() < 1e-12)
    ].copy()
    baseline_agg = (
        baseline.groupby(["method"], dropna=False)
        .agg(
            released=("released", _mean_std),
            utr=("utr", _mean_std),
            conservative_ftr=("conservative_ftr_uncertain_and_unlabeled_false", _mean_std),
            margin=("self_consistency_margin", _mean_std),
            nonempty_rate=("released", lambda s: f"{float((pd.to_numeric(s, errors='coerce').fillna(0) > 0).mean()):.3f}"),
        )
        .reset_index()
    )
    baseline_out = ensure_data_output(output_dir / "table_baseline_expanded_meanstd.csv")
    baseline_agg.to_csv(baseline_out, index=False)
    derived.append(baseline_out)
    return derived


def run_release_core_report(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", DATA_ROOT / "outputs/milestones/core_results"))
    docs_out = ensure_data_output(cfg.get("output", {}).get("docs_summary", DATA_ROOT / "docs/paper_results_summary.md"))
    source_paths = [Path(path) for path in cfg.get("sources", [])]
    copied: list[str] = []
    latex: list[str] = []
    for src in source_paths:
        if src.exists() and src.is_file():
            dst = ensure_data_output(output_dir / src.name)
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            copied.append(str(dst))
            if dst.suffix.lower() == ".csv":
                tex = _to_latex(dst, output_dir / "latex" / f"{dst.stem}.tex")
                if tex:
                    latex.append(tex)
    matrix_path = Path(cfg.get("matrix_csv", DATA_ROOT / "outputs/phase3_ovtb/ovtb_alpha_seed_m_matrix.csv"))
    for table in _derive_matrix_tables(matrix_path, output_dir, cfg):
        copied.append(str(table))
        tex = _to_latex(table, output_dir / "latex" / f"{table.stem}.tex")
        if tex:
            latex.append(tex)
    manifest = {
        "status": "completed",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "copied_files": copied,
        "latex_tables": latex,
        "hashes": {str(Path(path).name): _sha256(Path(path)) for path in copied},
    }
    tuned_table = output_dir / "table_main_tuned_m.csv"
    if tuned_table.exists():
        try:
            tuned_frame = pd.read_csv(tuned_table)
            protocols = sorted(tuned_frame.get("selection_protocol", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
            manifest["contains_tuned_m_main_result"] = bool(protocols) and all("requires_tune_selection" not in value for value in protocols)
            manifest["tuned_m_protocols"] = protocols
            statuses = sorted(tuned_frame.get("selection_status", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
            manifest["tuned_m_selection_statuses"] = statuses
            manifest["tuned_m_has_fallbacks"] = any("fallback" in value for value in statuses + protocols)
        except Exception:
            manifest["contains_tuned_m_main_result"] = False
            manifest["tuned_m_protocols"] = []
            manifest["tuned_m_selection_statuses"] = []
            manifest["tuned_m_has_fallbacks"] = False
    manifest["contains_best_m_diagnostic"] = (output_dir / "table_best_m_diagnostic.csv").exists()
    manifest["contains_fixed_m_main_result"] = (output_dir / "table_main_fixed_m.csv").exists()
    manifest["contains_alpha_sweep"] = (output_dir / "table_alpha_sweep_meanstd.csv").exists()
    manifest["contains_baseline_meanstd"] = (output_dir / "table_baseline_expanded_meanstd.csv").exists()
    write_json(output_dir / "manifest.json", manifest)
    lines = [
        "# PARC-Track Paper Results Summary",
        "",
        "This summary freezes the current release-core evidence bundle. GroundingDINO proposals are treated as a scaffold generator, not a final OVMOT backbone claim.",
        "",
        "## Frozen Files",
    ]
    for path in copied:
        lines.append(f"- `{Path(path).name}`")
    lines.extend(["", "## Next Required Evidence", "- OVT-B alpha/M/seed matrix.", "- TAO/OV-TAO transfer audit/certification.", "- CLEAR-MOT IDSW real evaluator table."])
    docs_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest["docs_summary"] = str(docs_out)
    return manifest
