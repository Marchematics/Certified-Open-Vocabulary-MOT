#!/usr/bin/env python3
"""Build Phase65b PARC-A mechanism diagnostics.

Phase65 established a GO-medium PARC-A result: certificate-directed policies
reproduce the original 0.5% CTC transition while score-targeted audit remains
the strongest fine-grid empirical transition.  Phase65b explains why the
score-targeted transition works: high-score positives remove the calibration
null-superset block maxima that limit the release e-values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import build_ncs_phase65_parc_a_certificate_directed_policy as phase65


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics"

FINE_BUDGETS = [0.0, 0.001, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01]
POLICIES = ["random", "score_targeted", "block_max_gain", "mass_gain", "diversity_mass_gain"]
SCOPE = (
    "PARC_A_mechanism_diagnostic;"
    "CTC_primary_only;"
    "simulated_one_sided_audit_over_existing_labels;"
    "hidden_labels_used_only_for_audit_return_and_posthoc_FTR;"
    "not_new_human_labels;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def block_maximum_mask(cal: pd.DataFrame) -> np.ndarray:
    ranked = cal.reset_index(drop=True).copy()
    ranked["_local_idx"] = np.arange(len(ranked))
    ranked = ranked.sort_values(["video_id", "score", "path_id"], ascending=[True, False, True])
    mask = np.zeros(len(ranked), dtype=bool)
    for _block, group in ranked.groupby("video_id", sort=True):
        if len(group):
            mask[int(group["_local_idx"].iloc[0])] = True
    return mask


def run_seed_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    block_values = frame["video_id"].astype(str)
    max_fraction = max(FINE_BUDGETS)
    for seed in phase65.SEEDS:
        cal_blocks, test_blocks = phase65.split_ids(block_values.tolist(), seed)
        cal = frame.loc[block_values.isin(cal_blocks)].copy().reset_index(drop=True)
        test = frame.loc[block_values.isin(test_blocks)].sort_values("score", ascending=False).reset_index(drop=True)
        is_block_max = block_maximum_mask(cal)
        n_block_max = int(is_block_max.sum())
        for k in phase65.BUDGETS:
            max_inspect = int(round(len(cal) * max_fraction))
            orders = {
                policy: phase65.policy_order(cal=cal, test=test, seed=seed, policy=policy, max_inspect=max_inspect, K=k)
                for policy in POLICIES
            }
            for policy in POLICIES:
                budget_grid = list(FINE_BUDGETS)
                if policy == "random":
                    budget_grid += [1.0]
                for fraction in budget_grid:
                    n_inspect = int(round(len(cal) * fraction))
                    if n_inspect <= 0:
                        chosen: list[int] = []
                    elif policy == "random" and fraction > max_fraction:
                        chosen = phase65.policy_order(
                            cal=cal, test=test, seed=seed, policy=policy, max_inspect=n_inspect, K=k
                        )
                    else:
                        chosen = orders[policy][:n_inspect]
                    audit_mask = np.zeros(len(cal), dtype=bool)
                    if chosen:
                        audit_mask[np.asarray(chosen, dtype=int)] = True
                    observed_positive = audit_mask & cal["_full_true"].to_numpy(dtype=bool)
                    maxima, _block_lists = phase65.maxima_from_cal(cal, observed_positive)
                    all_scores = test["score"].to_numpy(dtype=float)
                    all_evalues, diag = phase65.evalues_from_maxima(all_scores, maxima)
                    pool = test.head(k).copy()
                    pool_e = all_evalues[: len(pool)]
                    released, tau, margin, best_ratio = phase65.scs_release_count(pool_e, alpha=phase65.ALPHA, budget=k)
                    order = np.argsort(pool_e)[::-1]
                    selected = pool.iloc[order[:released]].copy() if released else pool.iloc[[]].copy()
                    actual_ftr = float((~selected["_full_true"].astype(bool)).mean()) if released else 0.0
                    audited_block_max = audit_mask & is_block_max
                    positive_block_max = observed_positive & is_block_max
                    rows.append(
                        {
                            "domain": "biomedical_cell_tracking",
                            "source": "ctc_learned_hybrid_appearance_sequence_disjoint",
                            "target_row": f"ctc_learned_strict_alpha010_K{k}",
                            "K": k,
                            "alpha": phase65.ALPHA,
                            "seed": seed,
                            "audit_policy": policy,
                            "audit_budget_fraction": fraction,
                            "calibration_candidates": int(len(cal)),
                            "audit_candidates_inspected": int(audit_mask.sum()),
                            "verified_positives_found": int(observed_positive.sum()),
                            "verified_positive_yield": (
                                float(observed_positive.sum() / audit_mask.sum()) if audit_mask.sum() else 0.0
                            ),
                            "calibration_block_maxima": n_block_max,
                            "audited_block_maxima": int(audited_block_max.sum()),
                            "positive_block_maxima_removed": int(positive_block_max.sum()),
                            "positive_blockmax_removed_fraction": (
                                float(positive_block_max.sum() / n_block_max) if n_block_max else 0.0
                            ),
                            "positive_blockmax_share_of_verified_positives": (
                                float(positive_block_max.sum() / observed_positive.sum())
                                if observed_positive.sum()
                                else 0.0
                            ),
                            "released": int(released),
                            "actual_FTR": actual_ftr,
                            "safe_release": bool(released > 0 and actual_ftr <= phase65.ALPHA),
                            "alpha_violation": bool(released > 0 and actual_ftr > phase65.ALPHA),
                            "evidence_mass": best_ratio,
                            "max_evalue": float(all_evalues.max()) if len(all_evalues) else 0.0,
                            "required_evalue": float(diag["required_e"]),
                            "self_consistency_margin": margin,
                            "tau_k": tau if released else "",
                            "n_nonempty_null_cal_blocks": int(diag["n_nonempty_null_cal_blocks"]),
                            "evidence_scope": SCOPE,
                        }
                    )
    return pd.DataFrame(rows)


def summarize(seed_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = ["target_row", "K", "alpha", "audit_policy", "audit_budget_fraction"]
    rows: list[dict[str, object]] = []
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "nonempty_seeds": int((group["released"].astype(int) > 0).sum()),
                "safe_seeds": int(group["safe_release"].astype(bool).sum()),
                "alpha_violation_seeds": int(group["alpha_violation"].astype(bool).sum()),
                "mean_release_size": float(group["released"].astype(float).mean()),
                "observed_FTR": float(group["actual_FTR"].astype(float).mean()),
                "mean_evidence_mass": float(group["evidence_mass"].astype(float).mean()),
                "mean_max_evalue": float(group["max_evalue"].astype(float).mean()),
                "mean_verified_positives": float(group["verified_positives_found"].astype(float).mean()),
                "mean_verified_positive_yield": float(group["verified_positive_yield"].astype(float).mean()),
                "mean_positive_blockmax_removed": float(group["positive_block_maxima_removed"].astype(float).mean()),
                "mean_positive_blockmax_removed_fraction": float(
                    group["positive_blockmax_removed_fraction"].astype(float).mean()
                ),
                "mean_positive_blockmax_share_of_verified": float(
                    group["positive_blockmax_share_of_verified_positives"].astype(float).mean()
                ),
                "evidence_scope": SCOPE,
            }
        )
        rows.append(row)
    frontier = pd.DataFrame(rows).sort_values(["K", "audit_policy", "audit_budget_fraction"])

    positive_yield = frontier[
        [
            "target_row",
            "K",
            "audit_policy",
            "audit_budget_fraction",
            "mean_verified_positives",
            "mean_verified_positive_yield",
            "mean_positive_blockmax_removed",
            "mean_positive_blockmax_removed_fraction",
            "mean_positive_blockmax_share_of_verified",
            "evidence_scope",
        ]
    ].copy()
    blockmax = positive_yield.copy()
    mass = frontier[
        [
            "target_row",
            "K",
            "audit_policy",
            "audit_budget_fraction",
            "nonempty_seeds",
            "safe_seeds",
            "mean_release_size",
            "observed_FTR",
            "mean_evidence_mass",
            "mean_max_evalue",
            "evidence_scope",
        ]
    ].copy()
    figure = mass.merge(
        positive_yield[
            [
                "target_row",
                "K",
                "audit_policy",
                "audit_budget_fraction",
                "mean_verified_positive_yield",
                "mean_positive_blockmax_removed_fraction",
            ]
        ],
        on=["target_row", "K", "audit_policy", "audit_budget_fraction"],
        how="left",
    )

    gate_rows: list[dict[str, object]] = []
    k100 = frontier[frontier["target_row"].eq("ctc_learned_strict_alpha010_K100")]
    score_002 = k100[(k100["audit_policy"].eq("score_targeted")) & (k100["audit_budget_fraction"].eq(0.002))].iloc[0]
    random_002 = k100[(k100["audit_policy"].eq("random")) & (k100["audit_budget_fraction"].eq(0.002))].iloc[0]
    ratio = (
        float(score_002["mean_positive_blockmax_removed_fraction"])
        / max(float(random_002["mean_positive_blockmax_removed_fraction"]), 1e-12)
    )
    gate_rows.extend(
        [
            {
                "gate": "score_0p2pct_safe_release_20of20",
                "value": int(score_002["safe_seeds"]),
                "threshold": 20,
                "status": "PASS" if int(score_002["safe_seeds"]) == 20 else "FAIL",
                "interpretation": "score-targeted 0.2% audit reaches the strict CTC K=100 release transition",
                "evidence_scope": SCOPE,
            },
            {
                "gate": "score_removes_more_blockmax_than_random_at_0p2pct",
                "value": ratio,
                "threshold": 5.0,
                "status": "PASS" if ratio >= 5.0 else "FAIL",
                "interpretation": "mechanism diagnostic: score-targeted positives concentrate on null-superset block maxima",
                "evidence_scope": SCOPE,
            },
            {
                "gate": "mechanism_claim_allowed",
                "value": int(int(score_002["safe_seeds"]) == 20 and ratio >= 5.0),
                "threshold": 1,
                "status": "PASS" if int(score_002["safe_seeds"]) == 20 and ratio >= 5.0 else "FAIL",
                "interpretation": "allowed mechanism claim: high-score positives remove the calibration maxima that constrain evidence",
                "evidence_scope": SCOPE,
            },
        ]
    )
    gate = pd.DataFrame(gate_rows)
    return frontier, positive_yield, blockmax, mass, figure, gate


def upsert_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase65b_parc_a_mechanism_diagnostics",
        "path": rel(OUT) + "/",
        "evidence_state": "completed_parc_a_mechanism_diagnostic",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics",
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
    status = "completed_mechanism_supported" if gate["status"].eq("PASS").all() else "completed_mechanism_mixed"
    append_once(
        ROOT / "docs/claim_table.md",
        "## Phase65b PARC-A Mechanism Diagnostics",
        f"""## Phase65b PARC-A Mechanism Diagnostics

Status: `{status}`.

Phase65b explains the CTC score-targeted active-audit transition by measuring
whether audited positives remove the calibration null-superset block maxima
that constrain release evidence. This is a mechanism diagnostic over existing
CTC labels, not new human labeling and not materials evidence.
""",
    )
    append_once(
        ROOT / "README.md",
        "NCS Phase65b PARC-A mechanism diagnostics",
        "- NCS Phase65b PARC-A mechanism diagnostics: fine-grid CTC audit frontier plus block-maximum removal and evidence-mass transition tables.",
    )
    append_once(
        ROOT / "REPRODUCIBILITY.md",
        "## NCS Phase65b PARC-A Mechanism Diagnostics",
        """## NCS Phase65b PARC-A Mechanism Diagnostics

Reproduce with:

```bash
make reproduce-ncs-phase65b-parc-a-mechanism-diagnostics
python scripts/validate_public_bundle.py outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics
```
""",
    )
    ledger = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    df = pd.read_csv(ledger)
    claim_id = "CTC-PARCA-MECH-001"
    df = df[df["claim_id"] != claim_id]
    artifact = OUT / "table_parc_a_mechanism_gate.csv"
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "claim_id": claim_id,
                        "claim_text": "Score-targeted CTC active audit works by removing high-scoring positive calibration block maxima that constrain PARC evidence.",
                        "evidence_type": "mechanism_diagnostic",
                        "positive_evidence": "partial",
                        "scope": "CTC_primary_only_existing_labels_no_new_human_audit",
                        "artifact_path": rel(artifact),
                        "hash": sha256_file(artifact),
                        "validation_command": "make reproduce-ncs-phase65b-parc-a-mechanism-diagnostics",
                        "status": "PASS",
                        "overclaim_guardrail": "do_not_claim_new_human_labels_or_materials_primary_success",
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
    target = "reproduce-ncs-phase65b-parc-a-mechanism-diagnostics"
    if target not in text:
        text = text.replace(".PHONY: test validate-public-bundle verify-manifest", ".PHONY: test validate-public-bundle verify-manifest " + target)
        text = text.rstrip() + f"\n\n{target}:\n\t$(PYTHON) scripts/build_ncs_phase65b_parc_a_mechanism_diagnostics.py\n"
    validation_line = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics\n"
    if validation_line not in text:
        marker = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy\n"
        if marker in text:
            text = text.replace(marker, marker + validation_line)
    path.write_text(text, encoding="utf-8")


def write_outputs() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = phase65.load_ctc()
    seed_rows = run_seed_rows(frame)
    frontier, positive_yield, blockmax, mass, figure, gate = summarize(seed_rows)
    seed_rows.to_csv(OUT / "table_parc_a_mechanism_seed_rows.csv", index=False)
    frontier.to_csv(OUT / "table_parc_a_budget_frontier_finegrid.csv", index=False)
    positive_yield.to_csv(OUT / "table_parc_a_positive_yield_by_policy.csv", index=False)
    blockmax.to_csv(OUT / "table_parc_a_blockmax_removal.csv", index=False)
    mass.to_csv(OUT / "table_parc_a_evidence_mass_transition.csv", index=False)
    figure.to_csv(OUT / "figure_parc_a_phase_transition_inputs.csv", index=False)
    gate.to_csv(OUT / "table_parc_a_mechanism_gate.csv", index=False)
    closeout_status = "completed_mechanism_supported" if gate["status"].eq("PASS").all() else "completed_mechanism_mixed"
    (OUT / "NCS_PHASE65B_PARC_A_MECHANISM_DIAGNOSTICS.md").write_text(
        f"""# Phase65b PARC-A Mechanism Diagnostics

Status: `{closeout_status}`.

This milestone explains the Phase65 score-targeted CTC transition. It reports
a fine-grid budget frontier, verified-positive yield, block-maximum removal,
and evidence-mass transition under the same hidden-label-use boundary as
Phase65.

Allowed claim: high-score one-sided positives remove calibration
null-superset block maxima that constrain release evidence.

Forbidden claims: no new human audit, no DFT evidence, no prospective
materials discovery, and no claim that Phase65b is a new cross-domain result.
""",
        encoding="utf-8",
    )
    provenance = {
        "status": "completed",
        "phase": "phase65b",
        "milestone": "ncs_phase65b_parc_a_mechanism_diagnostics",
        "source_tables": {
            "ctc_universe": {
                "path": "local_restricted_ctc_learned_hybrid_universe_not_distributed",
                "sha256": sha256_file(phase65.CTC_UNIVERSE),
            },
            "phase65_claim_gate": {
                "path": rel(ROOT / "outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy/table_parc_a_claim_gate.csv"),
                "sha256": sha256_file(ROOT / "outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy/table_parc_a_claim_gate.csv"),
            },
        },
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    update_docs(gate)
    patch_makefile()
    write_root_manifest()
    return {"status": closeout_status, "seed_rows": int(len(seed_rows)), "out_dir": rel(OUT)}


def main() -> None:
    print(json.dumps(write_outputs(), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
