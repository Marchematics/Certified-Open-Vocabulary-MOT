#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<PARC_ROOT>")
CODE = ROOT / "github/Certified-Open-Vocabulary-MOT/code/parc_track"

import sys

sys.path.insert(0, str(CODE))

from parc_track.adapters.datasets import ensure_data_output, load_yaml, write_json  # noqa: E402
from parc_track.phase2 import _best_mass_summary, _load_universe_with_labels, _split_video_ids  # noqa: E402


PARC_METHOD = "parc_track_gamma_tuned_uniform_scs"
ALPHAS = [0.10, 0.20]
SEEDS = [0, 1, 2]
BUDGET = 150


ENTRIES = [
    {
        "dataset": "OVT-B",
        "generator": "GroundingDINO",
        "config": ROOT / "configs/phase3_ovtb_full_matrix.yaml",
        "matrix": ROOT / "outputs/phase3_ovtb_full/ovtb_alpha_seed_m_matrix.csv",
        "output_dir": ROOT / "outputs/phase3_ovtb_full",
    },
    {
        "dataset": "TAO",
        "generator": "GroundingDINO",
        "config": ROOT / "configs/phase3_tao_full_matrix.yaml",
        "matrix": ROOT / "outputs/phase3_tao_full/tao_alpha_seed_m_matrix.csv",
        "output_dir": ROOT / "outputs/phase3_tao_full",
    },
    {
        "dataset": "OVT-B",
        "generator": "OWLv2",
        "config": ROOT / "configs/phase3_ovtb_owlv2_matrix.yaml",
        "matrix": ROOT / "outputs/phase3_ovtb_owlv2/ovtb_alpha_seed_m_matrix.csv",
        "output_dir": ROOT / "outputs/phase3_ovtb_owlv2",
    },
    {
        "dataset": "TAO",
        "generator": "OWLv2",
        "config": ROOT / "configs/phase3_tao_owlv2_matrix.yaml",
        "matrix": ROOT / "outputs/phase3_tao_owlv2/tao_alpha_seed_m_matrix.csv",
        "output_dir": ROOT / "outputs/phase3_tao_owlv2",
    },
    {
        "dataset": "OVT-B",
        "generator": "OWL-ViT v1",
        "config": ROOT / "configs/phase4_ovtb_owlvit_v1_matrix.yaml",
        "matrix": ROOT / "outputs/phase4_ovtb_owlvit_v1/ovtb_alpha_seed_m_matrix.csv",
        "output_dir": ROOT / "outputs/phase4_ovtb_owlvit_v1",
    },
    {
        "dataset": "TAO",
        "generator": "OWL-ViT v1",
        "config": ROOT / "configs/phase4_tao_owlvit_v1_matrix.yaml",
        "matrix": ROOT / "outputs/phase4_tao_owlvit_v1/tao_alpha_seed_m_matrix.csv",
        "output_dir": ROOT / "outputs/phase4_tao_owlvit_v1",
    },
]


def safe_name(value: float) -> str:
    return str(value).replace(".", "p")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def method_evalues(entry: dict, alpha: float, seed: int) -> pd.DataFrame:
    path = Path(entry["output_dir"]) / f"candidate_evalues_alpha{safe_name(alpha)}_seed{seed}.csv"
    if not path.exists() and alpha not in (0.05, 0.10, 0.20):
        path = Path(entry["output_dir"]) / f"candidate_evalues_alpha0p1_seed{seed}.csv"
    frame = read_csv(path)
    if frame.empty:
        return frame
    return frame[frame["method"].astype(str) == PARC_METHOD].copy()


def test_pool(cfg: dict, universe: pd.DataFrame, seed: int, budget: int) -> pd.DataFrame:
    run_cfg = json.loads(json.dumps(cfg))
    run_cfg.setdefault("splits", {})["seed"] = int(seed)
    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), run_cfg)
    frame = universe.copy()
    frame["split"] = frame["video_id"].astype(int).map(split_map)
    return frame[frame["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).head(budget)


def actual_released(matrix: pd.DataFrame, alpha: float, seed: int) -> int:
    if matrix.empty:
        return 0
    row = matrix[
        (pd.to_numeric(matrix["alpha1"], errors="coerce") == alpha)
        & (pd.to_numeric(matrix["seed"], errors="coerce") == seed)
        & (pd.to_numeric(matrix["candidate_budget_M"], errors="coerce") == BUDGET)
        & (matrix["method"].astype(str) == PARC_METHOD)
    ]
    return int(pd.to_numeric(row["released"], errors="coerce").fillna(0).iloc[0]) if not row.empty else 0


def main() -> None:
    out_dir = ensure_data_output(ROOT / "outputs/phase4_prop5_three_generator")
    seed_rows = []
    summary_rows = []
    for entry in ENTRIES:
        cfg = load_yaml(entry["config"])
        matrix = read_csv(entry["matrix"])
        universe = _load_universe_with_labels(cfg)
        for alpha in ALPHAS:
            ratios = []
            margins = []
            predicted_nonempty = 0
            actual_nonempty = 0
            correct = 0
            evaluated = 0
            for seed in SEEDS:
                evalues = method_evalues(entry, alpha, seed)
                if evalues.empty:
                    continue
                pool = test_pool(cfg, universe, seed, BUDGET)
                values = (
                    pool[["path_id", "candidate_rank", "score"]]
                    .merge(evalues[["path_id", "e_value"]], on="path_id", how="left")["e_value"]
                    .fillna(0.0)
                    .astype(float)
                    .tolist()
                )
                mass = _best_mass_summary(values, alpha1=alpha, candidate_budget_m=BUDGET)
                predicted = bool(float(mass["best_mass_ratio"]) >= 1.0)
                released = actual_released(matrix, alpha, seed)
                actual = released > 0
                ratios.append(float(mass["best_mass_ratio"]))
                margins.append(float(mass["best_margin"]))
                predicted_nonempty += int(predicted)
                actual_nonempty += int(actual)
                correct += int(predicted == actual)
                evaluated += 1
                seed_rows.append(
                    {
                        "dataset": entry["dataset"],
                        "generator": entry["generator"],
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": BUDGET,
                        "best_mass_ratio": mass["best_mass_ratio"],
                        "best_margin": mass["best_margin"],
                        "best_k": mass["best_k"],
                        "best_tau": mass["best_tau"],
                        "predicted_nonempty": predicted,
                        "actual_released": released,
                        "actual_nonempty": actual,
                        "prediction_correct": predicted == actual,
                    }
                )
            summary_rows.append(
                {
                    "dataset": entry["dataset"],
                    "generator": entry["generator"],
                    "alpha1": alpha,
                    "candidate_budget_M": BUDGET,
                    "evaluated_seeds": evaluated,
                    "predicted_nonempty_seeds": predicted_nonempty,
                    "actual_nonempty_seeds": actual_nonempty,
                    "correct_seed_predictions": correct,
                    "seed_prediction_accuracy": correct / evaluated if evaluated else None,
                    "mean_best_mass_ratio": float(np.mean(ratios)) if ratios else None,
                    "min_best_mass_ratio": float(np.min(ratios)) if ratios else None,
                    "max_best_mass_ratio": float(np.max(ratios)) if ratios else None,
                    "mean_best_margin": float(np.mean(margins)) if margins else None,
                    "all_seed_predictions_correct": bool(correct == evaluated) if evaluated else False,
                }
            )
    seed_csv = ensure_data_output(out_dir / "prop5_three_generator_by_seed.csv")
    table_csv = ensure_data_output(out_dir / "table_prop5_three_generator.csv")
    pd.DataFrame(seed_rows).to_csv(seed_csv, index=False)
    pd.DataFrame(summary_rows).to_csv(table_csv, index=False)
    summary = {
        "status": "completed",
        "table": str(table_csv),
        "seed_table": str(seed_csv),
        "rows": len(summary_rows),
        "seed_rows": len(seed_rows),
        "overall_seed_accuracy": float(pd.DataFrame(seed_rows)["prediction_correct"].mean()) if seed_rows else None,
    }
    write_json(out_dir / "prop5_three_generator_summary.json", summary)

    milestone = ROOT / "outputs/milestones/phase4_prop5_three_generator_v1"
    milestone.mkdir(parents=True, exist_ok=True)
    manifest = {"created_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "status": "completed", "files": []}
    for src in [seed_csv, table_csv, out_dir / "prop5_three_generator_summary.json", Path(__file__)]:
        dst = milestone / src.name
        shutil.copy2(src, dst)
        manifest["files"].append(
            {
                "source": str(src),
                "path": str(dst),
                "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                "bytes": dst.stat().st_size,
            }
        )
    readme = milestone / "README.md"
    readme.write_text(
        "# Proposition 5 three-generator validation v1\n\n"
        "Validates the high-evidence mass diagnostic on GroundingDINO, OWLv2, and OWL-ViT v1 across OVT-B/TAO and alpha={0.10,0.20} at fixed M=150.\n",
        encoding="utf-8",
    )
    manifest["files"].append(
        {
            "source": "generated",
            "path": str(readme),
            "sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
            "bytes": readme.stat().st_size,
        }
    )
    (milestone / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "milestone": str(milestone)}, indent=2))
    print(pd.DataFrame(summary_rows).to_string(index=False))


if __name__ == "__main__":
    main()
