from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import time
import zipfile


DATA_ROOT = Path("/home/waas/paper_experiments")
KEEP_ROOT_NAMES = {"annotations", "frames", ".cache", ".extract_markers", "cache", "downloads"}


def _is_under_workspace(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == DATA_ROOT or DATA_ROOT in resolved.parents


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _clean_partial_extracts(local_dir: Path) -> dict:
    removed: list[str] = []
    for child in local_dir.iterdir():
        if child.name in KEEP_ROOT_NAMES:
            continue
        if child.is_dir():
            shutil.rmtree(child)
            removed.append(str(child))
        elif child.is_file():
            child.unlink()
            removed.append(str(child))
    for split in ("train", "val"):
        split_dir = local_dir / split
        if split_dir.exists():
            shutil.rmtree(split_dir)
            removed.append(str(split_dir))
    marker_dir = local_dir / ".extract_markers"
    if marker_dir.exists():
        for marker in marker_dir.glob("frames__*.done"):
            marker.unlink()
            removed.append(str(marker))
    return {"removed_count": len(removed), "removed_sample": removed[:50]}


def _required_by_zip(annotation: dict) -> dict[tuple[str, str], list[tuple[str, str]]]:
    grouped: dict[tuple[str, str], list[tuple[str, str]]] = {}
    seen: set[str] = set()
    for image in annotation.get("images", []):
        file_name = str(image.get("file_name", "")).strip()
        if not file_name or file_name in seen:
            continue
        seen.add(file_name)
        parts = file_name.split("/")
        if len(parts) < 4:
            continue
        split, group = parts[0], parts[1]
        member = "/".join(parts[2:])
        grouped.setdefault((split, group), []).append((member, file_name))
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation", default=str(DATA_ROOT / "data" / "TAO" / "annotations" / "trainval.json"))
    parser.add_argument("--local-dir", default=str(DATA_ROOT / "data" / "TAO"))
    parser.add_argument("--zip-root", default=str(DATA_ROOT / "data" / "TAO" / "frames"))
    parser.add_argument(
        "--manifest",
        default=str(DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval_extract_manifest.json"),
    )
    parser.add_argument("--clean-partial", action="store_true")
    args = parser.parse_args()

    annotation_path = Path(args.annotation)
    local_dir = Path(args.local_dir).resolve()
    zip_root = Path(args.zip_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    for path in (local_dir, zip_root, manifest_path):
        if not _is_under_workspace(path):
            raise SystemExit(f"Refusing to use path outside workspace: {path}")
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    cleanup = _clean_partial_extracts(local_dir) if args.clean_partial else {"removed_count": 0, "removed_sample": []}
    grouped = _required_by_zip(annotation)
    started = time.time()
    rows: list[dict] = []
    payload = {
        "status": "running",
        "mode": "annotation_required_frames_only",
        "started": started,
        "annotation": str(annotation_path),
        "local_dir": str(local_dir),
        "zip_root": str(zip_root),
        "cleanup": cleanup,
        "files": rows,
    }
    _write(manifest_path, payload)

    total_required = 0
    total_extracted = 0
    total_skipped = 0
    total_missing = 0
    for (split, group), required in sorted(grouped.items()):
        zip_path = zip_root / split / f"{group}.zip"
        row = {
            "file": f"frames/{split}/{group}.zip",
            "zip_path": str(zip_path),
            "status": "pending",
            "required": len(required),
            "extracted": 0,
            "skipped_existing": 0,
            "missing": 0,
            "missing_sample": [],
            "error": "",
        }
        rows.append(row)
        _write(manifest_path, payload)
        total_required += len(required)
        if not zip_path.exists():
            row["status"] = "failed"
            row["error"] = "zip_missing"
            payload["status"] = "failed"
            _write(manifest_path, payload)
            return 2
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                row["status"] = "extracting"
                _write(manifest_path, payload)
                for member, dest_rel in required:
                    dest = (local_dir / dest_rel).resolve()
                    if not _is_under_workspace(dest) or not str(dest).startswith(str(local_dir)):
                        row["status"] = "failed"
                        row["error"] = f"unsafe_destination:{dest_rel}"
                        payload["status"] = "failed"
                        _write(manifest_path, payload)
                        return 2
                    if member not in names:
                        row["missing"] += 1
                        if len(row["missing_sample"]) < 10:
                            row["missing_sample"].append(member)
                        continue
                    if dest.exists() and dest.stat().st_size > 0:
                        row["skipped_existing"] += 1
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as src, dest.open("wb") as out:
                        shutil.copyfileobj(src, out, length=1024 * 1024)
                    row["extracted"] += 1
            row["status"] = "done" if row["missing"] == 0 else "done_with_missing"
        except Exception as exc:
            row["status"] = "failed"
            row["error"] = f"{type(exc).__name__}:{exc}"
            payload["status"] = "failed"
            _write(manifest_path, payload)
            return 2
        total_extracted += int(row["extracted"])
        total_skipped += int(row["skipped_existing"])
        total_missing += int(row["missing"])
        payload.update(
            {
                "total_required": total_required,
                "total_extracted": total_extracted,
                "total_skipped_existing": total_skipped,
                "total_missing": total_missing,
                "updated": time.time(),
            }
        )
        _write(manifest_path, payload)

    payload.update(
        {
            "status": "completed" if total_missing == 0 else "completed_with_missing",
            "finished": time.time(),
            "total_required": total_required,
            "total_extracted": total_extracted,
            "total_skipped_existing": total_skipped,
            "total_missing": total_missing,
        }
    )
    _write(manifest_path, payload)
    return 0 if total_missing == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
