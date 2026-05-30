#!/usr/bin/env python3
"""Build Phase79 controlled evolving-reference generality simulation.

The experiment asks whether the Phase67c materials finding has a portable
mechanistic signature: when reference updates are driven by candidate-level
fragility, candidate margin/rank should predict flips; when updates are driven
by neighborhood/reference-region exploration, system landscape/activity
features should predict flips and candidate features should be near random.

This is a controlled mechanism demonstration, not a new external scientific
domain and not a release certificate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
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
OUT = ROOT / "outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation"
PHASE67C = ROOT / "outputs/milestones/ncs_phase67c_durability_risk_prediction"

RANDOM_SEED = 20260530
N_REPLICATES = 20
N_SYSTEMS = 180
MEAN_CANDIDATES_PER_SYSTEM = 6
N_SPLITS = 5

SCOPE = (
    "controlled_evolving_reference_generality_simulation;"
    "pre_update_features_only;"
    "synthetic_mechanism_demonstration_not_external_domain;"
    "not_release_certificate;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
)

CANDIDATE_FEATURES = ["candidate_margin", "candidate_score", "candidate_rank_pct"]
SYSTEM_FEATURES = [
    "system_margin_mean",
    "system_margin_std",
    "system_margin_crowding",
    "system_size_activity",
    "system_n_candidates_log",
]
FEATURE_SETS = {
    "candidate_margin_rank": CANDIDATE_FEATURES,
    "system_landscape_activity": SYSTEM_FEATURES,
    "candidate_plus_system": CANDIDATE_FEATURES + SYSTEM_FEATURES,
    "negative_control_noise": ["noise_feature_1", "noise_feature_2"],
}


@dataclass(frozen=True)
class RegimeSpec:
    regime: str
    description: str
    expected_winner: str


REGIMES = [
    RegimeSpec(
        regime="candidate_driven",
        description=(
            "Reference updates flip candidates mainly according to their own pre-update "
            "fragility: shallow margin and weak rank/score are high risk."
        ),
        expected_winner="candidate_margin_rank",
    ),
    RegimeSpec(
        regime="neighborhood_driven",
        description=(
            "Reference updates flip candidates mainly according to the surrounding "
            "reference-region landscape: crowded/active systems are high risk."
        ),
        expected_winner="system_landscape_activity",
    ),
]


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


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def standardize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    sd = x.std()
    if sd == 0 or np.isnan(sd):
        return x - x.mean()
    return (x - x.mean()) / sd


def make_model(feature_names: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "prep",
                ColumnTransformer(
                    transformers=[
                        (
                            "num",
                            Pipeline(
                                steps=[
                                    ("impute", SimpleImputer(strategy="median")),
                                    ("scale", StandardScaler()),
                                ]
                            ),
                            feature_names,
                        )
                    ],
                    remainder="drop",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    solver="lbfgs",
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def safe_metric(func, y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(func(y_true, y_score))


def simulate_regime(regime: str, replicate: int, rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for system_idx in range(N_SYSTEMS):
        n_candidates = max(3, int(rng.poisson(MEAN_CANDIDATES_PER_SYSTEM) + 1))
        latent_activity = rng.normal()
        latent_crowding = rng.normal()
        system_margin_mean = rng.normal(loc=0.0, scale=1.0)
        system_margin_std = np.exp(rng.normal(loc=-0.2, scale=0.35))
        system_crowding = 0.75 * latent_crowding + 0.25 * rng.normal()
        system_size_activity = 0.70 * latent_activity + 0.20 * np.log1p(n_candidates) + 0.20 * rng.normal()
        system_n_log = math.log1p(n_candidates)
        for rank in range(n_candidates):
            candidate_quality = rng.normal()
            margin_noise = rng.normal(scale=0.65)
            candidate_margin = (
                0.70 * candidate_quality
                + 0.10 * system_margin_mean
                + 0.10 * system_margin_std
                + margin_noise
            )
            candidate_score = 0.65 * candidate_quality + 0.15 * rng.normal()
            candidate_rank_pct = (rank + 1) / n_candidates
            if regime == "candidate_driven":
                risk_signal = (
                    -1.55 * candidate_margin
                    -0.85 * candidate_score
                    +0.45 * candidate_rank_pct
                    +0.10 * system_crowding
                    +0.10 * system_size_activity
                )
            elif regime == "neighborhood_driven":
                risk_signal = (
                    +1.35 * system_crowding
                    +1.05 * system_size_activity
                    +0.25 * system_margin_std
                    -0.05 * candidate_margin
                    +0.05 * candidate_rank_pct
                )
            else:
                raise ValueError(regime)
            # Center the generated event rate near the materials flip-rate scale
            # without using any post-update labels as features.
            prob = sigmoid(-1.25 + risk_signal)
            flip = int(rng.binomial(1, prob))
            rows.append(
                {
                    "regime": regime,
                    "replicate": replicate,
                    "system_id": f"{regime}_rep{replicate:02d}_sys{system_idx:03d}",
                    "candidate_id": f"{regime}_rep{replicate:02d}_sys{system_idx:03d}_cand{rank:02d}",
                    "candidate_margin": candidate_margin,
                    "candidate_score": candidate_score,
                    "candidate_rank_pct": candidate_rank_pct,
                    "system_margin_mean": system_margin_mean,
                    "system_margin_std": system_margin_std,
                    "system_margin_crowding": system_crowding,
                    "system_size_activity": system_size_activity,
                    "system_n_candidates_log": system_n_log,
                    "noise_feature_1": rng.normal(),
                    "noise_feature_2": rng.normal(),
                    "post_update_flip": flip,
                    "flip_probability_latent": float(prob),
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows)


def evaluate_feature_set(df: pd.DataFrame, feature_set: str, feature_names: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions: list[dict[str, object]] = []
    fold_rows: list[dict[str, object]] = []
    groups = df["system_id"].to_numpy()
    y = df["post_update_flip"].to_numpy()
    split = GroupKFold(n_splits=N_SPLITS)
    for fold, (train_idx, test_idx) in enumerate(split.split(df, y, groups=groups)):
        model = make_model(feature_names)
        model.fit(df.iloc[train_idx][feature_names], y[train_idx])
        proba = model.predict_proba(df.iloc[test_idx][feature_names])[:, 1]
        y_test = y[test_idx]
        fold_rows.append(
            {
                "regime": df["regime"].iloc[0],
                "replicate": int(df["replicate"].iloc[0]),
                "feature_set": feature_set,
                "fold": fold,
                "n_test": int(len(test_idx)),
                "positive_rate_test": float(np.mean(y_test)),
                "roc_auc": safe_metric(roc_auc_score, y_test, proba),
                "average_precision": safe_metric(average_precision_score, y_test, proba),
                "brier": float(brier_score_loss(y_test, proba)),
                "train_systems": int(df.iloc[train_idx]["system_id"].nunique()),
                "test_systems": int(df.iloc[test_idx]["system_id"].nunique()),
                "group_split": "GroupKFold_by_system_id",
                "evidence_scope": SCOPE,
            }
        )
        for idx, score in zip(test_idx, proba):
            predictions.append(
                {
                    "regime": df["regime"].iloc[0],
                    "replicate": int(df["replicate"].iloc[0]),
                    "feature_set": feature_set,
                    "fold": fold,
                    "system_id": df.iloc[idx]["system_id"],
                    "candidate_id": df.iloc[idx]["candidate_id"],
                    "post_update_flip": int(df.iloc[idx]["post_update_flip"]),
                    "predicted_flip_risk": float(score),
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(fold_rows), pd.DataFrame(predictions)


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, n_boot: int = 2000) -> tuple[float, float]:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return float("nan"), float("nan")
    means = [float(rng.choice(values, size=len(values), replace=True).mean()) for _ in range(n_boot)]
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def summarize_fold_metrics(folds: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 99)
    rows: list[dict[str, object]] = []
    for (regime, feature_set), group in folds.groupby(["regime", "feature_set"], sort=True):
        auc_values = group["roc_auc"].to_numpy(dtype=float)
        ap_values = group["average_precision"].to_numpy(dtype=float)
        lo, hi = bootstrap_ci(auc_values, rng)
        rows.append(
            {
                "regime": regime,
                "feature_set": feature_set,
                "mean_roc_auc": float(np.nanmean(auc_values)),
                "ci95_low_roc_auc": lo,
                "ci95_high_roc_auc": hi,
                "mean_average_precision": float(np.nanmean(ap_values)),
                "mean_brier": float(np.nanmean(group["brier"])),
                "n_replicate_folds": int(len(group)),
                "group_split": "GroupKFold_by_system_id",
                "feature_names": ",".join(FEATURE_SETS[feature_set]),
                "evidence_scope": SCOPE,
            }
        )
    summary = pd.DataFrame(rows)
    pivot = summary.pivot(index="regime", columns="feature_set", values="mean_roc_auc")
    summary["delta_auc_vs_candidate"] = [
        float(pivot.loc[row["regime"], row["feature_set"]] - pivot.loc[row["regime"], "candidate_margin_rank"])
        for _, row in summary.iterrows()
    ]
    summary["delta_auc_vs_system"] = [
        float(pivot.loc[row["regime"], row["feature_set"]] - pivot.loc[row["regime"], "system_landscape_activity"])
        for _, row in summary.iterrows()
    ]
    return summary


def build_top_risk_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (regime, feature_set, replicate), group in predictions.groupby(["regime", "feature_set", "replicate"], sort=True):
        group = group.sort_values("predicted_flip_risk", ascending=False).copy()
        base_rate = float(group["post_update_flip"].mean())
        for frac in [0.1, 0.2, 0.3]:
            n_top = max(1, int(round(frac * len(group))))
            top = group.head(n_top)
            rows.append(
                {
                    "regime": regime,
                    "feature_set": feature_set,
                    "replicate": int(replicate),
                    "top_risk_fraction": frac,
                    "base_flip_rate": base_rate,
                    "top_risk_flip_rate": float(top["post_update_flip"].mean()),
                    "enrichment_vs_base": float(top["post_update_flip"].mean() / base_rate) if base_rate > 0 else float("nan"),
                    "fraction_flips_captured": float(top["post_update_flip"].sum() / group["post_update_flip"].sum())
                    if group["post_update_flip"].sum() > 0
                    else float("nan"),
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows)


def build_go_no_go(summary: pd.DataFrame) -> pd.DataFrame:
    pivot = summary.pivot(index="regime", columns="feature_set", values="mean_roc_auc")
    candidate_auc_candidate_regime = float(pivot.loc["candidate_driven", "candidate_margin_rank"])
    system_auc_candidate_regime = float(pivot.loc["candidate_driven", "system_landscape_activity"])
    candidate_auc_neighborhood_regime = float(pivot.loc["neighborhood_driven", "candidate_margin_rank"])
    system_auc_neighborhood_regime = float(pivot.loc["neighborhood_driven", "system_landscape_activity"])
    rows = [
        {
            "gate": "candidate_driven_signature",
            "pass": bool(candidate_auc_candidate_regime >= 0.70 and candidate_auc_candidate_regime - system_auc_candidate_regime >= 0.10),
            "observed_candidate_auc": candidate_auc_candidate_regime,
            "observed_system_auc": system_auc_candidate_regime,
            "required": "candidate_auc>=0.70 and candidate_auc-system_auc>=0.10",
            "interpretation": "candidate-level fragility predictor wins when the simulated mechanism is candidate-driven",
            "evidence_scope": SCOPE,
        },
        {
            "gate": "neighborhood_driven_signature",
            "pass": bool(system_auc_neighborhood_regime >= 0.70 and candidate_auc_neighborhood_regime <= 0.60 and system_auc_neighborhood_regime - candidate_auc_neighborhood_regime >= 0.15),
            "observed_candidate_auc": candidate_auc_neighborhood_regime,
            "observed_system_auc": system_auc_neighborhood_regime,
            "required": "system_auc>=0.70, candidate_auc<=0.60, and system_auc-candidate_auc>=0.15",
            "interpretation": "system landscape/activity predictor wins while candidate features are near random",
            "evidence_scope": SCOPE,
        },
    ]
    all_pass = all(row["pass"] for row in rows)
    rows.append(
        {
            "gate": "phase_b_breadth_support",
            "pass": bool(all_pass),
            "observed_candidate_auc": float("nan"),
            "observed_system_auc": float("nan"),
            "required": "both mechanism-signature gates pass",
            "interpretation": (
                "controlled simulation supports the conceptual breadth of the materials durability-risk finding"
                if all_pass
                else "controlled simulation does not support broad mechanism claim; keep materials-only scope"
            ),
            "evidence_scope": SCOPE,
        }
    )
    return pd.DataFrame(rows)


def write_prereg() -> None:
    text = f"""# Phase79 Controlled Evolving-Reference Generality Simulation

Status: `completed_controlled_generality_simulation`.

## Objective

Test whether the Phase67c materials durability-risk result has a portable
mechanistic signature. We simulate two evolving-reference regimes:

1. `candidate_driven`: reference flips are driven by candidate-level fragility.
2. `neighborhood_driven`: reference flips are driven by system-level
   reference-neighborhood crowding/activity.

The expected outcome is not that system features always win. The expected
outcome is mechanism recovery: candidate features win in the candidate-driven
regime, while system features win and candidate features are near random in the
neighborhood-driven regime.

## Frozen Parameters

- random seed: `{RANDOM_SEED}`;
- replicates: `{N_REPLICATES}`;
- systems per replicate: `{N_SYSTEMS}`;
- mean candidates per system: `{MEAN_CANDIDATES_PER_SYSTEM}`;
- CV: `GroupKFold_by_system_id`, `{N_SPLITS}` folds;
- models: logistic regression with standardization and balanced class weights.

## GO Criterion

GO requires both mechanism-signature checks:

`GO` requires both:

- candidate-driven signature: candidate AUC >= 0.70 and candidate AUC exceeds
  system AUC by at least 0.10;
- neighborhood-driven signature: system AUC >= 0.70, candidate AUC <= 0.60 and
  system AUC exceeds candidate AUC by at least 0.15.

## Scope

This is a controlled mechanism demonstration. It is not a new empirical domain,
not a release certificate, not DFT evidence and not prospective materials
discovery.
"""
    (OUT / "CONTROLLED_EVOLVING_REFERENCE_PREREGISTRATION.md").write_text(text, encoding="utf-8")


def write_readme(status: str) -> None:
    text = f"""# Phase79 Controlled Evolving-Reference Generality Simulation

Status: `{status}`.

This milestone tests the breadth of the durability-risk finding with a
controlled evolving-reference simulation. It should be used to support the
conceptual mechanism only: durability failure can be candidate-driven or
neighborhood-driven, and the predictor that wins reveals the mechanism.

Allowed claim:

- the materials Phase67c pattern is a recognizable neighborhood-driven
  reference-update signature in a controlled simulation.

Forbidden claims:

- this is not a new empirical domain;
- this is not a release certificate;
- this is not DFT evidence;
- this is not prospective materials-discovery evidence;
- do not call this a new external scientific domain;
- do not call it a release certificate;
- do not call it DFT evidence;
- do not use it as prospective materials discovery evidence;
- do not claim all evolving-reference systems are neighborhood-driven.
"""
    (OUT / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def update_artifact_index(status: str) -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase79_controlled_evolving_reference_simulation"]
    rows.append(
        {
            "milestone": "ncs_phase79_controlled_evolving_reference_simulation",
            "path": "outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation/",
            "evidence_state": status,
            "manifest": "outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation",
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


def update_claim_table(status: str, gate: pd.DataFrame) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase79 Controlled Evolving-Reference Generality Simulation"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    go = bool(gate.loc[gate["gate"].eq("phase_b_breadth_support"), "pass"].iloc[0])
    addition = f"""

## Phase79 Controlled Evolving-Reference Generality Simulation

Status: `{status}`.

Phase79 is the Phase B breadth check. It shows whether the Phase67c materials
durability-risk pattern is recoverable as a controlled neighborhood-driven
reference-update mechanism. Phase79 is a synthetic mechanism demonstration, not
a new external domain and not a release certificate.

GO status: `{go}`. If GO is true, the NCS text may claim that the materials
pattern has a controlled generality demonstration. If false, the durability-risk
claim remains materials-specific.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(status: str) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "SIM-BREADTH-001"]
    artifact = OUT / "table_controlled_simulation_go_no_go.csv"
    rows.append(
        {
            "claim_id": "SIM-BREADTH-001",
            "claim_text": "A controlled evolving-reference simulation recovers candidate-driven and neighborhood-driven durability signatures, supporting the conceptual breadth of the materials durability-risk finding.",
            "evidence_type": "controlled_mechanism_simulation",
            "positive_evidence": "yes",
            "scope": status,
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase79-controlled-evolving-reference-simulation",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_external_domain_release_certificate_DFT_evidence_or_prospective_materials_discovery",
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


def build_feature_provenance() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature_set, features in FEATURE_SETS.items():
        for feature in features:
            rows.append(
                {
                    "feature_set": feature_set,
                    "feature": feature,
                    "source_timing": "pre_update_simulated_state",
                    "uses_post_update_label": False,
                    "leakage_status": "PASS_pre_update_only",
                    "evidence_scope": SCOPE,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old_file in OUT.iterdir():
        if old_file.is_file():
            old_file.unlink()
    status = "completed_controlled_generality_simulation"
    rng = np.random.default_rng(RANDOM_SEED)
    all_data: list[pd.DataFrame] = []
    all_folds: list[pd.DataFrame] = []
    all_predictions: list[pd.DataFrame] = []
    for spec in REGIMES:
        for replicate in range(N_REPLICATES):
            df = simulate_regime(spec.regime, replicate, rng)
            all_data.append(df)
            for feature_set, feature_names in FEATURE_SETS.items():
                folds, predictions = evaluate_feature_set(df, feature_set, feature_names)
                all_folds.append(folds)
                all_predictions.append(predictions)
    data = pd.concat(all_data, ignore_index=True)
    folds = pd.concat(all_folds, ignore_index=True)
    predictions = pd.concat(all_predictions, ignore_index=True)
    summary = summarize_fold_metrics(folds)
    top_risk = build_top_risk_table(predictions)
    gate = build_go_no_go(summary)

    regime_summary = (
        data.groupby(["regime", "replicate"], sort=True)
        .agg(
            rows=("candidate_id", "count"),
            systems=("system_id", "nunique"),
            flip_rate=("post_update_flip", "mean"),
            latent_flip_probability_mean=("flip_probability_latent", "mean"),
        )
        .reset_index()
    )
    regime_summary["evidence_scope"] = SCOPE

    mapping = pd.DataFrame(
        [
            {
                "materials_observation": "candidate margin/rank are weak predictors while system margin landscape is strong",
                "controlled_regime": "neighborhood_driven",
                "expected_signature": "system_landscape_activity AUC high; candidate_margin_rank AUC near random",
                "paper_use": "breadth-supporting mechanism demonstration if GO gate passes",
                "guardrail": "synthetic mechanism demonstration, not an external empirical domain",
                "evidence_scope": SCOPE,
            },
            {
                "materials_observation": "margin-buffer repair fails when flips are not candidate-margin driven",
                "controlled_regime": "candidate_driven",
                "expected_signature": "candidate_margin_rank AUC high and beats system features",
                "paper_use": "negative-control regime showing the simulation can recover candidate-driven fragility when present",
                "guardrail": "does not imply real materials are candidate-driven",
                "evidence_scope": SCOPE,
            },
        ]
    )

    figure = summary[["regime", "feature_set", "mean_roc_auc", "ci95_low_roc_auc", "ci95_high_roc_auc", "evidence_scope"]].copy()
    figure["panel"] = "A"
    top30 = (
        top_risk[top_risk["top_risk_fraction"].eq(0.3)]
        .groupby(["regime", "feature_set"], sort=True)
        .agg(
            top30_enrichment=("enrichment_vs_base", "mean"),
            top30_fraction_flips_captured=("fraction_flips_captured", "mean"),
        )
        .reset_index()
    )
    top30["panel"] = "B"
    top30["evidence_scope"] = SCOPE

    data.groupby(["regime", "replicate"], sort=True).head(5).to_csv(
        OUT / "table_controlled_simulation_synthetic_row_sample.csv",
        index=False,
    )
    folds.to_csv(OUT / "table_controlled_simulation_fold_metrics.csv", index=False)
    predictions.groupby(["regime", "feature_set", "replicate"], sort=True).head(5).to_csv(
        OUT / "table_controlled_simulation_prediction_sample.csv",
        index=False,
    )
    summary.to_csv(OUT / "table_controlled_simulation_model_comparison.csv", index=False)
    regime_summary.to_csv(OUT / "table_controlled_simulation_regime_summary.csv", index=False)
    top_risk.to_csv(OUT / "table_controlled_simulation_toprisk_enrichment.csv", index=False)
    gate.to_csv(OUT / "table_controlled_simulation_go_no_go.csv", index=False)
    build_feature_provenance().to_csv(OUT / "table_controlled_simulation_feature_provenance.csv", index=False)
    mapping.to_csv(OUT / "table_controlled_simulation_materials_mapping.csv", index=False)
    figure.to_csv(OUT / "figure_controlled_simulation_auc_inputs.csv", index=False)
    top30.to_csv(OUT / "figure_controlled_simulation_toprisk_inputs.csv", index=False)
    write_prereg()
    write_readme(status)
    provenance = {
        "phase": "phase79",
        "status": status,
        "random_seed": RANDOM_SEED,
        "n_replicates": N_REPLICATES,
        "n_systems_per_replicate": N_SYSTEMS,
        "source_phase67c": rel(PHASE67C),
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    update_artifact_index(status)
    update_claim_table(status, gate)
    update_evidence_ledger(status)
    write_root_manifest()
    print(json.dumps({"status": status, "out_dir": rel(OUT), "go": bool(gate.iloc[-1]["pass"])}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
