#!/usr/bin/env python3
"""Build Phase66 certificate durability and recertification frontier.

Phase66 extends Phase56/64 in two ways:

1. It records the version-shift accounting and margin-buffer durability
   statements as a supplement-ready theoretical note.
2. It reruns the queue-limited current-MP PARC-R recertification replay on a
   predeclared small-to-large K grid, reporting every row rather than selecting
   the first favorable K after looking at t1 outcomes.

The available t1 labels cover the frozen K=500 WBM queue union.  This milestone
therefore remains a queue-limited recertification frontier, not a full-WBM
current-MP theorem certificate and not prospective materials discovery.
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
OUT = ROOT / "outputs/milestones/ncs_phase66_certificate_durability"

ALPHA = 0.10
SEEDS = list(range(20))
K_GRID = [10, 15, 20, 25, 50, 75, 100, 150, 200, 300, 500]
SUPPORT_MODES = [
    ("t1_10pct_support", 0.10),
    ("t1_full_calibration_block_support", 1.00),
]
MARGIN_GRID = [0.0, 0.01, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 0.50]
N_BOOTSTRAP = 1000
SCOPE = (
    "completed_certificate_durability_frontier;"
    "queue_limited_current_MP_t1_recertification;"
    "reports_all_predeclared_K_values;"
    "not_strict_t1_alpha_certificate_for_old_release;"
    "not_full_WBM_recertification;"
    "not_DFT_evidence;"
    "not_prospective_discovery;"
    "historical_drift_tail_not_future_guarantee"
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
    queue["t0_stable"] = queue["t0_label"].eq("stable")
    queue["t1_stable"] = queue["t1_label"].eq("stable")
    queue["score_for_recertification"] = pd.to_numeric(queue["raw_score"], errors="coerce")
    queue["h0"] = pd.to_numeric(queue["t0_e_above_hull"], errors="coerce")
    queue["h1"] = pd.to_numeric(queue["t1_e_above_hull"], errors="coerce")
    queue["t0_margin"] = np.where(queue["t0_stable"], -queue["h0"], np.nan)
    queue["hull_drift"] = queue["h1"] - queue["h0"]
    return queue


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
    cal_null = frame.loc[cal_mask & ~observed_positive, ["block_id", "score_for_recertification"]]
    maxima = (
        cal_null.groupby("block_id", sort=False)["score_for_recertification"].max().astype(float).to_numpy()
        if len(cal_null)
        else np.asarray([], dtype=float)
    )
    followup = frame.loc[followup_mask].sort_values("score_for_recertification", ascending=False).copy()
    p_min = 1.0 / (len(maxima) + 1.0) if len(maxima) else 1.0
    gamma = gamma_star_from_p(p_min)
    if gamma is None or len(maxima) == 0 or len(followup) == 0:
        followup["_recert_evalue"] = np.zeros(len(followup), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = followup["score_for_recertification"].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        followup["_recert_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
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


def summarize_release(selected: pd.DataFrame, *, k: int) -> dict[str, object]:
    n = int(len(selected))
    if n == 0:
        return {
            "release_size": 0,
            "release_false_t1": 0,
            "release_false_t0": 0,
            "release_FTR_t1": math.nan,
            "release_FTR_t0": math.nan,
            "release_FTR_t1_decision_empty_zero": 0.0,
            "stable_to_unstable_count": 0,
            "unstable_to_stable_count": 0,
            "stable_to_unstable_rate": 0.0,
            "unstable_to_stable_rate": 0.0,
            "mean_t0_margin": math.nan,
            "median_t0_margin": math.nan,
            "minimum_t0_margin": math.nan,
            "mean_hull_drift": math.nan,
            "median_hull_drift": math.nan,
        }
    t0_stable = selected["t0_stable"].astype(bool)
    t1_stable = selected["t1_stable"].astype(bool)
    stable_to_unstable = t0_stable & ~t1_stable
    unstable_to_stable = ~t0_stable & t1_stable
    return {
        "release_size": n,
        "release_false_t1": int((~t1_stable).sum()),
        "release_false_t0": int((~t0_stable).sum()),
        "release_FTR_t1": float((~t1_stable).mean()),
        "release_FTR_t0": float((~t0_stable).mean()),
        "release_FTR_t1_decision_empty_zero": float((~t1_stable).mean()),
        "stable_to_unstable_count": int(stable_to_unstable.sum()),
        "unstable_to_stable_count": int(unstable_to_stable.sum()),
        "stable_to_unstable_rate": float(stable_to_unstable.mean()),
        "unstable_to_stable_rate": float(unstable_to_stable.mean()),
        "mean_t0_margin": _mean_or_nan(selected.loc[t0_stable, "t0_margin"]),
        "median_t0_margin": _median_or_nan(selected.loc[t0_stable, "t0_margin"]),
        "minimum_t0_margin": _min_or_nan(selected.loc[t0_stable, "t0_margin"]),
        "mean_hull_drift": _mean_or_nan(selected["hull_drift"]),
        "median_hull_drift": _median_or_nan(selected["hull_drift"]),
    }


def run_seed(frame: pd.DataFrame, *, k: int, seed: int, support_mode: str, rho: float) -> tuple[dict[str, object], pd.DataFrame]:
    cal_blocks, followup_blocks = split_blocks(frame["block_id"].astype(str).tolist(), seed)
    block_series = frame["block_id"].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    observed = np.zeros(len(frame), dtype=bool)
    eligible = np.flatnonzero(cal_mask & frame["t1_stable"].to_numpy(dtype=bool))
    if len(eligible) and rho > 0:
        n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
        scores = frame["score_for_recertification"].to_numpy(dtype=float)
        chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
        observed[chosen] = True

    followup, diag = compute_evalues(
        frame,
        cal_blocks=cal_blocks,
        followup_blocks=followup_blocks,
        observed_positive=observed,
    )
    pool = followup.head(k).copy()
    released, tau, margin, best_ratio = scs_release_count(pool["_recert_evalue"].to_numpy(dtype=float), alpha=ALPHA, budget=k)
    if released:
        selected = pool.iloc[np.argsort(pool["_recert_evalue"].to_numpy(dtype=float))[::-1][:released]].copy()
    else:
        selected = pool.iloc[[]].copy()
    release_summary = summarize_release(selected, k=k)

    ftr_t1 = release_summary["release_FTR_t1"]
    if released and float(ftr_t1) <= ALPHA:
        decision = "versioned_current_MP_certified_release"
    elif released:
        decision = "versioned_boundary_release_fails_primary_gate"
    else:
        decision = "versioned_certified_refusal"

    row = {
        "K": k,
        "alpha": ALPHA,
        "seed": seed,
        "support_mode": support_mode,
        "rho_t1_positive_support": rho,
        "decision": decision,
        "raw_pool_size": int(len(pool)),
        "raw_pool_FTR_t1": float((~pool["t1_stable"].astype(bool)).mean()) if len(pool) else math.nan,
        "raw_pool_FTR_t0": float((~pool["t0_stable"].astype(bool)).mean()) if len(pool) else math.nan,
        "observed_t1_positives": int(observed.sum()),
        "t1_stable_eligible_in_calibration": int(len(eligible)),
        "release_threshold_tau": tau,
        "self_consistency_margin": margin,
        "evidence_mass_phi": best_ratio,
        "max_evalue": float(pool["_recert_evalue"].max()) if len(pool) else 0.0,
        "required_evalue_threshold": tau,
        "candidate_universe": "frozen_K500_WBM_queue_union",
        "operational_selector_rule": "report_all_K;optional_selector_largest_K_with_nonempty_ge18_seeds_using_calibration_only",
        "evidence_scope": SCOPE,
        **diag,
        **release_summary,
    }

    candidate = pool.copy()
    candidate["seed"] = seed
    candidate["support_mode"] = support_mode
    candidate["rho_t1_positive_support"] = rho
    candidate["selected_by_phase66_recertification"] = candidate["candidate_id"].isin(set(selected["candidate_id"].astype(str)))
    candidate["evidence_scope"] = SCOPE
    return row, candidate


def bootstrap_seed_metrics(seed_df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(20260529)
    rows: list[dict[str, object]] = []
    metrics = {
        "mean_release_size": "release_size",
        "mean_FTR_t1_if_nonempty": "release_FTR_t1",
        "mean_FTR_t1_decision_empty_zero": "release_FTR_t1_decision_empty_zero",
        "stable_to_unstable_drift_rate": "stable_to_unstable_rate",
        "mean_t0_margin": "mean_t0_margin",
        "evidence_mass_phi": "evidence_mass_phi",
    }
    for (k, support_mode), group in seed_df.groupby(["K", "support_mode"], sort=True):
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
            if len(finite):
                lo, hi = np.quantile(finite, [0.025, 0.975])
            else:
                lo, hi = math.nan, math.nan
            rows.append(
                {
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
    margin_rows: list[dict[str, object]] = []
    for (k, support_mode), group in seed_df.groupby(["K", "support_mode"], sort=True):
        nonempty = int((group["release_size"].astype(int) > 0).sum())
        safe = int(((group["release_size"].astype(int) > 0) & (group["release_FTR_t1"].astype(float) <= ALPHA)).sum())
        nonempty_group = group[group["release_size"].astype(int) > 0]
        mean_ftr_if_nonempty = float(nonempty_group["release_FTR_t1"].astype(float).mean()) if len(nonempty_group) else math.nan
        mean_release = float(group["release_size"].astype(float).mean())
        constructive_positive = bool(nonempty >= 18 and safe >= 18 and math.isfinite(mean_ftr_if_nonempty) and mean_ftr_if_nonempty <= ALPHA)
        if constructive_positive:
            claim_status = "completed_constructive_current_MP_recertification_positive"
            recertification_status = "versioned_current_MP_release_frontier_positive"
        elif nonempty > 0:
            claim_status = "completed_small_K_boundary_release_diagnostic_not_headline"
            recertification_status = "versioned_boundary_release_fails_primary_gate"
        else:
            claim_status = "completed_versioned_recertification_refusal_boundary"
            recertification_status = "versioned_refusal"
        row = {
            "K": int(k),
            "alpha": ALPHA,
            "support_mode": support_mode,
            "rho_t1_positive_support": float(group["rho_t1_positive_support"].iloc[0]),
            "n_seeds": int(group["seed"].nunique()),
            "nonempty_seeds": nonempty,
            "safe_seeds": safe,
            "mean_release_size": mean_release,
            "median_release_size": float(group["release_size"].astype(float).median()),
            "max_release_size": int(group["release_size"].astype(int).max()),
            "mean_FTR_t1_if_nonempty": mean_ftr_if_nonempty,
            "mean_FTR_t1_decision_empty_zero": float(group["release_FTR_t1_decision_empty_zero"].astype(float).mean()),
            "mean_FTR_t0_if_nonempty": float(nonempty_group["release_FTR_t0"].astype(float).mean()) if len(nonempty_group) else math.nan,
            "mean_raw_pool_FTR_t1": float(group["raw_pool_FTR_t1"].astype(float).mean()),
            "mean_raw_pool_FTR_t0": float(group["raw_pool_FTR_t0"].astype(float).mean()),
            "stable_to_unstable_drift_rate": float(group["stable_to_unstable_rate"].astype(float).mean()),
            "unstable_to_stable_correction_rate": float(group["unstable_to_stable_rate"].astype(float).mean()),
            "mean_t0_margin": float(group["mean_t0_margin"].astype(float).mean(skipna=True)) if group["mean_t0_margin"].notna().any() else math.nan,
            "median_t0_margin": float(group["median_t0_margin"].astype(float).median(skipna=True)) if group["median_t0_margin"].notna().any() else math.nan,
            "minimum_t0_margin": float(group["minimum_t0_margin"].astype(float).min(skipna=True)) if group["minimum_t0_margin"].notna().any() else math.nan,
            "evidence_mass_phi": float(group["evidence_mass_phi"].astype(float).mean()),
            "max_evalue": float(group["max_evalue"].astype(float).mean()),
            "required_evalue_threshold": float(group["required_evalue_threshold"].astype(float).mean()),
            "decision": "release" if nonempty else "refusal",
            "primary_success": constructive_positive,
            "recertification_status": recertification_status,
            "claim_status": claim_status,
            "operational_selector_rule": str(group["operational_selector_rule"].iloc[0]),
            "evidence_scope": SCOPE,
        }
        frontier_rows.append(row)
        gate_checks = [
            ("nonempty_release_ge_18_seeds", nonempty, 18, "PASS" if nonempty >= 18 else "FAIL"),
            ("safe_release_ge_18_seeds", safe, 18, "PASS" if safe >= 18 else "FAIL"),
            (
                "mean_FTR_t1_if_nonempty_le_alpha",
                mean_ftr_if_nonempty if math.isfinite(mean_ftr_if_nonempty) else math.nan,
                ALPHA,
                "PASS" if math.isfinite(mean_ftr_if_nonempty) and mean_ftr_if_nonempty <= ALPHA else "FAIL",
            ),
            (
                "constructive_current_MP_recertification_positive",
                1 if constructive_positive else 0,
                1,
                "PASS" if constructive_positive else "FAIL",
            ),
            ("full_grid_reported_no_posthoc_K_selection", 1, 1, "PASS"),
        ]
        for gate, value, threshold, status in gate_checks:
            gate_rows.append(
                {
                    "K": int(k),
                    "support_mode": support_mode,
                    "gate": gate,
                    "value": value,
                    "threshold": threshold,
                    "status": status,
                    "evidence_scope": SCOPE,
                }
            )
        margin_rows.append(
            {
                "K": int(k),
                "support_mode": support_mode,
                "mean_t0_margin": row["mean_t0_margin"],
                "median_t0_margin": row["median_t0_margin"],
                "minimum_t0_margin": row["minimum_t0_margin"],
                "stable_to_unstable_drift_rate": row["stable_to_unstable_drift_rate"],
                "FTR_t1_if_nonempty": row["mean_FTR_t1_if_nonempty"],
                "mean_release_size": row["mean_release_size"],
                "nonempty_seeds": nonempty,
                "safe_seeds": safe,
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(frontier_rows), pd.DataFrame(gate_rows), pd.DataFrame(margin_rows)


def build_version_shift_decomposition(seed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in seed_df.iterrows():
        n = int(row["release_size"])
        ftr0 = float(row["release_FTR_t0"]) if n else 0.0
        ftr1 = float(row["release_FTR_t1"]) if n else 0.0
        delta_plus = float(row["stable_to_unstable_rate"]) if n else 0.0
        delta_minus = float(row["unstable_to_stable_rate"]) if n else 0.0
        rhs = ftr0 + delta_plus - delta_minus
        rows.append(
            {
                "K": int(row["K"]),
                "support_mode": row["support_mode"],
                "seed": int(row["seed"]),
                "release_size": n,
                "FTR_t0": ftr0,
                "FTR_t1": ftr1,
                "delta_stable_to_unstable": delta_plus,
                "delta_unstable_to_stable": delta_minus,
                "accounting_rhs": rhs,
                "accounting_residual": ftr1 - rhs,
                "conservative_upper_bound": ftr0 + delta_plus,
                "bound_slack": ftr0 + delta_plus - ftr1,
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def build_historical_drift_tail(queue: pd.DataFrame) -> pd.DataFrame:
    stable = queue[queue["t0_stable"].astype(bool) & queue["hull_drift"].notna()].copy()
    rng = np.random.default_rng(20260529)
    rows: list[dict[str, object]] = []
    group_sizes = stable.groupby("chemical_system").size().astype(float).to_numpy()
    group_drifts = [group["hull_drift"].astype(float).to_numpy() for _, group in stable.groupby("chemical_system")]
    n_groups = len(group_drifts)
    for margin in MARGIN_GRID:
        tail = stable["hull_drift"].astype(float) > margin
        pi_hat = float(tail.mean()) if len(stable) else math.nan
        group_tail_counts = np.asarray([float((drifts > margin).sum()) for drifts in group_drifts], dtype=float)
        boot = []
        for _ in range(N_BOOTSTRAP):
            if n_groups == 0:
                boot.append(math.nan)
                continue
            sampled = rng.integers(0, n_groups, size=n_groups)
            denom = float(group_sizes[sampled].sum())
            numer = float(group_tail_counts[sampled].sum())
            boot.append(numer / denom if denom else math.nan)
        finite = np.asarray([x for x in boot if math.isfinite(x)], dtype=float)
        lo, hi = np.quantile(finite, [0.025, 0.975]) if len(finite) else (math.nan, math.nan)
        rows.append(
            {
                "margin_m_eV_atom": margin,
                "n_t0_stable_with_drift": int(len(stable)),
                "n_drift_gt_m": int(tail.sum()),
                "pi_hat": pi_hat,
                "pi_ci_low_95": float(lo),
                "pi_ci_high_95": float(hi),
                "alpha_plus_pi_hat": ALPHA + pi_hat if math.isfinite(pi_hat) else math.nan,
                "bootstrap_unit": "chemical_system",
                "n_bootstrap": N_BOOTSTRAP,
                "guardrail": "historical_drift_tail_not_future_guarantee",
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def write_supplement() -> None:
    tex = r"""\subsection{Versioned certificate durability under reference drift}
\paragraph{Motivation and scope.}
PARC certificates are defined relative to a frozen candidate universe, a fixed
score, a one-sided support rule, and a specified reference label version.  When
the reference database changes, the truth definition changes as well.  A release
set certified at version \(t_0\) should therefore not be silently inherited at
version \(t_1\).

\paragraph{Versioned labels.}
Let \(P\) be a frozen finite candidate universe.  Each candidate \(p\in P\)
has labels \(Y_p^{(0)},Y_p^{(1)}\in\{0,1\}\), where \(Y_p^{(0)}=1\) means valid
under reference version \(t_0\), and \(Y_p^{(1)}=1\) means valid under reference
version \(t_1\).  For any release set \(R\subseteq P\),
\[
\mathrm{FTR}_v(R)=
\frac{\sum_{p\in R}{\bf 1}\{Y_p^{(v)}=0\}}{|R|\vee 1},\qquad v\in\{0,1\}.
\]
Define
\[
\delta_R^+ =
\frac{\sum_{p\in R}{\bf 1}\{Y_p^{(0)}=1,Y_p^{(1)}=0\}}{|R|\vee 1},
\qquad
\delta_R^- =
\frac{\sum_{p\in R}{\bf 1}\{Y_p^{(0)}=0,Y_p^{(1)}=1\}}{|R|\vee 1}.
\]

\paragraph{Proposition X.1: exact version-shift accounting.}
For any fixed or data-dependent release set \(R\subseteq P\),
\[
\mathrm{FTR}_1(R)=\mathrm{FTR}_0(R)+\delta_R^+-\delta_R^-.
\]
Consequently, \(\mathrm{FTR}_1(R)\le \mathrm{FTR}_0(R)+\delta_R^+\).

\emph{Proof.}
For each candidate \(p\),
\[
{\bf 1}\{Y_p^{(1)}=0\} =
{\bf 1}\{Y_p^{(0)}=0\}
+{\bf 1}\{Y_p^{(0)}=1,Y_p^{(1)}=0\}
-{\bf 1}\{Y_p^{(0)}=0,Y_p^{(1)}=1\}.
\]
Summing over \(p\in R\) and dividing by \(|R|\vee 1\) gives the equality.
Dropping the non-negative term \(\delta_R^-\) gives the inequality.

\paragraph{Corollary X.2: inherited-certificate decay.}
If a \(t_0\)-version PARC release \(R_0\) satisfies
\(\mathbb E[\mathrm{FTR}_0(R_0)]\le \alpha\), then under \(t_1\),
\[
\mathbb E[\mathrm{FTR}_1(R_0)]\le \alpha+\mathbb E[\delta_{R_0}^+].
\]
If an externally calibrated bound \(\delta_{R_0}^+\le \Delta\) is available,
then \(\mathbb E[\mathrm{FTR}_1(R_0)]\le \alpha+\Delta\).  This is a decay
accounting statement, not prospective \(t_1\) alpha control.

\paragraph{Corollary X.3: approximate validity plus reference drift.}
If \(t_0\)-false-candidate e-values obey \(\mathbb E[E_p]\le 1+\eta\), the
same argument yields
\[
\mathbb E[\mathrm{FTR}_1(R_0)]\le \alpha(1+\eta)+\mathbb E[\delta_{R_0}^+].
\]
This separates calibration/e-value error from reference-drift penalty.

\paragraph{Margin-buffer durability.}
Let \(h_p^{(0)}\) and \(h_p^{(1)}\) be versioned energy above hull values, and
let \(Y_p^{(v)}=1\) correspond to \(h_p^{(v)}\le 0\).  For a \(t_0\)-stable
candidate, define \(M_p^{(0)}=-h_p^{(0)}\ge 0\) and
\(D_p=h_p^{(1)}-h_p^{(0)}\).  A \(t_0\)-stable candidate becomes \(t_1\)-unstable
only if \(D_p>M_p^{(0)}\).  Therefore, if a release rule restricts \(t_0\)-stable
released candidates to margin at least \(m\), any stable-to-unstable flip must
satisfy \(D_p>m\).

\paragraph{Corollary X.4: margin-buffer durability bound.}
If \(R_m\) is \(t_0\)-certified and every \(t_0\)-stable released candidate
has \(M_p^{(0)}\ge m\), then
\[
\delta_{R_m}^+
\le
\frac{\sum_{p\in R_m}{\bf 1}\{Y_p^{(0)}=1,D_p>m\}}{|R_m|\vee1}.
\]
If a historical or external drift model gives
\(\Pr(D_p>m\mid p\in R_m,Y_p^{(0)}=1)\le \pi(m)\), then
\[
\mathbb E[\mathrm{FTR}_1(R_m)]\le \alpha+\pi(m),
\]
or \(\alpha(1+\eta)+\pi(m)\) under approximate e-values.  The empirical
\(\pi(m)\) used in this paper is a design diagnostic, not an absolute future
guarantee.

\paragraph{Theorem X.5: versioned recertification.}
Fix the \(t_1\) reference.  If the candidate universe, scores, budget grid,
compatibility rule, and block construction are frozen; \(t_1\)-version
one-sided reliability holds; the PARC exchangeability assumptions hold; and the
returned set satisfies self-consistency, then
\[
\mathbb E[\mathrm{FTR}_1(R_1)]\le \alpha.
\]
If no non-empty compatible set satisfies self-consistency, PARC returns
\(R_1=\varnothing\), for which \(\mathrm{FTR}_1(R_1)=0\).  Recertification
therefore restores a \(t_1\)-relative certificate or refuses to renew the old
release; it does not guarantee a non-empty release.
"""
    (OUT / "supplement_certificate_durability.tex").write_text(tex, encoding="utf-8")


def write_readme(frontier: pd.DataFrame) -> None:
    positive = bool(frontier["primary_success"].astype(bool).any())
    best = frontier.sort_values(["safe_seeds", "nonempty_seeds", "mean_release_size"], ascending=False).iloc[0]
    text = f"""# Phase66 Certificate Durability Frontier

Status: `completed_certificate_durability_frontier`.

This milestone makes version dependence explicit.  It reports a deterministic
version-shift accounting identity, a margin-buffer durability design diagnostic,
and a full predeclared K-sweep for queue-limited current-MP PARC-R
recertification.

Headline positive current-MP recertification allowed: `{str(positive).lower()}`.

Best observed K-sweep row by safe/non-empty seeds:

- K: `{int(best['K'])}`
- support mode: `{best['support_mode']}`
- non-empty seeds: `{int(best['nonempty_seeds'])}/20`
- safe seeds: `{int(best['safe_seeds'])}/20`
- mean release size: `{float(best['mean_release_size']):.3f}`
- mean t1 FTR if non-empty: `{best['mean_FTR_t1_if_nonempty']}`

Allowed claims:

- Version-shift accounting decomposes t1 burden into t0 error plus
  stable-to-unstable drift minus unstable-to-stable correction.
- Historical margin/drift tails provide a durability design diagnostic.
- The predeclared K-sweep tests whether current-MP recertification recovers a
  smaller release after high-K refusal.

Forbidden claims:

- no prospective materials discovery;
- no DFT evidence;
- no t1 alpha certificate for the old t0 release;
- no post-hoc K selection using observed t1 FTR;
- no future-drift guarantee from historical drift tails.
"""
    (OUT / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def write_figures(frontier: pd.DataFrame, margin: pd.DataFrame, drift_tail: pd.DataFrame) -> None:
    recert_rows: list[dict[str, object]] = []
    for _, row in frontier.iterrows():
        for metric in [
            "nonempty_seeds",
            "safe_seeds",
            "mean_release_size",
            "mean_FTR_t1_if_nonempty",
            "mean_raw_pool_FTR_t1",
            "evidence_mass_phi",
        ]:
            recert_rows.append(
                {
                    "panel": "recertification_K_sweep",
                    "K": int(row["K"]),
                    "support_mode": row["support_mode"],
                    "metric": metric,
                    "value": row[metric],
                    "alpha_reference_line": ALPHA,
                    "evidence_scope": SCOPE,
                }
            )
    pd.DataFrame(recert_rows).to_csv(OUT / "figure_recertification_frontier_inputs.csv", index=False)

    margin_rows: list[dict[str, object]] = []
    for _, row in margin.iterrows():
        margin_rows.append(
            {
                "panel": "released_margin_vs_t1_burden",
                "K": int(row["K"]),
                "support_mode": row["support_mode"],
                "x_margin": row["median_t0_margin"],
                "y_FTR_t1": row["FTR_t1_if_nonempty"],
                "point_size_release_size": row["mean_release_size"],
                "stable_to_unstable_drift_rate": row["stable_to_unstable_drift_rate"],
                "evidence_scope": SCOPE,
            }
        )
    for _, row in drift_tail.iterrows():
        margin_rows.append(
            {
                "panel": "historical_drift_tail",
                "K": "",
                "support_mode": "historical_t0_to_t1_queue_tail",
                "x_margin": row["margin_m_eV_atom"],
                "y_FTR_t1": row["alpha_plus_pi_hat"],
                "point_size_release_size": row["n_t0_stable_with_drift"],
                "stable_to_unstable_drift_rate": row["pi_hat"],
                "evidence_scope": SCOPE,
            }
        )
    pd.DataFrame(margin_rows).to_csv(OUT / "figure_margin_durability_frontier_inputs.csv", index=False)


def write_provenance(report: dict[str, object]) -> None:
    source = PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv"
    provenance = {
        "milestone": "ncs_phase66_certificate_durability",
        "status": report["status"],
        "K_grid": K_GRID,
        "support_modes": [mode for mode, _rho in SUPPORT_MODES],
        "n_seeds": len(SEEDS),
        "alpha": ALPHA,
        "source_table": {
            "path": rel(source),
            "sha256": sha256_file(source),
        },
        "evidence_scope": SCOPE,
        "headline_positive_current_MP_recertification_allowed": report["headline_positive_allowed"],
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upsert_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase66_certificate_durability",
        "path": rel(OUT) + "/",
        "evidence_state": "completed_certificate_durability_frontier_no_positive_current_MP_recertification",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase66_certificate_durability",
    }
    df = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=row.keys())
    df = df[df["milestone"] != row["milestone"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)


def append_once(path: Path, marker: str, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker not in existing:
        path.write_text(existing.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def update_ledger() -> None:
    ledger = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    df = pd.read_csv(ledger)
    ids = {"DUR-001", "DUR-002", "DUR-003", "DUR-004", "DUR-005"}
    df = df[~df["claim_id"].isin(ids)]
    rows = [
        {
            "claim_id": "DUR-001",
            "claim_text": "Version-shift accounting decomposes FTR_t1 into FTR_t0 plus stable-to-unstable drift minus unstable-to-stable correction.",
            "evidence_type": "deterministic_accounting_identity",
            "positive_evidence": "yes",
            "scope": "deterministic_accounting_identity_not_new_risk_control_theorem",
            "artifact_path": rel(OUT / "table_version_shift_decomposition_by_k.csv"),
            "hash": sha256_file(OUT / "table_version_shift_decomposition_by_k.csv"),
            "validation_command": "make reproduce-ncs-phase66-certificate-durability",
            "status": "PASS",
            "overclaim_guardrail": "do_not_present_as_deep_risk_control_theorem_or_t1_alpha_certificate",
        },
        {
            "claim_id": "DUR-002",
            "claim_text": "A t0 certificate inherited at t1 degrades by the released-set stable-to-unstable drift term.",
            "evidence_type": "inherited_certificate_decay_bound",
            "positive_evidence": "yes",
            "scope": "expectation_level_inherited_bound_requires_drift_term",
            "artifact_path": rel(OUT / "supplement_certificate_durability.tex"),
            "hash": sha256_file(OUT / "supplement_certificate_durability.tex"),
            "validation_command": "make reproduce-ncs-phase66-certificate-durability",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_prospective_t1_alpha_control_without_pre_update_drift_bound",
        },
        {
            "claim_id": "DUR-003",
            "claim_text": "A margin buffer converts historical reference drift into an operational durability design diagnostic.",
            "evidence_type": "margin_buffer_durability_diagnostic",
            "positive_evidence": "partial",
            "scope": "empirical_drift_calibrated_design_principle",
            "artifact_path": rel(OUT / "table_historical_drift_tail_by_margin.csv"),
            "hash": sha256_file(OUT / "table_historical_drift_tail_by_margin.csv"),
            "validation_command": "make reproduce-ncs-phase66-certificate-durability",
            "status": "PASS",
            "overclaim_guardrail": "historical_drift_tails_are_not_absolute_future_guarantees",
        },
        {
            "claim_id": "DUR-004",
            "claim_text": "t1 recertification restores a version-specific PARC certificate or returns certified refusal.",
            "evidence_type": "versioned_recertification_theorem_and_frontier",
            "positive_evidence": "partial",
            "scope": "relative_to_selected_t1_reference_not_absolute_physical_truth",
            "artifact_path": rel(OUT / "table_parc_r_k_sweep_gate_audit.csv"),
            "hash": sha256_file(OUT / "table_parc_r_k_sweep_gate_audit.csv"),
            "validation_command": "make reproduce-ncs-phase66-certificate-durability",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_absolute_truth_DFT_or_prospective_materials_discovery",
        },
        {
            "claim_id": "DUR-005",
            "claim_text": "The small-K PARC-R frontier tests whether current-MP recertification recovers a smaller release after high-volume refusal.",
            "evidence_type": "predeclared_K_sweep_recertification_frontier",
            "positive_evidence": "no",
            "scope": "completed_frontier_no_positive_current_MP_recertification_gate",
            "artifact_path": rel(OUT / "table_parc_r_k_sweep_frontier.csv"),
            "hash": sha256_file(OUT / "table_parc_r_k_sweep_frontier.csv"),
            "validation_command": "make reproduce-ncs-phase66-certificate-durability",
            "status": "PASS",
            "overclaim_guardrail": "report_all_K_values_do_not_select_K_by_post_release_FTR",
        },
    ]
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(ledger, index=False)


def patch_makefile() -> None:
    path = ROOT / "Makefile"
    text = path.read_text(encoding="utf-8")
    target = "reproduce-ncs-phase66-certificate-durability"
    if target not in text:
        text = text.replace(
            ".PHONY: test tiny-fixture",
            ".PHONY: test tiny-fixture " + target,
        )
        text = text.rstrip() + f"\n\n{target}:\n\t$(PYTHON) scripts/build_ncs_phase66_certificate_durability.py\n"
    validation_line = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase66_certificate_durability\n"
    if validation_line not in text:
        marker = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase64_parc_r_versioned_recertification\n"
        if marker in text:
            text = text.replace(marker, marker + validation_line)
    path.write_text(text, encoding="utf-8")


def update_docs(report: dict[str, object]) -> None:
    upsert_artifact_index()
    update_ledger()
    append_once(
        ROOT / "docs/claim_table.md",
        "## Phase66 Certificate Durability Frontier",
        f"""## Phase66 Certificate Durability Frontier

Status: `completed_certificate_durability_frontier_no_positive_current_MP_recertification`.

Phase66 adds supplement-ready versioned certificate durability statements and
runs a predeclared K sweep for current-MP PARC-R recertification over
K = {K_GRID}. The full grid is reported. The observed frontier does not satisfy
the constructive positive gate of non-empty alpha-safe release in at least 18/20
seeds. The allowed claim is therefore durability accounting, margin-drift
diagnostics, and versioned refusal/boundary behavior; it is not a positive
current-MP release result, not DFT evidence, and not prospective materials
discovery.""",
    )
    append_once(
        ROOT / "README.md",
        "NCS Phase66 certificate durability frontier",
        "- NCS Phase66 certificate durability frontier: version-shift accounting, margin-drift diagnostics, and a full K-grid current-MP PARC-R recertification sweep with no positive t1 release headline.",
    )
    append_once(
        ROOT / "REPRODUCIBILITY.md",
        "## NCS Phase66 Certificate Durability Frontier",
        """## NCS Phase66 Certificate Durability Frontier

Reproduce the supplement-ready durability accounting and current-MP
recertification K-sweep with:

```bash
make reproduce-ncs-phase66-certificate-durability
python scripts/validate_public_bundle.py outputs/milestones/ncs_phase66_certificate_durability
make validate-evidence-ledger
```

This milestone reports all predeclared K values. It must not be described as a
post-hoc small-K selection, a t1 alpha certificate for the old release, DFT
evidence, or prospective materials discovery.""",
    )
    patch_makefile()


def build_outputs() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    queue = load_queue()
    seed_rows: list[dict[str, object]] = []
    candidate_rows: list[pd.DataFrame] = []
    for support_mode, rho in SUPPORT_MODES:
        for k in K_GRID:
            for seed in SEEDS:
                row, candidate = run_seed(queue, k=k, seed=seed, support_mode=support_mode, rho=rho)
                seed_rows.append(row)
                if seed == 0:
                    candidate_rows.append(candidate)

    seed_df = pd.DataFrame(seed_rows)
    seed_df.to_csv(OUT / "table_parc_r_k_sweep_seed_rows.csv", index=False)
    frontier, gate, margin = summarize_frontier(seed_df)
    bootstrap = bootstrap_seed_metrics(seed_df)
    decomposition = build_version_shift_decomposition(seed_df)
    drift_tail = build_historical_drift_tail(queue)

    frontier.to_csv(OUT / "table_parc_r_k_sweep_frontier.csv", index=False)
    gate.to_csv(OUT / "table_parc_r_k_sweep_gate_audit.csv", index=False)
    bootstrap.to_csv(OUT / "table_parc_r_k_sweep_bootstrap.csv", index=False)
    decomposition.to_csv(OUT / "table_version_shift_decomposition_by_k.csv", index=False)
    margin.to_csv(OUT / "table_margin_frontier_by_k.csv", index=False)
    drift_tail.to_csv(OUT / "table_historical_drift_tail_by_margin.csv", index=False)

    candidate_df = pd.concat(candidate_rows, ignore_index=True)
    candidate_cols = [
        "candidate_id",
        "structure_hash",
        "formula",
        "chemical_system",
        "source_model",
        "raw_rank",
        "raw_score",
        "policy_status",
        "t0_e_above_hull",
        "t0_label",
        "t1_e_above_hull",
        "t1_label",
        "drift_type",
        "t0_margin",
        "hull_drift",
        "seed",
        "support_mode",
        "rho_t1_positive_support",
        "_recert_evalue",
        "selected_by_phase66_recertification",
        "evidence_scope",
    ]
    candidate_df[candidate_cols].to_csv(OUT / "table_parc_r_k_sweep_candidate_level_seed0.csv", index=False)

    write_supplement()
    write_figures(frontier, margin, drift_tail)
    write_readme(frontier)

    headline_positive = bool(frontier["primary_success"].astype(bool).any())
    report = {
        "status": "completed_certificate_durability_frontier",
        "out_dir": rel(OUT),
        "K_grid_rows": int(len(frontier)),
        "seed_rows": int(len(seed_df)),
        "support_modes": [mode for mode, _rho in SUPPORT_MODES],
        "headline_positive_allowed": headline_positive,
        "best_nonempty_seeds": int(frontier["nonempty_seeds"].max()),
        "best_safe_seeds": int(frontier["safe_seeds"].max()),
    }
    write_provenance(report)
    write_manifest(OUT)
    update_docs(report)
    write_manifest(OUT)
    write_root_manifest()
    return report


def main() -> None:
    report = build_outputs()
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
