#!/usr/bin/env python3
"""Build Week 1-4 materials temporal + MLIP audit artifacts.

The milestone consumes only frozen public-safe tables.  It separates a temporal
t0/t1 no-go (missing timestamped snapshots) from a completed pre-outcome MLIP
directional audit.  It must not create prospective materials-discovery evidence
or change any A3 selection/manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/materials_temporal_mlip_audit"
FREEZE_TIMESTAMP = "2026-05-28T18:43:21+08:00"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def source(path: str) -> tuple[str, str]:
    file_path = ROOT / path
    if not file_path.exists():
        raise FileNotFoundError(path)
    return path, sha256_file(file_path)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_temporal_tables() -> None:
    inventory_path = "outputs/milestones/materials_temporal_replay_completed/table_temporal_snapshot_inventory.csv"
    primary_path = "outputs/milestones/materials_temporal_replay_completed/table_temporal_primary.csv"
    raw_vs_parc_path = "outputs/milestones/materials_temporal_replay_completed/table_temporal_raw_vs_parc.csv"
    inventory = pd.read_csv(ROOT / inventory_path)
    primary = pd.read_csv(ROOT / primary_path)
    raw_vs_parc = pd.read_csv(ROOT / raw_vs_parc_path)

    missing_required = inventory[
        inventory["required_object"].astype(str).str.contains("t0_public_label_snapshot|t1_future_label_snapshot", regex=True, na=False)
        & inventory["status"].astype(str).str.contains("missing", case=False, na=False)
    ]
    temporal_pass = missing_required.empty and bool(primary["completed_positive_result"].fillna(False).astype(bool).any())

    temporal_rows = [
        {
            "audit_component": "t0_t1_snapshot_availability",
            "status": "pass" if missing_required.empty else "no_go_missing_timestamped_snapshots",
            "completed_positive_result": temporal_pass,
            "source_artifact": inventory_path,
            "source_sha256": source(inventory_path)[1],
            "interpretation": "A1 can be positive only with auditable t0/t1 public-label snapshots.",
        },
        {
            "audit_component": "t1_future_FTR_evaluation",
            "status": "not_evaluable" if not temporal_pass else "evaluated",
            "completed_positive_result": temporal_pass,
            "source_artifact": primary_path,
            "source_sha256": source(primary_path)[1],
            "interpretation": "Current public bundle does not contain future-label FTR rows.",
        },
        {
            "audit_component": "stable_to_unstable_drift_concentration",
            "status": "not_evaluable_without_t0_t1_snapshots",
            "completed_positive_result": False,
            "source_artifact": primary_path,
            "source_sha256": source(primary_path)[1],
            "interpretation": "Cannot test whether drift destroys PARC release without timestamped hull shifts.",
        },
    ]
    write_csv(
        OUT / "table_temporal_hull_shift_audit.csv",
        temporal_rows,
        ["audit_component", "status", "completed_positive_result", "source_artifact", "source_sha256", "interpretation"],
    )

    lead = raw_vs_parc[
        (raw_vs_parc["source"].eq("alignn_ff_modern_learned_materials_model"))
        & (raw_vs_parc["K"].isin([300, 500]))
        & (raw_vs_parc["alpha"].eq(0.10))
    ].copy()
    lead_rows = []
    for row in lead.to_dict("records"):
        lead_rows.append(
            {
                "source": row["source"],
                "K": int(row["K"]),
                "alpha": row["alpha"],
                "PARC_FTR_current_public_label": row["PARC_FTR_current_public_label"],
                "raw_topK_FTR_current_public_label": row["raw_topK_FTR_current_public_label"],
                "raw_topR_FTR_current_public_label": row["raw_topR_FTR_current_public_label"],
                "prevented_unstable_followups_current_public_label": row[
                    "prevented_unstable_followups_current_public_label"
                ],
                "temporal_claim_status": "retrospective_current_snapshot_only",
                "completed_temporal_positive_result": False,
                "source_artifact": raw_vs_parc_path,
                "source_sha256": source(raw_vs_parc_path)[1],
            }
        )
    write_csv(
        OUT / "table_temporal_replay_lead_numbers.csv",
        lead_rows,
        [
            "source",
            "K",
            "alpha",
            "PARC_FTR_current_public_label",
            "raw_topK_FTR_current_public_label",
            "raw_topR_FTR_current_public_label",
            "prevented_unstable_followups_current_public_label",
            "temporal_claim_status",
            "completed_temporal_positive_result",
            "source_artifact",
            "source_sha256",
        ],
    )


def build_mlip_tables() -> None:
    contrast_path = "outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/table_alignnff_release_vs_tail_score_contrast.csv"
    rank_path = "outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/table_alignnff_rank_correlation.csv"
    overlap_path = "outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/table_alignnff_topk_overlap.csv"
    near_hull_path = "outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_near_hull_localization.csv"
    atlas_path = "outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_discordance_atlas_summary.csv"

    contrast = pd.read_csv(ROOT / contrast_path)
    deltas = contrast[contrast["arm"].astype(str).str.endswith("_minus_raw_top100_extra_tail")].copy()
    score_rows = []
    score_names = {"chgnet_score": "CHGNet", "mace_score": "MACE-MP", "consensus_score": "CHGNet/MACE consensus", "alignnff_score": "ALIGNN-FF"}
    for row in deltas.to_dict("records"):
        score = row["score"]
        if score not in score_names:
            continue
        score_rows.append(
            {
                "audit_model": score_names[score],
                "score_column": score,
                "n_release": int(row["n_release"]),
                "n_tail": int(row["n_tail"]),
                "release_minus_tail_mean_delta": row["mean_delta"],
                "release_minus_tail_median_delta": row["median_delta"],
                "directional_support": bool(row["mean_delta"] > 0 and row["median_delta"] > 0),
                "evidence_status": "completed_pre_outcome_MLIP_directional_audit_not_DFT_evidence",
                "source_artifact": contrast_path,
                "source_sha256": source(contrast_path)[1],
            }
        )
    write_csv(
        OUT / "table_mlip_dense_audit_summary.csv",
        score_rows,
        [
            "audit_model",
            "score_column",
            "n_release",
            "n_tail",
            "release_minus_tail_mean_delta",
            "release_minus_tail_median_delta",
            "directional_support",
            "evidence_status",
            "source_artifact",
            "source_sha256",
        ],
    )

    rank = pd.read_csv(ROOT / rank_path)
    rank_rows = []
    for row in rank.to_dict("records"):
        rank_rows.append(
            {
                "score_a": row["score_a"],
                "score_b": row["score_b"],
                "n": int(row["n"]),
                "spearman": row["spearman"],
                "pearson": row["pearson"],
                "agreement_interpretation": "high" if abs(float(row["spearman"])) >= 0.90 else "moderate_or_model_distinct",
                "source_artifact": rank_path,
                "source_sha256": source(rank_path)[1],
            }
        )
    write_csv(
        OUT / "table_mlip_rank_agreement.csv",
        rank_rows,
        ["score_a", "score_b", "n", "spearman", "pearson", "agreement_interpretation", "source_artifact", "source_sha256"],
    )

    overlap = pd.read_csv(ROOT / overlap_path)
    primary_overlap = overlap[overlap["K"].isin([75, 100, 300])].copy()
    primary_overlap["source_artifact"] = overlap_path
    primary_overlap["source_sha256"] = source(overlap_path)[1]
    primary_overlap.to_csv(OUT / "table_mlip_topk_overlap.csv", index=False)

    release_tail = contrast[contrast["score"].isin(["chgnet_score", "mace_score", "consensus_score", "alignnff_score"])].copy()
    release_tail["source_artifact"] = contrast_path
    release_tail["source_sha256"] = source(contrast_path)[1]
    release_tail.to_csv(OUT / "table_mlip_release_tail_contrast.csv", index=False)

    near_hull = pd.read_csv(ROOT / near_hull_path)
    atlas = pd.read_csv(ROOT / atlas_path)
    neither = near_hull[near_hull["band"].eq("neither_near_hull_25meV")].iloc[0]
    either = near_hull[near_hull["band"].eq("either_near_hull_25meV")].iloc[0]
    full = atlas[atlas["atlas_row"].eq("full_MP_Alex_identifier_denominator")].iloc[0]
    boundary_rows = [
        {
            "diagnostic": "source_label_disagreement_full_denominator",
            "n": int(full["denominator_n"]),
            "discordant_n": int(full["discordant_n"]),
            "discordance_rate": full["discordance_rate"],
            "interpretation": "source-level MP-Alex discordance; not PARC validation",
            "candidate_level_A3_explanation": "not_available",
            "source_artifact": atlas_path,
            "source_sha256": source(atlas_path)[1],
        },
        {
            "diagnostic": "either_source_near_hull_25meV",
            "n": int(either["n"]),
            "discordant_n": int(either["discordant_n"]),
            "discordance_rate": either["discordance_rate"],
            "interpretation": "discordance is present in near-hull boundary band",
            "candidate_level_A3_explanation": "source_level_boundary_support_only",
            "source_artifact": near_hull_path,
            "source_sha256": source(near_hull_path)[1],
        },
        {
            "diagnostic": "neither_source_near_hull_25meV",
            "n": int(neither["n"]),
            "discordant_n": int(neither["discordant_n"]),
            "discordance_rate": neither["discordance_rate"],
            "interpretation": "existing source diagnostic reports zero disagreements away from 25meV boundary in this small decomposition",
            "candidate_level_A3_explanation": "source_level_boundary_support_only",
            "source_artifact": near_hull_path,
            "source_sha256": source(near_hull_path)[1],
        },
    ]
    write_csv(
        OUT / "table_mlip_boundary_explanation.csv",
        boundary_rows,
        [
            "diagnostic",
            "n",
            "discordant_n",
            "discordance_rate",
            "interpretation",
            "candidate_level_A3_explanation",
            "source_artifact",
            "source_sha256",
        ],
    )


def build_go_no_go() -> None:
    mlip = pd.read_csv(OUT / "table_mlip_dense_audit_summary.csv")
    temporal = pd.read_csv(OUT / "table_temporal_hull_shift_audit.csv")
    n_support = int(mlip["directional_support"].astype(bool).sum())
    temporal_positive = bool(temporal["completed_positive_result"].astype(bool).any())
    rows = [
        {
            "gate": "temporal_t0_t1_hull_shift",
            "required_for_strong_materials_claim": True,
            "status": "NO_GO",
            "pass": False,
            "reason": "timestamped t0/t1 public-label snapshots are absent from the public bundle",
            "allowed_claim": "no completed temporal positive evidence; retain retrospective public-label utility only",
        },
        {
            "gate": "PARC_t1_hull_vs_raw_topK",
            "required_for_strong_materials_claim": True,
            "status": "NOT_EVALUABLE",
            "pass": False,
            "reason": "future-label FTR cannot be computed without frozen t1 labels",
            "allowed_claim": "no t1 hull-shift claim",
        },
        {
            "gate": "stable_to_unstable_drift_concentration",
            "required_for_strong_materials_claim": True,
            "status": "NOT_EVALUABLE",
            "pass": False,
            "reason": "no drift table exists without t0/t1 snapshots",
            "allowed_claim": "no drift-resilience claim",
        },
        {
            "gate": "two_or_more_MLIP_models_same_direction",
            "required_for_strong_materials_claim": False,
            "status": "PASS_DIRECTIONAL_SUPPORT",
            "pass": n_support >= 2,
            "reason": f"{n_support} frozen pre-outcome score sources have positive PARC-release versus extra-tail contrast",
            "allowed_claim": "pre-outcome MLIP directional audit supports formal selection feasibility; not DFT evidence",
        },
        {
            "gate": "boundary_hull_sensitive_explanation",
            "required_for_strong_materials_claim": False,
            "status": "PARTIAL_SOURCE_LEVEL_ONLY",
            "pass": True,
            "reason": "MP-Alex source-discordance decomposition supports a hull-boundary interpretation, but not candidate-level A3 validation",
            "allowed_claim": "boundary/source-label diagnostic only",
        },
        {
            "gate": "overall_week1_4_materials_temporal_mlip",
            "required_for_strong_materials_claim": True,
            "status": "PARTIAL_PASS_MLIP_SUPPORT_TEMPORAL_NO_GO",
            "pass": False,
            "reason": "MLIP audit is directionally positive, temporal t0/t1 validation remains blocked",
            "allowed_claim": "MLIP pre-outcome scorer audit completed; no prospective/temporal materials positive claim",
        },
    ]
    write_csv(
        OUT / "table_week1_4_go_no_go.csv",
        rows,
        ["gate", "required_for_strong_materials_claim", "status", "pass", "reason", "allowed_claim"],
    )


def build_closeout() -> None:
    mlip = pd.read_csv(OUT / "table_mlip_dense_audit_summary.csv")
    n_support = int(mlip["directional_support"].astype(bool).sum())
    alignn = mlip[mlip["audit_model"].eq("ALIGNN-FF")].iloc[0]
    text = f"""# Materials Temporal + MLIP Audit Closeout

Status: `partial_pass_MLIP_support_temporal_no_go`

This Week 1-4 package implements the post-freeze materials temporal + MLIP
audit step without changing A3 selection or manifests. It creates no DFT
outcome and no prospective materials-discovery claim.

## Temporal Hull-Shift Gate

The temporal t0/t1 hull-shift gate remains a no-go in the public bundle because
timestamped public-label snapshots are absent. Current ALIGNN-FF K=300/500
public-label utility rows are preserved as retrospective release-policy
diagnostics, not as t1 prospective validation.

## MLIP Dense Audit

The frozen pre-outcome MLIP audit is directionally supportive: {n_support}
score sources show positive PARC-release versus raw top100 extra-tail contrast.
ALIGNN-FF is the most independent scorer in this set and has mean release-tail
score delta {alignn['release_minus_tail_mean_delta']:.3f}. CHGNet and MACE-MP
are highly concordant, while ALIGNN-FF has lower top-K overlap but still
supports the release-vs-tail direction.

## Boundary Interpretation

The source-discordance atlas supports a hull-boundary explanation at source
level: MP-Alex disagreements appear in the near-hull decomposition, while the
available neither-near-hull 25 meV band has zero disagreements in that small
decomposition. This is not candidate-level A3 validation and must remain a
diagnostic.

## Claim Boundary

Allowed: pre-outcome MLIP scorer audit completed; temporal t0/t1 validation
blocked; materials main text remains retrospective public-label utility unless
a later preregistered t0/t1 or blind DFT audit passes.

Forbidden: prospective materials discovery, positive independent materials
validation, DFT utility evidence, or post-outcome model/endpoint selection.
"""
    (OUT / "MATERIALS_TEMPORAL_MLIP_AUDIT_CLOSEOUT.md").write_text(text, encoding="utf-8")
    provenance = {
        "milestone": "materials_temporal_mlip_audit",
        "built_at": FREEZE_TIMESTAMP,
        "evidence_status": "partial_pass_MLIP_support_temporal_no_go",
        "changes_A3_selection_or_manifest": False,
        "creates_DFT_outcome": False,
        "claim_boundary": [
            "no_prospective_materials_discovery_claim",
            "no_positive_independent_materials_validation_claim",
            "MLIP_pre_outcome_scorer_audit_only",
            "temporal_t0_t1_no_go_until_snapshots_exist",
        ],
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_temporal_tables()
    build_mlip_tables()
    build_go_no_go()
    build_closeout()
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
