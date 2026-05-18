import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "nmi_presubmission_final"


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def test_final_presubmission_inquiry_word_count_and_scope() -> None:
    text = (MILESTONE / "presubmission_inquiry_final.md").read_text(encoding="utf-8")
    words = count_words(text)

    assert 600 <= words <= 750
    assert "release-time certification" in text or "release/refuse" in text
    assert "prospective materials discovery is not claimed" in text
    assert "A3 positive evidence" not in text
    assert "not positive independent validation" in text


def test_final_evidence_table_roles_and_provenance() -> None:
    table = pd.read_csv(MILESTONE / "one_page_evidence_table_final.csv")

    assert {"hard_anchor", "audited_boundary", "source_discordance_stress_test", "pending_optional_extension"}.issubset(
        set(table["final_role"])
    )
    assert table["source_artifact"].astype(str).str.len().gt(0).all()
    assert table["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()

    stress = table[table["final_role"].eq("source_discordance_stress_test")]
    assert not stress.empty
    assert stress["parc_decision"].astype(str).str.contains("not positive independent validation").all()

    a3 = table[table["final_role"].eq("pending_optional_extension")]
    assert len(a3) == 1
    assert "pending" in a3["parc_decision"].iloc[0]
    assert "positive evidence" in a3["lead_consequence"].iloc[0]


def test_final_abstract_has_release_refuse_and_no_prospective_discovery_claim() -> None:
    text = (MILESTONE / "nmi_abstract_presubmission_final.md").read_text(encoding="utf-8")

    assert "release-time certification" in text or "refuse" in text
    assert "without claiming prospective discovery" in text
    assert "four-domain success" not in text.lower()
    assert "new materials discovered" not in text.lower()
