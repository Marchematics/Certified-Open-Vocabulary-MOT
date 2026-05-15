#!/usr/bin/env python3
"""Build PU and selective-conformal supplement baselines.

This benchmark is deliberately scoped as a *different-target-object* comparison:
PU classifiers and selective conformal procedures score or cover selected
individual candidates, while PARC certifies a finite compatible release set under
one-sided verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_materials_discovery_parc_flagship as materials  # noqa: E402


ALPHA = 0.10
K = 100
RHO = 0.10
SEEDS = list(range(20))


@dataclass
class DomainData:
    domain: str
    dataset: str
    proposal_source: str
    scores: np.ndarray
    labels: np.ndarray
    evaluation_label: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def standard_features(scores: np.ndarray) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    order = np.argsort(scores)[::-1]
    rank = np.empty(len(scores), dtype=float)
    rank[order] = np.arange(1, len(scores) + 1)
    z = (scores - np.nanmean(scores)) / (np.nanstd(scores) + 1e-8)
    rank_feature = -np.log(rank) / max(1.0, math.log(len(scores)))
    quantile_feature = 1.0 - (rank - 1) / max(1, len(scores) - 1)
    return np.column_stack([z, rank_feature, quantile_feature]).astype("float32")


def observed_positive_indices(labels: np.ndarray, scores: np.ndarray, train_idx: np.ndarray, rho: float) -> np.ndarray:
    positives = train_idx[labels[train_idx].astype(bool)]
    n_obs = max(1, int(round(len(positives) * rho))) if len(positives) else 0
    ordered = positives[np.argsort(scores[positives])[::-1]]
    return ordered[:n_obs]


class TinyPU(nn.Module):
    def __init__(self, in_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def train_nnpu(
    features: np.ndarray,
    labels: np.ndarray,
    train_idx: np.ndarray,
    observed_idx: np.ndarray,
    seed: int,
    rho: float,
) -> tuple[np.ndarray, float, dict]:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    p_idx = np.asarray(observed_idx, dtype=int)
    u_idx = np.setdiff1d(train_idx, p_idx, assume_unique=False)
    if len(p_idx) == 0:
        posterior = np.zeros(len(labels), dtype=float)
        return posterior, 0.0, {"epochs": 0, "class_prior": 0.0}
    # The simulated audit protocol observes a rho fraction of positives.  This
    # is available to the benchmark as an inspection-budget parameter, not as
    # full-label access.
    pi_hat = float(np.clip(len(p_idx) / max(1, len(train_idx)) / max(rho, 1e-6), 0.01, 0.95))
    x_all = torch.tensor(features, dtype=torch.float32)
    x_p = x_all[p_idx]
    x_u = x_all[u_idx]
    model = TinyPU(features.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    epochs = 45
    for _ in range(epochs):
        # Mini-sample the unlabeled pool for speed and to avoid a degenerate
        # full-batch PU classifier on very large materials tables.
        if len(u_idx) > 4096:
            sample = rng.choice(len(u_idx), size=4096, replace=False)
            x_u_batch = x_u[sample]
        else:
            x_u_batch = x_u
        logits_p = model(x_p)
        logits_u = model(x_u_batch)
        loss_pos = F.binary_cross_entropy_with_logits(logits_p, torch.ones_like(logits_p))
        loss_neg_p = F.binary_cross_entropy_with_logits(logits_p, torch.zeros_like(logits_p))
        loss_neg_u = F.binary_cross_entropy_with_logits(logits_u, torch.zeros_like(logits_u))
        positive_risk = pi_hat * loss_pos
        negative_risk = loss_neg_u - pi_hat * loss_neg_p
        loss = positive_risk + torch.clamp(negative_risk, min=0.0)
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        posterior = torch.sigmoid(model(x_all)).cpu().numpy().astype(float)
    return posterior, pi_hat, {"epochs": epochs, "class_prior": pi_hat}


def evaluate_selection(selected: np.ndarray, labels: np.ndarray) -> tuple[int, float]:
    if len(selected) == 0:
        return 0, 0.0
    return int(len(selected)), float((~labels[selected].astype(bool)).mean())


def raw_topk(scores: np.ndarray, labels: np.ndarray, test_idx: np.ndarray, k: int) -> dict:
    ordered = test_idx[np.argsort(scores[test_idx])[::-1]][:k]
    release, ftr = evaluate_selection(ordered, labels)
    return {"release_size": release, "FTR": ftr, "threshold": "top_K_by_source_score"}


def nnpu_release(
    posterior: np.ndarray,
    labels: np.ndarray,
    test_idx: np.ndarray,
    alpha: float,
    k: int,
) -> dict:
    ordered = test_idx[np.argsort(posterior[test_idx])[::-1]]
    eligible = ordered[posterior[ordered] >= (1.0 - alpha)]
    selected = eligible[:k]
    release, ftr = evaluate_selection(selected, labels)
    return {"release_size": release, "FTR": ftr, "threshold": 1.0 - alpha}


def bao_style_selective_conformal(
    scores: np.ndarray,
    labels: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    observed_idx: np.ndarray,
    alpha: float,
    k: int,
    use_oracle_labels: bool,
) -> dict:
    selected_cal = train_idx[np.argsort(scores[train_idx])[::-1]][: min(k, len(train_idx))]
    selected_test = test_idx[np.argsort(scores[test_idx])[::-1]][: min(k, len(test_idx))]
    if use_oracle_labels:
        cal_truth = labels[selected_cal].astype(bool)
        deployability = "oracle_full_label_not_deployable"
    else:
        observed = np.zeros(len(labels), dtype=bool)
        observed[observed_idx] = True
        # This is the deployable one-sided adaptation, but it targets a
        # different object from PARC: unverified items are treated as failures
        # inside the selective conformal calibration step.
        cal_truth = observed[selected_cal]
        deployability = "deployable_unverified_as_failure_different_target_object"

    best_threshold = math.inf
    best_release = np.asarray([], dtype=int)
    ordered_cal = selected_cal[np.argsort(scores[selected_cal])[::-1]]
    for m in range(1, len(ordered_cal) + 1):
        prefix = ordered_cal[:m]
        false_rate = float((~cal_truth[np.argsort(scores[selected_cal])[::-1]][:m]).mean())
        if false_rate <= alpha:
            best_threshold = float(scores[prefix[-1]])
    if not math.isfinite(best_threshold):
        selected = np.asarray([], dtype=int)
    else:
        selected = selected_test[scores[selected_test] >= best_threshold][:k]
    release, ftr = evaluate_selection(selected, labels)
    return {
        "release_size": release,
        "FTR": ftr,
        "threshold": best_threshold if math.isfinite(best_threshold) else "no_threshold_satisfies_calibration",
        "selected_calibration_count": int(len(selected_cal)),
        "selected_test_count": int(len(selected_test)),
        "deployability": deployability,
    }


def domain_arrays(args: argparse.Namespace) -> list[DomainData]:
    mat_frame, _ = materials.load_materials_inputs(args)
    ctc = pd.read_csv(args.ctc_learned_universe, low_memory=False)
    ctc_labels = ~bool_series(ctc["is_unmatched"]).to_numpy(dtype=bool)
    iwild_root = Path(args.iwildcam_dir)
    iwild = pd.concat(
        [
            pd.read_csv(iwild_root / "calibration_audit_human_confirmed_labels.csv"),
            pd.read_csv(iwild_root / "release_audit_human_confirmed_labels.csv"),
            pd.read_csv(iwild_root / "raw_topk_audit_human_confirmed_labels.csv"),
        ],
        ignore_index=True,
    ).drop_duplicates("path_id")
    return [
        DomainData(
            domain="Materials discovery",
            dataset="Matbench Discovery WBM",
            proposal_source="CGCNN ensemble",
            scores=mat_frame["primary_score"].to_numpy(dtype=float),
            labels=mat_frame["stable_DFT"].to_numpy(dtype=bool),
            evaluation_label="actual_DFT_stability",
        ),
        DomainData(
            domain="Biomedical cell tracking",
            dataset="CTC learned-hybrid held-out sequence",
            proposal_source="learned-hybrid appearance linker",
            scores=ctc["score"].to_numpy(dtype=float),
            labels=ctc_labels,
            evaluation_label="held_out_GT_link_truth",
        ),
        DomainData(
            domain="Ecological camera traps",
            dataset="iWildCam animal-present audited set",
            proposal_source="GroundingDINO-SwinT animal-present fallback",
            scores=iwild["score"].to_numpy(dtype=float),
            labels=(iwild["human_label"].astype(str) == "animal").to_numpy(dtype=bool),
            evaluation_label="human_audit_animal_present",
        ),
    ]


def summarize_rows(rows: list[dict], group_cols: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    out = []
    for key, group in frame.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "mean_release": float(group["release_size"].mean()),
                "min_release": int(group["release_size"].min()),
                "max_release": int(group["release_size"].max()),
                "realized_FTR_mean": float(group["realized_FTR"].mean()),
                "realized_FTR_max": float(group["realized_FTR"].max()),
                "coverage_diagnostic": "|".join(sorted(set(group["coverage_diagnostic"].astype(str)))),
                "threshold_or_rule": "|".join(sorted(set(group["threshold_or_rule"].astype(str)))[:4]),
                "set_level_release_guarantee": "|".join(sorted(set(group["set_level_release_guarantee"].astype(str)))),
                "target_object_note": "|".join(sorted(set(group["target_object_note"].astype(str)))),
            }
        )
        if "class_prior_estimate" in group.columns:
            vals = pd.to_numeric(group["class_prior_estimate"], errors="coerce").dropna()
            row["class_prior_estimate_mean"] = float(vals.mean()) if len(vals) else math.nan
        out.append(row)
    return pd.DataFrame(out)


def parc_reference_rows() -> list[dict]:
    rows = []
    ctc = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_hybrid_main.csv")
    ctc_row = ctc[(ctc["rho"] == RHO) & (ctc["alpha"] == ALPHA) & (ctc["M"] == K)].iloc[0]
    rows.append(
        {
            "domain": "Biomedical cell tracking",
            "dataset": "CTC learned-hybrid held-out sequence",
            "proposal_source": "learned-hybrid appearance linker",
            "method": "PARC certified release",
            "alpha": ALPHA,
            "K": K,
            "seeds": int(ctc_row["seeds"]),
            "mean_release": float(ctc_row["released_mean"]),
            "realized_FTR_mean": float(ctc_row["actual_FTR_mean"]),
            "coverage_diagnostic": "PARC block e-value release",
            "set_level_release_guarantee": "yes",
            "target_object_note": "same_target_release_FTR",
        }
    )
    materials_df = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_materials/table_materials_primary_results.csv")
    mat_row = materials_df[
        (materials_df["rho"] == RHO)
        & (materials_df["alpha"] == ALPHA)
        & (materials_df["K"] == K)
        & (materials_df["proposal_source"] == "cgcnn_ensemble_learned_materials_model")
        & (materials_df["block_definition"] == "composition_family_pair")
    ].iloc[0]
    rows.append(
        {
            "domain": "Materials discovery",
            "dataset": "Matbench Discovery WBM",
            "proposal_source": "CGCNN ensemble",
            "method": "PARC certified release",
            "alpha": ALPHA,
            "K": K,
            "seeds": int(mat_row["seeds"]),
            "mean_release": float(mat_row["mean_release"]),
            "realized_FTR_mean": float(mat_row["actual_FTR_mean"]),
            "coverage_diagnostic": "PARC block e-value release",
            "set_level_release_guarantee": "yes",
            "target_object_note": "same_target_release_FTR",
        }
    )
    iwild = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv")
    iwild_row = iwild[(iwild["alpha"] == ALPHA) & (iwild["K"] == K)].iloc[0]
    rows.append(
        {
            "domain": "Ecological camera traps",
            "dataset": "iWildCam animal-present audited set",
            "proposal_source": "GroundingDINO-SwinT animal-present fallback",
            "method": "PARC certified release",
            "alpha": ALPHA,
            "K": K,
            "seeds": 20,
            "mean_release": float(iwild_row["mean_release"]),
            "realized_FTR_mean": 0.0,
            "coverage_diagnostic": str(iwild_row["dominant_empty_reason"]),
            "set_level_release_guarantee": "yes_refusal_at_strict_alpha010",
            "target_object_note": "same_target_release_FTR",
        }
    )
    return rows


def build_benchmark(args: argparse.Namespace) -> dict:
    out_dir = Path(args.diagnostics_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_rows: list[dict] = []
    started = time.perf_counter()
    for domain in domain_arrays(args):
        n = len(domain.scores)
        features = standard_features(domain.scores)
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            idx = rng.permutation(n)
            split = max(1, int(round(0.5 * n)))
            train_idx = np.sort(idx[:split])
            test_idx = np.sort(idx[split:])
            observed_idx = observed_positive_indices(domain.labels, domain.scores, train_idx, RHO)

            raw = raw_topk(domain.scores, domain.labels, test_idx, K)
            seed_rows.append(
                {
                    "domain": domain.domain,
                    "dataset": domain.dataset,
                    "proposal_source": domain.proposal_source,
                    "alpha": ALPHA,
                    "K": K,
                    "rho": RHO,
                    "evaluation_label": domain.evaluation_label,
                    "method": "Raw top-K source ranking",
                    "seed": seed,
                    "release_size": raw["release_size"],
                    "realized_FTR": raw["FTR"],
                    "coverage_diagnostic": "no_calibration_no_coverage_claim",
                    "threshold_or_rule": raw["threshold"],
                    "set_level_release_guarantee": "no",
                    "target_object_note": "same_target_empirical_baseline",
                    "class_prior_estimate": math.nan,
                }
            )

            posterior, pi_hat, train_info = train_nnpu(features, domain.labels, train_idx, observed_idx, seed, RHO)
            nnpu = nnpu_release(posterior, domain.labels, test_idx, ALPHA, K)
            seed_rows.append(
                {
                    "domain": domain.domain,
                    "dataset": domain.dataset,
                    "proposal_source": domain.proposal_source,
                    "alpha": ALPHA,
                    "K": K,
                    "rho": RHO,
                    "evaluation_label": domain.evaluation_label,
                    "method": "nnPU classifier release",
                    "seed": seed,
                    "release_size": nnpu["release_size"],
                    "realized_FTR": nnpu["FTR"],
                    "coverage_diagnostic": f"PU_prior_estimated_from_observed_budget;epochs={train_info['epochs']}",
                    "threshold_or_rule": nnpu["threshold"],
                    "set_level_release_guarantee": "no",
                    "target_object_note": "different_target_object_concrete_demonstration",
                    "class_prior_estimate": pi_hat,
                }
            )

            for label, oracle in [
                ("Bao-style selective conformal adaptation", False),
                ("Bao-style selective conformal oracle-label diagnostic", True),
            ]:
                sc = bao_style_selective_conformal(
                    domain.scores,
                    domain.labels,
                    train_idx,
                    test_idx,
                    observed_idx,
                    ALPHA,
                    K,
                    use_oracle_labels=oracle,
                )
                seed_rows.append(
                    {
                        "domain": domain.domain,
                        "dataset": domain.dataset,
                        "proposal_source": domain.proposal_source,
                        "alpha": ALPHA,
                        "K": K,
                        "rho": RHO,
                        "evaluation_label": domain.evaluation_label,
                        "method": label,
                        "seed": seed,
                        "release_size": sc["release_size"],
                        "realized_FTR": sc["FTR"],
                        "coverage_diagnostic": (
                            f"post_selection_calibration;selected_cal={sc['selected_calibration_count']};"
                            f"selected_test={sc['selected_test_count']};{sc['deployability']}"
                        ),
                        "threshold_or_rule": sc["threshold"],
                        "set_level_release_guarantee": "no" if not oracle else "oracle_not_deployable_under_partial_verification",
                        "target_object_note": "different_target_object_concrete_demonstration",
                        "class_prior_estimate": math.nan,
                    }
                )

    seed_frame = pd.DataFrame(seed_rows)
    seed_path = out_dir / "table_pu_selective_conformal_benchmark_seed_rows.csv"
    seed_frame.to_csv(seed_path, index=False)
    summary = summarize_rows(
        seed_rows,
        [
            "domain",
            "dataset",
            "proposal_source",
            "alpha",
            "K",
            "rho",
            "evaluation_label",
            "method",
        ],
    )
    summary["paper_use"] = summary["method"].map(
        lambda method: "supplement_table2b_baseline_frontier"
        if method in {"nnPU classifier release", "Bao-style selective conformal adaptation"}
        else "supplement_context"
    )
    summary_path = out_dir / "table_pu_selective_conformal_benchmark.csv"
    summary.to_csv(summary_path, index=False)

    frontier_rows = []
    for _, row in summary.iterrows():
        frontier_rows.append(
            {
                "domain": row["domain"],
                "dataset": row["dataset"],
                "method": row["method"],
                "alpha": row["alpha"],
                "K": row["K"],
                "mean_release": row["mean_release"],
                "realized_FTR_mean": row["realized_FTR_mean"],
                "set_level_release_guarantee": row["set_level_release_guarantee"],
                "target_object_note": row["target_object_note"],
            }
        )
    frontier_rows.extend(parc_reference_rows())
    frontier = pd.DataFrame(frontier_rows)
    frontier_path = out_dir / "figure_table2b_baseline_frontier.csv"
    frontier.to_csv(frontier_path, index=False)

    closeout = out_dir / "PU_SELECTIVE_CONFORMAL_BENCHMARK_CLOSEOUT.md"
    closeout.write_text(
        """# PU and Selective-Conformal Benchmark Closeout

This supplement adds two concrete baseline families at alpha=0.10 and K=100
for CTC, materials discovery, and iWildCam: a PyTorch nnPU classifier and a
Bao-style post-selection selective conformal adaptation.  The selective
conformal reference follows the post-selection/FCR setting of Bao et al. 2024,
where selected units receive conformal predictions; here it is adapted as a
candidate-release comparator and is explicitly marked as a different target
object rather than a PARC-equivalent theorem.

Outputs:

- `table_pu_selective_conformal_benchmark.csv`
- `table_pu_selective_conformal_benchmark_seed_rows.csv`
- `figure_table2b_baseline_frontier.csv`

Paper wording: use "different target object (concrete demonstration in
Supplement X)".
""",
        encoding="utf-8",
    )
    report = {
        "status": "completed",
        "alpha": ALPHA,
        "K": K,
        "rho": RHO,
        "seeds": SEEDS,
        "runtime_sec": time.perf_counter() - started,
        "outputs": {
            "summary": str(summary_path),
            "seed_rows": str(seed_path),
            "frontier": str(frontier_path),
            "closeout": str(closeout),
        },
        "references": {
            "bao_selective_conformal": "Bao et al. 2024 selective conformal inference with false coverage-statement rate control",
            "cap_arxiv": "arXiv:2403.07728",
        },
    }
    report_path = out_dir / "pu_selective_conformal_benchmark_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def update_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbm-summary", default="data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--primary-predictions", default="data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--weak-predictions", default="data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
    parser.add_argument("--primary-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--weak-pred-col", default="e_form_per_atom_megnet")
    parser.add_argument("--stability-threshold", type=float, default=0.0)
    parser.add_argument("--ctc-learned-universe", default="outputs/ctc_learned_link_certification/universe_sequence02_eval_w1/candidate_universe.csv")
    parser.add_argument("--iwildcam-dir", default="outputs/milestones/scientific_domain_iwildcam_human_audit")
    parser.add_argument("--diagnostics-dir", default="outputs/milestones/release_story/paper_diagnostics")
    args = parser.parse_args()
    report = build_benchmark(args)
    update_manifest(Path(args.diagnostics_dir))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
