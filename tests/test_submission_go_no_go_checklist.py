from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "nmi_presubmission_final"


def test_all_required_go_no_go_rows_pass() -> None:
    checklist = pd.read_csv(MILESTONE / "submission_go_no_go_checklist.csv")

    required = {
        "lead_numbers_have_sha256",
        "no_A3_positive_claim",
        "no_prospective_materials_discovery_claim",
        "two_hard_anchors_visible",
        "audited_boundary_not_oversold",
        "source_discordance_scoped_as_stress_test",
        "abstract_contains_release_refuse_language",
        "abstract_does_not_claim_four_domain_success",
        "referee_rationale_balanced",
    }
    assert required.issubset(set(checklist["check_id"]))

    go_required = checklist[checklist["go_required"].astype(bool)]
    assert not go_required.empty
    assert set(go_required["status"]) == {"PASS"}


def test_final_package_manifest_lists_required_files() -> None:
    manifest = (MILESTONE / "MANIFEST_SHA256.txt").read_text(encoding="utf-8")

    for filename in [
        "presubmission_inquiry_final.md",
        "one_page_evidence_table_final.csv",
        "nmi_abstract_presubmission_final.md",
        "editor_cold_read_final.md",
        "submission_go_no_go_checklist.csv",
        "cover_letter_key_positioning.md",
        "forbidden_claims_final.md",
    ]:
        assert filename in manifest

