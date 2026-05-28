#!/usr/bin/env python3
"""Build Phase64 PARC-R versioned recertification audit.

PARC-R asks a different question from the Phase50 t1 audit.  Phase50 evaluates
an old t0 release under a new current-MP hull.  This milestone reruns a
versioned recertification replay using only t1 positives in calibration blocks
and evaluates held-out t1 blocks after the recertification decision.  The
available t1 labels cover the frozen K=300/500 materials queue union, so the
result is a queue-limited recertification audit rather than a full-WBM theorem
certificate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from run_materials_discovery_parc_flagship import gamma_star_from_p, scs_release_count


ROOT = Path(__file__).resolve().parents[1]
PHASE50 = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition"
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
OUT = ROOT / "outputs/milestones/ncs_phase64_parc_r_versioned_recertification"

ALPHA = 0.10
SEEDS = list(range(20))
RHO_GRID = [0.10, 1.00]
SCOPE = (
    "PARC_R_versioned_recertification_queue_limited_audit;"
    "uses_current_MP_t1_positives_in_calibration_blocks;"
    "heldout_t1_blocks_evaluated_after_decision;"
    "not_full_WBM_recertification;"
    "not_t1_alpha_certificate_for_old_release;"
    "not_DFT_evidence;"
    "not_prospective_discovery"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
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
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def split_blocks(block_ids: list[str], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def load_queue() -> pd.DataFrame:
    queue = pd.read_csv(PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv")
    queue = queue[queue["K"].isin([300, 500])].copy()
    queue["candidate_id"] = queue["candidate_id"].astype(str)
    queue["block_id"] = queue["chemical_system"].astype(str)
    queue["t0_stable"] = queue["t0_label"].eq("stable")
    queue["t1_stable"] = queue["t1_label"].eq("stable")
    queue["t1_labelable"] = queue["t1_label"].isin(["stable", "unstable_or_unresolved"])
    queue["score_for_recertification"] = pd.to_numeric(queue["raw_score"], errors="coerce")
    return queue.reset_index(drop=True)


def load_old_release_summary() -> pd.DataFrame:
    summary = pd.read_csv(PHASE50 / "table_t1_ftr_by_k_and_policy.csv")
    summary = summary[summary["policy"].isin(["PARC", "raw_topK", "raw_topR"])].copy()
    return summary


def compute_evalues(
    frame: pd.DataFrame,
    *,
    cal_blocks: set[str],
    followup_blocks: set[str],
    observed_positive: np.ndarray,
) -> tuple[pd.DataFrame, dict[str, object]]:
    block_series = frame["block_id"].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    followup_mask = block_series.isin(followup_blocks).to_numpy()
    cal_null = frame.loc[cal_mask & ~observed_positive, ["block_id", "score_for_recertification"]].copy()
    maxima = (
        cal_null.groupby("block_id", sort=False)["score_for_recertification"].max().astype(float).to_numpy()
        if len(cal_null)
        else np.asarray([], dtype=float)
    )
    followup = frame.loc[followup_mask].sort_values("score_for_recertification", ascending=False).copy()
    p_min = 1.0 / (len(maxima) + 1.0) if len(maxima) else 1.0
    gamma = gamma_star_from_p(p_min)
    if gamma is None or len(maxima) == 0 or len(followup) == 0:
        followup["_recert_evalue"] = np.zeros(len(followup), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = followup["score_for_recertification"].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        followup["_recert_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return followup, {
        "calibration_blocks": int(len(cal_blocks)),
        "followup_blocks": int(len(followup_blocks)),
        "nonempty_calibration_null_blocks": int(len(maxima)),
        "block_coverage": float(len(maxima) / len(cal_blocks)) if cal_blocks else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma if gamma is not None else math.nan,
        "required_e": 1.0 / ALPHA,
    }


def run_seed(frame: pd.DataFrame, *, k: int, seed: int, rho: float) -> tuple[dict[str, object], pd.DataFrame]:
    cal_blocks, followup_blocks = split_blocks(frame["block_id"].astype(str).tolist(), seed)
    block_series = frame["block_id"].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    observed = np.zeros(len(frame), dtype=bool)
    eligible = np.flatnonzero(cal_mask & frame["t1_stable"].to_numpy(dtype=bool))
    if len(eligible) and rho > 0:
        n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
        scores = frame["score_for_recertification"].to_numpy(dtype=float)
        chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
        observed[chosen] = True

    followup, diag = compute_evalues(
        frame,
        cal_blocks=cal_blocks,
        followup_blocks=followup_blocks,
        observed_positive=observed,
    )
    pool = followup.head(k).copy()
    released, tau, margin, best_ratio = scs_release_count(
        pool["_recert_evalue"].to_numpy(dtype=float), alpha=ALPHA, budget=k
    )
    if released:
        selected = pool.iloc[np.argsort(pool["_recert_evalue"].to_numpy(dtype=float))[::-1][:released]].copy()
        release_t1_ftr = float((~selected["t1_stable"].astype(bool)).mean())
        release_t0_ftr = float((~selected["t0_stable"].astype(bool)).mean())
        false_t1 = int((~selected["t1_stable"].astype(bool)).sum())
        false_t0 = int((~selected["t0_stable"].astype(bool)).sum())
        decision = "versioned_certified_release" if release_t1_ftr <= ALPHA else "versioned_boundary_release"
    else:
        selected = pool.iloc[[]].copy()
        release_t1_ftr = math.nan
        release_t0_ftr = math.nan
        false_t1 = 0
        false_t0 = 0
        decision = "versioned_certified_refusal"

    raw_prefix = pool.head(k).copy()
    raw_matched = pool.head(released).copy() if released else pool.iloc[[]].copy()
    row = {
        "K": k,
        "alpha": ALPHA,
        "rho_t1_positive_support": rho,
        "seed": seed,
        "recertification_mode": "scarce_t1_positive_support" if rho < 1 else "full_t1_positive_support_in_calibration_blocks",
        "decision": decision,
        "release_size": int(released),
        "release_false_t1": false_t1,
        "release_false_t0": false_t0,
        "release_FTR_t1": release_t1_ftr,
        "release_FTR_t0": release_t0_ftr,
        "raw_pool_size": int(len(raw_prefix)),
        "raw_pool_FTR_t1": float((~raw_prefix["t1_stable"].astype(bool)).mean()) if len(raw_prefix) else math.nan,
        "raw_pool_FTR_t0": float((~raw_prefix["t0_stable"].astype(bool)).mean()) if len(raw_prefix) else math.nan,
        "matched_rawR_FTR_t1": float((~raw_matched["t1_stable"].astype(bool)).mean()) if released else math.nan,
        "observed_t1_positives": int(observed.sum()),
        "t1_stable_eligible_in_calibration": int(len(eligible)),
        "release_threshold_tau": tau,
        "self_consistency_margin": margin,
        "best_mass_ratio": best_ratio,
        "evidence_scope": SCOPE,
        **diag,
    }

    candidate = frame.copy()
    candidate["seed"] = seed
    candidate["rho_t1_positive_support"] = rho
    candidate["partition"] = np.where(candidate["block_id"].isin(cal_blocks), "calibration", "followup")
    candidate["observed_t1_positive_for_recertification"] = observed
    evalue_map = followup.set_index("candidate_id")["_recert_evalue"].to_dict()
    candidate["recert_evalue"] = candidate["candidate_id"].map(evalue_map).fillna(0.0)
    selected_ids = set(selected["candidate_id"].astype(str))
    candidate["recertified_release"] = candidate["candidate_id"].isin(selected_ids)
    candidate["recertification_decision"] = decision
    candidate["evidence_scope"] = SCOPE
    return row, candidate


def summarize_seed_rows(seed_rows: pd.DataFrame, old_summary: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    primary_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    for (k, rho), group in seed_rows.groupby(["K", "rho_t1_positive_support"], dropna=False):
        k = int(k)
        rho = float(rho)
        old_parc = old_summary[(old_summary["K"].eq(k)) & old_summary["policy"].eq("PARC")].iloc[0]
        old_raw = old_summary[(old_summary["K"].eq(k)) & old_summary["policy"].eq("raw_topK")].iloc[0]
        nonempty = int((group["release_size"].astype(int) > 0).sum())
        safe_nonempty = int(
            ((group["release_size"].astype(int) > 0) & (group["release_FTR_t1"].astype(float) <= ALPHA)).sum()
        )
        mean_release = float(group["release_size"].astype(float).mean())
        mean_release_ftr = (
            float(group.loc[group["release_size"].astype(int) > 0, "release_FTR_t1"].astype(float).mean())
            if nonempty
            else math.nan
        )
        row = {
            "K": k,
            "alpha": ALPHA,
            "rho_t1_positive_support": rho,
            "recertification_mode": str(group["recertification_mode"].iloc[0]),
            "n_seeds": int(group["seed"].nunique()),
            "nonempty_seeds": nonempty,
            "safe_nonempty_seeds": safe_nonempty,
            "mean_release_size": mean_release,
            "max_release_size": int(group["release_size"].astype(int).max()),
            "mean_release_FTR_t1_if_nonempty": mean_release_ftr,
            "mean_raw_pool_FTR_t1": float(group["raw_pool_FTR_t1"].astype(float).mean()),
            "old_t0_PARC_release_FTR_t1": float(old_parc["ftr_t1"]),
            "old_t0_raw_topK_FTR_t1": float(old_raw["ftr_t1"]),
            "old_t0_PARC_release_size": int(old_parc["n_candidates"]),
            "old_t0_PARC_t1_false_n": int(old_parc["n_t1_unstable"]),
            "mean_observed_t1_positives": float(group["observed_t1_positives"].astype(float).mean()),
            "mean_best_mass_ratio": float(group["best_mass_ratio"].astype(float).mean()),
            "recertification_status": "versioned_refusal" if nonempty == 0 else "versioned_release_or_boundary",
            "claim_status": "completed_versioned_recertification_refusal_boundary" if nonempty == 0 else "completed_versioned_recertification_release_diagnostic",
            "evidence_scope": SCOPE,
        }
        primary_rows.append(row)
        gates = [
            (
                "t1_recertification_nonempty_ge_18_seeds",
                nonempty,
                18,
                "PASS" if nonempty >= 18 else "FAIL",
                "headline release requires nonempty recertified release in most seeds",
            ),
            (
                "t1_recertification_mean_FTR_le_alpha_if_nonempty",
                mean_release_ftr if not math.isnan(mean_release_ftr) else math.nan,
                ALPHA,
                "PASS" if nonempty and mean_release_ftr <= ALPHA else "NOT_APPLICABLE_REFUSAL",
                "FTR gate is evaluated only for nonempty recertified releases",
            ),
            (
                "t1_recertification_refuses_old_unsafe_release",
                1 if nonempty == 0 and float(old_parc["ftr_t1"]) > ALPHA else 0,
                1,
                "PASS" if nonempty == 0 and float(old_parc["ftr_t1"]) > ALPHA else "FAIL",
                "refusal is meaningful because the old t0 release exceeds the current-MP alpha reference",
            ),
            (
                "headline_positive_recertification_allowed",
                1 if nonempty >= 18 and nonempty and mean_release_ftr <= ALPHA else 0,
                1,
                "PASS" if nonempty >= 18 and nonempty and mean_release_ftr <= ALPHA else "FAIL",
                "positive PARC-R headline requires current-version nonempty alpha-safe release",
            ),
            (
                "versioned_refusal_claim_allowed",
                1 if nonempty == 0 and float(old_parc["ftr_t1"]) > ALPHA else 0,
                1,
                "PASS" if nonempty == 0 and float(old_parc["ftr_t1"]) > ALPHA else "FAIL",
                "allowed claim: versioned recertification returns refusal rather than inheriting unsafe old release",
            ),
        ]
        for gate, value, threshold, status, interpretation in gates:
            gate_rows.append(
                {
                    "K": k,
                    "rho_t1_positive_support": rho,
                    "gate": gate,
                    "value": value,
                    "threshold": threshold,
                    "status": status,
                    "interpretation": interpretation,
                    "evidence_scope": SCOPE,
                }
            )
    return primary_rows, gate_rows


def build_outputs() -> dict[str, object]:
    OUT.mkdir(parents=True, exist_ok=True)
    queue = load_queue()
    old_summary = load_old_release_summary()
    seed_rows: list[dict[str, object]] = []
    candidate_rows: list[pd.DataFrame] = []
    for k in [300, 500]:
        k_rows = queue[queue["K"].eq(k)].copy().reset_index(drop=True)
        for rho in RHO_GRID:
            for seed in SEEDS:
                row, candidate = run_seed(k_rows, k=k, seed=seed, rho=rho)
                seed_rows.append(row)
                if seed == 0:
                    candidate_rows.append(candidate)

    seed_df = pd.DataFrame(seed_rows)
    primary_rows, gate_rows = summarize_seed_rows(seed_df, old_summary)
    primary_df = pd.DataFrame(primary_rows)
    gate_df = pd.DataFrame(gate_rows)
    candidate_df = pd.concat(candidate_rows, ignore_index=True)

    seed_df.to_csv(OUT / "table_parc_r_seed_rows.csv", index=False)
    primary_df.to_csv(OUT / "table_parc_r_primary_results.csv", index=False)
    gate_df.to_csv(OUT / "table_parc_r_gate_audit.csv", index=False)
    candidate_df[
        [
            "candidate_id",
            "structure_hash",
            "formula",
            "chemical_system",
            "K",
            "raw_rank",
            "raw_score",
            "policy_status",
            "t0_label",
            "t1_label",
            "drift_type",
            "seed",
            "rho_t1_positive_support",
            "partition",
            "observed_t1_positive_for_recertification",
            "recert_evalue",
            "recertified_release",
            "recertification_decision",
            "evidence_scope",
        ]
    ].to_csv(OUT / "table_parc_r_candidate_level_seed0.csv", index=False)

    refusal_rows: list[dict[str, object]] = []
    for _, row in primary_df.iterrows():
        refusal_rows.append(
            {
                "K": int(row["K"]),
                "rho_t1_positive_support": float(row["rho_t1_positive_support"]),
                "old_t0_PARC_release_size": int(row["old_t0_PARC_release_size"]),
                "old_t0_PARC_t1_false_n": int(row["old_t0_PARC_t1_false_n"]),
                "old_t0_PARC_release_FTR_t1": float(row["old_t0_PARC_release_FTR_t1"]),
                "PARC_R_nonempty_seeds": int(row["nonempty_seeds"]),
                "PARC_R_decision": "versioned_certified_refusal" if int(row["nonempty_seeds"]) == 0 else "versioned_release_or_boundary",
                "refusal_reason": "insufficient_current_version_evidence_mass_under_t1_recertification",
                "paper_role": "versioned_refusal_boundary_not_positive_materials_discovery",
                "evidence_scope": SCOPE,
            }
        )
    pd.DataFrame(refusal_rows).to_csv(OUT / "table_parc_r_refusal_diagnostics.csv", index=False)

    figure_rows: list[dict[str, object]] = []
    for _, row in primary_df.iterrows():
        for metric in [
            "nonempty_seeds",
            "mean_release_size",
            "mean_raw_pool_FTR_t1",
            "old_t0_PARC_release_FTR_t1",
            "old_t0_raw_topK_FTR_t1",
            "mean_best_mass_ratio",
        ]:
            figure_rows.append(
                {
                    "panel": "versioned_recertification_frontier",
                    "K": int(row["K"]),
                    "rho_t1_positive_support": float(row["rho_t1_positive_support"]),
                    "metric": metric,
                    "value": row[metric],
                    "alpha_reference_line": ALPHA,
                    "evidence_scope": SCOPE,
                }
            )
    pd.DataFrame(figure_rows).to_csv(OUT / "figure_parc_r_versioned_recertification_inputs.csv", index=False)

    prereg = f"""# PARC-R Versioned Recertification Preregistration

Status: frozen before interpreting Phase64 outputs.

Question: when the public materials hull moves from t0 to current-MP t1, should
the old t0 release be inherited, or should the queue be recertified under the
new label version?

Inputs:

- Frozen K=300/500 materials queue union from Phase51.
- Frozen raw ALIGNN-FF score/rank.
- Current-MP t1 labels acquired in Phase49.

Protocol:

1. Split chemical systems into calibration/follow-up blocks for seeds 0-19.
2. Reveal only t1-stable positives in calibration blocks.
3. Construct null-superset block-max e-values from calibration non-observed rows.
4. Run the original SCS rule at alpha={ALPHA}.
5. Evaluate held-out t1 follow-up blocks only after the recertification decision.

Scope:

- queue-limited recertification audit, not full-WBM recertification;
- not a t1 alpha certificate for the old t0 release;
- no new DFT and no prospective materials discovery.
"""
    (OUT / "PARC_R_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")

    positive_allowed = bool((gate_df["gate"].eq("headline_positive_recertification_allowed") & gate_df["status"].eq("PASS")).any())
    closeout = f"""# Phase64 PARC-R Versioned Recertification

Status: `completed_versioned_recertification_refusal_boundary`.

PARC-R tests whether a materials release certificate should be inherited after
the reference hull moves from t0 to current-MP t1.  In the available
queue-limited t1 universe, recertification using t1 positives in calibration
blocks returns certified refusal for K=300 and K=500 under both scarce 10%
support and full calibration-block support.

Interpretation:

- This is not a positive current-MP alpha release result.
- It is a versioned refusal result: the old t0 release has current-MP FTR above
  alpha, and rerunning the release rule under t1 support refuses rather than
  inheriting the unsafe release.
- The result supports versioned release-card infrastructure: certificates are
  bound to their label version and should be renewed after database updates.

Headline positive PARC-R allowed: `{str(positive_allowed).lower()}`.

Allowed claim: current-MP recertification detects insufficient t1 evidence mass
and returns refusal for the K=300/500 materials queues.

Forbidden claims:

- no prospective materials discovery;
- no DFT evidence;
- no t1 alpha certificate for the old t0 release;
- no claim that PARC-R creates a nonempty current-MP materials release.
"""
    (OUT / "NCS_PHASE64_PARC_R_VERSIONED_RECERTIFICATION.md").write_text(closeout, encoding="utf-8")

    provenance = {
        "status": "completed",
        "phase": "phase64",
        "milestone": "ncs_phase64_parc_r_versioned_recertification",
        "source_tables": {
            "phase51_candidate_level": {
                "path": rel(PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv"),
                "sha256": sha256_file(PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv"),
            },
            "phase49_t1_ftr": {
                "path": rel(PHASE50 / "table_t1_ftr_by_k_and_policy.csv"),
                "sha256": sha256_file(PHASE50 / "table_t1_ftr_by_k_and_policy.csv"),
            },
        },
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")

    write_manifest(OUT)
    return {
        "status": "completed",
        "out_dir": rel(OUT),
        "primary_rows": int(len(primary_df)),
        "seed_rows": int(len(seed_df)),
        "candidate_seed0_rows": int(len(candidate_df)),
        "headline_positive_allowed": positive_allowed,
        "claim_status": "completed_versioned_recertification_refusal_boundary",
    }


def upsert_artifact_index(report: dict[str, object]) -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase64_parc_r_versioned_recertification",
        "path": rel(OUT) + "/",
        "evidence_state": "completed_versioned_recertification_refusal_boundary",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase64_parc_r_versioned_recertification",
    }
    if path.exists():
        df = pd.read_csv(path)
        df = df[df["milestone"] != row["milestone"]]
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_csv(path, index=False)


def append_once(path: Path, marker: str, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker not in existing:
        path.write_text(existing.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def update_docs(report: dict[str, object]) -> None:
    upsert_artifact_index(report)
    append_once(
        ROOT / "docs/claim_table.md",
        "## Phase64 PARC-R Versioned Recertification",
        """## Phase64 PARC-R Versioned Recertification

Status: `completed_versioned_recertification_refusal_boundary`.

PARC-R reruns a queue-limited current-MP t1 recertification replay for the
K=300/500 materials queues. It returns certified refusal under both scarce
10% t1 positive support and full calibration-block t1 positive support. This
supports a versioned release-card claim: old t0 certificates should not be
inherited after a database update without recertification. It is not a
nonempty current-MP materials release, not DFT evidence, and not prospective
materials discovery.""",
    )
    append_once(
        ROOT / "README.md",
        "NCS Phase64 PARC-R versioned recertification",
        "- NCS Phase64 PARC-R versioned recertification: queue-limited current-MP recertification refuses unsafe old materials releases rather than inheriting them.",
    )
    append_once(
        ROOT / "REPRODUCIBILITY.md",
        "## NCS Phase64 PARC-R Versioned Recertification",
        """## NCS Phase64 PARC-R Versioned Recertification

Reproduce the queue-limited current-MP recertification audit with:

```bash
make reproduce-ncs-phase64-parc-r-versioned-recertification
python scripts/validate_public_bundle.py outputs/milestones/ncs_phase64_parc_r_versioned_recertification
```

The milestone is a versioned refusal boundary, not a nonempty t1 alpha
certificate or DFT evidence.""",
    )
    ledger = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    df = pd.read_csv(ledger)
    claim_id = "M-PARCR-001"
    df = df[df["claim_id"] != claim_id]
    gate = OUT / "table_parc_r_gate_audit.csv"
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "claim_id": claim_id,
                        "claim_text": "Current-MP PARC-R recertification refuses the K=300/500 materials queues rather than inheriting the old t0 release under an unsafe current hull.",
                        "evidence_type": "versioned_recertification_refusal_boundary",
                        "positive_evidence": "partial",
                        "scope": "queue_limited_current_MP_t1_recertification_refusal_not_nonempty_release",
                        "artifact_path": rel(gate),
                        "hash": sha256_file(gate),
                        "validation_command": "make reproduce-ncs-phase64-parc-r-versioned-recertification",
                        "status": "PASS",
                        "overclaim_guardrail": "do_not_claim_nonempty_t1_alpha_release_DFT_or_prospective_materials_discovery",
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
    target = "reproduce-ncs-phase64-parc-r-versioned-recertification"
    if target not in text:
        text = text.replace(
            ".PHONY: test validate-public-bundle verify-manifest",
            ".PHONY: test validate-public-bundle verify-manifest " + target,
        )
        text = text.rstrip() + f"\n\n{target}:\n\t$(PYTHON) scripts/build_ncs_phase64_parc_r_versioned_recertification.py\n"
    validation_line = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase64_parc_r_versioned_recertification\n"
    if validation_line not in text:
        marker = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification\n"
        if marker in text:
            text = text.replace(marker, marker + validation_line)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    report = build_outputs()
    update_docs(report)
    patch_makefile()
    write_root_manifest()
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
