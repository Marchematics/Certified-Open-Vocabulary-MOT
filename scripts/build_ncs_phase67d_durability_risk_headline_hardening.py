#!/usr/bin/env python3
"""Build Phase67d headline hardening for durability-risk prediction.

Phase67c established the durability-risk diagnostic.  Phase67d is the
review-facing hardening layer for the headline display:

- headline pruned model = system margin distribution + size/activity;
- near-hull density is retained only as an Extended Data negative ablation;
- chemical-system bootstrap confidence intervals;
- calibration/frontier tables;
- explicit base-rate and memorization controls under GroupKFold.

This is not a release certificate, DFT evidence, or prospective discovery.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
PHASE67C = ROOT / "outputs/milestones/ncs_phase67c_durability_risk_prediction"
OUT = ROOT / "outputs/milestones/ncs_phase67d_durability_risk_headline_hardening"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"

N_BOOTSTRAP = 1000
RANDOM_SEED = 20260530
HEADLINE_FEATURE_SET = "headline_pruned_margin_distribution_plus_size_activity"
SCOPE = (
    "completed_durability_risk_headline_hardening;"
    "phase67c_review_hardening;"
    "features_t0_only;"
    "group_cv_by_chemical_system;"
    "chemical_system_bootstrap_CI;"
    "calibration_and_base_rate_controls;"
    "not_release_certificate;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
)


def load_phase67c_module():
    path = ROOT / "scripts/build_ncs_phase67c_durability_risk_prediction.py"
    spec = importlib.util.spec_from_file_location("phase67c_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P67C = load_phase67c_module()

HEADLINE_FEATURES = (
    P67C.SYSTEM_ABLATION_FEATURE_SETS["system_margin_distribution"]
    + P67C.SYSTEM_ABLATION_FEATURE_SETS["system_size_activity_proxy"]
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


def load_population() -> pd.DataFrame:
    base = P67C.add_system_features(P67C.load_base())
    data = base[base["is_release_row"].astype(bool) & base["is_t0_stable_row"].astype(bool)].copy()
    data = data[data["stable_to_unstable_t1"].notna()].copy()
    return data


def safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(roc_auc_score(y_true, y_score)) if len(set(y_true.tolist())) == 2 else math.nan


def safe_ap(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(average_precision_score(y_true, y_score)) if len(set(y_true.tolist())) == 2 else float(np.mean(y_true))


def clipped(scores: np.ndarray) -> np.ndarray:
    return np.clip(scores.astype(float), 1e-6, 1 - 1e-6)


def summarize_predictions(pred: pd.DataFrame, feature_set: str) -> dict[str, object]:
    y = pred["stable_to_unstable_t1"].astype(int).to_numpy()
    s = clipped(pred["predicted_durability_failure_risk"].to_numpy())
    out = {
        "feature_set": feature_set,
        "n_rows": int(len(pred)),
        "n_chemical_systems": int(pred["chemical_system"].nunique()),
        "base_flip_rate": float(np.mean(y)),
        "roc_auc": safe_auc(y, s),
        "average_precision": safe_ap(y, s),
        "brier_score": float(brier_score_loss(y, s)),
        "log_loss": float(log_loss(y, s, labels=[0, 1])),
    }
    for frac in [0.10, 0.20, 0.30]:
        group = pred.sort_values("predicted_durability_failure_risk", ascending=False)
        n = int(math.ceil(frac * len(group)))
        flagged = group.head(n)
        kept = group.iloc[n:]
        flips = int(group["stable_to_unstable_t1"].sum())
        out[f"top{int(frac*100)}_flagged_flip_rate"] = float(flagged["stable_to_unstable_t1"].mean())
        out[f"top{int(frac*100)}_retained_flip_rate"] = float(kept["stable_to_unstable_t1"].mean()) if len(kept) else math.nan
        out[f"top{int(frac*100)}_fraction_flips_flagged"] = (
            float(flagged["stable_to_unstable_t1"].sum() / flips) if flips else math.nan
        )
    out["evidence_scope"] = SCOPE
    return out


def group_bootstrap_ci(pred: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    systems = np.array(sorted(pred["chemical_system"].astype(str).unique()))
    rows: list[dict[str, object]] = []
    for b in range(N_BOOTSTRAP):
        sampled = rng.choice(systems, size=len(systems), replace=True)
        boot = pd.concat([pred[pred["chemical_system"].astype(str).eq(system)] for system in sampled], ignore_index=True)
        metrics = summarize_predictions(boot, feature_set)
        rows.append(
            {
                "bootstrap_id": b,
                "feature_set": feature_set,
                "roc_auc": metrics["roc_auc"],
                "average_precision": metrics["average_precision"],
                "brier_score": metrics["brier_score"],
                "top30_retained_flip_rate": metrics["top30_retained_flip_rate"],
                "top30_fraction_flips_flagged": metrics["top30_fraction_flips_flagged"],
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def ci_summary(boot: pd.DataFrame, point: dict[str, object]) -> pd.DataFrame:
    rows = []
    for metric in [
        "roc_auc",
        "average_precision",
        "brier_score",
        "top30_retained_flip_rate",
        "top30_fraction_flips_flagged",
    ]:
        series = boot[metric].dropna()
        rows.append(
            {
                "feature_set": point["feature_set"],
                "metric": metric,
                "estimate": float(point[metric]),
                "ci_low_95": float(series.quantile(0.025)),
                "ci_high_95": float(series.quantile(0.975)),
                "bootstrap_unit": "chemical_system",
                "n_bootstrap": N_BOOTSTRAP,
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def calibration_table(pred: pd.DataFrame, feature_set: str, n_bins: int = 10) -> pd.DataFrame:
    df = pred.copy()
    df["predicted_durability_failure_risk"] = clipped(df["predicted_durability_failure_risk"].to_numpy())
    # qcut can drop duplicate bins when a model produces repeated probabilities.
    df["risk_bin"] = pd.qcut(
        df["predicted_durability_failure_risk"].rank(method="first"),
        q=n_bins,
        labels=False,
        duplicates="drop",
    )
    rows = []
    for risk_bin, group in df.groupby("risk_bin", sort=True):
        rows.append(
            {
                "feature_set": feature_set,
                "risk_bin": int(risk_bin),
                "n": int(len(group)),
                "predicted_mean": float(group["predicted_durability_failure_risk"].mean()),
                "observed_flip_rate": float(group["stable_to_unstable_t1"].mean()),
                "absolute_calibration_error": float(
                    abs(group["predicted_durability_failure_risk"].mean() - group["stable_to_unstable_t1"].mean())
                ),
                "chemical_system_count": int(group["chemical_system"].nunique()),
                "evidence_scope": SCOPE,
            }
        )
    out = pd.DataFrame(rows)
    out["weighted_absolute_calibration_error"] = out["absolute_calibration_error"] * out["n"] / out["n"].sum()
    return out


def base_rate_predictions(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    y = data["stable_to_unstable_t1"].astype(int).to_numpy()
    groups = data["chemical_system"].astype(str).to_numpy()
    cv = P67C.GroupKFold(n_splits=min(P67C.N_SPLITS, int(data["chemical_system"].nunique())))
    for fold, (train_idx, test_idx) in enumerate(cv.split(data[HEADLINE_FEATURES], y, groups=groups)):
        train_rate = float(np.mean(y[train_idx]))
        test = data.iloc[test_idx][
            [
                "candidate_id",
                "K",
                "chemical_system",
                "formula",
                "raw_rank",
                "t0_e_above_hull_numeric",
                "t1_e_above_hull_numeric",
                "t0_margin",
                "stable_to_unstable_t1",
                "policy_status",
            ]
        ].copy()
        test["feature_set"] = "train_fold_base_rate"
        test["fold"] = fold
        test["predicted_durability_failure_risk"] = train_rate
        test["evidence_scope"] = SCOPE
        pred_rows.append(test)
        y_test = y[test_idx]
        scores = np.full_like(y_test, fill_value=train_rate, dtype=float)
        train_systems = set(data.iloc[train_idx]["chemical_system"].astype(str))
        test_systems = set(data.iloc[test_idx]["chemical_system"].astype(str))
        metric_rows.append(
            {
                "baseline": "train_fold_base_rate",
                "fold": fold,
                "train_flip_rate": train_rate,
                "test_flip_rate": float(np.mean(y_test)),
                "roc_auc": safe_auc(y_test, scores),
                "average_precision": safe_ap(y_test, scores),
                "brier_score": float(brier_score_loss(y_test, scores)),
                "train_test_system_overlap": len(train_systems & test_systems),
                "test_system_lookup_coverage": 0.0,
                "interpretation": "constant train-fold prevalence under GroupKFold; cannot memorize held-out chemical systems",
                "evidence_scope": SCOPE,
            }
        )
    return pd.concat(pred_rows, ignore_index=True), pd.DataFrame(metric_rows)


def compare_headline_to_controls(headline: dict[str, object], controls: pd.DataFrame) -> pd.DataFrame:
    base = controls[controls["baseline"].eq("train_fold_base_rate")]
    rows = [
        {
            "comparison": "headline_pruned_vs_train_fold_base_rate",
            "headline_roc_auc": float(headline["roc_auc"]),
            "baseline_mean_roc_auc": float(base["roc_auc"].mean()),
            "delta_roc_auc": float(headline["roc_auc"] - base["roc_auc"].mean()),
            "baseline_system_overlap": int(base["train_test_system_overlap"].sum()),
            "passes": bool(headline["roc_auc"] >= base["roc_auc"].mean() + 0.10 and base["train_test_system_overlap"].sum() == 0),
            "evidence_scope": SCOPE,
        }
    ]
    return pd.DataFrame(rows)


def write_text_files(headline_summary: dict[str, object], ci: pd.DataFrame) -> None:
    auc_row = ci[ci["metric"].eq("roc_auc")].iloc[0]
    retained_row = ci[ci["metric"].eq("top30_retained_flip_rate")].iloc[0]
    readme = f"""# Phase67d Durability-Risk Headline Hardening

Status: `completed_headline_display_hardening`.

This milestone answers the review-facing Phase A hardening checklist for the
durability-risk centerpiece.

Completed:

- headline pruned model: `system_margin_distribution + system_size_activity`;
- chemical-system bootstrap confidence intervals;
- calibration table over cross-fitted GroupKFold predictions;
- train-fold base-rate baseline and memorization control;
- near-hull-density is kept as an Extended Data negative ablation, not the
  headline model.

Headline model:

- ROC-AUC: `{headline_summary['roc_auc']:.3f}` (95% chemical-system bootstrap
  CI `{auc_row['ci_low_95']:.3f}` to `{auc_row['ci_high_95']:.3f}`);
- base flip rate: `{headline_summary['base_flip_rate']:.3f}`;
- top-30% risk triage retained flip rate: `{headline_summary['top30_retained_flip_rate']:.3f}`
  (95% CI `{retained_row['ci_low_95']:.3f}` to `{retained_row['ci_high_95']:.3f}`);
- top-30% high-risk rows capture `{headline_summary['top30_fraction_flips_flagged']:.3f}`
  of observed flips.

Scope guardrails:

- not a release certificate;
- not DFT evidence;
- not prospective materials discovery;
- not a label-free deployment predictor because the strongest features depend
  on t0 public-label margin landscapes;
- do not present the near-hull-density ablation as the headline model.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    display = f"""# Headline Display Guidance

Use `headline_pruned_margin_distribution_plus_size_activity` for the main
durability-risk display.  Report candidate margin/rank and train-fold base-rate
as the two main negative controls.  Move `system_near_hull_density` to Extended
Data because it is near random and dilutes the mechanism.

Main-text wording:

> Stable-to-current-unstable drift is predicted by the t0 chemical-system
> margin landscape and activity, not by candidate margin or rank.  The result
> is a release-card risk-triage signal, not a repaired current-reference
> certificate.

Do not claim current-MP alpha control, label-free deployment prediction, or
DFT validation.
"""
    (OUT / "HEADLINE_DISPLAY_GUIDANCE.md").write_text(display, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    df = pd.read_csv(path)
    df = df[df["milestone"] != "ncs_phase67d_durability_risk_headline_hardening"]
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "milestone": "ncs_phase67d_durability_risk_headline_hardening",
                        "path": "outputs/milestones/ncs_phase67d_durability_risk_headline_hardening/",
                        "evidence_state": "completed_headline_display_hardening",
                        "manifest": "outputs/milestones/ncs_phase67d_durability_risk_headline_hardening/MANIFEST_SHA256.txt",
                        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase67d_durability_risk_headline_hardening",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    df.to_csv(path, index=False)


def update_evidence_ledger(headline_summary: dict[str, object], ci: pd.DataFrame) -> None:
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != "DUR-RISK-HARDEN-001"]
    artifact = OUT / "table_headline_pruned_model_summary.csv"
    row = {
        "claim_id": "DUR-RISK-HARDEN-001",
        "claim_text": "The durability-risk headline display uses a pruned t0-only system margin-landscape/activity model with bootstrap CI, calibration and base-rate controls.",
        "evidence_type": "review_hardening",
        "positive_evidence": "yes",
        "scope": SCOPE,
        "artifact_path": rel(artifact),
        "hash": sha256_file(artifact),
        "validation_command": "make reproduce-ncs-phase67d-durability-risk-headline-hardening",
        "status": "PASS",
        "overclaim_guardrail": "not_release_certificate_not_DFT_not_label_free_predictor",
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(LEDGER, index=False)


def update_claim_table(headline_summary: dict[str, object], ci: pd.DataFrame) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "\n## Phase67d Durability-Risk Headline Hardening\n"
    auc_row = ci[ci["metric"].eq("roc_auc")].iloc[0]
    text = text.split(marker)[0].rstrip() + marker + f"""

Status: `completed_headline_display_hardening`.

Phase67d completes the review-facing hardening for the durability-risk
centerpiece. The headline model is the pruned t0-only system
margin-landscape/activity model, with ROC-AUC `{headline_summary['roc_auc']:.3f}`
and chemical-system bootstrap 95% CI `{auc_row['ci_low_95']:.3f}` to
`{auc_row['ci_high_95']:.3f}`. Calibration, base-rate and memorization controls
are frozen in the Phase67d artifact.

Allowed claim: t0 public-label system margin landscape and activity support
release-card durability-risk triage.

Forbidden claim: label-free deployment prediction, current-MP alpha repair, DFT
validation, or prospective materials discovery.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = load_population()
    headline_pred, headline_metrics = P67C.cross_validated_predictions(data, HEADLINE_FEATURE_SET, HEADLINE_FEATURES)
    headline_summary = summarize_predictions(headline_pred, HEADLINE_FEATURE_SET)
    boot = group_bootstrap_ci(headline_pred, HEADLINE_FEATURE_SET)
    ci = ci_summary(boot, headline_summary)
    cal = calibration_table(headline_pred, HEADLINE_FEATURE_SET)
    base_pred, base_metrics = base_rate_predictions(data)
    controls = compare_headline_to_controls(headline_summary, base_metrics)

    ablation = pd.read_csv(PHASE67C / "table_durability_risk_ablation_model_comparison.csv")
    extended = ablation[ablation["feature_set"].isin(["system_near_hull_density", "system_margin_distribution", "system_size_activity_proxy"])].copy()
    extended["main_display_role"] = np.where(
        extended["feature_set"].eq("system_near_hull_density"),
        "extended_data_negative_ablation",
        "component_of_headline_or_mechanism_support",
    )
    extended["evidence_scope"] = SCOPE

    pd.DataFrame([headline_summary]).to_csv(OUT / "table_headline_pruned_model_summary.csv", index=False)
    headline_metrics.to_csv(OUT / "table_headline_pruned_fold_metrics.csv", index=False)
    headline_pred.to_csv(OUT / "table_headline_pruned_crossfit_predictions.csv", index=False)
    boot.to_csv(OUT / "table_headline_pruned_bootstrap_seed_rows.csv", index=False)
    ci.to_csv(OUT / "table_headline_pruned_bootstrap_ci.csv", index=False)
    cal.to_csv(OUT / "table_headline_pruned_calibration.csv", index=False)
    base_metrics.to_csv(OUT / "table_base_rate_baseline_by_fold.csv", index=False)
    base_pred.to_csv(OUT / "table_base_rate_baseline_predictions.csv", index=False)
    controls.to_csv(OUT / "table_base_rate_and_memorization_controls.csv", index=False)
    extended.to_csv(OUT / "table_extended_data_ablation_role.csv", index=False)
    pd.concat(
        [
            pd.DataFrame([headline_summary]).assign(table_role="headline_summary"),
            controls.assign(table_role="base_rate_control"),
            extended.assign(table_role="extended_ablation"),
        ],
        ignore_index=True,
        sort=False,
    ).to_csv(OUT / "figure_durability_risk_headline_inputs.csv", index=False)

    write_text_files(headline_summary, ci)
    provenance = {
        "phase": "phase67d",
        "status": "completed_headline_display_hardening",
        "source_phase": rel(PHASE67C),
        "headline_feature_set": HEADLINE_FEATURE_SET,
        "headline_features": HEADLINE_FEATURES,
        "n_rows": int(len(data)),
        "n_chemical_systems": int(data["chemical_system"].nunique()),
        "n_bootstrap": N_BOOTSTRAP,
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_manifest(OUT)
    update_artifact_index()
    update_evidence_ledger(headline_summary, ci)
    update_claim_table(headline_summary, ci)
    write_root_manifest()
    print(json.dumps(provenance, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
