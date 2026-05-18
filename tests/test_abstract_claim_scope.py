from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "docs" / "abstract_claim_scope.md"


def test_abstract_scope_forbids_prospective_materials_discovery_without_a3_gates() -> None:
    text = SCOPE.read_text(encoding="utf-8")

    assert "Disallowed Oversell Language" in text
    assert "Do not claim prospective materials discovery" in text
    assert "OQMD or alex-mp diagnostics" in text
    assert "CGCNN K=100" in text
    assert "released_n >= 25" in text
    assert "selection_frozen == true" in text
    assert "dft_completed_n >= 25" in text
    assert "primary_FTR <= alpha" in text


def test_abstract_scope_allows_release_or_refuse_but_not_synthesis_claims() -> None:
    text = SCOPE.read_text(encoding="utf-8")

    assert "PARC converts frozen ranked candidate lists into auditable release-or-refuse decisions" in text
    assert "Do not imply experimental synthesis" in text

