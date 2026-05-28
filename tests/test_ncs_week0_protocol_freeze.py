from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs/milestones/ncs_week0_protocol_freeze"


def test_week0_protocol_freeze_outputs_exist() -> None:
    expected = {
        "NCS_WEEK0_PROTOCOL_FREEZE.md",
        "NCS_WEEK0_PROTOCOL_FREEZE.pdf",
        "protocol_freeze_timestamp.json",
        "table_frozen_candidate_universe.csv",
        "table_frozen_model_scores.csv",
        "table_frozen_parc_parameters.csv",
        "table_k_alpha_grid.csv",
        "table_block_definitions.csv",
        "table_dft_audit_sampling_scheme.csv",
        "table_temporal_hull_definitions.csv",
        "table_mlip_audit_models.csv",
        "table_ctc_human_audit_guidelines.csv",
        "table_go_no_go_rules.csv",
        "table_external_registration_plan.csv",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (MILESTONE / name).exists()]
    assert not missing
    assert (MILESTONE / "NCS_WEEK0_PROTOCOL_FREEZE.pdf").read_bytes().startswith(b"%PDF-")


def test_frozen_sources_have_sha256_hashes() -> None:
    for name, hash_column in [
        ("table_frozen_candidate_universe.csv", "source_sha256"),
        ("table_frozen_model_scores.csv", "source_sha256"),
        ("table_dft_audit_sampling_scheme.csv", "source_sha256"),
        ("table_ctc_human_audit_guidelines.csv", "source_sha256"),
    ]:
        table = pd.read_csv(MILESTONE / name)
        assert not table.empty
        assert table[hash_column].astype(str).str.fullmatch(r"[0-9a-f]{64}").all(), name


def test_dft_sampling_scheme_is_pre_outcome_and_comparative() -> None:
    table = pd.read_csv(MILESTONE / "table_dft_audit_sampling_scheme.csv")
    assert {"parc_release_full", "raw_topR_matched", "raw_top100_extra_tail"}.issubset(set(table["arm"]))
    assert table["uses_DFT_outcome"].eq("no").all()
    assert table["failure_policy"].str.contains("not-certified-stable|false", case=False, regex=True).all()
    assert table["construction_rule"].str.contains("pre-DFT|pre-DFT|frozen", case=False, regex=True).any()


def test_go_no_go_rules_block_p_hacking_and_overclaim() -> None:
    rules = pd.read_csv(MILESTONE / "table_go_no_go_rules.csv")
    text = " ".join(rules.astype(str).agg(" ".join, axis=1)).lower()
    assert "before comparator-arm freeze" in text
    assert "post" not in rules["claim_if_pass"].str.lower().str.cat(sep=" ")
    assert "prospective materials-discovery" in text
    assert "a3 remains diagnostic/failed gate" in text
    assert "matched raw top-r close is claimed only as certified stopping" in text


def test_external_registration_plan_does_not_fabricate_identifiers() -> None:
    plan = pd.read_csv(MILESTONE / "table_external_registration_plan.csv", keep_default_na=False)
    assert {"OSF", "Zenodo"} == set(plan["registry"])
    assert plan["registration_status"].eq("ready_for_upload_not_uploaded").all()
    assert plan["registration_url"].eq("").all()
    assert plan["doi"].eq("").all()
    assert plan["no_fake_identifier"].astype(str).str.lower().eq("true").all()


def test_mlip_models_are_frozen_before_outcomes() -> None:
    models = pd.read_csv(MILESTONE / "table_mlip_audit_models.csv")
    assert {"CHGNet", "MACE-MP", "ALIGNN-FF"}.issubset(set(models["model"]))
    assert models["post_outcome_selection_allowed"].eq("no").all()
    required = models[models["model"].isin(["CHGNet", "MACE-MP", "ALIGNN-FF"])]
    assert required["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()


def test_ctc_audit_guidelines_are_blind_and_conservative() -> None:
    guidelines = pd.read_csv(MILESTONE / "table_ctc_human_audit_guidelines.csv")
    text = " ".join(guidelines["rule"].astype(str)).lower()
    assert "blind" in text
    assert "uncertain is conservative" in text
    assert "leakage" in text


def test_markdown_states_no_new_positive_evidence() -> None:
    text = (MILESTONE / "NCS_WEEK0_PROTOCOL_FREEZE.md").read_text(encoding="utf-8").lower()
    assert "no dft outcome" in text
    assert "no prospective materials-discovery claim" in text
    assert "no positive independent materials validation claim" in text
    assert "ready-for-upload" in text
