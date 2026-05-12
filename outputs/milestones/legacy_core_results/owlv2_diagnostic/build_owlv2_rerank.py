#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def _as_float(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default).astype(float)


def build_rerank(input_csv: Path, output_csv: Path, scores_out: Path | None = None) -> None:
    df = pd.read_csv(input_csv)
    if df.empty:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)
        if scores_out:
            scores_out.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(scores_out, index=False)
        return

    original_score = _as_float(df.get("score", pd.Series(0.0, index=df.index)))
    objectness = _as_float(df.get("objectness", original_score))
    semantic = _as_float(df.get("semantic_margin", original_score))
    association = _as_float(df.get("association_score", pd.Series(0.0, index=df.index)))
    path_length = _as_float(df.get("path_length", pd.Series(1.0, index=df.index)), default=1.0)
    temporal = _as_float(df.get("temporal_stability", path_length), default=1.0)

    length_norm = np.clip(path_length / 8.0, 0.0, 1.0)
    temporal_norm = np.clip(temporal / 8.0, 0.0, 1.0)
    short_penalty = np.where(path_length < 2, 0.72, np.where(path_length < 3, 0.88, 1.0))

    rerank_score = (
        0.42 * objectness
        + 0.18 * semantic
        + 0.20 * association
        + 0.14 * length_norm
        + 0.06 * temporal_norm
    ) * short_penalty

    out = df.copy()
    out["score_original_owlv2"] = original_score
    out["score_rerank_v1"] = rerank_score
    out["score"] = rerank_score
    out["score_source"] = "owlv2_rerank_v1"
    out = out.sort_values(["score", "score_original_owlv2", "path_length"], ascending=[False, False, False]).reset_index(drop=True)
    out["candidate_rank"] = np.arange(1, len(out) + 1)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)

    if scores_out:
        score_cols = [
            "dataset",
            "video_id",
            "path_id",
            "score",
            "score_original_owlv2",
            "score_rerank_v1",
            "objectness",
            "semantic_margin",
            "temporal_stability",
            "association_score",
            "path_length",
            "candidate_rank",
            "score_source",
        ]
        existing = [col for col in score_cols if col in out.columns]
        scores_out.parent.mkdir(parents=True, exist_ok=True)
        out[existing].to_csv(scores_out, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build OWLv2 rerank-v1 candidate universe without using labels.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scores-out", default=None, type=Path)
    args = parser.parse_args()
    build_rerank(args.input, args.output, args.scores_out)


if __name__ == "__main__":
    main()
