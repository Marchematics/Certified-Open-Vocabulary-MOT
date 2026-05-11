from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import zipfile


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()


@dataclass(frozen=True)
class DatasetCatalogEntry:
    name: str
    path: str
    exists: bool
    kind: str
    image_entries: int = 0
    json_entries: int = 0
    tracking_like_entries: int = 0
    usable_for_mot_benchmark: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _is_under_data_root(path: Path) -> bool:
    resolved = path.resolve()
    if resolved == DATA_ROOT or DATA_ROOT in resolved.parents:
        return True
    extra_roots = os.environ.get("PARC_TRACK_EXTRA_OUTPUT_ROOTS", "")
    for raw_root in extra_roots.split(":"):
        if not raw_root.strip():
            continue
        root = Path(raw_root).resolve()
        if resolved == root or root in resolved.parents:
            return True
    return False


def ensure_data_output(path: str | Path) -> Path:
    out = Path(path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not _is_under_data_root(out):
        raise ValueError(f"Refusing to write outside data disk workspace: {out}")
    return out


def load_yaml(path: str | Path) -> dict[str, Any]:
    import yaml

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: dict[str, Any]) -> Path:
    out = ensure_data_output(path)
    with out.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    return out


def inspect_bdd100k_zip(path: str) -> DatasetCatalogEntry:
    zip_path = Path(path)
    if not zip_path.exists():
        return DatasetCatalogEntry(
            name="bdd100k_zip",
            path=str(zip_path),
            exists=False,
            kind="zip",
            note="Archive not found.",
        )

    image_entries = 0
    json_entries = 0
    tracking_like_entries = 0
    tracking_tokens = ("track", "mot", "box_track", "seg_track", "box-track")
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            lower = name.lower()
            if lower.endswith((".jpg", ".jpeg", ".png")):
                image_entries += 1
            if lower.endswith(".json"):
                json_entries += 1
            if any(token in lower for token in tracking_tokens):
                tracking_like_entries += 1

    usable = tracking_like_entries > 0
    note = (
        "Tracking-like entries were found; verify layout before benchmark use."
        if usable
        else "Image/JSON archive only in current inspection; cataloged as proxy data, not MOT tracking benchmark."
    )
    return DatasetCatalogEntry(
        name="bdd100k_zip",
        path=str(zip_path),
        exists=True,
        kind="zip",
        image_entries=image_entries,
        json_entries=json_entries,
        tracking_like_entries=tracking_like_entries,
        usable_for_mot_benchmark=usable,
        note=note,
    )


def _annotation_has_tracks(annotation: dict[str, Any]) -> bool:
    anns = annotation.get("annotations", [])
    if not anns:
        return False
    track_keys = ("track_id", "instance_id", "track")
    return any(any(key in ann for key in track_keys) for ann in anns)


def _annotation_has_frame_indices(annotation: dict[str, Any]) -> bool:
    images = annotation.get("images", [])
    anns = annotation.get("annotations", [])
    image_keys = ("frame_id", "frame_index", "frame", "index", "video_frame_id")
    ann_keys = ("frame_id", "frame_index", "frame", "image_id")
    return any(any(key in image for key in image_keys) for image in images) or any(
        any(key in ann for key in ann_keys) for ann in anns
    )


def _annotation_has_video_ids(annotation: dict[str, Any]) -> bool:
    if annotation.get("videos"):
        return True
    images = annotation.get("images", [])
    anns = annotation.get("annotations", [])
    return any("video_id" in image for image in images) or any("video_id" in ann for ann in anns)


def _annotation_counts(annotation: dict[str, Any]) -> dict[str, int | None]:
    anns = annotation.get("annotations", [])
    images = annotation.get("images", [])
    cats = annotation.get("categories", [])
    videos = annotation.get("videos", [])
    tracks = set()
    for ann in anns:
        for key in ("track_id", "instance_id", "track"):
            if key in ann:
                tracks.add(ann[key])
                break
    return {
        "num_videos": len(videos) if videos else len({img.get("video_id") for img in images if "video_id" in img}) or None,
        "num_frames": len(images) or None,
        "num_tracks": len(tracks) or None,
        "num_boxes": len(anns) or None,
        "num_categories": len(cats) or None,
    }


def _frame_path_candidates(dataset_root: Path, annotation: dict[str, Any], limit: int = 100) -> list[Path]:
    candidates: list[Path] = []
    for image in annotation.get("images", [])[:limit]:
        for key in ("file_name", "path", "filename"):
            value = image.get(key)
            if not value:
                continue
            candidates.append(dataset_root / value)
            candidates.append(dataset_root / "OVT-B" / value)
            candidates.append(dataset_root.parent / value)
    return candidates


def inspect_coco_video_dataset(
    dataset_name: str,
    dataset_root: str | Path,
    ann_file: str | Path,
    annotation_format: str,
) -> dict[str, Any]:
    root = Path(dataset_root)
    ann_path = Path(ann_file)
    errors: list[str] = []
    if not root.exists():
        errors.append(f"dataset_root_missing:{root}")
    if not ann_path.exists():
        errors.append(f"ann_file_missing:{ann_path}")
    if errors:
        return {
            "dataset_name": dataset_name,
            "dataset_root": str(root),
            "ann_file": str(ann_path),
            "status": "missing_files",
            "reason": ";".join(errors),
            "has_video_frames": False,
            "has_tracking_annotations": False,
            "has_track_ids": False,
            "has_category_labels": False,
            "has_frame_indices": False,
            "has_video_ids": False,
            "annotation_format": annotation_format,
            "annotation_mode": "partial_or_unknown",
            "errors": errors,
        }

    try:
        annotation = load_json(ann_path)
    except Exception as exc:
        return {
            "dataset_name": dataset_name,
            "dataset_root": str(root),
            "ann_file": str(ann_path),
            "status": "not_mot_tracking_layout",
            "reason": f"annotation_json_load_failed:{type(exc).__name__}:{exc}",
            "errors": [str(exc)],
        }

    has_tracking_annotations = bool(annotation.get("annotations"))
    has_track_ids = _annotation_has_tracks(annotation)
    has_category_labels = bool(annotation.get("categories"))
    has_frame_indices = _annotation_has_frame_indices(annotation)
    has_video_ids = _annotation_has_video_ids(annotation)
    frame_candidates = _frame_path_candidates(root, annotation)
    existing_frames = [path for path in frame_candidates if path.exists()]
    has_video_frames = bool(existing_frames)
    counts = _annotation_counts(annotation)
    errors = []
    for field, value in (
        ("has_video_frames", has_video_frames),
        ("has_tracking_annotations", has_tracking_annotations),
        ("has_track_ids", has_track_ids),
        ("has_category_labels", has_category_labels),
        ("has_frame_indices", has_frame_indices),
        ("has_video_ids", has_video_ids),
    ):
        if not value:
            errors.append(f"missing_{field}")
    status = "tracking_layout_ok" if not errors else "not_mot_tracking_layout"
    report: dict[str, Any] = {
        "dataset_name": dataset_name,
        "dataset_root": str(root),
        "ann_file": str(ann_path),
        "status": status,
        "reason": "" if status == "tracking_layout_ok" else ",".join(errors),
        "has_video_frames": has_video_frames,
        "has_tracking_annotations": has_tracking_annotations,
        "has_track_ids": has_track_ids,
        "has_category_labels": has_category_labels,
        "has_frame_indices": has_frame_indices,
        "has_video_ids": has_video_ids,
        "annotation_format": annotation_format,
        "annotation_mode": "partial_or_unknown",
        "errors": errors,
        "sample_existing_frame": str(existing_frames[0]) if existing_frames else None,
    }
    report.update(counts)
    return report


def inspect_bdd100k_mot_layout(dataset_root: str | Path) -> dict[str, Any]:
    root = Path(dataset_root)
    images_track = root / "images" / "track"
    labels_a = root / "labels-20" / "box-track"
    labels_b = root / "labels" / "box_track_20"
    has_images_track = images_track.exists()
    label_root = labels_a if labels_a.exists() else labels_b
    has_labels = label_root.exists()
    json_files = list(label_root.glob("*/*.json"))[:5] if has_labels else []
    status = "tracking_layout_ok" if has_images_track and has_labels and json_files else "not_mot_tracking_layout"
    errors = []
    if not has_images_track:
        errors.append("missing_images_track")
    if not has_labels:
        errors.append("missing_box_track_labels")
    if has_labels and not json_files:
        errors.append("missing_label_json")
    return {
        "dataset_name": "BDD100K-MOT",
        "dataset_root": str(root),
        "status": status,
        "reason": ",".join(errors),
        "has_video_frames": has_images_track,
        "has_tracking_annotations": has_labels and bool(json_files),
        "has_track_ids": has_labels and bool(json_files),
        "has_category_labels": has_labels and bool(json_files),
        "has_frame_indices": has_labels and bool(json_files),
        "has_video_ids": has_images_track and has_labels,
        "num_videos": None,
        "num_frames": None,
        "num_tracks": None,
        "num_boxes": None,
        "num_categories": None,
        "annotation_format": "bdd100k_box_track",
        "annotation_mode": "dense_or_unknown",
        "errors": errors,
    }


def inspect_dataset_from_config(config_path: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    dataset = cfg.get("dataset", {})
    name = str(dataset.get("name", "")).lower()
    if name in {"ovt-b", "ovtb"}:
        report = inspect_coco_video_dataset(
            dataset_name="OVT-B",
            dataset_root=dataset.get("root", "./data/OVT-B"),
            ann_file=dataset.get("ann_file", "./data/OVT-B/ovtb_ann.json"),
            annotation_format=dataset.get("format_hint", "tao_or_coco_video"),
        )
    elif name in {"tao", "ov-tao", "ov_tao"}:
        report = inspect_coco_video_dataset(
            dataset_name=dataset.get("name", "TAO"),
            dataset_root=dataset.get("root", "./data/TAO"),
            ann_file=dataset.get("ann_file", "./data/TAO/annotations/train.json"),
            annotation_format=dataset.get("format_hint", "tao"),
        )
    elif name in {"burst", "lv-vis", "lvvis", "lv_vis"}:
        report = inspect_coco_video_dataset(
            dataset_name=dataset.get("name", "BURST"),
            dataset_root=dataset.get("root", "./data/BURST"),
            ann_file=dataset.get(
                "ann_file",
                "./outputs/phase7_third_dataset/burst_val_box_annotations.json",
            ),
            annotation_format=dataset.get("format_hint", "coco_video_or_tracking_json"),
        )
    elif name in {"bdd100k", "bdd100k-mot"}:
        report = inspect_bdd100k_mot_layout(dataset.get("root", "./data/BDD100K"))
    else:
        report = {"dataset_name": dataset.get("name", "unknown"), "status": "missing_files", "reason": "unknown_dataset_name"}
    if out_path is not None:
        write_json(out_path, report)
    return report


def fetch_ovtb_from_config(config_path: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    dataset = cfg.get("dataset", {})
    root = Path(dataset.get("root", "./data/OVT-B")).resolve()
    if not _is_under_data_root(root):
        raise ValueError(f"Refusing to prepare OVT-B outside data disk workspace: {root}")
    root.mkdir(parents=True, exist_ok=True)
    expected_groups = {
        "frames": ["OVT-B"],
        "annotation": ["ovtb_ann.json"],
        "classname": ["ovtb_classname.py"],
        "format": ["OVTB-format.txt"],
        "classes": ["ovtb_class.pth", "ovtb_classes.txt"],
        "prompt": ["ovtb_prompt.pth", "ovtb_class_prompt.pt"],
    }

    def _present_groups() -> dict[str, str | None]:
        return {
            group: next((name for name in names if (root / name).exists()), None)
            for group, names in expected_groups.items()
        }

    present_groups = _present_groups()
    present = [value for value in present_groups.values() if value is not None]
    google_url = cfg.get("download", {}).get(
        "google_drive_url",
        "https://drive.google.com/drive/folders/1Qfmb6tEF92I2k84NgrkjEbOKnFlsrTVZ?usp=drive_link",
    )
    baidu_url = cfg.get("download", {}).get(
        "baidu_url",
        "https://pan.baidu.com/s/1hy44z_om609jIhXjRxXCug?pwd=8yy3",
    )
    download_attempt: dict[str, Any] | None = None
    if any(value is None for value in present_groups.values()) and cfg.get("download", {}).get("auto_attempt", True):
        timeout_sec = int(cfg.get("download", {}).get("timeout_sec", 120))
        command = [
            sys.executable,
            "-m",
            "gdown",
            "--folder",
            "--continue",
            "--no-cookies",
            google_url,
            "-O",
            str(root) + "/",
        ]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            download_attempt = {
                "tool": "gdown",
                "command": " ".join(command),
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-2000:],
                "stderr_tail": result.stderr[-2000:],
            }
        except ModuleNotFoundError as exc:
            download_attempt = {"tool": "gdown", "error": f"module_missing:{exc}"}
        except subprocess.TimeoutExpired as exc:
            download_attempt = {
                "tool": "gdown",
                "command": " ".join(command),
                "error": f"timeout_after_{timeout_sec}s",
                "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
                "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
            }
        present_groups = _present_groups()
        present = [value for value in present_groups.values() if value is not None]
    status = "already_present" if all(value is not None for value in present_groups.values()) else "download_blocked"
    report = {
        "dataset_name": "OVT-B",
        "dataset_root": str(root),
        "status": status,
        "present_expected_files": present,
        "present_expected_groups": present_groups,
        "missing_expected_files": [
            "/".join(names) for group, names in expected_groups.items() if present_groups[group] is None
        ],
        "attempted_urls": {"google_drive": google_url, "baidu": baidu_url},
        "download_attempt": download_attempt,
        "reason": (
            "All expected files are present."
            if status == "already_present"
            else "Automatic Google Drive folder download did not produce the full expected OVT-B layout; place the official OVT-B files at dataset_root and rerun dataset inspect."
        ),
        "expected_manual_destination": str(root),
    }
    if out_path is not None:
        write_json(out_path, report)
    return report
