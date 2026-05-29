#!/usr/bin/env python3
"""Build Phase67c durability-risk prediction diagnostic.

Phase67/67b asked whether t0 margin buffers can recover a t1-surviving release
frontier. Phase67c changes the task: predict, using only t0-time information,
which t0-stable released candidates will become unstable under the current-MP
t1 reference. The scientific question is whether durability failure is better
explained by candidate-level margin or by chemical-system exploration state.

This is a prediction diagnostic. It is not a new release certificate, not DFT
evidence and not prospective materials discovery.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE67C = ROOT / "outputs/milestones/ncs_phase67c_durability_risk_prediction"

N_SPLITS = 5
RISK_TRIAGE_FRACTIONS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50]
RANDOM_STATE = 20260529
SCOPE = (
    "completed_durability_risk_prediction_diagnostic;"
    "features_t0_only_candidate_and_chemical_system;"
    "label_stable_to_unstable_t1_drift;"
    "group_cv_by_chemical_system;"
    "not_release_certificate;"
    "not_prospective_discovery;"
    "not_DFT_evidence"
)


CANDIDATE_MARGIN_FEATURES = ["t0_margin"]
CANDIDATE_FEATURES = [
    "t0_margin",
    "t0_e_above_hull_numeric",
    "raw_rank",
    "raw_score",
    "parc_e_value",
    "parc_release_margin",
    "parc_release_seed_count",
    "near_hull_25mev_t0_int",
    "near_hull_50mev_t0_int",
    "K",
]
SYSTEM_FEATURES = [
    "chemsys_n_candidates",
    "chemsys_log_n_candidates",
    "chemsys_n_elements",
    "chemsys_t0_stable_count",
    "chemsys_t0_stable_frac",
    "chemsys_near_hull_25_count",
    "chemsys_near_hull_50_count",
    "chemsys_near_hull_100_count",
    "chemsys_near_hull_200_count",
    "chemsys_near_hull_25_frac",
    "chemsys_near_hull_50_frac",
    "chemsys_near_hull_100_frac",
    "chemsys_near_hull_200_frac",
    "chemsys_t0_margin_mean",
    "chemsys_t0_margin_std",
    "chemsys_t0_margin_min",
    "chemsys_t0_margin_max",
    "chemsys_t0_margin_median",
    "chemsys_t0_margin_ge_010_count",
    "chemsys_t0_margin_ge_020_count",
    "chemsys_t0_margin_ge_050_count",
    "chemsys_raw_score_mean",
    "chemsys_raw_score_max",
    "chemsys_raw_score_std",
    "chemsys_raw_rank_min",
    "chemsys_raw_rank_median",
]
FEATURE_SETS = {
    "candidate_margin_only": CANDIDATE_MARGIN_FEATURES,
    "candidate_t0_score_only": CANDIDATE_FEATURES,
    "chemical_system_exploration_only": SYSTEM_FEATURES,
    "candidate_plus_system": CANDIDATE_FEATURES + SYSTEM_FEATURES,
}
SYSTEM_ABLATION_FEATURE_SETS = {
    "system_size_activity_proxy": [
        "chemsys_n_candidates",
        "chemsys_log_n_candidates",
        "chemsys_n_elements",
        "chemsys_t0_stable_count",
        "chemsys_t0_stable_frac",
    ],
    "system_near_hull_density": [
        "chemsys_near_hull_25_count",
        "chemsys_near_hull_50_count",
        "chemsys_near_hull_100_count",
        "chemsys_near_hull_200_count",
        "chemsys_near_hull_25_frac",
        "chemsys_near_hull_50_frac",
        "chemsys_near_hull_100_frac",
        "chemsys_near_hull_200_frac",
    ],
    "system_margin_distribution": [
        "chemsys_t0_margin_mean",
        "chemsys_t0_margin_std",
        "chemsys_t0_margin_min",
        "chemsys_t0_margin_max",
        "chemsys_t0_margin_median",
        "chemsys_t0_margin_ge_010_count",
        "chemsys_t0_margin_ge_020_count",
        "chemsys_t0_margin_ge_050_count",
    ],
    "system_raw_score_context": [
        "chemsys_raw_score_mean",
        "chemsys_raw_score_max",
        "chemsys_raw_score_std",
        "chemsys_raw_rank_min",
        "chemsys_raw_rank_median",
    ],
}


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


def n_elements(chemical_system: str) -> int:
    return len([x for x in str(chemical_system).split("-") if x])


def bool_to_int(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.astype(int)
    return series.astype(str).str.lower().isin(["true", "1", "yes"]).astype(int)


def load_base() -> pd.DataFrame:
    path = PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv"
    df = pd.read_csv(path)
    df["candidate_id"] = df["candidate_id"].astype(str)
    df["chemical_system"] = df["chemical_system"].astype(str)
    df["t0_e_above_hull_numeric"] = pd.to_numeric(df["t0_e_above_hull"], errors="coerce")
    df["t1_e_above_hull_numeric"] = pd.to_numeric(df["t1_e_above_hull"], errors="coerce")
    df["t0_margin"] = -df["t0_e_above_hull_numeric"]
    df["raw_rank"] = pd.to_numeric(df["raw_rank"], errors="coerce")
    df["raw_score"] = pd.to_numeric(df["raw_score"], errors="coerce")
    df["parc_e_value"] = pd.to_numeric(df["parc_e_value"], errors="coerce")
    df["parc_release_margin"] = pd.to_numeric(df["parc_release_margin"], errors="coerce")
    df["parc_release_seed_count"] = pd.to_numeric(df["parc_release_seed_count"], errors="coerce").fillna(0)
    df["near_hull_25mev_t0_int"] = bool_to_int(df["near_hull_25mev_t0"])
    df["near_hull_50mev_t0_int"] = bool_to_int(df["near_hull_50mev_t0"])
    df["is_release_row"] = bool_to_int(df["parc_released"]) | df["parc_release_seed_count"].gt(0).astype(int)
    df["is_t0_stable_row"] = df["t0_label"].astype(str).eq("stable")
    df["stable_to_unstable_t1"] = df["drift_type"].astype(str).eq("stable_to_unstable").astype(int)
    return df


def add_system_features(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for _, group in df.groupby("K", sort=True):
        group = group.copy()
        group["abs_h0"] = group["t0_e_above_hull_numeric"].abs()
        group["t0_stable_int"] = group["t0_label"].astype(str).eq("stable").astype(int)
        group["near100"] = group["abs_h0"].le(0.100).astype(int)
        group["near200"] = group["abs_h0"].le(0.200).astype(int)
        group["margin_ge_010"] = group["t0_margin"].ge(0.10).astype(int)
        group["margin_ge_020"] = group["t0_margin"].ge(0.20).astype(int)
        group["margin_ge_050"] = group["t0_margin"].ge(0.50).astype(int)
        agg = group.groupby("chemical_system").agg(
            chemsys_n_candidates=("candidate_id", "count"),
            chemsys_t0_stable_count=("t0_stable_int", "sum"),
            chemsys_near_hull_25_count=("near_hull_25mev_t0_int", "sum"),
            chemsys_near_hull_50_count=("near_hull_50mev_t0_int", "sum"),
            chemsys_near_hull_100_count=("near100", "sum"),
            chemsys_near_hull_200_count=("near200", "sum"),
            chemsys_t0_margin_mean=("t0_margin", "mean"),
            chemsys_t0_margin_std=("t0_margin", "std"),
            chemsys_t0_margin_min=("t0_margin", "min"),
            chemsys_t0_margin_max=("t0_margin", "max"),
            chemsys_t0_margin_median=("t0_margin", "median"),
            chemsys_t0_margin_ge_010_count=("margin_ge_010", "sum"),
            chemsys_t0_margin_ge_020_count=("margin_ge_020", "sum"),
            chemsys_t0_margin_ge_050_count=("margin_ge_050", "sum"),
            chemsys_raw_score_mean=("raw_score", "mean"),
            chemsys_raw_score_max=("raw_score", "max"),
            chemsys_raw_score_std=("raw_score", "std"),
            chemsys_raw_rank_min=("raw_rank", "min"),
            chemsys_raw_rank_median=("raw_rank", "median"),
        )
        agg["chemsys_n_elements"] = [n_elements(x) for x in agg.index]
        agg["chemsys_log_n_candidates"] = np.log1p(agg["chemsys_n_candidates"])
        denom = agg["chemsys_n_candidates"].replace(0, np.nan)
        agg["chemsys_t0_stable_frac"] = agg["chemsys_t0_stable_count"] / denom
        for radius in [25, 50, 100, 200]:
            agg[f"chemsys_near_hull_{radius}_frac"] = agg[f"chemsys_near_hull_{radius}_count"] / denom
        group = group.merge(agg.reset_index(), on="chemical_system", how="left")
        rows.append(group)
    out = pd.concat(rows, ignore_index=True)
    out[SYSTEM_FEATURES] = out[SYSTEM_FEATURES].fillna(0)
    return out


def build_model(feature_names: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "prep",
                ColumnTransformer(
                    transformers=[
                        (
                            "num",
                            Pipeline(steps=[("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
                            feature_names,
                        )
                    ],
                    remainder="drop",
                ),
            ),
            ("clf", LogisticRegression(max_iter=5000, class_weight="balanced", solver="liblinear", random_state=RANDOM_STATE)),
        ]
    )


def safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(roc_auc_score(y_true, y_score)) if len(set(y_true.tolist())) == 2 else math.nan


def safe_ap(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(average_precision_score(y_true, y_score)) if len(set(y_true.tolist())) == 2 else float(np.mean(y_true))


def cross_validated_predictions(
    data: pd.DataFrame, feature_set: str, feature_names: list[str], *, n_splits: int | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    n_groups = int(data["chemical_system"].nunique())
    folds = min(n_splits or N_SPLITS, n_groups)
    cv = GroupKFold(n_splits=folds)
    y = data["stable_to_unstable_t1"].astype(int).to_numpy()
    groups = data["chemical_system"].astype(str).to_numpy()
    pred_rows: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []
    for fold, (train_idx, test_idx) in enumerate(cv.split(data[feature_names], y, groups=groups)):
        model = build_model(feature_names)
        model.fit(data.iloc[train_idx][feature_names], y[train_idx])
        pred = model.predict_proba(data.iloc[test_idx][feature_names])[:, 1]
        y_test = y[test_idx]
        fold_df = data.iloc[test_idx][
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
        fold_df["feature_set"] = feature_set
        fold_df["fold"] = fold
        fold_df["predicted_durability_failure_risk"] = pred
        fold_df["evidence_scope"] = SCOPE
        pred_rows.append(fold_df)
        metric_rows.append(
            {
                "feature_set": feature_set,
                "fold": fold,
                "n_test": int(len(test_idx)),
                "n_positive": int(y_test.sum()),
                "positive_rate": float(np.mean(y_test)),
                "roc_auc": safe_auc(y_test, pred),
                "average_precision": safe_ap(y_test, pred),
                "brier_score": float(brier_score_loss(y_test, pred)),
                "feature_names": ";".join(feature_names),
                "cv_scheme": "GroupKFold_by_chemical_system",
                "n_splits": folds,
                "evidence_scope": SCOPE,
            }
        )
    return pd.concat(pred_rows, ignore_index=True), pd.DataFrame(metric_rows)


def summarize_models(metrics: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    base_rate = float(predictions["stable_to_unstable_t1"].mean())
    for feature_set, group in metrics.groupby("feature_set", sort=True):
        pred = predictions[predictions["feature_set"].eq(feature_set)].copy()
        pred = pred.sort_values("predicted_durability_failure_risk", ascending=False)
        top_n = max(1, int(math.ceil(0.20 * len(pred))))
        top = pred.head(top_n)
        bottom = pred.tail(top_n)
        rows.append(
            {
                "feature_set": feature_set,
                "n_rows": int(len(pred)),
                "base_flip_rate": base_rate,
                "mean_roc_auc": float(group["roc_auc"].dropna().mean()) if group["roc_auc"].notna().any() else math.nan,
                "std_roc_auc": float(group["roc_auc"].dropna().std(ddof=1)) if group["roc_auc"].dropna().shape[0] > 1 else math.nan,
                "mean_average_precision": float(group["average_precision"].mean()),
                "std_average_precision": float(group["average_precision"].std(ddof=1)) if len(group) > 1 else math.nan,
                "mean_brier_score": float(group["brier_score"].mean()),
                "top20_risk_flip_rate": float(top["stable_to_unstable_t1"].mean()),
                "bottom20_risk_flip_rate": float(bottom["stable_to_unstable_t1"].mean()),
                "top20_enrichment_vs_base": float(top["stable_to_unstable_t1"].mean() / base_rate) if base_rate else math.nan,
                "feature_names": group["feature_names"].iloc[0],
                "cv_scheme": "GroupKFold_by_chemical_system",
                "evidence_scope": SCOPE,
            }
        )
    out = pd.DataFrame(rows)
    has_margin_reference = out["feature_set"].eq("candidate_margin_only").any()
    margin_auc = float(out.loc[out["feature_set"].eq("candidate_margin_only"), "mean_roc_auc"].iloc[0]) if has_margin_reference else math.nan
    system_auc = (
        float(out.loc[out["feature_set"].eq("chemical_system_exploration_only"), "mean_roc_auc"].iloc[0])
        if out["feature_set"].eq("chemical_system_exploration_only").any()
        else math.nan
    )
    combined_auc = (
        float(out.loc[out["feature_set"].eq("candidate_plus_system"), "mean_roc_auc"].iloc[0])
        if out["feature_set"].eq("candidate_plus_system").any()
        else math.nan
    )
    out["delta_auc_vs_candidate_margin"] = out["mean_roc_auc"] - margin_auc if math.isfinite(margin_auc) else math.nan
    out["system_beats_candidate_margin"] = bool(math.isfinite(system_auc) and math.isfinite(margin_auc) and system_auc >= margin_auc + 0.03)
    out["combined_beats_candidate_margin"] = bool(math.isfinite(combined_auc) and math.isfinite(margin_auc) and combined_auc >= margin_auc + 0.03)
    out["primary_prediction_signal"] = (
        (out["feature_set"].eq("chemical_system_exploration_only"))
        & out["system_beats_candidate_margin"]
        & out["mean_roc_auc"].ge(0.60)
        & out["top20_enrichment_vs_base"].ge(1.25)
    )
    return out


def triage_frontier(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature_set, group in predictions.groupby("feature_set", sort=True):
        group = group.sort_values("predicted_durability_failure_risk", ascending=False).reset_index(drop=True)
        base_rate = float(group["stable_to_unstable_t1"].mean())
        total_flips = int(group["stable_to_unstable_t1"].sum())
        for frac in RISK_TRIAGE_FRACTIONS:
            n_flag = int(math.ceil(frac * len(group)))
            flagged = group.iloc[:n_flag]
            kept = group.iloc[n_flag:]
            kept_rate = float(kept["stable_to_unstable_t1"].mean()) if len(kept) else math.nan
            flagged_rate = float(flagged["stable_to_unstable_t1"].mean()) if len(flagged) else math.nan
            flips_flagged = int(flagged["stable_to_unstable_t1"].sum()) if len(flagged) else 0
            rows.append(
                {
                    "feature_set": feature_set,
                    "flagged_fraction": frac,
                    "n_flagged_high_risk": int(n_flag),
                    "n_kept": int(len(kept)),
                    "base_flip_rate": base_rate,
                    "kept_flip_rate": kept_rate,
                    "flagged_flip_rate": flagged_rate,
                    "relative_flip_rate_reduction_kept": float((base_rate - kept_rate) / base_rate) if base_rate and math.isfinite(kept_rate) else math.nan,
                    "fraction_flips_flagged": float(flips_flagged / total_flips) if total_flips else math.nan,
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows)


def fit_feature_importance(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    y = data["stable_to_unstable_t1"].astype(int).to_numpy()
    for feature_set, feature_names in FEATURE_SETS.items():
        model = build_model(feature_names)
        model.fit(data[feature_names], y)
        coefs = model.named_steps["clf"].coef_[0]
        for feature, coef in zip(feature_names, coefs):
            rows.append(
                {
                    "feature_set": feature_set,
                    "feature": feature,
                    "standardized_logistic_coefficient": float(coef),
                    "abs_standardized_logistic_coefficient": float(abs(coef)),
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows).sort_values(["feature_set", "abs_standardized_logistic_coefficient"], ascending=[True, False])


def feature_provenance_table() -> pd.DataFrame:
    all_sets = {**FEATURE_SETS, **SYSTEM_ABLATION_FEATURE_SETS}
    memberships: dict[str, list[str]] = {}
    for feature_set, features in all_sets.items():
        for feature in features:
            memberships.setdefault(feature, []).append(feature_set)

    def describe(feature: str) -> dict[str, str]:
        if feature in {"raw_rank", "raw_score", "parc_e_value", "parc_release_margin", "parc_release_seed_count", "K"}:
            return {
                "source_columns": feature,
                "time_scope": "t0_release_metadata",
                "availability_scope": "available_at_release_time_after_frozen_PAR C_run".replace("PAR C", "PARC"),
                "leakage_status": "PASS_no_t1_or_post_update_information",
                "deployment_caveat": "requires frozen release run metadata",
            }
        if feature in {"near_hull_25mev_t0_int", "near_hull_50mev_t0_int", "t0_margin", "t0_e_above_hull_numeric"}:
            return {
                "source_columns": "t0_e_above_hull_or_t0_near_hull_flags",
                "time_scope": "t0_public_reference_label",
                "availability_scope": "available_only_when_t0_public_hull_labels_are_available",
                "leakage_status": "PASS_no_t1_or_post_update_information",
                "deployment_caveat": "not label-free; use as versioned public-label durability audit",
            }
        if feature.startswith("chemsys_raw"):
            return {
                "source_columns": "raw_rank/raw_score aggregated within chemical_system at t0",
                "time_scope": "t0_release_metadata_aggregate",
                "availability_scope": "available_at_release_time_from_frozen_queue_scores",
                "leakage_status": "PASS_no_t1_or_post_update_information",
                "deployment_caveat": "queue-local exploration proxy, not external database timestamp activity",
            }
        if feature in {"chemsys_n_candidates", "chemsys_log_n_candidates", "chemsys_n_elements"}:
            return {
                "source_columns": "candidate_id/formula/chemical_system aggregated within frozen t0 queue",
                "time_scope": "t0_candidate_universe_metadata",
                "availability_scope": "available_at_release_time_from_frozen_queue",
                "leakage_status": "PASS_no_t1_or_post_update_information",
                "deployment_caveat": "queue-local exploration proxy, not external database timestamp activity",
            }
        return {
            "source_columns": "t0_e_above_hull/t0_label aggregated within chemical_system at t0",
            "time_scope": "t0_public_reference_label_aggregate",
            "availability_scope": "available_only_when_t0_public_hull_labels_are_available",
            "leakage_status": "PASS_no_t1_or_post_update_information_SCOPE_WARN_t0_label_dependent",
            "deployment_caveat": "not label-free; does not use t1 but depends on t0 public reference labels",
        }

    rows = []
    for feature in sorted(memberships):
        row = {
            "feature": feature,
            "feature_sets": ";".join(sorted(memberships[feature])),
            **describe(feature),
            "forbidden_sources_absent": "t1_labels;t1_e_above_hull;stable_to_unstable_label;post_t0_entry_counts",
            "evidence_scope": SCOPE,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def run_model_family(data: pd.DataFrame, feature_sets: dict[str, list[str]], *, prefix: str = "") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_tables: list[pd.DataFrame] = []
    metric_tables: list[pd.DataFrame] = []
    for feature_set, feature_names in feature_sets.items():
        name = f"{prefix}{feature_set}" if prefix else feature_set
        pred, metrics = cross_validated_predictions(data, name, feature_names)
        prediction_tables.append(pred)
        metric_tables.append(metrics)
    predictions = pd.concat(prediction_tables, ignore_index=True)
    metrics = pd.concat(metric_tables, ignore_index=True)
    summary = summarize_models(metrics, predictions)
    return predictions, metrics, summary


def by_k_model_comparison(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for k, group in data.groupby("K", sort=True):
        if group["chemical_system"].nunique() < 5 or group["stable_to_unstable_t1"].nunique() < 2:
            continue
        _, _, summary = run_model_family(group, FEATURE_SETS)
        summary.insert(0, "K", int(k))
        rows.append(summary)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def write_text_files(queue_hash: str, summary: pd.DataFrame) -> None:
    positive = bool(summary["primary_prediction_signal"].astype(bool).any())
    best = summary.sort_values(["primary_prediction_signal", "mean_roc_auc", "top20_enrichment_vs_base"], ascending=False).iloc[0]
    prereg = f"""# Phase67c Durability-Risk Prediction Preregistration

Status: executed as a t0-feature prediction diagnostic on frozen Phase51
candidate rows. This is not a release certificate, prospective discovery or DFT
evidence.

## Frozen inputs

- Candidate source: Phase51 t1 candidate explanation table.
- Input hash: `{queue_hash}`.
- Population: PARC released candidates at K=300/500 that were stable at t0.
- Label: `stable_to_unstable` at the current-MP t1 reference.
- Primary split: GroupKFold by chemical system.

## Feature families

- Candidate margin only.
- Candidate t0 score/release metadata only.
- Chemical-system exploration/crowding proxies computed from t0 rows only.
- Candidate plus system features.

No t1 labels, t1 near-hull flags, drift labels or post-update features are used
as predictors. Several system-level predictors depend on t0 public hull labels;
these are valid for a versioned public-label durability audit but should not be
described as label-free deployment features.
"""
    (PHASE67C / "DURABILITY_RISK_PREDICTION_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")
    readme = f"""# Phase67c Durability-Risk Prediction

Status: `completed_durability_risk_prediction_diagnostic`.

This experiment asks whether t0-time features can predict which t0-stable PARC
release candidates later become unstable under the current-MP t1 reference.

Primary prediction signal allowed: `{str(positive).lower()}`.

Best model by primary-signal/AUC ordering:

- feature set: `{best['feature_set']}`
- mean group-CV ROC-AUC: `{best['mean_roc_auc']}`
- mean average precision: `{best['mean_average_precision']}`
- top-20% enrichment vs base: `{best['top20_enrichment_vs_base']}`
- delta AUC vs candidate-margin baseline: `{best['delta_auc_vs_candidate_margin']}`

Allowed claim:

- Durability risk can be audited as a t0-time prediction problem.

Guardrails:

- no release certificate;
- no prospective materials discovery;
- no DFT evidence;
- no t1 features used as predictors;
- t0-public-label-dependent system features are scoped as durability-audit
  features, not label-free deployment features;
- report candidate-only, system-only and combined models together.
"""
    (PHASE67C / "README_evidence_scope.md").write_text(readme, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase67c_durability_risk_prediction"]
    rows.append(
        {
            "milestone": "ncs_phase67c_durability_risk_prediction",
            "path": "outputs/milestones/ncs_phase67c_durability_risk_prediction/",
            "evidence_state": "completed_durability_risk_prediction_diagnostic",
            "manifest": "outputs/milestones/ncs_phase67c_durability_risk_prediction/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase67c_durability_risk_prediction",
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


def update_evidence_ledger(summary: pd.DataFrame) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "DUR-RISK-001"]
    positive = bool(summary["primary_prediction_signal"].astype(bool).any())
    rows.append(
        {
            "claim_id": "DUR-RISK-001",
            "claim_text": "Durability failure after reference drift is evaluated as a t0-time candidate/system risk-prediction problem.",
            "evidence_type": "durability_risk_prediction_diagnostic",
            "positive_evidence": "yes" if positive else "partial",
            "scope": "prediction_diagnostic_not_release_certificate",
            "artifact_path": "outputs/milestones/ncs_phase67c_durability_risk_prediction/table_durability_risk_prediction_model_comparison.csv",
            "hash": sha256_file(PHASE67C / "table_durability_risk_prediction_model_comparison.csv"),
            "validation_command": "make reproduce-ncs-phase67c-durability-risk-prediction",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_release_certificate_DFT_evidence_or_prospective_materials_discovery",
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


def assert_no_t1_feature_leakage() -> None:
    all_features = {**FEATURE_SETS, **SYSTEM_ABLATION_FEATURE_SETS}
    feature_blob = ";".join(sum((v for v in all_features.values()), []))
    forbidden = ["t1", "drift", "stable_to_unstable", "failure", "label"]
    bad = [token for token in forbidden if re.search(token, feature_blob, flags=re.IGNORECASE)]
    if bad:
        raise RuntimeError(f"forbidden post-update feature token(s): {bad}")


def main() -> None:
    assert_no_t1_feature_leakage()
    PHASE67C.mkdir(parents=True, exist_ok=True)
    input_path = PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv"
    input_hash = sha256_file(input_path)
    base = add_system_features(load_base())
    data = base[base["is_release_row"].astype(bool) & base["is_t0_stable_row"].astype(bool)].copy()
    data = data[data["stable_to_unstable_t1"].notna()].copy()
    predictions, metrics, summary = run_model_family(data, FEATURE_SETS)
    ablation_predictions, ablation_metrics, ablation_summary = run_model_family(data, SYSTEM_ABLATION_FEATURE_SETS)
    by_k_summary = by_k_model_comparison(data)
    triage = triage_frontier(predictions)
    importance = fit_feature_importance(data)
    provenance_table = feature_provenance_table()
    figure_inputs = pd.concat(
        [
            summary.assign(panel="model_comparison"),
            triage.assign(panel="risk_triage_frontier"),
        ],
        ignore_index=True,
        sort=False,
    )
    population = pd.DataFrame(
        [
            {
                "population": "t0_stable_PARCrelease_K300_K500_rows",
                "n_rows": int(len(data)),
                "n_chemical_systems": int(data["chemical_system"].nunique()),
                "n_positive_stable_to_unstable": int(data["stable_to_unstable_t1"].sum()),
                "positive_rate": float(data["stable_to_unstable_t1"].mean()),
                "K_values": ";".join(str(x) for x in sorted(data["K"].unique())),
                "evidence_scope": SCOPE,
            }
        ]
    )

    predictions.to_csv(PHASE67C / "table_durability_risk_group_cv_predictions.csv", index=False)
    metrics.to_csv(PHASE67C / "table_durability_risk_cv_fold_metrics.csv", index=False)
    summary.to_csv(PHASE67C / "table_durability_risk_prediction_model_comparison.csv", index=False)
    ablation_predictions.to_csv(PHASE67C / "table_durability_risk_ablation_predictions.csv", index=False)
    ablation_metrics.to_csv(PHASE67C / "table_durability_risk_ablation_fold_metrics.csv", index=False)
    ablation_summary.to_csv(PHASE67C / "table_durability_risk_ablation_model_comparison.csv", index=False)
    by_k_summary.to_csv(PHASE67C / "table_durability_risk_by_k_model_comparison.csv", index=False)
    triage.to_csv(PHASE67C / "table_durability_risk_triage_frontier.csv", index=False)
    importance.to_csv(PHASE67C / "table_durability_risk_feature_importance.csv", index=False)
    provenance_table.to_csv(PHASE67C / "table_durability_risk_feature_provenance.csv", index=False)
    population.to_csv(PHASE67C / "table_durability_risk_population.csv", index=False)
    figure_inputs.to_csv(PHASE67C / "figure_durability_risk_prediction_inputs.csv", index=False)
    write_text_files(input_hash, summary)

    provenance = {
        "status": "completed_durability_risk_prediction_diagnostic",
        "input_table": rel(input_path),
        "input_sha256": input_hash,
        "population_rows": int(len(data)),
        "chemical_systems": int(data["chemical_system"].nunique()),
        "positive_rate": float(data["stable_to_unstable_t1"].mean()),
        "feature_sets": list(FEATURE_SETS),
        "cv_scheme": "GroupKFold_by_chemical_system",
        "headline_positive_allowed": bool(summary["primary_prediction_signal"].astype(bool).any()),
        "scope": SCOPE,
    }
    (PHASE67C / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    update_artifact_index()
    update_evidence_ledger(summary)
    write_manifest(PHASE67C)
    write_root_manifest()
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
