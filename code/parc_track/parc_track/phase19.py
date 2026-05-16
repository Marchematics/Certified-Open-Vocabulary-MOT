from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .adapters.datasets import ensure_data_output, write_json


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
SUCCESS_DIR = DATA_ROOT / "outputs/milestones/scientific_release_success_map"

CTC_LEARNED_DIR = DATA_ROOT / "outputs/milestones/scientific_domain_ctc_learned"
CTC_HUMAN_AUDIT_DIR = DATA_ROOT / "outputs/milestones/ctc_strict_human_audit"
MATERIALS_DIR = DATA_ROOT / "outputs/milestones/scientific_domain_materials"
IWILDCAM_DIR = DATA_ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"
SPACENET_REAL_DIR = DATA_ROOT / "outputs/spacenet7_real_audit"
RELEASE_DIAG_DIR = DATA_ROOT / "outputs/milestones/release_story/paper_diagnostics"
MATERIALS_THRESHOLD_PATH = MATERIALS_DIR / "table_materials_stability_threshold_robustness.csv"
MATERIALS_THRESHOLD_VARIANTS_PATH = MATERIALS_DIR / "table_materials_stability_threshold_variant_report.csv"
MATERIALS_GAMMA_PATH = MATERIALS_DIR / "table_materials_gamma_sensitivity.csv"


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=DATA_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def _rel(path: str | Path) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(DATA_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _txt(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _pick(frame: pd.DataFrame, **criteria: Any) -> pd.Series | None:
    if frame.empty:
        return None
    data = frame.copy()
    for key, value in criteria.items():
        if key not in data.columns:
            return None
        if isinstance(value, (list, tuple, set)):
            data = data[data[key].isin(value)]
        elif isinstance(value, float):
            data = data[pd.to_numeric(data[key], errors="coerce").round(10).eq(round(value, 10))]
        else:
            data = data[data[key].astype(str).eq(str(value))]
    if data.empty:
        return None
    return data.iloc[0]


def _write_provenance(path: Path, sources: list[Path], started: float, notes: str = "") -> None:
    existing = [source for source in sources if source.exists()]
    write_json(
        path.with_suffix(path.suffix + ".provenance.json"),
        {
            "table": path.name,
            "repo_commit": _git_commit(),
            "command": "python -m parc_track.cli phase19 success-domain",
            "runtime_sec": round(time.time() - started, 6),
            "source_files": [{"path": _rel(source), "sha256": _sha256(source)} for source in existing],
            "output_sha256": _sha256(path),
            "notes": notes,
        },
    )


def _write_csv(frame: pd.DataFrame, path: Path, sources: list[Path], started: float, notes: str = "") -> Path:
    out = ensure_data_output(path)
    frame.to_csv(out, index=False)
    _write_provenance(out, sources, started, notes)
    return out


def _false_prevented(raw_ftr: float, raw_k: float, parc_ftr: float, parc_release: float) -> float:
    return max(0.0, raw_ftr * raw_k - parc_ftr * parc_release)


def _evidence_rows() -> tuple[pd.DataFrame, list[Path]]:
    ctc_path = CTC_LEARNED_DIR / "table_ctc_learned_strict_alpha010_smallK.csv"
    ctc_neg_path = CTC_LEARNED_DIR / "table_ctc_learned_negative_control.csv"
    ctc_human_summary_path = CTC_HUMAN_AUDIT_DIR / "table_ctc_strict_human_audit_summary.csv"
    ctc_human_gate_path = CTC_HUMAN_AUDIT_DIR / "table_ctc_strict_human_audit_go_no_go.csv"
    mat_path = MATERIALS_DIR / "table_materials_primary_results.csv"
    mat_raw_path = MATERIALS_DIR / "table_materials_raw_topK_baseline.csv"
    mat_modern_path = MATERIALS_DIR / "table_materials_modern_model_sensitivity.csv"
    mat_high_path = MATERIALS_DIR / "table_materials_high_volume_refusal.csv"
    mat_threshold_path = MATERIALS_THRESHOLD_PATH
    iwild_path = IWILDCAM_DIR / "table_iwildcam_human_audit_primary_results.csv"
    iwild_rel_path = IWILDCAM_DIR / "table_iwildcam_release_audit_summary.csv"
    iwild_raw_path = IWILDCAM_DIR / "table_iwildcam_raw_topk_audit_summary.csv"
    iwild_irr_path = IWILDCAM_DIR / "table_iwildcam_second_review_agreement_summary.csv"
    space_k50_path = SPACENET_REAL_DIR / "table_spacenet7_real_audit_k50_completed_summary.csv"
    space_k100_path = SPACENET_REAL_DIR / "table_spacenet7_real_audit_primary_refusal_diagnostics.csv"
    near_path = RELEASE_DIAG_DIR / "table_near_boundary_release_value.csv"

    ctc = _read_csv(ctc_path)
    ctc_neg = _read_csv(ctc_neg_path)
    ctc_human_summary = _read_csv(ctc_human_summary_path)
    ctc_human_gate = _read_csv(ctc_human_gate_path)
    materials = _read_csv(mat_path)
    mat_raw = _read_csv(mat_raw_path)
    mat_modern = _read_csv(mat_modern_path)
    mat_high = _read_csv(mat_high_path)
    mat_threshold = _read_csv(mat_threshold_path)
    iwild = _read_csv(iwild_path)
    iwild_rel = _read_csv(iwild_rel_path)
    iwild_raw = _read_csv(iwild_raw_path)
    iwild_irr = _read_csv(iwild_irr_path)
    space_k50 = _read_csv(space_k50_path)
    space_k100 = _read_csv(space_k100_path)
    near = _read_csv(near_path)

    rows: list[dict[str, Any]] = []

    for k in (100, 300):
        row = _pick(ctc, rho=0.1, alpha=0.1, M=k)
        if row is not None:
            raw = _num(row.get("raw_topM_actual_FTR_mean"))
            ftr = _num(row.get("actual_FTR_mean"))
            rel = _num(row.get("released_mean"))
            rows.append(
                {
                    "domain": "biomedical_cell_tracking",
                    "dataset": "Cell Tracking Challenge",
                    "unit": "adjacent_frame_cell_link",
                    "proposal_source": "sequence_disjoint_learned_hybrid_appearance_linker",
                    "verification_mode": "controlled_partial_verification_masked_GT",
                    "alpha": _num(row.get("alpha")),
                    "K": int(_num(row.get("M"))),
                    "release_status": "strict_success",
                    "non_empty_seeds": int(_num(row.get("nonempty_seeds"))),
                    "total_seeds": int(_num(row.get("seeds"))),
                    "PARC_release_size": rel,
                    "PARC_FTR": ftr,
                    "raw_topK_FTR": raw,
                    "false_releases_prevented_est": _false_prevented(raw, k, ftr, rel),
                    "coverage": "held_out_sequence_partial_verification",
                    "evidence_mass_phi": _num(row.get("best_mass_ratio_mean")),
                    "max_observed_e": _num(row.get("max_observed_e_mean")),
                    "required_e": _num(row.get("required_e")),
                    "empty_block_policy": "coverage_conditional",
                    "block_stress_pass": "reverse_split_and_negative_control_available",
                    "practical_interpretation": "strict alpha=0.10 learned-source cell-link release",
                    "paper_status": "main_flagship",
                }
            )

    ctc_bad = _pick(ctc_neg, alpha=0.1, M=100)
    if ctc_bad is not None:
        rows.append(
            {
                "domain": "biomedical_cell_tracking",
                "dataset": "Cell Tracking Challenge",
                "unit": "adjacent_frame_cell_link",
                "proposal_source": "random_score_negative_control",
                "verification_mode": "controlled_partial_verification_masked_GT",
                "alpha": _num(ctc_bad.get("alpha")),
                "K": int(_num(ctc_bad.get("M"))),
                "release_status": "certified_refusal",
                "non_empty_seeds": int(_num(ctc_bad.get("nonempty_seeds"))),
                "total_seeds": int(_num(ctc_bad.get("seeds"))),
                "PARC_release_size": _num(ctc_bad.get("released_mean")),
                "PARC_FTR": _num(ctc_bad.get("actual_FTR_mean")),
                "raw_topK_FTR": _num(ctc_bad.get("raw_topM_actual_FTR_mean")),
                "false_releases_prevented_est": _false_prevented(_num(ctc_bad.get("raw_topM_actual_FTR_mean")), 100, 0, 0),
                "coverage": "held_out_sequence_partial_verification",
                "evidence_mass_phi": _num(ctc_bad.get("best_mass_ratio_mean")),
                "max_observed_e": _num(ctc_bad.get("max_observed_e_mean")),
                "required_e": _num(ctc_bad.get("required_e")),
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": "negative_control_refused",
                "practical_interpretation": "PARC refuses uninformative learned ranking",
                "paper_status": "control",
            }
        )

    if not ctc_human_summary.empty:
        release_row = _pick(ctc_human_summary, queue="simulated_strict_release")
        gate_row = ctc_human_gate.iloc[0] if not ctc_human_gate.empty else None
        if release_row is not None:
            rows.append(
                {
                    "domain": "biomedical_cell_tracking",
                    "dataset": "Cell Tracking Challenge",
                    "unit": "adjacent_frame_cell_link",
                    "proposal_source": "sequence_disjoint_learned_hybrid_appearance_linker",
                    "verification_mode": "human_confirmed_release_queue_audit",
                    "alpha": _num(gate_row.get("required_human_FTR_max") if gate_row is not None else 0.10),
                    "K": int(_num(release_row.get("rows"))),
                    "release_status": "strict_release_queue_human_audit_pass",
                    "non_empty_seeds": "",
                    "total_seeds": "",
                    "PARC_release_size": _num(release_row.get("rows")),
                    "PARC_FTR": _num(release_row.get("human_FTR_false_only")),
                    "conservative_PARC_FTR": _num(release_row.get("human_FTR_uncertain_as_false")),
                    "raw_topK_FTR": 0.0,
                    "false_releases_prevented_est": 0.0,
                    "coverage": "human_confirmed_release_queue_plus_calibration_review",
                    "evidence_mass_phi": "",
                    "max_observed_e": "",
                    "required_e": 10.0,
                    "empty_block_policy": "coverage_conditional",
                    "block_stress_pass": "human_confirmed_release_queue_FTR_0",
                    "practical_interpretation": "human-confirmed CTC strict release queue; no separate expert-audit claim",
                    "paper_status": "human_audit_closeout",
                }
            )

    mat = _pick(materials, rho=0.1, alpha=0.1, K=100)
    if mat is not None:
        raw_row = _pick(mat_raw, proposal_source=mat.get("proposal_source"), K=100)
        raw = _num(raw_row.get("raw_topK_actual_FTR") if raw_row is not None else mat.get("raw_topK_actual_FTR_mean"))
        ftr = _num(mat.get("actual_FTR_mean"))
        rel = _num(mat.get("mean_release"))
        rows.append(
            {
                "domain": "materials_discovery",
                "dataset": "Matbench Discovery WBM",
                "unit": "crystal_stability_candidate",
                "proposal_source": mat.get("proposal_source"),
                "verification_mode": "controlled_partial_DFT_positive_masking",
                "alpha": _num(mat.get("alpha")),
                "K": int(_num(mat.get("K"))),
                "release_status": "strict_success",
                "non_empty_seeds": int(_num(mat.get("non_empty_seeds"))),
                "total_seeds": int(_num(mat.get("seeds"))),
                "PARC_release_size": rel,
                "PARC_FTR": ftr,
                "raw_topK_FTR": raw,
                "false_releases_prevented_est": _false_prevented(raw, 100, ftr, rel),
                "coverage": _num(mat.get("block_coverage_mean")),
                "evidence_mass_phi": _num(mat.get("best_mass_ratio_mean")),
                "max_observed_e": _num(mat.get("max_observed_e_mean")),
                "required_e": _num(mat.get("required_e")),
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": "composition_family_sensitivity_available",
                "practical_interpretation": "strict stable-material candidate release",
                "paper_status": "main_flagship",
            }
        )

    for k in (300, 500):
        row = _pick(mat_modern, alpha=0.1, K=k)
        if row is not None:
            raw = _num(row.get("raw_topK_actual_FTR_mean"))
            ftr = _num(row.get("actual_FTR_mean"))
            rel = _num(row.get("mean_release"))
            rows.append(
                {
                    "domain": "materials_discovery",
                    "dataset": "Matbench Discovery WBM",
                    "unit": "crystal_stability_candidate",
                    "proposal_source": row.get("proposal_source"),
                    "verification_mode": "controlled_partial_DFT_positive_masking",
                    "alpha": _num(row.get("alpha")),
                    "K": int(_num(row.get("K"))),
                    "release_status": "strict_success",
                    "non_empty_seeds": int(_num(row.get("non_empty_seeds"))),
                    "total_seeds": int(_num(row.get("seeds"))),
                    "PARC_release_size": rel,
                    "PARC_FTR": ftr,
                    "raw_topK_FTR": raw,
                    "false_releases_prevented_est": _false_prevented(raw, k, ftr, rel),
                    "coverage": _num(row.get("block_coverage_mean")),
                    "evidence_mass_phi": _num(row.get("best_mass_ratio_mean")),
                    "max_observed_e": _num(row.get("max_observed_e_mean")),
                    "required_e": _num(row.get("required_e")),
                    "empty_block_policy": "coverage_conditional",
                    "block_stress_pass": "modern_model_sensitivity",
                    "practical_interpretation": "modern learned materials source sensitivity",
                    "paper_status": "co_primary_practical_benefit",
                }
            )

    high = _pick(mat_high, rho=0.1, alpha=0.1, K=5000)
    if high is not None:
        rows.append(
            {
                "domain": "materials_discovery",
                "dataset": "Matbench Discovery WBM",
                "unit": "crystal_stability_candidate",
                "proposal_source": high.get("proposal_source"),
                "verification_mode": "controlled_partial_DFT_positive_masking",
                "alpha": _num(high.get("alpha")),
                "K": int(_num(high.get("K"))),
                "release_status": "certified_refusal",
                "non_empty_seeds": int(_num(high.get("non_empty_seeds"))),
                "total_seeds": int(_num(high.get("seeds"))),
                "PARC_release_size": _num(high.get("mean_release")),
                "PARC_FTR": _num(high.get("actual_FTR_mean")),
                "raw_topK_FTR": _num(high.get("raw_topK_actual_FTR_mean")),
                "false_releases_prevented_est": _false_prevented(_num(high.get("raw_topK_actual_FTR_mean")), 5000, 0, 0),
                "coverage": _num(high.get("block_coverage_mean")),
                "evidence_mass_phi": _num(high.get("best_mass_ratio_mean")),
                "max_observed_e": _num(high.get("max_observed_e_mean")),
                "required_e": _num(high.get("required_e")),
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": "unsafe_high_volume_refused",
                "practical_interpretation": "high-volume raw materials release guarded by certified refusal",
                "paper_status": "safety_guardrail",
            }
        )

    if not mat_threshold.empty:
        selected_threshold = mat_threshold[
            (mat_threshold["alpha"].astype(float).round(10) == 0.1)
            & (mat_threshold["rho"].astype(float).round(10) == 0.1)
            & (mat_threshold["K"].astype(int).isin([100, 300]))
            & (mat_threshold["variant"].isin(["tolerance_positive_25meV", "margin_excluded_25meV", "conservative_clear_stable_observed_25meV"]))
        ].copy()
        for _, row in selected_threshold.iterrows():
            k = int(_num(row.get("K")))
            raw = _num(row.get("raw_topK_actual_FTR_mean"))
            ftr = _num(row.get("actual_FTR_mean"))
            rel = _num(row.get("mean_release"))
            rows.append(
                {
                    "domain": "materials_discovery",
                    "dataset": "Matbench Discovery WBM",
                    "unit": "crystal_stability_candidate",
                    "proposal_source": row.get("proposal_source"),
                    "verification_mode": "materials_boundary_threshold_rerun",
                    "alpha": _num(row.get("alpha")),
                    "K": k,
                    "release_status": row.get("robustness_interpretation"),
                    "non_empty_seeds": int(_num(row.get("non_empty_seeds"))),
                    "total_seeds": int(_num(row.get("seeds"))),
                    "PARC_release_size": rel,
                    "PARC_FTR": ftr,
                    "raw_topK_FTR": raw,
                    "false_releases_prevented_est": _false_prevented(raw, k, ftr, rel),
                    "coverage": _num(row.get("block_coverage_mean")),
                    "evidence_mass_phi": _num(row.get("best_mass_ratio_mean")),
                    "max_observed_e": _num(row.get("max_observed_e_mean")),
                    "required_e": _num(row.get("required_e")),
                    "empty_block_policy": "coverage_conditional",
                    "block_stress_pass": row.get("variant"),
                    "practical_interpretation": "materials stability-threshold and boundary-label robustness",
                    "paper_status": "materials_threshold_robustness",
                }
            )

    iw = _pick(iwild, alpha=0.2, K=50)
    iw_rel = _pick(iwild_rel, endpoint_alpha=0.2, endpoint_K=50)
    iw_raw = iwild_raw.iloc[0] if not iwild_raw.empty else None
    if iw is not None:
        raw = _num(iw_raw.get("human_FTR") if iw_raw is not None else iw.get("mean_raw_topK_official_proxy_FTR"))
        ftr = _num(iw_rel.get("human_FTR") if iw_rel is not None else iw.get("human_FTR"))
        conservative = _num(iw_rel.get("conservative_human_FTR") if iw_rel is not None else iw.get("conservative_human_FTR"))
        irr = iwild_irr.iloc[0] if not iwild_irr.empty else None
        rows.append(
            {
                "domain": "ecological_camera_traps",
                "dataset": "iWildCam camera-trap subset",
                "unit": "animal_present_detection_box",
                "proposal_source": iw.get("source_name"),
                "verification_mode": "real_human_partial_audit",
                "alpha": _num(iw.get("alpha")),
                "K": int(_num(iw.get("K"))),
                "release_status": "operational_success_not_strict_alpha010",
                "non_empty_seeds": int(_num(iw.get("non_empty_seeds"))),
                "total_seeds": 20,
                "PARC_release_size": _num(iw.get("mean_release")),
                "PARC_FTR": ftr,
                "conservative_PARC_FTR": conservative,
                "raw_topK_FTR": raw,
                "false_releases_prevented_est": _false_prevented(raw, 50, ftr, _num(iw.get("mean_release"))),
                "coverage": "camera_location_x_temporal_chunk",
                "evidence_mass_phi": _num(iw.get("mean_best_mass_ratio")),
                "max_observed_e": _num(iw.get("max_observed_e")),
                "required_e": _num(iw.get("required_e")),
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": "human_second_review_kappa_" + (str(round(_num(irr.get("cohen_kappa")), 3)) if irr is not None else "missing"),
                "practical_interpretation": "real-audit ecological operational release at alpha=0.20; strict alpha=0.10 refused",
                "paper_status": "operational_real_audit",
            }
        )

    sp50 = space_k50.iloc[0] if not space_k50.empty else None
    if sp50 is not None:
        rows.append(
            {
                "domain": "earth_observation",
                "dataset": "SpaceNet 7",
                "unit": "same_building_temporal_link",
                "proposal_source": "geometry_building_linker",
                "verification_mode": "real_human_release_audit_diagnostic",
                "alpha": _num(sp50.get("alpha")),
                "K": int(_num(sp50.get("K"))),
                "release_status": "diagnostic_low_volume_success",
                "non_empty_seeds": int(_num(sp50.get("non_empty_seeds"))),
                "total_seeds": int(_num(sp50.get("total_seeds"))),
                "PARC_release_size": _num(sp50.get("mean_release_across_seeds")),
                "PARC_FTR": _num(sp50.get("audited_FTR_uncertain_as_false")),
                "raw_topK_FTR": "",
                "false_releases_prevented_est": "",
                "coverage": "AOI_time_blocks",
                "evidence_mass_phi": _num(sp50.get("mean_mass_ratio")),
                "max_observed_e": "",
                "required_e": "",
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": "K50_human_confirmed_but_not_primary",
                "practical_interpretation": "real-audit low-volume diagnostic release; K=100 primary refused",
                "paper_status": "diagnostic_not_primary",
            }
        )

    sp100 = space_k100.iloc[0] if not space_k100.empty else None
    if sp100 is not None:
        rows.append(
            {
                "domain": "earth_observation",
                "dataset": "SpaceNet 7",
                "unit": "same_building_temporal_link",
                "proposal_source": "geometry_building_linker",
                "verification_mode": "real_human_partial_audit_initial_review",
                "alpha": _num(sp100.get("alpha")),
                "K": int(_num(sp100.get("K"))),
                "release_status": "certified_refusal",
                "non_empty_seeds": int(_num(sp100.get("non_empty_seeds"))),
                "total_seeds": int(_num(sp100.get("total_seeds"))),
                "PARC_release_size": 0,
                "PARC_FTR": 0,
                "raw_topK_FTR": "",
                "false_releases_prevented_est": "",
                "coverage": "AOI_time_blocks",
                "evidence_mass_phi": _num(sp100.get("mean_best_mass_ratio")),
                "max_observed_e": _num(sp100.get("mean_max_observed_e")),
                "required_e": _num(sp100.get("required_e")),
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": "primary_real_audit_refusal",
                "practical_interpretation": "real-audit K=100 request refused because mass ratio remains below one",
                "paper_status": "refusal_diagnostic",
            }
        )

    # Preserve near-boundary rows as a practical-benefit panel without duplicating every seed row.
    for _, row in near.head(6).iterrows():
        rows.append(
            {
                "domain": _txt(row.get("domain")).lower().replace(" ", "_"),
                "dataset": row.get("dataset"),
                "unit": "candidate_release",
                "proposal_source": row.get("proposal_source"),
                "verification_mode": "existing_near_boundary_panel",
                "alpha": _num(row.get("alpha")),
                "K": int(_num(row.get("K"))),
                "release_status": row.get("near_boundary_status"),
                "non_empty_seeds": int(_num(row.get("PARC_non_empty_seeds"))),
                "total_seeds": int(_num(row.get("seeds"))),
                "PARC_release_size": _num(row.get("PARC_release_size")),
                "PARC_FTR": _num(row.get("PARC_FTR")),
                "raw_topK_FTR": _num(row.get("raw_topK_FTR")),
                "false_releases_prevented_est": _false_prevented(
                    _num(row.get("raw_topK_FTR")),
                    _num(row.get("K")),
                    _num(row.get("PARC_FTR")),
                    _num(row.get("PARC_release_size")),
                ),
                "coverage": "see_source_table",
                "evidence_mass_phi": _num(row.get("best_mass_ratio")),
                "max_observed_e": "",
                "required_e": "",
                "empty_block_policy": "coverage_conditional",
                "block_stress_pass": row.get("paper_use"),
                "practical_interpretation": row.get("practice_benefit_claim"),
                "paper_status": "near_boundary_practical_value",
            }
        )

    sources = [
        ctc_path,
        ctc_neg_path,
        ctc_human_summary_path,
        ctc_human_gate_path,
        mat_path,
        mat_raw_path,
        mat_modern_path,
        mat_high_path,
        mat_threshold_path,
        iwild_path,
        iwild_rel_path,
        iwild_raw_path,
        iwild_irr_path,
        space_k50_path,
        space_k100_path,
        near_path,
    ]
    return pd.DataFrame(rows), sources


def _success_feature_tables(evidence: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if evidence.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    features = evidence.copy()
    features["release_success_binary"] = features["release_status"].astype(str).str.contains("success|release", case=False, regex=True) & (
        pd.to_numeric(features["PARC_release_size"], errors="coerce").fillna(0) > 0
    )
    features["risk_success_binary"] = pd.to_numeric(features["PARC_FTR"], errors="coerce").fillna(0) <= pd.to_numeric(
        features["alpha"], errors="coerce"
    ).fillna(0)
    features["phi_ge_1"] = pd.to_numeric(features["evidence_mass_phi"], errors="coerce").fillna(0) >= 1
    features["max_e_ge_required"] = pd.to_numeric(features["max_observed_e"], errors="coerce").fillna(-1) >= pd.to_numeric(
        features["required_e"], errors="coerce"
    ).fillna(float("inf"))
    features["raw_minus_parc_FTR"] = pd.to_numeric(features["raw_topK_FTR"], errors="coerce") - pd.to_numeric(
        features["PARC_FTR"], errors="coerce"
    )
    features = features[
        [
            "domain",
            "dataset",
            "proposal_source",
            "verification_mode",
            "alpha",
            "K",
            "release_status",
            "PARC_release_size",
            "PARC_FTR",
            "raw_topK_FTR",
            "raw_minus_parc_FTR",
            "evidence_mass_phi",
            "phi_ge_1",
            "max_observed_e",
            "required_e",
            "max_e_ge_required",
            "coverage",
            "block_stress_pass",
            "release_success_binary",
            "risk_success_binary",
            "paper_status",
        ]
    ]

    checklist = pd.DataFrame(
        [
            {
                "condition": "one_sided_positive_reliability",
                "diagnostic": "human/GT verified positives must be high precision; uncertain/disputed rows stay unverified",
                "success_signal": "audit agreement acceptable and no false verified positives in checked subset",
                "failure_action": "tighten positive rule or downgrade row to assumption-boundary diagnostic",
            },
            {
                "condition": "covered_exchangeable_blocks",
                "diagnostic": "covered block rate and leave-block-family-out sensitivity",
                "success_signal": "release/refusal conclusion stable under domain-respecting block perturbations",
                "failure_action": "report covered-regime claim only or add block-balanced audit",
            },
            {
                "condition": "sufficient_evidence_mass",
                "diagnostic": "evidence_mass_phi = alpha * k * E_(k) / K",
                "success_signal": "phi >= 1 for at least one compatible release volume",
                "failure_action": "lower K, increase verified-positive audit budget, or certify refusal",
            },
            {
                "condition": "finite_resolution",
                "diagnostic": "max_observed_e >= required_e",
                "success_signal": "single-candidate evidence can cross the target threshold",
                "failure_action": "increase calibration denominator or relax the operating point; do not claim release",
            },
            {
                "condition": "manageable_conflicts",
                "diagnostic": "compatibility graph density and SCS-vs-ILP diagnostic",
                "success_signal": "SCS release close to feasible-compatible frontier",
                "failure_action": "report graph-conflict power loss; use ILP only as diagnostic unless preregistered",
            },
        ]
    )

    grouped = (
        features.assign(
            parc_release_numeric=pd.to_numeric(features["PARC_release_size"], errors="coerce"),
            parc_ftr_numeric=pd.to_numeric(features["PARC_FTR"], errors="coerce"),
            raw_ftr_numeric=pd.to_numeric(features["raw_topK_FTR"], errors="coerce"),
            phi_numeric=pd.to_numeric(features["evidence_mass_phi"], errors="coerce"),
        )
        .groupby("domain", dropna=False)
        .agg(
            n_rows=("domain", "size"),
            n_release_success=("release_success_binary", "sum"),
            mean_PARCl_release=("parc_release_numeric", "mean"),
            mean_PARCl_FTR=("parc_ftr_numeric", "mean"),
            mean_raw_topK_FTR=("raw_ftr_numeric", "mean"),
            max_phi=("phi_numeric", "max"),
        )
        .reset_index()
    )
    grouped = grouped.rename(columns={"mean_PARCl_release": "mean_PARC_release", "mean_PARCl_FTR": "mean_PARC_FTR"})
    return features, grouped, checklist


def _protocol_gap_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ctc_human_gate_path = CTC_HUMAN_AUDIT_DIR / "table_ctc_strict_human_audit_go_no_go.csv"
    ctc_completed = False
    if ctc_human_gate_path.exists():
        gate = _read_csv(ctc_human_gate_path)
        ctc_completed = (not gate.empty) and gate["decision"].astype(str).str.lower().eq("go").any()
    strict_audit = pd.DataFrame(
        [
            {
                "protocol": "ctc_strict_alpha010_human_audit",
                "status": "completed_human_confirmed_release_queue_audit"
                if ctc_completed
                else "requires_new_human_or_expert_audit",
                "purpose": "confirm CTC learned-hybrid strict alpha=0.10 release/candidate queues by human review; rerun PARC with human positives before claiming a fully prospective calibration audit",
                "frozen_source": "sequence-disjoint learned-hybrid appearance linker",
                "primary_endpoint": "alpha=0.10, K in {100,300}",
                "pass_gate": "human-confirmed release queue FTR <= alpha; uncertain rows counted conservatively; calibration positives kept one-sided",
                "paper_use_before_completion": "human-confirmed closeout evidence"
                if ctc_completed
                else "protocol_only_not_evidence",
            },
            {
                "protocol": "iwildcam_strict_alpha010_audit_expansion",
                "status": "optional_extension",
                "purpose": "test whether additional block-balanced animal-present audit can move ecology from alpha=0.20 operational success to alpha=0.10 strict release",
                "frozen_source": "animal-present detector candidate universe",
                "primary_endpoint": "alpha=0.10, K in {25,50}",
                "pass_gate": ">=18/20 non-empty seeds and conservative human FTR <= 0.10",
                "paper_use_before_completion": "audit-budget sensitivity protocol",
            },
        ]
    )

    variant_report = _read_csv(MATERIALS_THRESHOLD_VARIANTS_PATH)
    robustness = _read_csv(MATERIALS_THRESHOLD_PATH)
    if not variant_report.empty and not robustness.empty:
        rows = []
        for _, variant in variant_report.iterrows():
            subset = robustness[robustness["variant"].astype(str).eq(str(variant.get("variant")))]
            for source, source_rows in subset.groupby("proposal_source", dropna=False):
                strict_rows = source_rows[
                    (pd.to_numeric(source_rows["alpha"], errors="coerce").round(10) == 0.1)
                    & (pd.to_numeric(source_rows["K"], errors="coerce").isin([100, 300]))
                ]
                k100 = strict_rows[pd.to_numeric(strict_rows["K"], errors="coerce").eq(100)]
                k300 = strict_rows[pd.to_numeric(strict_rows["K"], errors="coerce").eq(300)]
                rows.append(
                    {
                        "analysis": variant.get("variant"),
                        "proposal_source": source,
                        "threshold_eV_per_atom": 0.025 if "25meV" in str(variant.get("variant")) else 0.0,
                        "status": "completed_rerun",
                        "positive_rule": variant.get("description"),
                        "n_candidates": int(_num(variant.get("n_candidates"))),
                        "n_observed_label_positive": int(_num(variant.get("n_observed_label_positive"))),
                        "n_eval_label_positive": int(_num(variant.get("n_eval_label_positive"))),
                        "strict_alpha010_K100_FTR": float(pd.to_numeric(k100["actual_FTR_mean"], errors="coerce").iloc[0])
                        if not k100.empty
                        else "",
                        "strict_alpha010_K300_FTR": float(pd.to_numeric(k300["actual_FTR_mean"], errors="coerce").iloc[0])
                        if not k300.empty
                        else "",
                        "paper_use": "completed materials boundary/threshold robustness evidence",
                    }
                )
        materials_threshold = pd.DataFrame(rows)
    else:
        materials_threshold = pd.DataFrame(
            [
                {
                    "analysis": "exact_stable_primary",
                    "threshold_eV_per_atom": 0.0,
                    "status": "completed_in_existing_primary_tables",
                    "positive_rule": "e_above_hull <= 0",
                    "paper_use": "main strict materials evidence",
                },
                {
                    "analysis": "tolerance_positive_25meV",
                    "threshold_eV_per_atom": 0.025,
                    "status": "requires_rerun",
                    "positive_rule": "e_above_hull <= 25 meV/atom",
                    "paper_use": "robustness_sensitivity_after_rerun",
                },
                {
                    "analysis": "margin_excluded_25meV",
                    "threshold_eV_per_atom": 0.025,
                    "status": "requires_rerun",
                    "positive_rule": "exclude |e_above_hull| <= 25 meV/atom before FTR",
                    "paper_use": "boundary-label-uncertainty sensitivity after rerun",
                },
                {
                    "analysis": "conservative_strict_boundary_as_unverified",
                    "threshold_eV_per_atom": 0.0,
                    "status": "requires_rerun",
                    "positive_rule": "only clearly stable positives enter A=1; near-boundary labels remain unsupported",
                    "paper_use": "one-sided precision robustness after rerun",
                },
            ]
        )

    new_domain = pd.DataFrame(
        [
            {
                "candidate_domain": "molecular_hit_release",
                "candidate_unit": "molecule_target_candidate",
                "one_sided_positive": "experimentally confirmed active hit",
                "block_rule": "Bemis-Murcko scaffold x target family or assay batch x scaffold family",
                "primary_endpoint": "alpha=0.10, K in {50,100}",
                "current_status": "not_started",
                "minimal_artifact_needed": "candidate universe with frozen scores, assay labels for held-out evaluation, partial-positive mask protocol",
                "paper_use": "future third-domain extension; not claimed in current results",
            },
            {
                "candidate_domain": "protein_variant_function_release",
                "candidate_unit": "protein_variant",
                "one_sided_positive": "experimentally confirmed functional variant",
                "block_rule": "protein family x mutation-neighborhood",
                "primary_endpoint": "alpha=0.10, K in {50,100}",
                "current_status": "backup_not_started",
                "minimal_artifact_needed": "variant library labels, frozen score model, family-aware blocks",
                "paper_use": "future extension only",
            },
        ]
    )
    return strict_audit, materials_threshold, new_domain


def _write_report(
    out_dir: Path,
    evidence: pd.DataFrame,
    grouped: pd.DataFrame,
    generated: list[Path],
    started: float,
) -> Path:
    report = ensure_data_output(out_dir / "SUCCESS_DOMAIN_CLOSEOUT.md")
    n_main = int(evidence["paper_status"].astype(str).eq("main_flagship").sum()) if not evidence.empty else 0
    n_controls = int(evidence["paper_status"].astype(str).str.contains("control|refusal|guardrail|diagnostic", case=False).sum()) if not evidence.empty else 0
    report.write_text(
        "# Release-Certification Success-Domain Closeout\n\n"
        "This artifact reframes cross-domain generality as a domain-of-success map rather than a claim that PARC releases in every domain. "
        "Rows are reportable only when the source table already contains completed evidence; proposed future audits and new domains are explicitly marked as protocol-only.\n\n"
        "## Summary\n\n"
        f"- Main flagship evidence rows: {n_main}\n"
        f"- Control/refusal/diagnostic rows: {n_controls}\n"
        f"- Generated tables: {len(generated)}\n\n"
        "## Paper-facing claim\n\n"
        "PARC is a general release-certification interface for finite scientific AI candidate universes under one-sided partial verification. "
        "It releases when reliable one-sided positives, covered exchangeable blocks, sufficient evidence mass, and manageable compatibility conflicts are present; it refuses otherwise.\n\n"
        "## Generated artifacts\n\n"
        + "\n".join(f"- `{_rel(path)}`" for path in generated)
        + "\n\n## Guardrails\n\n"
        "- CTC and materials strict rows are controlled partial-verification results unless a real human/experimental audit is completed.\n"
        "- Materials threshold and fixed-gamma sensitivity rows are completed reruns when the corresponding tables are present in `scientific_domain_materials`.\n"
        "- iWildCam is the current real-human-audit operational release row; strict alpha=0.10 remains refusal unless additional audit coverage changes the evidence mass.\n"
        "- SpaceNet K=50 remains diagnostic, while K=100 real-audit primary request is a certified refusal.\n"
        "- Molecular/protein domains are protocol-only here and must not be cited as completed evidence.\n",
        encoding="utf-8",
    )
    _write_provenance(report, generated, started, "markdown closeout over generated success-domain tables")
    return report


def run_phase19_success_domain(output_dir: str | None = None) -> dict[str, Any]:
    started = time.time()
    out_dir = ensure_data_output(Path(output_dir) if output_dir else SUCCESS_DIR)

    evidence, evidence_sources = _evidence_rows()
    features, grouped, checklist = _success_feature_tables(evidence)
    strict_audit, materials_threshold, new_domain = _protocol_gap_tables()

    generated: list[Path] = []
    generated.append(
        _write_csv(
            evidence,
            out_dir / "table_cross_domain_evidence_matrix.csv",
            evidence_sources,
            started,
            "Cross-domain evidence matrix assembled from completed source tables only.",
        )
    )
    generated.append(
        _write_csv(
            features,
            out_dir / "table_success_domain_features.csv",
            evidence_sources,
            started,
            "Normalized success-domain features for release/refusal diagnostics.",
        )
    )
    generated.append(
        _write_csv(
            grouped,
            out_dir / "table_success_domain_summary_by_domain.csv",
            evidence_sources,
            started,
            "Domain-level aggregation for paper discussion.",
        )
    )
    generated.append(
        _write_csv(
            checklist,
            out_dir / "table_practitioner_success_checklist.csv",
            [],
            started,
            "Practitioner checklist distilled from the PARC success-domain theory.",
        )
    )
    generated.append(
        _write_csv(
            strict_audit,
            out_dir / "table_strict_real_audit_protocols.csv",
            [],
            started,
            "Protocol-only rows for strict alpha=0.10 real/human partial verification.",
        )
    )
    generated.append(
        _write_csv(
            materials_threshold,
            out_dir / "table_materials_stability_threshold_robustness_plan.csv",
            [MATERIALS_THRESHOLD_PATH, MATERIALS_THRESHOLD_VARIANTS_PATH],
            started,
            "Materials threshold robustness status; completed rows are backed by actual rerun tables when available.",
        )
    )
    threshold = _read_csv(MATERIALS_THRESHOLD_PATH)
    if not threshold.empty:
        generated.append(
            _write_csv(
                threshold,
                out_dir / "table_materials_stability_threshold_robustness.csv",
                [MATERIALS_THRESHOLD_PATH],
                started,
                "Completed materials threshold and boundary-label robustness rerun.",
            )
        )
    gamma_sensitivity = _read_csv(MATERIALS_GAMMA_PATH)
    if not gamma_sensitivity.empty:
        generated.append(
            _write_csv(
                gamma_sensitivity,
                out_dir / "table_materials_gamma_sensitivity.csv",
                [MATERIALS_GAMMA_PATH],
                started,
                "Completed fixed-gamma sensitivity grid for materials release rows.",
            )
        )
    generated.append(
        _write_csv(
            new_domain,
            out_dir / "table_candidate_new_domain_protocols.csv",
            [],
            started,
            "Future non-visual/non-material domains; protocol-only.",
        )
    )

    assumption_path = RELEASE_DIAG_DIR / "table_assumption_diagnostic_panel.csv"
    assumption = _read_csv(assumption_path)
    if not assumption.empty:
        generated.append(
            _write_csv(
                assumption,
                out_dir / "table_block_coverage_exchangeability_diagnostics.csv",
                [assumption_path],
                started,
                "Copied existing assumption-diagnostic panel into success-domain milestone.",
            )
        )

    near_path = RELEASE_DIAG_DIR / "table_near_boundary_release_value.csv"
    near = _read_csv(near_path)
    if not near.empty:
        generated.append(
            _write_csv(
                near,
                out_dir / "table_near_boundary_practical_value.csv",
                [near_path],
                started,
                "Near-boundary release value table with raw vs PARC FTR and baseline frontiers.",
            )
        )

    contamination_path = RELEASE_DIAG_DIR / "table_ctc_audit_contamination_sensitivity.csv"
    contamination = _read_csv(contamination_path)
    if not contamination.empty:
        generated.append(
            _write_csv(
                contamination,
                out_dir / "table_audit_contamination_sensitivity.csv",
                [contamination_path],
                started,
                "Audit-contamination sensitivity copied into success-domain milestone.",
            )
        )

    report = _write_report(out_dir, evidence, grouped, generated, started)
    generated.append(report)

    manifest_path = out_dir / "success_domain_summary.json"
    manifest_txt = out_dir / "MANIFEST_SHA256.txt"
    generated_with_summary = generated + [manifest_path]
    protocol_only_count = int(
        strict_audit["status"].astype(str).str.contains("requires|optional|not_started|backup", case=False, regex=True).sum()
        + materials_threshold["status"].astype(str).str.contains("requires|optional|not_started|backup", case=False, regex=True).sum()
        + new_domain["current_status"].astype(str).str.contains("requires|optional|not_started|backup", case=False, regex=True).sum()
    )
    manifest = {
        "status": "completed",
        "output_dir": _rel(out_dir),
        "generated_files": [_rel(path) for path in generated_with_summary] + [_rel(manifest_txt)],
        "n_evidence_rows": int(len(evidence)),
        "n_main_flagship_rows": int(evidence["paper_status"].astype(str).eq("main_flagship").sum()) if not evidence.empty else 0,
        "n_protocol_only_rows": protocol_only_count,
        "manifest": _rel(manifest_txt),
    }
    write_json(manifest_path, manifest)

    with ensure_data_output(manifest_txt).open("w", encoding="utf-8") as handle:
        for path in sorted(generated_with_summary):
            if path.exists():
                handle.write(f"{_sha256(path)}  {path.name}\n")
    return manifest
