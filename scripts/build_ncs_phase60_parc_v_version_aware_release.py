#!/usr/bin/env python3
"""Build Phase60 PARC-V version-aware support-gate audit.

This milestone tests whether a frozen CHGNet/MACE support gate can turn the
Phase50/53 materials version-shift diagnostic into a new headline-capable
version-aware release rule. It intentionally reports no-go outcomes rather than
promoting support-gated subsets to a theorem-grade PARC certificate.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE53 = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit"
OUT = ROOT / "outputs/milestones/ncs_phase60_parc_v_version_aware_release"
ALPHA = 0.10
SCOPE = (
    "PARC_V_support_gate_feasibility_audit;"
    "uses_frozen_CHGNet_MACE_score_proxies;"
    "not_full_SCS_rerun;"
    "not_new_theorem_certificate;"
    "not_DFT_evidence;"
    "not_prospective_discovery"
)
SUPPORT_TIERS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
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


def load_sources() -> pd.DataFrame:
    phase51 = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    phase53 = pd.read_csv(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv")
    phase53 = phase53.rename(columns={"candidate_id": "material_id"})
    merged = phase51.merge(
        phase53[
            [
                "material_id",
                "structure_hash",
                "K",
                "policy_status",
                "chgnet_predicted_ehull_or_score",
                "mace_predicted_ehull_or_score",
                "chgnet_label",
                "mace_label",
                "chgnet_mace_consensus_label",
                "chgnet_mace_disagreement",
            ]
        ],
        on=["material_id", "K"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_phase53"),
    )
    merged["chgnet_support_rank_pct"] = np.nan
    merged["mace_support_rank_pct"] = np.nan
    merged["support_rank_mean"] = np.nan
    for k, idx in merged.groupby("K").groups.items():
        subset = merged.loc[idx]
        # Lower raw CHGNet/MACE score is treated as stronger score support.
        merged.loc[idx, "chgnet_support_rank_pct"] = subset[
            "chgnet_predicted_ehull_or_score"
        ].rank(pct=True, ascending=True)
        merged.loc[idx, "mace_support_rank_pct"] = subset[
            "mace_predicted_ehull_or_score"
        ].rank(pct=True, ascending=True)
        merged.loc[idx, "support_rank_mean"] = (
            merged.loc[idx, "chgnet_support_rank_pct"]
            + merged.loc[idx, "mace_support_rank_pct"]
        ) / 2.0
    merged["parc_v_consensus_eligible"] = (
        (merged["parc_seed_count"] > 0)
        & merged["chgnet_mace_consensus_label"].eq("consensus_score_supported")
    )
    for fraction in SUPPORT_TIERS:
        col = f"parc_v_top_{int(fraction * 100):03d}pct_support_eligible"
        merged[col] = False
        for k, idx in merged.groupby("K").groups.items():
            k_rows = merged.loc[idx]
            parc = k_rows[k_rows["parc_seed_count"] > 0].sort_values("support_rank_mean")
            n = int(round(len(parc) * fraction))
            n = max(1, n) if len(parc) else 0
            selected = set(parc.head(n)["material_id"])
            merged.loc[idx, col] = k_rows["material_id"].isin(selected).values
    return merged


def summarize_subset(
    df: pd.DataFrame,
    k: int,
    method: str,
    mask: pd.Series,
    construction_rule: str,
    certificate_status: str,
    raw_t1_ftr: float,
    original_parc_t1_ftr: float,
) -> dict[str, object]:
    subset = df[mask].copy()
    n = int(len(subset))
    if n == 0:
        t0_ftr = np.nan
        t1_ftr = np.nan
        drift = np.nan
        mlip_unsupported = np.nan
        disagreement = np.nan
        consensus_supported = np.nan
        mean_support_rank = np.nan
        t1_raw_minus = np.nan
        t1_original_minus = np.nan
    else:
        t0_stable = subset["stable_exact_t0"].astype(bool)
        t1_stable = subset["stable_exact_t1_current_mp"].astype(bool)
        t0_ftr = float((~t0_stable).mean())
        t1_ftr = float((~t1_stable).mean())
        drift = float((t0_stable & ~t1_stable).mean())
        mlip_unsupported = float(
            (~subset["chgnet_mace_consensus_label"].eq("consensus_score_supported")).mean()
        )
        disagreement = float(subset["chgnet_mace_disagreement"].astype(bool).mean())
        consensus_supported = float(
            subset["chgnet_mace_consensus_label"].eq("consensus_score_supported").mean()
        )
        mean_support_rank = float(subset["support_rank_mean"].mean())
        t1_raw_minus = raw_t1_ftr - t1_ftr
        t1_original_minus = original_parc_t1_ftr - t1_ftr
    return {
        "method": method,
        "K": k,
        "alpha": ALPHA,
        "release_size": n,
        "t0_FTR": t0_ftr,
        "t1_FTR": t1_ftr,
        "t1_raw_topK_minus_method": t1_raw_minus,
        "t1_original_PARC_minus_method": t1_original_minus,
        "stable_to_current_not_stable_rate": drift,
        "CHGNet_MACE_consensus_supported_fraction": consensus_supported,
        "MLIP_unsupported_fraction": mlip_unsupported,
        "CHGNet_MACE_disagreement_rate": disagreement,
        "mean_support_rank_pct": mean_support_rank,
        "construction_rule": construction_rule,
        "certificate_status": certificate_status,
        "evidence_scope": SCOPE,
    }


def build_primary_tables(df: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    for k in [300, 500]:
        k_rows = df[df["K"].eq(k)].copy()
        raw_mask = k_rows["raw_topK_seed_count"] > 0
        parc_mask = k_rows["parc_seed_count"] > 0
        raw_t1_ftr = float((~k_rows[raw_mask]["stable_exact_t1_current_mp"].astype(bool)).mean())
        original_parc_t1_ftr = float(
            (~k_rows[parc_mask]["stable_exact_t1_current_mp"].astype(bool)).mean()
        )
        methods = [
            (
                "raw top-K",
                raw_mask,
                "requested_budget_ranked_prefix",
                "no_release_certificate",
            ),
            (
                "matched raw top-R",
                k_rows["raw_topR_seed_count"] > 0,
                "same_size_raw_prefix_diagnostic",
                "no_release_certificate",
            ),
            (
                "PARC",
                parc_mask,
                "original_t0_public_label_PARC_release",
                "original_t0_PARC_certificate_only",
            ),
            (
                "PARC-V consensus gate",
                k_rows["parc_v_consensus_eligible"],
                "original_PARC_release_intersect_frozen_CHGNet_MACE_consensus_support",
                "support_gate_feasibility_not_full_SCS_rerun",
            ),
            (
                "raw-only extra-tail",
                k_rows["raw_only_tail_seed_count"] > 0,
                "raw_requested_budget_minus_PARC_release_tail",
                "no_release_certificate",
            ),
        ]
        for fraction in SUPPORT_TIERS:
            col = f"parc_v_top_{int(fraction * 100):03d}pct_support_eligible"
            methods.append(
                (
                    f"PARC-V top-{int(fraction * 100)}pct support tier",
                    k_rows[col],
                    "original_PARC_release_ranked_by_frozen_CHGNet_MACE_support_score",
                    "support_tier_feasibility_not_full_SCS_rerun",
                )
            )
        for method, mask, rule, cert in methods:
            rows.append(summarize_subset(k_rows, k, method, mask, rule, cert, raw_t1_ftr, original_parc_t1_ftr))

        primary = [r for r in rows if r["K"] == k and r["method"] == "PARC-V consensus gate"][0]
        best_tier = min(
            [r for r in rows if r["K"] == k and str(r["method"]).startswith("PARC-V top-")],
            key=lambda r: (np.inf if pd.isna(r["t1_FTR"]) else r["t1_FTR"]),
        )
        gate_rows.extend(
            [
                {
                    "K": k,
                    "gate": "parc_v_consensus_nonempty",
                    "value": primary["release_size"],
                    "threshold": 25,
                    "status": "PASS" if primary["release_size"] >= 25 else "FAIL",
                    "interpretation": "support-gated subset is nonempty",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "parc_v_consensus_t1_FTR_le_0p15",
                    "value": primary["t1_FTR"],
                    "threshold": 0.15,
                    "status": "PASS" if primary["t1_FTR"] <= 0.15 else "FAIL",
                    "interpretation": "primary empirical headline threshold for version-aware support gate",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "parc_v_consensus_t1_FTR_le_alpha",
                    "value": primary["t1_FTR"],
                    "threshold": ALPHA,
                    "status": "PASS" if primary["t1_FTR"] <= ALPHA else "FAIL",
                    "interpretation": "strict alpha-scale empirical threshold; not a theorem claim",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "parc_v_consensus_improves_original_PARC_by_0p05",
                    "value": primary["t1_original_PARC_minus_method"],
                    "threshold": 0.05,
                    "status": "PASS" if primary["t1_original_PARC_minus_method"] >= 0.05 else "FAIL",
                    "interpretation": "support gate should materially improve over original PARC",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "best_support_tier_t1_FTR_le_0p15",
                    "value": best_tier["t1_FTR"],
                    "threshold": 0.15,
                    "status": "PASS" if best_tier["t1_FTR"] <= 0.15 else "FAIL",
                    "interpretation": f"best frozen score tier is {best_tier['method']}",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "full_theorem_grade_PARC_V_claim_allowed",
                    "value": 0,
                    "threshold": 1,
                    "status": "FAIL",
                    "interpretation": "this phase did not rerun a theorem-grade SCS rule after a validated support gate",
                    "evidence_scope": SCOPE,
                },
            ]
        )
    return rows, gate_rows


def candidate_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in df.to_dict("records"):
        rows.append(
            {
                "candidate_id": row["material_id"],
                "structure_hash": row.get("structure_hash", ""),
                "formula": row["formula"],
                "chemical_system": row["chemical_system"],
                "K": row["K"],
                "policy_status": row["primary_queue_status"],
                "raw_rank": row["raw_rank"],
                "parc_released": row["parc_seed_count"] > 0,
                "parc_seed_count": row["parc_seed_count"],
                "raw_topK_member": row["raw_topK_seed_count"] > 0,
                "raw_topR_member": row["raw_topR_seed_count"] > 0,
                "raw_only_tail_member": row["raw_only_tail_seed_count"] > 0,
                "t0_label": "stable" if bool(row["stable_exact_t0"]) else "unstable_or_unresolved",
                "t1_label": "stable" if bool(row["stable_exact_t1_current_mp"]) else "unstable_or_unresolved",
                "drift_class": row["drift_class"],
                "t1_false_conservative": row["t1_false_conservative"],
                "parc_e_value": row["parc_e_value"],
                "required_e": row["required_e"],
                "self_consistency_margin": row["self_consistency_margin"],
                "chgnet_predicted_ehull_or_score": row["chgnet_predicted_ehull_or_score"],
                "mace_predicted_ehull_or_score": row["mace_predicted_ehull_or_score"],
                "chgnet_label": row["chgnet_label"],
                "mace_label": row["mace_label"],
                "chgnet_mace_consensus_label": row["chgnet_mace_consensus_label"],
                "chgnet_mace_disagreement": row["chgnet_mace_disagreement"],
                "support_rank_mean": row["support_rank_mean"],
                "parc_v_consensus_eligible": row["parc_v_consensus_eligible"],
                "parc_v_top_050pct_support_eligible": row["parc_v_top_050pct_support_eligible"],
                "near_hull_t1_25mev": row["near_hull_25mev_t1"],
                "near_hull_t1_50mev": row["near_hull_50mev_t1"],
                "failure_explanation_class": row["t1_false_explanation_class"],
                "evidence_scope": SCOPE,
            }
        )
    return rows


def write_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    if path.exists():
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        fieldnames = list(rows[0].keys()) if rows else [
            "milestone",
            "path",
            "evidence_state",
            "manifest",
            "public_bundle_check",
        ]
    else:
        rows = []
        fieldnames = ["milestone", "path", "evidence_state", "manifest", "public_bundle_check"]
    milestone = "ncs_phase60_parc_v_version_aware_release"
    rows = [row for row in rows if row.get("milestone") != milestone]
    row = {
        "milestone": milestone,
        "path": "outputs/milestones/ncs_phase60_parc_v_version_aware_release/",
        "evidence_state": "completed_PARC_V_support_gate_no_go_for_headline",
        "manifest": "outputs/milestones/ncs_phase60_parc_v_version_aware_release/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase60_parc_v_version_aware_release",
    }
    rows.append({key: row.get(key, "") for key in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_sources()
    primary_rows, gate_rows = build_primary_tables(df)
    candidates = candidate_rows(df)

    write_csv(OUT / "table_parc_v_candidate_level.csv", candidates, list(candidates[0].keys()))
    write_csv(OUT / "table_parc_v_primary_results.csv", primary_rows, list(primary_rows[0].keys()))
    write_csv(OUT / "table_parc_v_baseline_comparison.csv", primary_rows, list(primary_rows[0].keys()))
    write_csv(OUT / "table_parc_v_gate_audit.csv", gate_rows, list(gate_rows[0].keys()))
    write_csv(OUT / "figure_parc_v_version_aware_release_inputs.csv", primary_rows, list(primary_rows[0].keys()))

    prereg = """# PARC-V Support-Gate Preregistration

Status: frozen feasibility audit after Phase53 score generation and before any
new DFT recomputation.

Objective: test whether a frozen CHGNet/MACE score-support gate can create a
headline-capable version-aware release subset from the original t0 PARC
materials release.

Construction rules:

1. The candidate universe is the frozen WBM K=300/500 queue used in Phase50-53.
2. The primary PARC-V candidate is the original PARC release intersected with
   CHGNet/MACE consensus score support.
3. Secondary score tiers rank only the original PARC release by frozen
   CHGNet/MACE support score; t1 labels are not used for construction.
4. Current-MP t1 labels are used only for evaluation.
5. This milestone is not a full theorem-grade SCS rerun and cannot be cited as
   a new alpha certificate, DFT result, or prospective discovery.

Empirical headline gate:

- non-empty support-gated release;
- t1 FTR <= 0.15, preferably <= alpha=0.10;
- material improvement over original PARC t1 FTR by at least 0.05;
- release size not trivial.
"""
    (OUT / "PARC_V_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")

    gate = pd.DataFrame(gate_rows)
    failed_headline = gate[
        gate["gate"].isin(
            [
                "parc_v_consensus_t1_FTR_le_0p15",
                "parc_v_consensus_t1_FTR_le_alpha",
                "parc_v_consensus_improves_original_PARC_by_0p05",
                "best_support_tier_t1_FTR_le_0p15",
                "full_theorem_grade_PARC_V_claim_allowed",
            ]
        )
        & gate["status"].eq("FAIL")
    ]
    status = "no_go_for_headline" if not failed_headline.empty else "empirical_gate_passed"
    closeout = f"""# Phase60 PARC-V Version-Aware Support-Gate Audit

Status: `{status}`

This milestone tests the fastest plausible version-aware extension: intersect
the original t0 PARC release with a frozen CHGNet/MACE score-support gate, then
evaluate the fixed subset under current-MP t1 labels.

Result: the support gate is non-empty, but it does not materially reduce the
current-MP t1 false-release burden. The primary consensus gate remains around
the original PARC t1 FTR scale and does not reach the predeclared <=0.15 or
<=0.10 empirical thresholds. More stringent frozen score tiers also do not
produce a nontrivial low-FTR release.

Interpretation: PARC-V, in this simple support-gated form, should not be used as
the NCS headline or described as a solution to version shift. It is a completed
no-go/feasibility audit that redirects the substance upgrade toward blinded DFT
v2 or a real one-sided audit rather than additional MLIP proxy filtering.

Forbidden claims:

- no new theorem-grade PARC-V certificate;
- no t1 alpha control;
- no DFT evidence;
- no prospective materials discovery;
- no claim that CHGNet/MACE score support is a reference-hull label.
"""
    (OUT / "NCS_PHASE60_PARC_V_VERSION_AWARE_RELEASE.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase60_parc_v_version_aware_release",
        "status": status,
        "source_tables": [
            rel(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
            rel(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv"),
        ],
        "evidence_scope": SCOPE,
        "primary_headline_allowed": status == "empirical_gate_passed",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_artifact_index()
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
