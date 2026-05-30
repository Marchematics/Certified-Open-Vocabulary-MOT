from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase83_necessity_and_prevented_harm"


def test_phase83_outputs_exist_and_scope_is_synthesis_only() -> None:
    expected = {
        "README_evidence_scope.md",
        "NCS_PHASE83_NECESSITY_AND_PREVENTED_HARM.md",
        "supplement_necessity_and_prevented_harm.tex",
        "table_necessity_principles.csv",
        "table_prevented_scientific_harm.csv",
        "figure_prevented_harm_inputs.csv",
        "table_phase83_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "completed_paperization_synthesis_not_new_empirical_result" in readme
    assert "does not add new human labels" in readme
    assert "not_DFT_evidence" in readme


def test_phase83_necessity_principles_cover_core_non_variant_argument() -> None:
    principles = pd.read_csv(OUT / "table_necessity_principles.csv")
    assert set(principles["principle"]) == {
        "least_favourable_null_superset",
        "refusal_lower_bound",
        "active_audit_gain",
    }
    joined = " ".join(principles["paper_function"].astype(str))
    assert "e-BH variant" in joined
    assert "evidence-supported lifecycle" in joined
    assert principles["scope"].str.contains("not_new_empirical_result").all()

    supplement = (OUT / "supplement_necessity_and_prevented_harm.tex").read_text(encoding="utf-8")
    assert "Least-favourable null-superset principle" in supplement
    assert "Refusal lower bound" in supplement
    assert "Active-audit gain principle" in supplement


def test_phase83_prevented_harm_table_is_cross_domain_and_scoped() -> None:
    harm = pd.read_csv(OUT / "table_prevented_scientific_harm.csv")
    assert {"biomedical_cell_tracking", "materials_screening", "earth_observation"}.issubset(set(harm["domain"]))
    assert len(harm) >= 5
    assert harm["prevented_harm_mean"].ge(0).all()
    assert harm["evidence_scope"].str.contains("not_new_empirical_result").all()
    assert harm["claim_scope"].str.contains("not_prospective_discovery|not_new_labels|not_new_human_audit", regex=True).any()

    materials_5000 = harm[harm["naive_release"].eq("ALIGNN-FF raw top-5000 follow-up queue")].iloc[0]
    assert materials_5000["prevented_harm_mean"] == 2577.4
    ctc_300 = harm[harm["naive_release"].eq("random-score top-300 lineage links")].iloc[0]
    assert ctc_300["prevented_harm_mean"] == 237.0


def test_phase83_claim_gate_ledger_and_claim_table_guardrails() -> None:
    gate = pd.read_csv(OUT / "table_phase83_claim_gate.csv")
    assert len(gate) == 1
    row = gate.iloc[0]
    assert row["status"] == "completed_paperization_synthesis_not_new_empirical_result"
    assert row["positive_evidence"] == "synthesis_only"
    assert "new DFT evidence" in row["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    led = ledger[ledger["claim_id"].eq("NCS-PHASE83-001")]
    assert len(led) == 1
    assert led.iloc[0]["positive_evidence"] == "synthesis_only"
    assert "do_not_claim_new_labels" in led.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase83 Necessity and Prevented Harm" in claim_table
    assert "synthesis only" in claim_table


def test_phase83_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase83-necessity-and-prevented-harm"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_paperization_synthesis_not_new_empirical_result" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase83_necessity_and_prevented_harm"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
