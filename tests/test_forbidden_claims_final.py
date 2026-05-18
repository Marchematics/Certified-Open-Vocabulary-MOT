from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "nmi_presubmission_final"


def test_forbidden_claims_have_allowed_replacements() -> None:
    table = pd.read_csv(MILESTONE / "forbidden_claims_final.csv")

    required = {
        "prospective materials discovery before A3 DFT gates",
        "independent materials validation success from OQMD/alex-mp",
        "broad success across all domains",
        "A3 positive evidence while pending",
        "external materials databases as interchangeable ground truth",
        "PARC as a new generator",
    }
    assert required.issubset(set(table["forbidden_claim"]))
    assert table["allowed_replacement"].astype(str).str.len().gt(10).all()


def test_forbidden_claims_markdown_is_explicit() -> None:
    text = (MILESTONE / "forbidden_claims_final.md").read_text(encoding="utf-8")

    assert "prospective materials discovery before A3 DFT gates" in text
    assert "OQMD/alex-mp source-discordance stress tests" in text
    assert "A3 pending optional extension with no positive evidence" in text
    assert "release-time certification layer" in text

