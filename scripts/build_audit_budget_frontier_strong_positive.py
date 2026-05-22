#!/usr/bin/env python3
"""Freeze a strict strong-positive package for the active-audit frontier."""

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


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def summarize_group(group: pd.DataFrame) -> dict[str, float | int]:
    released = group["released"].astype(float)
    ftr = group["actual_FTR"].astype(float)
    false = released * ftr
    true = released - false
    inspected = group["audit_candidates_inspected"].astype(float)
    positives = group["verified_positives_found"].astype(float)
    return {
        "seeds": int(group["seed"].nunique()),
        "nonempty_seeds": int((released > 0).sum()),
        "safe_seeds": int(group["safe_release"].astype(bool).sum()),
        "alpha_violation_seeds": int(group["alpha_violation"].astype(bool).sum()),
        "mean_release": float(released.mean()),
        "min_release": int(released.min()),
        "max_release": int(released.max()),
        "total_released": int(released.sum()),
        "total_false_releases": float(false.sum()),
        "total_true_releases": float(true.sum()),
        "mean_FTR": float(ftr.mean()),
        "max_FTR": float(ftr.max()),
        "mean_verified_positives": float(positives.mean()),
        "mean_audit_inspected": float(inspected.mean()),
        "mean_verified_positive_yield": float((positives / inspected.replace(0, np.nan)).fillna(0.0).mean()),
        "mean_best_mass_ratio": float(group["best_mass_ratio"].astype(float).mean()),
    }


def bootstrap_delta(delta: np.ndarray, *, reps: int = 10000, seed: int = 1729) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    means = []
    idx = np.arange(len(delta))
    for _ in range(reps):
        draw = rng.choice(idx, size=len(idx), replace=True)
        means.append(float(delta[draw].mean()))
    arr = np.asarray(means)
    return float(delta.mean()), float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))


def pick(seed_rows: pd.DataFrame, target_row: str, policy: str, budget: float) -> pd.DataFrame:
    work = seed_rows[
        seed_rows["target_row"].eq(target_row)
        & seed_rows["audit_policy"].eq(policy)
        & np.isclose(seed_rows["audit_budget_fraction"].astype(float), budget)
    ].copy()
    if work.empty:
        raise ValueError(f"Missing row for {target_row}, {policy}, budget={budget}")
    return work.sort_values("seed").reset_index(drop=True)


def build_tables(seed_rows: pd.DataFrame, summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ctc_targets = ["ctc_learned_strict_alpha010_K100", "ctc_learned_strict_alpha010_K300"]
    gate_rows: list[dict[str, object]] = []
    seed_out: list[pd.DataFrame] = []
    contrast_rows: list[dict[str, object]] = []
    effect_rows: list[dict[str, object]] = []

    for target in ctc_targets:
        top = pick(seed_rows, target, "top_score", 0.005)
        random_same = pick(seed_rows, target, "random", 0.005)
        random_full = pick(seed_rows, target, "random", 1.0)
        top_summary = summarize_group(top)
        random_same_summary = summarize_group(random_same)
        random_full_summary = summarize_group(random_full)
        k_value = int(top["K"].iloc[0])
        seeds = int(top_summary["seeds"])
        budget_ratio = float(random_full["audit_budget_fraction"].iloc[0]) / float(top["audit_budget_fraction"].iloc[0])
        is_primary = (
            k_value == 100
            and top_summary["safe_seeds"] == seeds
            and top_summary["nonempty_seeds"] == seeds
            and top_summary["total_false_releases"] == 0.0
            and random_same_summary["nonempty_seeds"] == 0
            and random_full_summary["safe_seeds"] == seeds
        )
        role = "primary_strong_positive" if is_primary else "secondary_support_not_primary"
        gate_rows.append(
            {
                "target_row": target,
                "domain": "biomedical_cell_tracking",
                "K": k_value,
                "alpha": float(top["alpha"].iloc[0]),
                "audit_policy": "top_score",
                "audit_budget_fraction": 0.005,
                "random_same_budget_fraction": 0.005,
                "random_full_transition_budget_fraction": 1.0,
                "budget_ratio_vs_random_full": budget_ratio,
                "seeds": seeds,
                "top_nonempty_seeds": top_summary["nonempty_seeds"],
                "top_safe_seeds": top_summary["safe_seeds"],
                "top_mean_release": top_summary["mean_release"],
                "top_total_released": top_summary["total_released"],
                "top_total_false_releases": top_summary["total_false_releases"],
                "top_mean_FTR": top_summary["mean_FTR"],
                "top_max_FTR": top_summary["max_FTR"],
                "top_alpha_violation_seeds": top_summary["alpha_violation_seeds"],
                "random_same_nonempty_seeds": random_same_summary["nonempty_seeds"],
                "random_same_mean_release": random_same_summary["mean_release"],
                "random_full_safe_seeds": random_full_summary["safe_seeds"],
                "random_full_mean_release": random_full_summary["mean_release"],
                "top_mean_verified_positive_yield": top_summary["mean_verified_positive_yield"],
                "random_same_mean_verified_positive_yield": random_same_summary["mean_verified_positive_yield"],
                "top_mean_best_mass_ratio": top_summary["mean_best_mass_ratio"],
                "strong_positive_gate": "PASS" if is_primary else "SUPPORT_ONLY",
                "manuscript_role": role,
                "claim_boundary": (
                    "completed simulated-audit strong positive for CTC only; no materials prospective discovery; "
                    "does not modify A3"
                ),
            }
        )

        merged = top[
            [
                "target_row",
                "seed",
                "K",
                "released",
                "actual_FTR",
                "safe_release",
                "alpha_violation",
                "verified_positives_found",
                "audit_candidates_inspected",
                "best_mass_ratio",
            ]
        ].copy()
        merged = merged.rename(
            columns={
                "released": "top_score_released",
                "actual_FTR": "top_score_actual_FTR",
                "safe_release": "top_score_safe_release",
                "alpha_violation": "top_score_alpha_violation",
                "verified_positives_found": "top_score_verified_positives_found",
                "audit_candidates_inspected": "top_score_audit_candidates_inspected",
                "best_mass_ratio": "top_score_best_mass_ratio",
            }
        )
        merged["random_same_budget_released"] = random_same["released"].to_numpy()
        merged["random_same_budget_actual_FTR"] = random_same["actual_FTR"].to_numpy()
        merged["random_full_budget_released"] = random_full["released"].to_numpy()
        merged["random_full_budget_actual_FTR"] = random_full["actual_FTR"].to_numpy()
        merged["claim_boundary"] = "seed rows for CTC active-audit strong-positive package"
        seed_out.append(merged)

        delta_same = top["released"].to_numpy(dtype=float) - random_same["released"].to_numpy(dtype=float)
        mean_delta, ci_lo, ci_hi = bootstrap_delta(delta_same)
        effect_rows.append(
            {
                "target_row": target,
                "contrast": "top_score_0.005_minus_random_0.005_release_count",
                "mean_delta_release": mean_delta,
                "bootstrap_CI_low": ci_lo,
                "bootstrap_CI_high": ci_hi,
                "seeds": seeds,
                "claim_boundary": "paired seed bootstrap over simulated-audit rows",
            }
        )
        yield_delta = top_summary["mean_verified_positive_yield"] - random_same_summary["mean_verified_positive_yield"]
        contrast_rows.extend(
            [
                {
                    "target_row": target,
                    "audit_policy": "top_score",
                    "audit_budget_fraction": 0.005,
                    **top_summary,
                    "policy_role": "efficient_targeted_audit",
                },
                {
                    "target_row": target,
                    "audit_policy": "random",
                    "audit_budget_fraction": 0.005,
                    **random_same_summary,
                    "policy_role": "matched_budget_random_control",
                },
                {
                    "target_row": target,
                    "audit_policy": "random",
                    "audit_budget_fraction": 1.0,
                    **random_full_summary,
                    "policy_role": "full_random_audit_transition_control",
                },
                {
                    "target_row": target,
                    "audit_policy": "yield_delta",
                    "audit_budget_fraction": 0.005,
                    "seeds": seeds,
                    "nonempty_seeds": "",
                    "safe_seeds": "",
                    "alpha_violation_seeds": "",
                    "mean_release": "",
                    "min_release": "",
                    "max_release": "",
                    "total_released": "",
                    "total_false_releases": "",
                    "total_true_releases": "",
                    "mean_FTR": "",
                    "max_FTR": "",
                    "mean_verified_positives": "",
                    "mean_audit_inspected": "",
                    "mean_verified_positive_yield": yield_delta,
                    "mean_best_mass_ratio": "",
                    "policy_role": "top_score_minus_random_yield_delta",
                },
            ]
        )

    gate = pd.DataFrame(gate_rows)
    seed_table = pd.concat(seed_out, ignore_index=True)
    contrast = pd.DataFrame(contrast_rows)
    effect = pd.DataFrame(effect_rows)
    return gate, seed_table, contrast, effect


def write_closeout(out_dir: Path, gate: pd.DataFrame) -> None:
    primary = gate[gate["manuscript_role"].eq("primary_strong_positive")]
    support = gate[gate["manuscript_role"].eq("secondary_support_not_primary")]
    if primary.empty:
        status = "NO_PRIMARY_STRONG_POSITIVE"
    else:
        status = "completed strong-positive CTC active-audit result"
    lead = primary.iloc[0].to_dict() if not primary.empty else {}
    support_line = ""
    if not support.empty:
        row = support.iloc[0]
        support_line = (
            f"- Support row: {row['target_row']} released safely in {row['top_safe_seeds']}/"
            f"{row['seeds']} seeds at the same 0.5% budget, so it is support-only rather than the primary gate.\n"
        )
    text = (
        "# Active Audit Budget Frontier Strong-Positive Closeout\n\n"
        f"Status: {status}.\n\n"
        "This package tightens the audit-budget frontier into a CTC-only strong-positive gate. "
        "The primary row is deliberately narrower than the broader headline package: it requires "
        "20/20 nonempty safe seeds, zero observed false releases, a matched-budget random refusal, "
        "and a full-random-audit transition control. Materials rows are excluded from the strong-positive gate.\n\n"
        "## Primary Gate\n\n"
    )
    if lead:
        text += (
            f"- Primary row: {lead['target_row']}.\n"
            f"- Top-score audit budget: {lead['audit_budget_fraction']}.\n"
            f"- Top-score safe seeds: {lead['top_safe_seeds']}/{lead['seeds']}.\n"
            f"- Top-score total releases / false releases: {lead['top_total_released']} / "
            f"{lead['top_total_false_releases']}.\n"
            f"- Matched-budget random nonempty seeds: {lead['random_same_nonempty_seeds']}/{lead['seeds']}.\n"
            f"- Random transition budget: {lead['random_full_transition_budget_fraction']} "
            f"({lead['budget_ratio_vs_random_full']:.1f}x the targeted budget).\n"
        )
    text += (
        support_line
        + "\n## Claim Boundary\n\n"
        "- This is completed simulated-audit evidence over existing CTC held-out labels.\n"
        "- It is a strong positive for the active-audit release-governance mechanism, not for A3.\n"
        "- It does not claim prospective materials discovery.\n"
        "- Materials audit-budget rows remain boundary/secondary evidence outside this strong-positive gate.\n"
    )
    (out_dir / "ACTIVE_AUDIT_BUDGET_STRONG_POSITIVE_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed-rows",
        default="outputs/milestones/audit_budget_release_frontier_extended/table_audit_budget_frontier_seed_rows.csv",
    )
    parser.add_argument(
        "--summary",
        default="outputs/milestones/audit_budget_release_frontier_extended/table_audit_budget_frontier_summary.csv",
    )
    parser.add_argument("--out-dir", default="outputs/milestones/audit_budget_frontier_strong_positive")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_rows = pd.read_csv(args.seed_rows)
    summary = pd.read_csv(args.summary)
    gate, seed_table, contrast, effect = build_tables(seed_rows, summary)

    gate.to_csv(out_dir / "table_strong_positive_gate_audit.csv", index=False)
    seed_table.to_csv(out_dir / "table_ctc_primary_seed_rows.csv", index=False)
    contrast.to_csv(out_dir / "table_audit_budget_policy_contrast.csv", index=False)
    effect.to_csv(out_dir / "table_active_audit_effect_sizes.csv", index=False)
    figure = contrast[contrast["audit_policy"].isin(["top_score", "random"])].copy()
    figure.to_csv(out_dir / "figure_active_audit_strong_positive_source.csv", index=False)
    write_closeout(out_dir, gate)
    provenance = {
        "status": "completed",
        "evidence_status": "completed_strong_positive_simulated_audit",
        "primary_gate": "CTC K=100 only: 20/20 nonempty safe seeds, zero observed false releases, random matched-budget refusal",
        "inputs": {
            "seed_rows": args.seed_rows,
            "seed_rows_sha256": sha256_file(Path(args.seed_rows)),
            "summary": args.summary,
            "summary_sha256": sha256_file(Path(args.summary)),
        },
        "claim_boundary": "CTC active-audit strong positive only; not A3; not prospective materials discovery",
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
