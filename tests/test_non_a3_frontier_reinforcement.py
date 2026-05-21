from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'outputs/milestones/non_a3_frontier_reinforcement_redesign'
ATLAS = ROOT / 'outputs/milestones/materials_label_source_discordance_atlas'
OVERLAY = ROOT / 'outputs/milestones/materials_source_uncertainty_refusal_layer'


def test_non_a3_plan_forbids_a3_headline():
    text = (PLAN / 'NON_A3_FRONTIER_REINFORCEMENT_PLAN.md').read_text()
    assert 'A3 is not used as a headline-positive evidence route' in text
    assert 'no prospective materials discovery' in text
    gates = pd.read_csv(PLAN / 'table_non_a3_go_no_go.csv')
    assert 'A3_removed_from_headline' in set(gates['gate'])


def test_mp_alex_atlas_full_denominator_counts():
    atlas = pd.read_csv(ATLAS / 'table_mp_alex_discordance_atlas_summary.csv')
    full = atlas[atlas['atlas_row'].eq('full_MP_Alex_identifier_denominator')].iloc[0]
    assert int(full['denominator_n']) == 43139
    assert int(full['discordant_n']) == 5060
    assert abs(float(full['discordance_rate']) - 0.117295) < 1e-6
    assert full['paper_role'] == 'primary_frontier_benchmark_reliability_result'
    assert 'not PARC validation' in full['claim_scope']


def test_selected_set_rows_are_not_parc_queue_overlay():
    atlas = pd.read_csv(ATLAS / 'table_mp_alex_discordance_atlas_summary.csv')
    selected = atlas[atlas['atlas_row'].eq('MP_native_exact_stable_release_ehull_le_0')].iloc[0]
    assert int(selected['denominator_n']) == 124
    assert int(selected['discordant_n']) == 21
    assert float(selected['relative_to_full_rate']) > 1.0
    assert 'not PARC queue overlay' in selected['claim_scope']


def test_near_hull_localization_has_no_discordance_off_boundary():
    near = pd.read_csv(ATLAS / 'table_mp_alex_near_hull_localization.csv')
    neither = near[near['band'].eq('neither_near_hull_25meV')].iloc[0]
    assert int(neither['discordant_n']) == 0
    either = near[near['band'].eq('either_near_hull_25meV')].iloc[0]
    assert int(either['discordant_n']) > 0


def test_source_uncertainty_overlay_is_feasibility_not_completed_claim():
    feasibility = pd.read_csv(OVERLAY / 'table_candidate_level_overlay_feasibility.csv')
    row = feasibility.iloc[0]
    assert row['status'] == 'blocked_missing_candidate_level_material_ids_or_MP_ids'
    assert row['completed_candidate_level_overlay'] in (False, 'False')
    scenarios = pd.read_csv(OVERLAY / 'table_materials_source_uncertainty_overlay_scenarios.csv')
    assert scenarios['scenario_only'].astype(str).str.lower().eq('true').all()
    assert scenarios['paper_role'].eq('scenario_diagnostic_not_candidate_level_overlay').all()
