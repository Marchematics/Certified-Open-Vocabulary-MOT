import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition"


def test_materials_t0_t1_snapshot_outputs_exist() -> None:
    expected = {
        "MATERIALS_T0_T1_SNAPSHOT_ACQUISITION_CLOSEOUT.md",
        "table_t0_wbm_snapshot.csv",
        "table_t1_current_mp_entries_by_chemsys.csv",
        "table_t0_t1_label_join.csv",
        "table_stable_to_unstable_drift.csv",
        "table_t1_hull_ftr_summary.csv",
        "table_t1_hull_ftr_delta.csv",
        "table_t0_t1_gate_assessment.csv",
        "table_snapshot_acquisition_status.csv",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (MILESTONE / name).exists()]
    assert not missing


def test_snapshot_status_records_t0_and_t1_sources_without_local_paths() -> None:
    status = pd.read_csv(MILESTONE / "table_snapshot_acquisition_status.csv")
    assert set(status["snapshot"]) == {"t0_wbm_matbench_discovery", "t1_current_materials_project"}
    assert set(status["status"]) == {"acquired", "acquired_without_API_key_disclosure"}
    text = status.to_csv(index=False)
    assert "/home/waas" not in text
    assert "/root/" not in text
    assert "MP_API_KEY" not in text


def test_t0_t1_join_is_candidate_level_and_finite() -> None:
    joined = pd.read_csv(MILESTONE / "table_t0_t1_label_join.csv")
    assert len(joined) >= 1000
    assert joined["material_id"].is_unique
    required = {
        "e_above_hull_t0",
        "e_above_hull_t1_current_mp",
        "stable_exact_t0",
        "stable_exact_t1_current_mp",
        "t1_label_status",
        "drift_class",
        "K300_PARC_release_seed_count",
        "K300_raw_topK_requested_budget_seed_count",
        "K500_PARC_release_seed_count",
        "K500_raw_topK_requested_budget_seed_count",
    }
    assert required.issubset(joined.columns)
    labelable = joined[joined["t1_label_status"].eq("labelable_current_MP_hull")]
    assert len(labelable) >= 1000
    assert labelable["e_above_hull_t1_current_mp"].notna().all()
    assert set(joined["drift_class"]).issubset(
        {
            "stable_to_stable",
            "stable_to_unstable",
            "stable_to_unresolved",
            "unstable_to_stable",
            "unstable_to_unstable",
            "unstable_to_unresolved",
        }
    )


def test_t1_hull_ftr_tables_cover_parc_and_raw_at_k300_k500() -> None:
    summary = pd.read_csv(MILESTONE / "table_t1_hull_ftr_summary.csv")
    assert set(summary["K"]) == {300, 500}
    assert set(summary["arm"]) == {"PARC_release", "raw_topK"}
    assert summary["n_unique_candidates"].gt(0).all()
    assert summary["FTR_t1_current_mp"].between(0, 1).all()

    delta = pd.read_csv(MILESTONE / "table_t1_hull_ftr_delta.csv")
    assert set(delta["K"]) == {300, 500}
    for column in [
        "PARC_FTR_t1_current_mp",
        "raw_topK_FTR_t1_current_mp",
        "raw_minus_PARC_FTR_t1",
        "PARC_stable_to_unstable_rate",
        "raw_stable_to_unstable_rate",
        "drift_rate_delta_PARC_minus_raw",
    ]:
        assert column in delta.columns
        assert delta[column].notna().all()


def test_gate_assessment_separates_utility_from_strict_alpha_certificate() -> None:
    gates = pd.read_csv(MILESTONE / "table_t0_t1_gate_assessment.csv")
    gate_status = dict(zip(gates["gate"], gates["status"]))
    assert gate_status["PARC_release_lower_t1_FTR_than_raw_topK"] == "PASS"
    assert gate_status["stable_to_unstable_drift_not_concentrated_in_PARC"] == "PASS"
    assert gate_status["strict_alpha010_t1_hull_certificate"] == "FAIL"
    assert (
        gate_status["overall_t0_t1_hull_shift_audit"]
        == "PASS_UTILITY_DRIFT_NO_STRICT_ALPHA_CERTIFICATE"
    )
    text = " ".join(gates["claim"].astype(str)).lower()
    assert "not prospective materials discovery" in text


def test_provenance_and_closeout_preserve_claim_boundaries() -> None:
    provenance = json.loads((MILESTONE / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["evidence_status"] == "completed_t0_t1_hull_shift_acquisition_current_MP_api"
    assert provenance["mp_database_version_t1"]
    assert provenance["n_target_candidates"] >= 1000
    assert "not_prospective_materials_discovery" in provenance["claim_boundary"]
    assert "/home/waas" not in json.dumps(provenance)

    closeout = (MILESTONE / "MATERIALS_T0_T1_SNAPSHOT_ACQUISITION_CLOSEOUT.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "hull-shift audit" in closeout
    assert "not a new dft" in closeout and "calculation" in closeout
    assert "not" in closeout and "prospective" in closeout


def test_no_api_key_or_local_absolute_path_is_written_to_outputs() -> None:
    api_key = os.environ.get("MP_API_KEY", "")
    for path in MILESTONE.rglob("*"):
        if not path.is_file() or path.stat().st_size > 20_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert "/home/waas" not in text, path
        assert "/root/" not in text, path
        assert "MP_API_KEY" not in text, path
        if api_key:
            assert api_key not in text, path
