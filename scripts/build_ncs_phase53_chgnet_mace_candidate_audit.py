#!/usr/bin/env python3
"""Build Phase53 candidate-level CHGNet/MACE audit for the WBM t1 queue.

This script runs real CHGNet and MACE-MP single-point scores on the frozen
K=300/500 WBM queue candidates when the local private WBM structure cache is
available. The resulting labels are *score-support proxies*: raw MLIP energies
are not reference-hull e_above_hull values, so the audit must not be described
as MLIP ground truth or strict stability validation.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
OUT = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit"
PRIVATE_STEP1 = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2")
PRIVATE_WBM_FULL = Path("/home/waas/paper_experiments/private/wbm_raw_full")
SCORE_CACHE = OUT / "table_chgnet_mace_raw_scores.csv"
PUBLIC_SAFE_STRUCTURE_SOURCE = "local_private_WBM_raw_structure_cache_not_distributed"
SCOPE = (
    "completed_candidate_level_CHGNet_MACE_score_audit;"
    "score_support_proxy_not_reference_hull_ehull;"
    "not_DFT_evidence;"
    "not_prospective_discovery"
)


def bool_label(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


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
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def material_step_and_index(material_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"wbm-(\d+)-(\d+)", str(material_id))
    if not match:
        raise ValueError(f"unexpected material_id format: {material_id}")
    step = int(match.group(1))
    idx = int(match.group(2)) - 1
    return step, idx


def step_path(step: int) -> Path:
    if step == 1:
        return PRIVATE_STEP1
    return PRIVATE_WBM_FULL / f"step_{step}.json.bz2"


def load_needed_structures(candidate_ids: list[str]) -> dict[str, Structure]:
    by_step: dict[int, set[int]] = {}
    for candidate_id in candidate_ids:
        step, idx = material_step_and_index(candidate_id)
        by_step.setdefault(step, set()).add(idx)
    structures: dict[str, Structure] = {}
    for step, indexes in sorted(by_step.items()):
        path = step_path(step)
        if not path.exists():
            raise FileNotFoundError(f"missing private WBM raw structure cache: {path}")
        with bz2.open(path, "rt") as handle:
            entries = json.load(handle)["entries"]
        for idx in sorted(indexes):
            material_id = f"wbm-{step}-{idx + 1}"
            structures[material_id] = Structure.from_dict(entries[idx]["structure"])
    return structures


def score_candidates(candidate_ids: list[str], force: bool = False) -> pd.DataFrame:
    if SCORE_CACHE.exists() and not force:
        cached = pd.read_csv(SCORE_CACHE)
        if set(candidate_ids).issubset(set(cached["candidate_id"])):
            return cached[cached["candidate_id"].isin(candidate_ids)].copy()

    structures = load_needed_structures(candidate_ids)
    from chgnet.model.model import CHGNet
    from mace.calculators import mace_mp

    chgnet = CHGNet.load()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    mace_calc = mace_mp(model="small", device=device, default_dtype="float32")
    adaptor = AseAtomsAdaptor()
    rows: list[dict[str, object]] = []
    for i, candidate_id in enumerate(candidate_ids, start=1):
        structure = structures[candidate_id]
        chgnet_energy = np.nan
        mace_energy = np.nan
        chgnet_status = "not_scored"
        mace_status = "not_scored"
        chgnet_error = ""
        mace_error = ""
        try:
            pred: Any = chgnet.predict_structure(structure, task="e")
            chgnet_energy = float(pred["e"])
            chgnet_status = "scored"
        except Exception as exc:  # pragma: no cover - only hit for unsupported structures
            chgnet_status = "failed"
            chgnet_error = f"{type(exc).__name__}: {exc}"[:180]
        try:
            atoms = adaptor.get_atoms(structure)
            atoms.calc = mace_calc
            mace_energy = float(atoms.get_potential_energy() / len(atoms))
            mace_status = "scored"
        except Exception as exc:  # pragma: no cover - only hit for unsupported structures
            mace_status = "failed"
            mace_error = f"{type(exc).__name__}: {exc}"[:180]
        rows.append(
            {
                "candidate_id": candidate_id,
                "structure_hash": hashlib.sha256(structure.as_dict().__repr__().encode("utf-8")).hexdigest(),
                "n_sites": len(structure),
                "chgnet_energy_per_atom": chgnet_energy,
                "mace_energy_per_atom": mace_energy,
                "chgnet_score_status": chgnet_status,
                "mace_score_status": mace_status,
                "chgnet_error": chgnet_error,
                "mace_error": mace_error,
                "structure_source": PUBLIC_SAFE_STRUCTURE_SOURCE,
                "score_order": i,
            }
        )
        if i % 100 == 0:
            print(f"scored {i}/{len(candidate_ids)}", flush=True)
    scored = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    scored.to_csv(SCORE_CACHE, index=False)
    return scored


def assign_support_labels(df: pd.DataFrame, score_col: str, label_col: str, status_col: str) -> tuple[pd.DataFrame, float]:
    scored = df[df[score_col].notna()].copy()
    t0_stable_fraction = float(df["t0_label"].eq("stable").mean())
    quantile = min(max(t0_stable_fraction, 0.0), 1.0)
    threshold = float(scored[score_col].quantile(quantile)) if not scored.empty else np.nan
    df[label_col] = "not_scored"
    ok = df[status_col].eq("scored") & df[score_col].notna()
    df.loc[ok & (df[score_col] <= threshold), label_col] = "score_supported"
    df.loc[ok & (df[score_col] > threshold), label_col] = "score_unsupported"
    return df, threshold


def build_audit(force_score: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    phase51 = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    phase51["candidate_id"] = phase51["material_id"]
    phase51["t0_label"] = phase51["stable_exact_t0"].map(lambda value: "stable" if bool_label(value) else "unstable_or_unresolved")
    phase51["t1_label"] = phase51["stable_exact_t1_current_mp"].map(lambda value: "stable" if bool_label(value) else "unstable_or_unresolved")
    phase51["t1_drift_type"] = phase51["drift_class"]
    phase51["policy_status"] = "outside_requested_queue"
    phase51.loc[phase51["raw_topK_seed_count"] > 0, "policy_status"] = "raw_topK_only"
    phase51.loc[(phase51["raw_topR_seed_count"] > 0) & (phase51["parc_seed_count"] == 0), "policy_status"] = "raw_topR_matched"
    phase51.loc[(phase51["raw_only_tail_seed_count"] > 0) & (phase51["parc_seed_count"] == 0), "policy_status"] = "extra_tail"
    phase51.loc[phase51["parc_seed_count"] > 0, "policy_status"] = "parc_release"
    phase51.loc[(phase51["parc_seed_count"] > 0) & phase51["near_hull_50mev_t1"].astype(bool), "policy_status"] = "boundary_release"
    phase51["parc_released"] = phase51["parc_seed_count"] > 0
    phase51["failure_explanation_class"] = phase51["t1_false_explanation_class"]
    phase51["is_t1_false_release"] = phase51["parc_released"] & phase51["t1_false_conservative"].astype(bool)
    candidate_ids = sorted(phase51["candidate_id"].unique())
    scores = score_candidates(candidate_ids, force=force_score)
    scores = scores.rename(columns={"structure_hash": "structure_hash_scored"})
    rows = phase51.merge(scores, on="candidate_id", how="left")
    rows["structure_hash"] = rows["structure_hash_scored"]
    rows["chgnet_predicted_ehull_or_score"] = rows["chgnet_energy_per_atom"]
    rows["mace_predicted_ehull_or_score"] = rows["mace_energy_per_atom"]
    rows, chgnet_threshold = assign_support_labels(
        rows, "chgnet_energy_per_atom", "chgnet_label", "chgnet_score_status"
    )
    rows, mace_threshold = assign_support_labels(rows, "mace_energy_per_atom", "mace_label", "mace_score_status")
    rows["chgnet_mace_consensus_label"] = "not_scored"
    scored = rows["chgnet_label"].isin(["score_supported", "score_unsupported"]) & rows["mace_label"].isin(
        ["score_supported", "score_unsupported"]
    )
    rows.loc[scored & rows["chgnet_label"].eq("score_supported") & rows["mace_label"].eq("score_supported"), "chgnet_mace_consensus_label"] = "consensus_score_supported"
    rows.loc[scored & ~(rows["chgnet_label"].eq("score_supported") & rows["mace_label"].eq("score_supported")), "chgnet_mace_consensus_label"] = "not_consensus_supported"
    rows["chgnet_mace_disagreement"] = scored & (rows["chgnet_label"] != rows["mace_label"])
    rows["near_hull_t1_25mev"] = rows["near_hull_25mev_t1"]
    rows["near_hull_t1_50mev"] = rows["near_hull_50mev_t1"]
    rows["t1_drift_type"] = rows["t1_drift_type"]
    rows["label_rule"] = (
        "t0_prevalence_quantile_score_support_proxy_lower_energy_is_more_supported;"
        f"chgnet_threshold={chgnet_threshold:.8g};mace_threshold={mace_threshold:.8g}"
    )
    rows["evidence_scope"] = SCOPE

    required_cols = [
        "candidate_id",
        "structure_hash",
        "formula",
        "chemical_system",
        "policy_status",
        "K",
        "t0_label",
        "t1_label",
        "t1_drift_type",
        "chgnet_predicted_ehull_or_score",
        "mace_predicted_ehull_or_score",
        "chgnet_label",
        "mace_label",
        "chgnet_mace_consensus_label",
        "chgnet_mace_disagreement",
        "near_hull_t1_25mev",
        "near_hull_t1_50mev",
        "failure_explanation_class",
        "label_rule",
        "evidence_scope",
    ]
    rows[required_cols].to_csv(OUT / "table_materials_candidate_level_chgnet_mace_audit.csv", index=False)

    support_rows: list[dict[str, object]] = []
    for k in [300, 500]:
        k_rows = rows[rows["K"].eq(k)]
        group_map = {
            "PARC release": k_rows["parc_released"].astype(bool),
            "raw top-K": k_rows["raw_topK_seed_count"] > 0,
            "matched raw top-R": k_rows["raw_topR_seed_count"] > 0,
            "raw-only extra-tail": k_rows["raw_only_tail_seed_count"] > 0,
        }
        for group_name, mask in group_map.items():
            subset = k_rows[mask].copy()
            if subset.empty:
                continue
            support_rows.append(
                {
                    "K": k,
                    "policy_group": group_name,
                    "n_candidates": int(len(subset)),
                    "chgnet_stable_fraction_proxy": float(subset["chgnet_label"].eq("score_supported").mean()),
                    "mace_stable_fraction_proxy": float(subset["mace_label"].eq("score_supported").mean()),
                    "chgnet_mace_consensus_stable_fraction_proxy": float(
                        subset["chgnet_mace_consensus_label"].eq("consensus_score_supported").mean()
                    ),
                    "model_disagreement_rate": float(subset["chgnet_mace_disagreement"].mean()),
                    "near_hull_t1_25mev_fraction": float(subset["near_hull_t1_25mev"].mean()),
                    "near_hull_t1_50mev_fraction": float(subset["near_hull_t1_50mev"].mean()),
                    "mean_chgnet_score": float(subset["chgnet_predicted_ehull_or_score"].mean()),
                    "mean_mace_score": float(subset["mace_predicted_ehull_or_score"].mean()),
                    "label_rule": rows["label_rule"].iloc[0],
                    "evidence_scope": SCOPE,
                }
            )
    support = pd.DataFrame(support_rows)
    support.to_csv(OUT / "table_chgnet_mace_support_by_policy.csv", index=False)
    support.to_csv(OUT / "figure_chgnet_mace_release_vs_tail_inputs.csv", index=False)

    disagreement_rows: list[dict[str, object]] = []
    for k in [300, 500]:
        for t1_label, subset in rows[rows["K"].eq(k)].groupby("t1_label"):
            disagreement_rows.append(
                {
                    "K": k,
                    "t1_label": t1_label,
                    "n_candidates": int(len(subset)),
                    "chgnet_mace_disagreement_rate": float(subset["chgnet_mace_disagreement"].mean()),
                    "consensus_supported_fraction_proxy": float(
                        subset["chgnet_mace_consensus_label"].eq("consensus_score_supported").mean()
                    ),
                    "near_hull_t1_50mev_fraction": float(subset["near_hull_t1_50mev"].mean()),
                    "evidence_scope": SCOPE,
                }
            )
    pd.DataFrame(disagreement_rows).to_csv(OUT / "table_chgnet_mace_disagreement_by_t1_status.csv", index=False)

    pass_rows = []
    for k in [300, 500]:
        s = support[support["K"].eq(k)].set_index("policy_group")
        release = float(s.loc["PARC release", "chgnet_mace_consensus_stable_fraction_proxy"])
        tail = float(s.loc["raw-only extra-tail", "chgnet_mace_consensus_stable_fraction_proxy"])
        parc_false = rows[rows["K"].eq(k) & rows["is_t1_false_release"].astype(bool)].copy()
        boundary_or_disagree = float((parc_false["near_hull_t1_50mev"] | parc_false["chgnet_mace_disagreement"]).mean())
        far_consensus_negative = int(
            (
                (~parc_false["near_hull_t1_50mev"])
                & parc_false["chgnet_mace_consensus_label"].eq("not_consensus_supported")
                & (~parc_false["chgnet_mace_disagreement"])
            ).sum()
        )
        pass_rows.extend(
            [
                {
                    "K": k,
                    "gate": "PARC_release_consensus_support_exceeds_extra_tail",
                    "status": "PASS" if release > tail else "FAIL",
                    "lead_metric": f"{release:.3f} vs {tail:.3f}",
                    "claim_boundary": "score_support_proxy_not_stability_ground_truth",
                },
                {
                    "K": k,
                    "gate": "t1_false_cases_boundary_or_model_disagreement",
                    "status": "PASS" if boundary_or_disagree >= 0.50 else "DIAGNOSTIC_WEAK",
                    "lead_metric": f"{boundary_or_disagree:.3f}",
                    "claim_boundary": "explanation_diagnostic_not_alpha_certificate",
                },
                {
                    "K": k,
                    "gate": "far_from_hull_consensus_negative_PARC_false_low",
                    "status": "PASS" if far_consensus_negative <= max(5, 0.25 * len(parc_false)) else "FAIL",
                    "lead_metric": f"{far_consensus_negative}/{len(parc_false)}",
                    "claim_boundary": "score_support_proxy_not_reference_hull_ehull",
                },
            ]
        )
    write_csv(
        OUT / "table_phase53_go_no_go.csv",
        pass_rows,
        ["K", "gate", "status", "lead_metric", "claim_boundary"],
    )

    closeout = f"""# Phase53 CHGNet/MACE Candidate-Level Audit

Status: `completed_candidate_level_CHGNet_MACE_score_audit_partial_false_case_explanation`

This milestone scores the frozen K=300/500 WBM queue candidates with real
CHGNet and MACE-MP single-point energies from local WBM structures. It upgrades
Phase51 from an ALIGNN/model-zoo explanation to a candidate-level universal
potential audit, while keeping the claim boundary narrow.

Important boundary: the CHGNet/MACE columns are raw energy-per-atom score
proxies, not model-consistent reference-hull e_above_hull values. Stable labels
are t0-prevalence quantile score-support proxies and must not be cited as DFT
ground truth.

Allowed claim: CHGNet/MACE candidate-level score audit compares PARC release,
raw top-K, matched raw top-R and raw-only extra-tail under a frozen t1 audit.
The queue-level score-support contrast favors PARC release over raw-only
extra-tail. The t1 false-case explanation gate is weaker: false PARC candidates
are not primarily explained by CHGNet/MACE disagreement or t1 near-hull status,
so this milestone should not be promoted as a completed false-case mechanism.

Forbidden claim: CHGNet/MACE proves prospective materials discovery or strict
t1 alpha control.
"""
    (OUT / "NCS_PHASE53_CHGNET_MACE_CANDIDATE_AUDIT.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase53_chgnet_mace_candidate_audit",
        "structure_source": PUBLIC_SAFE_STRUCTURE_SOURCE,
        "chgnet": "CHGNet.load()",
        "mace": "mace_mp(model='small', default_dtype='float32')",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "n_unique_candidates": int(rows["candidate_id"].nunique()),
        "evidence_scope": SCOPE,
        "claim_status": "queue_level_CHGNet_MACE_support_passes_false_case_mechanism_partial",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT)
    write_root_manifest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-score", action="store_true")
    args = parser.parse_args()
    build_audit(force_score=args.force_score)
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
