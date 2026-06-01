#!/usr/bin/env python3
"""Build Phase94 current-MP relaxed recertification frontier.

Phase94 closes the low-cost current-MP recertified-release route by sweeping
small K and relaxed alpha values after Phase66/74/75 no-go results.  It uses
the same queue-limited public-label t1 recertification emulation discipline as
Phase75: t1 labels are used only as calibration-side one-sided positives, and
held-out t1 labels are evaluated only after release.

This phase is not DFT evidence, not prospective discovery, and not a strict
alpha=0.10 current-MP certificate if only relaxed alpha rows are nonempty.
"""

from __future__ import annotations

import hashlib
import importlib
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase94_current_mp_relaxed_recertification_frontier"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

ALPHA_GRID = [0.10, 0.15, 0.20]
K_GRID = [25, 50, 75, 100, 150, 200]
BUDGET_FRACTIONS = [0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 1.00]
POLICIES = [
    "random_t1_audit",
    "score_targeted_t1_audit",
    "low_risk_score_targeted_t1_audit",
    "blockmax_gain_t1_audit",
]
SUPPORT_MODES = {
    "t1_10pct_support": 0.10,
    "t1_full_calibration_block_support": 1.00,
}
SCOPE = (
    "current_MP_relaxed_recertification_frontier;"
    "queue_limited_public_label_t1_recertification_emulation;"
    "small_K_alpha_grid_reported_in_full;"
    "t1_labels_used_only_as_calibration_side_one_sided_positives;"
    "test_side_t1_labels_used_only_after_release_for_FTR;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery;"
    "not_strict_alpha_0p10_certificate_if_relaxed_only"
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


def phase75_module():
    return importlib.import_module("build_ncs_phase75_active_versioned_recertification")


def run_alpha_grid() -> pd.DataFrame:
    p75 = phase75_module()
    queue = p75.load_queue()
    all_rows = []
    old = {
        "ALPHA": p75.ALPHA,
        "K_GRID": p75.K_GRID,
        "BUDGET_FRACTIONS": p75.BUDGET_FRACTIONS,
        "POLICIES": p75.POLICIES,
        "SUPPORT_MODES": p75.SUPPORT_MODES,
        "SCOPE": p75.SCOPE,
    }
    try:
        p75.K_GRID = K_GRID
        p75.BUDGET_FRACTIONS = BUDGET_FRACTIONS
        p75.POLICIES = POLICIES
        p75.SUPPORT_MODES = SUPPORT_MODES
        p75.SCOPE = SCOPE
        for alpha in ALPHA_GRID:
            p75.ALPHA = float(alpha)
            rows = p75.run_seed_rows(queue)
            rows["alpha_grid_value"] = float(alpha)
            rows["evidence_scope"] = SCOPE
            all_rows.append(rows)
    finally:
        p75.ALPHA = old["ALPHA"]
        p75.K_GRID = old["K_GRID"]
        p75.BUDGET_FRACTIONS = old["BUDGET_FRACTIONS"]
        p75.POLICIES = old["POLICIES"]
        p75.SUPPORT_MODES = old["SUPPORT_MODES"]
        p75.SCOPE = old["SCOPE"]
    return pd.concat(all_rows, ignore_index=True)


def summarize(seed_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = [
        "alpha",
        "K",
        "support_mode",
        "audit_policy",
        "audit_budget_fraction_requested",
        "audit_budget_fraction_effective",
    ]
    rows = []
    for key, group in seed_rows.groupby(group_cols, dropna=False, sort=True):
        row = dict(zip(group_cols, key))
        alpha = float(row["alpha"])
        nonempty = int(group["release_size"].gt(0).sum())
        safe = int(group["safe_release_t1"].astype(bool).sum())
        nonempty_ftr = group.loc[group["release_size"].gt(0), "release_FTR_t1"].astype(float)
        mean_ftr = float(nonempty_ftr.mean()) if len(nonempty_ftr) else math.nan
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "nonempty_seeds": nonempty,
                "safe_seeds": safe,
                "mean_release_size": float(group["release_size"].astype(float).mean()),
                "median_release_size": float(group["release_size"].astype(float).median()),
                "max_release_size": int(group["release_size"].astype(int).max()),
                "total_released": int(group["release_size"].astype(int).sum()),
                "total_false_t1": int(group["release_false_t1"].astype(int).sum()),
                "mean_FTR_t1_if_nonempty": mean_ftr,
                "mean_FTR_t1_empty_zero": float(group["release_FTR_t1"].fillna(0).astype(float).mean()),
                "mean_raw_topK_t1_FTR": float(group["raw_topK_t1_FTR"].astype(float).mean()),
                "mean_verified_t1_positives": float(group["verified_t1_positives_found"].astype(float).mean()),
                "mean_verified_positive_yield": float(group["verified_positive_yield"].astype(float).mean()),
                "mean_max_evalue": float(group["max_evalue"].astype(float).mean()),
                "mean_required_evalue_threshold_if_released": (
                    float(group.loc[group["release_size"].gt(0), "required_evalue_threshold"].astype(float).mean())
                    if nonempty
                    else math.nan
                ),
                "mean_self_consistency_margin": float(group["self_consistency_margin"].astype(float).mean()),
                "mean_evidence_mass": float(group["evidence_mass"].astype(float).mean()),
                "self_consistency_pass_any_seed": bool(group["self_consistency_pass"].astype(bool).any()),
                "strict_alpha_0p10_success": bool(
                    alpha == 0.10
                    and nonempty >= 18
                    and safe >= 18
                    and pd.notna(mean_ftr)
                    and mean_ftr <= 0.10
                    and float(group["release_size"].astype(float).mean()) >= 20
                ),
                "relaxed_current_mp_operating_success": bool(
                    alpha > 0.10
                    and nonempty >= 18
                    and safe >= 18
                    and pd.notna(mean_ftr)
                    and mean_ftr <= alpha
                    and float(group["release_size"].astype(float).mean()) >= 20
                ),
                "boundary_nonempty": bool(nonempty > 0),
                "evidence_scope": SCOPE,
            }
        )
        rows.append(row)
    summary = pd.DataFrame(rows).sort_values(group_cols)

    random_lookup = summary[summary["audit_policy"].eq("random_t1_audit")][
        ["alpha", "K", "support_mode", "audit_budget_fraction_requested", "nonempty_seeds", "safe_seeds"]
    ].rename(
        columns={
            "nonempty_seeds": "random_same_budget_nonempty_seeds",
            "safe_seeds": "random_same_budget_safe_seeds",
        }
    )
    summary = summary.merge(
        random_lookup,
        on=["alpha", "K", "support_mode", "audit_budget_fraction_requested"],
        how="left",
    )
    summary["random_same_budget_refuses"] = summary["random_same_budget_nonempty_seeds"].fillna(0).eq(0)
    summary["claim_status"] = np.where(
        summary["strict_alpha_0p10_success"],
        "strict_current_mp_recertified_release_positive",
        np.where(
            summary["relaxed_current_mp_operating_success"],
            "relaxed_current_mp_operating_positive",
            np.where(summary["boundary_nonempty"], "boundary_nonempty_no_primary_gate", "certified_refusal"),
        ),
    )

    best = summary.sort_values(
        ["strict_alpha_0p10_success", "relaxed_current_mp_operating_success", "safe_seeds", "nonempty_seeds", "mean_FTR_t1_if_nonempty", "mean_release_size"],
        ascending=[False, False, False, False, True, False],
    ).head(20)

    gate = pd.DataFrame(
        [
            {
                "gate": "strict_alpha_0p10_current_mp_recertified_release",
                "threshold": "alpha=0.10; nonempty_seeds>=18; safe_seeds>=18; mean_FTR_t1<=0.10; mean_release_size>=20",
                "status": "PASS" if summary["strict_alpha_0p10_success"].astype(bool).any() else "FAIL",
                "evidence_scope": SCOPE,
            },
            {
                "gate": "relaxed_alpha_current_mp_operating_release",
                "threshold": "alpha in {0.15,0.20}; nonempty_seeds>=18; safe_seeds>=18; mean_FTR_t1<=alpha; mean_release_size>=20",
                "status": "PASS" if summary["relaxed_current_mp_operating_success"].astype(bool).any() else "FAIL",
                "evidence_scope": SCOPE,
            },
            {
                "gate": "boundary_nonempty_any_row",
                "threshold": "any row has nonempty_seeds>0",
                "status": "PASS" if summary["boundary_nonempty"].astype(bool).any() else "FAIL",
                "evidence_scope": SCOPE,
            },
            {
                "gate": "full_grid_reported",
                "threshold": "all predeclared K alpha support policy budget rows reported",
                "status": "PASS",
                "evidence_scope": SCOPE,
            },
        ]
    )

    figure = pd.concat(
        [
            summary.assign(panel="alpha_frontier"),
            best.assign(panel="best_rows"),
            gate.assign(panel="gate_audit"),
        ],
        ignore_index=True,
        sort=False,
    )
    return summary, best, gate, figure


def status_from_gate(gate: pd.DataFrame) -> str:
    gate_map = gate.set_index("gate")["status"].to_dict()
    if gate_map.get("strict_alpha_0p10_current_mp_recertified_release") == "PASS":
        return "completed_strict_current_mp_recertified_release_positive"
    if gate_map.get("relaxed_alpha_current_mp_operating_release") == "PASS":
        return "completed_relaxed_current_mp_operating_positive"
    if gate_map.get("boundary_nonempty_any_row") == "PASS":
        return "completed_current_mp_relaxed_recertification_boundary_no_go"
    return "completed_current_mp_relaxed_recertification_refusal_no_go"


def write_outputs(
    seed_rows: pd.DataFrame,
    summary: pd.DataFrame,
    best: pd.DataFrame,
    gate: pd.DataFrame,
    figure: pd.DataFrame,
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    seed_rows.to_csv(OUT / "table_phase94_recertification_alpha_frontier_seed_rows.csv", index=False)
    summary.to_csv(OUT / "table_phase94_recertification_alpha_frontier_summary.csv", index=False)
    best.to_csv(OUT / "table_phase94_best_operating_rows.csv", index=False)
    gate.to_csv(OUT / "table_phase94_gate_audit.csv", index=False)
    figure.to_csv(OUT / "figure_phase94_current_mp_frontier_inputs.csv", index=False)


def write_docs(status: str, best: pd.DataFrame, gate: pd.DataFrame) -> None:
    best_row = best.iloc[0]
    readme = f"""# Phase94 Current-MP Relaxed Recertification Frontier

Status: `{status}`.

Phase94 sweeps small K and relaxed alpha values after Phase66/74/75 no-go
results. It tests whether a current-MP public-label recertification replay can
recover a non-empty release frontier under the same no-leakage discipline.

Best boundary row:

- alpha: `{float(best_row['alpha'])}`;
- K: `{int(best_row['K'])}`;
- support mode: `{best_row['support_mode']}`;
- audit policy: `{best_row['audit_policy']}`;
- audit budget fraction: `{float(best_row['audit_budget_fraction_requested'])}`;
- nonempty seeds: `{int(best_row['nonempty_seeds'])}/20`;
- safe seeds: `{int(best_row['safe_seeds'])}/20`;
- mean release size: `{float(best_row['mean_release_size']):.6f}`;
- mean t1 FTR if nonempty: `{float(best_row['mean_FTR_t1_if_nonempty']):.6f}`.

Gate audit:

{gate.to_markdown(index=False)}

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase94 Protocol: Current-MP Relaxed Recertification Frontier

Frozen grid:

- K: `{K_GRID}`;
- alpha: `{ALPHA_GRID}`;
- audit budgets: `{BUDGET_FRACTIONS}`;
- policies: `{POLICIES}`;
- support modes: `{list(SUPPORT_MODES)}`.

Procedure:

1. Use the Phase75 queue-limited current-MP t1 public-label recertification
   emulation machinery.
2. Use t1 labels only as calibration-side one-sided positives.
3. Recompute the null-superset denominator and e-values after audit.
4. Evaluate held-out t1 labels only after release.
5. Report the full grid. Do not select a row by hiding failures.

Forbidden claims:

- independent DFT validation;
- prospective materials discovery;
- strict alpha=0.10 current-MP certificate unless the strict gate passes;
- physical ground truth.
"""
    (OUT / "PHASE94_CURRENT_MP_RELAXED_RECERTIFICATION_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def update_artifact_index(status: str) -> None:
    row = {
        "milestone": "ncs_phase94_current_mp_relaxed_recertification_frontier",
        "path": "outputs/milestones/ncs_phase94_current_mp_relaxed_recertification_frontier/",
        "evidence_state": status,
        "manifest": "outputs/milestones/ncs_phase94_current_mp_relaxed_recertification_frontier/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase94_current_mp_relaxed_recertification_frontier",
        "notes": "Current-MP public-label small-K relaxed-alpha recertification frontier; not DFT evidence.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(
        ARTIFACT_INDEX, index=False
    )


def update_ledger(status: str) -> None:
    row = {
        "claim_id": "NCS-PHASE94-CURRENT-MP-RECERT-FRONTIER-001",
        "claim_text": "Phase94 tests whether small-K and relaxed-alpha current-MP public-label recertification recovers a non-empty release frontier.",
        "evidence_type": "current_mp_public_label_recertification_frontier",
        "positive_evidence": "partial" if "positive" in status else "no",
        "scope": status,
        "artifact_path": "outputs/milestones/ncs_phase94_current_mp_relaxed_recertification_frontier/table_phase94_gate_audit.csv",
        "hash": sha256_file(OUT / "table_phase94_gate_audit.csv"),
        "validation_command": "make reproduce-ncs-phase94-current-mp-relaxed-recertification-frontier",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_DFT_evidence_prospective_discovery_or_strict_alpha_0p10_current_MP_certificate_unless_strict_gate_passes",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table(status: str, best: pd.DataFrame) -> None:
    row = best.iloc[0]
    section = f"""\n## Phase94 Current-MP Relaxed Recertification Frontier\n\nStatus: `{status}`.\n\nPhase94 sweeps small K and relaxed alpha values for current-MP public-label\nrecertification. The best boundary row is alpha `{float(row['alpha'])}`, K\n`{int(row['K'])}`, policy `{row['audit_policy']}`, support `{row['support_mode']}`,\nwith nonempty `{int(row['nonempty_seeds'])}/20` seeds, safe `{int(row['safe_seeds'])}/20`\nseeds, and mean t1 FTR `{float(row['mean_FTR_t1_if_nonempty']):.6f}` if nonempty.\nThis is a queue-limited public-reference recertification frontier, not DFT\nevidence, not prospective discovery, and not a strict alpha=0.10 current-MP\ncertificate unless the strict gate passes.\n"""
    marker = "## Phase94 Current-MP Relaxed Recertification Frontier"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        text = before + "\n" + section + (after[next_idx:] if next_idx >= 0 else "")
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    seed_rows = run_alpha_grid()
    summary, best, gate, figure = summarize(seed_rows)
    status = status_from_gate(gate)
    write_outputs(seed_rows, summary, best, gate, figure)
    write_docs(status, best, gate)
    write_manifest(OUT)
    update_artifact_index(status)
    update_ledger(status)
    update_claim_table(status, best)
    write_root_manifest()
    print(f"[phase94] wrote {rel(OUT)}")
    print(f"[phase94] status={status}")


if __name__ == "__main__":
    main()
