#!/usr/bin/env python3
"""Build Phase65c materials active-audit attempt.

This milestone extends PARC-A beyond the CTC primary result with a materials
t0 audit-emulation attempt.  It tests whether active one-sided verification
policies improve release transitions relative to random audit in WBM/Matbench
Discovery ALIGNN-FF queues.  The result is explicitly not prospective
materials discovery and not DFT evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_materials_threshold_robustness as materials_threshold  # noqa: E402
from run_verified_positive_removal_load_bearing_ablation import (  # noqa: E402
    compute_evalues_from_null,
    empty_reason,
    scs_release_count,
    split_ids,
)


OUT = ROOT / "outputs/milestones/ncs_phase65c_materials_active_audit_attempt"
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
CHGNET_CAL = ROOT / "outputs/milestones/materials_prospective_dft_followup_chgnet_v3/calibration_scores_chgnet_v3.csv"
MACE_CAL = ROOT / "outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/table_mace_full_calibration_scores.csv"

ALPHA = 0.10
SEEDS = list(range(20))
BUDGETS = [300, 500]
BUDGET_FRACTIONS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
POLICIES = [
    "random",
    "raw_score_targeted",
    "parc_m_evidence_targeted",
    "chgnet_mace_support_targeted",
    "mass_gain",
]
SCOPE = (
    "materials_t0_active_audit_emulation;"
    "existing_public_WBM_labels_only;"
    "t1_current_MP_used_only_as_utility_audit;"
    "not_prospective_materials_discovery;"
    "not_DFT_evidence;"
    "not_materials_primary_headline"
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


def rank01(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(np.nan, index=series.index)
    return numeric.rank(method="average", pct=True)


def load_materials_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, str]]:
    frame, meta = materials_threshold.load_frame(args)
    frame = frame.rename(columns={"material_id": "candidate_id"}).copy()
    frame["candidate_id"] = frame["candidate_id"].astype(str)
    chg = pd.read_csv(CHGNET_CAL, usecols=["candidate_id", "frozen_model_score", "score_status"])
    chg = chg.rename(columns={"frozen_model_score": "chgnet_fullcal_acq_score"})
    mace = pd.read_csv(MACE_CAL, usecols=["candidate_id", "mace_energy_per_atom", "mace_score_status"])
    mace["mace_fullcal_acq_score"] = -pd.to_numeric(mace["mace_energy_per_atom"], errors="coerce")
    frame = frame.merge(chg, on="candidate_id", how="left").merge(
        mace[["candidate_id", "mace_fullcal_acq_score", "mace_score_status"]],
        on="candidate_id",
        how="left",
    )
    frame["raw_rank_score"] = pd.to_numeric(frame["alignn_score"], errors="coerce")
    frame["stable_exact"] = frame["stable_exact"].astype(bool)
    return frame.reset_index(drop=True), meta


def load_t1_map() -> dict[int, pd.DataFrame]:
    path = PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"
    t1 = pd.read_csv(path, usecols=["material_id", "K", "stable_exact_t1_current_mp"])
    t1 = t1.rename(columns={"material_id": "candidate_id"})
    t1["candidate_id"] = t1["candidate_id"].astype(str)
    return {int(k): group.drop_duplicates("candidate_id").set_index("candidate_id") for k, group in t1.groupby("K")}


def add_acquisition_scores(cal: pd.DataFrame) -> pd.DataFrame:
    work = cal.copy()
    work["_raw_rank01"] = rank01(work["raw_rank_score"])
    work["_chg_rank01"] = rank01(work["chgnet_fullcal_acq_score"])
    work["_mace_rank01"] = rank01(work["mace_fullcal_acq_score"])
    work["_support_rank01"] = work[["_chg_rank01", "_mace_rank01"]].mean(axis=1, skipna=True)
    work["_parc_m_rank01"] = work[["_raw_rank01", "_chg_rank01", "_mace_rank01"]].mean(axis=1, skipna=True)
    return work


def blockmax_order(cal: pd.DataFrame, score_col: str, block_col: str, max_inspect: int) -> list[int]:
    ranked = cal.reset_index(drop=True).copy()
    ranked["_local_idx"] = np.arange(len(ranked))
    ranked = ranked.sort_values([block_col, score_col, "candidate_id"], ascending=[True, False, True])
    groups = [group["_local_idx"].astype(int).tolist() for _block, group in ranked.groupby(block_col, sort=True)]
    picked: list[int] = []
    while len(picked) < max_inspect and any(groups):
        front: list[int] = []
        next_groups: list[list[int]] = []
        for group in groups:
            if group:
                front.append(group.pop(0))
            if group:
                next_groups.append(group)
        front = sorted(front, key=lambda idx: (-float(cal.iloc[idx][score_col]), str(cal.iloc[idx]["candidate_id"])))
        for idx in front:
            if len(picked) < max_inspect:
                picked.append(int(idx))
        groups = next_groups
    return picked[:max_inspect]


def policy_order(cal: pd.DataFrame, *, policy: str, n_max: int, seed: int) -> list[int]:
    if n_max <= 0:
        return []
    cal = add_acquisition_scores(cal.reset_index(drop=True))
    n_max = min(n_max, len(cal))
    if policy == "random":
        rng = np.random.default_rng(seed + 4409)
        return rng.choice(np.arange(len(cal)), size=n_max, replace=False).astype(int).tolist()
    if policy == "raw_score_targeted":
        return cal.sort_values(["raw_rank_score", "candidate_id"], ascending=[False, True]).index.astype(int).tolist()[:n_max]
    if policy == "parc_m_evidence_targeted":
        ranked = cal.assign(_fallback=cal["raw_rank_score"]).sort_values(
            ["_parc_m_rank01", "_fallback", "candidate_id"], ascending=[False, False, True]
        )
        return ranked.index.astype(int).tolist()[:n_max]
    if policy == "chgnet_mace_support_targeted":
        ranked = cal.assign(_fallback=cal["raw_rank_score"]).sort_values(
            ["_support_rank01", "_fallback", "candidate_id"], ascending=[False, False, True]
        )
        return ranked.index.astype(int).tolist()[:n_max]
    if policy == "mass_gain":
        return blockmax_order(cal, "raw_rank_score", "composition_family_pair", n_max)
    raise ValueError(f"unknown materials audit policy: {policy}")


def t1_metrics(selected: pd.DataFrame, pool: pd.DataFrame, *, k: int, t1_map: dict[int, pd.DataFrame]) -> dict[str, object]:
    table = t1_map.get(k, pd.DataFrame())
    if table.empty:
        return {
            "t1_label_coverage": 0.0,
            "t1_FTR_known": math.nan,
            "t1_FTR_conservative_unknown_false": math.nan,
            "raw_topK_t1_FTR_known": math.nan,
        }
    selected_ids = selected["candidate_id"].astype(str)
    pool_ids = pool["candidate_id"].astype(str)
    sel_labels = selected_ids.map(table["stable_exact_t1_current_mp"])
    pool_labels = pool_ids.map(table["stable_exact_t1_current_mp"])
    known = sel_labels.notna()
    pool_known = pool_labels.notna()
    if len(selected) == 0:
        t1_known = 0.0
        t1_conservative = 0.0
        coverage = 0.0
    else:
        coverage = float(known.mean())
        t1_known = float((~sel_labels[known].astype(bool)).mean()) if known.any() else math.nan
        t1_conservative = float((~sel_labels.fillna(False).astype(bool)).mean())
    raw_known = float((~pool_labels[pool_known].astype(bool)).mean()) if pool_known.any() else math.nan
    return {
        "t1_label_coverage": coverage,
        "t1_FTR_known": t1_known,
        "t1_FTR_conservative_unknown_false": t1_conservative,
        "raw_topK_t1_FTR_known": raw_known,
    }


def run_materials(frame: pd.DataFrame, t1_map: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    block_values = frame["composition_family_pair"].astype(str)
    max_fraction = max(BUDGET_FRACTIONS)
    for seed in SEEDS:
        cal_blocks, test_blocks = split_ids(block_values.tolist(), seed)
        cal = frame.loc[block_values.isin(cal_blocks)].copy().reset_index(drop=True)
        test = frame.loc[block_values.isin(test_blocks)].sort_values("raw_rank_score", ascending=False).reset_index(drop=True)
        orders = {
            policy: policy_order(cal, policy=policy, n_max=int(round(len(cal) * max_fraction)), seed=seed)
            for policy in POLICIES
        }
        for policy in POLICIES:
            for fraction in BUDGET_FRACTIONS:
                n_inspect = int(round(len(cal) * fraction))
                chosen = orders[policy][:n_inspect] if n_inspect > 0 else []
                audit_mask = np.zeros(len(cal), dtype=bool)
                if chosen:
                    audit_mask[np.asarray(chosen, dtype=int)] = True
                observed_positive = audit_mask & cal["stable_exact"].to_numpy(dtype=bool)
                evalues, diag = compute_evalues_from_null(
                    test,
                    cal,
                    block_col="composition_family_pair",
                    score_col="raw_rank_score",
                    cal_block_ids=list(cal_blocks),
                    cal_null_mask=~observed_positive,
                    alpha=ALPHA,
                )
                max_observed_e = float(np.max(evalues)) if len(evalues) else 0.0
                for k in BUDGETS:
                    pool = test.head(k).copy()
                    pool_e = evalues[: len(pool)]
                    released, tau, margin, best_ratio = scs_release_count(pool_e, alpha=ALPHA, budget=k)
                    order = np.argsort(pool_e)[::-1]
                    selected = pool.iloc[order[:released]].copy() if released else pool.iloc[[]].copy()
                    t0_ftr = float((~selected["stable_exact"].astype(bool)).mean()) if released else 0.0
                    raw_t0 = float((~pool["stable_exact"].astype(bool)).mean()) if len(pool) else 0.0
                    t1 = t1_metrics(selected, pool, k=k, t1_map=t1_map)
                    rows.append(
                        {
                            "domain": "materials_discovery",
                            "source": "ALIGNN-FF WBM",
                            "target_row": f"materials_alignn_exact_stable_alpha010_K{k}",
                            "K": k,
                            "alpha": ALPHA,
                            "seed": seed,
                            "audit_policy": policy,
                            "audit_budget_fraction": fraction,
                            "calibration_candidates": int(len(cal)),
                            "audit_candidates_inspected": int(audit_mask.sum()),
                            "verified_positives_found": int(observed_positive.sum()),
                            "verified_positive_yield": (
                                float(observed_positive.sum() / audit_mask.sum()) if audit_mask.sum() else 0.0
                            ),
                            "released": int(released),
                            "t0_FTR": t0_ftr,
                            "safe_t0_release": bool(released > 0 and t0_ftr <= ALPHA),
                            "alpha_violation_t0": bool(released > 0 and t0_ftr > ALPHA),
                            "raw_topK_t0_FTR": raw_t0,
                            "t1_label_coverage": t1["t1_label_coverage"],
                            "t1_FTR_known": t1["t1_FTR_known"],
                            "t1_FTR_conservative_unknown_false": t1["t1_FTR_conservative_unknown_false"],
                            "raw_topK_t1_FTR_known": t1["raw_topK_t1_FTR_known"],
                            "evidence_mass": best_ratio,
                            "max_evalue": max_observed_e,
                            "required_evalue": float(diag["required_e"]) if diag["required_e"] is not None else math.nan,
                            "self_consistency_margin": margin,
                            "tau_k": tau if released else "",
                            "block_coverage": diag["block_coverage"],
                            "empty_reason": empty_reason(released, diag, max_observed_e),
                            "evidence_scope": SCOPE,
                        }
                    )
    return pd.DataFrame(rows)


def summarize(seed_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = ["target_row", "K", "alpha", "audit_policy", "audit_budget_fraction"]
    rows: list[dict[str, object]] = []
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "nonempty_seeds": int((group["released"].astype(int) > 0).sum()),
                "safe_t0_seeds": int(group["safe_t0_release"].astype(bool).sum()),
                "alpha_violation_t0_seeds": int(group["alpha_violation_t0"].astype(bool).sum()),
                "mean_release_size": float(group["released"].astype(float).mean()),
                "mean_t0_FTR": float(group["t0_FTR"].astype(float).mean()),
                "mean_raw_topK_t0_FTR": float(group["raw_topK_t0_FTR"].astype(float).mean()),
                "mean_t1_label_coverage": float(group["t1_label_coverage"].astype(float).mean()),
                "mean_t1_FTR_known": float(group["t1_FTR_known"].astype(float).mean()),
                "mean_t1_FTR_conservative_unknown_false": float(
                    group["t1_FTR_conservative_unknown_false"].astype(float).mean()
                ),
                "mean_raw_topK_t1_FTR_known": float(group["raw_topK_t1_FTR_known"].astype(float).mean()),
                "mean_verified_positives": float(group["verified_positives_found"].astype(float).mean()),
                "mean_verified_positive_yield": float(group["verified_positive_yield"].astype(float).mean()),
                "mean_evidence_mass": float(group["evidence_mass"].astype(float).mean()),
                "mean_max_evalue": float(group["max_evalue"].astype(float).mean()),
                "evidence_scope": SCOPE,
            }
        )
        rows.append(row)
    summary = pd.DataFrame(rows).sort_values(["K", "audit_policy", "audit_budget_fraction"])

    transition_rows: list[dict[str, object]] = []
    for (target_row, policy), group in summary.groupby(["target_row", "audit_policy"], dropna=False):
        ordered = group.sort_values("audit_budget_fraction")
        any_safe = ordered[(ordered["nonempty_seeds"].gt(0)) & (ordered["mean_t0_FTR"].le(ordered["alpha"]))]
        strict = ordered[(ordered["nonempty_seeds"].eq(20)) & (ordered["safe_t0_seeds"].eq(20))]
        transition_rows.append(
            {
                "target_row": target_row,
                "K": int(ordered["K"].iloc[0]),
                "audit_policy": policy,
                "first_any_safe_t0_budget_fraction": (
                    float(any_safe["audit_budget_fraction"].iloc[0]) if len(any_safe) else math.nan
                ),
                "first_strict_20of20_t0_budget_fraction": (
                    float(strict["audit_budget_fraction"].iloc[0]) if len(strict) else math.nan
                ),
                "best_nonempty_seeds": int(ordered["nonempty_seeds"].max()),
                "best_safe_t0_seeds": int(ordered["safe_t0_seeds"].max()),
                "best_total_released": int((ordered["mean_release_size"] * ordered["seeds"]).max()),
                "evidence_scope": SCOPE,
            }
        )
    transition = pd.DataFrame(transition_rows)

    utility = summary[
        [
            "target_row",
            "K",
            "audit_policy",
            "audit_budget_fraction",
            "mean_release_size",
            "mean_t0_FTR",
            "mean_t1_label_coverage",
            "mean_t1_FTR_known",
            "mean_raw_topK_t1_FTR_known",
            "mean_t1_FTR_conservative_unknown_false",
            "evidence_scope",
        ]
    ].copy()

    gate_rows: list[dict[str, object]] = []
    for k in BUDGETS:
        subset = transition[transition["K"].eq(k)]
        random_row = subset[subset["audit_policy"].eq("random")].iloc[0]
        active = subset[~subset["audit_policy"].eq("random")].copy()
        active = active.dropna(subset=["first_any_safe_t0_budget_fraction"])
        best_active = active.sort_values("first_any_safe_t0_budget_fraction").head(1)
        random_budget = random_row["first_any_safe_t0_budget_fraction"]
        best_budget = float(best_active["first_any_safe_t0_budget_fraction"].iloc[0]) if len(best_active) else math.nan
        if pd.notna(best_budget) and best_budget > 0 and pd.notna(random_budget):
            multiplier = float(random_budget / best_budget)
            status = "PASS" if multiplier > 1.0 else "FAIL"
            interpretation = "materials active audit shows a lower t0 release-transition budget than random"
        elif pd.notna(best_budget) and best_budget > 0 and pd.isna(random_budget):
            multiplier = math.inf
            status = "PASS"
            interpretation = "materials active audit transitions while random has no transition in the frozen budget grid"
        else:
            multiplier = math.nan
            status = "FAIL"
            interpretation = "materials active audit does not produce a t0 release transition in this frozen attempt"
        gate_rows.append(
            {
                "gate": f"materials_K{k}_active_audit_beats_random",
                "K": k,
                "best_active_policy": best_active["audit_policy"].iloc[0] if len(best_active) else "",
                "best_active_budget_fraction": best_budget,
                "random_budget_fraction": random_budget,
                "random_budget_multiplier": multiplier,
                "status": status,
                "interpretation": interpretation,
                "evidence_scope": SCOPE,
            }
        )
    gate = pd.DataFrame(gate_rows)
    return summary, transition, utility, gate


def upsert_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase65c_materials_active_audit_attempt",
        "path": rel(OUT) + "/",
        "evidence_state": "completed_materials_active_audit_attempt",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase65c_materials_active_audit_attempt",
    }
    df = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=row.keys())
    df = df[df["milestone"] != row["milestone"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)


def append_once(path: Path, marker: str, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker not in existing:
        path.write_text(existing.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def update_docs(gate: pd.DataFrame) -> None:
    upsert_artifact_index()
    status = "completed_active_better_than_random" if gate["status"].eq("PASS").any() else "completed_no_active_advantage"
    append_once(
        ROOT / "docs/claim_table.md",
        "## Phase65c Materials Active-Audit Attempt",
        f"""## Phase65c Materials Active-Audit Attempt

Status: `{status}`.

Phase65c runs a materials t0 active-audit emulation over frozen ALIGNN-FF WBM
queues. It compares random, raw-score targeted, PARC-M evidence targeted,
CHGNet/MACE support targeted, and mass-gain acquisition. The t1 current-MP
columns are reported only as utility audits and cannot support prospective
materials-discovery or t1 alpha-control claims.
""",
    )
    append_once(
        ROOT / "README.md",
        "NCS Phase65c materials active-audit attempt",
        "- NCS Phase65c materials active-audit attempt: tests active one-sided verification policies on ALIGNN-FF WBM K=300/500 under t0 labels, with t1 utility reported as a scoped audit.",
    )
    append_once(
        ROOT / "REPRODUCIBILITY.md",
        "## NCS Phase65c Materials Active-Audit Attempt",
        """## NCS Phase65c Materials Active-Audit Attempt

Reproduce with:

```bash
make reproduce-ncs-phase65c-materials-active-audit-attempt
python scripts/validate_public_bundle.py outputs/milestones/ncs_phase65c_materials_active_audit_attempt
```
""",
    )
    ledger = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    df = pd.read_csv(ledger)
    claim_id = "MAT-PARCA-ACTIVE-001"
    df = df[df["claim_id"] != claim_id]
    artifact = OUT / "table_materials_active_audit_claim_gate.csv"
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "claim_id": claim_id,
                        "claim_text": "Materials active-audit policies are evaluated as t0 public-label audit-emulation attempts with t1 utility reported only as a scoped audit.",
                        "evidence_type": "materials_active_audit_attempt",
                        "positive_evidence": "partial" if gate["status"].eq("PASS").any() else "no",
                        "scope": "materials_t0_public_label_emulation_not_prospective_discovery",
                        "artifact_path": rel(artifact),
                        "hash": sha256_file(artifact),
                        "validation_command": "make reproduce-ncs-phase65c-materials-active-audit-attempt",
                        "status": "PASS",
                        "overclaim_guardrail": "do_not_claim_prospective_materials_discovery_t1_alpha_control_or_DFT_evidence",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    df.to_csv(ledger, index=False)


def patch_makefile() -> None:
    path = ROOT / "Makefile"
    text = path.read_text(encoding="utf-8")
    target = "reproduce-ncs-phase65c-materials-active-audit-attempt"
    if target not in text:
        text = text.replace(".PHONY: test validate-public-bundle verify-manifest", ".PHONY: test validate-public-bundle verify-manifest " + target)
        text = text.rstrip() + f"\n\n{target}:\n\t$(PYTHON) scripts/build_ncs_phase65c_materials_active_audit_attempt.py\n"
    validation_line = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65c_materials_active_audit_attempt\n"
    if validation_line not in text:
        marker = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics\n"
        if marker in text:
            text = text.replace(marker, marker + validation_line)
    path.write_text(text, encoding="utf-8")


def write_outputs(args: argparse.Namespace) -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    frame, meta = load_materials_frame(args)
    t1_map = load_t1_map()
    seed_rows = run_materials(frame, t1_map)
    summary, transition, utility, gate = summarize(seed_rows)
    seed_rows.to_csv(OUT / "table_materials_active_audit_seed_rows.csv", index=False)
    summary.to_csv(OUT / "table_materials_active_audit_policy_comparison.csv", index=False)
    summary.to_csv(OUT / "table_materials_active_audit_budget_frontier.csv", index=False)
    transition.to_csv(OUT / "table_materials_active_audit_release_transition.csv", index=False)
    utility.to_csv(OUT / "table_materials_active_audit_t1_utility.csv", index=False)
    gate.to_csv(OUT / "table_materials_active_audit_claim_gate.csv", index=False)
    summary.to_csv(OUT / "figure_materials_active_audit_inputs.csv", index=False)
    status = "completed_active_better_than_random" if gate["status"].eq("PASS").any() else "completed_no_active_advantage"
    (OUT / "NCS_PHASE65C_MATERIALS_ACTIVE_AUDIT_ATTEMPT.md").write_text(
        f"""# Phase65c Materials Active-Audit Attempt

Status: `{status}`.

This milestone tests whether active one-sided verification policies improve
materials t0 release transitions relative to random audit. It uses existing
public WBM labels as simulated audit returns. Current-MP t1 labels are reported
only as a utility audit for released candidates with coverage.

Forbidden claims: no prospective materials discovery, no DFT evidence, no t1 alpha certificate, and no materials primary headline from this phase alone.
""",
        encoding="utf-8",
    )
    provenance = {
        "status": "completed",
        "phase": "phase65c",
        "milestone": "ncs_phase65c_materials_active_audit_attempt",
        "source_tables": {
            **{key: value for key, value in meta.items()},
            "phase51_t1_candidate_audit_sha256": sha256_file(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
            "chgnet_fullcal_scores_sha256": sha256_file(CHGNET_CAL),
            "mace_fullcal_scores_sha256": sha256_file(MACE_CAL),
        },
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    update_docs(gate)
    patch_makefile()
    write_root_manifest()
    return {"status": status, "seed_rows": int(len(seed_rows)), "out_dir": rel(OUT)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    args = parser.parse_args()
    print(json.dumps(write_outputs(args), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
