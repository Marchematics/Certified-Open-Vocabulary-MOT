from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


DATA_ROOT = Path("/home/waas/paper_experiments")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _download_complete(manifest: Path) -> bool:
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return False
    rows = data.get("files", [])
    frame_rows = [r for r in rows if str(r.get("file", "")).startswith("frames/") and str(r.get("file", "")).endswith(".zip")]
    return bool(frame_rows) and all(r.get("status") == "done" and r.get("path") for r in frame_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid-file", default=str(DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval_download.pid"))
    parser.add_argument(
        "--download-manifest",
        default=str(DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval.json"),
    )
    parser.add_argument(
        "--status",
        default=str(DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval.json"),
    )
    parser.add_argument("--poll-sec", type=int, default=60)
    args = parser.parse_args()

    pid_file = Path(args.pid_file)
    download_manifest = Path(args.download_manifest)
    status_path = Path(args.status)
    started = time.time()
    pid = None
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = None

    while True:
        state = {
            "status": "waiting_for_download",
            "started": started,
            "updated": time.time(),
            "download_pid": pid,
            "download_pid_alive": bool(pid and _alive(pid)),
            "download_complete": _download_complete(download_manifest),
        }
        _write(status_path, state)
        if state["download_complete"] or not state["download_pid_alive"]:
            break
        time.sleep(max(5, args.poll_sec))

    if not _download_complete(download_manifest):
        state = {
            "status": "download_not_complete",
            "started": started,
            "updated": time.time(),
            "download_pid": pid,
            "download_pid_alive": bool(pid and _alive(pid)),
        }
        _write(status_path, state)
        return 3

    commands = [
        [
            str(DATA_ROOT / ".venv" / "bin" / "python"),
            str(DATA_ROOT / "scripts" / "merge_tao_train_val_annotations.py"),
        ],
        [
            str(DATA_ROOT / ".venv" / "bin" / "python"),
            str(DATA_ROOT / "scripts" / "extract_tao_required_frames.py"),
            "--annotation",
            str(DATA_ROOT / "data" / "TAO" / "annotations" / "trainval.json"),
            "--local-dir",
            str(DATA_ROOT / "data" / "TAO"),
            "--zip-root",
            str(DATA_ROOT / "data" / "TAO" / "frames"),
            "--manifest",
            str(DATA_ROOT / "outputs" / "phase3_tao" / "tao_hf_trainval.json"),
            "--clean-partial",
        ],
        [
            str(DATA_ROOT / ".venv" / "bin" / "python"),
            "-m",
            "parc_track.cli",
            "dataset",
            "inspect",
            "--config",
            str(DATA_ROOT / "configs" / "phase3_tao_full_train_inspect.yaml"),
            "--out",
            str(DATA_ROOT / "outputs" / "phase3_tao" / "dataset_adapter_report_tao_full_train.json"),
        ],
        [
            str(DATA_ROOT / ".venv" / "bin" / "python"),
            "-m",
            "parc_track.cli",
            "dataset",
            "inspect",
            "--config",
            str(DATA_ROOT / "configs" / "phase3_tao_full_val_inspect.yaml"),
            "--out",
            str(DATA_ROOT / "outputs" / "phase3_tao" / "dataset_adapter_report_tao_full_val.json"),
        ],
    ]
    log_path = DATA_ROOT / "outputs" / "phase3_tao" / "logs" / "tao_hf_trainval_extract.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("EXP_ROOT", str(DATA_ROOT))
    env.setdefault("TMPDIR", str(DATA_ROOT / "tmp"))
    env.setdefault("HF_HOME", str(DATA_ROOT / "cache" / "huggingface"))
    env.setdefault("HUGGINGFACE_HUB_CACHE", str(DATA_ROOT / "cache" / "huggingface" / "hub"))
    env.setdefault("TRANSFORMERS_CACHE", str(DATA_ROOT / "cache" / "huggingface" / "transformers"))
    env["PYTHONPATH"] = str(DATA_ROOT / "code" / "parc_track") + os.pathsep + env.get("PYTHONPATH", "")
    with log_path.open("a", encoding="utf-8") as log:
        for command in commands:
            _write(
                status_path,
                {"status": "running_command", "updated": time.time(), "command": command, "started": started},
            )
            result = subprocess.run(command, cwd=str(DATA_ROOT), env=env, stdout=log, stderr=log, text=True)
            if result.returncode != 0:
                _write(
                    status_path,
                    {
                        "status": "failed",
                        "updated": time.time(),
                        "command": command,
                        "returncode": result.returncode,
                        "log": str(log_path),
                    },
                )
                return result.returncode
    _write(status_path, {"status": "completed", "started": started, "finished": time.time(), "log": str(log_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
