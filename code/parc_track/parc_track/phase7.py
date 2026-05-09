from __future__ import annotations

import hashlib
import json
import math
import shutil
import tarfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output, inspect_coco_video_dataset, write_json
from .phase2 import _load_universe_with_labels, _scs_release_count, _split_video_ids
from .phase3 import _label_metrics
from .phase4 import (
    DATA_ROOT,
    PARC_METHOD,
    _copy_if_exists,
    _entry_for,
    _load_cfg,
    _method_evalues,
    _read_csv,
    _sha256,
    run_second_rater_agreement,
)


ANYTIME_CHECKPOINTS: tuple[int | str, ...] = (10, 20, 40, 80, 160, "final")


def _checkpoint_sort_key(checkpoint: int | str) -> tuple[int, float]:
    if checkpoint == "final":
        return (1, math.inf)
    return (0, float(checkpoint))


def _visible_at_checkpoint(frame: pd.DataFrame, checkpoint: int | str) -> pd.DataFrame:
    if checkpoint == "final":
        return frame.copy()
    cp = int(checkpoint)
    # This is a conservative completed-prefix diagnostic: a path is eligible
    # only after its observed linked segment has ended by the checkpoint.
    return frame[
        (pd.to_numeric(frame["frame_start"], errors="coerce").fillna(math.inf) <= cp)
        & (pd.to_numeric(frame["frame_end"], errors="coerce").fillna(math.inf) <= cp)
    ].copy()


def _scope_pool(test: pd.DataFrame, scope: str, budget: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    test = test.sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    if scope == "all_test":
        return test.head(int(budget)).copy(), {"num_scope_videos": int(test["video_id"].nunique())}
    if scope == "long50_test":
        lengths = (
            test.assign(frame_end_num=pd.to_numeric(test["frame_end"], errors="coerce").fillna(0))
            .groupby("video_id", dropna=False)["frame_end_num"]
            .max()
            .sort_values(ascending=False)
        )
        video_ids = set(int(v) for v in lengths.head(50).index.tolist())
        pool = test[test["video_id"].astype(int).isin(video_ids)].head(int(budget)).copy()
        return pool, {
            "num_scope_videos": int(len(video_ids)),
            "min_scope_video_end": float(lengths.head(50).min()) if len(lengths.head(50)) else None,
            "max_scope_video_end": float(lengths.head(50).max()) if len(lengths.head(50)) else None,
        }
    raise ValueError(f"unknown anytime video scope: {scope}")


def _harmonize_label_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "label" not in out:
        out["label"] = ""
    if "audit_label" in out:
        label = out["label"].fillna("").astype(str).str.strip()
        audit = out["audit_label"].fillna("").astype(str).str.strip()
        out.loc[label == "", "label"] = audit[label == ""]
    return out


def run_anytime_demo(out_dir: str | Path | None = None, budget: int = 150) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase7_anytime")
    entry = _entry_for("OVT-B", "GroundingDINO")
    cfg = _load_cfg(entry)
    universe_base = _load_universe_with_labels(cfg)
    rows: list[dict[str, Any]] = []
    first_rows: list[dict[str, Any]] = []

    for alpha in (0.10, 0.20):
        for seed in (0, 1, 2):
            split_map = _split_video_ids(universe_base["video_id"].astype(int).tolist(), {**cfg, "splits": {**cfg.get("splits", {}), "seed": seed}})
            universe = universe_base.copy()
            universe["split"] = universe["video_id"].astype(int).map(split_map)
            test = universe[universe["split"] == "test"].copy()
            evalues = _method_evalues(entry, alpha, seed)
            evalues = evalues[evalues["method"].astype(str) == PARC_METHOD].copy() if not evalues.empty else evalues
            for scope in ("all_test", "long50_test"):
                pool, scope_meta = _scope_pool(test, scope, budget)
                if evalues.empty:
                    merged = pool.copy()
                    merged["e_value"] = 0.0
                else:
                    merged = pool.merge(evalues[["path_id", "e_value"]], on="path_id", how="left")
                    merged["e_value"] = pd.to_numeric(merged["e_value"], errors="coerce").fillna(0.0)
                merged = _harmonize_label_columns(merged)
                first_release_checkpoint: int | str | None = None
                first_release_count = 0
                for checkpoint in ANYTIME_CHECKPOINTS:
                    visible = _visible_at_checkpoint(merged, checkpoint)
                    values = visible["e_value"].astype(float).tolist()
                    k, tau, margin = _scs_release_count(values, alpha1=alpha, candidate_budget_m=budget)
                    selected = visible.sort_values("e_value", ascending=False).head(k).copy() if k else visible.iloc[[]].copy()
                    metrics = _label_metrics(selected, budget)
                    if k and first_release_checkpoint is None:
                        first_release_checkpoint = checkpoint
                        first_release_count = int(k)
                    rows.append(
                        {
                            "dataset": "OVT-B",
                            "generator": "GroundingDINO",
                            "video_scope": scope,
                            "alpha1": alpha,
                            "seed": seed,
                            "candidate_budget_M": budget,
                            "checkpoint": checkpoint,
                            "checkpoint_order": _checkpoint_sort_key(checkpoint)[0] * 1_000_000
                            + (999_999 if checkpoint == "final" else int(checkpoint)),
                            "eligible_candidates": int(len(visible)),
                            "tau_k": tau if k else None,
                            "self_consistency_margin": margin if k else None,
                            "score_source": "final_evalue_checkpoint_slice",
                            **scope_meta,
                            **metrics,
                        }
                    )
                first_rows.append(
                    {
                        "dataset": "OVT-B",
                        "generator": "GroundingDINO",
                        "video_scope": scope,
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": budget,
                        "first_nonempty_checkpoint": first_release_checkpoint,
                        "first_nonempty_released": first_release_count,
                        "ever_nonempty": first_release_checkpoint is not None,
                        **scope_meta,
                    }
                )

    table = pd.DataFrame(rows)
    first = pd.DataFrame(first_rows)
    table_csv = ensure_data_output(output_dir / "table_anytime_release.csv")
    first_csv = ensure_data_output(output_dir / "table_anytime_first_release.csv")
    figure_csv = ensure_data_output(output_dir / "figure_anytime_release_curve.csv")
    table.to_csv(table_csv, index=False)
    first.to_csv(first_csv, index=False)
    if not table.empty:
        (
            table.groupby(["video_scope", "alpha1", "checkpoint"], dropna=False)
            .agg(
                released_mean=("released", "mean"),
                released_std=("released", "std"),
                utr_mean=("utr", "mean"),
                conservative_ftr_mean=("conservative_ftr_uncertain_and_unlabeled_false", "mean"),
                margin_mean=("self_consistency_margin", "mean"),
                eligible_candidates_mean=("eligible_candidates", "mean"),
            )
            .reset_index()
            .sort_values(["video_scope", "alpha1", "checkpoint"], key=lambda s: s.astype(str))
            .to_csv(figure_csv, index=False)
        )
    else:
        pd.DataFrame().to_csv(figure_csv, index=False)
    result = {
        "status": "completed",
        "table": str(table_csv),
        "first_release": str(first_csv),
        "figure_csv": str(figure_csv),
        "rows": int(len(table)),
        "note": "Anytime demo uses final e-values on checkpoint-visible completed path slices; it is a timing diagnostic, not a per-frame re-scoring benchmark.",
    }
    write_json(output_dir / "anytime_demo_summary.json", result)
    return result


def _find_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.json") if path.is_file())[:200]


def _third_dataset_roots(dataset: str) -> list[Path]:
    name = dataset.upper()
    if name == "BURST":
        return [DATA_ROOT / "data/BURST", DATA_ROOT / "data/burst"]
    if name in {"LV-VIS", "LVVIS"}:
        return [
            DATA_ROOT / "data/LV-VIS",
            DATA_ROOT / "data/LVVIS",
            DATA_ROOT / "data/OVT-B/OVT-B/LVVIS",
        ]
    raise ValueError(f"unknown third dataset target: {dataset}")


def _is_burst_sequence_json(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    seqs = data.get("sequences")
    return isinstance(seqs, list) and bool(seqs) and isinstance(seqs[0], dict) and "segmentations" in seqs[0]


def _burst_frame_path(seq: dict[str, Any], image_name: str) -> Path:
    # BURST uses TAO image sequences. We keep absolute file paths in the
    # converted JSON so downstream tools do not need a special BURST root.
    return DATA_ROOT / "data/TAO" / str(seq.get("split", "val")) / str(seq.get("dataset", "")) / str(seq.get("seq_name", "")) / image_name


def _convert_burst_to_coco_video(annotation_path: Path, output_dir: Path, split: str | None = None) -> dict[str, Any]:
    import pycocotools.mask as mask_utils

    with annotation_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    split_name = split or str(data.get("split", "val"))
    categories = data.get("categories", [])
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    videos: list[dict[str, Any]] = []
    ann_id = 1
    image_id = 1
    existing_frames = 0
    missing_frames = 0
    for seq in data.get("sequences", []):
        seq = dict(seq)
        seq["split"] = split_name
        video_id = int(seq.get("id", len(videos) + 1))
        videos.append(
            {
                "id": video_id,
                "name": seq.get("seq_name", str(video_id)),
                "dataset": seq.get("dataset"),
                "fps": seq.get("fps"),
                "width": seq.get("width"),
                "height": seq.get("height"),
            }
        )
        track_categories = {str(k): int(v) for k, v in dict(seq.get("track_category_ids", {})).items()}
        annotated_paths = list(seq.get("annotated_image_paths", []))
        segmentations = list(seq.get("segmentations", []))
        for frame_index, (image_name, frame_segmentations) in enumerate(zip(annotated_paths, segmentations)):
            frame_path = _burst_frame_path(seq, str(image_name))
            if frame_path.exists():
                existing_frames += 1
            else:
                missing_frames += 1
            current_image_id = image_id
            image_id += 1
            images.append(
                {
                    "id": current_image_id,
                    "video_id": video_id,
                    "frame_index": frame_index,
                    "file_name": str(frame_path),
                    "width": int(seq.get("width", 0) or 0),
                    "height": int(seq.get("height", 0) or 0),
                }
            )
            for track_id, seg in dict(frame_segmentations).items():
                if not isinstance(seg, dict) or not seg.get("is_gt", True):
                    continue
                category_id = track_categories.get(str(track_id))
                rle = seg.get("rle")
                if category_id is None or not rle:
                    continue
                rle_obj = {
                    "size": [int(seq.get("height", 0) or 0), int(seq.get("width", 0) or 0)],
                    "counts": str(rle).encode("ascii"),
                }
                bbox = [float(x) for x in mask_utils.toBbox(rle_obj).tolist()]
                area = float(mask_utils.area(rle_obj))
                if bbox[2] <= 0 or bbox[3] <= 0:
                    continue
                annotations.append(
                    {
                        "id": ann_id,
                        "image_id": current_image_id,
                        "video_id": video_id,
                        "track_id": int(track_id),
                        "category_id": int(category_id),
                        "bbox": bbox,
                        "area": area,
                        "iscrowd": 0,
                        "frame_index": frame_index,
                    }
                )
                ann_id += 1
    converted = {
        "videos": videos,
        "images": images,
        "annotations": annotations,
        "categories": categories,
        "source": {
            "format": "BURST-sequences",
            "annotation_file": str(annotation_path),
            "split": split_name,
            "note": "Converted from BURST RLE masks to box-level COCO-video rows for PARC-Track scaffold inspection.",
        },
    }
    out_json = ensure_data_output(output_dir / f"burst_{split_name}_box_annotations.json")
    with out_json.open("w", encoding="utf-8") as handle:
        json.dump(converted, handle, ensure_ascii=False)
    return {
        "converted_ann_file": str(out_json),
        "num_videos": len(videos),
        "num_frames": len(images),
        "num_boxes": len(annotations),
        "num_categories": len(categories),
        "existing_frame_paths": existing_frames,
        "missing_frame_paths": missing_frames,
    }


def inspect_third_dataset(
    dataset: str = "BURST",
    out_dir: str | Path | None = None,
    root: str | Path | None = None,
    ann_file: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase7_third_dataset")
    dataset_key = dataset.upper()
    roots = [Path(root)] if root else _third_dataset_roots(dataset_key)
    existing_roots = [candidate for candidate in roots if candidate.exists()]
    report_path = ensure_data_output(output_dir / f"dataset_adapter_report_{dataset_key.lower().replace('-', '_')}.json")
    missing_path = ensure_data_output(output_dir / "missing_data_report.json")

    if not existing_roots:
        report = {
            "dataset_name": dataset_key,
            "status": "missing_files",
            "reason": "dataset_root_missing",
            "checked_roots": [str(path) for path in roots],
            "next_step": "download_or_mount_dataset_before_running_proposal_generation",
        }
        write_json(report_path, report)
        write_json(missing_path, report)
        return report

    root_path = existing_roots[0]
    json_candidates = [Path(ann_file)] if ann_file else _find_json_files(root_path)
    json_candidates = [path for path in json_candidates if path.exists()]
    if json_candidates:
        # Prefer COCO-video compatible files when present; otherwise report that
        # a dataset-specific converter is required.
        for candidate in json_candidates[:20]:
            try:
                report = inspect_coco_video_dataset(dataset_key, root_path, candidate, "coco_video_or_tracking_json")
            except Exception:
                continue
            if report.get("status") == "tracking_layout_ok":
                report["third_dataset_role"] = "adapter_ready"
                write_json(report_path, report)
                return report
        for candidate in json_candidates[:20]:
            try:
                with candidate.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception:
                continue
            if dataset_key == "BURST" and _is_burst_sequence_json(data):
                converted = _convert_burst_to_coco_video(candidate, output_dir, split=str(data.get("split", "val")))
                report = {
                    "dataset_name": dataset_key,
                    "dataset_root": str(root_path),
                    "ann_file": str(candidate),
                    "status": "tracking_layout_ok" if converted["existing_frame_paths"] > 0 and converted["num_boxes"] > 0 else "missing_files",
                    "reason": "" if converted["existing_frame_paths"] > 0 and converted["num_boxes"] > 0 else "converted_boxes_or_frames_missing",
                    "annotation_format": "burst_sequence_rle_converted_to_coco_video_boxes",
                    "annotation_mode": "partial_or_unknown",
                    "has_video_frames": converted["existing_frame_paths"] > 0,
                    "has_tracking_annotations": converted["num_boxes"] > 0,
                    "has_track_ids": converted["num_boxes"] > 0,
                    "has_category_labels": converted["num_categories"] > 0,
                    "has_frame_indices": converted["num_frames"] > 0,
                    "has_video_ids": converted["num_videos"] > 0,
                    "third_dataset_role": "adapter_ready_box_scaffold",
                    **converted,
                    "errors": [],
                }
                write_json(report_path, report)
                return report
        report = {
            "dataset_name": dataset_key,
            "dataset_root": str(root_path),
            "status": "requires_dataset_specific_converter",
            "reason": "json_files_found_but_not_coco_video_tracking_layout",
            "json_files_checked": [str(path) for path in json_candidates[:20]],
            "num_json_files_found": len(json_candidates),
        }
        write_json(report_path, report)
        return report

    report = {
        "dataset_name": dataset_key,
        "dataset_root": str(root_path),
        "status": "missing_files",
        "reason": "annotation_json_missing",
        "checked_roots": [str(path) for path in roots],
    }
    write_json(report_path, report)
    write_json(missing_path, report)
    return report


def run_stability_v2(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/milestones/ijcv_stability_v2")
    anytime = run_anytime_demo(DATA_ROOT / "outputs/phase7_anytime")
    burst_ann = DATA_ROOT / "data/BURST/val/all_classes.json"
    third = inspect_third_dataset(
        "BURST",
        DATA_ROOT / "outputs/phase7_third_dataset",
        root=DATA_ROOT / "data/BURST",
        ann_file=burst_ann if burst_ann.exists() else None,
    )
    second = run_second_rater_agreement(DATA_ROOT / "outputs/phase4_second_rater")

    copied: list[Path] = []
    sources = [
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/manifest.json",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/RUN_REPORT.md",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/table_main_bootstrap_ci.csv",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/table_worst_case_cons_ftr.csv",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/table_mondrian_ablation_summary.csv",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/table_per_class_breakdown.csv",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/table_prop5_three_generator.csv",
        DATA_ROOT / "outputs/milestones/ijcv_stability_v1/table_hota_scope_meanstd.csv",
        DATA_ROOT / "outputs/phase7_anytime/table_anytime_release.csv",
        DATA_ROOT / "outputs/phase7_anytime/table_anytime_first_release.csv",
        DATA_ROOT / "outputs/phase7_anytime/figure_anytime_release_curve.csv",
        DATA_ROOT / "outputs/phase7_third_dataset/dataset_adapter_report_burst.json",
        DATA_ROOT / "outputs/phase7_third_dataset/missing_data_report.json",
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_agreement.csv",
        DATA_ROOT / "outputs/phase4_second_rater/second_rater_disagreements.csv",
    ]
    for src in sources:
        dst = _copy_if_exists(src, output_dir)
        if dst is not None:
            copied.append(dst)

    manifest_rows = [
        {"file": str(path.relative_to(output_dir)), "sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in copied
    ]
    manifest_sha = ensure_data_output(output_dir / "MANIFEST_SHA256.txt")
    manifest_sha.write_text(
        "\n".join(f"{row['sha256']}  {row['file']}" for row in manifest_rows if row["sha256"]) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "ijcv_stability_v2",
        "contains_raw_data": False,
        "contains_model_weights": False,
        "contains_hf_cache": False,
        "anytime_status": anytime.get("status"),
        "third_dataset_status": third.get("status"),
        "third_dataset_name": third.get("dataset_name", "BURST"),
        "second_rater_status": second.get("status"),
        "second_rater_labeled": second.get("n_second_rater_labeled"),
        "files": manifest_rows,
    }
    write_json(output_dir / "manifest.json", manifest)
    report = ensure_data_output(output_dir / "RUN_REPORT.md")
    report.write_text(
        "# IJCV Stability v2\n\n"
        "- Adds Phase-7 anytime-valid release diagnostic and third-dataset adapter status.\n"
        f"- Anytime status: `{anytime.get('status')}`.\n"
        f"- Third dataset status: `{third.get('status')}` for `{third.get('dataset_name', 'BURST')}`.\n"
        f"- Second-rater status: `{second.get('status')}` with `{second.get('n_second_rater_labeled')}` labeled rows.\n"
        "- Raw videos, raw annotations, model weights, HF cache, and frame caches are excluded.\n",
        encoding="utf-8",
    )
    copied.extend([manifest_sha, output_dir / "manifest.json", report])

    packages = ensure_data_output(DATA_ROOT / "outputs/packages")
    package_path = packages / "ijcv_stability_v2.tar.gz"
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
        "package": str(package_path),
        "package_sha256": package_sha,
        "anytime": anytime,
        "third_dataset": third,
        "second_rater": second,
        "copied_files": len(copied),
    }
    write_json(output_dir / "ijcv_stability_v2_summary.json", summary)
    return summary


def _csv_row_count(path: Path) -> int | None:
    try:
        return int(sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
    except Exception:
        return None


def _candidate_file_hashes(output_dir: Path) -> dict[str, Any]:
    files = [
        output_dir / "candidate_universe.csv",
        output_dir / "candidate_scores.csv",
        output_dir / "candidate_nodes.csv",
    ]
    rows: list[dict[str, Any]] = []
    for path in files:
        if not path.exists():
            rows.append({"file": str(path), "exists": False})
            continue
        rows.append(
            {
                "file": str(path),
                "exists": True,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "rows": _csv_row_count(path),
            }
        )
    return {"files": rows}


def _write_burst_empty_diagnostics(matrix_csv: Path, out_csv: Path) -> dict[str, Any]:
    if not matrix_csv.exists():
        pd.DataFrame().to_csv(ensure_data_output(out_csv), index=False)
        return {"status": "missing_matrix", "path": str(out_csv), "rows": 0}
    matrix = pd.read_csv(matrix_csv)
    if matrix.empty or "released" not in matrix:
        pd.DataFrame().to_csv(ensure_data_output(out_csv), index=False)
        return {"status": "empty_matrix", "path": str(out_csv), "rows": 0}
    released = pd.to_numeric(matrix["released"], errors="coerce").fillna(0)
    cols = [
        "method",
        "alpha1",
        "seed",
        "candidate_budget_M",
        "released",
        "release_feasible",
        "p_min_effective",
        "gamma_star_eff",
        "emax_effective",
        "required_emax",
        "max_observed_e",
        "best_margin",
        "best_margin_k",
        "best_margin_tau",
        "empty_reason",
        "empty_diagnostic",
        "n_cal_total",
        "n_covered",
        "n_excluded_empty",
        "n_rank_denominator",
    ]
    keep = [col for col in cols if col in matrix.columns]
    empty = matrix.loc[released <= 0, keep].copy()
    empty.to_csv(ensure_data_output(out_csv), index=False)
    return {"status": "completed", "path": str(out_csv), "rows": int(len(empty))}


def _write_burst_certification_summary(matrix_csv: Path, out_csv: Path) -> dict[str, Any]:
    if not matrix_csv.exists():
        pd.DataFrame().to_csv(ensure_data_output(out_csv), index=False)
        return {"status": "missing_matrix", "path": str(out_csv), "rows": 0}
    matrix = pd.read_csv(matrix_csv)
    if matrix.empty:
        matrix.to_csv(ensure_data_output(out_csv), index=False)
        return {"status": "empty_matrix", "path": str(out_csv), "rows": 0}
    group_cols = [col for col in ["method", "alpha1", "candidate_budget_M"] if col in matrix.columns]
    if not group_cols:
        matrix.to_csv(ensure_data_output(out_csv), index=False)
        return {"status": "no_group_columns", "path": str(out_csv), "rows": int(len(matrix))}
    value_cols = {
        "released": ("released", "mean"),
        "utr": ("utr", "mean"),
        "conservative_ftr_uncertain_and_unlabeled_false": (
            "conservative_ftr_uncertain_and_unlabeled_false",
            "mean",
        ),
        "self_consistency_margin": ("self_consistency_margin", "mean"),
        "release_feasible": ("release_feasible", lambda s: float(pd.Series(s).astype(bool).mean())),
    }
    agg: dict[str, Any] = {}
    for out_name, (col, fn) in value_cols.items():
        if col in matrix.columns:
            agg[f"{out_name}_mean" if out_name != "release_feasible" else "release_feasible_rate"] = (col, fn)
    if "released" in matrix.columns:
        agg["nonempty_rate"] = ("released", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) > 0).mean()))
    summary = matrix.groupby(group_cols, dropna=False).agg(**agg).reset_index() if agg else matrix[group_cols].drop_duplicates()
    summary.to_csv(ensure_data_output(out_csv), index=False)
    return {"status": "completed", "path": str(out_csv), "rows": int(len(summary))}


def run_burst_milestone(
    output_dir: str | Path | None = None,
    source_dir: str | Path | None = None,
    third_dataset_dir: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_dir) if source_dir else DATA_ROOT / "outputs/phase7_burst"
    third = Path(third_dataset_dir) if third_dataset_dir else DATA_ROOT / "outputs/phase7_third_dataset"
    milestone = ensure_data_output(output_dir or DATA_ROOT / "outputs/milestones/ijcv_burst_v1")
    matrix_csv = source / "burst_alpha_seed_m_matrix.csv"
    if not matrix_csv.exists():
        legacy = source / "ovtb_alpha_seed_m_matrix.csv"
        matrix_csv = legacy if legacy.exists() else matrix_csv

    hashes = _candidate_file_hashes(source)
    write_json(milestone / "candidate_universe_hashes.json", hashes)
    empty_info = _write_burst_empty_diagnostics(matrix_csv, milestone / "table_burst_empty_diagnostics.csv")
    summary_info = _write_burst_certification_summary(matrix_csv, milestone / "table_burst_certification_summary.csv")

    copied: list[Path] = []
    sources = [
        third / "dataset_adapter_report_burst.json",
        source / "audit_manifest.json",
        source / "audit_candidates.csv",
        source / "audit_labels.csv",
        source / "audit_summary.csv",
        source / "burst_audit200_with_release_coverage_candidates.csv",
        source / "burst_audit200_with_release_coverage_labels.csv",
        source / "burst_audit200_summary.csv",
        source / "burst_released_unsupported_audit_candidates.csv",
        source / "burst_released_unsupported_audit_labels.csv",
        source / "burst_released_unsupported_audit_candidates_manifest.json",
        source / "table_burst_released_unsupported_audit_summary.csv",
        source / "table_burst_prop5_mass_ratio.csv",
        source / "table_burst_cross_generator_prop5.csv",
        matrix_csv,
        source / "table_baseline_expanded.csv",
        source / "table_alpha_sweep.csv",
        source / "run_merge_shards.log",
        source / "run_phase3_matrix.log",
        source / "build_logs/build_ext_groundingdino_sm86.log",
        source / "shards/logs/shard0.log",
        source / "shards/logs/shard1.log",
        source / "shards/logs/shard2.log",
        source / "shards/logs/shard3.log",
        Path("/home/waas/paper_experiments/configs/phase7_burst_audit.yaml"),
        Path("/home/waas/paper_experiments/configs/phase7_burst_matrix.yaml"),
        Path("/home/waas/paper_experiments/configs/phase7_burst_owlv2_audit.yaml"),
        Path("/home/waas/paper_experiments/configs/phase7_burst_owlv2_matrix.yaml"),
        Path("/home/waas/paper_experiments/scripts/merge_phase2_shards.py"),
    ]
    for src in sources:
        dst = _copy_if_exists(src, milestone)
        if dst is not None:
            copied.append(dst)

    run_report = ensure_data_output(milestone / "RUN_REPORT.md")
    milestone_name = milestone.name
    has_reviewed_audit = (source / "burst_audit200_with_release_coverage_labels.csv").exists()
    run_report.write_text(
        f"# {milestone_name}\n\n"
        "- Dataset: BURST val box-level scaffold converted from official RLE masks.\n"
        "- Proposal generator: GroundingDINO scaffold, 8 frames/video, 3 classes/video.\n"
        "- Proposal execution: four-way sharded run with `video_stride=4`, one process per A10G via `CUDA_VISIBLE_DEVICES`.\n"
        "- Environment note: GroundingDINO `_C` was rebuilt with `TORCH_CUDA_ARCH_LIST=8.6` for A10G compatibility.\n"
        "- Main protocol: fixed global `M=150`, `alpha1 in {0.10, 0.20}`, seeds `{0,1,2}`.\n"
        + (
            "- Audit status: 200 model-assisted visual audit labels are included; all released-unsupported paths are covered by the release audit table.\n"
            if has_reviewed_audit
            else "- Audit labels are template-only until reviewed; audited/conservative FTR is not final evidence before labels exist.\n"
        )
        + "- Candidate universe CSVs are represented by hashes to avoid packaging large derived files.\n"
        "- Raw frames, raw BURST annotations, model weights, HF/GroundingDINO caches are excluded.\n",
        encoding="utf-8",
    )
    copied.append(run_report)

    file_rows = []
    for path in sorted(milestone.rglob("*")):
        if not path.is_file():
            continue
        file_rows.append(
            {
                "file": str(path.relative_to(milestone)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest_sha = ensure_data_output(milestone / "MANIFEST_SHA256.txt")
    manifest_sha.write_text(
        "\n".join(f"{row['sha256']}  {row['file']}" for row in file_rows if row["sha256"]) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "status": milestone_name,
        "source_dir": str(source),
        "matrix_csv": str(matrix_csv) if matrix_csv.exists() else None,
        "contains_raw_data": False,
        "contains_model_weights": False,
        "contains_hf_cache": False,
        "contains_candidate_universe_hashes": True,
        "audit_status": "model_assisted_visual_audit" if has_reviewed_audit else "template_only_until_reviewed",
        "empty_diagnostics": empty_info,
        "certification_summary": summary_info,
        "candidate_hashes": hashes,
        "files": file_rows,
    }
    write_json(milestone / "manifest.json", manifest)

    packages = ensure_data_output(DATA_ROOT / "outputs/packages")
    package_path = packages / f"{milestone_name}.tar.gz"
    with tarfile.open(package_path, "w:gz") as tar:
        tar.add(milestone, arcname=milestone.name)
    package_sha = _sha256(package_path)
    (package_path.with_suffix(package_path.suffix + ".sha256")).write_text(
        f"{package_sha}  {package_path.name}\n",
        encoding="utf-8",
    )
    result = {
        "status": "completed",
        "output_dir": str(milestone),
        "package": str(package_path),
        "package_sha256": package_sha,
        "copied_files": len(copied),
        "empty_diagnostics": empty_info,
        "certification_summary": summary_info,
    }
    write_json(milestone / f"{milestone_name}_summary.json", result)
    return result
