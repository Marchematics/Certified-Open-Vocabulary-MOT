from __future__ import annotations

import csv
from collections import Counter, defaultdict
from html import escape
import json
from math import log
from pathlib import Path
import random
from typing import Any

import pandas as pd

from .adapters.datasets import ensure_data_output, inspect_dataset_from_config, load_yaml, write_json


AUDIT_COLUMNS = [
    "dataset",
    "video_id",
    "path_id",
    "query",
    "category_id",
    "score",
    "objectness",
    "semantic_margin",
    "temporal_stability",
    "association_score",
    "matched_gt_id",
    "matched_iou",
    "temporal_overlap",
    "is_unmatched",
    "cell_id",
    "novelty_bin",
    "query_cluster",
    "occ_bin",
    "domain_bin",
    "frame_start",
    "frame_end",
    "clip_path",
    "montage_path",
]

CANDIDATE_UNIVERSE_COLUMNS = [
    "dataset",
    "video_id",
    "path_id",
    "split",
    "query",
    "category_id",
    "score",
    "objectness",
    "semantic_margin",
    "temporal_stability",
    "association_score",
    "frame_start",
    "frame_end",
    "path_length",
    "candidate_rank",
    "is_dummy",
    "matched_gt_id",
    "matched_iou",
    "temporal_overlap",
    "matched_frames",
    "is_matched_to_gt",
    "is_unmatched",
    "audit_label",
    "verified_positive_for_calibration",
    "cell_id",
    "novelty_bin",
    "query_cluster",
    "occ_bin",
    "domain_bin",
    "fallback_level",
    "score_source",
]

CANDIDATE_SCORE_COLUMNS = [
    "video_id",
    "path_id",
    "release_checkpoint",
    "score_total",
    "score_obj",
    "score_sem",
    "score_temp",
    "score_assoc",
]

CANDIDATE_NODE_COLUMNS = [
    "video_id",
    "path_id",
    "node_index",
    "image_id",
    "frame_index",
    "image_path",
    "bbox_x",
    "bbox_y",
    "bbox_w",
    "bbox_h",
    "score",
]

RELEASE_AUDIT_COLUMNS = AUDIT_COLUMNS + [
    "method",
    "candidate_budget_M",
    "selected_rank",
    "e_value",
    "p_any",
    "p_block",
    "tau_k",
    "self_consistency_margin",
    "release_source",
]

AUDIT_LABEL_COLUMNS = [
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


def iou_xywh(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def groundingdino_status(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    gd = cfg.get("groundingdino", {})
    config_file = Path(gd.get("config", "/datasets/ComfyUI/models/grounding-dino/GroundingDINO_SwinT_OGC.cfg.py"))
    weights = Path(gd.get("weights", "/datasets/ComfyUI/models/grounding-dino/groundingdino_swint_ogc.pth"))
    missing_imports = []
    for module in ("torch", "torchvision", "groundingdino"):
        try:
            __import__(module)
        except Exception as exc:
            missing_imports.append(f"{module}:{type(exc).__name__}")
    return {
        "backend": "GroundingDINO",
        "config_exists": config_file.exists(),
        "weights_exists": weights.exists(),
        "config": str(config_file),
        "weights": str(weights),
        "import_ready": not missing_imports,
        "missing_imports": missing_imports,
    }


def _proposal_backend(cfg: dict[str, Any]) -> str:
    proposal = cfg.get("proposal", {})
    backend = str(proposal.get("backend", proposal.get("backbone", "groundingdino_audit_generator"))).strip().lower()
    aliases = {
        "groundingdino": "groundingdino",
        "groundingdino_audit_generator": "groundingdino",
        "groundingdino_audit": "groundingdino",
        "owlv2": "owlv2_hf",
        "owlv2_hf": "owlv2_hf",
        "owlv2_hf_audit_generator": "owlv2_hf",
        "owlvit": "owlvit_hf",
        "owlvit_hf": "owlvit_hf",
        "owlvit_v1": "owlvit_hf",
        "owlvit_hf_audit_generator": "owlvit_hf",
    }
    if backend not in aliases:
        raise ValueError(f"unknown proposal backend/backbone: {backend}")
    return aliases[backend]


def owlv2_status(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    ow = cfg.get("owlv2", {})
    model_id = str(ow.get("model", "google/owlv2-base-patch16-ensemble"))
    device = str(ow.get("device", "cuda:0"))
    cache_dir = ow.get("cache_dir", "./cache/huggingface")
    missing_imports = []
    torch_mod = None
    for module in ("torch", "transformers", "PIL"):
        try:
            imported = __import__(module)
            if module == "torch":
                torch_mod = imported
        except Exception as exc:
            missing_imports.append(f"{module}:{type(exc).__name__}")
    cuda_required = device.startswith("cuda")
    cuda_ready = True
    cuda_device_count = None
    if torch_mod is not None:
        try:
            cuda_ready = bool(torch_mod.cuda.is_available()) if cuda_required else True
            cuda_device_count = int(torch_mod.cuda.device_count()) if hasattr(torch_mod, "cuda") else 0
        except Exception:
            cuda_ready = False if cuda_required else True
    elif cuda_required:
        cuda_ready = False
    return {
        "backend": "OWLv2",
        "model": model_id,
        "device": device,
        "cache_dir": str(cache_dir),
        "import_ready": not missing_imports,
        "missing_imports": missing_imports,
        "cuda_required": cuda_required,
        "cuda_ready": cuda_ready,
        "cuda_device_count": cuda_device_count,
        "ready": (not missing_imports) and cuda_ready,
    }


def owlvit_status(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    ow = cfg.get("owlvit", {})
    model_id = str(ow.get("model", "google/owlvit-base-patch32"))
    device = str(ow.get("device", "cuda:0"))
    cache_dir = ow.get("cache_dir", "./cache/huggingface")
    missing_imports = []
    torch_mod = None
    for module in ("torch", "transformers", "PIL"):
        try:
            imported = __import__(module)
            if module == "torch":
                torch_mod = imported
        except Exception as exc:
            missing_imports.append(f"{module}:{type(exc).__name__}")
    class_ready = True
    if not missing_imports:
        try:
            from transformers import OwlViTForObjectDetection, OwlViTProcessor  # noqa: F401
        except Exception as exc:
            class_ready = False
            missing_imports.append(f"transformers.OwlViT:{type(exc).__name__}")
    cuda_required = device.startswith("cuda")
    cuda_ready = True
    cuda_device_count = None
    if torch_mod is not None:
        try:
            cuda_ready = bool(torch_mod.cuda.is_available()) if cuda_required else True
            cuda_device_count = int(torch_mod.cuda.device_count()) if hasattr(torch_mod, "cuda") else 0
        except Exception:
            cuda_ready = False if cuda_required else True
    elif cuda_required:
        cuda_ready = False
    return {
        "backend": "OWL-ViT",
        "model": model_id,
        "device": device,
        "cache_dir": str(cache_dir),
        "import_ready": not missing_imports,
        "class_ready": class_ready,
        "missing_imports": missing_imports,
        "cuda_required": cuda_required,
        "cuda_ready": cuda_ready,
        "cuda_device_count": cuda_device_count,
        "ready": (not missing_imports) and cuda_ready and class_ready,
    }


def write_empty_audit_files(
    out_csv: str | Path,
    labels_path: str | Path,
    manifest_path: str | Path,
    reason: str,
    gd_status: dict[str, Any],
    viewer_path: str | Path = "./audit_viewer",
) -> dict[str, Any]:
    out = ensure_data_output(out_csv)
    labels = ensure_data_output(labels_path)
    manifest = ensure_data_output(manifest_path)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
    viewer = Path(viewer_path)
    index_path = ensure_data_output(viewer / "index.html")
    (viewer / "montages").mkdir(parents=True, exist_ok=True)
    (viewer / "clips").mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as handle:
        handle.write(
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>PARC-Track Audit</title>"
            "<style>body{font-family:Arial,sans-serif;margin:2rem;line-height:1.4}"
            "code{background:#f2f2f2;padding:0.1rem 0.25rem}</style></head><body>"
            "<h1>PARC-Track Audit Viewer</h1>"
            f"<p>Status: <code>not_ready</code></p><p>Reason: <code>{reason}</code></p>"
            f"<p>Candidate CSV: <code>{out}</code></p>"
            f"<p>Label template: <code>{labels}</code></p>"
            "</body></html>"
        )
    data = {
        "status": "not_ready",
        "reason": reason,
        "candidate_csv": str(out),
        "label_template_csv": str(labels),
        "viewer_index": str(index_path),
        "groundingdino": gd_status,
        "audit_columns": AUDIT_COLUMNS,
        "label_columns": AUDIT_LABEL_COLUMNS,
    }
    write_json(manifest, data)
    return data


def _load_annotation(cfg: dict[str, Any]) -> dict[str, Any]:
    ann_file = Path(cfg.get("dataset", {}).get("ann_file", ""))
    with ann_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _local_groundingdino_config(cfg: dict[str, Any]) -> str:
    gd = cfg.get("groundingdino", {})
    config_path = Path(gd.get("config", "/datasets/ComfyUI/models/grounding-dino/GroundingDINO_SwinT_OGC.cfg.py"))
    local_text = gd.get("local_text_encoder")
    if not local_text:
        return str(config_path)
    local_text_path = Path(local_text)
    required = ["config.json", "vocab.txt"]
    if not all((local_text_path / name).exists() for name in required):
        return str(config_path)
    target = Path(cfg.get("proposal", {}).get("cache_dir", "./outputs/phase2/cache"))
    target.mkdir(parents=True, exist_ok=True)
    patched = ensure_data_output(target / "GroundingDINO_SwinT_OGC.local_bert.py")
    text = config_path.read_text(encoding="utf-8")
    lines = []
    replaced = False
    for line in text.splitlines():
        if line.startswith("text_encoder_type"):
            lines.append(f"text_encoder_type = {str(local_text_path)!r}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"text_encoder_type = {str(local_text_path)!r}")
    patched.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(patched)


def _sample_evenly(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not items or count <= 0:
        return []
    if len(items) <= count:
        return items
    positions = [round(i * (len(items) - 1) / max(count - 1, 1)) for i in range(count)]
    seen = set()
    result = []
    for pos in positions:
        if pos not in seen:
            result.append(items[pos])
            seen.add(pos)
    return result


def _xyxy_to_xywh(box: list[float]) -> list[float]:
    x1, y1, x2, y2 = box
    return [float(x1), float(y1), float(max(0.0, x2 - x1)), float(max(0.0, y2 - y1))]


def _load_owlv2_detector(cfg: dict[str, Any]) -> dict[str, Any]:
    import torch
    from transformers import Owlv2ForObjectDetection, Owlv2Processor

    ow = cfg.get("owlv2", {})
    model_id = str(ow.get("model", "google/owlv2-base-patch16-ensemble"))
    device = str(ow.get("device", "cuda:0"))
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(f"OWLv2 requested {device}, but torch.cuda.is_available() is false")
    cache_dir = ow.get("cache_dir", "./cache/huggingface")
    local_files_only = bool(ow.get("local_files_only", False))
    dtype_name = str(ow.get("dtype", "")).strip().lower()
    dtype = None
    if dtype_name in {"float16", "fp16"}:
        dtype = torch.float16
    elif dtype_name in {"bfloat16", "bf16"}:
        dtype = torch.bfloat16
    elif dtype_name in {"float32", "fp32"}:
        dtype = torch.float32

    processor = Owlv2Processor.from_pretrained(
        model_id,
        cache_dir=cache_dir,
        local_files_only=local_files_only,
    )
    model_kwargs = {"cache_dir": cache_dir, "local_files_only": local_files_only}
    if dtype is not None:
        model_kwargs["torch_dtype"] = dtype
    model = Owlv2ForObjectDetection.from_pretrained(model_id, **model_kwargs)
    model.to(device)
    model.eval()
    return {"processor": processor, "model": model, "device": device, "torch": torch, "model_id": model_id}


def _load_owlvit_detector(cfg: dict[str, Any]) -> dict[str, Any]:
    import torch
    from transformers import OwlViTForObjectDetection, OwlViTProcessor

    ow = cfg.get("owlvit", {})
    model_id = str(ow.get("model", "google/owlvit-base-patch32"))
    device = str(ow.get("device", "cuda:0"))
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(f"OWL-ViT requested {device}, but torch.cuda.is_available() is false")
    cache_dir = ow.get("cache_dir", "./cache/huggingface")
    local_files_only = bool(ow.get("local_files_only", False))
    dtype_name = str(ow.get("dtype", "")).strip().lower()
    dtype = None
    if dtype_name in {"float16", "fp16"}:
        dtype = torch.float16
    elif dtype_name in {"bfloat16", "bf16"}:
        dtype = torch.bfloat16
    elif dtype_name in {"float32", "fp32"}:
        dtype = torch.float32

    processor = OwlViTProcessor.from_pretrained(
        model_id,
        cache_dir=cache_dir,
        local_files_only=local_files_only,
    )
    model_kwargs = {"cache_dir": cache_dir, "local_files_only": local_files_only}
    if dtype is not None:
        model_kwargs["torch_dtype"] = dtype
    model = OwlViTForObjectDetection.from_pretrained(model_id, **model_kwargs)
    model.to(device)
    model.eval()
    return {"processor": processor, "model": model, "device": device, "torch": torch, "model_id": model_id}


def _predict_owlv2_with_classes(
    detector: dict[str, Any],
    image_path: Path,
    classes: list[str],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    from PIL import Image

    ow = cfg.get("owlv2", {})
    threshold = float(ow.get("threshold", ow.get("score_threshold", 0.10)))
    template = str(ow.get("text_template", "a photo of a {query}"))
    prompts = [template.format(query=value, class_name=value) for value in classes]
    if not prompts:
        return []
    torch = detector["torch"]
    processor = detector["processor"]
    model = detector["model"]
    device = detector["device"]
    image = Image.open(image_path).convert("RGB")
    text_labels = [prompts]
    inputs = processor(text=text_labels, images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    target_sizes = torch.tensor([(image.height, image.width)], device=device)
    if hasattr(processor, "post_process_grounded_object_detection"):
        results = processor.post_process_grounded_object_detection(
            outputs=outputs,
            target_sizes=target_sizes,
            threshold=threshold,
            text_labels=text_labels,
        )
    else:
        results = processor.post_process_object_detection(
            outputs=outputs,
            target_sizes=target_sizes,
            threshold=threshold,
        )
    if not results:
        return []
    result = results[0]
    boxes = result.get("boxes", [])
    scores = result.get("scores", [])
    grounded_labels = result.get("text_labels")
    indexed_labels = result.get("labels")
    prompt_to_idx = {prompt: idx for idx, prompt in enumerate(prompts)}
    predictions: list[dict[str, Any]] = []
    for idx, box in enumerate(boxes):
        score = float(scores[idx].item() if hasattr(scores[idx], "item") else scores[idx])
        class_idx = -1
        if grounded_labels is not None:
            class_idx = int(prompt_to_idx.get(str(grounded_labels[idx]), -1))
        elif indexed_labels is not None:
            label_value = indexed_labels[idx]
            class_idx = int(label_value.item() if hasattr(label_value, "item") else label_value)
        if class_idx < 0 or class_idx >= len(classes):
            continue
        box_list = box.detach().cpu().tolist() if hasattr(box, "detach") else list(box)
        predictions.append({"xyxy": [float(value) for value in box_list], "score": score, "class_idx": class_idx})
    return predictions


def _predict_owlvit_with_classes(
    detector: dict[str, Any],
    image_path: Path,
    classes: list[str],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    from PIL import Image

    ow = cfg.get("owlvit", {})
    threshold = float(ow.get("threshold", ow.get("score_threshold", 0.10)))
    template = str(ow.get("text_template", "a photo of a {query}"))
    prompts = [template.format(query=value, class_name=value) for value in classes]
    if not prompts:
        return []
    torch = detector["torch"]
    processor = detector["processor"]
    model = detector["model"]
    device = detector["device"]
    image = Image.open(image_path).convert("RGB")
    inputs = processor(text=[prompts], images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    target_sizes = torch.tensor([(image.height, image.width)], device=device)
    results = processor.post_process_object_detection(
        outputs=outputs,
        target_sizes=target_sizes,
        threshold=threshold,
    )
    if not results:
        return []
    result = results[0]
    boxes = result.get("boxes", [])
    scores = result.get("scores", [])
    indexed_labels = result.get("labels", [])
    predictions: list[dict[str, Any]] = []
    for idx, box in enumerate(boxes):
        score = float(scores[idx].item() if hasattr(scores[idx], "item") else scores[idx])
        label_value = indexed_labels[idx]
        class_idx = int(label_value.item() if hasattr(label_value, "item") else label_value)
        if class_idx < 0 or class_idx >= len(classes):
            continue
        box_list = box.detach().cpu().tolist() if hasattr(box, "detach") else list(box)
        predictions.append({"xyxy": [float(value) for value in box_list], "score": score, "class_idx": class_idx})
    return predictions


def _create_montage(path: dict[str, Any], montage_path: Path, frames_per_path: int) -> None:
    import cv2
    import numpy as np

    detections = path["detections"]
    selected = _sample_evenly(detections, min(frames_per_path, len(detections)))
    tiles = []
    for det in selected:
        image = cv2.imread(det["image_path"])
        if image is None:
            continue
        x, y, w, h = [int(round(v)) for v in det["bbox"]]
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 255), 3)
        label = f"{path['query']} {det['score']:.2f}"
        cv2.putText(image, label, (max(0, x), max(24, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        image = cv2.resize(image, (320, 180))
        tiles.append(image)
    if not tiles:
        return
    while len(tiles) < frames_per_path:
        tiles.append(np.zeros_like(tiles[0]))
    rows = []
    for start in range(0, len(tiles), 4):
        rows.append(np.hstack(tiles[start : start + 4]))
    montage = np.vstack(rows)
    montage_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(montage_path), montage)


def _write_audit_index(viewer_path: Path, candidates: list[dict[str, Any]], reason: str | None = None) -> Path:
    index_path = ensure_data_output(viewer_path / "index.html")
    rows = []
    for row in candidates[:500]:
        montage = row.get("montage_path", "")
        rel = Path(montage).relative_to(viewer_path) if montage and Path(montage).is_relative_to(viewer_path) else Path(montage)
        rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('path_id', '')))}</td>"
            f"<td>{escape(str(row.get('video_id', '')))}</td>"
            f"<td>{escape(str(row.get('query', '')))}</td>"
            f"<td>{float(row.get('score', 0.0)):.3f}</td>"
            f"<td>{float(row.get('matched_iou', 0.0)):.3f}</td>"
            f"<td><img src=\"{escape(str(rel))}\" width=\"640\"></td>"
            "</tr>"
        )
    body = "".join(rows) if rows else "<tr><td colspan=\"6\">No candidates exported.</td></tr>"
    status = f"<p>Status: <code>{escape(reason)}</code></p>" if reason else "<p>Status: <code>ready</code></p>"
    with index_path.open("w", encoding="utf-8") as handle:
        handle.write(
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>PARC-Track Audit</title>"
            "<style>body{font-family:Arial,sans-serif;margin:2rem;line-height:1.4}"
            "table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:0.4rem;vertical-align:top}"
            "code{background:#f2f2f2;padding:0.1rem 0.25rem}</style></head><body>"
            "<h1>PARC-Track Audit Viewer</h1>"
            f"{status}"
            "<table><thead><tr><th>Path</th><th>Video</th><th>Query</th><th>Score</th><th>Matched IoU</th><th>Montage</th></tr></thead>"
            f"<tbody>{body}</tbody></table></body></html>"
        )
    return index_path


def _path_from_nodes(row: dict[str, Any], nodes: pd.DataFrame) -> dict[str, Any]:
    detections = []
    for _, node in nodes.sort_values("node_index").iterrows():
        detections.append(
            {
                "image_path": str(node.get("image_path", "")),
                "bbox": [
                    float(node.get("bbox_x", 0.0)),
                    float(node.get("bbox_y", 0.0)),
                    float(node.get("bbox_w", 0.0)),
                    float(node.get("bbox_h", 0.0)),
                ],
                "score": float(node.get("score", row.get("score", 0.0)) or 0.0),
                "frame_index": int(node.get("frame_index", 0) or 0),
            }
        )
    return {
        "path_id": row.get("path_id", ""),
        "query": row.get("query", ""),
        "detections": detections,
    }


def _write_csv_and_optional_parquet(rows: list[dict[str, Any]], columns: list[str], path: str | Path) -> dict[str, Any]:
    out = ensure_data_output(path)
    frame = pd.DataFrame(rows, columns=columns)
    frame.to_csv(out, index=False)
    parquet_path = out.with_suffix(".parquet")
    parquet_written = False
    try:
        frame.to_parquet(parquet_path, index=False)
        parquet_written = True
    except Exception:
        parquet_path = None
    return {
        "csv": str(out),
        "rows": int(len(frame)),
        "parquet": str(parquet_path) if parquet_written and parquet_path is not None else None,
    }


def _label_template_has_labels(labels_path: Path) -> bool:
    if not labels_path.exists():
        return False
    try:
        labels = pd.read_csv(labels_path)
    except Exception:
        return False
    if labels.empty or "label" not in labels:
        return False
    return bool(labels["label"].fillna("").astype(str).str.strip().str.len().any())


def _candidate_row_from_path(
    dataset_name: str,
    path: dict[str, Any],
    idx: int,
    anns_by_image: dict[int, list[dict[str, Any]]],
    iou_threshold: float,
    temporal_overlap_threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dets = path["detections"]
    matches = []
    best_iou = 0.0
    best_gt = ""
    for det in dets:
        frame_best = (0.0, "")
        for ann in anns_by_image.get(det["image_id"], []):
            if int(ann.get("category_id", -1)) != int(path["category_id"]):
                continue
            overlap = iou_xywh(tuple(det["bbox"]), tuple(float(v) for v in ann["bbox"]))
            if overlap > frame_best[0]:
                frame_best = (overlap, str(ann.get("track_id", "")))
        if frame_best[0] >= iou_threshold:
            matches.append(frame_best[1])
        if frame_best[0] > best_iou:
            best_iou, best_gt = frame_best
    temporal_overlap = len(matches) / max(len(dets), 1)
    is_unmatched = temporal_overlap < temporal_overlap_threshold
    score = sum(float(det["score"]) for det in dets) / max(len(dets), 1)
    path_id = f"ovtb_v{path['video_id']}_p{idx:06d}"
    path.update({"path_id": path_id, "score": score})
    row = {
        "dataset": dataset_name,
        "video_id": path["video_id"],
        "path_id": path_id,
        "split": "",
        "query": path["query"],
        "category_id": path["category_id"],
        "score": score,
        "objectness": score,
        "semantic_margin": score,
        "temporal_stability": len(dets),
        "association_score": max(0.0, min(1.0, (len(dets) - 1) / max(len(dets), 1))),
        "frame_start": min(det["frame_index"] for det in dets),
        "frame_end": max(det["frame_index"] for det in dets),
        "path_length": len(dets),
        "candidate_rank": 0,
        "is_dummy": False,
        "matched_gt_id": best_gt,
        "matched_iou": best_iou,
        "temporal_overlap": temporal_overlap,
        "matched_frames": len(matches),
        "is_matched_to_gt": not is_unmatched,
        "is_unmatched": is_unmatched,
        "audit_label": "",
        "verified_positive_for_calibration": "no",
        "cell_id": f"cat:{path['category_id']}",
        "novelty_bin": "unknown",
        "query_cluster": path["query"],
        "occ_bin": "unknown",
        "domain_bin": "global",
        "fallback_level": 0,
        "score_source": "final_score_proxy",
    }
    node_rows = []
    for node_index, det in enumerate(dets):
        bbox = det["bbox"]
        node_rows.append(
            {
                "video_id": path["video_id"],
                "path_id": path_id,
                "node_index": node_index,
                "image_id": int(det["image_id"]),
                "frame_index": int(det["frame_index"]),
                "image_path": det["image_path"],
                "bbox_x": float(bbox[0]),
                "bbox_y": float(bbox[1]),
                "bbox_w": float(bbox[2]),
                "bbox_h": float(bbox[3]),
                "score": float(det["score"]),
            }
        )
    return row, node_rows


def _run_groundingdino_audit(
    cfg: dict[str, Any],
    dataset_name: str,
    out_csv: str | Path,
    labels_path: str | Path,
    manifest_path: str | Path,
    gd_status: dict[str, Any],
    viewer_path: str | Path,
) -> dict[str, Any]:
    import cv2

    annotation = _load_annotation(cfg)
    dataset = cfg.get("dataset", {})
    proposal = cfg.get("proposal", {})
    matching = cfg.get("matching", {})
    sampling = cfg.get("sampling", {})
    audit_export = cfg.get("audit_export", {})
    phase2 = cfg.get("output", {})
    gd = cfg.get("groundingdino", {})

    root = Path(dataset.get("root", "./data/OVT-B"))
    frame_subdir = dataset.get("frame_subdir")
    if frame_subdir is None:
        dataset_name_lower = str(dataset.get("name", dataset_name)).lower()
        frame_subdir = "OVT-B" if dataset_name_lower in {"ovt-b", "ovtb"} else ""
    frame_root = root / str(frame_subdir) if str(frame_subdir) else root
    max_videos = int(proposal.get("max_videos", 50))
    frames_per_video = int(proposal.get("frames_per_video", 3))
    classes_per_video = int(proposal.get("classes_per_video", 3))
    max_det_per_frame = int(proposal.get("max_detections_per_frame", 25))
    min_path_length = int(proposal.get("min_path_length", 1))
    link_iou_threshold = float(proposal.get("link_iou_threshold", 0.3))
    max_frame_gap = int(proposal.get("max_frame_gap", 1000))
    iou_threshold = float(matching.get("iou_threshold", 0.5))
    temporal_overlap_threshold = float(matching.get("temporal_overlap_threshold", 0.3))
    total_samples = int(sampling.get("total_samples", 300))
    top_b_per_cell = int(sampling.get("top_b_per_cell", 10))
    frames_per_path = int(audit_export.get("frames_per_path", 8))
    make_montages = bool(audit_export.get("make_montages", True))
    montage_dir = Path(audit_export.get("montage_dir", "./audit_viewer/montages"))
    viewer = Path(viewer_path)
    backend = _proposal_backend(cfg)

    categories = {int(cat["id"]): cat["name"].replace("_", " ") for cat in annotation.get("categories", [])}
    images_by_video: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for image in annotation.get("images", []):
        images_by_video[int(image["video_id"])].append(image)
    for images in images_by_video.values():
        images.sort(key=lambda item: int(item.get("frame_index", item.get("frame_id", 0))))
    anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    category_counts_by_video: dict[int, Counter] = defaultdict(Counter)
    for ann in annotation.get("annotations", []):
        image_id = int(ann["image_id"])
        video_id = int(ann["video_id"])
        category_id = int(ann["category_id"])
        anns_by_image[image_id].append(ann)
        category_counts_by_video[video_id][category_id] += 1

    config_path = ""
    detector: Any
    if backend == "groundingdino":
        from groundingdino.util.inference import Model

        config_path = _local_groundingdino_config(cfg)
        detector = Model(
            model_config_path=config_path,
            model_checkpoint_path=gd_status["weights"],
            device=gd.get("device", "cuda"),
        )
    elif backend == "owlv2_hf":
        detector = _load_owlv2_detector(cfg)
        config_path = str(detector["model_id"])
    elif backend == "owlvit_hf":
        detector = _load_owlvit_detector(cfg)
        config_path = str(detector["model_id"])
    else:
        raise ValueError(f"unsupported proposal backend: {backend}")

    detections: list[dict[str, Any]] = []
    all_selected_videos = sorted(images_by_video.keys())[:max_videos]
    video_stride = max(1, int(proposal.get("video_stride", 1)))
    video_offset = int(proposal.get("video_offset", 0))
    if video_offset < 0 or video_offset >= video_stride:
        raise ValueError(f"proposal.video_offset must be in [0, video_stride); got {video_offset}/{video_stride}")
    selected_videos = [
        video_id
        for idx, video_id in enumerate(all_selected_videos)
        if idx % video_stride == video_offset
    ]
    progress_every = int(proposal.get("progress_every", 0))
    for video_pos, video_id in enumerate(selected_videos, start=1):
        if progress_every > 0 and (video_pos == 1 or video_pos % progress_every == 0 or video_pos == len(selected_videos)):
            print(
                f"[audit-sample] shard {video_offset}/{video_stride} "
                f"video {video_pos}/{len(selected_videos)} video_id={video_id}",
                flush=True,
            )
        top_categories = [cat_id for cat_id, _ in category_counts_by_video[video_id].most_common(classes_per_video)]
        classes = [categories[cat_id] for cat_id in top_categories if cat_id in categories]
        if not classes:
            continue
        sampled_images = _sample_evenly(images_by_video[video_id], frames_per_video)
        for image in sampled_images:
            image_path = frame_root / image["file_name"]
            if not image_path.exists():
                continue
            bgr = cv2.imread(str(image_path))
            if bgr is None:
                continue
            if backend == "groundingdino":
                pred = detector.predict_with_classes(
                    image=bgr,
                    classes=classes,
                    box_threshold=float(gd.get("box_threshold", 0.30)),
                    text_threshold=float(gd.get("text_threshold", 0.25)),
                )
                xyxy = getattr(pred, "xyxy", [])
                confidence = getattr(pred, "confidence", None)
                class_ids = getattr(pred, "class_id", None)
                if confidence is None or class_ids is None:
                    continue
                raw_predictions = []
                for idx in range(len(xyxy)):
                    raw_class_id = class_ids[idx]
                    if raw_class_id is None:
                        continue
                    try:
                        class_idx = int(raw_class_id)
                    except (TypeError, ValueError):
                        continue
                    raw_predictions.append(
                        {
                            "xyxy": [float(value) for value in xyxy[idx]],
                            "score": float(confidence[idx]),
                            "class_idx": class_idx,
                        }
                    )
            elif backend == "owlv2_hf":
                raw_predictions = _predict_owlv2_with_classes(detector, image_path, classes, cfg)
            elif backend == "owlvit_hf":
                raw_predictions = _predict_owlvit_with_classes(detector, image_path, classes, cfg)
            else:
                raise ValueError(f"unsupported proposal backend: {backend}")
            raw_predictions = sorted(raw_predictions, key=lambda item: float(item["score"]), reverse=True)[:max_det_per_frame]
            for pred_row in raw_predictions:
                class_idx = int(pred_row["class_idx"])
                if class_idx < 0 or class_idx >= len(top_categories):
                    continue
                category_id = int(top_categories[class_idx])
                detections.append(
                    {
                        "dataset": dataset_name,
                        "video_id": int(video_id),
                        "image_id": int(image["id"]),
                        "frame_index": int(image.get("frame_index", image.get("frame_id", 0))),
                        "image_path": str(image_path),
                        "category_id": category_id,
                        "query": categories.get(category_id, str(category_id)),
                        "bbox": _xyxy_to_xywh([float(value) for value in pred_row["xyxy"]]),
                        "score": float(pred_row["score"]),
                    }
                )

    active: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    paths: list[dict[str, Any]] = []
    for det in sorted(detections, key=lambda item: (item["video_id"], item["category_id"], item["frame_index"], -item["score"])):
        key = (det["video_id"], det["category_id"])
        best_path = None
        best_iou = 0.0
        for path in active[key]:
            last = path["detections"][-1]
            if det["frame_index"] <= last["frame_index"] or det["frame_index"] - last["frame_index"] > max_frame_gap:
                continue
            overlap = iou_xywh(tuple(det["bbox"]), tuple(last["bbox"]))
            if overlap > best_iou:
                best_iou = overlap
                best_path = path
        if best_path is not None and best_iou >= link_iou_threshold:
            best_path["detections"].append(det)
        else:
            path = {"detections": [det], "video_id": det["video_id"], "category_id": det["category_id"], "query": det["query"]}
            active[key].append(path)
            paths.append(path)

    universe_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    node_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for idx, path in enumerate(paths):
        dets = path["detections"]
        if not dets:
            continue
        row, path_nodes = _candidate_row_from_path(
            dataset_name=dataset_name,
            path=path,
            idx=idx,
            anns_by_image=anns_by_image,
            iou_threshold=iou_threshold,
            temporal_overlap_threshold=temporal_overlap_threshold,
        )
        universe_rows.append(row)
        score_rows.append(
            {
                "video_id": row["video_id"],
                "path_id": row["path_id"],
                "release_checkpoint": "final",
                "score_total": row["score"],
                "score_obj": row["objectness"],
                "score_sem": row["semantic_margin"],
                "score_temp": row["temporal_stability"],
                "score_assoc": row["association_score"],
            }
        )
        node_rows.extend(path_nodes)
        if len(dets) < min_path_length or not row["is_unmatched"]:
            continue
        path_id = row["path_id"]
        montage_path = montage_dir / f"{path_id}.jpg"
        if make_montages:
            _create_montage(path, montage_path, frames_per_path)
        rows.append(
            {
                "dataset": row["dataset"],
                "video_id": row["video_id"],
                "path_id": row["path_id"],
                "query": row["query"],
                "category_id": row["category_id"],
                "score": row["score"],
                "objectness": row["objectness"],
                "semantic_margin": row["semantic_margin"],
                "temporal_stability": row["temporal_stability"],
                "association_score": row["association_score"],
                "matched_gt_id": row["matched_gt_id"],
                "matched_iou": row["matched_iou"],
                "temporal_overlap": row["temporal_overlap"],
                "is_unmatched": row["is_unmatched"],
                "cell_id": row["cell_id"],
                "novelty_bin": row["novelty_bin"],
                "query_cluster": row["query_cluster"],
                "occ_bin": row["occ_bin"],
                "domain_bin": row["domain_bin"],
                "frame_start": row["frame_start"],
                "frame_end": row["frame_end"],
                "clip_path": "",
                "montage_path": str(montage_path) if montage_path.exists() else "",
            }
        )

    universe_rows.sort(key=lambda row: float(row["score"]), reverse=True)
    for rank, row in enumerate(universe_rows, start=1):
        row["candidate_rank"] = rank
    rows.sort(key=lambda row: float(row["score"]), reverse=True)
    per_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        per_cell[str(row["cell_id"])].append(row)
    selected: list[dict[str, Any]] = []
    seen = set()
    for cell_rows in per_cell.values():
        for row in cell_rows[:top_b_per_cell]:
            selected.append(row)
            seen.add(row["path_id"])
    for row in rows:
        if len(selected) >= total_samples:
            break
        if row["path_id"] not in seen:
            selected.append(row)
            seen.add(row["path_id"])
    selected = selected[:total_samples]

    universe_path = phase2.get("candidate_universe", "./outputs/phase2/candidate_universe.csv")
    scores_path = phase2.get("candidate_scores", "./outputs/phase2/candidate_scores.csv")
    nodes_path = phase2.get("candidate_nodes", "./outputs/phase2/candidate_nodes.csv")
    universe_export = _write_csv_and_optional_parquet(universe_rows, CANDIDATE_UNIVERSE_COLUMNS, universe_path)
    scores_export = _write_csv_and_optional_parquet(score_rows, CANDIDATE_SCORE_COLUMNS, scores_path)
    nodes_export = _write_csv_and_optional_parquet(node_rows, CANDIDATE_NODE_COLUMNS, nodes_path)

    out = ensure_data_output(out_csv)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        writer.writerows(selected)
    labels = ensure_data_output(labels_path)
    should_write_label_template = True
    if labels.exists():
        try:
            existing_labels = pd.read_csv(labels)
            should_write_label_template = existing_labels.empty or not existing_labels.get("label", pd.Series(dtype=str)).astype(str).str.len().any()
        except Exception:
            should_write_label_template = True
    if should_write_label_template:
        with labels.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
            writer.writeheader()
            for row in selected:
                writer.writerow(
                    {
                        "dataset": row["dataset"],
                        "video_id": row["video_id"],
                        "path_id": row["path_id"],
                        "label": "",
                        "reason": "",
                        "auditor": "",
                        "confidence": "",
                    }
                )
    index_path = _write_audit_index(viewer, selected)
    manifest = {
        "status": "completed",
        "reason": "",
        "dataset": dataset_name,
        "proposal_backend": backend,
        "candidate_csv": str(out),
        "label_template_csv": str(labels),
        "viewer_index": str(index_path),
        "groundingdino": gd_status | {"runtime_config": config_path},
        "proposal_runtime": gd_status | {"runtime_config": config_path},
        "num_videos_requested": max_videos,
        "num_videos_processed": len(selected_videos),
        "num_videos_selected_before_shard": len(all_selected_videos),
        "video_stride": video_stride,
        "video_offset": video_offset,
        "num_frame_detections": len(detections),
        "num_paths": len(universe_rows),
        "num_unmatched_paths": len(rows),
        "num_exported_candidates": len(selected),
        "processed_video_ids": selected_videos,
        "candidate_universe": universe_export,
        "candidate_scores": scores_export,
        "candidate_nodes": nodes_export,
        "audit_columns": AUDIT_COLUMNS,
        "label_columns": AUDIT_LABEL_COLUMNS,
        "candidate_universe_columns": CANDIDATE_UNIVERSE_COLUMNS,
    }
    write_json(manifest_path, manifest)
    return manifest


def sample_audit_candidates(config_path: str | Path, dataset_name: str, out_csv: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    phase2 = cfg.get("output", {})
    viewer_path = cfg.get("audit_export", {}).get("output_viewer", "./audit_viewer")
    manifest_path = phase2.get("manifest", "./outputs/phase2/audit_manifest.json")
    labels_path = phase2.get("labels", "./outputs/phase2/audit_labels.csv")
    dataset_report = inspect_dataset_from_config(config_path)
    backend = _proposal_backend(cfg)
    if backend == "owlv2_hf":
        gd_status = owlv2_status(config_path)
    elif backend == "owlvit_hf":
        gd_status = owlvit_status(config_path)
    else:
        gd_status = groundingdino_status(config_path)
    if dataset_report.get("status") != "tracking_layout_ok":
        if backend in {"owlv2_hf", "owlvit_hf"}:
            raise RuntimeError(
                f"dataset_not_ready:{dataset_report.get('status')}:{dataset_report.get('reason')}"
            )
        return write_empty_audit_files(
            out_csv,
            labels_path,
            manifest_path,
            reason=f"dataset_not_ready:{dataset_report.get('status')}:{dataset_report.get('reason')}",
            gd_status=gd_status,
            viewer_path=viewer_path,
        )
    if backend == "owlv2_hf" and not gd_status["ready"]:
        raise RuntimeError(f"owlv2_runtime_not_ready:{json.dumps(gd_status, ensure_ascii=False)}")
    if backend == "owlvit_hf" and not gd_status["ready"]:
        raise RuntimeError(f"owlvit_runtime_not_ready:{json.dumps(gd_status, ensure_ascii=False)}")
    if backend == "groundingdino" and not gd_status["import_ready"]:
        return write_empty_audit_files(
            out_csv,
            labels_path,
            manifest_path,
            reason="groundingdino_runtime_not_ready",
            gd_status=gd_status,
            viewer_path=viewer_path,
        )
    try:
        return _run_groundingdino_audit(cfg, dataset_name, out_csv, labels_path, manifest_path, gd_status, viewer_path)
    except Exception as exc:
        if backend == "owlv2_hf":
            raise RuntimeError(f"owlv2_audit_failed:{type(exc).__name__}:{exc}") from exc
        if backend == "owlvit_hf":
            raise RuntimeError(f"owlvit_audit_failed:{type(exc).__name__}:{exc}") from exc
        return write_empty_audit_files(
            out_csv,
            labels_path,
            manifest_path,
            reason=f"groundingdino_audit_failed:{type(exc).__name__}:{exc}",
            gd_status=gd_status,
            viewer_path=viewer_path,
        )


def run_phase2_propose(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    dataset_name = str(cfg.get("dataset", {}).get("name", "unknown"))
    out_csv = cfg.get("output", {}).get("candidates")
    if not out_csv:
        raise ValueError("phase2 propose requires output.candidates in the config")
    return sample_audit_candidates(config_path, dataset_name, out_csv)


def summarize_audit(candidates_path: str | Path, labels_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    candidates = pd.read_csv(candidates_path)
    labels_file = Path(labels_path)
    if not labels_file.exists():
        labels = pd.DataFrame(columns=AUDIT_LABEL_COLUMNS)
    else:
        labels = pd.read_csv(labels_file)
    dataset = candidates["dataset"].iloc[0] if not candidates.empty and "dataset" in candidates else "unknown"
    valid_labels = {"actually_true", "actually_false", "uncertain"}
    if labels.empty or "label" not in labels:
        labeled = pd.DataFrame(columns=AUDIT_LABEL_COLUMNS)
    else:
        labels = labels.copy()
        labels["label"] = labels["label"].fillna("").astype(str).str.strip()
        labeled = labels[labels["label"].isin(valid_labels)].copy()
    extra_labeled = 0
    if not labeled.empty and not candidates.empty and {"dataset", "video_id", "path_id"}.issubset(candidates.columns) and {"dataset", "video_id", "path_id"}.issubset(labeled.columns):
        candidate_keys = set(
            zip(
                candidates["dataset"].astype(str),
                candidates["video_id"].astype(str),
                candidates["path_id"].astype(str),
            )
        )
        label_keys = list(
            zip(
                labeled["dataset"].astype(str),
                labeled["video_id"].astype(str),
                labeled["path_id"].astype(str),
            )
        )
        in_candidate = pd.Series([key in candidate_keys for key in label_keys], index=labeled.index)
        extra_labeled = int((~in_candidate).sum())
        labeled = labeled[in_candidate].copy()
    total = int(len(labeled))
    true_count = int((labeled["label"] == "actually_true").sum()) if total else 0
    false_count = int((labeled["label"] == "actually_false").sum()) if total else 0
    uncertain_count = int((labeled["label"] == "uncertain").sum()) if total else 0
    verified_count = 0
    if total and "verified_positive_for_calibration" in labeled:
        verified_count = int(
            labeled["verified_positive_for_calibration"].fillna("").astype(str).str.lower().isin(["yes", "true", "1"]).sum()
        )
    summary = pd.DataFrame(
        [
            {
                "Dataset": dataset,
                "High-score unmatched": int(len(candidates)),
                "Labeled": total,
                "Extra labels outside audit candidates": extra_labeled,
                "Pending": max(0, int(len(candidates)) - total),
                "Actually true": true_count,
                "Actually false": false_count,
                "Uncertain": uncertain_count,
                "Actually true %": true_count / total if total else 0.0,
                "Verified positive for calibration": verified_count,
                "Verified positive %": verified_count / total if total else 0.0,
            }
        ]
    )
    out = ensure_data_output(out_path)
    summary.to_csv(out, index=False)
    return {"summary_csv": str(out), "rows": len(summary)}


def gamma_star(n_eff: int, grid_size: int) -> float | None:
    if n_eff <= grid_size - 1:
        return None
    return -1.0 / log(grid_size / (n_eff + 1.0))


def emax(gamma: float, n_eff: int, grid_size: int) -> float | None:
    if n_eff <= grid_size - 1:
        return None
    return gamma * ((grid_size / (n_eff + 1.0)) ** (gamma - 1.0))


def gamma_star_from_p(p_value: float | None) -> float | None:
    if p_value is None or p_value <= 0.0 or p_value >= 1.0:
        return None
    gamma = -1.0 / log(p_value)
    return gamma if 0.0 < gamma < 1.0 else None


def emax_from_p(gamma: float | None, p_value: float | None) -> float | None:
    if gamma is None or p_value is None or p_value <= 0.0 or p_value > 1.0:
        return None
    return gamma * (p_value ** (gamma - 1.0))


def _empty_block_policy(cfg: dict[str, Any]) -> str:
    policy = str(cfg.get("calibration", {}).get("empty_block_policy", "conservative_infinity")).strip()
    if policy not in {"conservative_infinity", "coverage_conditional"}:
        raise ValueError(f"unknown calibration.empty_block_policy: {policy}")
    return policy


def _effective_pmin_diagnostics(
    n_total: int,
    n_nonempty: int,
    grid_size: int,
    empty_block_policy: str,
    alpha1: float,
) -> dict[str, Any]:
    n_total = max(0, int(n_total))
    n_nonempty = max(0, int(n_nonempty))
    n_empty = max(0, n_total - n_nonempty)
    if empty_block_policy == "coverage_conditional":
        n_rank = n_nonempty
        n_inf = 0
        p_min_block = 1.0 / (n_nonempty + 1.0) if n_nonempty > 0 else 1.0
    else:
        n_rank = n_total
        n_inf = n_empty
        p_min_block = (1.0 + n_empty) / (n_total + 1.0) if n_total > 0 else 1.0
    p_min_any = min(1.0, grid_size * p_min_block)
    gamma_eff = gamma_star_from_p(p_min_any)
    emax_eff = emax_from_p(gamma_eff, p_min_any)
    required_emax = 1.0 / alpha1 if alpha1 > 0 else None
    release_feasible = bool(
        emax_eff is not None and required_emax is not None and emax_eff >= required_emax
    )
    return {
        "empty_block_policy": empty_block_policy,
        "n_rank": n_rank,
        "n_nonempty": n_nonempty,
        "n_empty": n_empty,
        "n_inf": n_inf,
        "p_min_block": p_min_block,
        "p_min_any": p_min_any,
        "p_min_effective": p_min_any,
        "gamma_star_eff": gamma_eff,
        "emax_eff": emax_eff,
        "emax_effective": emax_eff,
        "required_emax": required_emax,
        "release_feasible": release_feasible,
    }


def _output_paths_from_cfg(cfg: dict[str, Any]) -> dict[str, Path]:
    output = cfg.get("output", {})
    inputs = cfg.get("input", {})
    candidate_universe = Path(
        inputs.get(
            "candidate_universe",
            output.get("candidate_universe", "./outputs/phase2/candidate_universe.csv"),
        )
    )
    sibling_scores = candidate_universe.with_name("candidate_scores.csv")
    sibling_nodes = candidate_universe.with_name("candidate_nodes.csv")
    return {
        "candidate_universe": candidate_universe,
        "candidate_scores": Path(output.get("candidate_scores", sibling_scores)),
        "candidate_nodes": Path(output.get("candidate_nodes", sibling_nodes)),
        "candidate_evalues": Path(output.get("candidate_evalues", "./outputs/phase2/candidate_evalues.csv")),
        "audit_labels": Path(
            inputs.get("audit_labels", output.get("labels", "./outputs/phase2/audit_labels.csv"))
        ),
        "cell_effective_n": Path(output.get("cell_effective_n", "./outputs/phase2/cell_effective_n.csv")),
        "per_video_candidate_coverage": Path(
            output.get(
                "per_video_candidate_coverage",
                "./outputs/phase2/per_video_candidate_coverage.csv",
            )
        ),
        "coverage_sweep": Path(output.get("coverage_sweep", "./outputs/phase2/coverage_sweep.csv")),
        "projection_vs_observed": Path(
            output.get(
                "projection_vs_observed",
                "./outputs/phase2/coverage_projection_check.csv",
            )
        ),
        "high_e_mass_diagnostics": Path(
            output.get(
                "high_e_mass_diagnostics",
                "./outputs/phase2/high_e_mass_diagnostics.csv",
            )
        ),
        "gamma_mass_sweep": Path(
            output.get("gamma_mass_sweep", "./outputs/phase2/gamma_mass_sweep.csv")
        ),
        "real_cert_summary": Path(
            output.get("real_cert_summary", "./outputs/phase2/real_cert_summary.csv")
        ),
        "summary": Path(output.get("summary", "./outputs/phase2/real_certify_summary.json")),
    }


def _split_video_ids(video_ids: list[int], cfg: dict[str, Any]) -> dict[int, str]:
    splits = cfg.get("splits", {})
    tune_ratio = float(splits.get("tune_ratio", 0.15))
    cal_ratio = float(splits.get("cal_ratio", 0.35))
    seed = int(splits.get("seed", 0))
    strategy = str(splits.get("strategy", "random")).strip()
    ordered = sorted({int(video_id) for video_id in video_ids})
    rng = random.Random(seed)
    if strategy == "severe_sparse_annotation_shift":
        universe_path = Path(
            cfg.get("input", {}).get(
                "candidate_universe",
                cfg.get("output", {}).get("candidate_universe", ""),
            )
        )
        support_ratio: dict[int, float] = {}
        path_count: dict[int, int] = {}
        if universe_path.exists():
            try:
                universe = pd.read_csv(
                    universe_path,
                    usecols=lambda col: col in {"video_id", "is_matched_to_gt", "is_unmatched", "matched_gt_id"},
                )
                universe["video_id"] = universe["video_id"].astype(int)
                if "is_matched_to_gt" in universe:
                    matched = universe["is_matched_to_gt"].astype(str).str.lower().isin(["true", "1", "yes"])
                else:
                    matched = ~universe.get("is_unmatched", pd.Series([True] * len(universe))).astype(str).str.lower().isin(
                        ["true", "1", "yes"]
                    )
                universe["_matched"] = matched
                grouped = universe.groupby("video_id")
                for video_id, group in grouped:
                    paths = int(len(group))
                    path_count[int(video_id)] = paths
                    support_ratio[int(video_id)] = (float(group["_matched"].sum()) + 1.0) / (paths + 2.0)
            except Exception:
                support_ratio = {}
        # Calibration gets dense/officially supported videos, test gets sparse
        # unsupported videos. This is deliberately non-exchangeable and must be
        # reported as an assumption-boundary stress test.
        rng.shuffle(ordered)
        ordered = sorted(
            ordered,
            key=lambda video_id: (
                -support_ratio.get(int(video_id), 0.0),
                -path_count.get(int(video_id), 0),
                int(video_id),
            ),
        )
    else:
        rng.shuffle(ordered)
    total = len(ordered)
    tune_end = int(round(total * tune_ratio))
    cal_end = tune_end + int(round(total * cal_ratio))
    mapping: dict[int, str] = {}
    for idx, video_id in enumerate(ordered):
        if idx < tune_end:
            mapping[video_id] = "tune"
        elif idx < cal_end:
            mapping[video_id] = "cal"
        else:
            mapping[video_id] = "test"
    return mapping


def _load_labels(labels_path: Path) -> pd.DataFrame:
    if not labels_path.exists():
        return pd.DataFrame(columns=AUDIT_LABEL_COLUMNS)
    labels = pd.read_csv(labels_path)
    for column in AUDIT_LABEL_COLUMNS:
        if column not in labels:
            labels[column] = ""
    labels["label"] = labels["label"].fillna("").astype(str).str.strip()
    labels["verified_positive_for_calibration"] = (
        labels["verified_positive_for_calibration"].fillna("").astype(str).str.lower()
    )
    return labels


def _load_universe_with_labels(cfg: dict[str, Any]) -> pd.DataFrame:
    paths = _output_paths_from_cfg(cfg)
    universe_path = paths["candidate_universe"]
    if not universe_path.exists():
        return pd.DataFrame(columns=CANDIDATE_UNIVERSE_COLUMNS)
    universe = pd.read_csv(universe_path)
    labels = _load_labels(paths["audit_labels"])
    if labels.empty:
        universe["label"] = ""
        universe["reason"] = ""
        universe["auditor"] = ""
        universe["confidence"] = ""
        universe["review_status"] = ""
        universe["verified_positive_for_calibration_label"] = ""
    else:
        universe = universe.merge(
            labels,
            on=["dataset", "video_id", "path_id"],
            how="left",
            suffixes=("", "_label"),
        )
    if "label" not in universe:
        universe["label"] = ""
    if "verified_positive_for_calibration_label" in universe:
        verified_source = universe["verified_positive_for_calibration_label"]
    elif "verified_positive_for_calibration" in universe:
        verified_source = universe["verified_positive_for_calibration"]
    else:
        verified_source = pd.Series([""] * len(universe), index=universe.index)
    universe["label"] = universe["label"].fillna("").astype(str).str.strip()
    universe["verified_positive_for_calibration"] = (
        verified_source.fillna("").astype(str).str.lower().where(lambda s: s.isin(["yes", "true", "1"]), "no")
    )
    universe["is_verified_positive"] = universe["verified_positive_for_calibration"].isin(["yes", "true", "1"])
    if "is_matched_to_gt" not in universe:
        universe["is_matched_to_gt"] = ~universe.get("is_unmatched", pd.Series([True] * len(universe))).astype(bool)
    universe["is_unmatched"] = universe["is_unmatched"].astype(str).str.lower().isin(["true", "1", "yes"])
    universe["is_matched_to_gt"] = universe["is_matched_to_gt"].astype(str).str.lower().isin(["true", "1", "yes"])
    universe["truth"] = universe["label"].map(_truth_from_label)
    return universe


def compute_cell_effective_n(config_path: str | Path, out_csv: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    grid = cfg.get("release_grid", {}).get("times_sec", [0.5, 1.0, 2.0, 4.0, 8.0])
    grid_size = len(grid)
    alpha1 = float(cfg.get("risk", {}).get("alpha1", 0.10))
    dataset_report = inspect_dataset_from_config(config_path)
    universe = _load_universe_with_labels(cfg)
    if not universe.empty:
        split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), cfg)
        universe["split"] = universe["video_id"].astype(int).map(split_map)
    else:
        split_map = {}
    out = ensure_data_output(out_csv)
    rows: list[dict[str, Any]] = []
    if dataset_report.get("status") == "tracking_layout_ok":
        n_dataset_total = int(dataset_report.get("num_videos") or 0)
        n_processed = int(universe["video_id"].nunique()) if not universe.empty else 0
        cal = universe[universe["split"] == "cal"].copy() if not universe.empty else pd.DataFrame()
        n_split_calibration = sum(1 for split in split_map.values() if split == "cal") if split_map else 0
        n_scored_calibration = int(cal["video_id"].nunique()) if not cal.empty else n_split_calibration
        null_mask = cal["is_unmatched"] & ~cal.get("is_verified_positive", pd.Series(False, index=cal.index)) if not cal.empty else pd.Series(dtype=bool)
        null_cal = cal[null_mask] if not cal.empty else pd.DataFrame()
        nonempty_null_videos = int(null_cal["video_id"].nunique()) if not null_cal.empty else 0
        empty_null_videos = max(0, n_scored_calibration - nonempty_null_videos)
        n_rank_denominator = n_scored_calibration
        p_min_theoretical = min(1.0, grid_size / (n_rank_denominator + 1.0)) if n_rank_denominator > 0 else 1.0
        conservative = _effective_pmin_diagnostics(
            n_total=n_rank_denominator,
            n_nonempty=nonempty_null_videos,
            grid_size=grid_size,
            empty_block_policy="conservative_infinity",
            alpha1=alpha1,
        )
        coverage = _effective_pmin_diagnostics(
            n_total=n_rank_denominator,
            n_nonempty=nonempty_null_videos,
            grid_size=grid_size,
            empty_block_policy="coverage_conditional",
            alpha1=alpha1,
        )
        p_min_effective = conservative["p_min_effective"]
        gamma_eff = gamma_star_from_p(p_min_effective)
        gamma_theory = gamma_star_from_p(p_min_theoretical)
        rows.append(
            {
                "cell_id": "global",
                "parent_cell_id": "",
                "n_eff": n_rank_denominator,
                "n_dataset_total": n_dataset_total,
                "n_processed_videos": n_processed,
                "n_split_calibration": n_split_calibration,
                "n_scored_calibration_videos": n_scored_calibration,
                "n_nonempty_null_videos": nonempty_null_videos,
                "n_empty_null_videos": empty_null_videos,
                "n_inf_blockmax_videos": empty_null_videos,
                "n_rank_denominator": n_rank_denominator,
                "grid_size": grid_size,
                "gamma_star": gamma_eff,
                "gamma_star_eff": gamma_eff,
                "gamma_star_theoretical": gamma_theory,
                "p_min_theoretical": p_min_theoretical,
                "p_min_effective": p_min_effective,
                "emax_theoretical": emax_from_p(gamma_theory, p_min_theoretical),
                "emax_effective": emax_from_p(gamma_eff, p_min_effective),
                "e_max_uniform_gamma05": emax_from_p(0.5, p_min_effective),
                "e_max_gamma_star": emax_from_p(gamma_eff, p_min_effective),
                "p_min_block_conservative": conservative["p_min_block"],
                "p_min_any_conservative": conservative["p_min_any"],
                "gamma_star_conservative": conservative["gamma_star_eff"],
                "emax_conservative": conservative["emax_eff"],
                "release_feasible_conservative": conservative["release_feasible"],
                "p_min_cov": coverage["p_min_any"],
                "p_min_block_cov": coverage["p_min_block"],
                "gamma_star_cov": coverage["gamma_star_eff"],
                "emax_cov": coverage["emax_eff"],
                "release_feasible_cov": coverage["release_feasible"],
                "required_emax": coverage["required_emax"],
                "num_unknown_paths": int(len(cal)),
                "num_verified_positive": int(cal.get("is_verified_positive", pd.Series(dtype=bool)).sum()) if not cal.empty else 0,
                "num_null_superset_paths": int(len(null_cal)),
                "fallback_level": 0,
            }
        )
    pd.DataFrame(
        rows,
        columns=[
            "cell_id",
            "parent_cell_id",
            "n_eff",
            "n_dataset_total",
            "n_processed_videos",
            "n_split_calibration",
            "n_scored_calibration_videos",
            "n_nonempty_null_videos",
            "n_empty_null_videos",
            "n_inf_blockmax_videos",
            "n_rank_denominator",
            "grid_size",
            "gamma_star",
            "gamma_star_eff",
            "gamma_star_theoretical",
            "p_min_theoretical",
            "p_min_effective",
            "emax_theoretical",
            "emax_effective",
            "e_max_uniform_gamma05",
            "e_max_gamma_star",
            "p_min_block_conservative",
            "p_min_any_conservative",
            "gamma_star_conservative",
            "emax_conservative",
            "release_feasible_conservative",
            "p_min_cov",
            "p_min_block_cov",
            "gamma_star_cov",
            "emax_cov",
            "release_feasible_cov",
            "required_emax",
            "num_unknown_paths",
            "num_verified_positive",
            "num_null_superset_paths",
            "fallback_level",
        ],
    ).to_csv(out, index=False)
    return {"cell_effective_n_csv": str(out), "rows": len(rows), "dataset_status": dataset_report.get("status")}


def _truth_from_label(label: str) -> int | None:
    if label == "actually_true":
        return 1
    if label == "actually_false":
        return 0
    return None


def _scs_release_count(evalues: list[float], alpha1: float, candidate_budget_m: int) -> tuple[int, float, float]:
    if not evalues:
        return 0, float("inf"), float("-inf")
    sorted_e = sorted((float(value) for value in evalues), reverse=True)
    best_k = 0
    best_tau = float("inf")
    best_margin = float("-inf")
    max_k = len(sorted_e)
    for k in range(max_k, 0, -1):
        tau = candidate_budget_m / (alpha1 * k)
        if sorted_e[k - 1] >= tau:
            best_k = k
            best_tau = tau
            best_margin = sorted_e[k - 1] - tau
            break
    return best_k, best_tau, best_margin


def _scs_best_margin(evalues: list[float], alpha1: float, candidate_budget_m: int) -> tuple[int, float, float]:
    if not evalues:
        return 0, float("inf"), float("-inf")
    sorted_e = sorted((float(value) for value in evalues), reverse=True)
    best_k = 0
    best_tau = float("inf")
    best_margin = float("-inf")
    for k in range(1, len(sorted_e) + 1):
        tau = candidate_budget_m / (alpha1 * k)
        margin = sorted_e[k - 1] - tau
        if margin > best_margin:
            best_k = k
            best_tau = tau
            best_margin = margin
    return best_k, best_tau, best_margin


def _default_high_e_budgets(cfg: dict[str, Any]) -> list[int]:
    values = cfg.get("high_e_diagnostics", {}).get(
        "candidate_budget_sweep",
        cfg.get("high_e_diagnostics", {}).get("budgets", [25, 50, 100, 150, 200, 250, 500, 1000]),
    )
    return [int(value) for value in values]


def _default_high_e_gammas(cfg: dict[str, Any]) -> list[float]:
    values = cfg.get("high_e_diagnostics", {}).get(
        "gamma_candidates",
        cfg.get("e_calibrator", {}).get("gamma_candidates", [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.50]),
    )
    return [float(value) for value in values]


def _mass_curve_rows(evalues: list[float], alpha1: float, candidate_budget_m: int) -> list[dict[str, Any]]:
    sorted_e = sorted((float(value) for value in evalues[:candidate_budget_m]), reverse=True)
    rows = []
    for k in range(1, len(sorted_e) + 1):
        tau = candidate_budget_m / (alpha1 * k)
        e_at_k = sorted_e[k - 1]
        margin = e_at_k - tau
        mass_ratio = alpha1 * k * e_at_k / candidate_budget_m
        rows.append(
            {
                "k": k,
                "tau_k": tau,
                "e_at_k": e_at_k,
                "margin_k": margin,
                "mass_ratio_k": mass_ratio,
                "num_above_tau": sum(1 for value in sorted_e if value >= tau),
                "unconstrained_feasible": mass_ratio >= 1.0,
            }
        )
    return rows


def _best_mass_summary(evalues: list[float], alpha1: float, candidate_budget_m: int) -> dict[str, Any]:
    curve = _mass_curve_rows(evalues, alpha1, candidate_budget_m)
    if not curve:
        return {
            "best_k": 0,
            "best_tau": None,
            "best_margin": None,
            "best_mass_ratio": 0.0,
            "released_unconstrained": False,
        }
    best = max(curve, key=lambda row: float(row["mass_ratio_k"]))
    best_margin = max(curve, key=lambda row: float(row["margin_k"]))
    return {
        "best_k": int(best["k"]),
        "best_tau": float(best["tau_k"]),
        "best_margin": float(best_margin["margin_k"]),
        "best_mass_ratio": float(best["mass_ratio_k"]),
        "released_unconstrained": bool(float(best["mass_ratio_k"]) >= 1.0),
    }


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    series = pd.Series(values, dtype=float)
    return float(series.quantile(q))


def _build_real_cert_summary(
    cfg: dict[str, Any],
    candidates_path: Path,
    labels_path: Path,
    cell_out: str | Path,
    out_csv: str | Path,
) -> dict[str, Any]:
    candidates = pd.read_csv(candidates_path)
    labels = pd.read_csv(labels_path)
    merged = candidates.merge(
        labels,
        on=["dataset", "video_id", "path_id"],
        how="left",
        suffixes=("", "_label"),
    )
    if "label" not in merged:
        merged["label"] = ""
    merged["label"] = merged["label"].fillna("").astype(str).str.strip()
    if "verified_positive_for_calibration" not in merged:
        merged["verified_positive_for_calibration"] = "no"
    merged["verified_positive_for_calibration"] = (
        merged["verified_positive_for_calibration"].fillna("").astype(str).str.lower()
    )
    merged["is_verified_positive"] = merged["verified_positive_for_calibration"].isin(["yes", "true", "1"])
    merged["truth"] = merged["label"].map(_truth_from_label)

    alpha1 = float(cfg.get("risk", {}).get("alpha1", 0.10))
    configured_m = int(cfg.get("selector", {}).get("candidate_budget_M", len(merged)))
    effective_m = max(1, int(len(merged)))
    grid_size = len(cfg.get("release_grid", {}).get("times_sec", [0.5, 1.0, 2.0, 4.0, 8.0]))
    cells = pd.read_csv(cell_out) if Path(cell_out).exists() else pd.DataFrame()
    n_eff = int(cells["n_eff"].iloc[0]) if not cells.empty and "n_eff" in cells else 0
    gamma = gamma_star(n_eff, grid_size) or 0.5
    e_max_value = emax(gamma, n_eff, grid_size) or 0.0

    methods = [
        {
            "method": "unmatched_as_false_block",
            "audit_policy": "treat_all_unmatched_as_false_diagnostic",
            "remove_verified": False,
            "gamma": 0.5,
        },
        {
            "method": "null_superset_no_audit",
            "audit_policy": "remove_no_verified_positives",
            "remove_verified": False,
            "gamma": gamma,
        },
        {
            "method": "null_superset_model_assisted_audit",
            "audit_policy": "remove_verified_positive_for_calibration",
            "remove_verified": True,
            "gamma": gamma,
        },
        {
            "method": "parc_track_gamma_tuned_uniform_scs",
            "audit_policy": "remove_verified_positive_for_calibration",
            "remove_verified": True,
            "gamma": gamma,
        },
    ]
    rows: list[dict[str, Any]] = []
    scores = merged["score"].astype(float)
    for method in methods:
        gamma_used = float(method["gamma"])
        null_mask = pd.Series(True, index=merged.index)
        if method["remove_verified"]:
            null_mask &= ~merged["is_verified_positive"]
        null_scores = scores[null_mask].tolist()
        evalues = []
        p_any_values = []
        for score in scores:
            exceed = sum(1 for value in null_scores if float(value) >= float(score))
            p_block = (1.0 + exceed) / (n_eff + 1.0) if n_eff > 0 else 1.0
            p_any = min(1.0, p_block * grid_size)
            p_any_values.append(p_any)
            evalues.append(gamma_used * (p_any ** (gamma_used - 1.0)) if p_any > 0 else 0.0)
        k, tau, margin = _scs_release_count(evalues, alpha1=alpha1, candidate_budget_m=effective_m)
        best_k, best_tau, best_margin = _scs_best_margin(evalues, alpha1=alpha1, candidate_budget_m=effective_m)
        selected_idx = sorted(range(len(evalues)), key=lambda idx: evalues[idx], reverse=True)[:k]
        selected = merged.iloc[selected_idx].copy() if selected_idx else merged.iloc[[]].copy()
        released = int(len(selected))
        audited = selected[selected["truth"].notna()]
        false_released = int((audited["truth"] == 0).sum()) if released else 0
        true_released = int((audited["truth"] == 1).sum()) if released else 0
        unsupported_released = int((selected["label"] != "actually_true").sum()) if released else 0
        audited_ftr = false_released / max(1, len(audited))
        utr = unsupported_released / max(1, released)
        rows.append(
            {
                "method": method["method"],
                "audit_policy": method["audit_policy"],
                "n_cal": n_eff,
                "n_eff": n_eff,
                "grid_size": grid_size,
                "gamma": gamma_used,
                "gamma_star": gamma,
                "e_max": emax(gamma_used, n_eff, grid_size),
                "alpha1": alpha1,
                "configured_candidate_budget_M": configured_m,
                "effective_candidate_budget_M": effective_m,
                "released": released,
                "audited_released": int(len(audited)),
                "true_released": true_released,
                "false_released": false_released,
                "utr": utr,
                "audited_ftr_on_labeled_subset": audited_ftr,
                "actually_true_removed": int(merged["is_verified_positive"].sum()) if method["remove_verified"] else 0,
                "null_superset_size": int(null_mask.sum()),
                "mean_recall_on_audit_true": true_released / max(1, int((merged["label"] == "actually_true").sum())),
                "self_consistency_margin": margin if released else None,
                "best_empty_margin_k": best_k,
                "best_empty_margin_tau": best_tau,
                "best_empty_margin": best_margin,
                "max_e_observed": max(evalues) if evalues else None,
                "mean_e_observed": sum(evalues) / len(evalues) if evalues else None,
                "empty_reason": "no_k_satisfies_uniform_self_consistency" if released == 0 else "",
                "tau_k": tau if released else None,
                "selected_e_min": min((evalues[idx] for idx in selected_idx), default=None),
                "selected_e_mean": sum(evalues[idx] for idx in selected_idx) / released if released else None,
                "selected_e_max": max((evalues[idx] for idx in selected_idx), default=None),
                "p_any_min_observed": min(p_any_values) if p_any_values else None,
                "empty_rate": 1.0 if released == 0 else 0.0,
                "scaffold_note": "audited_subset_scaffold_not_full_benchmark_claim",
            }
        )
    out = ensure_data_output(out_csv)
    pd.DataFrame(rows).to_csv(out, index=False)
    return {"real_cert_summary_csv": str(out), "rows": len(rows)}


def _candidate_budgets(cfg: dict[str, Any]) -> list[int]:
    selector = cfg.get("selector", {})
    values = selector.get("candidate_budget_sweep", selector.get("candidate_budgets"))
    if values is None:
        values = [selector.get("candidate_budget_M", 500)]
    return [int(value) for value in values]


def _method_specs_for_real_certify() -> list[dict[str, Any]]:
    return [
        {
            "method": "unmatched_as_false_block",
            "audit_policy": "treat_unmatched_as_false_baseline",
            "remove_verified": False,
            "gamma_mode": "fixed_0.5",
        },
        {
            "method": "null_superset_no_audit",
            "audit_policy": "remove_official_gt_matches_only",
            "remove_verified": False,
            "gamma_mode": "effective_finite_resolution",
        },
        {
            "method": "parc_track_gamma_tuned_uniform_scs",
            "audit_policy": "remove_official_gt_matches_and_verified_positive_for_calibration",
            "remove_verified": True,
            "gamma_mode": "effective_finite_resolution",
        },
    ]


def _block_evalues(
    test: pd.DataFrame,
    cal: pd.DataFrame,
    cal_video_ids: list[int],
    grid_size: int,
    gamma: float,
    remove_verified: bool,
    empty_block_policy: str,
    alpha1: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if cal.empty or not cal_video_ids:
        empty = test[["dataset", "video_id", "path_id", "cell_id", "score"]].copy() if not test.empty else pd.DataFrame()
        for column in ("p_block", "p_any", "e_value"):
            empty[column] = None
        return empty, {
            "empty_block_policy": empty_block_policy,
            "n_cal_total": 0,
            "n_covered": 0,
            "n_excluded_empty": 0,
            "n_rank_denominator": 0,
            "n_rank": 0,
            "n_nonempty": 0,
            "n_empty": 0,
            "n_inf": 0,
            "p_min_theoretical": 1.0,
            "p_min_block": 1.0,
            "p_min_effective": 1.0,
            "required_emax": 1.0 / alpha1 if alpha1 > 0 else None,
            "release_feasible": False,
            "max_observed_e": None,
        }
    null_mask = cal["is_unmatched"].astype(bool)
    if remove_verified:
        null_mask &= ~cal["is_verified_positive"].astype(bool)
    null_cal = cal[null_mask].copy()
    blockmax = {}
    inf_count = 0
    nonempty_count = 0
    for video_id in cal_video_ids:
        scores = null_cal.loc[null_cal["video_id"].astype(int) == int(video_id), "score"].astype(float)
        if scores.empty:
            if empty_block_policy == "conservative_infinity":
                blockmax[int(video_id)] = float("inf")
                inf_count += 1
        else:
            blockmax[int(video_id)] = float(scores.max())
            nonempty_count += 1
    maxima = list(blockmax.values())
    n_rank = len(maxima)
    diag = _effective_pmin_diagnostics(
        n_total=len(cal_video_ids),
        n_nonempty=nonempty_count,
        grid_size=grid_size,
        empty_block_policy=empty_block_policy,
        alpha1=alpha1,
    )
    p_min_theoretical = min(1.0, grid_size / (len(cal_video_ids) + 1.0)) if cal_video_ids else 1.0
    p_min_effective = diag["p_min_effective"]
    rows = []
    for _, row in test.iterrows():
        score = float(row["score"])
        exceed = sum(1 for value in maxima if value >= score)
        p_block = (1.0 + exceed) / (n_rank + 1.0) if n_rank else 1.0
        p_any = min(1.0, p_block * grid_size)
        e_value = gamma * (p_any ** (gamma - 1.0)) if p_any > 0 else 0.0
        rows.append(
            {
                "dataset": row["dataset"],
                "video_id": int(row["video_id"]),
                "path_id": row["path_id"],
                "release_checkpoint": "final",
                "cell_id": row.get("cell_id", "global"),
                "score": score,
                "p_block": p_block,
                "p_any": p_any,
                "e_value": e_value,
                "gamma": gamma,
                "gamma_star": gamma_star_from_p(p_min_effective),
                "empty_block_policy": empty_block_policy,
                "p_min_block": diag["p_min_block"],
                "p_min_effective": p_min_effective,
                "emax_effective": emax_from_p(gamma, p_min_effective),
                "score_source": row.get("score_source", "final_score_proxy"),
            }
        )
    evalue_frame = pd.DataFrame(rows)
    return evalue_frame, {
        "n_cal_total": len(cal_video_ids),
        "n_covered": nonempty_count,
        "n_excluded_empty": len(cal_video_ids) - nonempty_count,
        "n_rank_denominator": n_rank,
        "n_rank": n_rank,
        "n_nonempty": nonempty_count,
        "n_empty": len(cal_video_ids) - nonempty_count,
        "n_inf": inf_count,
        "p_min_theoretical": p_min_theoretical,
        "p_min_block": diag["p_min_block"],
        "p_min_effective": p_min_effective,
        "gamma_star_eff": diag["gamma_star_eff"],
        "emax_effective": emax_from_p(gamma, p_min_effective),
        "required_emax": diag["required_emax"],
        "release_feasible": diag["release_feasible"],
        "max_observed_e": float(evalue_frame["e_value"].max()) if not evalue_frame.empty else None,
    }


def _coverage_diag_for_method(
    cal: pd.DataFrame,
    cal_video_ids: list[int],
    grid_size: int,
    remove_verified: bool,
    empty_block_policy: str,
    alpha1: float,
) -> dict[str, Any]:
    if cal.empty or not cal_video_ids:
        return _effective_pmin_diagnostics(0, 0, grid_size, empty_block_policy, alpha1)
    null_mask = cal["is_unmatched"].astype(bool)
    if remove_verified:
        null_mask &= ~cal["is_verified_positive"].astype(bool)
    null_cal = cal[null_mask].copy()
    nonempty = int(null_cal["video_id"].astype(int).nunique()) if not null_cal.empty else 0
    return _effective_pmin_diagnostics(len(cal_video_ids), nonempty, grid_size, empty_block_policy, alpha1)


def _write_per_video_candidate_coverage(universe: pd.DataFrame, cfg: dict[str, Any], out_csv: Path) -> dict[str, Any]:
    paths = _output_paths_from_cfg(cfg)
    detections_by_video: dict[int, int] = {}
    nodes_path = paths["candidate_nodes"]
    if nodes_path.exists():
        try:
            nodes = pd.read_csv(nodes_path, usecols=["video_id"])
            detections_by_video = nodes["video_id"].astype(int).value_counts().to_dict()
        except Exception:
            detections_by_video = {}
    rows = []
    if not universe.empty:
        for video_id, group in universe.groupby(universe["video_id"].astype(int)):
            unmatched = group["is_unmatched"].astype(bool)
            verified = group["is_verified_positive"].astype(bool)
            null_paths = unmatched & ~verified
            rows.append(
                {
                    "video_id": int(video_id),
                    "split": str(group["split"].iloc[0]) if "split" in group else "",
                    "num_detections": int(detections_by_video.get(int(video_id), 0)),
                    "num_paths": int(len(group)),
                    "num_unmatched_paths": int(unmatched.sum()),
                    "num_verified_positive_paths": int(verified.sum()),
                    "num_null_paths": int(null_paths.sum()),
                    "has_null_block": bool(null_paths.any()),
                }
            )
    out = ensure_data_output(out_csv)
    pd.DataFrame(
        rows,
        columns=[
            "video_id",
            "split",
            "num_detections",
            "num_paths",
            "num_unmatched_paths",
            "num_verified_positive_paths",
            "num_null_paths",
            "has_null_block",
        ],
    ).to_csv(out, index=False)
    return {"per_video_candidate_coverage_csv": str(out), "rows": len(rows)}


def _empty_diagnostic(released: int, method_diag: dict[str, Any], max_observed_e: float | None) -> str:
    if released:
        return ""
    required = method_diag.get("required_emax")
    emax_value = method_diag.get("emax_effective")
    if required is not None and (emax_value is None or float(emax_value) < float(required)):
        return "resolution_below_required_emax"
    if required is not None and (max_observed_e is None or float(max_observed_e) < float(required)):
        return "observed_e_below_required_emax"
    return "insufficient_high_e_mass_for_uniform_scs"


def run_real_certify(config_path: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    paths = _output_paths_from_cfg(cfg)
    universe_path = paths["candidate_universe"]
    if not universe_path.exists():
        summary = {
            "status": "requires_candidate_universe",
            "reason": f"missing {universe_path}",
            "candidate_universe": str(universe_path),
        }
        write_json(out_path or paths["summary"], summary)
        return summary

    universe = _load_universe_with_labels(cfg)
    if universe.empty:
        summary = {
            "status": "requires_candidate_universe",
            "reason": "candidate universe is empty",
            "candidate_universe": str(universe_path),
        }
        write_json(out_path or paths["summary"], summary)
        return summary

    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), cfg)
    universe["split"] = universe["video_id"].astype(int).map(split_map)
    universe["audit_label"] = universe["label"].fillna("").astype(str)
    universe["verified_positive_for_calibration"] = universe["verified_positive_for_calibration"].where(
        universe["is_verified_positive"], "no"
    )
    universe_for_csv = universe.copy()
    for column in CANDIDATE_UNIVERSE_COLUMNS:
        if column not in universe_for_csv:
            universe_for_csv[column] = ""
    universe_for_csv[CANDIDATE_UNIVERSE_COLUMNS].to_csv(ensure_data_output(universe_path), index=False)

    cell_summary = compute_cell_effective_n(config_path, paths["cell_effective_n"])
    cells = pd.read_csv(paths["cell_effective_n"]) if paths["cell_effective_n"].exists() else pd.DataFrame()
    cell = cells.iloc[0].to_dict() if not cells.empty else {}
    n_rank = int(cell.get("n_rank_denominator") or 0)
    p_min_effective = float(cell.get("p_min_effective") or 1.0)
    p_min_theoretical = float(cell.get("p_min_theoretical") or 1.0)
    grid_size = len(cfg.get("release_grid", {}).get("times_sec", [0.5, 1.0, 2.0, 4.0, 8.0]))
    alpha1 = float(cfg.get("risk", {}).get("alpha1", 0.10))
    empty_block_policy = _empty_block_policy(cfg)

    cal = universe[universe["split"] == "cal"].copy()
    test = universe[universe["split"] == "test"].copy()
    cal_video_ids = sorted(cal["video_id"].astype(int).unique().tolist())
    test = test.sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    per_video_summary = _write_per_video_candidate_coverage(universe, cfg, paths["per_video_candidate_coverage"])

    summary_rows = []
    evalue_frames = []
    for method in _method_specs_for_real_certify():
        method_pre_diag = _coverage_diag_for_method(
            cal=cal,
            cal_video_ids=cal_video_ids,
            grid_size=grid_size,
            remove_verified=bool(method["remove_verified"]),
            empty_block_policy=empty_block_policy,
            alpha1=alpha1,
        )
        gamma_eff = method_pre_diag["gamma_star_eff"] or 0.5
        gamma = 0.5 if method["gamma_mode"] == "fixed_0.5" else gamma_eff
        evalues, method_diag = _block_evalues(
            test=test,
            cal=cal,
            cal_video_ids=cal_video_ids,
            grid_size=grid_size,
            gamma=gamma,
            remove_verified=bool(method["remove_verified"]),
            empty_block_policy=empty_block_policy,
            alpha1=alpha1,
        )
        if not evalues.empty:
            evalues["method"] = method["method"]
            evalues["audit_policy"] = method["audit_policy"]
            evalue_frames.append(evalues)
        evalue_map = dict(zip(evalues["path_id"], evalues["e_value"])) if not evalues.empty else {}
        for budget_m in _candidate_budgets(cfg):
            pool = test.head(budget_m).copy()
            dummy_paths = max(0, budget_m - len(pool))
            pool_evalues = [float(evalue_map.get(path_id, 0.0)) for path_id in pool["path_id"]]
            max_observed_e = max(pool_evalues) if pool_evalues else None
            k, tau, margin = _scs_release_count(pool_evalues, alpha1=alpha1, candidate_budget_m=budget_m)
            best_k, best_tau, best_margin = _scs_best_margin(pool_evalues, alpha1=alpha1, candidate_budget_m=budget_m)
            selected_positions = sorted(range(len(pool_evalues)), key=lambda idx: pool_evalues[idx], reverse=True)[:k]
            selected = pool.iloc[selected_positions].copy() if selected_positions else pool.iloc[[]].copy()
            released = int(len(selected))
            if released:
                selected["selected_e"] = [pool_evalues[idx] for idx in selected_positions]
            labeled = selected[selected["label"].isin(["actually_true", "actually_false"])].copy()
            false_released = int((labeled["label"] == "actually_false").sum()) if released else 0
            true_released = int((labeled["label"] == "actually_true").sum()) if released else 0
            uncertain_released = int((selected["label"] == "uncertain").sum()) if released else 0
            unsupported = selected[(~selected["is_matched_to_gt"].astype(bool)) & (~selected["is_verified_positive"].astype(bool))]
            unsupported_true = int((unsupported["label"] == "actually_true").sum()) if released else 0
            unsupported_false = int((unsupported["label"] == "actually_false").sum()) if released else 0
            unsupported_uncertain = int((unsupported["label"] == "uncertain").sum()) if released else 0
            unsupported_unlabeled = int((unsupported["label"].fillna("").astype(str).str.strip() == "").sum()) if released else 0
            official_supported = released - int(len(unsupported))
            utr = len(unsupported) / released if released else 0.0
            audited_ftr = false_released / len(labeled) if len(labeled) else None
            supported_plus_labeled = official_supported + unsupported_true + unsupported_false
            audited_supported_ftr = unsupported_false / supported_plus_labeled if supported_plus_labeled else None
            conservative_ftr = (
                (unsupported_false + unsupported_uncertain + unsupported_unlabeled) / released if released else None
            )
            summary_rows.append(
                {
                    "method": method["method"],
                    "audit_policy": method["audit_policy"],
                    "empty_block_policy": empty_block_policy,
                    "alpha1": alpha1,
                    "score_source": "final_score_proxy",
                    "n_cal_total": method_diag["n_cal_total"],
                    "n_covered": method_diag["n_covered"],
                    "n_excluded_empty": method_diag["n_excluded_empty"],
                    "n_rank_denominator": method_diag["n_rank_denominator"],
                    "n_rank": method_diag["n_rank"],
                    "n_nonempty": method_diag["n_nonempty"],
                    "n_empty_null_videos": method_diag["n_empty"],
                    "n_inf_blockmax_videos": method_diag["n_inf"],
                    "gamma": gamma,
                    "gamma_star_eff": method_diag["gamma_star_eff"],
                    "p_min_theoretical": p_min_theoretical,
                    "p_min_block": method_diag["p_min_block"],
                    "p_min_effective": method_diag["p_min_effective"],
                    "emax_theoretical": emax_from_p(gamma, p_min_theoretical),
                    "emax_effective": emax_from_p(gamma, method_diag["p_min_effective"]),
                    "required_emax": method_diag["required_emax"],
                    "release_feasible": method_diag["release_feasible"],
                    "max_observed_e": max_observed_e,
                    "mean_observed_e": sum(pool_evalues) / len(pool_evalues) if pool_evalues else None,
                    "candidate_budget_M": budget_m,
                    "real_candidate_count": int(len(pool)),
                    "dummy_paths": dummy_paths,
                    "released": released,
                    "official_supported": official_supported,
                    "unsupported": int(len(unsupported)),
                    "unsupported_actually_true": unsupported_true,
                    "unsupported_actually_false": unsupported_false,
                    "unsupported_uncertain": unsupported_uncertain,
                    "unsupported_unlabeled": unsupported_unlabeled,
                    "audited_released": int(len(labeled)),
                    "true_released": true_released,
                    "false_released": false_released,
                    "uncertain_released": uncertain_released,
                    "utr": utr,
                    "audited_ftr_on_labeled_released": audited_ftr,
                    "audited_ftr_supported_plus_labeled": audited_supported_ftr,
                    "conservative_ftr_uncertain_and_unlabeled_false": conservative_ftr,
                    "recall_proxy": released / max(1, budget_m),
                    "verified_positive_removed": int(cal["is_verified_positive"].sum()) if method["remove_verified"] else 0,
                    "null_superset_size": int((cal["is_unmatched"] & (~cal["is_verified_positive"] if method["remove_verified"] else True)).sum()),
                    "tau_k": tau if released else None,
                    "self_consistency_margin": margin if released else None,
                    "best_margin_k": best_k,
                    "best_margin_tau": best_tau,
                    "best_margin": best_margin,
                    "selected_e_min": min((pool_evalues[idx] for idx in selected_positions), default=None),
                    "selected_e_mean": (
                        sum(pool_evalues[idx] for idx in selected_positions) / released if released else None
                    ),
                    "selected_e_max": max((pool_evalues[idx] for idx in selected_positions), default=None),
                    "empty_reason": "no_k_satisfies_uniform_self_consistency" if released == 0 else "",
                    "empty_diagnostic": _empty_diagnostic(released, method_diag, max_observed_e),
                }
            )

    real_cert_out = ensure_data_output(paths["real_cert_summary"])
    pd.DataFrame(summary_rows).to_csv(real_cert_out, index=False)
    if evalue_frames:
        evalue_out = ensure_data_output(paths["candidate_evalues"])
        pd.concat(evalue_frames, ignore_index=True).to_csv(evalue_out, index=False)
    else:
        evalue_out = ensure_data_output(paths["candidate_evalues"])
        pd.DataFrame().to_csv(evalue_out, index=False)
    summary = {
        "status": "completed_full_universe_scaffold",
        "dataset": cfg.get("dataset", {}).get("name", "unknown"),
        "candidate_universe": str(universe_path),
        "candidate_universe_rows": int(len(universe)),
        "processed_videos": int(universe["video_id"].nunique()),
        "test_candidates": int(len(test)),
        "calibration_candidates": int(len(cal)),
        "cell_effective_n": cell_summary,
        "per_video_candidate_coverage": per_video_summary,
        "real_cert_summary_csv": str(real_cert_out),
        "candidate_evalues_csv": str(evalue_out),
        "rows": int(len(summary_rows)),
    }
    write_json(out_path or paths["summary"], summary)
    return summary


def _write_projection_vs_observed(
    observed_rows: pd.DataFrame,
    cfg: dict[str, Any],
    out_path: Path,
) -> dict[str, Any]:
    sweep_cfg = cfg.get("coverage_sweep", {})
    baseline_value = sweep_cfg.get("projection_baseline")
    columns = [
        "processed_videos",
        "projected_processed_videos",
        "grid_size",
        "cal_ratio",
        "empty_block_policy",
        "projected_n_nonempty",
        "observed_n_nonempty",
        "projected_p_min_eff",
        "observed_p_min_eff",
        "projected_emax_eff",
        "observed_emax_eff",
        "projected_feasible",
        "observed_feasible",
    ]
    rows: list[dict[str, Any]] = []
    if baseline_value:
        baseline_path = Path(baseline_value)
        if baseline_path.exists() and not observed_rows.empty:
            baseline = pd.read_csv(baseline_path)
            projected = baseline[baseline.get("projection", pd.Series(False, index=baseline.index)).astype(bool)].copy()
            observed = observed_rows[~observed_rows.get("projection", pd.Series(True, index=observed_rows.index)).astype(bool)].copy()
            for _, obs in observed.iterrows():
                candidates = projected[
                    (projected["grid_size"].astype(int) == int(obs["grid_size"]))
                    & (projected["empty_block_policy"].astype(str) == str(obs["empty_block_policy"]))
                    & ((projected["cal_ratio"].astype(float) - float(obs["cal_ratio"])).abs() < 1e-12)
                ]
                exact = candidates[candidates["processed_videos"].astype(int) == int(obs["processed_videos"])]
                if not exact.empty:
                    match = exact
                elif not candidates.empty:
                    distances = (candidates["processed_videos"].astype(int) - int(obs["processed_videos"])).abs()
                    match = candidates.loc[[distances.idxmin()]]
                else:
                    match = candidates
                if match.empty:
                    continue
                pred = match.iloc[0]
                rows.append(
                    {
                        "processed_videos": int(obs["processed_videos"]),
                        "projected_processed_videos": int(pred["processed_videos"]),
                        "grid_size": int(obs["grid_size"]),
                        "cal_ratio": float(obs["cal_ratio"]),
                        "empty_block_policy": str(obs["empty_block_policy"]),
                        "projected_n_nonempty": int(pred["n_nonempty"]),
                        "observed_n_nonempty": int(obs["n_nonempty"]),
                        "projected_p_min_eff": float(pred["p_min_any"]),
                        "observed_p_min_eff": float(obs["p_min_any"]),
                        "projected_emax_eff": pred["emax_eff"],
                        "observed_emax_eff": obs["emax_eff"],
                        "projected_feasible": bool(pred["release_feasible"]),
                        "observed_feasible": bool(obs["release_feasible"]),
                    }
                )
    out = ensure_data_output(out_path)
    pd.DataFrame(rows, columns=columns).to_csv(out, index=False)
    return {"projection_vs_observed_csv": str(out), "rows": len(rows)}


def run_real_coverage_sweep(config_path: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    paths = _output_paths_from_cfg(cfg)
    universe = _load_universe_with_labels(cfg)
    if universe.empty:
        out = ensure_data_output(out_path or paths["coverage_sweep"])
        pd.DataFrame().to_csv(out, index=False)
        return {
            "status": "requires_candidate_universe",
            "reason": "candidate universe is empty or missing",
            "coverage_sweep_csv": str(out),
            "rows": 0,
        }

    alpha1 = float(cfg.get("risk", {}).get("alpha1", 0.10))
    current_grid = cfg.get("release_grid", {}).get("times_sec", [0.5, 1.0, 2.0, 4.0, 8.0])
    sweep_cfg = cfg.get("coverage_sweep", {})
    observed_videos = sorted(universe["video_id"].astype(int).unique().tolist())
    n_observed = len(observed_videos)
    dataset_report = inspect_dataset_from_config(config_path)
    n_dataset_total = int(dataset_report.get("num_videos") or n_observed)

    processed_targets = sweep_cfg.get("processed_videos", [n_observed, 500, 1000, n_dataset_total])
    processed_targets = list(processed_targets) + [n_observed]
    processed_targets = sorted({int(value) for value in processed_targets if int(value) > 0})
    cal_ratios = sweep_cfg.get(
        "cal_ratios",
        [float(cfg.get("splits", {}).get("cal_ratio", 0.35)), 0.50, 0.60],
    )
    cal_ratios = [float(value) for value in cal_ratios]
    release_grids = sweep_cfg.get("release_grids", [[2.0], [1.0, 2.0], current_grid])
    policies = sweep_cfg.get("empty_block_policy", ["conservative_infinity", "coverage_conditional"])
    policies = [str(policy) for policy in policies]
    tune_ratio = float(sweep_cfg.get("tune_ratio", cfg.get("splits", {}).get("tune_ratio", 0.10)))

    unmatched = universe["is_unmatched"].astype(bool)
    verified = universe["is_verified_positive"].astype(bool)
    has_null_by_video = (unmatched & ~verified).groupby(universe["video_id"].astype(int)).any()
    observed_nonempty_rate = float(has_null_by_video.mean()) if len(has_null_by_video) else 0.0

    rows = []
    for processed_target in processed_targets:
        for cal_ratio in cal_ratios:
            if processed_target <= n_observed:
                selected_video_ids = observed_videos[:processed_target]
                split_cfg = dict(cfg)
                split_cfg["splits"] = {
                    **cfg.get("splits", {}),
                    "tune_ratio": tune_ratio,
                    "cal_ratio": cal_ratio,
                    "seed": int(cfg.get("splits", {}).get("seed", 0)),
                }
                split_map = _split_video_ids(selected_video_ids, split_cfg)
                cal_ids = [video_id for video_id, split in split_map.items() if split == "cal"]
                n_rank = len(cal_ids)
                n_nonempty = sum(1 for video_id in cal_ids if bool(has_null_by_video.get(video_id, False)))
                projection = False
            else:
                n_rank = int(round(processed_target * cal_ratio))
                n_nonempty = int(round(n_rank * observed_nonempty_rate))
                projection = True
            n_empty = max(0, n_rank - n_nonempty)
            for grid in release_grids:
                grid_size = len(grid)
                for policy in policies:
                    diag = _effective_pmin_diagnostics(
                        n_total=n_rank,
                        n_nonempty=n_nonempty,
                        grid_size=grid_size,
                        empty_block_policy=policy,
                        alpha1=alpha1,
                    )
                    rows.append(
                        {
                            "processed_videos": processed_target,
                            "cal_ratio": cal_ratio,
                            "grid_size": grid_size,
                            "release_grid": "|".join(str(value) for value in grid),
                            "empty_block_policy": policy,
                            "n_rank": diag["n_rank"],
                            "n_nonempty": n_nonempty,
                            "n_empty": n_empty,
                            "p_min_block": diag["p_min_block"],
                            "p_min_any": diag["p_min_any"],
                            "gamma_star_eff": diag["gamma_star_eff"],
                            "emax_eff": diag["emax_eff"],
                            "required_emax": diag["required_emax"],
                            "release_feasible": diag["release_feasible"],
                            "observed_nonempty_rate": observed_nonempty_rate,
                            "projection": projection,
                        }
                    )

    out = ensure_data_output(out_path or paths["coverage_sweep"])
    frame = pd.DataFrame(rows)
    frame.to_csv(out, index=False)
    projection_summary = _write_projection_vs_observed(frame, cfg, paths["projection_vs_observed"])
    return {
        "status": "completed",
        "coverage_sweep_csv": str(out),
        "projection_vs_observed": projection_summary,
        "rows": len(rows),
        "observed_processed_videos": n_observed,
        "observed_nonempty_rate": observed_nonempty_rate,
    }


def run_real_high_e_diagnostics(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    paths = _output_paths_from_cfg(cfg)
    evalue_path = paths["candidate_evalues"]
    if not evalue_path.exists():
        summary = {
            "status": "requires_candidate_evalues",
            "reason": f"missing {evalue_path}",
            "candidate_evalues": str(evalue_path),
        }
        return summary
    evalues = pd.read_csv(evalue_path)
    if evalues.empty:
        summary = {
            "status": "requires_candidate_evalues",
            "reason": "candidate e-values are empty",
            "candidate_evalues": str(evalue_path),
        }
        return summary

    universe = _load_universe_with_labels(cfg)
    rank_cols = ["path_id", "candidate_rank", "split"]
    if not universe.empty and all(column in universe for column in rank_cols):
        rank_frame = universe[rank_cols].copy()
        rank_frame["candidate_rank"] = pd.to_numeric(rank_frame["candidate_rank"], errors="coerce")
        evalues = evalues.merge(rank_frame, on="path_id", how="left")
    if "candidate_rank" not in evalues:
        evalues["candidate_rank"] = range(1, len(evalues) + 1)
    if "split" not in evalues:
        evalues["split"] = "test"
    evalues["candidate_rank"] = pd.to_numeric(evalues["candidate_rank"], errors="coerce").fillna(10**12)
    evalues["e_value"] = pd.to_numeric(evalues["e_value"], errors="coerce").fillna(0.0)
    evalues["p_any"] = pd.to_numeric(evalues["p_any"], errors="coerce")

    alpha1 = float(cfg.get("risk", {}).get("alpha1", 0.10))
    budgets = _default_high_e_budgets(cfg)
    gammas = _default_high_e_gammas(cfg)
    output_dir = paths["high_e_mass_diagnostics"].parent
    methods = sorted(evalues["method"].dropna().astype(str).unique().tolist())

    diagnostic_rows: list[dict[str, Any]] = []
    gamma_rows: list[dict[str, Any]] = []
    curve_frames: dict[int, list[dict[str, Any]]] = {budget: [] for budget in budgets}

    for method in methods:
        method_frame = evalues[evalues["method"].astype(str) == method].sort_values(["candidate_rank", "score"], ascending=[True, False])
        current_values_all = method_frame["e_value"].astype(float).tolist()
        for budget in budgets:
            values = current_values_all[:budget]
            best = _best_mass_summary(values, alpha1, budget)
            sorted_values = sorted(values, reverse=True)
            diagnostic_rows.append(
                {
                    "method": method,
                    "candidate_budget_M": budget,
                    "alpha1": alpha1,
                    "num_candidates": len(values),
                    "max_e": max(values) if values else None,
                    "e_p99": _quantile(values, 0.99),
                    "e_p95": _quantile(values, 0.95),
                    "e_p90": _quantile(values, 0.90),
                    "count_e_ge_10": sum(1 for value in values if value >= 10.0),
                    "count_e_ge_11": sum(1 for value in values if value >= 11.0),
                    "count_e_ge_12": sum(1 for value in values if value >= 12.0),
                    "best_k_unconstrained": best["best_k"],
                    "best_tau_unconstrained": best["best_tau"],
                    "best_margin_unconstrained": best["best_margin"],
                    "best_mass_ratio_unconstrained": best["best_mass_ratio"],
                    "released_unconstrained": best["released_unconstrained"],
                    "empty_reason": "" if best["released_unconstrained"] else "insufficient_high_e_mass_for_uniform_scs",
                }
            )
            for curve_row in _mass_curve_rows(sorted_values, alpha1, budget):
                curve_frames[budget].append(
                    {
                        "method": method,
                        "candidate_budget_M": budget,
                        **curve_row,
                    }
                )

        for gamma in gammas:
            gamma_frame = method_frame.copy()
            gamma_frame["gamma_e_value"] = gamma * (gamma_frame["p_any"].astype(float) ** (gamma - 1.0))
            gamma_values_all = gamma_frame["gamma_e_value"].astype(float).tolist()
            for budget in budgets:
                values = gamma_values_all[:budget]
                best = _best_mass_summary(values, alpha1, budget)
                gamma_rows.append(
                    {
                        "method": method,
                        "gamma": gamma,
                        "candidate_budget_M": budget,
                        "max_e": max(values) if values else None,
                        "count_e_ge_10": sum(1 for value in values if value >= 10.0),
                        "count_e_ge_11": sum(1 for value in values if value >= 11.0),
                        "count_e_ge_12": sum(1 for value in values if value >= 12.0),
                        "best_k": best["best_k"],
                        "best_tau": best["best_tau"],
                        "best_margin": best["best_margin"],
                        "best_mass_ratio": best["best_mass_ratio"],
                        "released_unconstrained": best["released_unconstrained"],
                    }
                )

    high_e_out = ensure_data_output(paths["high_e_mass_diagnostics"])
    gamma_out = ensure_data_output(paths["gamma_mass_sweep"])
    pd.DataFrame(diagnostic_rows).to_csv(high_e_out, index=False)
    pd.DataFrame(gamma_rows).to_csv(gamma_out, index=False)

    curve_outputs = []
    for budget, rows in curve_frames.items():
        curve_path = ensure_data_output(output_dir / f"scs_feasibility_curve_M{budget}.csv")
        pd.DataFrame(rows).to_csv(curve_path, index=False)
        curve_outputs.append(str(curve_path))

    best_ratio = max((float(row["best_mass_ratio_unconstrained"]) for row in diagnostic_rows), default=0.0)
    gamma_best_ratio = max((float(row["best_mass_ratio"]) for row in gamma_rows), default=0.0)
    return {
        "status": "completed",
        "candidate_evalues": str(evalue_path),
        "high_e_mass_diagnostics_csv": str(high_e_out),
        "gamma_mass_sweep_csv": str(gamma_out),
        "scs_feasibility_curves": curve_outputs,
        "methods": methods,
        "budgets": budgets,
        "gamma_candidates": gammas,
        "best_mass_ratio": best_ratio,
        "best_gamma_mass_ratio": gamma_best_ratio,
        "any_unconstrained_feasible": bool(best_ratio >= 1.0 or gamma_best_ratio >= 1.0),
    }


def export_release_audit_candidates(
    config_path: str | Path,
    method: str | None = None,
    budget: int | None = None,
    out_csv: str | Path | None = None,
    labels_out: str | Path | None = None,
    viewer_path: str | Path | None = None,
    unsupported_only: bool = False,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    paths = _output_paths_from_cfg(cfg)
    evalue_path = paths["candidate_evalues"]
    if not evalue_path.exists():
        return {
            "status": "requires_candidate_evalues",
            "reason": f"missing {evalue_path}",
            "candidate_evalues": str(evalue_path),
        }
    universe = _load_universe_with_labels(cfg)
    if universe.empty:
        return {
            "status": "requires_candidate_universe",
            "reason": "candidate universe is empty or missing",
            "candidate_universe": str(paths["candidate_universe"]),
        }
    evalues = pd.read_csv(evalue_path)
    if evalues.empty:
        return {
            "status": "requires_candidate_evalues",
            "reason": "candidate e-values are empty",
            "candidate_evalues": str(evalue_path),
        }

    preferred_method = method or str(cfg.get("release_audit", {}).get("method", "parc_track_gamma_tuned_uniform_scs"))
    if preferred_method not in set(evalues["method"].astype(str)):
        methods = sorted(evalues["method"].dropna().astype(str).unique().tolist())
        if not methods:
            return {"status": "requires_candidate_evalues", "reason": "candidate e-values have no method column values"}
        preferred_method = methods[0]

    cert_path = paths["real_cert_summary"]
    selected_budget = budget or cfg.get("release_audit", {}).get("candidate_budget_M")
    if selected_budget is None and cert_path.exists():
        cert = pd.read_csv(cert_path)
        rows = cert[(cert["method"].astype(str) == preferred_method) & (pd.to_numeric(cert["released"], errors="coerce") > 0)]
        if not rows.empty:
            rows = rows.copy()
            rows["released"] = pd.to_numeric(rows["released"], errors="coerce")
            rows["candidate_budget_M"] = pd.to_numeric(rows["candidate_budget_M"], errors="coerce")
            rows = rows.sort_values(["released", "candidate_budget_M"], ascending=[False, True])
            selected_budget = int(rows["candidate_budget_M"].iloc[0])
    if selected_budget is None:
        budgets = _candidate_budgets(cfg)
        selected_budget = int(budgets[0]) if budgets else 100
    selected_budget = int(selected_budget)

    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), cfg)
    universe["split"] = universe["video_id"].astype(int).map(split_map)
    test = universe[universe["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    method_evalues = evalues[evalues["method"].astype(str) == preferred_method].copy()
    method_evalues["e_value"] = pd.to_numeric(method_evalues["e_value"], errors="coerce").fillna(0.0)
    method_evalues["p_any"] = pd.to_numeric(method_evalues["p_any"], errors="coerce")
    method_evalues["p_block"] = pd.to_numeric(method_evalues["p_block"], errors="coerce")
    value_map = method_evalues.set_index("path_id")[["e_value", "p_any", "p_block"]].to_dict(orient="index")

    alpha1 = float(cfg.get("risk", {}).get("alpha1", 0.10))
    pool = test.head(selected_budget).copy()
    pool_values = [float(value_map.get(path_id, {}).get("e_value", 0.0)) for path_id in pool["path_id"]]
    k, tau, margin = _scs_release_count(pool_values, alpha1=alpha1, candidate_budget_m=selected_budget)
    selected_positions = sorted(range(len(pool_values)), key=lambda idx: pool_values[idx], reverse=True)[:k]
    selected = pool.iloc[selected_positions].copy() if selected_positions else pool.iloc[[]].copy()
    released_total = int(len(selected))
    if unsupported_only and not selected.empty:
        selected = selected[(~selected["is_matched_to_gt"].astype(bool)) & (~selected["is_verified_positive"].astype(bool))].copy()

    default_out = paths["real_cert_summary"].with_name(
        f"release_audit_{preferred_method}_M{selected_budget}{'_unsupported' if unsupported_only else ''}.csv"
    )
    out = ensure_data_output(out_csv or cfg.get("release_audit", {}).get("out", default_out))
    labels_path = ensure_data_output(
        labels_out
        or cfg.get("release_audit", {}).get("labels_out", out.with_name(out.stem + "_labels.csv"))
    )
    viewer = Path(
        viewer_path
        or cfg.get("release_audit", {}).get("viewer", str(out.parent / f"{out.stem}_viewer"))
    )
    montage_dir = ensure_data_output(viewer / "montages")
    montage_dir.mkdir(parents=True, exist_ok=True)

    nodes = pd.DataFrame()
    if paths["candidate_nodes"].exists():
        nodes = pd.read_csv(paths["candidate_nodes"])
    nodes_by_path = {path_id: group.copy() for path_id, group in nodes.groupby("path_id")} if not nodes.empty else {}

    rows: list[dict[str, Any]] = []
    selected_e_values = []
    for release_rank, (_, row) in enumerate(selected.iterrows(), start=1):
        path_id = row["path_id"]
        ev = value_map.get(path_id, {})
        e_value = float(ev.get("e_value", 0.0))
        selected_e_values.append(e_value)
        montage_path = montage_dir / f"{path_id}.jpg"
        if path_id in nodes_by_path:
            try:
                _create_montage(_path_from_nodes(row.to_dict(), nodes_by_path[path_id]), montage_path, frames_per_path=8)
            except Exception:
                pass
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
            "montage_path": str(montage_path) if montage_path.exists() else "",
            "method": preferred_method,
            "candidate_budget_M": selected_budget,
            "selected_rank": release_rank,
            "e_value": e_value,
            "p_any": ev.get("p_any", ""),
            "p_block": ev.get("p_block", ""),
            "tau_k": tau if k else "",
            "self_consistency_margin": margin if k else "",
            "release_source": str(evalue_path),
        }
        rows.append(audit_row)

    pd.DataFrame(rows, columns=RELEASE_AUDIT_COLUMNS).to_csv(out, index=False)

    if not _label_template_has_labels(labels_path):
        with labels_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(
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

    index_path = _write_audit_index(viewer, rows, reason="release_audit_ready" if rows else "no_released_candidates")
    manifest_path = ensure_data_output(out.with_name(out.stem + "_manifest.json"))
    manifest = {
        "status": "completed" if rows else "empty_release",
        "method": preferred_method,
        "candidate_budget_M": selected_budget,
        "alpha1": alpha1,
        "released": len(rows),
        "released_total": released_total,
        "unsupported_only": unsupported_only,
        "tau_k": tau if k else None,
        "self_consistency_margin": margin if k else None,
        "selected_e_min": min(selected_e_values) if selected_e_values else None,
        "selected_e_mean": sum(selected_e_values) / len(selected_e_values) if selected_e_values else None,
        "selected_e_max": max(selected_e_values) if selected_e_values else None,
        "release_audit_csv": str(out),
        "label_template_csv": str(labels_path),
        "viewer_index": str(index_path),
        "candidate_evalues": str(evalue_path),
    }
    write_json(manifest_path, manifest)
    manifest["manifest"] = str(manifest_path)
    return manifest


def run_real_mini(config_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    dataset = cfg.get("dataset", {}).get("name", "unknown")
    dataset_report = inspect_dataset_from_config(config_path)
    cell_out = cfg.get("output", {}).get("cell_effective_n", "./outputs/phase2/cell_effective_n.csv")
    cell_summary = compute_cell_effective_n(config_path, cell_out)
    default_candidates = Path("./outputs/phase2/audit_candidates.csv")
    default_labels = Path("./outputs/phase2/audit_labels.csv")
    candidate_rows = 0
    labeled_rows = 0
    if default_candidates.exists():
        try:
            candidate_rows = int(len(pd.read_csv(default_candidates)))
        except Exception:
            candidate_rows = 0
    if default_labels.exists():
        try:
            labels = pd.read_csv(default_labels)
            labeled_rows = int(len(labels[labels.get("label", "").isin(["actually_true", "actually_false", "uncertain"])]))
            verified_rows = int(
                labels.get("verified_positive_for_calibration", pd.Series(dtype=str))
                .fillna("")
                .astype(str)
                .str.lower()
                .isin(["yes", "true", "1"])
                .sum()
            )
        except Exception:
            labeled_rows = 0
            verified_rows = 0
    else:
        verified_rows = 0
    if dataset_report.get("status") != "tracking_layout_ok":
        status = "not_ready"
        reason = dataset_report.get("reason", "")
    elif candidate_rows <= 0:
        status = "requires_cached_proposals"
        reason = "run audit sample before real mini certification"
    elif labeled_rows <= 0:
        status = "requires_audit_labels"
        reason = "audit candidates exist; manual labels are required before audited FTR / verified-positive calibration"
    else:
        status = "completed_audited_subset_scaffold"
        reason = "manual audit labels are present; wrote audited-subset certification scaffold"
    real_cert_summary = None
    if status == "completed_audited_subset_scaffold":
        cert_out = cfg.get("output", {}).get(
            "real_cert_summary",
            "./outputs/phase2/real_cert_summary.csv",
        )
        real_cert_summary = _build_real_cert_summary(cfg, default_candidates, default_labels, cell_out, cert_out)
        try:
            cert_rows = pd.read_csv(real_cert_summary["real_cert_summary_csv"])
            parc = cert_rows[cert_rows["method"] == "parc_track_gamma_tuned_uniform_scs"].iloc[0]
            gamma_value = float(parc["gamma"])
            gamma_star_value = float(parc["gamma_star"])
            released_value = int(parc["released"])
            utr_value = float(parc["utr"])
            audited_ftr_value = float(parc["audited_ftr_on_labeled_subset"])
            mean_recall_value = float(parc["mean_recall_on_audit_true"])
            empty_rate_value = float(parc["empty_rate"])
        except Exception:
            gamma_value = None
            gamma_star_value = None
            released_value = 0
            utr_value = None
            audited_ftr_value = None
            mean_recall_value = None
            empty_rate_value = None
    else:
        gamma_value = None
        gamma_star_value = None
        released_value = 0
        utr_value = None
        audited_ftr_value = None
        mean_recall_value = None
        empty_rate_value = None
    summary = {
        "dataset": dataset,
        "alpha1": cfg.get("risk", {}).get("alpha1", 0.10),
        "status": status,
        "reason": reason,
        "methods": [
            "unmatched_as_false_block",
            "null_superset_block_evalues",
            "parc_track_gamma_tuned_uniform_scs",
        ],
        "audit_candidate_rows": candidate_rows,
        "audit_labeled_rows": labeled_rows,
        "verified_positive_for_calibration_rows": verified_rows,
        "gamma": gamma_value,
        "gamma_star_median_cell": gamma_star_value,
        "released": released_value,
        "utr": utr_value,
        "audited_ftr": audited_ftr_value,
        "mean_recall": mean_recall_value,
        "empty_rate": empty_rate_value,
        "cell_effective_n_summary": cell_summary,
        "real_cert_summary": real_cert_summary,
        "dataset_report": dataset_report,
    }
    write_json(out_path, summary)
    return summary
