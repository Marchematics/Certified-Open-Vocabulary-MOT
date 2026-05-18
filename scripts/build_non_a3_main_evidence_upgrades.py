#!/usr/bin/env python3
"""Build non-A3 main-evidence hardening milestones.

The outputs here deliberately avoid promoting feasibility/protocol rows into
completed positives.  When a requested artifact needs unavailable temporal
snapshots or candidate-level graphs, the row is marked as diagnostic or
protocol-only.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "outputs" / "milestones"


NEW_MILESTONES = [
    "materials_temporal_replay_completed",
    "fixed_budget_scientific_utility_trial",
    "adversarial_release_stress_trial",
    "selector_optimality_diagnostics",
]


def read_csv(rel: str) -> pd.DataFrame:
    path = ROOT / rel
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def write_csv(path: Path, frame: pd.DataFrame | list[dict]) -> None:
    df = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(frame)
    df.to_csv(path, index=False)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(directory: Path) -> None:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(directory).as_posix()}")
    (directory / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def ensure_dir(name: str) -> Path:
    path = MILESTONES / name
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()
    return path


def safe_float(value, default: float = math.nan) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def build_materials_temporal_replay() -> None:
    out = ensure_dir("materials_temporal_replay_completed")
    existing = read_csv("outputs/milestones/materials_temporal_validation/table_materials_temporal_primary.csv")
    utility = read_csv("outputs/milestones/fixed_budget_downstream_utility/table_materials_budget_utility_primary.csv")

    snapshot_inventory = pd.DataFrame(
        [
            {
                "required_object": "t0_public_label_snapshot",
                "local_artifact": "not_available",
                "status": "missing_timestamped_public_label_release",
                "blocks_completed_positive": True,
            },
            {
                "required_object": "t1_future_label_snapshot",
                "local_artifact": "not_available",
                "status": "missing_timestamped_public_label_release",
                "blocks_completed_positive": True,
            },
            {
                "available_object": "current_WBM_public_label_followup",
                "local_artifact": "outputs/milestones/fixed_budget_downstream_utility/table_materials_budget_utility_primary.csv",
                "status": "available_for_retrospective_decision_replay_only",
                "blocks_completed_positive": False,
            },
        ]
    )
    write_csv(out / "table_temporal_snapshot_inventory.csv", snapshot_inventory)

    primary = pd.DataFrame(
        [
            {
                "domain": "materials_discovery",
                "trial": "materials_temporal_replay_completed",
                "requested_validation": "t0_to_t1_quasi_prospective_public_label_replay",
                "release_version_inputs": "missing_t0_t1_public_label_snapshots",
                "completed_replay": False,
                "completed_positive_result": False,
                "evidence_state": "protocol_only",
                "future_FTR": math.nan,
                "raw_topK_future_FTR": math.nan,
                "raw_vs_PARC_delta": math.nan,
                "claim_scope": "not a temporal validation result; current public-label utility is reported separately",
                "blocker": "No auditable historical public-label snapshot or release-version table is present in the public bundle.",
            }
        ]
    )
    write_csv(out / "table_temporal_primary.csv", primary)

    seed_cols = [
        "trial",
        "source",
        "K",
        "alpha",
        "seed",
        "PARC_release",
        "future_FTR",
        "raw_topK_future_FTR",
        "evidence_state",
        "completed_positive_result",
    ]
    write_csv(out / "table_temporal_seed_rows.csv", pd.DataFrame(columns=seed_cols))

    replay_rows = []
    for _, row in utility.iterrows():
        replay_rows.append(
            {
                "domain": row.get("domain", "materials_discovery"),
                "source": row.get("proposal_source", ""),
                "K": row.get("K", ""),
                "alpha": row.get("alpha", ""),
                "PARC_FTR_current_public_label": row.get("PARC_FTR_mean", math.nan),
                "raw_topK_FTR_current_public_label": row.get("raw_topK_FTR_mean", math.nan),
                "raw_topR_FTR_current_public_label": row.get("raw_topR_FTR_mean", math.nan),
                "prevented_unstable_followups_current_public_label": row.get(
                    "prevented_unstable_followups_mean", math.nan
                ),
                "temporal_status": "retrospective_current_snapshot_only",
                "evidence_state": "diagnostic",
                "completed_positive_result": False,
            }
        )
    write_csv(out / "table_temporal_raw_vs_parc.csv", replay_rows)

    write_csv(
        out / "table_temporal_claim_scope.csv",
        [
            {
                "claim": "A1 temporal public-label replay",
                "state": "not_completed",
                "reason": "requires versioned t0/t1 public labels",
                "allowed_use": "documents blocker and current-snapshot diagnostic only",
            },
            {
                "claim": "materials fixed-budget utility under current WBM labels",
                "state": "completed_elsewhere",
                "reason": "uses completed public DFT labels but not temporal replay",
                "allowed_use": "downstream utility / certified stopping evidence, not quasi-prospective validation",
            },
        ],
    )
    write_md(
        out / "MATERIALS_TEMPORAL_REPLAY_CLOSEOUT.md",
        """# Materials Temporal Replay Closeout

Status: `protocol_only` for the requested t0-to-t1 temporal validation.  The
public bundle does not contain auditable historical label-release snapshots, so
no future-label FTR or completed quasi-prospective positive is claimed.

The milestone also records a current-public-label raw-vs-PARC diagnostic copied
from the completed fixed-budget utility package.  That diagnostic is useful for
utility framing, but it is not temporal replay evidence.
""",
    )
    write_manifest(out)


def build_fixed_budget_scientific_utility() -> None:
    out = ensure_dir("fixed_budget_scientific_utility_trial")
    primary = read_csv("outputs/milestones/fixed_budget_downstream_utility/table_materials_budget_utility_primary.csv")
    seeds = read_csv("outputs/milestones/fixed_budget_downstream_utility/table_materials_budget_utility_seed_rows.csv")
    ctc = read_csv("outputs/milestones/fixed_budget_downstream_utility/table_ctc_lineage_consequence.csv")
    spacenet = read_csv("outputs/milestones/fixed_budget_downstream_utility/table_spacenet_persistence_consequence.csv")

    write_csv(out / "table_fixed_budget_primary.csv", primary)
    write_csv(out / "table_fixed_budget_seed_rows.csv", seeds)

    curve_cols = [
        "proposal_source",
        "K",
        "alpha",
        "mean_release",
        "raw_unstable_count_mean",
        "PARC_unstable_count_mean",
        "prevented_unstable_followups_mean",
        "DFT_efficiency_mean",
        "raw_DFT_efficiency_mean",
        "release_status",
        "evidence_state",
    ]
    curve = primary.copy()
    curve["evidence_state"] = "completed_evidence"
    write_csv(out / "table_decision_curve.csv", curve[[c for c in curve_cols if c in curve.columns]])

    cost = primary.copy()
    cost["true_candidates_PARC_mean"] = cost["mean_release"].astype(float) - cost["PARC_unstable_count_mean"].astype(float)
    cost["cost_per_true_candidate_PARC"] = cost["mean_release"].astype(float) / cost["true_candidates_PARC_mean"].replace(
        0, math.nan
    )
    cost["true_candidates_raw_mean"] = cost["K"].astype(float) - cost["raw_unstable_count_mean"].astype(float)
    cost["cost_per_true_candidate_raw"] = cost["K"].astype(float) / cost["true_candidates_raw_mean"].replace(0, math.nan)
    cost["efficiency_lift"] = cost["DFT_efficiency_mean"].astype(float) - cost["raw_DFT_efficiency_mean"].astype(float)
    write_csv(
        out / "table_cost_per_true_candidate.csv",
        cost[
            [
                "proposal_source",
                "K",
                "alpha",
                "mean_release",
                "true_candidates_PARC_mean",
                "cost_per_true_candidate_PARC",
                "true_candidates_raw_mean",
                "cost_per_true_candidate_raw",
                "efficiency_lift",
                "evidence_status",
            ]
        ],
    )

    refusal = primary[primary["release_status"].astype(str).str.contains("refusal|blocked|unsafe", case=False, na=False)].copy()
    if refusal.empty:
        refusal = primary[(primary["K"].astype(float) >= 1000) & (primary["non_empty_seeds"].astype(float) < 18)].copy()
    refusal["refusal_value"] = refusal["raw_unstable_count_mean"].astype(float) - refusal["PARC_unstable_count_mean"].astype(float)
    refusal["interpretation"] = "unsafe requested budget blocked or sharply reduced before downstream follow-up"
    write_csv(out / "table_refusal_value.csv", refusal)

    false_followups = primary[
        [
            "proposal_source",
            "K",
            "alpha",
            "raw_unstable_count_mean",
            "PARC_unstable_count_mean",
            "prevented_unstable_followups_mean",
            "raw_topK_FTR_mean",
            "PARC_FTR_mean",
            "evidence_status",
        ]
    ].copy()
    false_followups["evidence_state"] = "completed_evidence"
    write_csv(out / "table_false_followups_prevented.csv", false_followups)

    if not ctc.empty:
        write_csv(out / "table_ctc_downstream_artifact_utility.csv", ctc)
    if not spacenet.empty:
        write_csv(out / "table_spacenet_downstream_artifact_utility.csv", spacenet)

    write_md(
        out / "FIXED_BUDGET_SCIENTIFIC_UTILITY_CLOSEOUT.md",
        """# Fixed-Budget Scientific Utility Trial

Status: `completed_evidence` for public-label/official-GT downstream utility
diagnostics.  The materials endpoint is not fixed-size reranking improvement;
it is certified stopping/refusal at the requested follow-up budget, measured as
unstable follow-ups prevented, cost per true candidate and refusal value.
""",
    )
    write_manifest(out)


def build_adversarial_release_stress() -> None:
    out = ensure_dir("adversarial_release_stress_trial")
    rows: list[dict] = []

    ctc_rand = read_csv("outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_negative_control.csv")
    for _, r in ctc_rand.iterrows():
        rows.append(
            {
                "stress_family": "score_corruption",
                "domain": r.get("domain", "biomedical_cell_tracking"),
                "source": r.get("proposal_source", ""),
                "K": r.get("M", ""),
                "alpha": r.get("alpha", ""),
                "raw_FTR": r.get("raw_topM_actual_FTR_mean", math.nan),
                "PARC_release": r.get("released_mean", math.nan),
                "PARC_FTR": r.get("actual_FTR_mean", math.nan),
                "mass_ratio": r.get("best_mass_ratio_mean", math.nan),
                "max_observed_e": r.get("max_observed_e_mean", math.nan),
                "refusal_reason": r.get("dominant_empty_reason", ""),
                "outcome": r.get("result_status", ""),
                "evidence_state": "completed_diagnostic",
            }
        )

    mat_rand = read_csv("outputs/milestones/scientific_domain_materials/table_materials_random_score_control.csv")
    for _, r in mat_rand.iterrows():
        rows.append(
            {
                "stress_family": "score_corruption",
                "domain": "materials_discovery",
                "source": r.get("proposal_source", ""),
                "K": r.get("K", ""),
                "alpha": r.get("alpha", ""),
                "raw_FTR": r.get("raw_topK_actual_FTR_mean", math.nan),
                "PARC_release": r.get("mean_release", math.nan),
                "PARC_FTR": r.get("actual_FTR_mean", math.nan),
                "mass_ratio": r.get("best_mass_ratio_mean", math.nan),
                "max_observed_e": r.get("max_observed_e_mean", math.nan),
                "refusal_reason": r.get("dominant_empty_reason", ""),
                "outcome": r.get("control_interpretation", ""),
                "evidence_state": "completed_diagnostic",
            }
        )

    highk = read_csv("outputs/milestones/scientific_domain_materials/table_materials_high_volume_refusal.csv")
    for _, r in highk.iterrows():
        rows.append(
            {
                "stress_family": "high_K_unsafe_request",
                "domain": "materials_discovery",
                "source": r.get("proposal_source", ""),
                "K": r.get("K", ""),
                "alpha": r.get("alpha", ""),
                "raw_FTR": r.get("raw_topK_actual_FTR_mean", math.nan),
                "PARC_release": r.get("mean_release", math.nan),
                "PARC_FTR": r.get("actual_FTR_mean", math.nan),
                "mass_ratio": r.get("best_mass_ratio_mean", math.nan),
                "max_observed_e": r.get("max_observed_e_mean", math.nan),
                "refusal_reason": r.get("dominant_empty_reason", ""),
                "outcome": r.get("paper_status", ""),
                "evidence_state": "completed_evidence_or_sensitivity",
            }
        )

    down = read_csv("outputs/milestones/block_heterogeneity_robustness/table_downsampled_blockmax_stress.csv")
    for _, r in down.iterrows():
        rows.append(
            {
                "stress_family": "block_shift_downsampled_max",
                "domain": r.get("domain", ""),
                "source": r.get("row_id", ""),
                "K": r.get("K", ""),
                "alpha": r.get("alpha", ""),
                "raw_FTR": r.get("raw_topK_FTR_mean", math.nan),
                "PARC_release": r.get("mean_release", math.nan),
                "PARC_FTR": r.get("mean_FTR", math.nan),
                "mass_ratio": r.get("best_mass_ratio_mean", math.nan),
                "max_observed_e": r.get("max_observed_e_mean", math.nan),
                "refusal_reason": r.get("qualitative_decision", ""),
                "outcome": r.get("safety_flag", ""),
                "evidence_state": "completed_stress_diagnostic",
            }
        )

    size = read_csv("outputs/milestones/block_heterogeneity_robustness/table_size_matched_rerun.csv")
    for _, r in size.iterrows():
        rows.append(
            {
                "stress_family": "block_shift_size_matched",
                "domain": r.get("domain", ""),
                "source": r.get("row_id", ""),
                "K": r.get("K", ""),
                "alpha": r.get("alpha", ""),
                "raw_FTR": r.get("raw_topK_FTR_mean", math.nan),
                "PARC_release": r.get("mean_release", math.nan),
                "PARC_FTR": r.get("mean_FTR", math.nan),
                "mass_ratio": r.get("best_mass_ratio_mean", math.nan),
                "max_observed_e": r.get("max_observed_e_mean", math.nan),
                "refusal_reason": r.get("qualitative_decision", ""),
                "outcome": r.get("safety_flag", ""),
                "evidence_state": "completed_stress_diagnostic",
            }
        )

    stress = pd.DataFrame(rows)
    write_csv(out / "table_adversarial_stress_trials.csv", stress)

    boundary = stress.groupby(["stress_family", "domain"], dropna=False).agg(
        n_rows=("stress_family", "size"),
        mean_raw_FTR=("raw_FTR", "mean"),
        mean_PARC_release=("PARC_release", "mean"),
        mean_PARC_FTR=("PARC_FTR", "mean"),
        min_mass_ratio=("mass_ratio", "min"),
        max_mass_ratio=("mass_ratio", "max"),
    )
    boundary = boundary.reset_index()
    boundary["boundary_interpretation"] = boundary.apply(
        lambda r: "refusal_or_power_loss_under_stress"
        if safe_float(r["mean_PARC_release"], 0) < 1 or safe_float(r["max_mass_ratio"], 0) < 1
        else "stress_release_without_mean_over_alpha_signal",
        axis=1,
    )
    write_csv(out / "table_refusal_boundary.csv", boundary)

    write_csv(
        out / "table_stress_claim_scope.csv",
        [
            {
                "claim": "PARC refuses or loses power under adversarial stress instead of silently over-releasing",
                "evidence_state": "completed_diagnostic",
                "scope": "uses completed stress/refusal tables; not a new theorem",
            },
            {
                "claim": "Random score or high-volume rows are main positive evidence",
                "evidence_state": "not_claimed",
                "scope": "controls and refusal-boundary diagnostics only",
            },
        ],
    )
    write_md(
        out / "ADVERSARIAL_RELEASE_STRESS_CLOSEOUT.md",
        """# Adversarial Release Stress Trial

Status: completed diagnostic stress package.  Rows cover destroyed rankings,
high-K unsafe requests, block-size downsampling and size-matched block-max
reruns.  Stress rows are not promoted to primary positive evidence; they
support the refusal-boundary and assumption-boundary story.
""",
    )
    write_manifest(out)


def build_selector_optimality() -> None:
    out = ensure_dir("selector_optimality_diagnostics")
    ilp = read_csv("outputs/milestones/scientific_release_success_map/table_refusal_diagnosis_ilp.csv")
    write_csv(out / "table_greedy_vs_ilp.csv", ilp)

    if not ilp.empty:
        mass = ilp.copy()
        mass["mass_failure"] = mass["evidence_mass_phi"].astype(float) < 1
        mass["finite_resolution_failure"] = mass["max_e"].astype(float) < mass["required_e"].astype(float)
        mass["selector_power_limitation"] = mass["ilp_feasible"].astype(bool) & mass["greedy_result"].astype(str).eq("empty")
        write_csv(out / "table_mass_vs_graph_failure.csv", mass)
        loss = mass[
            [
                "row_id",
                "domain",
                "proposal_source",
                "K",
                "alpha",
                "evidence_mass_phi",
                "conflict_density",
                "greedy_release_size",
                "ilp_feasible",
                "failure_mode",
                "selector_power_limitation",
                "diagnostic_status",
            ]
        ].copy()
        loss["conflict_loss_interpretation"] = loss["selector_power_limitation"].map(
            lambda x: "candidate-level ILP could matter" if bool(x) else "failure diagnosed before selector optimality"
        )
        write_csv(out / "table_conflict_loss.csv", loss)
    else:
        write_csv(out / "table_mass_vs_graph_failure.csv", pd.DataFrame())
        write_csv(out / "table_conflict_loss.csv", pd.DataFrame())

    write_csv(
        out / "table_selector_claim_scope.csv",
        [
            {
                "claim": "SCS-Greedy refusals in diagnosed rows are caused by greedy missing an ILP-feasible set",
                "evidence_state": "not_supported",
                "scope": "current diagnosed refusal rows fail finite-resolution or pre-graph mass checks",
            },
            {
                "claim": "ILP oracle proves no release for every possible candidate graph",
                "evidence_state": "not_claimed",
                "scope": "aggregate rows diagnose pre-graph infeasibility; candidate-level graph optimality is only claimed when candidate-level graph artifacts exist",
            },
        ],
    )
    write_md(
        out / "SELECTOR_OPTIMALITY_DIAGNOSTICS_CLOSEOUT.md",
        """# Selector Optimality Diagnostics

Status: completed diagnostic.  The available refusal rows are diagnosed as
finite-resolution or pre-graph evidence-mass failures, so an ILP/MIS selector
cannot rescue them.  Candidate-level selector optimality is not fabricated for
rows whose full compatibility graph is not in the public package.
""",
    )
    write_manifest(out)


def update_artifact_index() -> None:
    path = ROOT / "outputs" / "artifact_index.csv"
    df = pd.read_csv(path)
    new_rows = pd.DataFrame(
        [
            {
                "milestone": "materials_temporal_replay_completed",
                "path": "outputs/milestones/materials_temporal_replay_completed/",
                "evidence_state": "protocol_only_temporal_replay_missing_snapshots",
                "manifest": "outputs/milestones/materials_temporal_replay_completed/MANIFEST_SHA256.txt",
                "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/materials_temporal_replay_completed",
            },
            {
                "milestone": "fixed_budget_scientific_utility_trial",
                "path": "outputs/milestones/fixed_budget_scientific_utility_trial/",
                "evidence_state": "completed_public_label_utility_evidence",
                "manifest": "outputs/milestones/fixed_budget_scientific_utility_trial/MANIFEST_SHA256.txt",
                "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/fixed_budget_scientific_utility_trial",
            },
            {
                "milestone": "adversarial_release_stress_trial",
                "path": "outputs/milestones/adversarial_release_stress_trial/",
                "evidence_state": "completed_diagnostic_stress_boundary",
                "manifest": "outputs/milestones/adversarial_release_stress_trial/MANIFEST_SHA256.txt",
                "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/adversarial_release_stress_trial",
            },
            {
                "milestone": "selector_optimality_diagnostics",
                "path": "outputs/milestones/selector_optimality_diagnostics/",
                "evidence_state": "completed_diagnostic_selector_boundary",
                "manifest": "outputs/milestones/selector_optimality_diagnostics/MANIFEST_SHA256.txt",
                "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/selector_optimality_diagnostics",
            },
        ]
    )
    df = df[~df["milestone"].isin(new_rows["milestone"])]
    df = pd.concat([df, new_rows], ignore_index=True)
    df.to_csv(path, index=False)


def update_claim_table() -> None:
    path = ROOT / "docs" / "claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Reviewer Route"
    block = """| Materials temporal replay remains blocked unless timestamped t0/t1 public-label snapshots are available. | `outputs/milestones/materials_temporal_replay_completed/table_temporal_primary.csv`; `table_temporal_snapshot_inventory.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | This milestone is protocol-only for temporal validation and must not be promoted to completed quasi-prospective evidence. |
| Fixed-budget scientific utility is quantified as downstream follow-up value. | `outputs/milestones/fixed_budget_scientific_utility_trial/table_decision_curve.csv`; `table_false_followups_prevented.csv`; `table_cost_per_true_candidate.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | Completed public-label utility evidence; the claim is certified stopping/refusal, not fixed-size reranking superiority. |
| Adversarial release stress rows support refusal-boundary diagnostics. | `outputs/milestones/adversarial_release_stress_trial/table_adversarial_stress_trials.csv`; `table_refusal_boundary.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | Stress rows are controls/diagnostics and not primary positive evidence. |
| Selector optimality diagnostics separate evidence-mass failure from greedy selector limitations. | `outputs/milestones/selector_optimality_diagnostics/table_greedy_vs_ilp.csv`; `table_mass_vs_graph_failure.csv`; `table_conflict_loss.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | ILP/MIS claims are limited to available diagnostics; candidate graphs are not fabricated. |
"""
    # Remove a prior inserted copy if present.
    start = text.find("| Materials temporal replay remains blocked")
    if start != -1:
        end = text.find("\n## Reviewer Route", start)
        text = text[:start] + text[end + 1 :]
    text = text.replace(marker, block + "\n" + marker)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    build_materials_temporal_replay()
    build_fixed_budget_scientific_utility()
    build_adversarial_release_stress()
    build_selector_optimality()
    update_artifact_index()
    update_claim_table()
    print("non-A3 main evidence upgrade milestones built")


if __name__ == "__main__":
    main()
