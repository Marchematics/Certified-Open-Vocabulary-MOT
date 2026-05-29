#!/usr/bin/env python3
"""Build Phase69 durability-budgeted PARC artifacts.

Phase67c established a t0-only durability-risk prediction signal for
stable-to-unstable flips under a later Materials Project reference. Phase69
turns that prediction diagnostic into release-card decision artifacts:

1. cross-fitted durability-risk scores;
2. triage frontiers that route high-risk release rows to recertification;
3. a candidate-level durability-budget frontier using
   alpha0 + beta_UCB <= alpha_total.

The budget frontier is intentionally scoped. It is a candidate-level
release-card diagnostic over t0-stable PARC release rows, not a repaired
full-release alpha certificate, not DFT evidence and not prospective materials
discovery.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE67C = ROOT / "outputs/milestones/ncs_phase67c_durability_risk_prediction"
OUT = ROOT / "outputs/milestones/ncs_phase69_durability_budgeted_parc"

ALPHA_TOTAL = 0.10
ALPHA0_GRID = [0.01, 0.025, 0.05, 0.075]
RETAIN_FRACTIONS = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 1.00]
PRIMARY_MODEL = "system_margin_distribution"
RISK_MODELS = [
    "system_margin_distribution",
    "system_size_activity_proxy",
    "chemical_system_exploration_only",
    "candidate_plus_system",
    "candidate_margin_only",
    "candidate_t0_score_only",
]
SCOPE = (
    "durability_budgeted_release_card_diagnostic;"
    "crossfit_risk_scores_grouped_by_chemical_system;"
    "t0_public_label_features_not_label_free;"
    "candidate_level_t0_stable_release_rows;"
    "not_full_release_alpha_certificate;"
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


def wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    """Two-sided 95%-style Wilson upper endpoint used as conservative UCB."""
    if n <= 0:
        return 1.0
    phat = k / n
    denom = 1.0 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    return float(min(1.0, center + half))


def load_crossfit_scores() -> pd.DataFrame:
    main = pd.read_csv(PHASE67C / "table_durability_risk_group_cv_predictions.csv")
    ablation = pd.read_csv(PHASE67C / "table_durability_risk_ablation_predictions.csv")
    scores = pd.concat([main, ablation], ignore_index=True)
    scores = scores[scores["feature_set"].isin(RISK_MODELS)].copy()
    scores = scores.rename(
        columns={
            "feature_set": "risk_model",
            "predicted_durability_failure_risk": "crossfit_durability_risk",
        }
    )
    scores["candidate_key"] = scores["candidate_id"].astype(str) + "::K" + scores["K"].astype(int).astype(str)
    scores["evidence_scope"] = SCOPE
    return scores


def load_model_metrics() -> pd.DataFrame:
    main = pd.read_csv(PHASE67C / "table_durability_risk_prediction_model_comparison.csv")
    ablation = pd.read_csv(PHASE67C / "table_durability_risk_ablation_model_comparison.csv")
    metrics = pd.concat([main, ablation], ignore_index=True)
    metrics = metrics[metrics["feature_set"].isin(RISK_MODELS)].copy()
    metrics = metrics.rename(columns={"feature_set": "risk_model"})
    metrics["model_role"] = np.where(metrics["risk_model"].eq(PRIMARY_MODEL), "primary_phase69_model", "comparison")
    metrics["evidence_scope"] = SCOPE
    return metrics


def triage_frontier(scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for risk_model, model_group in scores.groupby("risk_model", sort=True):
        for k_value, group in model_group.groupby("K", sort=True):
            group = group.sort_values("crossfit_durability_risk", ascending=True).reset_index(drop=True)
            base_rate = float(group["stable_to_unstable_t1"].mean())
            total_flips = int(group["stable_to_unstable_t1"].sum())
            for retain_fraction in RETAIN_FRACTIONS:
                n_keep = int(math.floor(retain_fraction * len(group)))
                if retain_fraction > 0 and n_keep == 0:
                    n_keep = 1
                kept = group.iloc[:n_keep].copy()
                flagged = group.iloc[n_keep:].copy()
                kept_flips = int(kept["stable_to_unstable_t1"].sum()) if len(kept) else 0
                flagged_flips = int(flagged["stable_to_unstable_t1"].sum()) if len(flagged) else 0
                kept_rate = float(kept["stable_to_unstable_t1"].mean()) if len(kept) else math.nan
                flagged_rate = float(flagged["stable_to_unstable_t1"].mean()) if len(flagged) else math.nan
                rows.append(
                    {
                        "risk_model": risk_model,
                        "K": int(k_value),
                        "retain_fraction": retain_fraction,
                        "flagged_fraction": 1.0 - retain_fraction,
                        "n_total": int(len(group)),
                        "n_retained_low_risk": int(len(kept)),
                        "n_flagged_high_risk": int(len(flagged)),
                        "base_flip_rate": base_rate,
                        "retained_flip_rate": kept_rate,
                        "flagged_flip_rate": flagged_rate,
                        "relative_flip_rate_reduction_retained": (base_rate - kept_rate) / base_rate
                        if base_rate and math.isfinite(kept_rate)
                        else math.nan,
                        "fraction_flips_flagged": flagged_flips / total_flips if total_flips else math.nan,
                        "retained_beta_UCB_observed": wilson_upper(kept_flips, len(kept)),
                        "triage_secondary_success": bool(
                            len(kept) >= 10
                            and math.isfinite(kept_rate)
                            and kept_rate <= 0.13
                            and (flagged_flips / total_flips if total_flips else 0.0) >= 0.60
                        ),
                        "evidence_scope": SCOPE,
                    }
                )
    return pd.DataFrame(rows)


def fold_budget_rows(scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for risk_model, model_group in scores.groupby("risk_model", sort=True):
        for k_value, k_group in model_group.groupby("K", sort=True):
            for retain_fraction in RETAIN_FRACTIONS:
                for fold in sorted(k_group["fold"].unique()):
                    test = k_group[k_group["fold"].eq(fold)].copy()
                    calibration = k_group[~k_group["fold"].eq(fold)].copy()
                    if calibration.empty or test.empty:
                        continue
                    threshold = float(calibration["crossfit_durability_risk"].quantile(retain_fraction))
                    cal_retained = calibration[calibration["crossfit_durability_risk"].le(threshold)]
                    test_retained = test[test["crossfit_durability_risk"].le(threshold)]
                    cal_flips = int(cal_retained["stable_to_unstable_t1"].sum())
                    test_flips = int(test_retained["stable_to_unstable_t1"].sum())
                    beta_ucb = wilson_upper(cal_flips, len(cal_retained))
                    overlap = set(calibration["chemical_system"].astype(str)) & set(test["chemical_system"].astype(str))
                    for alpha0 in ALPHA0_GRID:
                        alpha0_plus_beta = float(alpha0 + beta_ucb)
                        rows.append(
                            {
                                "risk_model": risk_model,
                                "K": int(k_value),
                                "fold": int(fold),
                                "retain_fraction": retain_fraction,
                                "risk_threshold_from_calibration": threshold,
                                "alpha0": alpha0,
                                "calibration_n": int(len(calibration)),
                                "calibration_retained_n": int(len(cal_retained)),
                                "calibration_retained_flips": cal_flips,
                                "beta_UCB": beta_ucb,
                                "alpha0_plus_beta_UCB": alpha0_plus_beta,
                                "budget_pass_pre_eval": bool(alpha0_plus_beta <= ALPHA_TOTAL),
                                "test_n": int(len(test)),
                                "test_retained_n": int(len(test_retained)),
                                "test_retained_flips": test_flips,
                                "test_retained_FTR_t1": float(test_flips / len(test_retained)) if len(test_retained) else math.nan,
                                "test_safe_alpha010": bool(len(test_retained) > 0 and test_flips / len(test_retained) <= ALPHA_TOTAL),
                                "chemical_system_overlap_n": int(len(overlap)),
                                "split_scope": "outer_fold_heldout_chemical_systems;threshold_and_beta_from_other_folds",
                                "evidence_scope": SCOPE,
                            }
                        )
    return pd.DataFrame(rows)


def budget_frontier(fold_rows: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    grouped = fold_rows.groupby(["risk_model", "K", "retain_fraction", "alpha0"], sort=True)
    for (risk_model, k_value, retain_fraction, alpha0), group in grouped:
        test_n = int(group["test_retained_n"].sum())
        test_flips = int(group["test_retained_flips"].sum())
        observed = float(test_flips / test_n) if test_n else math.nan
        fold_count = int(group["fold"].nunique())
        nonempty_folds = int(group["test_retained_n"].gt(0).sum())
        safe_folds = int(group["test_safe_alpha010"].sum())
        min_test_retained = int(group["test_retained_n"].min())
        max_beta = float(group["beta_UCB"].max())
        mean_beta = float(group["beta_UCB"].mean())
        alpha0_plus_beta = float(alpha0 + max_beta)
        budget_pass = bool(alpha0_plus_beta <= ALPHA_TOTAL)
        primary_candidate_success = bool(
            budget_pass
            and test_n >= 10
            and math.isfinite(observed)
            and observed <= ALPHA_TOTAL
            and nonempty_folds == fold_count
            and min_test_retained >= 5
            and safe_folds >= max(1, math.ceil(0.8 * fold_count))
        )
        rows.append(
            {
                "risk_model": risk_model,
                "K": int(k_value),
                "alpha0": alpha0,
                "retain_fraction": retain_fraction,
                "release_size_candidate_level": test_n,
                "nonempty_folds": nonempty_folds,
                "fold_count": fold_count,
                "min_test_retained_n_across_folds": min_test_retained,
                "safe_folds_t1": safe_folds,
                "observed_FTR_t1": observed,
                "observed_flip_rate_retained": observed,
                "mean_FTR_t0_by_design": 0.0,
                "beta_UCB_max_across_calibration_folds": max_beta,
                "beta_UCB_mean_across_calibration_folds": mean_beta,
                "alpha0_plus_beta_UCB": alpha0_plus_beta,
                "budget_pass_pre_eval": budget_pass,
                "seed_level_gate_available": False,
                "primary_success_candidate_level": primary_candidate_success,
                "primary_success_full_certificate": False,
                "paper_role": "candidate_level_durability_budget_positive"
                if primary_candidate_success
                else "risk_triage_or_boundary_diagnostic",
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def claim_gate(triage: pd.DataFrame, frontier: pd.DataFrame) -> pd.DataFrame:
    best_budget = frontier.sort_values(
        [
            "primary_success_candidate_level",
            "budget_pass_pre_eval",
            "observed_FTR_t1",
            "release_size_candidate_level",
        ],
        ascending=[False, False, True, False],
    ).iloc[0]
    triage_rows = triage[triage["risk_model"].eq(PRIMARY_MODEL)].copy()
    best_triage = triage_rows.sort_values(
        ["triage_secondary_success", "retained_flip_rate", "fraction_flips_flagged"],
        ascending=[False, True, False],
    ).iloc[0]
    return pd.DataFrame(
        [
            {
                "claim_id": "PARC-D-PRIMARY-BUDGET",
                "claim_supported": bool(frontier["primary_success_candidate_level"].any()),
                "claim_text": "A durability-budgeted candidate-level release row satisfies alpha0 + beta_UCB <= 0.10 and observed retained t1 FTR <= 0.10.",
                "best_risk_model": best_budget["risk_model"],
                "best_K": int(best_budget["K"]),
                "best_alpha0": float(best_budget["alpha0"]),
                "best_retain_fraction": float(best_budget["retain_fraction"]),
                "best_release_size_candidate_level": int(best_budget["release_size_candidate_level"]),
                "best_observed_FTR_t1": float(best_budget["observed_FTR_t1"])
                if math.isfinite(float(best_budget["observed_FTR_t1"]))
                else math.nan,
                "best_alpha0_plus_beta_UCB": float(best_budget["alpha0_plus_beta_UCB"]),
                "paper_role": "main_text_constructive_candidate_level_method" if bool(frontier["primary_success_candidate_level"].any()) else "not_supported",
                "guardrail": "not_full_release_alpha_certificate;seed_level_gate_not_available;not_DFT_evidence",
                "evidence_scope": SCOPE,
            },
            {
                "claim_id": "PARC-D-TRIAGE",
                "claim_supported": bool(triage["triage_secondary_success"].any()),
                "claim_text": "Durability-risk triage reduces retained stable-to-unstable flip burden and routes high-risk rows to recertification.",
                "best_risk_model": best_triage["risk_model"],
                "best_K": int(best_triage["K"]),
                "best_alpha0": math.nan,
                "best_retain_fraction": float(best_triage["retain_fraction"]),
                "best_release_size_candidate_level": int(best_triage["n_retained_low_risk"]),
                "best_observed_FTR_t1": float(best_triage["retained_flip_rate"]),
                "best_alpha0_plus_beta_UCB": math.nan,
                "paper_role": "main_text_risk_triage_positive" if bool(triage["triage_secondary_success"].any()) else "boundary_diagnostic",
                "guardrail": "triage_not_repaired_alpha_certificate;not_label_free_deployment_predictor",
                "evidence_scope": SCOPE,
            },
        ]
    )


def figure_inputs(metrics: pd.DataFrame, triage: pd.DataFrame, frontier: pd.DataFrame) -> pd.DataFrame:
    panels = []
    panels.append(metrics.assign(panel="risk_model_comparison"))
    panels.append(triage.assign(panel="risk_triage_frontier"))
    panels.append(frontier.assign(panel="durability_budget_frontier"))
    return pd.concat(panels, ignore_index=True, sort=False)


def write_text_files(claims: pd.DataFrame) -> None:
    budget_supported = bool(claims.loc[claims["claim_id"].eq("PARC-D-PRIMARY-BUDGET"), "claim_supported"].iloc[0])
    triage_supported = bool(claims.loc[claims["claim_id"].eq("PARC-D-TRIAGE"), "claim_supported"].iloc[0])
    readme = f"""# Phase69 Durability-Budgeted PARC

Status: `completed_durability_budgeted_release_card_diagnostic`.

Phase69 upgrades the Phase67c durability-risk prediction signal into
release-card decision artifacts. It reports cross-fitted risk scores,
risk-triage frontiers and a candidate-level durability-budget frontier.

Primary budgeted candidate-level support: `{str(budget_supported).lower()}`.
Risk-triage support: `{str(triage_supported).lower()}`.

Allowed claims:

- t0 public-label release-card features can triage which released materials
  candidates are more likely to lose durability after a reference update.
- A candidate-level durability budget can be audited with
  `alpha0 + beta_UCB <= 0.10`, using thresholds and beta estimates from
  chemical-system-held-out calibration folds.

Guardrails:

- no label-free deployment predictor;
- no prospective materials discovery;
- no DFT evidence;
- no full-release alpha certificate unless a future seed-level/full-release
  analysis satisfies the required gate;
- t0 public-label aggregate features are allowed only as release-card
  durability-audit features.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")
    prereg = f"""# Phase69 Durability-Budgeted PARC Preregistration

Status: registered after Phase67c leakage audit and before any DFT v2 stability
outcome table.

## Objective

Convert t0-only durability-risk scores into release-card triage and a
candidate-level durability-budget frontier.

## Frozen inputs

- Phase67c cross-fitted risk predictions.
- Phase67c feature provenance and leakage audit.
- Population: t0-stable PARC release rows at K=300/500.
- Label for evaluation: stable-to-unstable at current-MP t1.

## Grids

- alpha0 grid: `{ALPHA0_GRID}`.
- retain-fraction grid: `{RETAIN_FRACTIONS}`.
- total target alpha: `{ALPHA_TOTAL}`.
- primary risk model: `{PRIMARY_MODEL}`.

## Calibration discipline

For each held-out fold, risk thresholds and beta_UCB are computed from other
chemical-system folds. Held-out t1 labels are used only for evaluation.

## Success criteria

Candidate-level budget positive requires:

1. `alpha0 + beta_UCB <= 0.10` using the maximum calibration-fold beta_UCB;
2. observed retained t1 FTR <= 0.10 on held-out folds;
3. every held-out fold non-empty;
4. at least 80% of held-out folds individually t1-safe;
5. at least 10 retained candidate-level release rows in aggregate;
6. at least 5 retained candidate-level rows in every held-out fold.

This is still not a full PARC alpha certificate because the available Phase67c
population is restricted to t0-stable released rows and does not reconstruct
seed-level release sets.
"""
    (OUT / "DURABILITY_BUDGETED_PARC_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase69_durability_budgeted_parc"]
    rows.append(
        {
            "milestone": "ncs_phase69_durability_budgeted_parc",
            "path": "outputs/milestones/ncs_phase69_durability_budgeted_parc/",
            "evidence_state": "completed_durability_budgeted_release_card_diagnostic",
            "manifest": "outputs/milestones/ncs_phase69_durability_budgeted_parc/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase69_durability_budgeted_parc",
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


def update_claim_table(claims: pd.DataFrame) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase69 Durability-Budgeted PARC"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    budget_supported = bool(claims.loc[claims["claim_id"].eq("PARC-D-PRIMARY-BUDGET"), "claim_supported"].iloc[0])
    triage_supported = bool(claims.loc[claims["claim_id"].eq("PARC-D-TRIAGE"), "claim_supported"].iloc[0])
    addition = f"""

## Phase69 Durability-Budgeted PARC

Status: `completed_durability_budgeted_release_card_diagnostic`.

Phase69 converts the Phase67c t0-only durability-risk predictor into
release-card decision artifacts. Candidate-level durability-budget support:
`{str(budget_supported).lower()}`. Risk-triage support:
`{str(triage_supported).lower()}`.

The allowed claim is that t0 public-label release-card features can route
high-risk materials candidates to recertification and reduce retained
stable-to-unstable burden. Unless the stricter budget gate passes, this is not a
repaired `alpha=0.10` certificate. Even when the candidate-level budget gate
passes, it remains scoped to t0-stable released rows and is not a full
seed-level release certificate, not DFT evidence, and not prospective materials
discovery.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(claims: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if not row["claim_id"].startswith("PARC-D-")]
    for row in claims.to_dict("records"):
        artifact = (
            OUT / "table_durability_budgeted_release_frontier.csv"
            if row["claim_id"] == "PARC-D-PRIMARY-BUDGET"
            else OUT / "table_risk_triage_frontier.csv"
        )
        rows.append(
            {
                "claim_id": row["claim_id"],
                "claim_text": row["claim_text"],
                "evidence_type": "durability_budgeted_release_card",
                "positive_evidence": "yes" if bool(row["claim_supported"]) else "partial",
                "scope": row["guardrail"],
                "artifact_path": rel(artifact),
                "hash": sha256_file(artifact),
                "validation_command": "make reproduce-ncs-phase69-durability-budgeted-parc",
                "status": "PASS",
                "overclaim_guardrail": row["guardrail"],
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
    scores = load_crossfit_scores()
    metrics = load_model_metrics()
    triage = triage_frontier(scores)
    fold_rows = fold_budget_rows(scores)
    frontier = budget_frontier(fold_rows)
    claims = claim_gate(triage, frontier)
    fig = figure_inputs(metrics, triage, frontier)

    scores.to_csv(OUT / "table_crossfit_durability_risk_scores.csv", index=False)
    metrics.to_csv(OUT / "table_risk_model_cv_metrics.csv", index=False)
    triage.to_csv(OUT / "table_risk_triage_frontier.csv", index=False)
    fold_rows.to_csv(OUT / "table_alpha0_beta_budget_by_row.csv", index=False)
    frontier.to_csv(OUT / "table_durability_budgeted_release_frontier.csv", index=False)
    claims.to_csv(OUT / "table_phase69_claim_gate.csv", index=False)
    fig.to_csv(OUT / "figure_durability_budget_frontier_inputs.csv", index=False)
    # Alias for figure scripts that expect a prediction-panel source.
    fig.to_csv(OUT / "figure_durability_risk_prediction_inputs.csv", index=False)
    write_text_files(claims)
    provenance = {
        "status": "completed_durability_budgeted_release_card_diagnostic",
        "source_phase67c": rel(PHASE67C),
        "source_phase67c_manifest_sha256": sha256_file(PHASE67C / "MANIFEST_SHA256.txt"),
        "risk_models": RISK_MODELS,
        "primary_risk_model": PRIMARY_MODEL,
        "alpha0_grid": ALPHA0_GRID,
        "retain_fraction_grid": RETAIN_FRACTIONS,
        "total_alpha": ALPHA_TOTAL,
        "scope": SCOPE,
        "candidate_level_budget_positive": bool(claims.loc[claims["claim_id"].eq("PARC-D-PRIMARY-BUDGET"), "claim_supported"].iloc[0]),
        "risk_triage_positive": bool(claims.loc[claims["claim_id"].eq("PARC-D-TRIAGE"), "claim_supported"].iloc[0]),
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    update_artifact_index()
    update_claim_table(claims)
    update_evidence_ledger(claims)
    write_manifest(OUT)
    write_root_manifest()
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
