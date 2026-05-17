#!/usr/bin/env python3
"""Build the scientific-AI release-certification benchmark cards.

This script does not run new experiments. It standardizes completed release,
refusal and diagnostic rows into a reusable governance-card format so external
users can see how to instantiate PARC on a new finite candidate universe.
Protocol-only ideas are represented only as checklist/schema rows, not as
completed evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_int(value, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(round(float(value)))
    except Exception:
        return default


def load_tables() -> dict[str, pd.DataFrame]:
    paths = {
        "ctc_strict": ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv",
        "ctc_human": ROOT / "outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_go_no_go.csv",
        "ctc_human_summary": ROOT / "outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_summary.csv",
        "materials_trial": ROOT / "outputs/milestones/materials_computational_followup_trial/table_materials_computational_trial_summary.csv",
        "iwildcam": ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv",
        "downstream_ctc": ROOT / "outputs/milestones/official_downstream_consequence/table_ctc_official_lineage_metric_summary.csv",
        "downstream_spacenet": ROOT / "outputs/milestones/official_downstream_consequence/table_spacenet_map_metric_summary.csv",
        "validity": ROOT / "outputs/milestones/scientific_release_success_map/table_validity_assumptions_by_domain.csv",
    }
    return {key: pd.read_csv(path) for key, path in paths.items()}


def build_cards(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cards: list[dict] = []

    ctc = tables["ctc_strict"]
    ctc_k300 = ctc[(ctc["alpha"].astype(float).eq(0.10)) & (ctc["M"].astype(int).eq(300))].iloc[0]
    cards.append(
        {
            "card_id": "ctc_learned_strict_alpha010_K300",
            "track_id": "biomedical_cell_link_release",
            "domain": "biomedical_cell_tracking",
            "dataset": "Cell Tracking Challenge",
            "release_unit": "adjacent-frame cell link",
            "proposal_source": "learned_hybrid_appearance_linker",
            "verification_source": "masked CTC GT positives; human-confirmed strict audit closeout available",
            "block_definition": str(ctc_k300["block_variant"]),
            "alpha": clean_float(ctc_k300["alpha"]),
            "requested_K": clean_int(ctc_k300["M"]),
            "seeds": clean_int(ctc_k300["seeds"]),
            "non_empty_seeds": clean_int(ctc_k300["nonempty_seeds"]),
            "mean_release": clean_float(ctc_k300["released_mean"]),
            "PARC_FTR": clean_float(ctc_k300["actual_FTR_mean"]),
            "raw_topK_FTR": clean_float(ctc_k300["raw_topM_actual_FTR_mean"]),
            "PARC_decision": "certified_release",
            "risk_regime": "strict_alpha010",
            "downstream_artifact": "cell lineage graph",
            "consequence_metric": "release-quality cell-link FTR",
            "consequence_prevented": 0.0,
            "evidence_status": "completed_evidence",
            "paper_status": "strict_flagship_card",
            "primary_artifact": "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv",
            "scope_limitations": "release certification for candidate links, not an end-to-end cell tracker claim",
        }
    )

    if "ctc_human" in tables and len(tables["ctc_human"]):
        human = tables["ctc_human"].iloc[0]
        release_summary = tables["ctc_human_summary"][
            tables["ctc_human_summary"]["queue"].eq("simulated_strict_release")
        ].iloc[0]
        release_rows = clean_int(human.get("observed_rows", release_summary["rows"]))
        release_ftr = clean_float(human.get("observed_human_FTR_false_only", release_summary["human_FTR_false_only"]))
        cards.append(
            {
                "card_id": "ctc_strict_human_confirmed_release_queue",
                "track_id": "biomedical_cell_link_release",
                "domain": "biomedical_cell_tracking",
                "dataset": "Cell Tracking Challenge",
                "release_unit": "adjacent-frame cell link",
                "proposal_source": "learned_hybrid_appearance_linker",
                "verification_source": "human-confirmed strict audit queue",
                "block_definition": "frame_pair_blocks",
                "alpha": clean_float(human.get("required_human_FTR_max", 0.10), 0.10),
                "requested_K": release_rows,
                "seeds": clean_int(human.get("seeds", 20), 20),
                "non_empty_seeds": clean_int(human.get("non_empty_seeds", 20), 20),
                "mean_release": float(release_rows),
                "PARC_FTR": release_ftr,
                "raw_topK_FTR": clean_float(human.get("raw_topK_human_FTR", 0.0)),
                "PARC_decision": "human_confirmed_release",
                "risk_regime": "strict_alpha010_human_closeout",
                "downstream_artifact": "cell lineage graph",
                "consequence_metric": "human-confirmed release queue FTR",
                "consequence_prevented": 0.0,
                "evidence_status": "completed_human_confirmed_closeout",
                "paper_status": "strict_human_audit_card",
                "primary_artifact": "outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_go_no_go.csv",
                "scope_limitations": "human-confirmed strict-release queue aggregated across seeds; no separate microscopy-expert adjudication claim",
            }
        )

    materials = tables["materials_trial"]
    for model_family, budget, status in [("ALIGNN-FF", 500, "certified_release"), ("ALIGNN-FF", 5000, "certified_refusal")]:
        row = materials[
            (materials["model_family"].eq(model_family))
            & (materials["alpha"].astype(float).eq(0.10))
            & (materials["K"].astype(int).eq(budget))
        ].iloc[0]
        cards.append(
            {
                "card_id": f"materials_alignn_followup_alpha010_K{budget}",
                "track_id": "materials_computational_followup",
                "domain": "materials_discovery",
                "dataset": "Matbench Discovery WBM unique prototypes",
                "release_unit": "stable inorganic crystal candidate",
                "proposal_source": str(row["proposal_source"]),
                "verification_source": "pre-release DFT-stable positives in calibration blocks",
                "block_definition": str(row["block_definition"]),
                "alpha": clean_float(row["alpha"]),
                "requested_K": clean_int(row["K"]),
                "seeds": clean_int(row["seeds"]),
                "non_empty_seeds": clean_int(row["non_empty_seeds"]),
                "mean_release": clean_float(row["mean_release"]),
                "PARC_FTR": clean_float(row["PARC_FTR_mean"]),
                "raw_topK_FTR": clean_float(row["raw_topK_FTR_mean"]),
                "PARC_decision": status,
                "risk_regime": "strict_alpha010_quasi_prospective_public_DFT",
                "downstream_artifact": "DFT computational follow-up queue",
                "consequence_metric": "unstable follow-ups prevented",
                "consequence_prevented": clean_float(row["unstable_followups_prevented_mean"]),
                "evidence_status": str(row["evidence_status"]),
                "paper_status": "completed_quasi_prospective_card",
                "primary_artifact": "outputs/milestones/materials_computational_followup_trial/table_materials_computational_trial_summary.csv",
                "scope_limitations": "public-label replay; no new DFT, experimental synthesis, or true prospective discovery claim",
            }
        )

    iw = tables["iwildcam"]
    iw_k50 = iw[(iw["alpha"].astype(float).eq(0.20)) & (iw["K"].astype(int).eq(50))].iloc[0]
    cards.append(
        {
            "card_id": "iwildcam_animal_human_audit_alpha020_K50",
            "track_id": "ecology_camera_trap_animal_release",
            "domain": "ecological_camera_traps",
            "dataset": "iWildCam camera-trap subset",
            "release_unit": "animal-present detection box",
            "proposal_source": str(iw_k50["source_name"]),
            "verification_source": "human-confirmed animal-present positives",
            "block_definition": "camera location x temporal chunk",
            "alpha": clean_float(iw_k50["alpha"]),
            "requested_K": clean_int(iw_k50["K"]),
            "seeds": 20,
            "non_empty_seeds": clean_int(iw_k50["non_empty_seeds"]),
            "mean_release": clean_float(iw_k50["mean_release"]),
            "PARC_FTR": clean_float(iw_k50["human_FTR"]),
            "raw_topK_FTR": clean_float(iw_k50["mean_raw_topK_official_proxy_FTR"]),
            "PARC_decision": "human_confirmed_operational_release",
            "risk_regime": "operational_alpha020",
            "downstream_artifact": "camera-trap animal-detection release list",
            "consequence_metric": "human-audited animal-present FTR",
            "consequence_prevented": 0.0,
            "evidence_status": "completed_human_confirmed_operational_evidence",
            "paper_status": "operational_card_not_strict",
            "primary_artifact": "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv",
            "scope_limitations": "strict alpha=0.10 refused; this is operational alpha=0.20 ecology evidence",
        }
    )

    down_ctc = tables["downstream_ctc"]
    for source in ["ctc_noisy_geometric_linker", "ctc_random_score_negative_control"]:
        row = down_ctc[
            (down_ctc["proposal_source"].eq(source))
            & (down_ctc["K"].astype(int).eq(5000))
        ].iloc[0]
        cards.append(
            {
                "card_id": f"{source}_official_lineage_refusal_K5000",
                "track_id": "biomedical_lineage_artifact_guardrail",
                "domain": "biomedical_cell_tracking",
                "dataset": "Cell Tracking Challenge",
                "release_unit": "adjacent-frame cell link",
                "proposal_source": source,
                "verification_source": "official/held-out CTC lineage identities",
                "block_definition": "video/frame-pair blocks",
                "alpha": clean_float(row["alpha"]),
                "requested_K": clean_int(row["K"]),
                "seeds": clean_int(row["seeds"]),
                "non_empty_seeds": clean_int(row["non_empty_seeds"]),
                "mean_release": clean_float(row["PARC_released_mean"]),
                "PARC_FTR": clean_float(row["PARC_false_edge_fraction_mean"]),
                "raw_topK_FTR": clean_float(row["raw_false_edge_fraction_mean"]),
                "PARC_decision": "certified_refusal",
                "risk_regime": "strict_alpha010_downstream_guardrail",
                "downstream_artifact": "cell lineage graph",
                "consequence_metric": "prevented false lineage edges",
                "consequence_prevented": clean_float(row["prevented_false_lineage_edges_mean"]),
                "evidence_status": str(row["evidence_status"]),
                "paper_status": "downstream_guardrail_card",
                "primary_artifact": "outputs/milestones/official_downstream_consequence/table_ctc_official_lineage_metric_summary.csv",
                "scope_limitations": "TRA/AOGM-style values are edge-edit proxies, not official challenge leaderboard scores",
            }
        )

    down_sn = tables["downstream_spacenet"]
    for source in ["spacenet_geometry_linker", "spacenet_identity_preserving_random_score_control"]:
        row = down_sn[
            (down_sn["proposal_source"].eq(source))
            & (down_sn["K"].astype(int).eq(5000))
        ].iloc[0]
        cards.append(
            {
                "card_id": f"{source}_official_map_K5000",
                "track_id": "earth_observation_persistence_map_guardrail",
                "domain": "earth_observation",
                "dataset": "SpaceNet 7 official building identities",
                "release_unit": "same-building temporal link",
                "proposal_source": source,
                "verification_source": "official SpaceNet building identities",
                "block_definition": "AOI x time block",
                "alpha": clean_float(row["alpha"]),
                "requested_K": clean_int(row["K"]),
                "seeds": clean_int(row["seeds"]),
                "non_empty_seeds": clean_int(row["non_empty_seeds"]),
                "mean_release": clean_float(row["PARC_released_mean"]),
                "PARC_FTR": clean_float(row["PARC_false_link_fraction_mean"]),
                "raw_topK_FTR": clean_float(row["raw_false_link_fraction_mean"]),
                "PARC_decision": "certified_refusal" if clean_int(row["non_empty_seeds"]) == 0 else "boundary_release_refusal_frontier",
                "risk_regime": "operational_alpha020_downstream_guardrail",
                "downstream_artifact": "building-persistence map",
                "consequence_metric": "prevented false persistence links",
                "consequence_prevented": clean_float(row["prevented_false_persistence_links_mean"]),
                "evidence_status": str(row["evidence_status"]),
                "paper_status": "downstream_guardrail_card",
                "primary_artifact": "outputs/milestones/official_downstream_consequence/table_spacenet_map_metric_summary.csv",
                "scope_limitations": "link-derived map artifact proxy from official identities, not a new geospatial challenge score",
            }
        )
    return pd.DataFrame(cards)


def build_registry(cards: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "track_id": "biomedical_cell_link_release",
            "track_name": "CTC cell-link release certification",
            "domain": "biomedical_cell_tracking",
            "release_unit": "adjacent-frame cell link",
            "verification_mode": "masked official positives plus human-confirmed queue closeout",
            "downstream_artifact": "cell lineage graph",
            "primary_cards": "ctc_learned_strict_alpha010_K300;ctc_strict_human_confirmed_release_queue",
            "recommended_metric": "PARC_FTR; raw_topK_FTR; non_empty_seeds",
            "intended_use": "strict release-card template for learned scientific link sources",
            "limitations": "candidate-link certification, not end-to-end tracking",
            "evidence_status": "completed_evidence",
        },
        {
            "track_id": "materials_computational_followup",
            "track_name": "Materials computational follow-up queue",
            "domain": "materials_discovery",
            "release_unit": "stable inorganic crystal candidate",
            "verification_mode": "pre-release DFT-stable positives in calibration blocks",
            "downstream_artifact": "DFT follow-up queue",
            "primary_cards": "materials_alignn_followup_alpha010_K500;materials_alignn_followup_alpha010_K5000",
            "recommended_metric": "unstable_followups_prevented; PARC_DFT_efficiency; raw_DFT_efficiency",
            "intended_use": "quasi-prospective public-label release/refusal queue template",
            "limitations": "no new DFT or synthesis claim",
            "evidence_status": "completed_evidence",
        },
        {
            "track_id": "ecology_camera_trap_animal_release",
            "track_name": "Camera-trap animal-present release",
            "domain": "ecological_camera_traps",
            "release_unit": "animal-present detection box",
            "verification_mode": "human-confirmed one-sided positives",
            "downstream_artifact": "animal-detection release list",
            "primary_cards": "iwildcam_animal_human_audit_alpha020_K50",
            "recommended_metric": "human_FTR; conservative_human_FTR; strict-refusal diagnostic",
            "intended_use": "operational human-audit card for real partial verification",
            "limitations": "operational alpha=0.20; strict alpha=0.10 refused",
            "evidence_status": "completed_operational_evidence",
        },
        {
            "track_id": "biomedical_lineage_artifact_guardrail",
            "track_name": "CTC lineage artifact guardrail",
            "domain": "biomedical_cell_tracking",
            "release_unit": "adjacent-frame cell link",
            "verification_mode": "official CTC lineage identities",
            "downstream_artifact": "cell lineage graph",
            "primary_cards": "ctc_noisy_geometric_linker_official_lineage_refusal_K5000;ctc_random_score_negative_control_official_lineage_refusal_K5000",
            "recommended_metric": "prevented_false_lineage_edges; edge-edit burden proxy",
            "intended_use": "downstream-consequence refusal card",
            "limitations": "edit-burden proxy, not official challenge score",
            "evidence_status": "completed_diagnostic",
        },
        {
            "track_id": "earth_observation_persistence_map_guardrail",
            "track_name": "SpaceNet building-persistence map guardrail",
            "domain": "earth_observation",
            "release_unit": "same-building temporal link",
            "verification_mode": "official SpaceNet building identities",
            "downstream_artifact": "building-persistence map",
            "primary_cards": "spacenet_geometry_linker_official_map_K5000;spacenet_identity_preserving_random_score_control_official_map_K5000",
            "recommended_metric": "prevented_false_persistence_links; map-edit burden proxy",
            "intended_use": "map-artifact release/refusal card",
            "limitations": "link-derived proxy, not new geospatial benchmark score",
            "evidence_status": "completed_diagnostic",
        },
    ]
    registry = pd.DataFrame(rows)
    registry["n_cards"] = registry["track_id"].map(cards.groupby("track_id").size()).fillna(0).astype(int)
    return registry


def build_field_schema() -> pd.DataFrame:
    rows = [
        ("card_id", "string", "Stable unique card identifier.", "required"),
        ("track_id", "string", "Reusable benchmark track identifier.", "required"),
        ("domain", "string", "Scientific or benchmark domain.", "required"),
        ("dataset", "string", "Source dataset or public label collection.", "required"),
        ("release_unit", "string", "Finite candidate object released or refused.", "required"),
        ("proposal_source", "string", "Frozen upstream model/source ranking candidates.", "required"),
        ("verification_source", "string", "One-sided positive support used by PARC.", "required"),
        ("block_definition", "string", "Exchangeability/coverage block construction.", "required"),
        ("alpha", "float", "Certified risk target for the card.", "required"),
        ("requested_K", "integer", "Requested raw release/follow-up budget.", "required"),
        ("seeds", "integer", "Number of split/randomization seeds.", "required"),
        ("non_empty_seeds", "integer", "Seeds with non-empty PARC release.", "required"),
        ("mean_release", "float", "Mean release size across seeds.", "required"),
        ("PARC_FTR", "float", "Realized false-release fraction on the card evaluation source.", "required"),
        ("raw_topK_FTR", "float", "Raw top-K false fraction on the same evaluation source.", "required"),
        ("PARC_decision", "enum", "certified_release, certified_refusal, operational_release, or diagnostic frontier.", "required"),
        ("risk_regime", "string", "Strict, operational, or downstream-guardrail regime.", "required"),
        ("downstream_artifact", "string", "Scientific object passed downstream.", "required"),
        ("consequence_metric", "string", "Workflow metric summarized by the card.", "required"),
        ("consequence_prevented", "float", "Prevented false candidates or edit-burden proxy units when applicable.", "optional"),
        ("evidence_status", "enum", "completed_evidence, completed_diagnostic, completed_human_confirmed_closeout, or protocol_only.", "required"),
        ("paper_status", "string", "How the card may be used in writing.", "required"),
        ("primary_artifact", "path", "Primary public-safe evidence file.", "required"),
        ("scope_limitations", "string", "Required limitation language.", "required"),
    ]
    return pd.DataFrame(rows, columns=["field", "type", "definition", "requirement"])


def build_governance_checklist() -> pd.DataFrame:
    rows = [
        (1, "freeze_candidate_universe", "Freeze candidate IDs, scores, proposal source and requested budgets before release.", "pre_release"),
        (2, "define_release_unit", "State exactly what object can be released: link, detection, material candidate, or map edge.", "pre_release"),
        (3, "define_one_sided_positive_rule", "Only high-precision positive support may enter A=1; negative/uncertain labels remain unverified.", "pre_release"),
        (4, "define_blocks", "Declare exchangeability/coverage blocks and empty-block policy.", "pre_release"),
        (5, "lock_alpha_K_seed_grid", "Declare alpha, K and seeds before evaluating held-out/full labels.", "pre_release"),
        (6, "run_parc_release_or_refusal", "Run null-superset calibration and SCS release/refusal on the frozen universe.", "release"),
        (7, "evaluate_on_heldout_or_human_source", "Evaluate realized FTR only after the release decision using held-out official, DFT or human labels.", "post_release"),
        (8, "report_raw_baseline", "Report raw top-K risk on the same evaluation source.", "post_release"),
        (9, "report_downstream_artifact", "Translate release/refusal into the downstream workflow object when available.", "post_release"),
        (10, "write_release_card", "Publish card, provenance, evidence status, limitations and manifest hash.", "public_release"),
    ]
    return pd.DataFrame(rows, columns=["step", "check_name", "description", "stage"])


def build_benchmark_index(cards: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in registry.itertuples(index=False):
        track_cards = cards[cards["track_id"] == row.track_id]
        rows.append(
            {
                "track_id": row.track_id,
                "track_name": row.track_name,
                "domain": row.domain,
                "n_cards": int(len(track_cards)),
                "strict_cards": int(track_cards["risk_regime"].astype(str).str.contains("strict").sum()),
                "human_confirmed_cards": int(track_cards["evidence_status"].astype(str).str.contains("human").sum()),
                "refusal_or_guardrail_cards": int(track_cards["PARC_decision"].astype(str).str.contains("refusal|guardrail", regex=True).sum()),
                "primary_artifacts": ";".join(sorted(set(track_cards["primary_artifact"].astype(str)))),
                "ready_for_community_reuse": bool(len(track_cards) > 0),
            }
        )
    return pd.DataFrame(rows)


def plot_cards(cards: pd.DataFrame, out_csv: Path, out_pdf: Path) -> None:
    figure = cards.copy()
    figure["release_or_prevented_value"] = np.where(
        figure["mean_release"].astype(float) > 0,
        figure["mean_release"].astype(float),
        figure["consequence_prevented"].astype(float),
    )
    figure.to_csv(out_csv, index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.0))

    release = figure[figure["mean_release"].astype(float) > 0].copy()
    colors = {
        "biomedical_cell_tracking": "#1b9e77",
        "materials_discovery": "#7570b3",
        "ecological_camera_traps": "#66a61e",
        "earth_observation": "#e6ab02",
    }
    axes[0].scatter(
        release["mean_release"],
        release["PARC_FTR"],
        s=75,
        c=[colors.get(d, "#666666") for d in release["domain"]],
        edgecolor="black",
        linewidth=0.5,
    )
    for row in release.itertuples(index=False):
        axes[0].annotate(row.card_id.split("_")[0], (row.mean_release, row.PARC_FTR), fontsize=7, xytext=(3, 3), textcoords="offset points")
    axes[0].set_xlabel("Mean PARC release size")
    axes[0].set_ylabel("Realized FTR")
    axes[0].set_title("Release cards")
    axes[0].grid(alpha=0.25)

    guardrail = figure[figure["consequence_prevented"].astype(float) > 0].copy()
    guardrail = guardrail.sort_values("consequence_prevented", ascending=True)
    axes[1].barh(
        guardrail["card_id"].str.replace("_", " "),
        guardrail["consequence_prevented"].astype(float),
        color=[colors.get(d, "#666666") for d in guardrail["domain"]],
    )
    axes[1].set_xlabel("Consequence prevented")
    axes[1].set_title("Guardrail cards")
    axes[1].tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def write_markdown(out_dir: Path, cards: pd.DataFrame, registry: pd.DataFrame) -> None:
    strict = int(cards["risk_regime"].astype(str).str.contains("strict").sum())
    human = int(cards["evidence_status"].astype(str).str.contains("human").sum())
    refusal = int(cards["PARC_decision"].astype(str).str.contains("refusal").sum())
    text = f"""# Scientific AI Release Certification Benchmark

Evidence status: completed benchmark-card package.

This milestone packages completed PARC evidence into a reusable release-governance protocol. It does not add new experiments, human labels, or protocol-only positive rows. Each card identifies a frozen candidate source, one-sided verification source, block definition, requested risk/budget, release/refusal decision, evaluation source, and required limitation language.

Summary:
- Tracks: {len(registry)}
- Release cards: {len(cards)}
- Strict-risk cards: {strict}
- Human-confirmed cards: {human}
- Refusal or downstream-guardrail cards: {refusal}

Primary files:
- `table_release_certification_cards.csv`
- `table_release_certification_track_registry.csv`
- `table_release_card_field_schema.csv`
- `table_release_governance_checklist.csv`
- `table_release_certification_benchmark_index.csv`
- `figure_release_certification_benchmark_map.csv`
- `figure_release_certification_benchmark_map.pdf`

Use:
1. Select a track with a matching release unit.
2. Follow the governance checklist before inspecting held-out labels.
3. Fill the release-card fields for the new candidate universe.
4. Mark evidence as completed only after the release/refusal decision and evaluation are both finished.

Scope boundaries:
- CTC link cards certify candidate links, not an end-to-end tracker.
- Materials cards are public-label computational replay, not new DFT or synthesis.
- iWildCam is an operational alpha=0.20 card, not a strict alpha=0.10 success.
- SpaceNet and CTC downstream consequence cards report artifact proxies, not official leaderboard scores.
"""
    (out_dir / "SCIENTIFIC_AI_RELEASE_CERTIFICATION_BENCHMARK.md").write_text(text, encoding="utf-8")

    protocol = """# Release Certification Governance Protocol

This protocol is a reusable checklist for finite scientific-AI candidate universes under one-sided partial verification.

## Required Setup

1. Freeze the candidate universe and proposal-source scores.
2. Define the release unit and downstream artifact.
3. Define the one-sided positive rule: only confirmed positives enter `A=1`; uncertain, negative or disputed labels remain unverified.
4. Define blocks and the empty-block policy.
5. Freeze alpha, requested K values and seeds.

## Release Decision

Run PARC on the frozen universe. A certified refusal is a valid outcome when the observed evidence is insufficient for the requested release.

## Evaluation

Use held-out official labels, public DFT labels, or human-audit labels only after the release/refusal decision. Report raw top-K risk on the same evaluation source.

## Reporting

Every card must include evidence status and limitation language. Protocol-only designs must not be reported as completed evidence.
"""
    (out_dir / "RELEASE_CERTIFICATION_GOVERNANCE_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def write_provenance(path: Path, role: str, inputs: dict[str, str], started: float) -> None:
    payload = {
        "artifact": path.name,
        "role": role,
        "input_sha256": inputs,
        "command": "python scripts/build_release_certification_benchmark_cards.py",
        "runtime_sec": round(time.time() - started, 3),
        "output_sha256": sha256_file(path),
    }
    path.with_suffix(path.suffix + ".provenance.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="outputs/milestones/release_certification_benchmark")
    args = parser.parse_args()
    started = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_paths = {
        "ctc_strict": ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv",
        "ctc_human": ROOT / "outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_go_no_go.csv",
        "ctc_human_summary": ROOT / "outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_summary.csv",
        "materials_trial": ROOT / "outputs/milestones/materials_computational_followup_trial/table_materials_computational_trial_summary.csv",
        "iwildcam": ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv",
        "downstream_ctc": ROOT / "outputs/milestones/official_downstream_consequence/table_ctc_official_lineage_metric_summary.csv",
        "downstream_spacenet": ROOT / "outputs/milestones/official_downstream_consequence/table_spacenet_map_metric_summary.csv",
        "validity": ROOT / "outputs/milestones/scientific_release_success_map/table_validity_assumptions_by_domain.csv",
    }
    inputs = {key: sha256_file(path) for key, path in input_paths.items()}
    tables = load_tables()
    cards = build_cards(tables)
    registry = build_registry(cards)
    schema = build_field_schema()
    checklist = build_governance_checklist()
    index = build_benchmark_index(cards, registry)

    outputs = {
        "table_release_certification_cards.csv": (cards, "release_cards"),
        "table_release_certification_track_registry.csv": (registry, "track_registry"),
        "table_release_card_field_schema.csv": (schema, "field_schema"),
        "table_release_governance_checklist.csv": (checklist, "governance_checklist"),
        "table_release_certification_benchmark_index.csv": (index, "benchmark_index"),
    }
    for name, (frame, _role) in outputs.items():
        frame.to_csv(out_dir / name, index=False)
    plot_cards(cards, out_dir / "figure_release_certification_benchmark_map.csv", out_dir / "figure_release_certification_benchmark_map.pdf")
    write_markdown(out_dir, cards, registry)

    md_files = {
        "SCIENTIFIC_AI_RELEASE_CERTIFICATION_BENCHMARK.md": "benchmark_closeout",
        "RELEASE_CERTIFICATION_GOVERNANCE_PROTOCOL.md": "governance_protocol",
        "figure_release_certification_benchmark_map.csv": "figure_source",
        "figure_release_certification_benchmark_map.pdf": "figure",
    }
    for name, (frame, role) in outputs.items():
        write_provenance(out_dir / name, role, inputs, started)
    for name, role in md_files.items():
        write_provenance(out_dir / name, role, inputs, started)
    write_manifest(out_dir)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
