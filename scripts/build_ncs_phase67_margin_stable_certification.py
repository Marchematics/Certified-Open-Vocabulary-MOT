#!/usr/bin/env python3
"""Build Phase67 margin-stable certification.

This experiment is the constructive counterpart to Phase66.  Instead of asking
whether a t0 certificate for the fragile event h_t0 <= 0 survives a current-MP
hull update, it changes the versioned release-card target to robust t0
stability:

    Y_m(t0) = 1{e_above_hull,t0 <= -m}.

The score used for certification is the frozen t0 margin, -e_above_hull,t0,
not the original raw model score.  The experiment is therefore a versioned
release-card durability diagnostic, not prospective materials discovery and not
independent DFT evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from run_materials_discovery_parc_flagship import gamma_star_from_p, scs_release_count


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE67 = ROOT / "outputs/milestones/ncs_phase67_margin_stable_certification"

ALPHA = 0.10
SEEDS = list(range(20))
K_GRID = [10, 15, 20, 25, 50, 75, 100, 150, 200, 300, 500]
MARGIN_GRID = [0.0, 0.01, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00, 1.50, 2.00, 2.50, 3.00]
SUPPORT_MODES = [
    ("margin_10pct_support", 0.10),
    ("margin_full_calibration_block_support", 1.00),
]
N_BOOTSTRAP = 1000
SCOPE = (
    "completed_margin_stable_certification_diagnostic;"
    "validity_event_t0_ehull_le_minus_m;"
    "score_is_t0_margin_not_raw_model_score;"
    "queue_limited_K500_WBM_union;"
    "t1_used_only_for_post_release_survival_audit;"
    "not_prospective_discovery;"
    "not_DFT_evidence;"
    "not_independent_validation"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def split_blocks(block_ids: list[str], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def load_queue() -> pd.DataFrame:
    queue = pd.read_csv(PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv")
    queue = queue[queue["K"].eq(500)].copy()
    queue["candidate_id"] = queue["candidate_id"].astype(str)
    queue = queue.sort_values(["raw_rank", "candidate_id"]).drop_duplicates("candidate_id").reset_index(drop=True)
    queue["block_id"] = queue["chemical_system"].astype(str)
    queue["h0"] = pd.to_numeric(queue["t0_e_above_hull"], errors="coerce")
    queue["h1"] = pd.to_numeric(queue["t1_e_above_hull"], errors="coerce")
    queue["t0_stable"] = queue["h0"].le(0.0)
    queue["t1_stable"] = queue["h1"].le(0.0)
    queue["t0_margin"] = -queue["h0"]
    queue["hull_drift"] = queue["h1"] - queue["h0"]
    queue = queue[queue["t0_margin"].notna() & queue["h1"].notna()].copy()
    return queue


def add_margin_labels(frame: pd.DataFrame, margin_m: float) -> pd.DataFrame:
    out = frame.copy()
    out["margin_m"] = margin_m
    out["t0_margin_stable"] = out["t0_margin"].ge(margin_m)
    out["margin_score"] = out["t0_margin"]
    out["t1_survives_stable"] = out["t1_stable"]
    out["robust_to_unstable_t1"] = out["t0_margin_stable"] & ~out["t1_stable"]
    return out


def compute_evalues(
    frame: pd.DataFrame,
    *,
    cal_blocks: set[str],
    followup_blocks: set[str],
    observed_positive: np.ndarray,
) -> tuple[pd.DataFrame, dict[str, object]]:
    block_series = frame["block_id"].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    followup_mask = block_series.isin(followup_blocks).to_numpy()
    cal_null = frame.loc[cal_mask & ~observed_positive, ["block_id", "margin_score"]]
    maxima = (
        cal_null.groupby("block_id", sort=False)["margin_score"].max().astype(float).to_numpy()
        if len(cal_null)
        else np.asarray([], dtype=float)
    )
    followup = frame.loc[followup_mask].sort_values(["margin_score", "candidate_id"], ascending=[False, True]).copy()
    p_min = 1.0 / (len(maxima) + 1.0) if len(maxima) else 1.0
    gamma = gamma_star_from_p(p_min)
    if gamma is None or len(maxima) == 0 or len(followup) == 0:
        followup["_margin_evalue"] = np.zeros(len(followup), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = followup["margin_score"].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        followup["_margin_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return followup, {
        "calibration_blocks": int(len(cal_blocks)),
        "followup_blocks": int(len(followup_blocks)),
        "nonempty_calibration_null_blocks": int(len(maxima)),
        "block_coverage": float(len(maxima) / len(cal_blocks)) if cal_blocks else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma if gamma is not None else math.nan,
    }


def _mean_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else math.nan


def _median_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.median()) if len(values) else math.nan


def _min_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.min()) if len(values) else math.nan


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
            "mean_hull_drift": math.nan,
            "median_hull_drift": math.nan,
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
        "mean_t0_margin": _mean_or_nan(selected["t0_margin"]),
        "median_t0_margin": _median_or_nan(selected["t0_margin"]),
        "minimum_t0_margin": _min_or_nan(selected["t0_margin"]),
        "mean_hull_drift": _mean_or_nan(selected["hull_drift"]),
        "median_hull_drift": _median_or_nan(selected["hull_drift"]),
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
    eligible = np.flatnonzero(cal_mask & frame["t0_margin_stable"].to_numpy(dtype=bool))
    if len(eligible) and rho > 0:
        n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
        scores = frame["margin_score"].to_numpy(dtype=float)
        chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
        observed[chosen] = True

    followup, diag = compute_evalues(frame, cal_blocks=cal_blocks, followup_blocks=followup_blocks, observed_positive=observed)
    pool = followup.head(k).copy()
    released, tau, scs_margin, evidence_mass = scs_release_count(pool["_margin_evalue"].to_numpy(dtype=float), alpha=ALPHA, budget=k)
    if released:
        selected = pool.iloc[np.argsort(pool["_margin_evalue"].to_numpy(dtype=float))[::-1][:released]].copy()
    else:
        selected = pool.iloc[[]].copy()
    summary = summarize_release(selected)

    if released and summary["FTR_t1_stability"] <= ALPHA:
        decision = "margin_stable_t1_survival_positive"
    elif released:
        decision = "margin_stable_release_fails_t1_survival_gate"
    else:
        decision = "margin_stable_certified_refusal"

    robust_pool = pool[pool["t0_margin_stable"].astype(bool)]
    row = {
        "margin_m_eV_atom": margin_m,
        "K": k,
        "alpha": ALPHA,
        "seed": seed,
        "support_mode": support_mode,
        "rho_margin_positive_support": rho,
        "decision": decision,
        "ranking_score": "t0_margin_descending",
        "validity_event": "t0_e_above_hull_le_minus_m",
        "observed_margin_positives": int(observed.sum()),
        "margin_positive_eligible_in_calibration": int(len(eligible)),
        "raw_pool_size": int(len(pool)),
        "raw_pool_margin_false_rate": float((~pool["t0_margin_stable"].astype(bool)).mean()) if len(pool) else math.nan,
        "raw_pool_t1_FTR": float((~pool["t1_stable"].astype(bool)).mean()) if len(pool) else math.nan,
        "raw_pool_robust_to_unstable_rate": float((robust_pool["t0_margin_stable"].astype(bool) & ~robust_pool["t1_stable"].astype(bool)).mean())
        if len(robust_pool)
        else math.nan,
        "release_threshold_tau": tau,
        "self_consistency_margin": scs_margin,
        "evidence_mass_phi": evidence_mass,
        "max_evalue": float(pool["_margin_evalue"].max()) if len(pool) else 0.0,
        "required_evalue_threshold": tau,
        "candidate_universe": "frozen_K500_WBM_queue_union",
        "selection_rule": "rank_by_t0_margin_then_SCS_evalue_self_consistency",
        "evidence_scope": SCOPE,
        **diag,
        **summary,
    }
    candidate = pool.copy()
    candidate["seed"] = seed
    candidate["support_mode"] = support_mode
    candidate["rho_margin_positive_support"] = rho
    candidate["selected_by_phase67_margin_stable_certification"] = candidate["candidate_id"].isin(set(selected["candidate_id"].astype(str)))
    candidate["ranking_score"] = "t0_margin_descending"
    candidate["validity_event"] = "t0_e_above_hull_le_minus_m"
    candidate["evidence_scope"] = SCOPE
    return row, candidate


def bootstrap_seed_metrics(seed_df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(20260529)
    rows: list[dict[str, object]] = []
    metrics = {
        "mean_release_size": "release_size",
        "mean_FTR_t0_margin_event": "FTR_t0_margin_event",
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
            boot: list[float] = []
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


def summarize_frontier(seed_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frontier_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    survival_rows: list[dict[str, object]] = []
    for (margin_m, k, support_mode), group in seed_df.groupby(["margin_m_eV_atom", "K", "support_mode"], sort=True):
        nonempty = int((group["release_size"].astype(int) > 0).sum())
        t0_safe = int(((group["release_size"].astype(int) > 0) & (group["FTR_t0_margin_event"].astype(float) <= ALPHA)).sum())
        t1_safe = int(((group["release_size"].astype(int) > 0) & (group["FTR_t1_stability"].astype(float) <= ALPHA)).sum())
        nonempty_group = group[group["release_size"].astype(int) > 0]
        mean_t0_ftr = float(nonempty_group["FTR_t0_margin_event"].astype(float).mean()) if len(nonempty_group) else math.nan
        mean_t1_ftr = float(nonempty_group["FTR_t1_stability"].astype(float).mean()) if len(nonempty_group) else math.nan
        primary_success = bool(nonempty >= 18 and t1_safe >= 18 and math.isfinite(mean_t1_ftr) and mean_t1_ftr <= ALPHA)
        if primary_success:
            claim_status = "completed_margin_stable_constructive_t1_survival_positive"
        elif nonempty > 0:
            claim_status = "completed_margin_stable_boundary_diagnostic_not_headline"
        else:
            claim_status = "completed_margin_stable_refusal_boundary"
        row = {
            "margin_m_eV_atom": float(margin_m),
            "K": int(k),
            "alpha": ALPHA,
            "support_mode": support_mode,
            "rho_margin_positive_support": float(group["rho_margin_positive_support"].iloc[0]),
            "n_seeds": int(group["seed"].nunique()),
            "nonempty_seeds": nonempty,
            "t0_margin_safe_seeds": t0_safe,
            "t1_survival_safe_seeds": t1_safe,
            "mean_release_size": float(group["release_size"].astype(float).mean()),
            "median_release_size": float(group["release_size"].astype(float).median()),
            "max_release_size": int(group["release_size"].astype(int).max()),
            "mean_FTR_t0_margin_event_if_nonempty": mean_t0_ftr,
            "mean_FTR_t1_stability_if_nonempty": mean_t1_ftr,
            "mean_FTR_t1_empty_zero": float(group["FTR_t1_empty_zero"].astype(float).mean()),
            "mean_raw_pool_t1_FTR": float(group["raw_pool_t1_FTR"].astype(float).mean()),
            "mean_raw_pool_margin_false_rate": float(group["raw_pool_margin_false_rate"].astype(float).mean()),
            "robust_to_unstable_rate": float(group["robust_to_unstable_rate"].astype(float).mean()),
            "mean_t0_margin": float(group["mean_t0_margin"].astype(float).mean(skipna=True)) if group["mean_t0_margin"].notna().any() else math.nan,
            "median_t0_margin": float(group["median_t0_margin"].astype(float).median(skipna=True)) if group["median_t0_margin"].notna().any() else math.nan,
            "minimum_t0_margin": float(group["minimum_t0_margin"].astype(float).min(skipna=True)) if group["minimum_t0_margin"].notna().any() else math.nan,
            "evidence_mass_phi": float(group["evidence_mass_phi"].astype(float).mean()),
            "max_evalue": float(group["max_evalue"].astype(float).mean()),
            "required_evalue_threshold": float(group["required_evalue_threshold"].astype(float).mean()),
            "decision": "release" if nonempty else "refusal",
            "primary_success": primary_success,
            "claim_status": claim_status,
            "ranking_score": "t0_margin_descending",
            "validity_event": "t0_e_above_hull_le_minus_m",
            "selection_rule": "rank_by_t0_margin_then_SCS_evalue_self_consistency",
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
            ("constructive_margin_stable_t1_survival_positive", 1 if primary_success else 0, 1, "PASS" if primary_success else "FAIL"),
            ("margin_ranked_not_raw_score", 1, 1, "PASS"),
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
        survival_rows.append(
            {
                "margin_m_eV_atom": float(margin_m),
                "K": int(k),
                "support_mode": support_mode,
                "nonempty_seeds": nonempty,
                "t1_survival_safe_seeds": t1_safe,
                "mean_release_size": row["mean_release_size"],
                "mean_t0_margin": row["mean_t0_margin"],
                "mean_FTR_t1_stability_if_nonempty": mean_t1_ftr,
                "robust_to_unstable_rate": row["robust_to_unstable_rate"],
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(frontier_rows), pd.DataFrame(gate_rows), pd.DataFrame(survival_rows)


def write_preregistration(queue_hash: str) -> None:
    text = f"""# Phase67 Margin-Stable Certification Preregistration

Status: executed as a versioned release-card diagnostic on already frozen
t0/t1 queue artifacts.  This is not prospective materials discovery and not DFT
evidence.

## Frozen inputs

- Candidate universe: Phase51 frozen K=500 WBM queue union.
- Candidate universe hash: `{queue_hash}`.
- t0 reference: WBM/Matbench t0 hull labels already present in Phase51 table.
- t1 reference: current-MP labels already present in Phase51 table; used only
  for post-release survival audit.
- Blocks: chemical system / composition-family proxy via `chemical_system`.
- Alpha: `0.10`.
- Seeds: `0..19`.
- K grid: `{K_GRID}`.
- Margin grid eV/atom: `{MARGIN_GRID}`.

## Validity event

For margin `m`, the certified t0 event is:

`Y_m(t0) = 1[e_above_hull,t0 <= -m]`.

The t1 survival audit uses the ordinary current-MP stability event
`e_above_hull,t1 <= 0`.

## Selection rule

Candidates are ranked by t0 margin (`-e_above_hull,t0`) and then filtered by
the PARC SCS e-value rule.  Raw model score is not used for Phase67 ranking.

## Success gate

A row is a constructive margin-stable t1-survival positive only if:

- non-empty release in at least `18/20` seeds;
- t1 FTR <= alpha in at least `18/20` non-empty seeds;
- mean t1 FTR among non-empty releases <= alpha.

All K and margin rows are reported; no row is selected by post-release t1 FTR.
"""
    (PHASE67 / "MARGIN_STABLE_CERTIFICATION_PREREGISTRATION.md").write_text(text, encoding="utf-8")


def write_readme(frontier: pd.DataFrame) -> None:
    positive = bool(frontier["primary_success"].astype(bool).any())
    best = frontier.sort_values(
        ["primary_success", "t1_survival_safe_seeds", "nonempty_seeds", "mean_release_size"],
        ascending=False,
    ).iloc[0]
    text = f"""# Phase67 Margin-Stable Certification

Status: `completed_margin_stable_certification_diagnostic`.

Phase67 changes the release-card target from fragile t0 stability
`e_above_hull,t0 <= 0` to robust t0 margin-stability
`e_above_hull,t0 <= -m`, ranks by t0 margin, and evaluates whether the released
set survives the current-MP t1 hull.

Headline positive margin-stable t1 survival allowed: `{str(positive).lower()}`.

Best row by primary-success/safe/nonempty/release-size ordering:

- margin m eV/atom: `{best['margin_m_eV_atom']}`
- K: `{int(best['K'])}`
- support mode: `{best['support_mode']}`
- non-empty seeds: `{int(best['nonempty_seeds'])}/20`
- t1 survival safe seeds: `{int(best['t1_survival_safe_seeds'])}/20`
- mean release size: `{float(best['mean_release_size']):.3f}`
- mean t1 FTR if non-empty: `{best['mean_FTR_t1_stability_if_nonempty']}`

Allowed claim:

- Margin-stable release cards test whether t0 hull margin buffers current-MP
  drift and can identify a smaller release frontier.

Guardrails:

- no prospective materials discovery;
- no independent DFT evidence;
- no claim that t0 margin labels are hidden from selection;
- no post-hoc K or margin selection as a headline unless the full grid is
  reported.
"""
    (PHASE67 / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase67_margin_stable_certification"]
    rows.append(
        {
            "milestone": "ncs_phase67_margin_stable_certification",
            "path": "outputs/milestones/ncs_phase67_margin_stable_certification/",
            "evidence_state": "completed_margin_stable_certification_diagnostic",
            "manifest": "outputs/milestones/ncs_phase67_margin_stable_certification/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase67_margin_stable_certification",
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
    rows = [row for row in rows if row["claim_id"] != "DUR-MARGIN-001"]
    positive = bool(frontier["primary_success"].astype(bool).any())
    rows.append(
        {
            "claim_id": "DUR-MARGIN-001",
            "claim_text": "Margin-stable certification tests whether requiring t0 hull margin m yields a current-MP surviving release frontier.",
            "evidence_type": "margin_stable_certification_frontier",
            "positive_evidence": "yes" if positive else "partial",
            "scope": "t0_margin_release_card_diagnostic_not_prospective_discovery",
            "artifact_path": "outputs/milestones/ncs_phase67_margin_stable_certification/table_margin_stable_certification_frontier.csv",
            "hash": sha256_file(PHASE67 / "table_margin_stable_certification_frontier.csv"),
            "validation_command": "make reproduce-ncs-phase67-margin-stable-certification",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_DFT_evidence_or_prospective_materials_discovery_or_raw_score_ranking",
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


def write_figures(frontier: pd.DataFrame, survival: pd.DataFrame) -> None:
    fig = pd.concat(
        [
            frontier.assign(panel="margin_stable_frontier"),
            survival.assign(panel="survival_vs_margin"),
        ],
        ignore_index=True,
        sort=False,
    )
    fig.to_csv(PHASE67 / "figure_margin_stable_certification_inputs.csv", index=False)


def main() -> None:
    PHASE67.mkdir(parents=True, exist_ok=True)
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
    candidate_seed0 = pd.concat(candidate_rows, ignore_index=True)
    frontier, gate, survival = summarize_frontier(seed_df)
    boot = bootstrap_seed_metrics(seed_df)

    seed_df.to_csv(PHASE67 / "table_margin_stable_seed_rows.csv", index=False)
    frontier.to_csv(PHASE67 / "table_margin_stable_certification_frontier.csv", index=False)
    gate.to_csv(PHASE67 / "table_margin_stable_gate_audit.csv", index=False)
    survival.to_csv(PHASE67 / "table_margin_stable_survival_by_margin.csv", index=False)
    boot.to_csv(PHASE67 / "table_margin_stable_bootstrap.csv", index=False)
    candidate_seed0.to_csv(PHASE67 / "table_margin_stable_candidate_level_seed0.csv", index=False)
    write_figures(frontier, survival)
    write_preregistration(queue_hash)
    write_readme(frontier)

    provenance = {
        "status": "completed_margin_stable_certification_diagnostic",
        "input_table": rel(queue_path),
        "input_sha256": queue_hash,
        "K_grid": K_GRID,
        "margin_grid_eV_atom": MARGIN_GRID,
        "support_modes": [mode for mode, _ in SUPPORT_MODES],
        "seed_rows": int(len(seed_df)),
        "headline_positive_allowed": bool(frontier["primary_success"].astype(bool).any()),
        "scope": SCOPE,
    }
    (PHASE67 / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    update_artifact_index()
    update_evidence_ledger(frontier)
    write_manifest(PHASE67)
    write_root_manifest()
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
