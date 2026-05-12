from __future__ import annotations

import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output, load_yaml, write_json
from .phase2 import _load_universe_with_labels, _split_video_ids
from .phase4 import _base_entries, _select_from_evalues, _test_pool


DATA_ROOT = Path("<PARC_ROOT>")
TRACK_EVAL_ROOT = DATA_ROOT / "third_party/TrackEval"
PARC_METHOD = "PARC"
CONF_METHOD = "confidence_top_m"


def _safe_alpha(alpha: float) -> str:
    return str(float(alpha)).replace(".", "p")


def _base_entry(dataset: str, generator: str) -> dict[str, Any]:
    for entry in _base_entries():
        if entry["dataset"] == dataset and entry["generator"] == generator:
            return entry
    raise ValueError(f"unknown dataset/generator entry: {dataset}/{generator}")


def _seq_name(video_id: int) -> str:
    return f"v{int(video_id):06d}"


def _load_annotation_bundle(ann_file: Path) -> dict[str, Any]:
    with ann_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    videos = {int(v["id"]): v for v in data.get("videos", [])}
    images_by_video: dict[int, list[dict[str, Any]]] = {}
    image_to_frame: dict[int, int] = {}
    image_to_video: dict[int, int] = {}
    for image in data.get("images", []):
        video_id = int(image["video_id"])
        image_id = int(image["id"])
        frame_index = int(image.get("frame_index", image.get("frame_id", 0)))
        image_to_frame[image_id] = frame_index
        image_to_video[image_id] = video_id
        images_by_video.setdefault(video_id, []).append(image)
    anns_by_video: dict[int, list[dict[str, Any]]] = {}
    for ann in data.get("annotations", []):
        video_id = int(ann.get("video_id", image_to_video.get(int(ann["image_id"]), -1)))
        anns_by_video.setdefault(video_id, []).append(ann)
    return {
        "videos": videos,
        "images_by_video": images_by_video,
        "image_to_frame": image_to_frame,
        "anns_by_video": anns_by_video,
    }


def _video_seq_length(images: list[dict[str, Any]], anns: list[dict[str, Any]], image_to_frame: dict[int, int]) -> int:
    frame_indices = [int(img.get("frame_index", img.get("frame_id", 0))) for img in images]
    frame_indices += [int(image_to_frame.get(int(ann["image_id"]), 0)) for ann in anns]
    return max(frame_indices) + 1 if frame_indices else 1


def _write_seqinfo(path: Path, seq_name: str, video: dict[str, Any] | None, seq_length: int) -> None:
    width = int(video.get("width", 1920)) if video else 1920
    height = int(video.get("height", 1080)) if video else 1080
    content = "\n".join(
        [
            "[Sequence]",
            f"name={seq_name}",
            "imDir=img1",
            "frameRate=30",
            f"seqLength={int(seq_length)}",
            f"imWidth={width}",
            f"imHeight={height}",
            "imExt=.jpg",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def _write_gt_file(path: Path, anns: list[dict[str, Any]], image_to_frame: dict[int, int]) -> int:
    rows = []
    for ann in anns:
        bbox = ann.get("bbox", [0, 0, 0, 0])
        frame = int(image_to_frame.get(int(ann["image_id"]), 0)) + 1
        track_id = int(ann.get("track_id", ann.get("id", 0))) + 1
        rows.append(
            [
                frame,
                track_id,
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
                1,
                1,
                1.0,
            ]
        )
    rows.sort(key=lambda row: (row[0], row[1]))
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                f"{int(row[0])},{int(row[1])},{row[2]:.3f},{row[3]:.3f},{row[4]:.3f},{row[5]:.3f},{int(row[6])},{int(row[7])},{row[8]:.3f}\n"
            )
    return len(rows)


def _selected_paths(entry: dict[str, Any], cfg: dict[str, Any], universe: pd.DataFrame, method: str, alpha: float, seed: int, budget: int) -> pd.DataFrame:
    if method == PARC_METHOD:
        return _select_from_evalues(entry, alpha, seed, budget)
    if method == CONF_METHOD:
        return _test_pool(cfg, universe, seed, budget).copy()
    raise ValueError(f"unknown TrackEval export method: {method}")


def _write_tracker_files(
    tracker_root: Path,
    seq_names_by_video: dict[int, str],
    nodes: pd.DataFrame,
    selected: pd.DataFrame,
) -> int:
    tracker_root.mkdir(parents=True, exist_ok=True)
    selected_ids = set(selected["path_id"].astype(str).tolist()) if not selected.empty else set()
    selected_nodes = nodes[nodes["path_id"].astype(str).isin(selected_ids)].copy() if selected_ids else nodes.iloc[[]].copy()
    if not selected_nodes.empty:
        selected_nodes["seq_name"] = selected_nodes["video_id"].astype(int).map(seq_names_by_video)
        selected_nodes = selected_nodes[selected_nodes["seq_name"].notna()].copy()
    total_rows = 0
    for video_id, seq_name in seq_names_by_video.items():
        path = tracker_root / f"{seq_name}.txt"
        vnodes = selected_nodes[selected_nodes["video_id"].astype(int) == int(video_id)].copy() if not selected_nodes.empty else selected_nodes
        if vnodes.empty:
            path.write_text("", encoding="utf-8")
            continue
        path_id_map = {pid: idx + 1 for idx, pid in enumerate(sorted(vnodes["path_id"].astype(str).unique().tolist()))}
        vnodes["track_num_id"] = vnodes["path_id"].astype(str).map(path_id_map)
        vnodes = vnodes.sort_values(["frame_index", "track_num_id", "node_index"])
        with path.open("w", encoding="utf-8") as handle:
            for _, row in vnodes.iterrows():
                frame = int(row["frame_index"]) + 1
                conf = float(row.get("score", 1.0))
                handle.write(
                    f"{frame},{int(row['track_num_id'])},{float(row['bbox_x']):.3f},{float(row['bbox_y']):.3f},"
                    f"{float(row['bbox_w']):.3f},{float(row['bbox_h']):.3f},{conf:.6f},1,-1,-1\n"
                )
                total_rows += 1
    return total_rows


def export_motchallenge_trackeval(
    dataset: str = "OVT-B",
    generator: str = "GroundingDINO",
    alpha: float = 0.10,
    seed: int = 0,
    budget: int = 150,
    out_dir: str | Path | None = None,
    methods: list[str] | None = None,
) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase5_trackeval")
    methods = methods or [PARC_METHOD, CONF_METHOD]
    entry = _base_entry(dataset, generator)
    cfg = load_yaml(entry["config"])
    universe = _load_universe_with_labels(cfg)
    run_cfg = json.loads(json.dumps(cfg))
    run_cfg.setdefault("splits", {})["seed"] = int(seed)
    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), run_cfg)
    universe = universe.copy()
    universe["split"] = universe["video_id"].astype(int).map(split_map)
    test_video_ids = sorted(universe.loc[universe["split"] == "test", "video_id"].astype(int).unique().tolist())
    ann = _load_annotation_bundle(Path(entry["ann_file"]))
    selections: dict[str, pd.DataFrame] = {}
    selected_counts: dict[str, int] = {}
    selected_categories: set[int] = set()
    for method in methods:
        selected = _selected_paths(entry, cfg, universe, method, alpha, seed, budget)
        selections[method] = selected
        selected_counts[method] = int(len(selected))
        if "category_id" in selected.columns and not selected.empty:
            selected_categories.update(selected["category_id"].dropna().astype(int).tolist())
    # Keep only processed test videos that have GT annotations. Empty tracker files are
    # still written for these videos when a method releases nothing in a sequence.
    test_video_ids = [vid for vid in test_video_ids if vid in ann["anns_by_video"]]
    benchmark = f"PARC_{dataset.replace('-', '')}_{generator}_a{_safe_alpha(alpha)}_s{seed}_m{budget}"
    split = "train"
    work_root = output_dir / "work" / benchmark
    if work_root.exists():
        shutil.rmtree(work_root)
    gt_root = work_root / "gt" / "mot_challenge"
    tracker_root = work_root / "trackers" / "mot_challenge"
    seqmap_dir = gt_root / "seqmaps"
    seqmap_dir.mkdir(parents=True, exist_ok=True)
    split_root = gt_root / f"{benchmark}-{split}"
    tracker_split_root = tracker_root / f"{benchmark}-{split}"
    seq_names_by_video = {vid: _seq_name(vid) for vid in test_video_ids}
    gt_rows = 0
    for video_id, seq_name in seq_names_by_video.items():
        seq_dir = split_root / seq_name
        gt_dir = seq_dir / "gt"
        gt_dir.mkdir(parents=True, exist_ok=True)
        anns = ann["anns_by_video"].get(video_id, [])
        if dataset == "TAO" and selected_categories:
            anns = [ann_row for ann_row in anns if int(ann_row.get("category_id", -1)) in selected_categories]
        images = ann["images_by_video"].get(video_id, [])
        seq_length = _video_seq_length(images, anns, ann["image_to_frame"])
        _write_seqinfo(seq_dir / "seqinfo.ini", seq_name, ann["videos"].get(video_id), seq_length)
        gt_rows += _write_gt_file(gt_dir / "gt.txt", anns, ann["image_to_frame"])
    seqmap = seqmap_dir / f"{benchmark}-{split}.txt"
    with seqmap.open("w", encoding="utf-8") as handle:
        handle.write("name\n")
        for seq_name in seq_names_by_video.values():
            handle.write(f"{seq_name}\n")
    nodes = pd.read_csv(entry["candidate_nodes"])
    node_cols = {"bbox_x", "bbox_y", "bbox_w", "bbox_h", "frame_index", "path_id", "video_id"}
    missing = sorted(node_cols - set(nodes.columns))
    if missing:
        raise ValueError(f"candidate_nodes missing required columns: {missing}")
    tracker_rows: dict[str, int] = {}
    for method in methods:
        selected = selections[method]
        tracker_name = f"{method}_a{_safe_alpha(alpha)}_s{seed}_m{budget}"
        tracker_rows[method] = _write_tracker_files(
            tracker_split_root / tracker_name / "data",
            seq_names_by_video,
            nodes,
            selected,
        )
    manifest = {
        "status": "exported",
        "dataset": dataset,
        "generator": generator,
        "alpha": alpha,
        "seed": seed,
        "candidate_budget_M": budget,
        "benchmark": benchmark,
        "split": split,
        "gt_folder": str(gt_root),
        "trackers_folder": str(tracker_root),
        "seqmap_file": str(seqmap),
        "work_root": str(work_root),
        "output_folder": str(work_root / "results"),
        "trackers_to_eval": [f"{method}_a{_safe_alpha(alpha)}_s{seed}_m{budget}" for method in methods],
        "num_sequences": len(seq_names_by_video),
        "gt_rows": int(gt_rows),
        "tracker_rows": tracker_rows,
        "selected_counts": selected_counts,
        "selected_categories": sorted(selected_categories),
        "class_agnostic_motchallenge_note": "GT and tracker classes are exported as pedestrian/class=1 with DO_PREPROC=False.",
        "tao_supported_subset_note": "For TAO, GT is restricted to categories present in the exported predictions." if dataset == "TAO" else None,
    }
    write_json(output_dir / f"export_manifest_{benchmark}.json", manifest)
    return manifest


def _summarize_trackeval_result(result: dict[str, Any], dataset_name: str, tracker: str) -> dict[str, Any]:
    tracker_res = result.get(dataset_name, {}).get(tracker)
    if tracker_res is None:
        return {"tracker": tracker, "status": "failed"}
    combined = tracker_res["COMBINED_SEQ"]["pedestrian"]
    hota = combined.get("HOTA", {})
    clear = combined.get("CLEAR", {})
    identity = combined.get("Identity", {})

    def mean_array(value: Any) -> float | None:
        if value is None:
            return None
        arr = np.asarray(value, dtype=float)
        return float(np.nanmean(arr)) if arr.size else None

    return {
        "tracker": tracker,
        "method": CONF_METHOD if tracker.startswith(CONF_METHOD) else PARC_METHOD,
        "status": "success",
        "HOTA": mean_array(hota.get("HOTA")),
        "HOTA_0": float(hota.get("HOTA(0)")) if hota.get("HOTA(0)") is not None else None,
        "DetA": mean_array(hota.get("DetA")),
        "AssA": mean_array(hota.get("AssA")),
        "LocA": mean_array(hota.get("LocA")),
        "MOTA": float(clear.get("MOTA")) if clear.get("MOTA") is not None else None,
        "MOTP": float(clear.get("MOTP")) if clear.get("MOTP") is not None else None,
        "CLR_TP": float(clear.get("CLR_TP")) if clear.get("CLR_TP") is not None else None,
        "CLR_FP": float(clear.get("CLR_FP")) if clear.get("CLR_FP") is not None else None,
        "CLR_FN": float(clear.get("CLR_FN")) if clear.get("CLR_FN") is not None else None,
        "IDSW": float(clear.get("IDSW")) if clear.get("IDSW") is not None else None,
        "IDF1": float(identity.get("IDF1")) if identity.get("IDF1") is not None else None,
        "IDP": float(identity.get("IDP")) if identity.get("IDP") is not None else None,
        "IDR": float(identity.get("IDR")) if identity.get("IDR") is not None else None,
    }


def run_trackeval_motchallenge(
    dataset: str = "OVT-B",
    generator: str = "GroundingDINO",
    alpha: float = 0.10,
    seed: int = 0,
    budget: int = 150,
    out_dir: str | Path | None = None,
    methods: list[str] | None = None,
) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase5_trackeval")
    manifest = export_motchallenge_trackeval(dataset, generator, alpha, seed, budget, output_dir, methods)
    if not TRACK_EVAL_ROOT.exists():
        return {"status": "trackeval_missing", "manifest": manifest}
    sys.path.insert(0, str(TRACK_EVAL_ROOT))
    # TrackEval uses deprecated numpy aliases in the current upstream code.
    if not hasattr(np, "float"):
        np.float = float  # type: ignore[attr-defined]
    if not hasattr(np, "int"):
        np.int = int  # type: ignore[attr-defined]
    import trackeval  # type: ignore

    eval_config = trackeval.Evaluator.get_default_eval_config()
    eval_config.update(
        {
            "USE_PARALLEL": False,
            "BREAK_ON_ERROR": True,
            "PRINT_RESULTS": False,
            "PRINT_CONFIG": False,
            "TIME_PROGRESS": False,
            "OUTPUT_SUMMARY": False,
            "OUTPUT_DETAILED": False,
            "PLOT_CURVES": False,
        }
    )
    dataset_config = trackeval.datasets.MotChallenge2DBox.get_default_dataset_config()
    dataset_config.update(
        {
            "GT_FOLDER": manifest["gt_folder"],
            "TRACKERS_FOLDER": manifest["trackers_folder"],
            "OUTPUT_FOLDER": manifest["output_folder"],
            "TRACKERS_TO_EVAL": manifest["trackers_to_eval"],
            "CLASSES_TO_EVAL": ["pedestrian"],
            "BENCHMARK": manifest["benchmark"],
            "SPLIT_TO_EVAL": manifest["split"],
            "DO_PREPROC": False,
            "TRACKER_SUB_FOLDER": "data",
            "OUTPUT_SUB_FOLDER": "",
            "SEQMAP_FILE": manifest["seqmap_file"],
            "PRINT_CONFIG": False,
        }
    )
    metrics_config = {"METRICS": ["HOTA", "CLEAR", "Identity"], "THRESHOLD": 0.5}
    start = time.perf_counter()
    evaluator = trackeval.Evaluator(eval_config)
    dataset_list = [trackeval.datasets.MotChallenge2DBox(dataset_config)]
    metrics_list = [trackeval.metrics.HOTA(metrics_config), trackeval.metrics.CLEAR(metrics_config), trackeval.metrics.Identity(metrics_config)]
    result, messages = evaluator.evaluate(dataset_list, metrics_list)
    runtime = time.perf_counter() - start
    dataset_name = dataset_list[0].get_name()
    rows = []
    for tracker in manifest["trackers_to_eval"]:
        row = _summarize_trackeval_result(result, dataset_name, tracker)
        row.update(
            {
                "dataset": dataset,
                "generator": generator,
                "alpha1": alpha,
                "seed": seed,
                "candidate_budget_M": budget,
                "benchmark": manifest["benchmark"],
                "num_sequences": manifest["num_sequences"],
                "gt_rows": manifest["gt_rows"],
                "tracker_rows": manifest["tracker_rows"].get(tracker.rsplit("_a", 1)[0], None),
                "selected_count": manifest["selected_counts"].get(tracker.rsplit("_a", 1)[0], None),
            }
        )
        rows.append(row)
    table = pd.DataFrame(rows)
    table_csv = ensure_data_output(output_dir / f"trackeval_summary_{manifest['benchmark']}.csv")
    table.to_csv(table_csv, index=False)
    summary = {
        "status": "completed",
        "manifest": manifest,
        "messages": messages,
        "runtime_sec": runtime,
        "summary_csv": str(table_csv),
    }
    write_json(output_dir / f"trackeval_run_{manifest['benchmark']}.json", summary)
    shutil.rmtree(manifest["work_root"], ignore_errors=True)
    return summary


def run_trackeval_grid(out_dir: str | Path | None = None, dataset: str = "OVT-B") -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase5_trackeval")
    rows = []
    runs = []
    for alpha in [0.10, 0.20]:
        for seed in [0, 1, 2]:
            summary = run_trackeval_motchallenge(dataset=dataset, alpha=alpha, seed=seed, out_dir=output_dir)
            runs.append(summary)
            table_path = Path(summary["summary_csv"])
            rows.append(pd.read_csv(table_path))
    merged = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    dataset_slug = dataset.lower().replace("-", "")
    out_csv = ensure_data_output(output_dir / f"table_trackeval_{dataset_slug}.csv")
    merged.to_csv(out_csv, index=False)
    summary_csv = ensure_data_output(output_dir / f"table_trackeval_{dataset_slug}_meanstd.csv")
    if not merged.empty:
        grouped = (
            merged.groupby(["dataset", "generator", "method", "alpha1"], dropna=False)[
                ["HOTA", "HOTA_0", "DetA", "AssA", "LocA", "MOTA", "MOTP", "IDF1", "IDP", "IDR", "IDSW", "CLR_TP", "CLR_FP", "CLR_FN"]
            ]
            .agg(["mean", "std"])
            .reset_index()
        )
        grouped.columns = [
            "_".join(str(part) for part in col if str(part)) if isinstance(col, tuple) else str(col)
            for col in grouped.columns
        ]
        grouped.to_csv(summary_csv, index=False)
    else:
        pd.DataFrame().to_csv(summary_csv, index=False)
    result = {"status": "completed", "dataset": dataset, "table": str(out_csv), "summary": str(summary_csv), "runs": len(runs)}
    write_json(output_dir / f"trackeval_grid_summary_{dataset_slug}.json", result)
    return result
