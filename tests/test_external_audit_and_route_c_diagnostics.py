from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'outputs/milestones/external_blind_audit_packet'
ROUTE_C = ROOT / 'outputs/milestones/route_c_reduced_frontier_panel_diagnostic'


def test_external_audit_packet_templates_are_blind():
    manifest = pd.read_csv(AUDIT / 'external_blind_audit_packet_manifest.csv')
    auditor = pd.read_csv(AUDIT / 'external_blind_auditor_A_template.csv')
    assert len(manifest) == 484
    assert len(auditor) == len(manifest)
    forbidden = {'source_arm', 'score_recorded_in_key_only', 'candidate_rank_recorded_in_key_only'}
    assert forbidden.isdisjoint(auditor.columns)
    assert not any(c.startswith('human_') for c in auditor.columns)
    assert '_true' not in auditor.columns
    assert set(manifest['external_label_status']) == {'pending_not_completed_evidence'}


def test_external_audit_packet_has_release_and_raw_for_both_domains():
    summary = pd.read_csv(AUDIT / 'table_external_blind_audit_packet_summary.csv')
    arms = set(summary['source_arm'])
    assert 'PARC_release_iwildcam_alpha0.20_K50' in arms
    assert 'raw_topK_iwildcam_matched_count' in arms
    assert 'PARC_release_spacenet_prospective_packet' in arms
    assert 'raw_topK_spacenet_matched_count' in arms
    assert summary['completed_positive_evidence'].astype(str).str.lower().eq('false').all()
    integrity = pd.read_csv(AUDIT / 'table_external_blind_audit_packet_integrity.csv')
    assert integrity['status'].astype(str).str.lower().eq('true').all()


def test_external_audit_closeout_is_not_completed_evidence():
    text = (AUDIT / 'EXTERNAL_BLIND_AUDIT_PACKET_CLOSEOUT.md').read_text()
    assert 'not completed audit evidence' in text
    assert 'external auditor labels and adjudication are pending' in text
    rubric = (AUDIT / 'EXTERNAL_BLIND_AUDIT_RUBRIC.md').read_text()
    assert 'Auditors receive only blinded item ids' in rubric
    assert 'do not receive PARC/raw arm' in rubric


def test_route_c_reduced_panel_is_no_go_diagnostic():
    summary = pd.read_csv(ROUTE_C / 'table_route_c_reduced_frontier_panel_summary.csv').iloc[0]
    assert summary['go_no_go'] == 'NO_GO_existing_probe_no_material_F1_ranking_flip'
    assert str(summary['top_model_flip']).lower() == 'false'
    assert str(summary['ordering_flip']).lower() == 'false'
    assert summary['paper_role'] == 'bonus_no_go_diagnostic_only'
    closeout = (ROUTE_C / 'ROUTE_C_REDUCED_FRONTIER_PANEL_DIAGNOSTIC.md').read_text()
    assert 'not a full MP-Alex Route C primary result' in closeout
    assert 'should not be promoted to a headline materials result' in closeout


def test_route_c_scores_are_public_safe_and_have_three_models():
    scores = pd.read_csv(ROUTE_C / 'table_route_c_reduced_panel_scores_public_safe.csv')
    assert set(scores['model']) == {'CHGNet', 'MACE-MP', 'M3GNet'}
    assert {'material_id', 'formula', 'score'}.issubset(scores.columns)
    assert 'structure' not in ''.join(scores.columns).lower()
