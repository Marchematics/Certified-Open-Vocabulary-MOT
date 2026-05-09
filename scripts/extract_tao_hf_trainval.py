from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile


DATA_ROOT = Path("/home/waas/paper_experiments")
DEFAULT_LOCAL_DIR = DATA_ROOT / "data" / "TAO"
DEFAULT_DOWNLOAD_MANIFEST = DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval_download_manifest.json"
DEFAULT_EXTRACT_MANIFEST = DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval_extract_manifest.json"


def _is_under_workspace(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == DATA_ROOT or DATA_ROOT in resolved.parents


def _safe_members(zip_path: Path, local_dir: Path) -> tuple[bool, str, int]:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            for name in names:
                target = (local_dir / name).resolve()
                if not _is_under_workspace(target) or not str(target).startswith(str(local_dir.resolve())):
                    return False, f"unsafe_zip_member:{name}", len(names)
            return True, "", len(names)
    except Exception as exc:
        return False, f"zip_inspect_failed:{type(exc).__name__}:{exc}", 0


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-dir", default=str(DEFAULT_LOCAL_DIR))
    parser.add_argument("--download-manifest", default=str(DEFAULT_DOWNLOAD_MANIFEST))
    parser.add_argument("--extract-manifest", default=str(DEFAULT_EXTRACT_MANIFEST))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    local_dir = Path(args.local_dir).resolve()
    download_manifest = Path(args.download_manifest)
    extract_manifest = Path(args.extract_manifest)
    if not _is_under_workspace(local_dir) or not _is_under_workspace(extract_manifest):
        raise SystemExit(f"Refusing to write outside workspace: {local_dir} / {extract_manifest}")
    if not download_manifest.exists():
        raise SystemExit(f"Download manifest missing: {download_manifest}")

    download = json.loads(download_manifest.read_text(encoding="utf-8"))
    rows = download.get("files", [])
    zip_rows = [row for row in rows if str(row.get("file", "")).startswith("frames/") and str(row.get("file", "")).endswith(".zip")]
    missing = [row.get("file") for row in zip_rows if row.get("status") != "done" or not row.get("path")]
    if missing:
        payload = {
            "status": "waiting_for_downloads",
            "missing": missing,
            "download_manifest": str(download_manifest),
            "updated": time.time(),
        }
        _write_manifest(extract_manifest, payload)
        return 3

    started = time.time()
    extract_rows: list[dict] = []
    payload = {
        "status": "running",
        "started": started,
        "local_dir": str(local_dir),
        "download_manifest": str(download_manifest),
        "files": extract_rows,
    }
    _write_manifest(extract_manifest, payload)

    for row in zip_rows:
        zip_path = Path(row["path"]).resolve()
        marker = local_dir / ".extract_markers" / (str(row["file"]).replace("/", "__") + ".done")
        out_row = {
            "file": row["file"],
            "zip_path": str(zip_path),
            "status": "pending",
            "members": None,
            "marker": str(marker),
            "error": "",
        }
        extract_rows.append(out_row)
        _write_manifest(extract_manifest, payload)
        if marker.exists() and not args.force:
            out_row.update({"status": "skipped_existing_marker"})
            _write_manifest(extract_manifest, payload)
            continue
        if not zip_path.exists():
            out_row.update({"status": "failed", "error": "zip_missing"})
            payload["status"] = "failed"
            payload["finished"] = time.time()
            _write_manifest(extract_manifest, payload)
            return 2
        ok, error, members = _safe_members(zip_path, local_dir)
        out_row["members"] = members
        if not ok:
            out_row.update({"status": "failed", "error": error})
            payload["status"] = "failed"
            payload["finished"] = time.time()
            _write_manifest(extract_manifest, payload)
            return 2
        out_row["status"] = "extracting"
        _write_manifest(extract_manifest, payload)
        result = subprocess.run(
            ["unzip", "-q", "-n", str(zip_path), "-d", str(local_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            out_row.update({"status": "failed", "error": result.stderr[-4000:]})
            payload["status"] = "failed"
            payload["finished"] = time.time()
            _write_manifest(extract_manifest, payload)
            return result.returncode or 2
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(time.time()), encoding="utf-8")
        out_row["status"] = "done"
        _write_manifest(extract_manifest, payload)

    payload["status"] = "completed"
    payload["finished"] = time.time()
    _write_manifest(extract_manifest, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
