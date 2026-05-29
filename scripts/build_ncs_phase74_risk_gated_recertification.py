#!/usr/bin/env python3
"""Build Phase74 risk-gated PARC-R recertification artifacts.

Phase69b showed that a post-filtered durability-risk subset did not inherit
PARC self-consistency. Phase74 moves the risk rule upstream: it defines a
filtered candidate universe before recertification, rebuilds the calibration
null superset inside that universe, recomputes e-values and reruns SCS.

The point of this milestone is not to rescue a claim at any cost. It tests the
constructive route directly. If filtered-universe recertification still refuses,
PARC-D remains a risk-triage module rather than a current-MP alpha certificate.
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
PHASE69 = ROOT / "outputs/milestones/ncs_phase69_durability_budgeted_parc"
OUT = ROOT / "outputs/milestones/ncs_phase74_risk_gated_recertification"

ALPHA = 0.10
SEEDS = list(range(20))
K_GRID = [20, 50, 75, 100, 150, 200, 300, 500]
RETAIN_FRACTIONS = [0.20, 0.30, 0.40, 0.50]
SUPPORT_MODES = [
    ("t1_10pct_support", 0.10),
    ("t1_full_calibration_block_support", 1.00),
]
PRIMARY_RISK_MODEL = "system_margin_distribution"
PRIMARY_K = 300
PRIMARY_RETAIN = 0.40
N_BOOTSTRAP = 1000
SCOPE = (
    "risk_gated_filtered_universe_recertification;"
    "risk_gate_before_PARC;"
    "recomputed_nullsuperset_after_filter;"
    "recomputed_evalues_after_filter;"
    "K_eff_used_in_SCS_threshold;"
    "t0_public_label_risk_features_not_label_free;"
    "queue_limited_current_MP_t1_recertification;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
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
    queue["raw_rank"] = pd.to_numeric(queue["raw_rank"], errors="coerce")
    return queue


def attach_risk_scores(queue: pd.DataFrame) -> pd.DataFrame:
    scores = pd.read_csv(PHASE69 / "table_crossfit_durability_risk_scores.csv")
    scores = scores[scores["risk_model"].eq(PRIMARY_RISK_MODEL)].copy()
    # The Phase69 risk signal is system-level.  Use the cross-fitted mean score
    # for each chemical system and apply it to every candidate from that system.
    system_risk = scores.groupby("chemical_system", sort=False)["crossfit_durability_risk"].mean()
    out = queue.copy()
    out["risk_model"] = PRIMARY_RISK_MODEL
    out["crossfit_system_durability_risk"] = out["chemical_system"].map(system_risk)
    out["risk_score_available"] = out["crossfit_system_durability_risk"].notna()
    return out


def filtered_frame(queue: pd.DataFrame, *, k_original: int, retain_fraction: float) -> tuple[pd.DataFrame, dict[str, object]]:
    base = queue[queue["raw_rank"].le(k_original) & queue["risk_score_available"]].copy()
    threshold = float(base["crossfit_system_durability_risk"].quantile(retain_fraction)) if len(base) else math.nan
    filtered = queue[
        queue["risk_score_available"] & queue["crossfit_system_durability_risk"].le(threshold)
    ].copy()
    # Ties in the queue rank can make the count of rows with raw_rank <= K
    # exceed K.  The release budget is still capped by the requested K.
    k_eff = int(min(k_original, filtered["raw_rank"].le(k_original).sum()))
    return filtered, {
        "K_original": int(k_original),
        "retain_fraction": float(retain_fraction),
        "risk_model": PRIMARY_RISK_MODEL,
        "risk_threshold": threshold,
        "full_queue_n": int(len(queue)),
        "risk_score_available_n": int(queue["risk_score_available"].sum()),
        "risk_score_missing_n": int((~queue["risk_score_available"]).sum()),
        "filtered_universe_n": int(len(filtered)),
        "filtered_chemical_systems": int(filtered["chemical_system"].nunique()),
        "K_eff": k_eff,
        "filter_stage": "pre_PARC_before_calibration_split",
        "threshold_source": "risk_score_quantile_only_no_t1_labels",
        "denominator_recomputed_after_filter": True,
        "evidence_scope": SCOPE,
    }


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
        followup["_risk_gated_evalue"] = np.zeros(len(followup), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = followup["score_for_recertification"].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        followup["_risk_gated_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return followup, {
        "calibration_blocks": int(len(cal_blocks)),
        "followup_blocks": int(len(followup_blocks)),
        "nonempty_calibration_null_blocks": int(len(maxima)),
        "block_coverage": float(len(maxima) / len(cal_blocks)) if cal_blocks else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma if gamma is not None else math.nan,
        "denominator_recomputed_after_filter": True,
    }


def run_seed(
    frame: pd.DataFrame,
    *,
    k_original: int,
    k_eff: int,
    retain_fraction: float,
    support_mode: str,
    rho: float,
    seed: int,
) -> tuple[dict[str, object], dict[str, object]]:
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
    pool = followup.head(k_eff).copy()
    released, tau, scs_margin, evidence_mass = scs_release_count(
        pool["_risk_gated_evalue"].to_numpy(dtype=float), alpha=ALPHA, budget=k_eff
    )
    if released:
        selected = pool.iloc[np.argsort(pool["_risk_gated_evalue"].to_numpy(dtype=float))[::-1][:released]].copy()
        ftr_t1 = float((~selected["t1_stable"].astype(bool)).mean())
        false_t1 = int((~selected["t1_stable"].astype(bool)).sum())
        ftr_t0 = float((~selected["t0_stable"].astype(bool)).mean())
        decision = "risk_gated_current_MP_release" if ftr_t1 <= ALPHA else "risk_gated_boundary_release"
    else:
        selected = pool.iloc[[]].copy()
        ftr_t1 = math.nan
        false_t1 = 0
        ftr_t0 = math.nan
        decision = "risk_gated_certified_refusal"
    required_evalue = k_eff / (ALPHA * released) if released else math.inf
    row = {
        "risk_model": PRIMARY_RISK_MODEL,
        "K_original": int(k_original),
        "K_eff": int(k_eff),
        "alpha": ALPHA,
        "retain_fraction": float(retain_fraction),
        "support_mode": support_mode,
        "rho_t1_positive_support": rho,
        "seed": int(seed),
        "decision": decision,
        "release_size": int(released),
        "release_false_t1": false_t1,
        "release_FTR_t1": ftr_t1,
        "release_FTR_t0": ftr_t0,
        "safe_release_t1": bool(released > 0 and ftr_t1 <= ALPHA),
        "raw_pool_size": int(len(pool)),
        "raw_pool_FTR_t1": float((~pool["t1_stable"].astype(bool)).mean()) if len(pool) else math.nan,
        "observed_t1_positives": int(observed.sum()),
        "t1_stable_eligible_in_calibration": int(len(eligible)),
        "max_evalue": float(pool["_risk_gated_evalue"].max()) if len(pool) else 0.0,
        "required_evalue_threshold": required_evalue,
        "self_consistency_margin": scs_margin,
        "evidence_mass": evidence_mass,
        "self_consistency_pass": bool(released > 0 and scs_margin >= 0),
        "risk_gate_uses_t1_labels": False,
        "heldout_t1_used_for_selection": False,
        "filter_stage": "pre_PARC_before_calibration_split",
        "evidence_scope": SCOPE,
        **diag,
    }
    diag_row = {
        "risk_model": PRIMARY_RISK_MODEL,
        "K_original": int(k_original),
        "K_eff": int(k_eff),
        "retain_fraction": float(retain_fraction),
        "support_mode": support_mode,
        "seed": int(seed),
        "calibration_blocks": diag["calibration_blocks"],
        "followup_blocks": diag["followup_blocks"],
        "nonempty_calibration_null_blocks": diag["nonempty_calibration_null_blocks"],
        "block_coverage": diag["block_coverage"],
        "p_min_effective": diag["p_min_effective"],
        "gamma": diag["gamma"],
        "observed_t1_positives": int(observed.sum()),
        "denominator_recomputed_after_filter": True,
        "evalues_recomputed_after_filter": True,
        "evidence_scope": SCOPE,
    }
    return row, diag_row


def aggregate_grid(seed_rows: pd.DataFrame, universe_rows: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for key, group in seed_rows.groupby(["risk_model", "K_original", "retain_fraction", "support_mode"], sort=True):
        risk_model, k_original, retain_fraction, support_mode = key
        universe = universe_rows[
            universe_rows["K_original"].eq(k_original)
            & universe_rows["retain_fraction"].eq(retain_fraction)
            & universe_rows["risk_model"].eq(risk_model)
        ].iloc[0]
        nonempty = int(group["release_size"].gt(0).sum())
        safe = int(group["safe_release_t1"].astype(bool).sum())
        nonempty_ftr = group.loc[group["release_size"].gt(0), "release_FTR_t1"].astype(float)
        mean_ftr = float(nonempty_ftr.mean()) if len(nonempty_ftr) else math.nan
        rows.append(
            {
                "risk_model": risk_model,
                "K_original": int(k_original),
                "K_eff": int(universe["K_eff"]),
                "alpha": ALPHA,
                "retain_fraction": float(retain_fraction),
                "support_mode": support_mode,
                "filtered_universe_n": int(universe["filtered_universe_n"]),
                "filtered_chemical_systems": int(universe["filtered_chemical_systems"]),
                "n_seeds": int(group["seed"].nunique()),
                "nonempty_seeds": nonempty,
                "safe_seeds": safe,
                "mean_release_size": float(group["release_size"].astype(float).mean()),
                "median_release_size": float(group["release_size"].astype(float).median()),
                "max_release_size": int(group["release_size"].astype(int).max()),
                "mean_FTR_t1_if_nonempty": mean_ftr,
                "mean_raw_pool_FTR_t1": float(group["raw_pool_FTR_t1"].astype(float).mean()),
                "mean_max_evalue": float(group["max_evalue"].astype(float).mean()),
                "mean_required_evalue_threshold_if_released": float(
                    group.loc[group["release_size"].gt(0), "required_evalue_threshold"].astype(float).mean()
                )
                if nonempty
                else math.nan,
                "mean_evidence_mass": float(group["evidence_mass"].astype(float).mean()),
                "mean_self_consistency_margin": float(group["self_consistency_margin"].astype(float).mean()),
                "self_consistency_pass_any_seed": bool(group["self_consistency_pass"].astype(bool).any()),
                "go_strong": bool(nonempty == group["seed"].nunique() and safe >= 18 and mean_ftr <= ALPHA and group["release_size"].mean() >= 50),
                "go_medium": bool(nonempty == group["seed"].nunique() and safe >= 15 and (math.isfinite(mean_ftr) and mean_ftr <= 0.15)),
                "claim_status": "constructive_positive"
                if bool(nonempty == group["seed"].nunique() and safe >= 18 and mean_ftr <= ALPHA and group["release_size"].mean() >= 50)
                else "risk_gated_recertification_refusal_no_go",
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def bootstrap_ci(seed_rows: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(74)
    rows: list[dict[str, object]] = []
    for key, group in seed_rows.groupby(["risk_model", "K_original", "retain_fraction", "support_mode"], sort=True):
        risk_model, k_original, retain_fraction, support_mode = key
        systems = sorted(set(group["seed"].astype(int)))
        release_sizes = group["release_size"].astype(float).to_numpy()
        ftr_empty_zero = np.where(group["release_size"].to_numpy() > 0, group["release_FTR_t1"].fillna(0).to_numpy(), 0.0)
        if len(release_sizes) == 0:
            continue
        means_release = []
        means_ftr = []
        for _ in range(N_BOOTSTRAP):
            idx = rng.integers(0, len(release_sizes), size=len(release_sizes))
            means_release.append(float(np.mean(release_sizes[idx])))
            means_ftr.append(float(np.mean(ftr_empty_zero[idx])))
        rows.append(
            {
                "risk_model": risk_model,
                "K_original": int(k_original),
                "retain_fraction": float(retain_fraction),
                "support_mode": support_mode,
                "metric": "mean_release_size",
                "estimate": float(np.mean(release_sizes)),
                "ci_low_95": float(np.percentile(means_release, 2.5)),
                "ci_high_95": float(np.percentile(means_release, 97.5)),
                "bootstrap_unit": "seed",
                "n_bootstrap": N_BOOTSTRAP,
                "evidence_scope": SCOPE,
            }
        )
        rows.append(
            {
                "risk_model": risk_model,
                "K_original": int(k_original),
                "retain_fraction": float(retain_fraction),
                "support_mode": support_mode,
                "metric": "mean_FTR_t1_decision_empty_zero",
                "estimate": float(np.mean(ftr_empty_zero)),
                "ci_low_95": float(np.percentile(means_ftr, 2.5)),
                "ci_high_95": float(np.percentile(means_ftr, 97.5)),
                "bootstrap_unit": "seed",
                "n_bootstrap": N_BOOTSTRAP,
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def primary_row(grid: pd.DataFrame) -> pd.DataFrame:
    prior = grid[
        grid["risk_model"].eq(PRIMARY_RISK_MODEL)
        & grid["K_original"].eq(PRIMARY_K)
        & grid["retain_fraction"].eq(PRIMARY_RETAIN)
        & grid["support_mode"].eq("t1_10pct_support")
    ]
    if len(prior):
        selected = prior.iloc[0]
    else:
        selected = grid.sort_values(["go_strong", "go_medium", "nonempty_seeds", "mean_release_size"], ascending=[False, False, False, False]).iloc[0]
    return pd.DataFrame(
        [
            {
                "selection_rule_id": "PHASE74_PRIOR_ROW_FROM_PHASE69B",
                "selection_rule": "evaluate_K300_retain40_system_margin_distribution_t1_10pct_support_then_report_full_grid",
                "uses_heldout_t1_for_selection": False,
                "risk_model": selected["risk_model"],
                "K_original": int(selected["K_original"]),
                "K_eff": int(selected["K_eff"]),
                "retain_fraction": float(selected["retain_fraction"]),
                "support_mode": selected["support_mode"],
                "nonempty_seeds": int(selected["nonempty_seeds"]),
                "safe_seeds": int(selected["safe_seeds"]),
                "mean_release_size": float(selected["mean_release_size"]),
                "mean_FTR_t1_if_nonempty": float(selected["mean_FTR_t1_if_nonempty"])
                if math.isfinite(float(selected["mean_FTR_t1_if_nonempty"]))
                else math.nan,
                "self_consistency_pass_any_seed": bool(selected["self_consistency_pass_any_seed"]),
                "claim_supported": bool(selected["go_strong"]),
                "paper_role": "failed_gate_supplementary_diagnostic"
                if not bool(selected["go_strong"])
                else "main_text_constructive_recertification_positive",
                "guardrail": "risk_gated_recertification_no_go_if_all_rows_refuse;do_not_claim_alpha_certificate_without_nonempty_self_consistent_release",
                "evidence_scope": SCOPE,
            }
        ]
    )


def write_text(primary: pd.DataFrame, grid: pd.DataFrame) -> None:
    row = primary.iloc[0]
    any_positive = bool(grid["go_strong"].any())
    readme = f"""# Phase74 Risk-Gated PARC-R Recertification

Status: `completed_risk_gated_recertification_no_go`.

Phase74 moves the Phase69/69b durability-risk rule upstream. The low-risk gate
is applied before PARC-R recertification; the calibration null superset,
e-values and SCS threshold are rebuilt inside the filtered universe.

Primary prior row:

- risk model: `{row['risk_model']}`
- K original: `{int(row['K_original'])}`
- K effective after risk gate: `{int(row['K_eff'])}`
- retain fraction: `{row['retain_fraction']}`
- support mode: `{row['support_mode']}`
- non-empty seeds: `{int(row['nonempty_seeds'])}/20`
- any self-consistent release: `{str(bool(row['self_consistency_pass_any_seed'])).lower()}`

Full-grid constructive positive: `{str(any_positive).lower()}`.

Interpretation:

The constructive rescue route does not pass.  Once the risk gate is moved
upstream and the null-superset denominator is recomputed, the low-risk universe
does not produce a non-empty self-consistent current-MP release on the
predeclared grid. PARC-D therefore remains a release-card risk-triage module,
not a current-MP alpha certificate.

Guardrails:

- risk gate is pre-PARC and uses no held-out t1 labels for thresholding;
- denominator and e-values are recomputed after filtering;
- no DFT evidence;
- no prospective materials discovery;
- no full current-MP alpha certificate.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase74_risk_gated_recertification"]
    rows.append(
        {
            "milestone": "ncs_phase74_risk_gated_recertification",
            "path": "outputs/milestones/ncs_phase74_risk_gated_recertification/",
            "evidence_state": "completed_risk_gated_recertification_no_go",
            "manifest": "outputs/milestones/ncs_phase74_risk_gated_recertification/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase74_risk_gated_recertification",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["milestone", "path", "evidence_state", "manifest", "public_bundle_check"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def update_claim_table(primary: pd.DataFrame) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase74 Risk-Gated Recertification"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    row = primary.iloc[0]
    addition = f"""

## Phase74 Risk-Gated Recertification

Status: `completed_risk_gated_recertification_no_go`.

Phase74 tests the strongest constructive follow-up to Phase69b: move the
durability-risk gate upstream, rebuild the filtered null-superset denominator,
recompute e-values and rerun SCS. The primary prior row
(`K={int(row['K_original'])}`, retain fraction `{row['retain_fraction']}`,
support `{row['support_mode']}`) returns `{int(row['nonempty_seeds'])}/20`
non-empty seeds. The full grid does not recover a non-empty self-consistent
current-MP release certificate. The allowed claim is therefore a principled
no-go for risk-gated recertification on the queue-limited current-MP audit; it
does not supersede Phase69b risk triage.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(primary: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if not row["claim_id"].startswith("PARC-D-CERT-")]
    artifact = OUT / "table_risk_gated_primary_row.csv"
    rows.append(
        {
            "claim_id": "PARC-D-CERT-001",
            "claim_text": "Risk-gated filtered-universe recertification recomputes the null-superset denominator but does not recover a current-MP release certificate.",
            "evidence_type": "risk_gated_recertification",
            "positive_evidence": "no",
            "scope": "completed_no_go_risk_gated_recertification",
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase74-risk-gated-recertification",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_alpha_certificate_DFT_or_prospective_discovery",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
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
    OUT.mkdir(parents=True, exist_ok=True)
    queue = attach_risk_scores(load_queue())
    universe_rows: list[dict[str, object]] = []
    seed_rows: list[dict[str, object]] = []
    null_rows: list[dict[str, object]] = []
    for k_original in K_GRID:
        for retain_fraction in RETAIN_FRACTIONS:
            frame, universe = filtered_frame(queue, k_original=k_original, retain_fraction=retain_fraction)
            universe_rows.append(universe)
            if int(universe["K_eff"]) <= 0 or frame.empty:
                continue
            for support_mode, rho in SUPPORT_MODES:
                for seed in SEEDS:
                    seed_row, null_row = run_seed(
                        frame,
                        k_original=k_original,
                        k_eff=int(universe["K_eff"]),
                        retain_fraction=retain_fraction,
                        support_mode=support_mode,
                        rho=rho,
                        seed=seed,
                    )
                    seed_rows.append(seed_row)
                    null_rows.append(null_row)

    universe_df = pd.DataFrame(universe_rows)
    seed_df = pd.DataFrame(seed_rows)
    null_df = pd.DataFrame(null_rows)
    grid = aggregate_grid(seed_df, universe_df)
    boot = bootstrap_ci(seed_df)
    primary = primary_row(grid)
    figure = pd.concat(
        [
            universe_df.assign(panel="filtered_universe"),
            null_df.assign(panel="recomputed_nullsuperset"),
            seed_df.assign(panel="seed_scs_results"),
            grid.assign(panel="full_grid"),
        ],
        ignore_index=True,
        sort=False,
    )

    universe_df.to_csv(OUT / "table_risk_gated_filtered_universe.csv", index=False)
    null_df.to_csv(OUT / "table_risk_gated_nullsuperset_recomputed.csv", index=False)
    seed_df.to_csv(OUT / "table_risk_gated_scs_results.csv", index=False)
    grid.to_csv(OUT / "table_risk_gated_full_grid.csv", index=False)
    primary.to_csv(OUT / "table_risk_gated_primary_row.csv", index=False)
    boot.to_csv(OUT / "table_risk_gated_bootstrap_ci.csv", index=False)
    figure.to_csv(OUT / "figure_risk_gated_recertification_inputs.csv", index=False)
    write_text(primary, grid)

    provenance = {
        "status": "completed_risk_gated_recertification_no_go",
        "source_phase51": rel(PHASE51),
        "source_phase69": rel(PHASE69),
        "source_phase69_manifest_sha256": sha256_file(PHASE69 / "MANIFEST_SHA256.txt"),
        "risk_model": PRIMARY_RISK_MODEL,
        "K_grid": K_GRID,
        "retain_fraction_grid": RETAIN_FRACTIONS,
        "support_modes": [mode for mode, _ in SUPPORT_MODES],
        "any_constructive_positive": bool(grid["go_strong"].any()),
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    update_artifact_index()
    update_claim_table(primary)
    update_evidence_ledger(primary)
    write_manifest(OUT)
    write_root_manifest()
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
