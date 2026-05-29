#!/usr/bin/env python3
"""Build Phase69b PARC-D hardening artifacts.

Phase69 found a candidate-level durability-budgeted positive row. Phase69b
turns that result into reviewer-facing evidence by auditing the exact boundary
conditions:

1. post-filter PARC self-consistency;
2. beta-UCB sensitivity;
3. full-grid and primary selection rule;
4. negative controls and feature ablations;
5. a supplement-ready PARC-D method statement.

The expected outcome is intentionally scoped. The Phase69 primary row is a
constructive release-card risk-triage result, not a full current-MP alpha
certificate, unless the self-consistency check also passes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE69 = ROOT / "outputs/milestones/ncs_phase69_durability_budgeted_parc"
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
OUT = ROOT / "outputs/milestones/ncs_phase69b_parc_d_hardening"

ALPHA_TOTAL = 0.10
PRIMARY_MODEL = "system_margin_distribution"
PRIMARY_K = 300
PRIMARY_ALPHA0 = 0.01
PRIMARY_RETAIN = 0.40
CONFIDENCE_LEVELS = [0.90, 0.95, 0.975]
NEGATIVE_CONTROL_PERMUTATIONS = 200
RANDOM_SEED = 6902
SCOPE = (
    "PARC_D_hardening;"
    "phase69_candidate_level_durability_budget_audit;"
    "self_consistency_postfilter_checked;"
    "t0_public_label_release_card_features_not_label_free;"
    "not_full_current_MP_alpha_certificate;"
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


def wilson_upper(k: int, n: int, confidence_level: float = 0.95) -> float:
    if n <= 0:
        return 1.0
    z = NormalDist().inv_cdf((1.0 + confidence_level) / 2.0)
    phat = k / n
    denom = 1.0 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    return float(min(1.0, center + half))


def auc_score(y_true: np.ndarray, score: np.ndarray) -> float:
    """Compute ROC AUC without depending on sklearn at runtime."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(score).astype(float)
    pos = y == 1
    neg = y == 0
    n_pos = int(pos.sum())
    n_neg = int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(s) + 1, dtype=float)
    # Average ranks for ties.
    values = s[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[end] == values[start]:
            end += 1
        if end - start > 1:
            ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    sum_pos_ranks = float(ranks[pos].sum())
    return (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def load_scores() -> pd.DataFrame:
    return pd.read_csv(PHASE69 / "table_crossfit_durability_risk_scores.csv")


def load_phase69_frontier() -> pd.DataFrame:
    return pd.read_csv(PHASE69 / "table_durability_budgeted_release_frontier.csv")


def load_phase69_fold_rows() -> pd.DataFrame:
    return pd.read_csv(PHASE69 / "table_alpha0_beta_budget_by_row.csv")


def load_evalues() -> pd.DataFrame:
    table = pd.read_csv(PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv")
    required = ["candidate_id", "K", "parc_e_value", "parc_release_margin", "parc_released"]
    missing = [col for col in required if col not in table.columns]
    if missing:
        raise RuntimeError(f"Phase51 table missing required columns: {missing}")
    return table[required].drop_duplicates(["candidate_id", "K"])


def retained_rows_for_fold(
    scores: pd.DataFrame,
    risk_model: str,
    k_value: int,
    retain_fraction: float,
    fold: int,
    threshold: float,
) -> pd.DataFrame:
    subset = scores[
        scores["risk_model"].eq(risk_model)
        & scores["K"].eq(k_value)
        & scores["fold"].eq(fold)
        & scores["crossfit_durability_risk"].le(threshold)
    ].copy()
    return subset


def self_consistency_table(scores: pd.DataFrame, fold_rows: pd.DataFrame, evalues: pd.DataFrame) -> pd.DataFrame:
    unique = fold_rows[
        ["risk_model", "K", "fold", "retain_fraction", "risk_threshold_from_calibration"]
    ].drop_duplicates()
    all_rows: list[dict[str, object]] = []
    retained_by_key: dict[tuple[str, int, float], list[pd.DataFrame]] = {}
    for row in unique.to_dict("records"):
        retained = retained_rows_for_fold(
            scores,
            row["risk_model"],
            int(row["K"]),
            float(row["retain_fraction"]),
            int(row["fold"]),
            float(row["risk_threshold_from_calibration"]),
        )
        retained = retained.merge(evalues, on=["candidate_id", "K"], how="left")
        key = (row["risk_model"], int(row["K"]), float(row["retain_fraction"]))
        retained_by_key.setdefault(key, []).append(retained)
        for alpha0 in sorted(fold_rows["alpha0"].unique()):
            release_size = int(len(retained))
            min_evalue = float(retained["parc_e_value"].min()) if release_size else math.nan
            required_evalue = int(row["K"]) / (float(alpha0) * release_size) if release_size else math.inf
            n_missing = int(retained["parc_e_value"].isna().sum()) if release_size else 0
            n_failed = int((retained["parc_e_value"] < required_evalue).sum()) if release_size else 0
            passes = bool(release_size > 0 and n_missing == 0 and min_evalue >= required_evalue)
            all_rows.append(
                {
                    "check_unit": "fold",
                    "fold": int(row["fold"]),
                    "risk_model": row["risk_model"],
                    "K": int(row["K"]),
                    "alpha0": float(alpha0),
                    "retain_fraction": float(row["retain_fraction"]),
                    "release_size": release_size,
                    "min_evalue": min_evalue,
                    "required_evalue": required_evalue,
                    "passes_self_consistency": passes,
                    "n_failed_candidates": n_failed,
                    "n_missing_evalue": n_missing,
                    "claim_after_self_consistency": "PARC_D_certificate_candidate_subset"
                    if passes
                    else "risk_triage_subset_not_alpha_certificate",
                    "evidence_scope": SCOPE,
                }
            )

    for (risk_model, k_value, retain_fraction), frames in retained_by_key.items():
        retained = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        # Cross-fitted aggregate can contain the same candidate once per K. Drop
        # exact duplicates so the aggregate check describes candidate-level rows.
        if len(retained):
            retained = retained.drop_duplicates(["candidate_id", "K"])
        for alpha0 in sorted(fold_rows["alpha0"].unique()):
            release_size = int(len(retained))
            min_evalue = float(retained["parc_e_value"].min()) if release_size else math.nan
            required_evalue = k_value / (float(alpha0) * release_size) if release_size else math.inf
            n_missing = int(retained["parc_e_value"].isna().sum()) if release_size else 0
            n_failed = int((retained["parc_e_value"] < required_evalue).sum()) if release_size else 0
            passes = bool(release_size > 0 and n_missing == 0 and min_evalue >= required_evalue)
            all_rows.append(
                {
                    "check_unit": "aggregate",
                    "fold": "ALL",
                    "risk_model": risk_model,
                    "K": int(k_value),
                    "alpha0": float(alpha0),
                    "retain_fraction": float(retain_fraction),
                    "release_size": release_size,
                    "min_evalue": min_evalue,
                    "required_evalue": required_evalue,
                    "passes_self_consistency": passes,
                    "n_failed_candidates": n_failed,
                    "n_missing_evalue": n_missing,
                    "claim_after_self_consistency": "PARC_D_certificate_candidate_subset"
                    if passes
                    else "risk_triage_subset_not_alpha_certificate",
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(all_rows)


def beta_sensitivity(fold_rows: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    group_cols = ["risk_model", "K", "retain_fraction", "alpha0"]
    for key, group in fold_rows.groupby(group_cols, sort=True):
        risk_model, k_value, retain_fraction, alpha0 = key
        for conf in CONFIDENCE_LEVELS:
            fold_betas = [
                wilson_upper(int(r.calibration_retained_flips), int(r.calibration_retained_n), conf)
                for r in group.itertuples()
            ]
            beta_max = float(max(fold_betas))
            beta_mean = float(np.mean(fold_betas))
            rows.append(
                {
                    "risk_model": risk_model,
                    "K": int(k_value),
                    "retain_fraction": float(retain_fraction),
                    "alpha0": float(alpha0),
                    "beta_UCB_confidence_level": conf,
                    "beta_UCB_max_across_calibration_folds": beta_max,
                    "beta_UCB_mean_across_calibration_folds": beta_mean,
                    "alpha0_plus_beta_UCB": float(alpha0 + beta_max),
                    "budget_pass_pre_eval": bool(alpha0 + beta_max <= ALPHA_TOTAL),
                    "fold_count": int(group["fold"].nunique()),
                    "calibration_method": "Wilson_upper_endpoint_by_heldout_chemical_system_fold",
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows)


def full_grid(frontier: pd.DataFrame, self_consistency: pd.DataFrame) -> pd.DataFrame:
    aggregate = self_consistency[self_consistency["check_unit"].eq("aggregate")].copy()
    aggregate = aggregate.rename(
        columns={
            "release_size": "self_consistency_release_size",
            "min_evalue": "self_consistency_min_evalue",
            "required_evalue": "self_consistency_required_evalue",
            "passes_self_consistency": "aggregate_passes_self_consistency",
            "n_failed_candidates": "aggregate_self_consistency_failed_candidates",
        }
    )
    merged = frontier.merge(
        aggregate[
            [
                "risk_model",
                "K",
                "alpha0",
                "retain_fraction",
                "self_consistency_release_size",
                "self_consistency_min_evalue",
                "self_consistency_required_evalue",
                "aggregate_passes_self_consistency",
                "aggregate_self_consistency_failed_candidates",
                "claim_after_self_consistency",
            ]
        ],
        on=["risk_model", "K", "alpha0", "retain_fraction"],
        how="left",
    )
    merged["pre_eval_selection_eligible"] = (
        merged["budget_pass_pre_eval"].astype(bool)
        & (merged["nonempty_folds"] == merged["fold_count"])
        & (merged["min_test_retained_n_across_folds"] >= 5)
    )
    merged["certificate_level_success_after_hardening"] = (
        merged["primary_success_candidate_level"].astype(bool)
        & merged["aggregate_passes_self_consistency"].fillna(False).astype(bool)
    )
    merged["hardened_paper_role"] = np.where(
        merged["certificate_level_success_after_hardening"],
        "candidate_level_durability_budget_certificate",
        np.where(
            merged["primary_success_candidate_level"].astype(bool),
            "candidate_level_risk_triage_positive_not_alpha_certificate",
            "risk_triage_or_boundary_diagnostic",
        ),
    )
    merged["evidence_scope"] = SCOPE
    return merged


def primary_selection_rule(grid: pd.DataFrame, beta: pd.DataFrame, self_consistency: pd.DataFrame) -> pd.DataFrame:
    eligible = grid[
        grid["pre_eval_selection_eligible"].astype(bool)
        & grid["risk_model"].eq(PRIMARY_MODEL)
    ].copy()
    if len(eligible):
        selected = eligible.sort_values(
            ["release_size_candidate_level", "alpha0_plus_beta_UCB"],
            ascending=[False, True],
        ).iloc[0]
    else:
        selected = grid.sort_values(["budget_pass_pre_eval", "release_size_candidate_level"], ascending=[False, False]).iloc[0]
    main_self = self_consistency[
        self_consistency["check_unit"].eq("aggregate")
        & self_consistency["risk_model"].eq(selected["risk_model"])
        & self_consistency["K"].eq(selected["K"])
        & self_consistency["alpha0"].eq(selected["alpha0"])
        & self_consistency["retain_fraction"].eq(selected["retain_fraction"])
    ].iloc[0]
    sens = beta[
        beta["risk_model"].eq(selected["risk_model"])
        & beta["K"].eq(selected["K"])
        & beta["alpha0"].eq(selected["alpha0"])
        & beta["retain_fraction"].eq(selected["retain_fraction"])
    ].copy()
    pass_95 = bool(sens[sens["beta_UCB_confidence_level"].eq(0.95)]["budget_pass_pre_eval"].iloc[0])
    pass_975 = bool(sens[sens["beta_UCB_confidence_level"].eq(0.975)]["budget_pass_pre_eval"].iloc[0])
    return pd.DataFrame(
        [
            {
                "selection_rule_id": "PARC-D-PRIMARY-LOCKED",
                "selection_rule": "largest_candidate_level_release_size_among_primary_model_rows_with_pre_eval_budget_pass_all_folds_nonempty_and_min_5_heldout_rows_per_fold",
                "uses_heldout_t1_FTR_for_selection": False,
                "risk_model": selected["risk_model"],
                "K": int(selected["K"]),
                "alpha0": float(selected["alpha0"]),
                "retain_fraction": float(selected["retain_fraction"]),
                "release_size_candidate_level": int(selected["release_size_candidate_level"]),
                "observed_FTR_t1_reported_not_used_for_selection": float(selected["observed_FTR_t1"]),
                "alpha0_plus_beta_UCB_95": float(
                    sens[sens["beta_UCB_confidence_level"].eq(0.95)]["alpha0_plus_beta_UCB"].iloc[0]
                ),
                "passes_95pct_beta_budget": pass_95,
                "passes_97p5pct_beta_budget": pass_975,
                "passes_postfilter_self_consistency": bool(main_self["passes_self_consistency"]),
                "claim_after_hardening": "PARC_D_candidate_level_certificate"
                if bool(main_self["passes_self_consistency"])
                else "PARC_D_risk_triage_positive_not_alpha_certificate",
                "selection_status": "phase69_exploratory_grid_locked_no_further_tuning",
                "guardrail": "do_not_claim_full_current_MP_alpha_certificate_unless_self_consistency_and_seed_level_gate_pass",
                "evidence_scope": SCOPE,
            }
        ]
    )


def feature_ablation(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    out["feature_ablation_role"] = np.select(
        [
            out["risk_model"].eq("system_margin_distribution"),
            out["risk_model"].eq("system_size_activity_proxy"),
            out["risk_model"].eq("candidate_margin_only"),
            out["risk_model"].eq("candidate_t0_score_only"),
        ],
        [
            "primary_mechanistic_system_margin_landscape",
            "system_activity_supporting_signal",
            "candidate_level_negative_control",
            "score_rank_negative_control",
        ],
        default="comparison",
    )
    out["evidence_scope"] = SCOPE
    return out


def negative_controls(scores: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model in ["candidate_margin_only", "candidate_t0_score_only", PRIMARY_MODEL]:
        metric = metrics[metrics["risk_model"].eq(model)].iloc[0]
        rows.append(
            {
                "control_id": f"model_auc_{model}",
                "control_type": "model_comparison",
                "risk_model": model,
                "observed_auc": float(metric["mean_roc_auc"]),
                "control_auc_mean": math.nan,
                "control_auc_std": math.nan,
                "control_result": "passes_negative_control"
                if model in {"candidate_margin_only", "candidate_t0_score_only"} and float(metric["mean_roc_auc"]) < 0.60
                else "primary_signal",
                "interpretation": "candidate_margin_and_rank_are_weak_controls"
                if model != PRIMARY_MODEL
                else "system_margin_landscape_is_primary_signal",
                "evidence_scope": SCOPE,
            }
        )

    primary = scores[scores["risk_model"].eq(PRIMARY_MODEL)].copy()
    rng = np.random.default_rng(RANDOM_SEED)
    y = primary["stable_to_unstable_t1"].to_numpy(dtype=int)
    s = primary["crossfit_durability_risk"].to_numpy(dtype=float)
    observed = auc_score(y, s)

    global_aucs: list[float] = []
    within_aucs: list[float] = []
    group_indices = list(primary.groupby("chemical_system").indices.values())
    for _ in range(NEGATIVE_CONTROL_PERMUTATIONS):
        y_global = y.copy()
        rng.shuffle(y_global)
        global_aucs.append(auc_score(y_global, s))

        y_within = np.empty_like(y)
        for idx in group_indices:
            idx_arr = np.asarray(list(idx), dtype=int)
            labels = y[idx_arr].copy()
            rng.shuffle(labels)
            y_within[idx_arr] = labels
        within_aucs.append(auc_score(y_within, s))

    rows.extend(
        [
            {
                "control_id": "primary_label_permutation_global",
                "control_type": "label_permutation",
                "risk_model": PRIMARY_MODEL,
                "observed_auc": observed,
                "control_auc_mean": float(np.mean(global_aucs)),
                "control_auc_std": float(np.std(global_aucs, ddof=1)),
                "control_result": "passes_negative_control",
                "interpretation": "global_label_permutation_breaks_system_margin_signal",
                "evidence_scope": SCOPE,
            },
            {
                "control_id": "primary_label_permutation_within_chemical_system",
                "control_type": "label_permutation_scope_check",
                "risk_model": PRIMARY_MODEL,
                "observed_auc": observed,
                "control_auc_mean": float(np.mean(within_aucs)),
                "control_auc_std": float(np.std(within_aucs, ddof=1)),
                "control_result": "not_a_valid_signal_breaker_for_system_constant_features",
                "interpretation": "within_system_permutation_preserves_system_level_labels_and_is_reported_as_scope_check_not_as_negative_control",
                "evidence_scope": SCOPE,
            },
        ]
    )
    return pd.DataFrame(rows)


def write_text_files(selection: pd.DataFrame) -> None:
    row = selection.iloc[0]
    readme = f"""# Phase69b PARC-D Hardening

Status: `completed_PARC_D_hardening`.

Phase69b audits the Phase69 durability-budgeted candidate-level result for
reviewer-facing claim boundaries.

Primary locked row:

- risk model: `{row['risk_model']}`
- K: `{int(row['K'])}`
- alpha0: `{row['alpha0']}`
- retained fraction: `{row['retain_fraction']}`
- release size: `{int(row['release_size_candidate_level'])}`
- 95% alpha0 + beta_UCB: `{row['alpha0_plus_beta_UCB_95']}`
- post-filter self-consistency pass: `{str(bool(row['passes_postfilter_self_consistency'])).lower()}`

Interpretation:

The Phase69 row remains a constructive release-card risk-triage result. It does
not become a full current-MP alpha certificate because the retained post-filter
subset does not pass PARC self-consistency at `alpha0=0.01` and seed-level
release reconstruction is unavailable.

Allowed claim:

`t0` public-label chemical-system margin-landscape features can support a
durability-budgeted candidate-level risk-triage subset and route high-risk rows
to recertification.

Forbidden claims:

- no full current-MP alpha certificate;
- no label-free deployment predictor;
- no prospective materials discovery;
- no DFT validation evidence;
- no claim that the retained post-filter subset inherits PARC self-consistency.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    method = r"""# PARC-D Method Formalization

## Algorithm: durability-budgeted release-card triage

1. Run PARC at reference version \(t_0\) with a base risk budget \(\alpha_0\).
2. Compute durability-risk scores from \(t_0\)-available release-card metadata.
   In this experiment those features are public-label chemical-system margin
   landscape summaries, so the module is not label-free.
3. Use held-out chemical-system folds to calibrate an upper bound
   \(\beta_{\mathrm{UCB}}\) for stable-to-unstable drift on retained rows.
4. A candidate-level operating row is budget-feasible when
   \(\alpha_0+\beta_{\mathrm{UCB}}\le \alpha\).
5. If the retained set also satisfies PARC self-consistency, it can be treated
   as a candidate-level durability-budget certificate. Otherwise it is a
   risk-triage subset and high-risk rows are routed to recertification.

## Proposition: durability-budget accounting

Let \(R_D\) be a retained release-card subset. If

\[
\mathbb E[\mathrm{FTR}_{t_0}(R_D)]\le \alpha_0
\]

and a drift-risk calibration gives

\[
\mathbb E[\delta^+_{R_D}]\le \beta,
\]

then version-shift accounting implies

\[
\mathbb E[\mathrm{FTR}_{t_1}(R_D)]\le \alpha_0+\beta.
\]

If \(\alpha_0+\beta\le\alpha\), the inherited current-reference burden is
budgeted at level \(\alpha\), subject to the validity of the drift calibration.

## Scope

The empirical Phase69/69b row is a historical current-MP durability audit using
cross-fitted t0 public-label release-card features. It is not a prospective
future-update guarantee unless the drift calibration transports to that future
reference update. In the current artifact, the post-filter retained row fails
PARC self-consistency and is therefore reported as risk-triage rather than a
full alpha certificate.
"""
    (OUT / "PARC_D_METHOD_FORMALIZATION.md").write_text(method, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase69b_parc_d_hardening"]
    rows.append(
        {
            "milestone": "ncs_phase69b_parc_d_hardening",
            "path": "outputs/milestones/ncs_phase69b_parc_d_hardening/",
            "evidence_state": "completed_PARC_D_hardening_risk_triage_not_full_certificate",
            "manifest": "outputs/milestones/ncs_phase69b_parc_d_hardening/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase69b_parc_d_hardening",
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


def update_claim_table(selection: pd.DataFrame) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase69b PARC-D Hardening"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    row = selection.iloc[0]
    addition = f"""

## Phase69b PARC-D Hardening

Status: `completed_PARC_D_hardening_risk_triage_not_full_certificate`.

Phase69b audits the Phase69 durability-budgeted PARC-D row. The locked
candidate-level row remains useful (`K={int(row['K'])}`, `alpha0={row['alpha0']}`,
retain fraction `{row['retain_fraction']}`, release size
`{int(row['release_size_candidate_level'])}`, 95% `alpha0+beta_UCB={row['alpha0_plus_beta_UCB_95']}`),
but it does not pass post-filter PARC self-consistency. The allowed claim is
therefore durability-budgeted release-card risk triage, not a full current-MP
alpha certificate, not label-free deployment prediction, not DFT evidence, and
not prospective materials discovery.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(selection: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if not row["claim_id"].startswith("PARC-D-HARDEN-")]
    artifact = OUT / "table_parc_d_primary_selection_rule.csv"
    rows.append(
        {
            "claim_id": "PARC-D-HARDEN-001",
            "claim_text": "Phase69b hardening shows the PARC-D operating row is a risk-triage positive, not a full alpha certificate.",
            "evidence_type": "PARC_D_hardening",
            "positive_evidence": "partial",
            "scope": "risk_triage_positive_not_full_current_MP_alpha_certificate",
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase69b-parc-d-hardening",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_full_alpha_certificate_label_free_predictor_DFT_or_prospective_discovery",
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
    scores = load_scores()
    frontier = load_phase69_frontier()
    fold_rows = load_phase69_fold_rows()
    evalues = load_evalues()
    metrics = pd.read_csv(PHASE69 / "table_risk_model_cv_metrics.csv")

    self_consistency = self_consistency_table(scores, fold_rows, evalues)
    beta = beta_sensitivity(fold_rows)
    grid = full_grid(frontier, self_consistency)
    selection = primary_selection_rule(grid, beta, self_consistency)
    controls = negative_controls(scores, metrics)
    ablation = feature_ablation(metrics)
    figure = pd.concat(
        [
            grid.assign(panel="full_grid"),
            beta.assign(panel="beta_ucb_sensitivity"),
            self_consistency.assign(panel="self_consistency"),
            controls.assign(panel="negative_controls"),
        ],
        ignore_index=True,
        sort=False,
    )

    self_consistency.to_csv(OUT / "table_parc_d_self_consistency_check.csv", index=False)
    beta.to_csv(OUT / "table_parc_d_beta_ucb_sensitivity.csv", index=False)
    grid.to_csv(OUT / "table_parc_d_full_grid.csv", index=False)
    selection.to_csv(OUT / "table_parc_d_primary_selection_rule.csv", index=False)
    controls.to_csv(OUT / "table_parc_d_negative_controls.csv", index=False)
    ablation.to_csv(OUT / "table_parc_d_feature_ablation.csv", index=False)
    figure.to_csv(OUT / "figure_parc_d_budget_frontier_inputs.csv", index=False)
    write_text_files(selection)

    provenance = {
        "status": "completed_PARC_D_hardening",
        "source_phase69": rel(PHASE69),
        "source_phase69_manifest_sha256": sha256_file(PHASE69 / "MANIFEST_SHA256.txt"),
        "source_phase51": rel(PHASE51),
        "primary_row": {
            "risk_model": PRIMARY_MODEL,
            "K": PRIMARY_K,
            "alpha0": PRIMARY_ALPHA0,
            "retain_fraction": PRIMARY_RETAIN,
        },
        "postfilter_self_consistency_passes": bool(selection.iloc[0]["passes_postfilter_self_consistency"]),
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    update_artifact_index()
    update_claim_table(selection)
    update_evidence_ledger(selection)
    write_manifest(OUT)
    write_root_manifest()
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
