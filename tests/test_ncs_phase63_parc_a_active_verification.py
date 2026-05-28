from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE63 = ROOT / "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification"


def test_phase63_outputs_exist() -> None:
    expected = {
        "PARC_A_PREREGISTRATION.md",
        "table_parc_a_primary_gate.csv",
        "table_parc_a_policy_contrast.csv",
        "table_parc_a_seed_rows.csv",
        "table_parc_a_materials_boundary.csv",
        "table_parc_a_claim_gate_audit.csv",
        "figure_parc_a_active_verification_inputs.csv",
        "NCS_PHASE63_PARC_A_CERTIFICATE_DIRECTED_ACTIVE_VERIFICATION.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE63 / name).exists()]


def test_phase63_primary_ctc_gate_is_strong_positive() -> None:
    primary = pd.read_csv(PHASE63 / "table_parc_a_primary_gate.csv")
    row = primary[primary["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    assert row["manuscript_role"] == "primary_method_headline"
    assert row["audit_budget_fraction"] == 0.005
    assert row["safe_seeds"] == 20
    assert row["nonempty_seeds"] == 20
    assert row["total_released"] == 2000
    assert row["total_false_releases"] == 0
    assert row["matched_random_nonempty_seeds"] == 0
    assert row["budget_ratio_vs_full_random"] >= 100


def test_phase63_support_and_materials_boundaries_are_not_overpromoted() -> None:
    primary = pd.read_csv(PHASE63 / "table_parc_a_primary_gate.csv")
    k300 = primary[primary["target_row"].eq("ctc_learned_strict_alpha010_K300")].iloc[0]
    assert k300["manuscript_role"] == "secondary_support"
    assert k300["safe_seeds"] == 19

    materials = pd.read_csv(PHASE63 / "table_parc_a_materials_boundary.csv")
    assert set(materials["manuscript_role"]) == {
        "materials_boundary_secondary_not_primary",
        "calibration_check_not_headline",
    }
    assert materials[materials["target_row"].str.contains("alignn")]["manuscript_role"].eq(
        "materials_boundary_secondary_not_primary"
    ).all()
    assert materials[materials["target_row"].str.contains("cgcnn")]["manuscript_role"].eq(
        "calibration_check_not_headline"
    ).all()


def test_phase63_claim_gate_audit_forbids_materials_discovery_claims() -> None:
    gate = pd.read_csv(PHASE63 / "table_parc_a_claim_gate_audit.csv")
    assert gate["status"].eq("PASS").all()
    assert gate.set_index("gate").loc["materials_rows_not_primary", "value"] == 0
    closeout = (PHASE63 / "NCS_PHASE63_PARC_A_CERTIFICATE_DIRECTED_ACTIVE_VERIFICATION.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "no new human labels",
        "no new DFT",
        "no prospective materials discovery",
        "materials active-audit rows are primary strong-positive evidence",
    ]:
        assert phrase in closeout


def test_phase63_ledger_records_primary_ctc_only_claim() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-PARCA-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "yes"
    assert "primary_CTC_only" in row.iloc[0]["scope"]
    assert "do_not_claim_new_human_labels" in row.iloc[0]["overclaim_guardrail"]


def test_phase63_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase63-parc-a-active-verification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification" in result.stdout
