from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "cross_domain_blind_audit_main_evidence"


def test_cross_domain_audit_primary_rows_have_blind_labels() -> None:
    primary = pd.read_csv(MILESTONE / "table_cross_domain_audit_primary.csv")

    assert {"iWildCam", "SpaceNet7"}.issubset(set(primary["dataset"]))
    promoted = primary[primary["main_text_role"].isin(["primary_main_evidence", "secondary_main_evidence"])]
    assert promoted["blind_audit_labels_present"].astype(bool).all()
    assert (promoted["conservative_audited_FTR"].astype(float) <= promoted["alpha"].astype(float)).all()

    iwildcam = primary[(primary["dataset"] == "iWildCam") & (primary["main_text_role"] == "primary_main_evidence")]
    assert len(iwildcam) == 1
    assert int(iwildcam["audited_released_n"].iloc[0]) == 167
    assert bool(iwildcam["second_review_present"].iloc[0])


def test_cross_domain_agreement_reports_iwildcam_kappa() -> None:
    agreement = pd.read_csv(MILESTONE / "table_cross_domain_agreement.csv")
    iw = agreement[agreement["dataset"] == "iWildCam"].iloc[0]

    assert int(iw["n_rows"]) == 1123
    assert float(iw["cohen_kappa"]) >= 0.80
    assert float(iw["label_agreement"]) > 0.90
