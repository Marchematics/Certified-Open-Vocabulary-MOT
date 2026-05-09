from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from huggingface_hub import hf_hub_download


REPO_ID = "chengyenhsieh/TAO-Amodal"
FILES = [
    "annotations/train.json",
    "annotations/validation.json",
    "annotations/train_with_freeform.json",
    "annotations/validation_with_freeform.json",
    "annotations/checksums/train_checksums.json",
    "annotations/checksums/validation_checksums.json",
    "frames/train/AVA.zip",
    "frames/train/ArgoVerse.zip",
    "frames/train/BDD.zip",
    "frames/train/Charades.zip",
    "frames/train/HACS.zip",
    "frames/train/LaSOT.zip",
    "frames/train/YFCC100M.zip",
    "frames/val/AVA.zip",
    "frames/val/ArgoVerse.zip",
    "frames/val/BDD.zip",
    "frames/val/Charades.zip",
    "frames/val/HACS.zip",
    "frames/val/LaSOT.zip",
    "frames/val/YFCC100M.zip",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", default="")
    parser.add_argument("--local-dir", default="/home/waas/paper_experiments/data/TAO")
    parser.add_argument("--manifest", default="/home/waas/paper_experiments/outputs/phase3_tao/tao_hf_trainval_download_manifest.json")
    args = parser.parse_args()

    token = ""
    if args.token_file:
        token_path = Path(args.token_file)
        token = token_path.read_text(encoding="utf-8").strip()
        try:
            token_path.unlink()
        except FileNotFoundError:
            pass
    if not token:
        token_path = Path("/home/waas/paper_experiments/cache/huggingface/token")
        if token_path.exists():
            token = token_path.read_text(encoding="utf-8").strip()

    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    started = time.time()
    for name in FILES:
        row = {"file": name, "status": "pending", "path": "", "bytes": None, "error": ""}
        rows.append(row)
        manifest_path.write_text(
            json.dumps({"repo_id": REPO_ID, "started": started, "files": rows}, indent=2),
            encoding="utf-8",
        )
        try:
            path = hf_hub_download(
                repo_id=REPO_ID,
                repo_type="dataset",
                filename=name,
                local_dir=local_dir,
                token=token or True,
                resume_download=True,
            )
            p = Path(path)
            row.update({"status": "done", "path": str(p), "bytes": p.stat().st_size})
        except Exception as exc:  # pragma: no cover - runtime report path
            row.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            manifest_path.write_text(
                json.dumps({"repo_id": REPO_ID, "started": started, "finished": time.time(), "files": rows}, indent=2),
                encoding="utf-8",
            )
            return 2
        manifest_path.write_text(
            json.dumps({"repo_id": REPO_ID, "started": started, "files": rows}, indent=2),
            encoding="utf-8",
        )
    manifest_path.write_text(
        json.dumps({"repo_id": REPO_ID, "started": started, "finished": time.time(), "files": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
