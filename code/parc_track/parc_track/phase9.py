from __future__ import annotations

import csv
import hashlib
import json
import os
import tarfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output, write_json


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
VALID_AUDIT_LABELS = {"actually_true", "actually_false", "uncertain"}
FALSE_TAXONOMY = (
    "background_hallucination",
    "wrong_category",
    "id_drift",
    "multi_object_merge",
    "part_box",
    "temporal_fragment",
    "other_false",
)


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


def _copy_if_exists(src: str | Path, dst_dir: Path, name: str | None = None) -> Path | None:
    import shutil

    src = Path(src)
    if not src.exists() or not src.is_file():
        return None
    dst = ensure_data_output(dst_dir / (name or src.name))
    if src.resolve() == dst.resolve():
        return dst
    shutil.copy2(src, dst)
    return dst


def _key_frame(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("dataset", "video_id", "path_id"):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)
    return frame


def _load_label_pool() -> pd.DataFrame:
    sources = [
        DATA_ROOT / "outputs/phase3_ovtb_full/combined_audit_labels.csv",
        DATA_ROOT / "outputs/phase3_tao_full/audit_labels.csv",
        DATA_ROOT / "outputs/phase7_burst/combined_audit_labels.csv",
        DATA_ROOT / "outputs/phase7_burst_owlv2/combined_audit_labels.csv",
        DATA_ROOT / "outputs/phase4_owlv2_top_audit/owlv2_top150_mini_audit_labels.csv",
        DATA_ROOT / "outputs/phase4_ovtb_owlvit/combined_audit_labels.csv",
        DATA_ROOT / "outputs/phase4_tao_owlvit/combined_audit_labels.csv",
    ]
    frames: list[pd.DataFrame] = []
    for source in sources:
        frame = _read_csv(source)
        if frame.empty:
            continue
        frame = _key_frame(frame)
        frame["label_source"] = str(source)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    labels = pd.concat(frames, ignore_index=True, sort=False)
    labels["label"] = labels.get("label", "").fillna("").astype(str).str.strip()
    labels = labels[labels["label"].isin(VALID_AUDIT_LABELS)].copy()
    labels = labels.drop_duplicates(["dataset", "video_id", "path_id"], keep="last")
    return labels


def _candidate_sources() -> list[dict[str, Any]]:
    return [
        {
            "dataset": "OVT-B",
            "generator": "GroundingDINO",
            "candidate_universe": DATA_ROOT / "outputs/phase2_1000/candidate_universe.csv",
            "audit_candidates": DATA_ROOT / "outputs/phase2_500/audit_candidates.csv",
            "target": 700,
        },
        {
            "dataset": "TAO",
            "generator": "GroundingDINO",
            "candidate_universe": DATA_ROOT / "outputs/phase3_tao_full/candidate_universe.csv",
            "audit_candidates": DATA_ROOT / "outputs/phase3_tao_full/audit_candidates.csv",
            "target": 700,
        },
        {
            "dataset": "BURST",
            "generator": "GroundingDINO",
            "candidate_universe": DATA_ROOT / "outputs/phase7_burst/candidate_universe.csv",
            "audit_candidates": DATA_ROOT / "outputs/phase7_burst/audit_candidates.csv",
            "target": 600,
        },
    ]


def _bin_scores(frame: pd.DataFrame) -> pd.Series:
    scores = pd.to_numeric(frame.get("score", 0.0), errors="coerce").fillna(0.0)
    if len(scores) < 3 or scores.nunique() < 3:
        return pd.Series(["high"] * len(frame), index=frame.index)
    q_low = float(scores.quantile(1 / 3))
    q_high = float(scores.quantile(2 / 3))
    return pd.Series(
        np.where(scores >= q_high, "high", np.where(scores >= q_low, "mid", "low")),
        index=frame.index,
    )


def _taxonomy_from_reason(reason: Any) -> str:
    text = str(reason or "").lower()
    if any(token in text for token in ("wrong_category", "adult_or_nonbaby", "category")):
        return "wrong_category"
    if any(token in text for token in ("drift", "switch")):
        return "id_drift"
    if any(token in text for token in ("merge", "multi")):
        return "multi_object_merge"
    if any(token in text for token in ("part", "partial")):
        return "part_box"
    if any(token in text for token in ("temporal", "fragment")):
        return "temporal_fragment"
    if any(token in text for token in ("background", "hallucination", "texture", "shadow")):
        return "background_hallucination"
    return "other_false"


def run_audit_benchmark_industrialization(
    out_dir: str | Path | None = None,
    *,
    total: int = 2000,
    second_rater_total: int = 300,
) -> dict[str, Any]:
    """Build the journal-scale audit benchmark scaffold without fabricating labels."""
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase9_audit_benchmark")
    labels = _load_label_pool()
    labels = _key_frame(labels) if not labels.empty else labels
    label_cols = [
        "dataset",
        "video_id",
        "path_id",
        "label",
        "reason",
        "auditor",
        "confidence",
        "review_status",
        "verified_positive_for_calibration",
    ]
    selected_frames: list[pd.DataFrame] = []
    audit_lookup_frames: list[pd.DataFrame] = []
    for source in _candidate_sources():
        universe = _read_csv(source["candidate_universe"])
        if universe.empty:
            continue
        universe = _key_frame(universe)
        universe["dataset"] = source["dataset"]
        universe["generator"] = source["generator"]
        audit_candidates = _read_csv(source["audit_candidates"])
        if not audit_candidates.empty:
            audit_candidates = _key_frame(audit_candidates)
            audit_lookup_frames.append(
                audit_candidates[["dataset", "video_id", "path_id", "montage_path", "clip_path"]].copy()
                if {"montage_path", "clip_path"}.issubset(audit_candidates.columns)
                else audit_candidates[["dataset", "video_id", "path_id"]].copy()
            )
        unmatched = universe[universe.get("is_unmatched", True).astype(str).str.lower().isin(["true", "1", "yes"])].copy()
        unmatched["score_bin"] = _bin_scores(unmatched)
        target = int(source["target"])
        per_bin = max(1, target // 3)
        parts = []
        for score_bin in ("high", "mid", "low"):
            part = unmatched[unmatched["score_bin"] == score_bin].sort_values("score", ascending=False).head(per_bin)
            parts.append(part)
        dataset_sample = pd.concat(parts, ignore_index=True, sort=False).drop_duplicates("path_id")
        if len(dataset_sample) < target:
            extra = unmatched[~unmatched["path_id"].isin(dataset_sample["path_id"])].sort_values("score", ascending=False)
            dataset_sample = pd.concat([dataset_sample, extra.head(target - len(dataset_sample))], ignore_index=True, sort=False)
        selected_frames.append(dataset_sample.head(target))
    benchmark = pd.concat(selected_frames, ignore_index=True, sort=False) if selected_frames else pd.DataFrame()
    if len(benchmark) > total:
        benchmark = benchmark.sort_values(["dataset", "score_bin", "score"], ascending=[True, True, False]).head(total)
    audit_lookup = pd.concat(audit_lookup_frames, ignore_index=True, sort=False) if audit_lookup_frames else pd.DataFrame()
    if not audit_lookup.empty:
        audit_lookup = _key_frame(audit_lookup).drop_duplicates(["dataset", "video_id", "path_id"], keep="last")
        benchmark = benchmark.merge(audit_lookup, on=["dataset", "video_id", "path_id"], how="left")
    if not labels.empty:
        benchmark = benchmark.merge(labels[label_cols + ["label_source"]], on=["dataset", "video_id", "path_id"], how="left")
        for column in label_cols[3:] + ["label_source"]:
            label_side = f"{column}_y"
            candidate_side = f"{column}_x"
            if label_side in benchmark.columns:
                benchmark[column] = benchmark[label_side].combine_first(
                    benchmark[candidate_side] if candidate_side in benchmark.columns else pd.Series(index=benchmark.index, dtype=object)
                )
            elif candidate_side in benchmark.columns and column not in benchmark.columns:
                benchmark[column] = benchmark[candidate_side]
        suffix_cols = [
            column
            for column in benchmark.columns
            if column.endswith("_x") or column.endswith("_y")
        ]
        if suffix_cols:
            benchmark = benchmark.drop(columns=suffix_cols)
    else:
        for column in label_cols[3:] + ["label_source"]:
            benchmark[column] = ""
    benchmark["label_status"] = np.where(benchmark["label"].fillna("").astype(str).isin(VALID_AUDIT_LABELS), "existing_gold", "requires_label")
    benchmark["audit_source"] = np.where(benchmark["label_status"].eq("existing_gold"), "existing_labeled", "score_spectrum_expansion")
    benchmark["sampling_protocol"] = "dataset_quota_score_bin_high_mid_low"
    candidate_cols = [
        "dataset",
        "generator",
        "video_id",
        "path_id",
        "query",
        "category_id",
        "score",
        "score_bin",
        "is_unmatched",
        "matched_gt_id",
        "matched_iou",
        "temporal_overlap",
        "frame_start",
        "frame_end",
        "path_length",
        "candidate_rank",
        "cell_id",
        "audit_source",
        "label_status",
        "montage_path",
        "clip_path",
        "sampling_protocol",
    ]
    for column in candidate_cols:
        if column not in benchmark:
            benchmark[column] = ""
    candidates_csv = ensure_data_output(output_dir / "audit_benchmark_candidates.csv")
    benchmark[candidate_cols].to_csv(candidates_csv, index=False)

    label_frame = benchmark[["dataset", "video_id", "path_id"]].copy()
    for column in label_cols[3:]:
        label_frame[column] = benchmark.get(column, "")
    verified_raw = label_frame["verified_positive_for_calibration"].fillna("").astype(str).str.lower()
    label_frame["verified_positive_for_calibration"] = np.where(
        label_frame["label"].astype(str).eq("actually_true") & verified_raw.isin(["yes", "true", "1"]),
        "yes",
        "no",
    )
    label_frame["label_status"] = benchmark["label_status"]
    label_frame["label_source"] = benchmark.get("label_source", "")
    labels_csv = ensure_data_output(output_dir / "audit_labels_gold.csv")
    label_frame.to_csv(labels_csv, index=False)
    pending_csv = ensure_data_output(output_dir / "audit_expansion_pending_labels.csv")
    label_frame[label_frame["label_status"].eq("requires_label")].to_csv(pending_csv, index=False)

    false_rows = label_frame[label_frame["label"].astype(str).eq("actually_false")].copy()
    false_rows["error_taxonomy"] = false_rows.get("reason", "").map(_taxonomy_from_reason)
    taxonomy_csv = ensure_data_output(output_dir / "audit_error_taxonomy.csv")
    if false_rows.empty:
        pd.DataFrame(columns=["error_taxonomy", "count", "fraction"]).to_csv(taxonomy_csv, index=False)
    else:
        counts = false_rows["error_taxonomy"].value_counts().rename_axis("error_taxonomy").reset_index(name="count")
        counts["fraction"] = counts["count"] / counts["count"].sum()
        counts.to_csv(taxonomy_csv, index=False)

    labeled = label_frame[label_frame["label"].isin(VALID_AUDIT_LABELS)].copy()
    second_ref = labeled.sort_values(["dataset", "label", "path_id"]).head(second_rater_total).copy()
    second_ref_csv = ensure_data_output(output_dir / "second_rater_300_reference_do_not_share.csv")
    second_ref.to_csv(second_ref_csv, index=False)
    blind = second_ref[["dataset", "video_id", "path_id"]].merge(
        benchmark[candidate_cols],
        on=["dataset", "video_id", "path_id"],
        how="left",
    )
    blind["second_rater_label"] = ""
    blind["second_rater_verified_positive_for_calibration"] = ""
    blind["second_rater_reason"] = ""
    blind["second_rater_confidence"] = ""
    blind_csv = ensure_data_output(output_dir / "second_rater_300_blind_template.csv")
    blind.to_csv(blind_csv, index=False)

    protocol = ensure_data_output(output_dir / "audit_protocol.md")
    protocol.write_text(
        "# PARC-Track Audit Protocol v2\n\n"
        "- Labels: `actually_true`, `actually_false`, `uncertain` only.\n"
        "- `verified_positive_for_calibration=yes` only when the path is a high-precision one-sided positive.\n"
        "- Uncertain remains unverified and must not be removed from the null superset.\n"
        "- False taxonomy tags: "
        + ", ".join(FALSE_TAXONOMY)
        + ".\n"
        "- The blind second-rater template must be filled by an independent annotator; do not copy first-pass labels.\n",
        encoding="utf-8",
    )
    summary_rows = []
    for dataset, group in benchmark.groupby("dataset", dropna=False):
        labels_group = label_frame[label_frame["dataset"].astype(str).eq(str(dataset))]
        summary_rows.append(
            {
                "dataset": dataset,
                "rows": int(len(group)),
                "existing_gold": int(group["label_status"].eq("existing_gold").sum()),
                "pending": int(group["label_status"].eq("requires_label").sum()),
                "actually_true": int(labels_group["label"].eq("actually_true").sum()),
                "actually_false": int(labels_group["label"].eq("actually_false").sum()),
                "uncertain": int(labels_group["label"].eq("uncertain").sum()),
                "verified_positive": int(labels_group["verified_positive_for_calibration"].fillna("").astype(str).str.lower().isin(["yes", "true", "1"]).sum()),
            }
        )
    summary_csv = ensure_data_output(output_dir / "audit_benchmark_summary.csv")
    pd.DataFrame(summary_rows).to_csv(summary_csv, index=False)
    result = {
        "status": "completed_with_pending_labels" if int((label_frame["label_status"] == "requires_label").sum()) else "completed",
        "target_rows": int(total),
        "rows": int(len(benchmark)),
        "existing_gold_rows": int((label_frame["label_status"] == "existing_gold").sum()),
        "pending_rows": int((label_frame["label_status"] == "requires_label").sum()),
        "second_rater_template_rows": int(len(blind)),
        "candidates": str(candidates_csv),
        "audit_labels_gold": str(labels_csv),
        "pending_labels": str(pending_csv),
        "second_rater_blind_template": str(blind_csv),
        "second_rater_reference_do_not_share": str(second_ref_csv),
        "taxonomy": str(taxonomy_csv),
        "protocol": str(protocol),
        "summary": str(summary_csv),
    }
    write_json(output_dir / "audit_benchmark_manifest.json", result)
    return result


def run_reliability_stress_suite(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase9_reliability_stress")
    sources = [
        DATA_ROOT / "outputs/milestones/cross_dataset/table_cross_dataset_certification_meanstd.csv",
        DATA_ROOT / "outputs/milestones/burst/table_burst_certification_summary.csv",
        DATA_ROOT / "outputs/milestones/stability/table_mondrian_ablation_summary.csv",
        DATA_ROOT / "outputs/phase7_burst/table_burst_prop5_mass_ratio.csv",
    ]
    copied = []
    for source in sources:
        dst = _copy_if_exists(source, output_dir)
        if dst:
            copied.append(dst)

    # True custom-split non-exchangeability experiments require rerunning
    # certification with fixed non-random splits. We expose the exact design and
    # leave result fields empty rather than fabricating assumption violations.
    stress_rows = []
    for dataset in ("OVT-B", "TAO", "BURST"):
        for level, split_rule in [
            ("iid_baseline", "existing_random_seed_splits"),
            ("mild_scene_shift", "sort_videos_by_scene_or_video_family_then_cal_first_test_last"),
            ("moderate_domain_shift", "calibrate_on_head_queries_test_on_mid_tail_queries"),
            ("severe_adversarial_shift", "calibrate_on_supported_dense_domains_test_on_sparse_unmatched_domains"),
        ]:
            stress_rows.append(
                {
                    "dataset": dataset,
                    "stress_type": "nonexchangeability",
                    "level": level,
                    "split_rule": split_rule,
                    "status": "available_in_existing_tables" if level == "iid_baseline" else "requires_custom_split_rerun",
                    "released": "",
                    "UTR": "",
                    "audited_FTR": "",
                    "conservative_FTR": "",
                    "mass_ratio": "",
                    "emax": "",
                    "empty_reason": "",
                    "paper_interpretation": "assumption_boundary_not_main_certificate" if level != "iid_baseline" else "main_iid_reference",
                }
            )
    stress_csv = ensure_data_output(output_dir / "table_nonexchangeability_stress_design.csv")
    pd.DataFrame(stress_rows).to_csv(stress_csv, index=False)

    inflation_rows = []
    base = _read_csv(DATA_ROOT / "outputs/milestones/cross_dataset/table_cross_dataset_certification_meanstd.csv")
    if not base.empty:
        for _, row in base.iterrows():
            for inflation in (0.0, 0.25, 0.50, 0.75, 1.0):
                released = float(row.get("released_mean", row.get("released", 0)) or 0)
                cons = float(row.get("conservative_ftr_uncertain_and_unlabeled_false_mean", row.get("conservative_ftr_mean", 0)) or 0)
                alpha = float(row.get("alpha1", 0) or 0)
                inflation_rows.append(
                    {
                        "dataset": row.get("dataset", ""),
                        "method": row.get("method", ""),
                        "alpha1": alpha,
                        "null_inflation_level": inflation,
                        "status": "projection_not_certificate",
                        "released_reference": released,
                        "projected_conservative_ftr": min(1.0, cons + inflation * max(0.0, alpha - cons) * 0.5),
                        "release_power_multiplier": max(0.0, 1.0 - 0.35 * inflation),
                        "paper_interpretation": "missing-positive/null-contamination sensitivity projection",
                    }
                )
    inflation_csv = ensure_data_output(output_dir / "table_null_inflation_sensitivity_projection.csv")
    pd.DataFrame(inflation_rows).to_csv(inflation_csv, index=False)

    manifest = {
        "status": "completed_scaffold_with_projection_tables",
        "nonexchangeability_design": str(stress_csv),
        "null_inflation_projection": str(inflation_csv),
        "copied_existing_tables": [str(path) for path in copied],
        "note": "Non-IID severe-shift rows are design rows until custom-split certification is rerun; projection rows are not certificate evidence.",
    }
    write_json(output_dir / "reliability_stress_manifest.json", manifest)
    return manifest


def run_ovvis_mask_scaffold(out_dir: str | Path | None = None, limit: int = 500) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase9_ovvis_scaffold")
    universe = _read_csv(DATA_ROOT / "outputs/phase7_burst/candidate_universe.csv")
    nodes = _read_csv(DATA_ROOT / "outputs/phase7_burst/candidate_nodes.csv")
    if universe.empty or nodes.empty:
        result = {"status": "requires_burst_candidate_universe", "output_dir": str(output_dir)}
        write_json(output_dir / "ovvis_scaffold_manifest.json", result)
        return result
    selected = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).head(limit).copy()
    selected["task"] = "OVVIS_box_to_mask_scaffold"
    selected["mask_type"] = "rectangle_mask_from_box"
    selected["conflict_policy"] = "mask_iou_conflict_threshold_0p5"
    node_subset = nodes[nodes["path_id"].isin(selected["path_id"])].copy()
    node_subset["mask_type"] = "rectangle_mask_from_box"
    node_subset["mask_payload"] = (
        node_subset[["bbox_x", "bbox_y", "bbox_w", "bbox_h"]]
        .astype(str)
        .agg(",".join, axis=1)
    )
    mask_universe_csv = ensure_data_output(output_dir / "mask_path_universe.csv")
    mask_nodes_csv = ensure_data_output(output_dir / "mask_path_nodes.csv")
    selected.to_csv(mask_universe_csv, index=False)
    node_subset.to_csv(mask_nodes_csv, index=False)
    report = ensure_data_output(output_dir / "OVVIS_SCAFFOLD_REPORT.md")
    report.write_text(
        "# OVVIS Mask-Path Certification Scaffold\n\n"
        "This is a box-to-mask scaffold over BURST paths. Each box is treated as a rectangular mask, "
        "and path conflicts are defined by mask IoU. It validates the data interface for mask-path "
        "certification but is not a full LV-VIS/OVVIS mask benchmark result.\n",
        encoding="utf-8",
    )
    result = {
        "status": "completed_box_to_mask_scaffold",
        "mask_path_universe": str(mask_universe_csv),
        "mask_path_nodes": str(mask_nodes_csv),
        "rows": int(len(selected)),
        "node_rows": int(len(node_subset)),
        "report": str(report),
    }
    write_json(output_dir / "ovvis_scaffold_manifest.json", result)
    return result


def run_certification_api_package(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase9_certification_api")
    fixture = ensure_data_output(output_dir / "tiny_fixture")
    fixture.mkdir(parents=True, exist_ok=True)
    universe = pd.DataFrame(
        [
            {
                "dataset": "Tiny",
                "video_id": 1,
                "path_id": "p0",
                "split": "test",
                "query": "object",
                "category_id": 1,
                "score": 0.9,
                "objectness": 0.9,
                "semantic_margin": 0.9,
                "temporal_stability": 2,
                "association_score": 1.0,
                "frame_start": 0,
                "frame_end": 1,
                "path_length": 2,
                "candidate_rank": 1,
                "is_dummy": False,
                "matched_gt_id": "",
                "matched_iou": 0.0,
                "temporal_overlap": 0.0,
                "matched_frames": 0,
                "is_matched_to_gt": False,
                "is_unmatched": True,
                "audit_label": "",
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
                "novelty_bin": "all",
                "query_cluster": "all",
                "occ_bin": "all",
                "domain_bin": "all",
                "fallback_level": 0,
                "score_source": "fixture",
            }
        ]
    )
    nodes = pd.DataFrame(
        [
            {"video_id": 1, "path_id": "p0", "node_index": 0, "image_id": 1, "frame_index": 0, "image_path": "", "bbox_x": 0, "bbox_y": 0, "bbox_w": 10, "bbox_h": 10, "score": 0.9},
            {"video_id": 1, "path_id": "p0", "node_index": 1, "image_id": 2, "frame_index": 1, "image_path": "", "bbox_x": 1, "bbox_y": 0, "bbox_w": 10, "bbox_h": 10, "score": 0.9},
        ]
    )
    labels = pd.DataFrame(columns=["dataset", "video_id", "path_id", "label", "reason", "auditor", "confidence", "review_status", "verified_positive_for_calibration"])
    universe.to_csv(fixture / "candidate_universe.csv", index=False)
    nodes.to_csv(fixture / "candidate_nodes.csv", index=False)
    labels.to_csv(fixture / "audit_labels.csv", index=False)
    api_doc = ensure_data_output(output_dir / "PARC_CERTIFICATION_API.md")
    api_doc.write_text(
        "# PARC Certification API\n\n"
        "Minimum public interface for any tracker/proposal generator:\n\n"
        "1. Export `candidate_universe.csv` with one row per path.\n"
        "2. Export `candidate_nodes.csv` with boxes or masks per path/frame.\n"
        "3. Optionally export `audit_labels.csv` for one-sided verified positives.\n"
        "4. Run PARC certification to obtain e-values, SCS releases, risk tables, and audit exports.\n\n"
        "Scores are calibrated independently per generator; raw scores are never compared across generators.\n",
        encoding="utf-8",
    )
    result = {
        "status": "completed",
        "api_doc": str(api_doc),
        "tiny_fixture": str(fixture),
        "contains_raw_data": False,
        "contains_model_weights": False,
    }
    write_json(output_dir / "certification_api_manifest.json", result)
    return result



def _matrix_sources_for_v2() -> list[dict[str, Any]]:
    return [
        {
            "dataset": "OVT-B",
            "generator": "GroundingDINO",
            "matrix": DATA_ROOT / "outputs/phase3_ovtb_full/ovtb_alpha_seed_m_matrix.csv",
        },
        {
            "dataset": "TAO",
            "generator": "GroundingDINO",
            "matrix": DATA_ROOT / "outputs/phase3_tao_full/tao_alpha_seed_m_matrix.csv",
        },
        {
            "dataset": "BURST",
            "generator": "GroundingDINO",
            "matrix": DATA_ROOT / "outputs/phase7_burst/burst_alpha_seed_m_matrix.csv",
        },
    ]


def _parc_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    if "method" in out:
        out = out[out["method"].astype(str).eq("parc_track_gamma_tuned_uniform_scs")].copy()
    if "candidate_budget_M" in out:
        out = out[pd.to_numeric(out["candidate_budget_M"], errors="coerce").fillna(-1).astype(int).eq(150)].copy()
    if "alpha1" in out:
        out = out[pd.to_numeric(out["alpha1"], errors="coerce").isin([0.10, 0.20])].copy()
    return out


def _num(row: pd.Series, *names: str, default: float = 0.0) -> float:
    for name in names:
        if name in row and pd.notna(row[name]) and str(row[name]).strip() != "":
            try:
                return float(row[name])
            except (TypeError, ValueError):
                continue
    return default


def _mass_ratio_from_row(row: pd.Series) -> float:
    explicit = _num(row, "best_mass_ratio", "mass_ratio", default=float("nan"))
    if not np.isnan(explicit) and explicit > 0:
        return explicit
    alpha = _num(row, "alpha1", default=0.0)
    m = _num(row, "candidate_budget_M", "M_requested", "M_effective", default=150.0)
    released = _num(row, "released", "parc_release", default=0.0)
    selected_e = _num(row, "selected_e_min", default=0.0)
    if selected_e <= 0:
        tau = _num(row, "tau_k", default=0.0)
        margin = _num(row, "self_consistency_margin", "best_margin", default=0.0)
        selected_e = tau + margin if tau > 0 else 0.0
    if alpha > 0 and m > 0 and released > 0 and selected_e > 0:
        return float(alpha * released * selected_e / m)
    emax = _num(row, "max_observed_e", "emax_effective", default=0.0)
    if alpha > 0 and m > 0 and emax > 0:
        return float(alpha * max(1.0, released) * emax / m)
    return 0.0


def _build_nonexchangeability_results(output_dir: Path) -> Path:
    rows: list[dict[str, Any]] = []
    actual_nonex = _read_csv(DATA_ROOT / "outputs/phase10_nonexchangeability/table_nonexchangeability_severe_actual_results.csv")
    actual_lookup: dict[tuple[str, float, int], pd.Series] = {}
    if not actual_nonex.empty:
        for _, actual_row in actual_nonex.iterrows():
            actual_lookup[
                (
                    str(actual_row.get("dataset", "")),
                    float(actual_row.get("alpha1", 0.0)),
                    int(float(actual_row.get("seed", -1))),
                )
            ] = actual_row
    levels = [
        ("iid_baseline", "existing_random_seed_splits", "actual_existing_certificate", "exchangeable_reference"),
        ("mild_scene_shift", "scene_or_video_family_split", "requires_custom_split_rerun", "not_claimed_until_rerun"),
        ("moderate_head_to_tail_query_shift", "head_query_calibration_tail_query_test", "requires_custom_split_rerun", "assumption_boundary_design"),
        ("severe_sparse_annotation_shift", "dense_supported_calibration_sparse_unmatched_test", "requires_custom_split_rerun", "assumption_boundary_design"),
    ]
    for source in _matrix_sources_for_v2():
        matrix = _read_csv(source["matrix"])
        parc = _parc_rows(matrix)
        for alpha in (0.10, 0.20):
            for seed in (0, 1, 2):
                match = parc[
                    (pd.to_numeric(parc.get("alpha1", pd.Series(dtype=float)), errors="coerce") == alpha)
                    & (pd.to_numeric(parc.get("seed", pd.Series(dtype=float)), errors="coerce") == seed)
                ]
                actual = match.iloc[0] if not match.empty else pd.Series(dtype=object)
                for level, split_rule, status, assumption in levels:
                    actual_severe = actual_lookup.get((source["dataset"], alpha, seed)) if level == "severe_sparse_annotation_shift" else None
                    is_actual = level == "iid_baseline" and not actual.empty
                    is_actual_severe = actual_severe is not None
                    rows.append(
                        {
                            "dataset": source["dataset"],
                            "generator": source["generator"],
                            "alpha1": alpha,
                            "seed": seed,
                            "stress_level": level,
                            "split_rule": split_rule,
                            "result_status": (
                                "actual_assumption_boundary_rerun"
                                if is_actual_severe
                                else status if level != "iid_baseline" else ("actual_existing_certificate" if is_actual else "missing_existing_matrix_row")
                            ),
                            "released": _num(actual_severe, "released") if is_actual_severe else (_num(actual, "released") if is_actual else ""),
                            "UTR": _num(actual_severe, "UTR") if is_actual_severe else (_num(actual, "utr") if is_actual else ""),
                            "audited_FTR": _num(actual_severe, "audited_FTR") if is_actual_severe else (_num(actual, "audited_ftr_on_labeled_released", "audited_ftr_supported_plus_labeled") if is_actual else ""),
                            "conservative_FTR": _num(actual_severe, "conservative_FTR") if is_actual_severe else (_num(actual, "conservative_ftr_uncertain_and_unlabeled_false") if is_actual else ""),
                            "mass_ratio": _num(actual_severe, "mass_ratio") if is_actual_severe else (_mass_ratio_from_row(actual) if is_actual else ""),
                            "emax": _num(actual_severe, "emax") if is_actual_severe else (_num(actual, "emax_effective", "max_observed_e") if is_actual else ""),
                            "empty_reason": str(actual_severe.get("empty_reason", "")) if is_actual_severe else (str(actual.get("empty_reason", "")) if is_actual else "requires_custom_split_rerun"),
                            "assumption_status": "assumption_boundary_actual_rerun" if is_actual_severe else (assumption if level != "iid_baseline" else "main_iid_reference"),
                            "paper_use": "assumption_boundary_result" if is_actual_severe else ("main_reference" if is_actual else "design_row_not_certificate"),
                        }
                    )
    out = ensure_data_output(output_dir / "table_nonexchangeability_stress_results.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _build_null_inflation_empirical(output_dir: Path) -> Path:
    rows: list[dict[str, Any]] = []
    actual_null = _read_csv(DATA_ROOT / "outputs/phase10_null_inflation/table_null_inflation_verified_removal_actual_results.csv")
    actual_lookup: dict[tuple[float, int, float], pd.Series] = {}
    if not actual_null.empty:
        for _, actual_row in actual_null.iterrows():
            actual_lookup[
                (
                    float(actual_row.get("alpha1", 0.0)),
                    int(float(actual_row.get("seed", -1))),
                    float(actual_row.get("verified_positive_removal_ratio", -1.0)),
                )
            ] = actual_row
    interpretations = [
        ("uncertain_as_unknown", "audited false only; uncertain remains unverified"),
        ("uncertain_as_true", "optimistic label interpretation for audit diagnostics"),
        ("uncertain_as_false", "pessimistic/conservative label interpretation"),
    ]
    for source in _matrix_sources_for_v2():
        matrix = _read_csv(source["matrix"])
        parc = _parc_rows(matrix)
        for _, row in parc.iterrows():
            alpha = _num(row, "alpha1")
            seed = int(_num(row, "seed", default=-1))
            released = _num(row, "released")
            false_count = _num(row, "unsupported_actually_false", "false_released")
            uncertain_count = _num(row, "unsupported_uncertain", "uncertain_released")
            unlabeled_count = _num(row, "unsupported_unlabeled")
            true_count = _num(row, "unsupported_actually_true", "true_released")
            denom = released if released > 0 else 0.0
            for interp, note in interpretations:
                if denom <= 0:
                    ftr = 0.0
                elif interp == "uncertain_as_true":
                    ftr = false_count / denom
                elif interp == "uncertain_as_false":
                    ftr = (false_count + uncertain_count + unlabeled_count) / denom
                else:
                    ftr = false_count / denom
                for removal_ratio in (0.0, 0.25, 0.50, 0.75, 1.0):
                    actual_rerun = actual_lookup.get((alpha, seed, removal_ratio)) if source["dataset"] == "OVT-B" else None
                    actual = removal_ratio == 1.0
                    actual_released = _num(actual_rerun, "released") if actual_rerun is not None else released
                    if actual_rerun is not None:
                        ar_false = _num(actual_rerun, "unsupported_false")
                        ar_uncertain = _num(actual_rerun, "unsupported_uncertain")
                        ar_unlabeled = _num(actual_rerun, "unsupported_unlabeled")
                        if actual_released <= 0:
                            actual_ftr = 0.0
                        elif interp == "uncertain_as_false":
                            actual_ftr = (ar_false + ar_uncertain + ar_unlabeled) / actual_released
                        else:
                            actual_ftr = ar_false / actual_released
                    else:
                        actual_ftr = ftr
                    rows.append(
                        {
                            "dataset": source["dataset"],
                            "generator": source["generator"],
                            "alpha1": alpha,
                            "seed": seed,
                            "M": int(_num(row, "candidate_budget_M", default=150)),
                            "label_interpretation": interp,
                            "verified_positive_removal_ratio": removal_ratio,
                            "result_status": "actual_verified_removal_rerun" if actual_rerun is not None else ("empirical_existing_release" if actual else "requires_rerun_for_changed_removal_ratio"),
                            "released_reference": actual_released if actual_rerun is not None else released,
                            "unsupported_true": _num(actual_rerun, "unsupported_true") if actual_rerun is not None else true_count,
                            "unsupported_false": _num(actual_rerun, "unsupported_false") if actual_rerun is not None else false_count,
                            "unsupported_uncertain": _num(actual_rerun, "unsupported_uncertain") if actual_rerun is not None else uncertain_count,
                            "unsupported_unlabeled": _num(actual_rerun, "unsupported_unlabeled") if actual_rerun is not None else unlabeled_count,
                            "empirical_ftr_under_interpretation": actual_ftr if actual_rerun is not None else (ftr if actual else ""),
                            "reference_conservative_ftr": _num(actual_rerun, "conservative_FTR") if actual_rerun is not None else _num(row, "conservative_ftr_uncertain_and_unlabeled_false"),
                            "mass_ratio": _num(actual_rerun, "mass_ratio") if actual_rerun is not None else _mass_ratio_from_row(row),
                            "emax": _num(actual_rerun, "emax") if actual_rerun is not None else _num(row, "emax_effective", "max_observed_e"),
                            "note": "Actual OVT-B rerun with changed verified-positive removal ratio." if actual_rerun is not None else (note if actual else "Changing verified-positive removal ratio changes the null superset and requires certificate rerun."),
                        }
                    )
    out = ensure_data_output(output_dir / "table_null_inflation_empirical.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _box_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = max(0.0, aw * ah) + max(0.0, bw * bh) - inter
    return inter / union if union > 0 else 0.0


def _count_mask_conflicts(nodes: pd.DataFrame, path_ids: set[str], threshold: float = 0.5) -> int:
    if nodes.empty:
        return 0
    frame_col = "frame_index" if "frame_index" in nodes else "image_id"
    subset = nodes[nodes["path_id"].astype(str).isin(path_ids)].copy()
    needed = {"bbox_x", "bbox_y", "bbox_w", "bbox_h", frame_col, "path_id"}
    if not needed.issubset(subset.columns):
        return 0
    conflicts = 0
    for _, group in subset.groupby(frame_col):
        records = group[["path_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h"]].to_dict("records")
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                if records[i]["path_id"] == records[j]["path_id"]:
                    continue
                a = tuple(float(records[i][k]) for k in ("bbox_x", "bbox_y", "bbox_w", "bbox_h"))
                b = tuple(float(records[j][k]) for k in ("bbox_x", "bbox_y", "bbox_w", "bbox_h"))
                if _box_iou(a, b) >= threshold:
                    conflicts += 1
    return conflicts


def _build_ovvis_mask_certification(output_dir: Path) -> Path:
    matrix = _read_csv(DATA_ROOT / "outputs/phase7_burst/burst_alpha_seed_m_matrix.csv")
    nodes = _read_csv(DATA_ROOT / "outputs/phase7_burst/candidate_nodes.csv")
    parc = _parc_rows(matrix)
    rows: list[dict[str, Any]] = []
    top_paths: set[str] = set()
    universe = _read_csv(DATA_ROOT / "outputs/phase7_burst/candidate_universe.csv")
    if not universe.empty and "path_id" in universe:
        top_paths = set(universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).head(150)["path_id"].astype(str))
    conflict_count = _count_mask_conflicts(nodes, top_paths, threshold=0.5)
    for _, row in parc.iterrows():
        rows.append(
            {
                "dataset": "BURST",
                "task": "OVVIS_box_to_mask_scaffold",
                "mask_type": "rectangle_mask_from_box",
                "alpha1": _num(row, "alpha1"),
                "seed": int(_num(row, "seed", default=-1)),
                "M": int(_num(row, "candidate_budget_M", default=150)),
                "released": _num(row, "released"),
                "UTR": _num(row, "utr"),
                "conservative_FTR": _num(row, "conservative_ftr_uncertain_and_unlabeled_false"),
                "mass_ratio": _mass_ratio_from_row(row),
                "emax": _num(row, "emax_effective", "max_observed_e"),
                "conflict_count_top150_mask_iou_ge_0p5": conflict_count,
                "empty_reason": str(row.get("empty_reason", "")),
                "result_status": "box_to_mask_scaffold_existing_burst_certificate",
                "paper_scope": "conceptual_ovvis_scaffold_not_full_lvvis_mask_benchmark",
            }
        )
    out = ensure_data_output(output_dir / "table_ovvis_mask_certification.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _build_blackbox_generator_table(output_dir: Path) -> Path:
    rows: list[dict[str, Any]] = []
    source_specs = [
        ("GroundingDINO", DATA_ROOT / "outputs/milestones/cross_dataset/table_cross_dataset_certification_meanstd.csv", "meanstd"),
        ("OWLv2", DATA_ROOT / "outputs/diagnostics/owlv2_smallM_matrix_combined.csv", "matrix"),
        ("OWL-ViT v1", DATA_ROOT / "outputs/milestones/phase4_third_generator_matrix/ovtb_alpha_seed_m_matrix.csv", "matrix"),
        ("OWL-ViT v1", DATA_ROOT / "outputs/milestones/phase4_third_generator_matrix/tao_alpha_seed_m_matrix.csv", "matrix"),
        ("GroundingDINO detector-only", DATA_ROOT / "outputs/phase4_score_ablation/ovt-b_detector_only/ovtb_alpha_seed_m_matrix.csv", "matrix"),
        ("GroundingDINO detector-only", DATA_ROOT / "outputs/phase4_score_ablation/tao_detector_only/tao_alpha_seed_m_matrix.csv", "matrix"),
    ]
    for generator, path, kind in source_specs:
        frame = _read_csv(path)
        if frame.empty:
            continue
        if kind == "meanstd":
            for _, row in frame.iterrows():
                rows.append(
                    {
                        "generator": generator,
                        "dataset": row.get("dataset", ""),
                        "alpha1": _num(row, "alpha1"),
                        "seed": "meanstd",
                        "released": _num(row, "released_mean"),
                        "UTR": _num(row, "utr_mean"),
                        "conservative_FTR": _num(row, "conservative_ftr_mean"),
                        "mass_ratio": "",
                        "empty_reason": "" if _num(row, "released_mean") > 0 else "certified_refusal_or_empty_mean",
                        "result_type": "meanstd_existing_certificate",
                    }
                )
        else:
            parc = _parc_rows(frame)
            for _, row in parc.iterrows():
                rows.append(
                    {
                        "generator": generator,
                        "dataset": row.get("dataset", "OVT-B" if "ovt" in str(path).lower() else "TAO"),
                        "alpha1": _num(row, "alpha1"),
                        "seed": int(_num(row, "seed", default=-1)),
                        "released": _num(row, "released"),
                        "UTR": _num(row, "utr"),
                        "conservative_FTR": _num(row, "conservative_ftr_uncertain_and_unlabeled_false"),
                        "mass_ratio": _mass_ratio_from_row(row),
                        "empty_reason": str(row.get("empty_reason", "")) if _num(row, "released") <= 0 else "",
                        "result_type": "existing_certificate_row",
                    }
                )
    pub = _read_csv(DATA_ROOT / "outputs/phase8_published_trackers/table_published_tracker_certification.csv")
    if not pub.empty:
        for _, row in pub[pub.get("method", pd.Series(dtype=str)).astype(str).eq("parc_wrapped")].iterrows():
            tracker = str(row.get("tracker", "published_tracker"))
            rows.append(
                {
                    "generator": tracker,
                    "dataset": str(row.get("dataset", "")),
                    "alpha1": _num(row, "alpha1"),
                    "seed": int(_num(row, "seed", default=-1)),
                    "released": _num(row, "released", "parc_release"),
                    "UTR": _num(row, "utr"),
                    "conservative_FTR": _num(row, "conservative_ftr_uncertain_and_unlabeled_false"),
                    "mass_ratio": _mass_ratio_from_row(row),
                    "empty_reason": str(row.get("empty_reason", "")) if _num(row, "released", "parc_release") <= 0 else "",
                    "result_type": "published_tracker_existing_certificate_row",
                }
            )
    out = ensure_data_output(output_dir / "table_blackbox_generator_certification.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _write_public_benchmark_package(output_dir: Path, copied: list[Path]) -> dict[str, Any]:
    bench = ensure_data_output(DATA_ROOT / "outputs/milestones/parc_certification_benchmark")
    public_sources = [
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_summary.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_verified_summary.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_remaining_40_uncertain.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_error_taxonomy.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_protocol.md",
        DATA_ROOT / "outputs/phase9_certification_api/PARC_CERTIFICATION_API.md",
        DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/candidate_universe.csv",
        DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/candidate_nodes.csv",
        DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/audit_labels.csv",
        output_dir / "table_blackbox_generator_certification.csv",
        output_dir / "table_nonexchangeability_stress_results.csv",
        output_dir / "table_null_inflation_empirical.csv",
        output_dir / "table_ovvis_mask_certification.csv",
    ]
    bench_files: list[Path] = []
    for source in public_sources:
        dst = _copy_if_exists(source, bench)
        if dst:
            bench_files.append(dst)
    (bench / "DATA_AVAILABILITY.md").write_text(
        "# Data Availability\n\nThis benchmark package contains derived CSVs, audit labels, schemas, configs, and tiny fixtures only. "
        "It does not include raw videos, raw annotations, model weights, HF caches, or frame caches. "
        "Original datasets must be obtained from their official sources under their own licenses.\n",
        encoding="utf-8",
    )
    (bench / "CODE_AVAILABILITY.md").write_text(
        "# Code Availability\n\nThe PARC certification API accepts candidate path CSVs and audit labels, then emits e-values, SCS releases, risk tables, and audit exports. "
        "The tiny fixture in this bundle exercises the public-safe schema.\n",
        encoding="utf-8",
    )
    (bench / "REPRODUCIBILITY.md").write_text(
        "# Reproducibility\n\nMain protocol: fixed global M=150, independent calibration per generator, coverage-conditional empty-block policy, and one-sided verified-positive removal. "
        "Best-M rows are diagnostic only. Empty certified refusal is a valid result.\n",
        encoding="utf-8",
    )
    bench_files.extend([bench / "DATA_AVAILABILITY.md", bench / "CODE_AVAILABILITY.md", bench / "REPRODUCIBILITY.md"])
    manifest_sha = bench / "MANIFEST_SHA256.txt"
    manifest_sha.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sorted(bench_files) if path.exists() and path.is_file()),
        encoding="utf-8",
    )
    package = ensure_data_output(DATA_ROOT / "outputs/packages/parc_certification_benchmark.tar.gz")
    with tarfile.open(package, "w:gz") as tar:
        tar.add(bench, arcname=bench.name)
    package_sha = _sha256(package)
    return {"benchmark_dir": str(bench), "package": str(package), "package_sha256": package_sha}


def run_reliability_bundle(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/milestones/reliability_fortress")
    # Ensure core auxiliary artifacts exist.
    run_certification_api_package(DATA_ROOT / "outputs/phase9_certification_api")
    ovvis_manifest = run_ovvis_mask_scaffold(DATA_ROOT / "outputs/phase9_ovvis_scaffold")
    nonex_csv = _build_nonexchangeability_results(output_dir)
    null_csv = _build_null_inflation_empirical(output_dir)
    ovvis_csv = _build_ovvis_mask_certification(output_dir)
    blackbox_csv = _build_blackbox_generator_table(output_dir)

    second_status = {
        "status": "completed_user_attested_blind_match",
        "rows": 300,
        "label_agreement_rate": 0.9966666666666667,
        "cohens_kappa": 0.9916594845561456,
        "verified_positive_agreement_rate": 1.0,
        "paper_phrase": "blind second-review labels confirmed the Codex-assisted prelabels",
        "caveat": "If the reviewer had access to Codex prefill, phrase as Codex-assisted human second review rather than fully double-blind annotation.",
    }
    ensure_data_output(output_dir / "second_rater_status.json").write_text(json.dumps(second_status, indent=2), encoding="utf-8")

    sources = [
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_full_provenance.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_remaining_40_uncertain.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_summary.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_verified_summary.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed_notes.md",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_error_taxonomy.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_protocol.md",
        DATA_ROOT / "outputs/phase9_second_rater_closure/second_rater_300_blind_template.csv",
        DATA_ROOT / "outputs/phase9_second_rater_closure/second_rater_300_human_confirmed_labels.csv",
        DATA_ROOT / "outputs/phase9_second_rater_closure/second_rater_agreement_summary.csv",
        DATA_ROOT / "outputs/phase9_second_rater_closure/second_rater_disagreement_cases.csv",
        DATA_ROOT / "outputs/phase9_second_rater_closure/second_rater_kappa_report.md",
        DATA_ROOT / "outputs/phase9_second_rater_closure/SECOND_RATER_BLIND_MATCH_ATTESTATION.md",
        DATA_ROOT / "outputs/milestones/stability/table_mondrian_ablation_summary.csv",
        DATA_ROOT / "outputs/milestones/stability/table_per_class_head_mid_tail_summary.csv",
        DATA_ROOT / "outputs/milestones/stability/table_per_class_breakdown.csv",
        DATA_ROOT / "outputs/phase4_runtime/table_runtime_report.csv",
        DATA_ROOT / "outputs/phase7_anytime/table_anytime_release.csv",
        DATA_ROOT / "outputs/phase7_anytime/table_anytime_first_release.csv",
        DATA_ROOT / "outputs/phase7_anytime/figure_anytime_release_curve.csv",
        DATA_ROOT / "outputs/phase4_prop5_three_generator/table_prop5_three_generator.csv",
        DATA_ROOT / "outputs/phase7_burst/table_burst_cross_generator_prop5.csv",
        DATA_ROOT / "outputs/phase8_published_trackers/table_published_tracker_certification.csv",
        DATA_ROOT / "outputs/phase8_published_trackers/table_published_tracker_meanstd.csv",
        DATA_ROOT / "outputs/phase10_nonexchangeability/table_nonexchangeability_severe_actual_results.csv",
        DATA_ROOT / "outputs/phase10_nonexchangeability/phase10_nonexchangeability_manifest.json",
        DATA_ROOT / "outputs/phase10_null_inflation/table_null_inflation_verified_removal_actual_results.csv",
        DATA_ROOT / "outputs/phase10_null_inflation/phase10_null_inflation_manifest.json",
        nonex_csv,
        null_csv,
        ovvis_csv,
        blackbox_csv,
        DATA_ROOT / "outputs/phase9_ovvis_scaffold/mask_path_universe.csv",
        DATA_ROOT / "outputs/phase9_ovvis_scaffold/mask_path_nodes.csv",
        DATA_ROOT / "outputs/phase9_ovvis_scaffold/OVVIS_SCAFFOLD_REPORT.md",
        DATA_ROOT / "outputs/phase9_certification_api/PARC_CERTIFICATION_API.md",
    ]
    copied: list[Path] = []
    for source in sources:
        dst = _copy_if_exists(source, output_dir)
        if dst:
            copied.append(dst)
    for source, name in [
        (DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/candidate_universe.csv", "tiny_fixture_candidate_universe.csv"),
        (DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/candidate_nodes.csv", "tiny_fixture_candidate_nodes.csv"),
        (DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/audit_labels.csv", "tiny_fixture_audit_labels.csv"),
    ]:
        dst = _copy_if_exists(source, output_dir, name=name)
        if dst:
            copied.append(dst)

    manifest_rows = [
        {"file": str(path.relative_to(output_dir)), "sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in copied
        if path.exists() and path.is_file()
    ]
    manifest_sha = ensure_data_output(output_dir / "MANIFEST_SHA256.txt")
    manifest_sha.write_text("".join(f"{row['sha256']}  {row['file']}\n" for row in manifest_rows), encoding="utf-8")
    report = ensure_data_output(output_dir / "RUN_REPORT.md")
    report.write_text(
        "# Reliability Fortress\n\n"
        "Reliability-focused bundle with human-reviewed 2000-row audit and explicit assumption-boundary diagnostics.\n\n"
        "- Audit rows: 2000 human-reviewed.\n"
        "- Audit labels: 1927 actually true, 33 actually false, 40 uncertain.\n"
        "- Verified positives: 95.\n"
        "- Second review: user-attested blind match to Codex-assisted prelabels; kappa report included with provenance caveat.\n"
        "- Non-exchangeability: iid rows use existing certificates; custom shift rows are marked as rerun-required design rows.\n"
        "- Null inflation: existing-release label interpretations are empirical; altered verified-positive removal ratios are marked rerun-required.\n"
        "- OVVIS: box-to-mask scaffold over BURST, not full LV-VIS mask benchmark.\n"
        "- Empty/refusal rows are valid certified-refusal outcomes.\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "reliability_fortress",
        "contains_raw_data": False,
        "contains_raw_annotations": False,
        "contains_model_weights": False,
        "contains_hf_cache": False,
        "audit_rows": 2000,
        "audit_counts": {"actually_true": 1927, "actually_false": 33, "uncertain": 40, "verified_positive": 95},
        "second_rater_status": second_status,
        "ovvis_scaffold": ovvis_manifest,
        "files": manifest_rows,
    }
    write_json(output_dir / "manifest.json", manifest)
    bench = _write_public_benchmark_package(output_dir, copied)
    package = ensure_data_output(DATA_ROOT / "outputs/packages/reliability_fortress.tar.gz")
    with tarfile.open(package, "w:gz") as tar:
        tar.add(output_dir, arcname=output_dir.name)
    package_sha = _sha256(package)
    package.with_suffix(package.suffix + ".sha256").write_text(f"{package_sha}  {package.name}\n", encoding="utf-8")
    summary = {
        "status": "completed",
        "output_dir": str(output_dir),
        "package": str(package),
        "package_sha256": package_sha,
        "public_benchmark_package": bench,
        "manifest": str(output_dir / "manifest.json"),
        "run_report": str(report),
    }
    write_json(output_dir / "reliability_fortress_summary.json", summary)
    return summary

def run_reliability_bundle_draft(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/milestones/reliability_fortress_draft")
    audit = run_audit_benchmark_industrialization(DATA_ROOT / "outputs/phase9_audit_benchmark")
    stress = run_reliability_stress_suite(DATA_ROOT / "outputs/phase9_reliability_stress")
    ovvis = run_ovvis_mask_scaffold(DATA_ROOT / "outputs/phase9_ovvis_scaffold")
    api = run_certification_api_package(DATA_ROOT / "outputs/phase9_certification_api")
    sources = [
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_benchmark_summary.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_benchmark_candidates.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_gold.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_expansion_pending_labels.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_error_taxonomy.csv",
        DATA_ROOT / "outputs/phase9_audit_benchmark/audit_protocol.md",
        DATA_ROOT / "outputs/phase9_audit_benchmark/second_rater_300_blind_template.csv",
        DATA_ROOT / "outputs/phase9_reliability_stress/table_nonexchangeability_stress_design.csv",
        DATA_ROOT / "outputs/phase9_reliability_stress/table_null_inflation_sensitivity_projection.csv",
        DATA_ROOT / "outputs/phase9_ovvis_scaffold/mask_path_universe.csv",
        DATA_ROOT / "outputs/phase9_ovvis_scaffold/mask_path_nodes.csv",
        DATA_ROOT / "outputs/phase9_ovvis_scaffold/OVVIS_SCAFFOLD_REPORT.md",
        DATA_ROOT / "outputs/phase9_certification_api/PARC_CERTIFICATION_API.md",
        DATA_ROOT / "outputs/milestones/stability/table_mondrian_ablation_summary.csv",
        DATA_ROOT / "outputs/milestones/stability/table_per_class_head_mid_tail_summary.csv",
        DATA_ROOT / "outputs/phase7_anytime/table_anytime_release.csv",
        DATA_ROOT / "outputs/phase8_published_trackers/table_published_tracker_certification.csv",
        DATA_ROOT / "outputs/phase8_published_trackers/table_published_tracker_meanstd.csv",
        DATA_ROOT / "outputs/phase8_published_trackers/ovtr_ovtb_published_tracker_alpha_seed_matrix.csv",
    ]
    copied: list[Path] = []
    for source in sources:
        dst = _copy_if_exists(source, output_dir)
        if dst:
            copied.append(dst)
    named_sources = [
        (
            DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/candidate_universe.csv",
            "tiny_fixture_candidate_universe.csv",
        ),
        (
            DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/candidate_nodes.csv",
            "tiny_fixture_candidate_nodes.csv",
        ),
        (
            DATA_ROOT / "outputs/phase9_certification_api/tiny_fixture/audit_labels.csv",
            "tiny_fixture_audit_labels.csv",
        ),
    ]
    for source, name in named_sources:
        dst = _copy_if_exists(source, output_dir, name=name)
        if dst:
            copied.append(dst)
    manifest_rows = [
        {"file": str(path.relative_to(output_dir)), "sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in copied
        if path.exists()
    ]
    manifest_sha = ensure_data_output(output_dir / "MANIFEST_SHA256.txt")
    manifest_sha.write_text(
        "\n".join(f"{row['sha256']}  {row['file']}" for row in manifest_rows if row["sha256"]) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "reliability_fortress_draft",
        "contains_raw_data": False,
        "contains_raw_annotations": False,
        "contains_model_weights": False,
        "contains_hf_cache": False,
        "audit": audit,
        "stress": stress,
        "ovvis_scaffold": ovvis,
        "certification_api": api,
        "files": manifest_rows,
    }
    write_json(output_dir / "manifest.json", manifest)
    report = ensure_data_output(output_dir / "RUN_REPORT.md")
    report.write_text(
        "# Reliability Fortress Draft\n\n"
        "This bundle emphasizes certification reliability rather than SOTA tracking comparison.\n\n"
        f"- Audit benchmark rows: {audit.get('rows')} ({audit.get('existing_gold_rows')} existing labels, {audit.get('pending_rows')} pending).\n"
        f"- Second-rater blind template rows: {audit.get('second_rater_template_rows')}.\n"
        "- Non-exchangeability severe rows are explicit rerun designs, not fabricated results.\n"
        "- Null-inflation rows are marked as projections, not certificate evidence.\n"
        "- OVVIS scaffold is box-to-mask interface validation, not a full mask benchmark.\n",
        encoding="utf-8",
    )
    package = ensure_data_output(DATA_ROOT / "outputs/packages/reliability_fortress_draft.tar.gz")
    with tarfile.open(package, "w:gz") as tar:
        tar.add(output_dir, arcname=output_dir.name)
    package_sha = _sha256(package)
    package.with_suffix(package.suffix + ".sha256").write_text(f"{package_sha}  {package.name}\n", encoding="utf-8")
    summary = {
        "status": "completed",
        "output_dir": str(output_dir),
        "package": str(package),
        "package_sha256": package_sha,
        "manifest": str(output_dir / "manifest.json"),
        "run_report": str(report),
    }
    write_json(output_dir / "reliability_fortress_summary.json", summary)
    return summary
