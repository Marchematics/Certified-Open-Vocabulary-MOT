from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSITIONING = ROOT / "docs" / "nmi_submission_positioning.md"


def test_nmi_positioning_defines_what_the_paper_is() -> None:
    text = POSITIONING.read_text(encoding="utf-8")

    assert "Release-time certification" in text
    assert "Scientific AI governance" in text
    assert "one-sided partial verification" in text
    assert "certified release set or a certified refusal" in text


def test_nmi_positioning_defines_what_the_paper_is_not() -> None:
    text = POSITIONING.read_text(encoding="utf-8")

    assert "Not prospective materials discovery unless A3 DFT gates are met" in text
    assert "Not a new materials generator" in text
    assert "Not a pure e-BH theory paper" in text
    assert "Not a claim that external materials databases are interchangeable stability labels" in text
    assert "universal scientific-discovery guarantee" in text

