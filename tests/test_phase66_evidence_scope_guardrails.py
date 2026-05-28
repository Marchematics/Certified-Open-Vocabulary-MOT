from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE66 = ROOT / "outputs/milestones/ncs_phase66_certificate_durability"


def test_phase66_readme_forbids_overclaiming() -> None:
    text = (PHASE66 / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "Headline positive current-MP recertification allowed: `false`",
        "no prospective materials discovery",
        "no DFT evidence",
        "no t1 alpha certificate for the old t0 release",
        "no post-hoc K selection using observed t1 FTR",
        "no future-drift guarantee from historical drift tails",
    ]:
        assert phrase in text


def test_phase66_ledger_entries_exist_and_are_scoped() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    rows = ledger[ledger["claim_id"].isin(["DUR-001", "DUR-002", "DUR-003", "DUR-004", "DUR-005"])]
    assert set(rows["claim_id"]) == {"DUR-001", "DUR-002", "DUR-003", "DUR-004", "DUR-005"}
    assert rows["status"].eq("PASS").all()
    assert rows["overclaim_guardrail"].str.contains("do_not|not_|historical|report_all", regex=True).all()
    dur5 = rows[rows["claim_id"].eq("DUR-005")].iloc[0]
    assert dur5["positive_evidence"] == "no"
    assert "no_positive_current_MP_recertification_gate" in dur5["scope"]


def test_phase66_artifact_index_and_public_bundle_validation() -> None:
    artifact_index = pd.read_csv(ROOT / "outputs/artifact_index.csv")
    row = artifact_index[artifact_index["milestone"].eq("ncs_phase66_certificate_durability")]
    assert len(row) == 1
    assert "no_positive_current_MP" in row.iloc[0]["evidence_state"]
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase66_certificate_durability"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
