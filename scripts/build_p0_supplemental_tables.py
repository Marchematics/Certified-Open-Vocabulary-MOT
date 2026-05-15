#!/usr/bin/env python3
"""Build P0 supplemental tables for the release-certification paper.

Outputs:
  * Materials modern-model sensitivity using public ALIGNN-FF WBM predictions.
  * Minimal PU / selective-conformal baseline matrix.
  * iWildCam second-review blind package and status table.
  * Runtime / compute overhead table for the main scientific domains.

The script writes only public-safe CSV/JSON/MD artifacts.  Raw images, raw
structures, model weights, and private caches are not copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_materials_discovery_parc_flagship as materials  # noqa: E402


ALIGNN_FF_URL = (
    "https://raw.githubusercontent.com/janosh/matbench-discovery/main/models/"
    "alignn_ff/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz"
)
DEFAULT_SEEDS = list(range(20))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def ensure_alignn_predictions(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    urllib.request.urlretrieve(ALIGNN_FF_URL, path)


def bootstrap_ci(values: np.ndarray, seed: int = 20260515, n_boot: int = 3000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    boot = [float(values[rng.integers(0, len(values), len(values))].mean()) for _ in range(n_boot)]
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def add_modern_materials_score(frame: pd.DataFrame, prediction_path: Path) -> pd.DataFrame:
    modern = pd.read_csv(prediction_path, usecols=["material_id", "e_form_per_atom_alignn_ff"])
    out = frame.merge(modern, on="material_id", how="inner").copy()
    hull_reference = (
        out["e_form_per_atom_mp2020_corrected"].astype(float)
        - out["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    )
    out["modern_predicted_e_above_hull"] = out["e_form_per_atom_alignn_ff"].astype(float) - hull_reference
    out["modern_score"] = -out["modern_predicted_e_above_hull"]
    return out


def build_materials_modern_sensitivity(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    ensure_alignn_predictions(Path(args.modern_predictions))
    frame, _meta = materials.load_materials_inputs(args)
    frame = add_modern_materials_score(frame, Path(args.modern_predictions))
    started = time.perf_counter()
    rows = materials.run_grid(
        frame,
        source="alignn_ff_modern_learned_materials_model",
        score_col="modern_score",
        block_col="composition_family_pair",
        rhos=[0.10],
        alphas=[0.10],
        budgets=[50, 100, 300, 500, 1000, 5000],
        seeds=DEFAULT_SEEDS,
        observed_strategy="top_score",
    )
    runtime = time.perf_counter() - started
    out_dir = Path(args.materials_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_path = out_dir / "table_materials_modern_model_sensitivity_seed_rows.csv"
    rows.to_csv(seed_path, index=False)
    summary = materials.summarize_grid(
        rows,
        ["proposal_source", "block_definition", "rho", "observed_positive_strategy", "alpha", "K"],
    )
    summary["modern_model_role"] = summary.apply(
        lambda row: (
            "modern_source_strict_alpha010_release"
            if int(row["non_empty_seeds"]) >= 18 and float(row["actual_FTR_mean"]) <= 0.10
            else "modern_source_release_or_refusal_sensitivity"
        ),
        axis=1,
    )
    summary["paper_interpretation"] = summary.apply(
        lambda row: (
            "stronger_source_supports_larger_or_lower_FTR_release"
            if float(row["raw_topK_actual_FTR_mean"]) > float(row["actual_FTR_mean"])
            else "modern_source_quality_sensitivity"
        ),
        axis=1,
    )
    summary_path = out_dir / "table_materials_modern_model_sensitivity.csv"
    summary.to_csv(summary_path, index=False)
    report = pd.DataFrame(
        [
            {
                "proposal_source": "alignn_ff_modern_learned_materials_model",
                "model_family": "ALIGNN-FF",
                "prediction_file_public_url": ALIGNN_FF_URL,
                "prediction_file_sha256": sha256_file(Path(args.modern_predictions)),
                "prediction_column": "e_form_per_atom_alignn_ff",
                "score_definition": "-(ALIGNN-FF predicted formation energy - WBM hull reference energy)",
                "trained_for_this_PARC_experiment": False,
                "uses_DFT_target_label_for_ranking": False,
                "runtime_sec_for_grid": runtime,
            }
        ]
    )
    report_path = out_dir / "table_materials_modern_model_report.csv"
    report.to_csv(report_path, index=False)
    return summary_path, seed_path, report_path


def observed_positive_indices(labels: np.ndarray, scores: np.ndarray, rho: float = 0.10) -> np.ndarray:
    positive = np.flatnonzero(labels.astype(bool))
    n = int(round(len(positive) * rho))
    order = positive[np.argsort(scores[positive])[::-1]]
    return order[:n]


def pu_plugin_release(
    scores: np.ndarray,
    labels: np.ndarray,
    observed_idx: np.ndarray,
    alpha: float,
    K: int,
    prior_multiplier: float,
) -> dict:
    n = len(scores)
    observed = np.zeros(n, dtype=bool)
    observed[observed_idx] = True
    unlabeled = ~observed
    x = scores.reshape(-1, 1).astype(float)
    y = observed.astype(int)
    if y.sum() == 0 or y.sum() == len(y):
        posterior = np.zeros(n, dtype=float)
    else:
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
        clf.fit(x, y)
        prop = clf.predict_proba(x)[:, 1]
        c_hat = float(np.clip(prop[observed].mean(), 1e-6, 1.0)) if observed.any() else 1.0
        posterior = np.clip((prop / c_hat) * prior_multiplier, 0.0, 1.0)
    order = np.argsort(posterior)[::-1]
    eligible = order[posterior[order] >= (1.0 - alpha)]
    if len(eligible) == 0:
        selected = order[:0]
    else:
        selected = eligible[:K]
    if len(selected) == 0:
        return {"release_size": 0, "FTR": 0.0, "threshold": 1.0 - alpha}
    return {
        "release_size": int(len(selected)),
        "FTR": float((~labels[selected].astype(bool)).mean()),
        "threshold": 1.0 - alpha,
    }


def naive_one_sided_conformal(scores: np.ndarray, labels: np.ndarray, observed_idx: np.ndarray, alpha: float, K: int) -> dict:
    observed_scores = scores[observed_idx]
    threshold = float(np.quantile(observed_scores, alpha)) if len(observed_scores) else math.inf
    order = np.argsort(scores)[::-1]
    selected = order[scores[order] >= threshold][:K]
    return {
        "release_size": int(len(selected)),
        "FTR": float((~labels[selected].astype(bool)).mean()) if len(selected) else 0.0,
        "threshold": threshold,
    }


def oracle_full_label_conformal(scores: np.ndarray, labels: np.ndarray, alpha: float, K: int) -> dict:
    order = np.argsort(scores)[::-1][:K]
    best = np.asarray([], dtype=int)
    for k in range(1, len(order) + 1):
        selected = order[:k]
        ftr = float((~labels[selected].astype(bool)).mean())
        if ftr <= alpha:
            best = selected
    return {
        "release_size": int(len(best)),
        "FTR": float((~labels[best].astype(bool)).mean()) if len(best) else 0.0,
        "threshold": "oracle_full_label_prefix",
    }


def baseline_domain_arrays(args: argparse.Namespace) -> list[dict]:
    domains = []
    mat_frame, _ = materials.load_materials_inputs(args)
    domains.append(
        {
            "domain": "Materials discovery",
            "dataset": "Matbench Discovery WBM",
            "proposal_source": "CGCNN ensemble",
            "scores": mat_frame["primary_score"].to_numpy(dtype=float),
            "labels": mat_frame["stable_DFT"].to_numpy(dtype=bool),
            "alpha": 0.10,
            "K": 300,
            "rho": 0.10,
            "evaluation_label": "actual_DFT_stability",
        }
    )
    ctc = pd.read_csv(args.ctc_learned_universe, low_memory=False)
    ctc_labels = ~bool_series(ctc["is_unmatched"]).to_numpy(dtype=bool)
    domains.append(
        {
            "domain": "Biomedical cell tracking",
            "dataset": "CTC learned-hybrid held-out sequence",
            "proposal_source": "learned-hybrid appearance linker",
            "scores": ctc["score"].to_numpy(dtype=float),
            "labels": ctc_labels,
            "alpha": 0.10,
            "K": 300,
            "rho": 0.10,
            "evaluation_label": "held_out_GT_link_truth",
        }
    )
    release = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit/release_audit_human_confirmed_labels.csv")
    raw = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit/raw_topk_audit_human_confirmed_labels.csv")
    audit = pd.concat([release, raw], ignore_index=True).drop_duplicates("path_id")
    domains.append(
        {
            "domain": "Ecological camera traps",
            "dataset": "iWildCam animal-present audited subset",
            "proposal_source": "GroundingDINO-SwinT animal-present fallback",
            "scores": audit["score"].to_numpy(dtype=float),
            "labels": (audit["human_label"].astype(str) == "animal").to_numpy(dtype=bool),
            "alpha": 0.20,
            "K": min(50, len(audit)),
            "rho": 0.50,
            "evaluation_label": "human_audit_animal_present",
        }
    )
    return domains


def build_minimal_baseline_matrix(args: argparse.Namespace) -> Path:
    rows = []
    for domain in baseline_domain_arrays(args):
        scores = np.asarray(domain["scores"], dtype=float)
        labels = np.asarray(domain["labels"], dtype=bool)
        observed_idx = observed_positive_indices(labels, scores, rho=float(domain["rho"]))
        for prior_multiplier in [0.8, 1.0, 1.2]:
            result = pu_plugin_release(
                scores,
                labels,
                observed_idx,
                alpha=float(domain["alpha"]),
                K=int(domain["K"]),
                prior_multiplier=prior_multiplier,
            )
            rows.append(
                {
                    **{k: domain[k] for k in ["domain", "dataset", "proposal_source", "alpha", "K", "rho", "evaluation_label"]},
                    "baseline": "PU plug-in positive-vs-unlabeled classifier",
                    "prior_sensitivity_multiplier": prior_multiplier,
                    "release_size": result["release_size"],
                    "actual_or_human_FTR": result["FTR"],
                    "set_level_guarantee": "no",
                    "uses_class_prior_or_correction": "Elkan-Noto c_hat with multiplier sensitivity",
                    "threshold_or_rule": result["threshold"],
                }
            )
        for baseline, result in [
            ("Naive one-sided split conformal treating unverified as negative", naive_one_sided_conformal(scores, labels, observed_idx, float(domain["alpha"]), int(domain["K"]))),
            ("Oracle full-label conformal prefix", oracle_full_label_conformal(scores, labels, float(domain["alpha"]), int(domain["K"]))),
        ]:
            rows.append(
                {
                    **{k: domain[k] for k in ["domain", "dataset", "proposal_source", "alpha", "K", "rho", "evaluation_label"]},
                    "baseline": baseline,
                    "prior_sensitivity_multiplier": "",
                    "release_size": result["release_size"],
                    "actual_or_human_FTR": result["FTR"],
                    "set_level_guarantee": "no" if "Naive" in baseline else "oracle_not_deployable_under_partial_verification",
                    "uses_class_prior_or_correction": "no",
                    "threshold_or_rule": result["threshold"],
                }
            )
    out_dir = Path(args.diagnostics_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "table_pu_selective_conformal_minimal_baselines.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def build_iwildcam_second_review_package(args: argparse.Namespace) -> tuple[Path, Path]:
    root = Path(args.iwildcam_dir)
    cal = pd.read_csv(root / "calibration_audit_human_confirmed_labels.csv")
    rel = pd.read_csv(root / "release_audit_human_confirmed_labels.csv")
    raw = pd.read_csv(root / "raw_topk_audit_human_confirmed_labels.csv")
    negative = cal[cal["human_label"].astype(str) == "not_animal"].copy()
    positive = cal[cal["human_label"].astype(str) == "animal"].copy()
    pos_sample = positive.sample(n=min(300, len(positive)), random_state=20260515)
    pieces = [
        rel.assign(second_review_stratum="all_release_candidates"),
        negative.assign(second_review_stratum="all_calibration_not_animal"),
        pos_sample.assign(second_review_stratum="random_300_calibration_animal"),
        raw.assign(second_review_stratum="all_raw_topK_candidates"),
    ]
    template = pd.concat(pieces, ignore_index=True).drop_duplicates("path_id", keep="first").copy()
    leak_cols = [c for c in template.columns if c.startswith("human_")]
    template = template.drop(columns=leak_cols)
    template["second_reviewer_label"] = ""
    template["second_reviewer_verified_positive_for_calibration"] = ""
    template["second_reviewer_reason"] = ""
    template["second_reviewer_confidence"] = ""
    template["second_reviewer_status"] = "requires_independent_second_review"
    template_path = root / "second_review_blind_template.csv"
    template.to_csv(template_path, index=False)
    status = pd.DataFrame(
        [
            {
                "status": "requires_independent_second_review",
                "n_rows": int(len(template)),
                "all_release_candidates_included": int(len(rel)),
                "all_calibration_not_animal_included": int(len(negative)),
                "random_calibration_animal_included": int(len(pos_sample)),
                "all_raw_topK_candidates_included": int(len(raw)),
                "kappa_status": "not_computed_until_second_reviewer_labels_exist",
                "paper_use": "template_ready_not_claimed_as_completed_IRR",
            }
        ]
    )
    status_path = root / "table_iwildcam_second_review_status.csv"
    status.to_csv(status_path, index=False)
    return template_path, status_path


def build_runtime_table(args: argparse.Namespace) -> Path:
    rows = []
    materials_summary = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_materials/table_materials_candidate_universe_summary.csv").iloc[0]
    materials_primary = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_materials/table_materials_primary_results.csv")
    runtime_modern = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_materials/table_materials_modern_model_report.csv").iloc[0]
    rows.append(
        {
            "domain": "Materials discovery",
            "candidate_universe_size": int(materials_summary["n_candidates"]),
            "evaluated_K": "100,300,5000",
            "num_blocks": int(materials_summary["n_composition_family_pair_blocks"]),
            "calibration_and_evalue_time_sec": float(runtime_modern["runtime_sec_for_grid"]),
            "scs_greedy_time_sec": "included_in_grid_time",
            "peak_memory_gb": "not_profiled_table_only",
            "hardware": "CPU table recomputation; no model inference",
            "source_table": "table_materials_modern_model_report.csv",
        }
    )
    ctc = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_verification_budget_by_domain.csv")
    ctc_row = ctc[ctc["domain"].astype(str).str.contains("CTC", na=False)].iloc[0]
    rows.append(
        {
            "domain": "Biomedical cell tracking",
            "candidate_universe_size": int(ctc_row["candidate_universe_size"]),
            "evaluated_K": "300",
            "num_blocks": str(ctc_row["blocks_covered"]),
            "calibration_and_evalue_time_sec": "precomputed in CTC learned closeout",
            "scs_greedy_time_sec": "subsecond table-level selection",
            "peak_memory_gb": "not_profiled_table_only",
            "hardware": "CPU table recomputation; learned source precomputed",
            "source_table": "scientific_domain_ctc_learned tables",
        }
    )
    iw = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_protocol_summary.csv").iloc[0]
    rows.append(
        {
            "domain": "Ecological camera traps",
            "candidate_universe_size": int(iw["candidate_rows"]),
            "evaluated_K": "50",
            "num_blocks": int(iw["blocks"]),
            "calibration_and_evalue_time_sec": "precomputed in iWildCam human-audit closeout",
            "scs_greedy_time_sec": "subsecond table-level selection",
            "peak_memory_gb": "not_profiled_table_only",
            "hardware": "CPU table recomputation; detector inference excluded",
            "source_table": "table_iwildcam_human_audit_protocol_summary.csv",
        }
    )
    sp = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_spacenet7/table_spacenet7_adapter_report.csv")
    rows.append(
        {
            "domain": "Earth observation",
            "candidate_universe_size": int(sp["candidate_links"].sum()),
            "evaluated_K": "100,5000,randomized",
            "num_blocks": int(len(sp)),
            "calibration_and_evalue_time_sec": "precomputed in SpaceNet closeout",
            "scs_greedy_time_sec": "subsecond table-level selection",
            "peak_memory_gb": "not_profiled_table_only",
            "hardware": "CPU table recomputation; geospatial candidate generation excluded",
            "source_table": "table_spacenet7_adapter_report.csv",
        }
    )
    out_dir = Path(args.diagnostics_dir)
    path = out_dir / "table_runtime_compute_overhead_scientific_domains.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def update_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_closeout(args: argparse.Namespace, outputs: dict[str, str]) -> Path:
    path = Path(args.diagnostics_dir) / "P0_SUPPLEMENTAL_CLOSEOUT.md"
    text = f"""# P0 Supplemental Closeout

## Materials Modern-Model Sensitivity

Added a public ALIGNN-FF WBM prediction source as a modern learned materials
model sensitivity row.  The protocol reuses the same WBM candidate universe,
composition-family blocks, rho=0.10, alpha=0.10, seeds 0..19, and K grid used by
the CGCNN flagship.

Table: `{outputs['materials_modern']}`

## Minimal PU / Selective-Conformal Baselines

Added a compact supplement table for a PU plug-in classifier and two selective
conformal variants.  The table explicitly marks whether the method provides a
finite set-level release guarantee under one-sided verification.

Table: `{outputs['baselines']}`

## iWildCam Second-Review Package

Prepared the blind second-review template for all release candidates, all
calibration negatives, a random 300 calibration positives, and all raw top-K
candidates.  No inter-rater agreement is claimed until independent labels are
filled.

Template: `{outputs['iwildcam_second_review_template']}`

Status: `{outputs['iwildcam_second_review_status']}`

## Runtime / Compute Overhead

Added a compact domain-level runtime and compute-overhead table.  The table
separates PARC table-level certification from upstream proposal inference.

Table: `{outputs['runtime']}`
"""
    path.write_text(text, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--primary-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--weak-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
    parser.add_argument("--modern-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--primary-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--weak-pred-col", default="e_form_per_atom_megnet")
    parser.add_argument("--stability-threshold", type=float, default=0.0)
    parser.add_argument("--materials-dir", default="outputs/milestones/scientific_domain_materials")
    parser.add_argument("--diagnostics-dir", default="outputs/milestones/release_story/paper_diagnostics")
    parser.add_argument("--iwildcam-dir", default="outputs/milestones/scientific_domain_iwildcam_human_audit")
    parser.add_argument("--ctc-learned-universe", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1/candidate_universe.csv")
    args = parser.parse_args()

    modern, modern_seed, modern_report = build_materials_modern_sensitivity(args)
    baselines = build_minimal_baseline_matrix(args)
    template, status = build_iwildcam_second_review_package(args)
    runtime = build_runtime_table(args)
    closeout = write_closeout(
        args,
        {
            "materials_modern": str(modern),
            "materials_modern_seed": str(modern_seed),
            "materials_modern_report": str(modern_report),
            "baselines": str(baselines),
            "iwildcam_second_review_template": str(template),
            "iwildcam_second_review_status": str(status),
            "runtime": str(runtime),
        },
    )
    report = {
        "status": "completed",
        "outputs": {
            "materials_modern": str(modern),
            "materials_modern_seed": str(modern_seed),
            "materials_modern_report": str(modern_report),
            "baselines": str(baselines),
            "iwildcam_second_review_template": str(template),
            "iwildcam_second_review_status": str(status),
            "runtime": str(runtime),
            "closeout": str(closeout),
        },
        "modern_prediction_sha256": sha256_file(Path(args.modern_predictions)),
    }
    Path(args.diagnostics_dir, "p0_supplemental_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    update_manifest(Path(args.materials_dir))
    update_manifest(Path(args.diagnostics_dir))
    update_manifest(Path(args.iwildcam_dir))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
