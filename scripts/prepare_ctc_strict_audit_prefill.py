#!/usr/bin/env python3
"""Prepare CTC strict-audit blind templates and reviewer prefill sheets.

This script builds an audit package for the learned-hybrid CTC flagship without
copying raw microscopy images.  It writes:

* a blind template with only image-pair and box coordinates;
* a prefill sheet with screening labels for human review;
* a private audit key that maps audit IDs back to path IDs;
* a protocol note and summary tables.

The prefill labels are not final human labels.  They are screening suggestions
that must be confirmed or edited by human reviewers before any paper-facing
``human_*`` fields are populated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEARNED_UNIVERSE_DIR = Path(
    os.environ.get("CTC_LEARNED_UNIVERSE_DIR", "outputs/ctc_learned_link_certification/universe_sequence02_eval_w1")
)
DEFAULT_UNIVERSE = DEFAULT_LEARNED_UNIVERSE_DIR / "candidate_universe.csv"
DEFAULT_NODES = DEFAULT_LEARNED_UNIVERSE_DIR / "candidate_nodes.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def parse_csv_list(value: str, cast):
    return [cast(part) for part in value.split(",") if part.strip()]


def gamma_star_from_p(p_value: float | None) -> float | None:
    if p_value is None or p_value <= 0.0 or p_value >= 1.0:
        return None
    gamma = -1.0 / math.log(p_value)
    return gamma if 0.0 < gamma < 1.0 else None


def emax_from_p(gamma: float | None, p_value: float | None) -> float | None:
    if gamma is None or p_value is None or p_value <= 0.0 or p_value > 1.0:
        return None
    return gamma * (p_value ** (gamma - 1.0))


def split_video_ids(video_ids: list[int], seed: int, tune_ratio: float, cal_ratio: float) -> dict[int, str]:
    ordered = sorted(set(int(video_id) for video_id in video_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    tune_end = int(round(len(ordered) * tune_ratio))
    cal_end = tune_end + int(round(len(ordered) * cal_ratio))
    mapping: dict[int, str] = {}
    for idx, video_id in enumerate(ordered):
        if idx < tune_end:
            mapping[video_id] = "tune"
        elif idx < cal_end:
            mapping[video_id] = "cal"
        else:
            mapping[video_id] = "test"
    return mapping


def observed_true_mask(full_true: pd.Series, scores: pd.Series, rho: float) -> np.ndarray:
    true_indices = np.flatnonzero(full_true.to_numpy(dtype=bool))
    observed = np.zeros(len(full_true), dtype=bool)
    if rho >= 1.0:
        observed[true_indices] = True
        return observed
    if rho <= 0.0 or len(true_indices) == 0:
        return observed
    n_observed = int(round(len(true_indices) * rho))
    score_values = scores.to_numpy(dtype=float)
    order = true_indices[np.argsort(score_values[true_indices])[::-1]]
    observed[order[:n_observed]] = True
    return observed


def compute_evalues(test: pd.DataFrame, cal: pd.DataFrame, cal_video_ids: list[int], alpha: float) -> np.ndarray:
    null_cal = cal[cal["_partial_null"].astype(bool)].copy()
    if null_cal.empty:
        maxima = np.asarray([], dtype=float)
    else:
        maxima = null_cal.groupby("video_id")["score"].max().astype(float).to_numpy()
    n_nonempty = int(len(maxima))
    if n_nonempty == 0 or len(test) == 0:
        return np.zeros(len(test), dtype=float)
    p_min_effective = min(1.0, 1.0 / (n_nonempty + 1.0))
    gamma = gamma_star_from_p(p_min_effective)
    required = 1.0 / alpha if alpha > 0 else None
    emax = emax_from_p(gamma, p_min_effective)
    if gamma is None or required is None or emax is None or emax < required:
        return np.zeros(len(test), dtype=float)
    maxima_sorted = np.sort(maxima)
    scores = test["score"].astype(float).to_numpy()
    exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
    p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
    p_any = np.minimum(1.0, p_block)
    return (gamma * (p_any ** (gamma - 1.0))).astype(float)


def scs_selected_indices(evalues: np.ndarray, alpha: float, budget: int) -> np.ndarray:
    if len(evalues) == 0:
        return np.asarray([], dtype=int)
    order = np.argsort(evalues.astype(float))[::-1]
    sorted_e = evalues[order]
    released = 0
    for k in range(1, len(sorted_e) + 1):
        tau = budget / (alpha * k)
        if sorted_e[k - 1] >= tau:
            released = k
    return order[:released]


def simulated_release_membership(
    universe: pd.DataFrame,
    seeds: list[int],
    budgets: list[int],
    alpha: float,
    rho: float,
    tune_ratio: float,
    cal_ratio: float,
) -> pd.DataFrame:
    rows: list[dict] = []
    base = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)
    observed = observed_true_mask(base["_full_true"], base["score"], rho=rho)
    for seed in seeds:
        split_map = split_video_ids(base["video_id"].astype(int).tolist(), seed=seed, tune_ratio=tune_ratio, cal_ratio=cal_ratio)
        work = base.copy()
        work["_observed_positive"] = observed
        work["_partial_null"] = ~work["_observed_positive"]
        work["_split"] = work["video_id"].map(split_map)
        cal = work[work["_split"] == "cal"].copy()
        test = work[work["_split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
        evalues = compute_evalues(test, cal, cal_video_ids=sorted(cal["video_id"].unique().tolist()), alpha=alpha)
        test = test.copy()
        test["_evalue"] = evalues
        for budget in budgets:
            pool = test.head(budget).copy()
            chosen = scs_selected_indices(pool["_evalue"].to_numpy(dtype=float), alpha=alpha, budget=budget)
            selected = pool.iloc[chosen].copy() if len(chosen) else pool.iloc[[]].copy()
            for path_id in selected["path_id"].astype(str):
                rows.append({"path_id": path_id, "seed": seed, "budget": budget, "alpha": alpha})
    if not rows:
        return pd.DataFrame(columns=["path_id", "simulated_release_hits", "simulated_release_budgets", "simulated_release_seeds"])
    raw = pd.DataFrame(rows)
    return (
        raw.groupby("path_id")
        .agg(
            simulated_release_hits=("seed", "size"),
            simulated_release_budgets=("budget", lambda x: ",".join(map(str, sorted(set(map(int, x)))))),
            simulated_release_seeds=("seed", lambda x: ",".join(map(str, sorted(set(map(int, x)))))),
        )
        .reset_index()
    )


def node_pair_table(nodes: pd.DataFrame) -> pd.DataFrame:
    cols = ["path_id", "node_index", "image_id", "frame_index", "image_path", "bbox_x", "bbox_y", "bbox_w", "bbox_h"]
    work = nodes[cols].copy()
    left = work[work["node_index"] == 0].drop(columns=["node_index"]).copy()
    right = work[work["node_index"] == 1].drop(columns=["node_index"]).copy()
    left = left.rename(columns={c: f"source_{c}" for c in left.columns if c != "path_id"})
    right = right.rename(columns={c: f"target_{c}" for c in right.columns if c != "path_id"})
    return left.merge(right, on="path_id", how="inner")


def add_screening_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    src_purity = pd.to_numeric(out.get("source_gt_purity", 0.0), errors="coerce").fillna(0.0)
    tgt_purity = pd.to_numeric(out.get("target_gt_purity", 0.0), errors="coerce").fillna(0.0)
    same_gt = out.get("source_gt_label", "").astype(str).eq(out.get("target_gt_label", "").astype(str))
    is_false = out["_full_false"].astype(bool)
    uncertain = (src_purity < 0.75) | (tgt_purity < 0.75)

    labels = np.where(is_false, "not_same_cell_link", "same_cell_link")
    labels = np.where(uncertain, "uncertain", labels)
    out["screening_label"] = labels
    out["screening_verified_positive_for_calibration"] = np.where(out["screening_label"].eq("same_cell_link"), "yes", "no")
    out["screening_confidence"] = np.where(
        uncertain,
        "low",
        np.where((~is_false) & same_gt & (src_purity >= 0.95) & (tgt_purity >= 0.95), "high", "medium"),
    )
    reasons: list[str] = []
    for _, row in out.iterrows():
        if row["screening_label"] == "uncertain":
            reasons.append("low GT-instance purity or ambiguous crop; human reviewer should decide same/not-same/uncertain.")
        elif row["screening_label"] == "same_cell_link":
            reasons.append("source and target align to the same CTC lineage identity in held-out GT; use only as prefill, not final human label.")
        else:
            reasons.append("source and target do not align to the same CTC lineage identity in held-out GT; use only as prefill, not final human label.")
    out["screening_reason"] = reasons
    out["review_status"] = "requires_human_confirmation"
    return out


def block_balanced_queue(df: pd.DataFrame, n: int, exclude: set[str], max_per_block: int, seed: int) -> pd.DataFrame:
    pool = df[~df["path_id"].astype(str).isin(exclude)].copy()
    pool = pool.sort_values(["score", "candidate_rank"], ascending=[False, True])
    grouped = {int(k): g.copy() for k, g in pool.groupby("video_id", sort=False)}
    block_order = sorted(grouped, key=lambda k: float(grouped[k]["score"].max()), reverse=True)
    selected: list[pd.DataFrame] = []
    selected_ids: set[str] = set()
    for _ in range(max_per_block):
        for block in block_order:
            group = grouped[block]
            available = group[~group["path_id"].astype(str).isin(selected_ids)]
            if available.empty:
                continue
            row = available.iloc[[0]]
            selected.append(row)
            selected_ids.add(str(row.iloc[0]["path_id"]))
            if len(selected) >= n:
                return pd.concat(selected, ignore_index=True)
    if len(selected) < n:
        remaining = pool[~pool["path_id"].astype(str).isin(selected_ids)].copy()
        if not remaining.empty:
            selected.append(remaining.head(n - len(selected)))
    if not selected:
        return pool.iloc[[]].copy()
    return pd.concat(selected, ignore_index=True).head(n)


def make_audit_rows(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    universe_path = Path(args.candidate_universe)
    nodes_path = Path(args.candidate_nodes)
    universe = pd.read_csv(universe_path, low_memory=False)
    nodes = pd.read_csv(nodes_path, low_memory=False)
    universe["video_id"] = universe["video_id"].astype(int)
    universe["_full_false"] = bool_series(universe["is_unmatched"])
    universe["_full_true"] = ~universe["_full_false"]
    universe = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)
    release = simulated_release_membership(
        universe,
        seeds=parse_csv_list(args.seeds, int),
        budgets=parse_csv_list(args.release_budgets, int),
        alpha=args.alpha,
        rho=args.rho,
        tune_ratio=args.tune_ratio,
        cal_ratio=args.cal_ratio,
    )
    release_ids = set(release["path_id"].astype(str))
    raw_top = universe.head(args.raw_top_n).copy()
    raw_ids = set(raw_top["path_id"].astype(str))
    calibration = block_balanced_queue(
        universe,
        n=args.calibration_n,
        exclude=release_ids | raw_ids,
        max_per_block=args.max_per_block,
        seed=args.seed,
    )
    audit_membership = []
    for path_id in sorted(release_ids):
        audit_membership.append({"path_id": path_id, "queue_simulated_strict_release": True})
    release_df = pd.DataFrame(audit_membership)
    raw_df = pd.DataFrame({"path_id": list(raw_ids), "queue_raw_topK_reference": True})
    cal_df = pd.DataFrame({"path_id": calibration["path_id"].astype(str), "queue_calibration": True})
    membership = release_df.merge(raw_df, on="path_id", how="outer").merge(cal_df, on="path_id", how="outer")
    for col in ["queue_simulated_strict_release", "queue_raw_topK_reference", "queue_calibration"]:
        membership[col] = membership[col].where(membership[col].notna(), False).astype(bool)
    membership["queue_membership"] = membership.apply(
        lambda r: ",".join(
            name
            for name, col in [
                ("simulated_strict_release", "queue_simulated_strict_release"),
                ("raw_topK_reference", "queue_raw_topK_reference"),
                ("calibration", "queue_calibration"),
            ]
            if bool(r[col])
        ),
        axis=1,
    )
    rows = universe.merge(membership, on="path_id", how="inner")
    rows = rows.merge(release, on="path_id", how="left")
    rows["simulated_release_hits"] = rows["simulated_release_hits"].fillna(0).astype(int)
    rows["simulated_release_budgets"] = rows["simulated_release_budgets"].fillna("")
    rows["simulated_release_seeds"] = rows["simulated_release_seeds"].fillna("")
    rows = rows.merge(node_pair_table(nodes), on="path_id", how="left")
    rows = add_screening_labels(rows)
    rows = rows.sort_values(
        ["queue_simulated_strict_release", "queue_raw_topK_reference", "queue_calibration", "candidate_rank"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    rows.insert(0, "audit_id", [f"CTC-AUDIT-{idx:05d}" for idx in range(1, len(rows) + 1)])
    report = {
        "candidate_universe_sha256": sha256_file(universe_path),
        "candidate_nodes_sha256": sha256_file(nodes_path),
        "rows_total": int(len(rows)),
        "rows_calibration": int(rows["queue_calibration"].sum()),
        "rows_simulated_release": int(rows["queue_simulated_strict_release"].sum()),
        "rows_raw_topK_reference": int(rows["queue_raw_topK_reference"].sum()),
        "screening_label_counts": rows["screening_label"].value_counts().to_dict(),
        "note": "Screening labels are prefill suggestions only; final paper-facing human labels require independent human confirmation.",
    }
    return rows, report


def write_protocol(out_dir: Path, report: dict, args: argparse.Namespace) -> None:
    text = f"""# CTC Strict Human Audit Prefill Protocol

## Status

This package prepares a CTC learned-hybrid strict-audit review queue.  It is a
prefill package, not a completed human audit.  Paper-facing `human_*` fields
must remain empty until a reviewer confirms or edits the labels.

## Review Task

For each row, inspect the source crop at frame `t` and target crop at frame
`t+1` and label the candidate link as:

- `same_cell_link`: the source and target boxes correspond to the same cell
  identity across adjacent frames.
- `not_same_cell_link`: the target box corresponds to a different cell,
  background/artifact, or an impossible continuation.
- `uncertain`: the pair is too ambiguous because of overlap, mitosis,
  low contrast, crop truncation, or insufficient visual evidence.

Only confirmed `same_cell_link` rows may be used as one-sided verified
positives.  `not_same_cell_link`, `uncertain`, and disagreements remain
unverified and must never be used as trusted negatives.

## Files

- `ctc_strict_audit_blind_template.csv`: blinded review sheet. It omits path
  IDs, scores, release/calibration strata, and GT-derived screening labels.
- `ctc_strict_audit_prefill_for_human_review.csv`: review sheet with screening
  suggestions and traceability fields for rapid confirmation.
- `ctc_strict_audit_private_key.csv`: audit ID to path ID mapping and queue
  membership. Keep separate from a strict blind reviewer.
- `table_ctc_strict_audit_prefill_summary.csv`: package counts.

## Expert Requirement

Expert microscopy review is strongly recommended for a NMI flagship claim, but
it is not logically mandatory for every row.  A trained independent reviewer can
review ordinary same-cell continuation cases if the protocol uses conservative
rules and held-out official CTC ground truth remains available only for final
evaluation.  However, expert or microscopy-experienced adjudication should be
used for mitosis, dense overlaps, low-contrast cells, segmentation ambiguity,
and any row marked `uncertain` or disputed by reviewers.

If expert review is not completed, phrase the result as `trained independent
human review`, not `expert audit`.

## Package Counts

- total rows: {report['rows_total']}
- calibration queue rows: {report['rows_calibration']}
- simulated strict-release queue rows: {report['rows_simulated_release']}
- raw top-K reference rows: {report['rows_raw_topK_reference']}
- screening label counts: `{json.dumps(report['screening_label_counts'], sort_keys=True)}`

## Predeclared Simulation Context

- learned-hybrid source: sequence-disjoint CTC appearance/geometry scorer
- release simulation used only to define candidate queues
- alpha: {args.alpha}
- rho: {args.rho}
- release budgets: {args.release_budgets}
- seeds: {args.seeds}

The real-audit release trial must rerun PARC using confirmed human positives;
release-audit labels must not be fed back into calibration.
"""
    (out_dir / "CTC_STRICT_HUMAN_AUDIT_PREFILL_PROTOCOL.md").write_text(text, encoding="utf-8")


def write_outputs(rows: pd.DataFrame, report: dict, args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    blind_cols = [
        "audit_id",
        "ctc_dataset",
        "sequence_id",
        "frame_start",
        "frame_end",
        "source_image_path",
        "source_frame_index",
        "source_bbox_x",
        "source_bbox_y",
        "source_bbox_w",
        "source_bbox_h",
        "target_image_path",
        "target_frame_index",
        "target_bbox_x",
        "target_bbox_y",
        "target_bbox_w",
        "target_bbox_h",
    ]
    blind = rows[blind_cols].copy()
    for col in ["human_label", "human_verified_positive_for_calibration", "human_reason", "human_confidence", "human_review_status"]:
        blind[col] = ""
    blind.to_csv(out_dir / "ctc_strict_audit_blind_template.csv", index=False)

    prefill_cols = [
        "audit_id",
        "path_id",
        "queue_membership",
        "ctc_dataset",
        "sequence_id",
        "frame_start",
        "frame_end",
        "video_id",
        "candidate_rank",
        "score",
        "source_image_path",
        "source_frame_index",
        "source_bbox_x",
        "source_bbox_y",
        "source_bbox_w",
        "source_bbox_h",
        "target_image_path",
        "target_frame_index",
        "target_bbox_x",
        "target_bbox_y",
        "target_bbox_w",
        "target_bbox_h",
        "screening_label",
        "screening_verified_positive_for_calibration",
        "screening_confidence",
        "screening_reason",
        "review_status",
    ]
    prefill = rows[prefill_cols].copy()
    for col in ["human_label", "human_verified_positive_for_calibration", "human_reason", "human_confidence", "human_review_status"]:
        prefill[col] = ""
    prefill.to_csv(out_dir / "ctc_strict_audit_prefill_for_human_review.csv", index=False)

    key_cols = [
        "audit_id",
        "path_id",
        "queue_membership",
        "queue_calibration",
        "queue_simulated_strict_release",
        "queue_raw_topK_reference",
        "simulated_release_hits",
        "simulated_release_budgets",
        "simulated_release_seeds",
        "ctc_dataset",
        "sequence_id",
        "video_id",
        "frame_pair",
        "candidate_rank",
        "score",
        "screening_label",
        "screening_verified_positive_for_calibration",
        "screening_confidence",
        "source_gt_purity",
        "target_gt_purity",
    ]
    rows[key_cols].to_csv(out_dir / "ctc_strict_audit_private_key.csv", index=False)

    summary_rows = []
    for queue_col, queue_name in [
        ("queue_calibration", "calibration"),
        ("queue_simulated_strict_release", "simulated_strict_release"),
        ("queue_raw_topK_reference", "raw_topK_reference"),
    ]:
        subset = rows[rows[queue_col]].copy()
        for label, group in subset.groupby("screening_label", dropna=False):
            summary_rows.append(
                {
                    "queue": queue_name,
                    "screening_label": label,
                    "rows": int(len(group)),
                    "verified_positive_prefill_yes": int((group["screening_verified_positive_for_calibration"] == "yes").sum()),
                    "datasets": ",".join(sorted(group["ctc_dataset"].dropna().astype(str).unique())),
                }
            )
    pd.DataFrame(summary_rows).to_csv(out_dir / "table_ctc_strict_audit_prefill_summary.csv", index=False)

    report = dict(report)
    report["outputs"] = {
        "blind_template": "ctc_strict_audit_blind_template.csv",
        "prefill_for_human_review": "ctc_strict_audit_prefill_for_human_review.csv",
        "private_key": "ctc_strict_audit_private_key.csv",
        "summary": "table_ctc_strict_audit_prefill_summary.csv",
    }
    (out_dir / "CTC_STRICT_HUMAN_AUDIT_PREFILL_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_protocol(out_dir, report, args)

    manifest_paths = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name != "MANIFEST_SHA256.txt")
    with (out_dir / "MANIFEST_SHA256.txt").open("w", encoding="utf-8") as handle:
        for path in manifest_paths:
            rel = path.relative_to(out_dir)
            handle.write(f"{sha256_file(path)}  {rel}\n")

    package_path = ROOT / "outputs/packages/ctc_strict_human_audit_prefill.tar.gz"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(package_path, "w:gz") as tar:
        for path in sorted(out_dir.rglob("*")):
            tar.add(path, arcname=str(Path("ctc_strict_human_audit_prefill") / path.relative_to(out_dir)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", default=str(DEFAULT_UNIVERSE))
    parser.add_argument("--candidate-nodes", default=str(DEFAULT_NODES))
    parser.add_argument("--out-dir", default="outputs/milestones/ctc_strict_human_audit_prefill")
    parser.add_argument("--calibration-n", type=int, default=1500)
    parser.add_argument("--raw-top-n", type=int, default=300)
    parser.add_argument("--max-per-block", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260516)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--release-budgets", default="100,300")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    parser.add_argument("--tune-ratio", type=float, default=1 / 6)
    parser.add_argument("--cal-ratio", type=float, default=1 / 2)
    args = parser.parse_args()
    rows, report = make_audit_rows(args)
    write_outputs(rows, report, args)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
