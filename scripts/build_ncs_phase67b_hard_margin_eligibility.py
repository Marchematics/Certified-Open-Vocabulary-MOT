#!/usr/bin/env python3
"""Build Phase67b hard-margin eligibility diagnostic.

Phase67 ranked by t0 hull margin and certified the margin-stability event.
Phase67b adds the stricter operational variant: a candidate can enter the
release pool only if its frozen t0 margin satisfies margin >= m.  This directly
tests whether a deterministic t0 margin buffer can recover a current-MP
surviving release frontier.

This is a versioned release-card design diagnostic.  It uses t0 hull margins as
eligibility metadata, so it is not prospective discovery, not DFT evidence and
not a hidden-label ranking benchmark.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from build_ncs_phase67_margin_stable_certification import (
    ALPHA,
    K_GRID,
    MARGIN_GRID,
    N_BOOTSTRAP,
    PHASE51,
    ROOT,
    SEEDS,
    SUPPORT_MODES,
    add_margin_labels,
    compute_evalues,
    load_queue,
    rel,
    scs_release_count,
    sha256_file,
    split_blocks,
    write_root_manifest,
)


PHASE67B = ROOT / "outputs/milestones/ncs_phase67b_hard_margin_eligibility"
SCOPE = (
    "completed_hard_margin_eligibility_diagnostic;"
    "hard_release_eligibility_t0_margin_ge_m;"
    "validity_event_t0_ehull_le_minus_m;"
    "score_is_t0_margin_not_raw_model_score;"
    "queue_limited_K500_WBM_union;"
    "t1_used_only_for_post_release_survival_audit;"
    "not_prospective_discovery;"
    "not_DFT_evidence;"
    "not_independent_validation;"
    "t0_margin_used_as_eligibility_metadata"
)


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def summarize_release(selected: pd.DataFrame) -> dict[str, object]:
    n = int(len(selected))
    if n == 0:
        return {
            "release_size": 0,
            "t0_margin_false_count": 0,
            "t1_false_count": 0,
            "FTR_t0_margin_event": math.nan,
            "FTR_t1_stability": math.nan,
            "FTR_t1_empty_zero": 0.0,
            "robust_to_unstable_count": 0,
            "robust_to_unstable_rate": 0.0,
            "mean_t0_margin": math.nan,
            "median_t0_margin": math.nan,
            "minimum_t0_margin": math.nan,
        }
    t0_margin_stable = selected["t0_margin_stable"].astype(bool)
    t1_stable = selected["t1_stable"].astype(bool)
    robust_to_unstable = t0_margin_stable & ~t1_stable
    return {
        "release_size": n,
        "t0_margin_false_count": int((~t0_margin_stable).sum()),
        "t1_false_count": int((~t1_stable).sum()),
        "FTR_t0_margin_event": float((~t0_margin_stable).mean()),
        "FTR_t1_stability": float((~t1_stable).mean()),
        "FTR_t1_empty_zero": float((~t1_stable).mean()),
        "robust_to_unstable_count": int(robust_to_unstable.sum()),
        "robust_to_unstable_rate": float(robust_to_unstable.mean()),
        "mean_t0_margin": float(selected["t0_margin"].mean()),
        "median_t0_margin": float(selected["t0_margin"].median()),
        "minimum_t0_margin": float(selected["t0_margin"].min()),
    }


def run_seed(
    base_frame: pd.DataFrame,
    *,
    margin_m: float,
    k: int,
    seed: int,
    support_mode: str,
    rho: float,
) -> tuple[dict[str, object], pd.DataFrame]:
    frame = add_margin_labels(base_frame, margin_m)
    cal_blocks, followup_blocks = split_blocks(frame["block_id"].astype(str).tolist(), seed)
    block_series = frame["block_id"].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    observed = np.zeros(len(frame), dtype=bool)
    eligible_cal = np.flatnonzero(cal_mask & frame["t0_margin_stable"].to_numpy(dtype=bool))
    if len(eligible_cal) and rho > 0:
        n_observed = max(1, int(round(len(eligible_cal) * min(rho, 1.0))))
        scores = frame["margin_score"].to_numpy(dtype=float)
        chosen = eligible_cal[np.argsort(scores[eligible_cal])[::-1]][:n_observed]
        observed[chosen] = True

    followup, diag = compute_evalues(frame, cal_blocks=cal_blocks, followup_blocks=followup_blocks, observed_positive=observed)
    eligible_followup = followup[followup["t0_margin_stable"].astype(bool)].copy()
    pool = eligible_followup.head(k).copy()
    released, tau, scs_margin, evidence_mass = scs_release_count(pool["_margin_evalue"].to_numpy(dtype=float), alpha=ALPHA, budget=k)
    if released:
        selected = pool.iloc[np.argsort(pool["_margin_evalue"].to_numpy(dtype=float))[::-1][:released]].copy()
    else:
        selected = pool.iloc[[]].copy()
    summary = summarize_release(selected)

    if released and summary["FTR_t1_stability"] <= ALPHA:
        decision = "hard_margin_t1_survival_positive"
    elif released:
        decision = "hard_margin_release_fails_t1_survival_gate"
    else:
        decision = "hard_margin_certified_refusal"

    row = {
        "margin_m_eV_atom": margin_m,
        "K": k,
        "alpha": ALPHA,
        "seed": seed,
        "support_mode": support_mode,
        "rho_margin_positive_support": rho,
        "decision": decision,
        "observed_margin_positives": int(observed.sum()),
        "margin_positive_eligible_in_calibration": int(len(eligible_cal)),
        "eligible_followup_size": int(len(eligible_followup)),
        "pool_size": int(len(pool)),
        "pool_t1_FTR": float((~pool["t1_stable"].astype(bool)).mean()) if len(pool) else math.nan,
        "pool_robust_to_unstable_rate": float((pool["t0_margin_stable"].astype(bool) & ~pool["t1_stable"].astype(bool)).mean())
        if len(pool)
        else math.nan,
        "release_threshold_tau": tau,
        "self_consistency_margin": scs_margin,
        "evidence_mass_phi": evidence_mass,
        "max_evalue": float(pool["_margin_evalue"].max()) if len(pool) else 0.0,
        "required_evalue_threshold": tau,
        "candidate_universe": "frozen_K500_WBM_queue_union",
        "ranking_score": "t0_margin_descending",
        "validity_event": "t0_e_above_hull_le_minus_m",
        "selection_rule": "hard_t0_margin_eligibility_then_SCS_evalue_self_consistency",
        "evidence_scope": SCOPE,
        **diag,
        **summary,
    }
    candidate = pool.copy()
    candidate["seed"] = seed
    candidate["support_mode"] = support_mode
    candidate["rho_margin_positive_support"] = rho
    candidate["selected_by_phase67b_hard_margin_eligibility"] = candidate["candidate_id"].isin(set(selected["candidate_id"].astype(str)))
    candidate["selection_rule"] = "hard_t0_margin_eligibility_then_SCS_evalue_self_consistency"
    candidate["evidence_scope"] = SCOPE
    return row, candidate


def summarize_frontier(seed_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frontier_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    for (margin_m, k, support_mode), group in seed_df.groupby(["margin_m_eV_atom", "K", "support_mode"], sort=True):
        nonempty = int((group["release_size"].astype(int) > 0).sum())
        t1_safe = int(((group["release_size"].astype(int) > 0) & (group["FTR_t1_stability"].astype(float) <= ALPHA)).sum())
        nonempty_group = group[group["release_size"].astype(int) > 0]
        mean_t1_ftr = float(nonempty_group["FTR_t1_stability"].astype(float).mean()) if len(nonempty_group) else math.nan
        primary_success = bool(nonempty >= 18 and t1_safe >= 18 and math.isfinite(mean_t1_ftr) and mean_t1_ftr <= ALPHA)
        if primary_success:
            claim_status = "completed_hard_margin_constructive_t1_survival_positive"
        elif nonempty > 0:
            claim_status = "completed_hard_margin_boundary_diagnostic_not_headline"
        else:
            claim_status = "completed_hard_margin_refusal_boundary"
        row = {
            "margin_m_eV_atom": float(margin_m),
            "K": int(k),
            "alpha": ALPHA,
            "support_mode": support_mode,
            "rho_margin_positive_support": float(group["rho_margin_positive_support"].iloc[0]),
            "n_seeds": int(group["seed"].nunique()),
            "nonempty_seeds": nonempty,
            "t1_survival_safe_seeds": t1_safe,
            "mean_release_size": float(group["release_size"].astype(float).mean()),
            "median_release_size": float(group["release_size"].astype(float).median()),
            "max_release_size": int(group["release_size"].astype(int).max()),
            "mean_FTR_t0_margin_event_if_nonempty": 0.0 if nonempty else math.nan,
            "mean_FTR_t1_stability_if_nonempty": mean_t1_ftr,
            "mean_FTR_t1_empty_zero": float(group["FTR_t1_empty_zero"].astype(float).mean()),
            "mean_pool_t1_FTR": float(group["pool_t1_FTR"].astype(float).mean(skipna=True)) if group["pool_t1_FTR"].notna().any() else math.nan,
            "robust_to_unstable_rate": float(group["robust_to_unstable_rate"].astype(float).mean(skipna=True))
            if group["robust_to_unstable_rate"].notna().any()
            else math.nan,
            "mean_t0_margin": float(group["mean_t0_margin"].astype(float).mean(skipna=True)) if group["mean_t0_margin"].notna().any() else math.nan,
            "minimum_t0_margin": float(group["minimum_t0_margin"].astype(float).min(skipna=True)) if group["minimum_t0_margin"].notna().any() else math.nan,
            "evidence_mass_phi": float(group["evidence_mass_phi"].astype(float).mean()),
            "max_evalue": float(group["max_evalue"].astype(float).mean()),
            "required_evalue_threshold": float(group["required_evalue_threshold"].astype(float).mean()),
            "decision": "release" if nonempty else "refusal",
            "primary_success": primary_success,
            "claim_status": claim_status,
            "ranking_score": "t0_margin_descending",
            "validity_event": "t0_e_above_hull_le_minus_m",
            "selection_rule": "hard_t0_margin_eligibility_then_SCS_evalue_self_consistency",
            "evidence_scope": SCOPE,
        }
        frontier_rows.append(row)
        for gate, value, threshold, status in [
            ("nonempty_release_ge_18_seeds", nonempty, 18, "PASS" if nonempty >= 18 else "FAIL"),
            ("t1_survival_safe_ge_18_seeds", t1_safe, 18, "PASS" if t1_safe >= 18 else "FAIL"),
            (
                "mean_FTR_t1_stability_if_nonempty_le_alpha",
                mean_t1_ftr if math.isfinite(mean_t1_ftr) else math.nan,
                ALPHA,
                "PASS" if math.isfinite(mean_t1_ftr) and mean_t1_ftr <= ALPHA else "FAIL",
            ),
            ("constructive_hard_margin_t1_survival_positive", 1 if primary_success else 0, 1, "PASS" if primary_success else "FAIL"),
            ("hard_margin_eligibility_enforced", 1, 1, "PASS"),
        ]:
            gate_rows.append(
                {
                    "margin_m_eV_atom": float(margin_m),
                    "K": int(k),
                    "support_mode": support_mode,
                    "gate": gate,
                    "value": value,
                    "threshold": threshold,
                    "status": status,
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(frontier_rows), pd.DataFrame(gate_rows)


def bootstrap_seed_metrics(seed_df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(20260529)
    rows: list[dict[str, object]] = []
    metrics = {
        "mean_release_size": "release_size",
        "mean_FTR_t1_stability": "FTR_t1_stability",
        "mean_FTR_t1_empty_zero": "FTR_t1_empty_zero",
        "robust_to_unstable_rate": "robust_to_unstable_rate",
        "mean_t0_margin": "mean_t0_margin",
        "evidence_mass_phi": "evidence_mass_phi",
    }
    for (margin_m, k, support_mode), group in seed_df.groupby(["margin_m_eV_atom", "K", "support_mode"], sort=True):
        group = group.reset_index(drop=True)
        n = len(group)
        for metric, col in metrics.items():
            values = pd.to_numeric(group[col], errors="coerce").to_numpy(dtype=float)
            estimate = float(np.nanmean(values)) if np.isfinite(values).any() else math.nan
            boot = []
            for _ in range(N_BOOTSTRAP):
                sample = values[rng.integers(0, n, size=n)]
                boot.append(float(np.nanmean(sample)) if np.isfinite(sample).any() else math.nan)
            finite = np.asarray([x for x in boot if math.isfinite(x)], dtype=float)
            lo, hi = np.quantile(finite, [0.025, 0.975]) if len(finite) else (math.nan, math.nan)
            rows.append(
                {
                    "margin_m_eV_atom": float(margin_m),
                    "K": int(k),
                    "support_mode": support_mode,
                    "metric": metric,
                    "estimate": estimate,
                    "ci_low_95": float(lo),
                    "ci_high_95": float(hi),
                    "bootstrap_unit": "seed",
                    "n_bootstrap": N_BOOTSTRAP,
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows)


def write_preregistration(queue_hash: str) -> None:
    text = f"""# Phase67b Hard-Margin Eligibility Preregistration

Status: executed as a versioned release-card design diagnostic on frozen t0/t1
queue artifacts. This is not prospective materials discovery and not DFT
evidence.

## Frozen inputs

- Candidate universe: Phase51 frozen K=500 WBM queue union.
- Candidate universe hash: `{queue_hash}`.
- Alpha: `0.10`.
- Seeds: `0..19`.
- K grid: `{K_GRID}`.
- Margin grid eV/atom: `{MARGIN_GRID}`.

## Eligibility and validity event

For margin `m`, a candidate can enter the release pool only if
`e_above_hull,t0 <= -m`.  The certified t0 event is the same margin-stability
event.  Current-MP t1 labels are used only for post-release survival audit.

## Selection rule

Eligible candidates are ranked by t0 margin and then filtered by the PARC SCS
e-value rule.  The rule explicitly uses t0 hull margin as eligibility metadata;
it is therefore a durability design diagnostic, not a hidden-label discovery
benchmark.
"""
    (PHASE67B / "HARD_MARGIN_ELIGIBILITY_PREREGISTRATION.md").write_text(text, encoding="utf-8")


def write_readme(frontier: pd.DataFrame) -> None:
    positive = bool(frontier["primary_success"].astype(bool).any())
    best = frontier.sort_values(
        ["primary_success", "t1_survival_safe_seeds", "nonempty_seeds", "mean_release_size", "mean_FTR_t1_stability_if_nonempty"],
        ascending=[False, False, False, False, True],
    ).iloc[0]
    text = f"""# Phase67b Hard-Margin Eligibility

Status: `completed_hard_margin_eligibility_diagnostic`.

Phase67b is a stricter follow-up to Phase67. It permits release only for
candidates whose frozen t0 hull margin satisfies `margin >= m`, ranks eligible
candidates by t0 margin, and evaluates current-MP t1 survival after release.

Headline positive hard-margin t1 survival allowed: `{str(positive).lower()}`.

Best row by primary-success/safe/nonempty/release-size ordering:

- margin m eV/atom: `{best['margin_m_eV_atom']}`
- K: `{int(best['K'])}`
- support mode: `{best['support_mode']}`
- non-empty seeds: `{int(best['nonempty_seeds'])}/20`
- t1 survival safe seeds: `{int(best['t1_survival_safe_seeds'])}/20`
- mean release size: `{float(best['mean_release_size']):.3f}`
- mean t1 FTR if non-empty: `{best['mean_FTR_t1_stability_if_nonempty']}`

Guardrails:

- no prospective materials discovery;
- no independent DFT evidence;
- t0 margin is used as eligibility metadata;
- no post-hoc K or margin selection as a headline unless the full grid is
  reported.
"""
    (PHASE67B / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase67b_hard_margin_eligibility"]
    rows.append(
        {
            "milestone": "ncs_phase67b_hard_margin_eligibility",
            "path": "outputs/milestones/ncs_phase67b_hard_margin_eligibility/",
            "evidence_state": "completed_hard_margin_eligibility_diagnostic",
            "manifest": "outputs/milestones/ncs_phase67b_hard_margin_eligibility/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase67b_hard_margin_eligibility",
        }
    )
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["milestone", "path", "evidence_state", "manifest", "public_bundle_check"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def update_evidence_ledger(frontier: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "DUR-MARGIN-HARD-001"]
    positive = bool(frontier["primary_success"].astype(bool).any())
    rows.append(
        {
            "claim_id": "DUR-MARGIN-HARD-001",
            "claim_text": "Hard t0-margin eligibility tests whether a deterministic margin buffer yields a current-MP surviving release frontier.",
            "evidence_type": "hard_margin_eligibility_frontier",
            "positive_evidence": "yes" if positive else "partial",
            "scope": "t0_margin_eligibility_design_diagnostic_not_prospective_discovery",
            "artifact_path": "outputs/milestones/ncs_phase67b_hard_margin_eligibility/table_hard_margin_frontier.csv",
            "hash": sha256_file(PHASE67B / "table_hard_margin_frontier.csv"),
            "validation_command": "make reproduce-ncs-phase67b-hard-margin-eligibility",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_DFT_evidence_or_prospective_materials_discovery_or_hidden_label_discovery",
        }
    )
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "claim_id",
                "claim_text",
                "evidence_type",
                "positive_evidence",
                "scope",
                "artifact_path",
                "hash",
                "validation_command",
                "status",
                "overclaim_guardrail",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    PHASE67B.mkdir(parents=True, exist_ok=True)
    queue_path = PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv"
    queue_hash = sha256_file(queue_path)
    base = load_queue()
    seed_rows: list[dict[str, object]] = []
    candidate_rows: list[pd.DataFrame] = []
    for margin_m in MARGIN_GRID:
        for k in K_GRID:
            for support_mode, rho in SUPPORT_MODES:
                for seed in SEEDS:
                    row, candidates = run_seed(base, margin_m=margin_m, k=k, seed=seed, support_mode=support_mode, rho=rho)
                    seed_rows.append(row)
                    if seed == 0:
                        candidate_rows.append(candidates)
    seed_df = pd.DataFrame(seed_rows)
    candidate_seed0 = pd.concat(candidate_rows, ignore_index=True) if candidate_rows else pd.DataFrame()
    frontier, gate = summarize_frontier(seed_df)
    boot = bootstrap_seed_metrics(seed_df)
    fig = frontier.assign(panel="hard_margin_frontier")

    seed_df.to_csv(PHASE67B / "table_hard_margin_seed_rows.csv", index=False)
    frontier.to_csv(PHASE67B / "table_hard_margin_frontier.csv", index=False)
    gate.to_csv(PHASE67B / "table_hard_margin_gate_audit.csv", index=False)
    boot.to_csv(PHASE67B / "table_hard_margin_bootstrap.csv", index=False)
    candidate_seed0.to_csv(PHASE67B / "table_hard_margin_candidate_level_seed0.csv", index=False)
    fig.to_csv(PHASE67B / "figure_hard_margin_frontier_inputs.csv", index=False)
    write_preregistration(queue_hash)
    write_readme(frontier)

    provenance = {
        "status": "completed_hard_margin_eligibility_diagnostic",
        "input_table": rel(queue_path),
        "input_sha256": queue_hash,
        "K_grid": K_GRID,
        "margin_grid_eV_atom": MARGIN_GRID,
        "support_modes": [mode for mode, _ in SUPPORT_MODES],
        "seed_rows": int(len(seed_df)),
        "headline_positive_allowed": bool(frontier["primary_success"].astype(bool).any()),
        "scope": SCOPE,
    }
    (PHASE67B / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    update_artifact_index()
    update_evidence_ledger(frontier)
    write_manifest(PHASE67B)
    write_root_manifest()
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
