#!/usr/bin/env python3
"""Create a score-control CTC universe for learned-source stress checks.

The control preserves candidate identities, labels, blocks, and node geometry,
but replaces the proposal ranking with random scores.  This makes the stress
test local to the upstream ranking signal: PARC should refuse or sharply reduce
release when the learned proposal source no longer carries evidence separation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", required=True)
    parser.add_argument("--candidate-nodes", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260515)
    parser.add_argument("--control-name", default="random_score_negative_control")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    universe_path = Path(args.candidate_universe)
    nodes_path = Path(args.candidate_nodes)
    universe = pd.read_csv(universe_path)
    nodes = pd.read_csv(nodes_path)

    rng = np.random.default_rng(args.seed)
    random_scores = rng.random(len(universe))
    control = universe.copy()
    control["score"] = random_scores
    control["association_score"] = random_scores
    control["objectness"] = pd.Series(random_scores).rank(pct=True).to_numpy()
    control["score_source"] = args.control_name
    control = control.sort_values(["score", "path_id"], ascending=[False, True]).reset_index(drop=True)
    control["candidate_rank"] = np.arange(1, len(control) + 1)

    nodes_control = nodes.copy()
    node_scores = control[["path_id", "video_id", "score"]].rename(columns={"score": "control_score", "video_id": "control_video_id"})
    nodes_control = nodes_control.drop(columns=[c for c in ["score"] if c in nodes_control.columns], errors="ignore")
    nodes_control = nodes_control.merge(node_scores, on="path_id", how="left")
    nodes_control["score"] = nodes_control["control_score"].astype(float)
    nodes_control["video_id"] = nodes_control["control_video_id"].astype(int)
    nodes_control = nodes_control.drop(columns=["control_score", "control_video_id"], errors="ignore")

    universe_out = out_dir / "candidate_universe.csv"
    nodes_out = out_dir / "candidate_nodes.csv"
    scores_out = out_dir / "candidate_scores.csv"
    control.to_csv(universe_out, index=False)
    nodes_control.to_csv(nodes_out, index=False)
    control[["path_id", "score", "objectness", "semantic_margin", "temporal_stability", "association_score", "score_source"]].to_csv(scores_out, index=False)

    report = {
        "status": "completed",
        "source": args.control_name,
        "control": "random_scores_preserving_candidate_identities_labels_and_blocks",
        "seed": args.seed,
        "candidate_universe_input_sha256": sha256_file(universe_path),
        "candidate_nodes_input_sha256": sha256_file(nodes_path),
        "rows": int(len(control)),
        "outputs": {
            "candidate_universe": str(universe_out),
            "candidate_nodes": str(nodes_out),
            "candidate_scores": str(scores_out),
        },
        "output_sha256": {
            "candidate_universe": sha256_file(universe_out),
            "candidate_nodes": sha256_file(nodes_out),
            "candidate_scores": sha256_file(scores_out),
        },
    }
    report_path = out_dir / "CTC_SCORE_CONTROL_UNIVERSE_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
