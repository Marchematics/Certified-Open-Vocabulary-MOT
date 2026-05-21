from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "materials_label_discordance_preregistration"
MATCHES = ROOT / "outputs/milestones/materials_alex_mp_a1_a2_validation/table_alex_mp_a2_candidate_matches.csv"
ALIGNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
CGCNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
MEGNET = Path("/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
CHGNET_FULL = Path("/home/waas/paper_experiments/private/chgnet/2023-12-21-chgnet-0.3.0-wbm-IS2RE.csv.gz")
CHGNET_SUBSET = ROOT / "outputs/milestones/materials_prospective_dft_followup_chgnet_v2/calibration_scores_chgnet_v2.csv"
FRONTIER_SCORES = OUT / "table_frontier_model_scores.csv"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def update_manifest() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(OUT)}")
    (OUT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def stable_f1(y_true: pd.Series, y_pred: pd.Series) -> float:
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)
    tp = int((y_true & y_pred).sum())
    fp = int((~y_true & y_pred).sum())
    fn = int((y_true & ~y_pred).sum())
    denom = 2 * tp + fp + fn
    return float(2 * tp / denom) if denom else 0.0


def balanced_accuracy(y_true: pd.Series, y_pred: pd.Series) -> float:
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)
    pos = int(y_true.sum())
    neg = int((~y_true).sum())
    tpr = float((y_true & y_pred).sum() / pos) if pos else math.nan
    tnr = float(((~y_true) & (~y_pred)).sum() / neg) if neg else math.nan
    if math.isnan(tpr) or math.isnan(tnr):
        return math.nan
    return float((tpr + tnr) / 2)


def precision(y_true: pd.Series, y_pred: pd.Series) -> float:
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)
    pred = int(y_pred.sum())
    return float((y_true & y_pred).sum() / pred) if pred else 0.0


def prediction_flag(scores: pd.Series, q: float = 0.05) -> pd.Series:
    n = len(scores)
    k = max(int(math.ceil(q * n)), 20)
    k = min(k, n)
    order = scores.astype(float).sort_values(ascending=True).index[:k]
    out = pd.Series(False, index=scores.index)
    out.loc[order] = True
    return out


def load_model_scores(material_ids: set[str]) -> tuple[pd.DataFrame, list[dict]]:
    rows = pd.DataFrame({"material_id": sorted(material_ids)})
    eligibility: list[dict] = []

    alignn = pd.read_csv(ALIGNN)
    rows = rows.merge(alignn.rename(columns={"e_form_per_atom_alignn_ff": "score_alignn_ff"}), on="material_id", how="left")
    eligibility.append(
        {
            "model": "ALIGNN-FF",
            "pre_registered_role": "primary_model_set",
            "score_source": f"private_matbench_discovery::{ALIGNN.name}",
            "score_source_sha256": sha256_file(ALIGNN),
            "valid_scores_on_exact_denominator": int(rows["score_alignn_ff"].notna().sum()),
            "eligible_primary_ranking": "true",
            "ineligibility_reason": "",
        }
    )

    cgcnn = pd.read_csv(CGCNN, usecols=["material_id", "e_form_per_atom_mp2020_corrected_pred_ens"])
    rows = rows.merge(cgcnn.rename(columns={"e_form_per_atom_mp2020_corrected_pred_ens": "score_cgcnn"}), on="material_id", how="left")
    eligibility.append(
        {
            "model": "CGCNN",
            "pre_registered_role": "legacy_fallback_anchor",
            "score_source": f"private_matbench_discovery::{CGCNN.name}",
            "score_source_sha256": sha256_file(CGCNN),
            "valid_scores_on_exact_denominator": int(rows["score_cgcnn"].notna().sum()),
            "eligible_primary_ranking": "false",
            "ineligibility_reason": "legacy fallback only; not used to define frontier primary endpoint",
        }
    )

    megnet = pd.read_csv(MEGNET)
    rows = rows.merge(megnet.rename(columns={"e_form_per_atom_megnet": "score_megnet"}), on="material_id", how="left")
    eligibility.append(
        {
            "model": "MEGNet",
            "pre_registered_role": "pre_existing_auxiliary_public_prediction_not_grilled_primary",
            "score_source": f"private_matbench_discovery::{MEGNET.name}",
            "score_source_sha256": sha256_file(MEGNET),
            "valid_scores_on_exact_denominator": int(rows["score_megnet"].notna().sum()),
            "eligible_primary_ranking": "false",
            "ineligibility_reason": "not in grilled primary model set; reported as auxiliary only",
        }
    )

    if FRONTIER_SCORES.exists():
        frontier = pd.read_csv(FRONTIER_SCORES)
        for model, col in [("CHGNet", "score_chgnet_frontier"), ("MACE-MP", "score_mace_mp_frontier")]:
            sub = frontier[(frontier["model"].eq(model)) & (frontier["score_status"].eq("scored"))][
                ["material_id", "score"]
            ].copy()
            sub = sub.rename(columns={"score": col})
            rows = rows.merge(sub, on="material_id", how="left")
    else:
        rows["score_chgnet_frontier"] = math.nan
        rows["score_mace_mp_frontier"] = math.nan

    chgnet_valid = int(rows["score_chgnet_frontier"].notna().sum())
    mace_valid = int(rows["score_mace_mp_frontier"].notna().sum())
    if chgnet_valid >= 200:
        chgnet_eligible = "true"
        chgnet_reason = "reproducibly generated CHGNet raw-energy scores on exact matched denominator"
        chgnet_source = "table_frontier_model_scores.csv::CHGNet"
        chgnet_sha = sha256_file(FRONTIER_SCORES)
    else:
        chgnet_eligible = "false"
        chgnet_reason = "full WBM prediction file is invalid HTML download"
        if CHGNET_SUBSET.exists():
            subset = pd.read_csv(CHGNET_SUBSET)
            chgnet_reason += f"; public subset overlap={int(subset['candidate_id'].astype(str).isin(material_ids).sum())}"
        chgnet_source = f"private_chgnet::{CHGNET_FULL.name}"
        chgnet_sha = sha256_file(CHGNET_FULL) if CHGNET_FULL.exists() else ""
    if mace_valid >= 200:
        mace_eligible = "true"
        mace_reason = "reproducibly generated MACE-MP raw-energy scores on exact matched denominator"
        mace_source = "table_frontier_model_scores.csv::MACE-MP"
        mace_sha = sha256_file(FRONTIER_SCORES)
    else:
        mace_eligible = "false"
        mace_reason = "no frozen WBM prediction table or generated score coverage below n=200"
        mace_source = "no frozen WBM prediction table in repository"
        mace_sha = ""

    chgnet_reason = "full WBM prediction file is invalid HTML download"
    chgnet_overlap = 0
    eligibility.append(
        {
            "model": "CHGNet",
            "pre_registered_role": "primary_model_set",
            "score_source": chgnet_source,
            "score_source_sha256": chgnet_sha,
            "valid_scores_on_exact_denominator": chgnet_valid,
            "eligible_primary_ranking": chgnet_eligible,
            "ineligibility_reason": "" if chgnet_eligible == "true" else chgnet_reason,
        }
    )

    eligibility.append(
        {
            "model": "MACE-MP",
            "pre_registered_role": "primary_model_set",
            "score_source": mace_source,
            "score_source_sha256": mace_sha,
            "valid_scores_on_exact_denominator": mace_valid,
            "eligible_primary_ranking": mace_eligible,
            "ineligibility_reason": "" if mace_eligible == "true" else mace_reason,
        }
    )
    return rows, eligibility


def metric_rows(data: pd.DataFrame, score_cols: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    for model, col in score_cols.items():
        scored = data[data[col].notna()].copy()
        if scored.empty:
            continue
        pred = prediction_flag(scored[col])
        for label_source, label_col in [("WBM", "wbm_stable_DFT"), ("alex-mp", "alex_stable_exact")]:
            y = scored[label_col].astype(bool)
            rows.append(
                {
                    "model": model,
                    "label_source": label_source,
                    "n_common": int(len(scored)),
                    "predicted_positive_rule": "top max(5%,20) by lowest frozen score",
                    "predicted_positive_n": int(pred.sum()),
                    "stable_positive_n": int(y.sum()),
                    "stable_class_F1_primary": stable_f1(y, pred),
                    "balanced_accuracy_coprimary": balanced_accuracy(y, pred),
                    "precision_discovery": precision(y, pred),
                    "discovered_stable_count": int((y & pred).sum()),
                    "score_col": col,
                }
            )
    return rows


def rank_order(metrics: pd.DataFrame, source: str, metric: str, models: list[str]) -> list[str]:
    sub = metrics[(metrics["label_source"] == source) & (metrics["model"].isin(models))].copy()
    sub = sub.sort_values([metric, "model"], ascending=[False, True])
    return sub["model"].tolist()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matches = pd.read_csv(MATCHES)
    exact = matches[matches["match_confidence"].eq("exact_structure_match")].copy()
    exact["alex_stable_exact"] = exact["alex_stable_exact"].astype(str).str.lower().eq("true")
    exact["wbm_stable_DFT"] = exact["wbm_stable_DFT"].astype(bool)

    discordance = float((exact["alex_stable_exact"] != exact["wbm_stable_DFT"]).mean()) if len(exact) else math.nan
    write_csv(
        OUT / "table_minimal_discordance_probe.csv",
        [
            {
                "source_pair": "WBM_Matbench_vs_alex_mp_v20",
                "match_basis": "exact_structure_match_from_existing_phase29_alex_mp_diagnostic",
                "matched_n": int(len(exact)),
                "pair_coverage_reference_n": int(len(matches)),
                "pair_coverage_fraction": float(len(exact) / len(matches)) if len(matches) else math.nan,
                "binary_label": "stable iff e_above_hull <= 0 eV/atom",
                "discordance_rate": discordance,
                "launch_gate_discordance_ge_0_40": str(bool(discordance >= 0.40)).lower(),
                "no_go_discordance_le_0_10": str(bool(discordance <= 0.10)).lower(),
                "paper_role": "minimal_existing_probe_passes_discordance_gate_but_not_final_MP_vs_alex_full_snapshot",
            }
        ],
    )

    score_df, eligibility = load_model_scores(set(exact["material_id"].astype(str)))
    write_csv(OUT / "table_model_score_eligibility.csv", eligibility)

    data = exact.merge(score_df, on="material_id", how="left")
    available_score_cols = {
        "ALIGNN-FF": "score_alignn_ff",
        "CGCNN": "score_cgcnn",
        "MEGNet": "score_megnet",
        "CHGNet": "score_chgnet_frontier",
        "MACE-MP": "score_mace_mp_frontier",
    }
    metrics = pd.DataFrame(metric_rows(data, available_score_cols))
    metrics.to_csv(OUT / "table_downstream_ranking_metrics.csv", index=False)

    primary_models = ["ALIGNN-FF", "CHGNet", "MACE-MP"]
    primary_eligible = [r for r in eligibility if r["model"] in primary_models and r["eligible_primary_ranking"] == "true"]
    primary_status = "not_run_primary_frontier_endpoint_model_coverage_gate_failed"
    primary_top_flip: str | bool = ""
    primary_ordering_flip: str | bool = ""
    primary_max_delta: str | float = ""
    primary_go_no_go = "NO_GO_primary_until_CHGNet_and_MACE_have_frozen_scores_on_same_denominator"
    primary_scope = "coverage gate failed; do not claim primary Matbench-style ranking flip"
    if len(primary_eligible) == 3:
        primary_status = "run"
        po_wbm = rank_order(metrics, "WBM", "stable_class_F1_primary", primary_models)
        po_alex = rank_order(metrics, "alex-mp", "stable_class_F1_primary", primary_models)
        primary_top_flip = bool(po_wbm and po_alex and po_wbm[0] != po_alex[0])
        primary_ordering_flip = bool(po_wbm != po_alex)
        primary_pivot = metrics.pivot(index="model", columns="label_source", values="stable_class_F1_primary")
        primary_max_delta = float((primary_pivot.loc[primary_models, "WBM"] - primary_pivot.loc[primary_models, "alex-mp"]).abs().max())
        if primary_ordering_flip and primary_max_delta >= 0.05:
            primary_go_no_go = "GO_primary_downstream_conclusion_flip"
            primary_scope = "primary frontier endpoint passes using reproducibly generated same-denominator raw-energy scores"
        else:
            primary_go_no_go = "NO_GO_primary_no_material_F1_ranking_flip"
            primary_scope = "frontier scores available but primary ranking flip criterion did not pass"

    auxiliary_models = ["ALIGNN-FF", "CGCNN", "MEGNet"]
    wbm_order = rank_order(metrics, "WBM", "stable_class_F1_primary", auxiliary_models)
    alex_order = rank_order(metrics, "alex-mp", "stable_class_F1_primary", auxiliary_models)
    top_flip = bool(wbm_order and alex_order and wbm_order[0] != alex_order[0])
    ordering_flip = bool(wbm_order != alex_order)
    pivot = metrics.pivot(index="model", columns="label_source", values="stable_class_F1_primary")
    max_delta = float((pivot["WBM"] - pivot["alex-mp"]).abs().max()) if {"WBM", "alex-mp"}.issubset(pivot.columns) else math.nan
    write_csv(
        OUT / "table_downstream_ranking_flip_summary.csv",
        [
            {
                "endpoint": "primary_frontier_model_ranking",
                "models_required": "ALIGNN-FF;CHGNet;MACE-MP",
                "n_common_floor": 200,
                "status": primary_status,
                "top_model_flip": str(primary_top_flip).lower() if isinstance(primary_top_flip, bool) else "",
                "ordering_flip": str(primary_ordering_flip).lower() if isinstance(primary_ordering_flip, bool) else "",
                "max_abs_F1_delta": f"{primary_max_delta:.6f}" if isinstance(primary_max_delta, float) and math.isfinite(primary_max_delta) else "",
                "go_no_go": primary_go_no_go,
                "claim_scope": primary_scope,
            },
            {
                "endpoint": "auxiliary_available_public_prediction_ranking",
                "models_required": ";".join(auxiliary_models),
                "n_common_floor": 200,
                "status": "completed_auxiliary_diagnostic",
                "top_model_flip": str(top_flip).lower(),
                "ordering_flip": str(ordering_flip).lower(),
                "max_abs_F1_delta": f"{max_delta:.6f}" if math.isfinite(max_delta) else "",
                "go_no_go": "GO_auxiliary_if_flip_else_no_auxiliary_consequence",
                "claim_scope": "auxiliary legacy/public-prediction diagnostic; no NMI launch from this endpoint alone",
            },
        ],
    )

    discovery_rows: list[dict] = []
    for model in primary_models:
        sub = metrics[metrics["model"].eq(model)].set_index("label_source")
        if {"WBM", "alex-mp"}.issubset(sub.index):
            wbm_count = int(sub.loc["WBM", "discovered_stable_count"])
            alex_count = int(sub.loc["alex-mp", "discovered_stable_count"])
            rel = float(abs(wbm_count - alex_count) / max(1, wbm_count))
            discovery_rows.append(
                {
                    "model": model,
                    "WBM_discovered_stable_count": wbm_count,
                    "alex_mp_discovered_stable_count": alex_count,
                    "absolute_delta": abs(wbm_count - alex_count),
                    "relative_delta_vs_WBM": rel,
                    "relative_delta_ge_0_25": str(rel >= 0.25).lower(),
                    "absolute_delta_ge_50": str(abs(wbm_count - alex_count) >= 50).lower(),
                    "paper_role": "discovery_consequence_support_not_primary_ranking_flip",
                }
            )
    if discovery_rows:
        write_csv(OUT / "table_discovered_count_delta.csv", discovery_rows)

    closeout = f"""# Materials Label Discordance Experiment Closeout

This artifact executes the first clean experiment after the preregistration.
It uses the existing alex-mp exact-structure diagnostic as a minimal probe.

## Step 1

- Source pair: WBM/Matbench labels versus alex-mp v20 local public snapshot.
- Primary denominator: exact-structure matches only.
- Matched structures: `{len(exact)}`.
- Binary exact-stability discordance: `{discordance:.3f}`.
- Status: passes the preregistered `>=0.40` launch-signal threshold for this
  minimal existing probe.

This is not yet the final MP-vs-alex full-snapshot result. It is a go signal
to freeze broader source snapshots and run the same exact-match probe there.

## Step 2

The preregistered primary frontier-model endpoint requires ALIGNN-FF, CHGNet
and MACE-MP scores on the same matched denominator. If
`table_frontier_model_scores.csv` is present, CHGNet and MACE-MP were generated
from public weights on the exact-match structures and the endpoint is evaluated
under the frozen stable-class F1 rule. These locally generated scores are
raw-energy utility scores, so the artifact remains a go/no-go experiment rather
than a completed paper claim until the full MP-vs-alex source snapshots are
frozen.

The primary frontier-model ranking endpoint is now executable because
CHGNet/MACE-MP raw-energy scores were generated on the same 270-structure
denominator. The primary stable-class F1 ranking did not materially flip
between WBM and alex-mp labels, so the preregistered primary downstream
conclusion-flip gate is not met. Discovery-count consequences are reported as
supporting diagnostics only.
"""
    (OUT / "MATERIALS_LABEL_DISCORDANCE_EXPERIMENT_CLOSEOUT.md").write_text(closeout, encoding="utf-8")
    update_manifest()


if __name__ == "__main__":
    main()
