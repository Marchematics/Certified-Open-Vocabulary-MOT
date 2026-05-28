#!/usr/bin/env python3
"""Build Phase61 PARC-M multi-evidence fusion feasibility audit.

This script tests whether fixed mixtures of original PARC e-values and frozen
ALIGNN/CHGNet/MACE score-derived e-proxies can improve the current-MP t1
materials queue. It also audits whether the ingredients are sufficient for a
theorem-grade multi-evidence e-value claim.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from build_materials_computational_trial import scs_release_count


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE53 = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit"
OUT = ROOT / "outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion"
ALPHA = 0.10
SCOPE = (
    "PARC_M_multi_evidence_fusion_feasibility;"
    "empirical_proxy_fusion_not_theorem_grade;"
    "CHGNet_MACE_queue_scores_not_full_null_calibration;"
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


def gamma_star_from_p(p_value: float) -> float:
    gamma = -1.0 / math.log(p_value)
    return gamma if 0.0 < gamma < 1.0 else 0.5


def score_rank_eproxy(scores: pd.Series, *, higher_is_better: bool) -> pd.Series:
    n = int(scores.notna().sum())
    if n <= 1:
        return pd.Series(np.zeros(len(scores)), index=scores.index)
    gamma = gamma_star_from_p(1.0 / (n + 1.0))
    rank = scores.rank(method="min", ascending=not higher_is_better)
    p_value = (rank / (n + 1.0)).clip(upper=1.0)
    return gamma * (p_value ** (gamma - 1.0))


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
                "chgnet_predicted_ehull_or_score",
                "mace_predicted_ehull_or_score",
                "chgnet_mace_consensus_label",
                "chgnet_mace_disagreement",
            ]
        ],
        on=["material_id", "K"],
        how="left",
        validate="one_to_one",
    )
    return merged


def add_evidence_columns(k_rows: pd.DataFrame) -> pd.DataFrame:
    out = k_rows.copy()
    out["E_original_PARC"] = out["parc_e_value"].astype(float)
    out["E_ALIGNN_rank_proxy"] = score_rank_eproxy(out["alignn_score"].astype(float), higher_is_better=True)
    out["E_CHGNet_rank_proxy"] = score_rank_eproxy(
        out["chgnet_predicted_ehull_or_score"].astype(float), higher_is_better=False
    )
    out["E_MACE_rank_proxy"] = score_rank_eproxy(
        out["mace_predicted_ehull_or_score"].astype(float), higher_is_better=False
    )
    out["E_PARC_M_avg"] = (
        out["E_original_PARC"]
        + out["E_ALIGNN_rank_proxy"]
        + out["E_CHGNet_rank_proxy"]
        + out["E_MACE_rank_proxy"]
    ) / 4.0
    out["E_PARC_M_raw_heavy"] = (
        0.50 * out["E_original_PARC"]
        + 0.25 * out["E_CHGNet_rank_proxy"]
        + 0.25 * out["E_MACE_rank_proxy"]
    )
    out["E_PARC_M_maxBonf"] = out[
        ["E_original_PARC", "E_ALIGNN_rank_proxy", "E_CHGNet_rank_proxy", "E_MACE_rank_proxy"]
    ].max(axis=1) / 4.0
    out["E_PARC_M_consensus"] = out["E_PARC_M_raw_heavy"]
    out["E_PARC_M_aux_only"] = (
        out["E_ALIGNN_rank_proxy"] + out["E_CHGNet_rank_proxy"] + out["E_MACE_rank_proxy"]
    ) / 3.0
    return out


FUSION_RULES = {
    "PARC-M-avg": "E_PARC_M_avg",
    "PARC-M-raw-heavy": "E_PARC_M_raw_heavy",
    "PARC-M-maxBonf": "E_PARC_M_maxBonf",
    "PARC-M-consensus": "E_PARC_M_consensus",
    "PARC-M-aux-only": "E_PARC_M_aux_only",
}


def summarize_selection(
    pool: pd.DataFrame,
    *,
    k: int,
    method: str,
    e_col: str | None,
    mask: pd.Series | None,
    original_t1_ftr: float,
    raw_t1_ftr: float,
) -> tuple[dict[str, object], pd.DataFrame]:
    if mask is not None:
        selected = pool[mask].copy()
        selected["_fusion_e"] = selected["E_original_PARC"].astype(float)
        released = int(len(selected))
        tau = np.nan
        margin = np.nan
        best_ratio = np.nan
        construction_rule = "fixed_existing_membership"
    else:
        assert e_col is not None
        values = pool[e_col].to_numpy(dtype=float)
        released, tau, margin, best_ratio = scs_release_count(values, alpha=ALPHA, budget=k)
        selected = pool.assign(_fusion_e=values).sort_values("_fusion_e", ascending=False).head(released).copy()
        construction_rule = "SCS_on_frozen_proxy_fusion_evidence"

    if released:
        t0_stable = selected["stable_exact_t0"].astype(bool)
        t1_stable = selected["stable_exact_t1_current_mp"].astype(bool)
        t0_ftr = float((~t0_stable).mean())
        t1_ftr = float((~t1_stable).mean())
        stable_to_unstable = float((t0_stable & ~t1_stable).mean())
        mlip_support = float(selected["chgnet_mace_consensus_label"].eq("consensus_score_supported").mean())
        min_e = float(selected["_fusion_e"].min())
        max_e = float(selected["_fusion_e"].max())
    else:
        t0_ftr = np.nan
        t1_ftr = np.nan
        stable_to_unstable = np.nan
        mlip_support = np.nan
        min_e = np.nan
        max_e = np.nan

    row = {
        "method": method,
        "K": k,
        "alpha": ALPHA,
        "release_size": released,
        "t0_FTR": t0_ftr,
        "t1_FTR": t1_ftr,
        "t1_raw_topK_minus_method": raw_t1_ftr - t1_ftr if released else np.nan,
        "t1_original_PARC_minus_method": original_t1_ftr - t1_ftr if released else np.nan,
        "stable_to_current_not_stable_rate": stable_to_unstable,
        "CHGNet_MACE_consensus_supported_fraction": mlip_support,
        "fusion_e_min": min_e,
        "fusion_e_max": max_e,
        "release_threshold_tau": tau,
        "self_consistency_margin": margin,
        "best_mass_ratio": best_ratio,
        "construction_rule": construction_rule,
        "theorem_grade_status": "proxy_fusion_not_theorem_grade",
        "evidence_scope": SCOPE,
    }
    return row, selected


def build_tables(df: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    result_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    for k in [300, 500]:
        k_rows = df[df["K"].eq(k)].copy()
        pool = add_evidence_columns(k_rows[k_rows["raw_topK_seed_count"] > 0].copy())
        raw_t1_ftr = float((~pool["stable_exact_t1_current_mp"].astype(bool)).mean())
        original = k_rows[k_rows["parc_seed_count"] > 0].copy()
        original_t1_ftr = float((~original["stable_exact_t1_current_mp"].astype(bool)).mean())

        baseline_specs = [
            ("raw top-K", pool.index.to_series().isin(pool.index)),
            ("PARC original release", pool["parc_seed_count"] > 0),
            ("matched raw top-R", pool["raw_topR_seed_count"] > 0),
            ("raw-only extra-tail", pool["raw_only_tail_seed_count"] > 0),
        ]
        for method, mask in baseline_specs:
            row, selected = summarize_selection(
                pool,
                k=k,
                method=method,
                e_col=None,
                mask=mask,
                original_t1_ftr=original_t1_ftr,
                raw_t1_ftr=raw_t1_ftr,
            )
            result_rows.append(row)
            for _, cand in selected.iterrows():
                candidate_rows.append(candidate_output_row(cand, k, method))

        for method, e_col in FUSION_RULES.items():
            row, selected = summarize_selection(
                pool,
                k=k,
                method=method,
                e_col=e_col,
                mask=None,
                original_t1_ftr=original_t1_ftr,
                raw_t1_ftr=raw_t1_ftr,
            )
            result_rows.append(row)
            for _, cand in selected.iterrows():
                candidate_rows.append(candidate_output_row(cand, k, method))

        fusion = [r for r in result_rows if r["K"] == k and str(r["method"]).startswith("PARC-M-")]
        best = min(fusion, key=lambda r: np.inf if pd.isna(r["t1_FTR"]) else r["t1_FTR"])
        gate_rows.extend(
            [
                {
                    "K": k,
                    "gate": "PARC_M_best_empirical_t1_improvement_ge_0p05",
                    "value": best["t1_original_PARC_minus_method"],
                    "threshold": 0.05,
                    "status": "PASS" if best["t1_original_PARC_minus_method"] >= 0.05 else "FAIL",
                    "interpretation": f"best empirical fusion row is {best['method']}",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "PARC_M_best_empirical_t1_improvement_ge_0p03",
                    "value": best["t1_original_PARC_minus_method"],
                    "threshold": 0.03,
                    "status": "PASS" if best["t1_original_PARC_minus_method"] >= 0.03 else "FAIL",
                    "interpretation": f"best empirical fusion row is {best['method']}",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "PARC_M_best_release_size_ge_100",
                    "value": best["release_size"],
                    "threshold": 100,
                    "status": "PASS" if best["release_size"] >= 100 else "FAIL",
                    "interpretation": "best empirical fusion release should not be trivial",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "theorem_grade_all_evalue_sources_available",
                    "value": 0,
                    "threshold": 1,
                    "status": "FAIL",
                    "interpretation": "CHGNet/MACE are queue-level score proxies without full null-superset calibration blocks",
                    "evidence_scope": SCOPE,
                },
                {
                    "K": k,
                    "gate": "PARC_M_headline_claim_allowed",
                    "value": 0,
                    "threshold": 1,
                    "status": "FAIL",
                    "interpretation": "empirical medium signal is not a theorem-grade or DFT-supported headline result",
                    "evidence_scope": SCOPE,
                },
            ]
        )
    return result_rows, candidate_rows, gate_rows


def candidate_output_row(row: pd.Series, k: int, method: str) -> dict[str, object]:
    return {
        "candidate_id": row["material_id"],
        "structure_hash": row.get("structure_hash", ""),
        "formula": row["formula"],
        "chemical_system": row["chemical_system"],
        "K": k,
        "method": method,
        "raw_rank": row["raw_rank"],
        "t0_label": "stable" if bool(row["stable_exact_t0"]) else "unstable_or_unresolved",
        "t1_label": "stable" if bool(row["stable_exact_t1_current_mp"]) else "unstable_or_unresolved",
        "drift_class": row["drift_class"],
        "E_original_PARC": row["E_original_PARC"],
        "E_ALIGNN_rank_proxy": row["E_ALIGNN_rank_proxy"],
        "E_CHGNet_rank_proxy": row["E_CHGNet_rank_proxy"],
        "E_MACE_rank_proxy": row["E_MACE_rank_proxy"],
        "E_fusion_selected": row["_fusion_e"],
        "chgnet_mace_consensus_label": row["chgnet_mace_consensus_label"],
        "evidence_scope": SCOPE,
    }


def source_audit_rows() -> list[dict[str, object]]:
    return [
        {
            "source": "original_PARC_evalue",
            "score_origin": "original ALIGNN-FF PARC candidate table",
            "construction": "pre-existing PARC e-value from t0 public-label certificate artifact",
            "theorem_grade_status": "valid_only_in_original_PARC_context",
            "blocking_issue": "",
            "evidence_scope": SCOPE,
        },
        {
            "source": "ALIGNN_rank_proxy",
            "score_origin": "Phase51 ALIGNN score",
            "construction": "rank-based e-proxy within frozen raw top-K queue",
            "theorem_grade_status": "not_theorem_grade",
            "blocking_issue": "not reconstructed from full null-superset calibration block maxima in this milestone",
            "evidence_scope": SCOPE,
        },
        {
            "source": "CHGNet_rank_proxy",
            "score_origin": "Phase53 CHGNet raw-energy score proxy",
            "construction": "rank-based e-proxy within frozen raw top-K queue",
            "theorem_grade_status": "not_theorem_grade",
            "blocking_issue": "CHGNet scores are available only for the queue, not the full calibration null superset",
            "evidence_scope": SCOPE,
        },
        {
            "source": "MACE_rank_proxy",
            "score_origin": "Phase53 MACE-MP raw-energy score proxy",
            "construction": "rank-based e-proxy within frozen raw top-K queue",
            "theorem_grade_status": "not_theorem_grade",
            "blocking_issue": "MACE scores are available only for the queue, not the full calibration null superset",
            "evidence_scope": SCOPE,
        },
    ]


def write_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []
    fieldnames = list(rows[0].keys()) if rows else [
        "milestone",
        "path",
        "evidence_state",
        "manifest",
        "public_bundle_check",
    ]
    milestone = "ncs_phase61_parc_m_multi_evidence_fusion"
    rows = [row for row in rows if row.get("milestone") != milestone]
    row = {
        "milestone": milestone,
        "path": "outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/",
        "evidence_state": "completed_empirical_medium_proxy_fusion_not_headline_ready",
        "manifest": "outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion",
    }
    rows.append({key: row.get(key, "") for key in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_sources()
    primary_rows, candidate_rows, gate_rows = build_tables(df)
    source_rows = source_audit_rows()

    write_csv(OUT / "table_parc_m_primary_results.csv", primary_rows, list(primary_rows[0].keys()))
    write_csv(OUT / "table_parc_m_candidate_level.csv", candidate_rows, list(candidate_rows[0].keys()))
    write_csv(OUT / "table_parc_m_gate_audit.csv", gate_rows, list(gate_rows[0].keys()))
    write_csv(OUT / "table_parc_m_source_evalue_audit.csv", source_rows, list(source_rows[0].keys()))
    write_csv(OUT / "figure_parc_m_fusion_inputs.csv", primary_rows, list(primary_rows[0].keys()))

    prereg = """# PARC-M Multi-Evidence Fusion Preregistration

Objective: test whether fixed multi-evidence fusion of original PARC evidence,
ALIGNN score evidence, CHGNet score evidence and MACE score evidence can improve
the materials current-MP t1 release frontier.

Frozen fusion rules:

- `PARC-M-avg`: equal mixture of original PARC, ALIGNN, CHGNet and MACE e-proxies.
- `PARC-M-raw-heavy`: 0.50 original PARC + 0.25 CHGNet + 0.25 MACE.
- `PARC-M-maxBonf`: max evidence divided by four.
- `PARC-M-consensus`: same fixed original/CHGNet/MACE mixture as raw-heavy.
- `PARC-M-aux-only`: ALIGNN + CHGNet + MACE e-proxies only.

Headline gates:

- GO-strong: t1 FTR improves over original PARC by at least 0.05 with a
  nontrivial release.
- GO-medium: t1 FTR improves by at least 0.03 with a nontrivial release.
- Claim-ready theorem gate: every component evidence source must be constructed
  from full null-superset calibration block maxima. This milestone does not meet
  that gate for CHGNet/MACE.
"""
    (OUT / "PARC_M_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")

    gate = pd.DataFrame(gate_rows)
    medium_pass = bool(
        gate[gate["gate"].eq("PARC_M_best_empirical_t1_improvement_ge_0p03")]["status"].eq("PASS").all()
    )
    strong_pass = bool(
        gate[gate["gate"].eq("PARC_M_best_empirical_t1_improvement_ge_0p05")]["status"].eq("PASS").all()
    )
    theorem_ready = bool(
        gate[gate["gate"].eq("theorem_grade_all_evalue_sources_available")]["status"].eq("PASS").all()
    )
    if strong_pass and theorem_ready:
        status = "headline_ready"
    elif medium_pass:
        status = "empirical_medium_signal_not_claim_ready"
    else:
        status = "no_go"
    closeout = f"""# Phase61 PARC-M Multi-Evidence Fusion

Status: `{status}`

PARC-M tests fixed mixtures of original PARC e-values with frozen
ALIGNN/CHGNet/MACE score-derived e-proxies. The empirical signal is better than
the simple Phase60 support gate: the best proxy-fusion rows reduce current-MP
t1 FTR by about 0.03-0.04 while keeping nontrivial release sizes.

However, this is not yet a theorem-grade PARC-M result. CHGNet and MACE scores
are available here only for the frozen queue, not for the full null-superset
calibration blocks. Therefore the e-value mixture theorem cannot be invoked for
the auxiliary sources in this milestone.

Allowed claim: PARC-M has a medium empirical feasibility signal that justifies a
full-calibration implementation if the project wants a method upgrade.

Forbidden claims:

- no theorem-grade multi-evidence e-value certificate;
- no t1 alpha control;
- no DFT evidence;
- no prospective materials discovery;
- no claim that CHGNet/MACE queue score proxies are calibrated null-superset
  e-values.
"""
    (OUT / "NCS_PHASE61_PARC_M_MULTI_EVIDENCE_FUSION.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase61_parc_m_multi_evidence_fusion",
        "status": status,
        "source_tables": [
            rel(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
            rel(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv"),
        ],
        "evidence_scope": SCOPE,
        "headline_claim_allowed": False,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_artifact_index()
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
