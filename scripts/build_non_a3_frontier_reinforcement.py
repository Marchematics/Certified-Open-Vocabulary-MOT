#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DISC = Path(os.environ.get('MATERIALS_DISCORDANCE_REPO', ROOT.parent / 'materials-stability-label-discordance'))
DISC_FULL = DISC / 'outputs/milestones/materials_label_discordance_full_mp_alex_43984'
DISC_PRE = DISC / 'outputs/milestones/materials_label_discordance_preregistration'

PLAN_OUT = ROOT / 'outputs/milestones/non_a3_frontier_reinforcement_redesign'
ATLAS_OUT = ROOT / 'outputs/milestones/materials_label_source_discordance_atlas'
OVERLAY_OUT = ROOT / 'outputs/milestones/materials_source_uncertainty_refusal_layer'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(path: Path) -> None:
    rows = []
    for p in sorted(path.rglob('*')):
        if p.is_file() and p.name != 'MANIFEST_SHA256.txt':
            rows.append(f'{sha256(p)}  {p.relative_to(path).as_posix()}')
    (path / 'MANIFEST_SHA256.txt').write_text('\n'.join(rows) + '\n', encoding='utf-8')


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return math.nan, math.nan
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def ensure_dirs() -> None:
    for p in [PLAN_OUT, ATLAS_OUT, OVERLAY_OUT]:
        p.mkdir(parents=True, exist_ok=True)


def build_plan() -> None:
    rows = [
        {
            'path_id': 'materials_label_source_discordance_atlas',
            'positioning': 'frontier_benchmark_reliability_result',
            'two_week_feasibility': 'very_high',
            'main_text_value': 'high',
            'risk_level': 'low',
            'evidence_status': 'completed_public_data_artifact_available',
            'next_action': 'promote full MP-Alex exact-match denominator into paper-facing atlas',
            'claim_boundary': 'not prospective discovery; not PARC independent validation success',
        },
        {
            'path_id': 'materials_source_uncertainty_refusal_layer',
            'positioning': 'release_governance_overlay_or_feasibility_gate',
            'two_week_feasibility': 'medium_high',
            'main_text_value': 'high_if_candidate_level_join_available',
            'risk_level': 'medium_low',
            'evidence_status': 'candidate_level_PARC_material_ids_not_in_public_aggregate_tables',
            'next_action': 'audit whether PARC material release queues expose candidate ids for MP-Alex exact-match join',
            'claim_boundary': 'scenario/feasibility only unless candidate-level join is completed',
        },
        {
            'path_id': 'external_blind_audit_package',
            'positioning': 'reviewer_trust_upgrade',
            'two_week_feasibility': 'medium_high_if_auditors_available',
            'main_text_value': 'very_high',
            'risk_level': 'medium',
            'evidence_status': 'not_started_in_this_builder',
            'next_action': 'freeze non-author blind-audit packets for iWildCam and SpaceNet',
            'claim_boundary': 'operational audit envelope; not universal strict success',
        },
        {
            'path_id': 'route_c_plus_reduced_frontier_panel',
            'positioning': 'optional_bonus',
            'two_week_feasibility': 'medium',
            'main_text_value': 'medium_high_if_flip_or_large_delta',
            'risk_level': 'medium_high',
            'evidence_status': 'optional_pilot_only',
            'next_action': 'run only after atlas/overlay/audit paths are secured',
            'claim_boundary': 'diagnostic unless preregistered gate passes',
        },
    ]
    pd.DataFrame(rows).to_csv(PLAN_OUT / 'table_non_a3_frontier_path_priorities.csv', index=False)
    gates = [
        {'gate': 'A3_removed_from_headline', 'status': 'required', 'acceptance': 'A3 may appear only as failed/pending/diagnostic unless DFT gates pass'},
        {'gate': 'full_mp_alex_atlas_completed', 'status': 'completed_by_source_repo', 'acceptance': '43139 strict matches and 5060 discordant exact-stability labels reproduced from source artifact'},
        {'gate': 'PARC_queue_candidate_level_overlay', 'status': 'blocked_pending_candidate_ids', 'acceptance': 'requires material_id/prototype id for released and raw candidates'},
        {'gate': 'external_blind_audit', 'status': 'pending', 'acceptance': 'non-author blind labels and agreement/adjudication table'},
    ]
    pd.DataFrame(gates).to_csv(PLAN_OUT / 'table_non_a3_go_no_go.csv', index=False)
    (PLAN_OUT / 'NON_A3_FRONTIER_REINFORCEMENT_PLAN.md').write_text(
        '# PARC Non-A3 Frontier Reinforcement Plan\n\n'
        'Status: active redesign plan. A3 is not used as a headline-positive evidence route.\n\n'
        'Priority order:\n\n'
        '1. Promote the completed public MP-Alex exact-match discordance denominator into a paper-facing materials benchmark-reliability atlas.\n'
        '2. Attempt a source-uncertainty release/refusal overlay only if candidate-level PARC materials identifiers are available; otherwise report a blocked feasibility gate.\n'
        '3. Freeze independent blind audit packets for iWildCam and SpaceNet as the main trust upgrade.\n'
        '4. Treat Route C+ reduced frontier model panel as optional bonus only.\n\n'
        'Claim boundary: no prospective materials discovery, no positive OQMD/alex-mp independent validation claim, and no A3 positive claim unless DFT gates are met.\n',
        encoding='utf-8',
    )
    provenance = {
        'status': 'active_non_A3_redesign_plan',
        'does_not_use_A3_positive_evidence': True,
        'does_not_modify_A3_selection_or_manifests': True,
        'source_repos': {
            'PARC': 'Marchematics/PARC-Certified-Open-Vocabulary-MOT',
            'materials_stability_label_discordance': 'Marchematics/materials-stability-label-discordance',
        },
    }
    (PLAN_OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    write_manifest(PLAN_OUT)


def build_atlas() -> None:
    summary = pd.read_csv(DISC_FULL / 'table_full_mp_alex_denominator_summary.csv')
    status = pd.read_csv(DISC_FULL / 'table_full_mp_alex_match_status_counts.csv')
    source_counts = pd.read_csv(DISC_FULL / 'table_full_denominator_source_counts.csv')
    full_matches = pd.read_csv(DISC_FULL / 'table_full_mp_alex_structure_matches.csv')
    bars = pd.read_csv(DISC_PRE / 'table_fig4_reconciliation_bars.csv')
    fig4c = pd.read_csv(DISC_PRE / 'table_fig4c_selection_conditioned_mp_alex.csv')
    near = pd.read_csv(DISC_PRE / 'table_discordance_near_hull_decomposition.csv')

    full = summary.iloc[0]
    full_rate = float(full['discordance_rate'])
    full_n = int(full['strict_structure_matches'])
    full_disc = int(full['discordant_n'])
    lo, hi = wilson(full_disc, full_n)

    rows = [
        {
            'atlas_row': 'full_MP_Alex_identifier_denominator',
            'source_pair': 'Materials_Project_vs_Alexandria_alex_mp_v20',
            'denominator_n': full_n,
            'discordant_n': full_disc,
            'discordance_rate': full_rate,
            'wilson95_low': lo,
            'wilson95_high': hi,
            'relative_to_full_rate': 1.0,
            'paper_role': 'primary_frontier_benchmark_reliability_result',
            'claim_scope': 'public exact-structure MP-Alex stability-label discordance atlas; not PARC validation and not prospective discovery',
            'source_artifact': 'external_discordance_repo::outputs/milestones/materials_label_discordance_full_mp_alex_43984/table_full_mp_alex_denominator_summary.csv',
            'source_sha256': sha256(DISC_FULL / 'table_full_mp_alex_denominator_summary.csv'),
        }
    ]
    for _, row in fig4c.iterrows():
        n = int(row['n_selected'])
        d = int(row['discordant_n'])
        r = float(row['discordance_rate'])
        l, h = wilson(d, n)
        rows.append(
            {
                'atlas_row': row['selection_rule'],
                'source_pair': 'Materials_Project_vs_Alexandria_alex_mp_v20',
                'denominator_n': n,
                'discordant_n': d,
                'discordance_rate': r,
                'wilson95_low': l,
                'wilson95_high': h,
                'relative_to_full_rate': r / full_rate if full_rate else math.nan,
                'paper_role': row['paper_role'],
                'claim_scope': 'selection/source-condition diagnostic from existing discordance artifact; not PARC queue overlay',
                'source_artifact': 'external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_fig4c_selection_conditioned_mp_alex.csv',
                'source_sha256': sha256(DISC_PRE / 'table_fig4c_selection_conditioned_mp_alex.csv'),
            }
        )
    pd.DataFrame(rows).to_csv(ATLAS_OUT / 'table_mp_alex_discordance_atlas_summary.csv', index=False)

    status.assign(
        source_artifact='external_discordance_repo::outputs/milestones/materials_label_discordance_full_mp_alex_43984/table_full_mp_alex_match_status_counts.csv',
        source_sha256=sha256(DISC_FULL / 'table_full_mp_alex_match_status_counts.csv'),
    ).to_csv(ATLAS_OUT / 'table_mp_alex_denominator_status.csv', index=False)
    public_source_counts = source_counts.drop(columns=[c for c in ['source_artifact'] if c in source_counts.columns]).copy()
    public_source_counts['source_artifact'] = 'external_alex_mp_20_snapshot_not_redistributed'
    public_source_counts['source_sha256'] = sha256(DISC_FULL / 'table_full_denominator_source_counts.csv')
    public_source_counts.to_csv(ATLAS_OUT / 'table_mp_alex_source_inventory.csv', index=False)

    near_rows = []
    for _, row in near.iterrows():
        n = int(row['n'])
        d = int(row['discordant_n'])
        r = float(row['discordance_rate'])
        l, h = wilson(d, n)
        near_rows.append(
            {
                'band': row['band'],
                'n': n,
                'discordant_n': d,
                'discordance_rate': r,
                'wilson95_low': l,
                'wilson95_high': h,
                'relative_to_full_rate': r / full_rate if full_rate else math.nan,
                'paper_role': 'near_hull_localization_diagnostic',
                'source_artifact': 'external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_discordance_near_hull_decomposition.csv',
                'source_sha256': sha256(DISC_PRE / 'table_discordance_near_hull_decomposition.csv'),
            }
        )
    pd.DataFrame(near_rows).to_csv(ATLAS_OUT / 'table_mp_alex_near_hull_localization.csv', index=False)

    # Public-safe sampled rows: top discordant examples by |delta e_hull|, no structures.
    m = full_matches[full_matches['match_status'].eq('strict_structure_match')].copy()
    for c in ['mp_stable_exact', 'alex_stable_exact']:
        m[c] = m[c].astype(str).str.lower().eq('true')
    m['discordant'] = m['mp_stable_exact'] != m['alex_stable_exact']
    m['abs_delta_ehull'] = (m['mp_e_above_hull'] - m['alex_e_above_hull']).abs()
    sample = m[m['discordant']].sort_values('abs_delta_ehull', ascending=False).head(100)
    sample[[
        'material_id', 'formula', 'chemical_system', 'mp_e_above_hull', 'alex_e_above_hull',
        'mp_stable_exact', 'alex_stable_exact', 'abs_delta_ehull', 'alex_source_file'
    ]].to_csv(ATLAS_OUT / 'table_mp_alex_top_discordant_examples_public_safe.csv', index=False)

    fig = pd.DataFrame(rows)[['atlas_row', 'denominator_n', 'discordant_n', 'discordance_rate', 'relative_to_full_rate', 'paper_role']]
    fig.to_csv(ATLAS_OUT / 'figure_materials_label_source_discordance_atlas_source.csv', index=False)

    (ATLAS_OUT / 'MATERIALS_LABEL_SOURCE_DISCORDANCE_ATLAS.md').write_text(
        '# Materials Label-Source Discordance Atlas\n\n'
        f'Completed public-data atlas from MP-Alex exact-structure matches. The full denominator contains `{full_n}` strict matches and `{full_disc}` exact-stability disagreements, discordance rate `{full_rate:.4f}`.\n\n'
        'This is a frontier benchmark-reliability result and a source-label uncertainty diagnostic. It is not a positive independent validation of PARC, not a prospective materials-discovery claim, and not evidence that external materials databases are interchangeable ground truth.\n\n'
        'The selected-set rows are imported from the existing discordance artifact to show source-condition sensitivity; they are not a candidate-level PARC release overlay.\n',
        encoding='utf-8',
    )
    provenance = {
        'status': 'completed_public_data_frontier_benchmark_reliability_result',
        'source_repo': 'Marchematics/materials-stability-label-discordance',
        'full_summary_sha256': sha256(DISC_FULL / 'table_full_mp_alex_denominator_summary.csv'),
        'full_matches_sha256': sha256(DISC_FULL / 'table_full_mp_alex_structure_matches.csv'),
        'no_new_DFT': True,
        'no_new_human_labels': True,
        'not_PARC_independent_validation_success': True,
    }
    (ATLAS_OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    write_manifest(ATLAS_OUT)


def build_overlay_feasibility() -> None:
    fixed = pd.read_csv(ROOT / 'outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv')
    atlas = pd.read_csv(ATLAS_OUT / 'table_mp_alex_discordance_atlas_summary.csv')
    full = atlas[atlas['atlas_row'].eq('full_MP_Alex_identifier_denominator')].iloc[0]
    selected = atlas[atlas['atlas_row'].eq('MP_native_exact_stable_release_ehull_le_0')].iloc[0]

    primary = fixed[(fixed['proposal_source'].eq('alignn_ff_modern_learned_materials_model')) & (fixed['alpha'].eq(0.1)) & (fixed['K'].isin([300, 500]))].copy()
    scenario_rows = []
    for _, row in primary.iterrows():
        for source_uncertainty_rate_name, rate in [
            ('full_MP_Alex_denominator_rate', float(full['discordance_rate'])),
            ('MP_native_exact_stable_selected_set_rate', float(selected['discordance_rate'])),
        ]:
            scenario_rows.append(
                {
                    'result_id': row['result_id'],
                    'proposal_source': row['proposal_source'],
                    'alpha': row['alpha'],
                    'K': int(row['K']),
                    'mean_release': row['mean_release'],
                    'raw_unstable_count_mean': row['raw_unstable_count_mean'],
                    'PARC_unstable_count_mean': row['PARC_unstable_count_mean'],
                    'prevented_unstable_followups_mean': row['prevented_unstable_followups_mean'],
                    'source_uncertainty_rate_name': source_uncertainty_rate_name,
                    'source_uncertainty_rate': rate,
                    'expected_source_ambiguous_release_count_scenario': row['mean_release'] * rate,
                    'scenario_only': True,
                    'paper_role': 'scenario_diagnostic_not_candidate_level_overlay',
                    'claim_scope': 'uses aggregate release counts and external discordance rates; not a completed candidate-level PARC queue overlay',
                    'source_artifact': row['source_table'],
                    'source_sha256': row['source_sha256'],
                }
            )
    pd.DataFrame(scenario_rows).to_csv(OVERLAY_OUT / 'table_materials_source_uncertainty_overlay_scenarios.csv', index=False)

    feasibility = [
        {
            'overlay_target': 'PARC_ALIGNN_FF_alpha0.10_K300_K500_candidate_level_source_uncertainty_overlay',
            'candidate_level_material_identifier_available_in_public_PARC_tables': False,
            'public_tables_checked': 'materials_fixed_budget_scientific_utility;fixed_budget_downstream_utility;scientific_domain_materials',
            'completed_candidate_level_overlay': False,
            'status': 'blocked_missing_candidate_level_material_ids_or_MP_ids',
            'allowed_role': 'diagnostic_feasibility_audit_only',
            'next_action': 'rerun/export material release candidate-level tables with stable MP/WBM identifiers before claiming source-aware refusal overlay',
        }
    ]
    pd.DataFrame(feasibility).to_csv(OVERLAY_OUT / 'table_candidate_level_overlay_feasibility.csv', index=False)

    policy = [
        {
            'policy_layer': 'source_uncertainty_warning',
            'rule': 'flag candidate if exact MP-Alex source labels disagree or either source is near hull within 25 meV, when candidate-level exact match exists',
            'status': 'predeclared_policy_template_only',
            'completed_evidence': False,
        },
        {
            'policy_layer': 'source_uncertainty_refusal',
            'rule': 'refuse or route to audit if source-ambiguous fraction exceeds predeclared tolerance in the covered candidate-level release set',
            'status': 'requires_candidate_level_join',
            'completed_evidence': False,
        },
    ]
    pd.DataFrame(policy).to_csv(OVERLAY_OUT / 'table_source_uncertainty_refusal_policy_template.csv', index=False)

    (OVERLAY_OUT / 'MATERIALS_SOURCE_UNCERTAINTY_REFUSAL_LAYER.md').write_text(
        '# Materials Source-Uncertainty Refusal Layer\n\n'
        'Status: feasibility audit plus aggregate scenario diagnostic. This milestone does not claim a completed candidate-level PARC queue overlay because the public PARC material utility tables available here are aggregate seed/row tables and do not expose stable material IDs for released and raw candidates.\n\n'
        'The scenario table combines phase31-approved fixed-budget lead numbers with MP-Alex discordance rates to show the scale of source-label ambiguity that a candidate-level overlay would need to address. It is not a replacement for an exact candidate-level join.\n\n'
        'Claim boundary: diagnostic only; not primary evidence, not independent validation, and not prospective discovery.\n',
        encoding='utf-8',
    )
    provenance = {
        'status': 'candidate_level_overlay_blocked_missing_ids; aggregate_scenario_completed',
        'no_new_DFT': True,
        'no_new_human_labels': True,
        'materials_fixed_budget_source_sha256': sha256(ROOT / 'outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv'),
        'atlas_summary_sha256': sha256(ATLAS_OUT / 'table_mp_alex_discordance_atlas_summary.csv'),
        'claim_boundary': 'not candidate-level overlay evidence',
    }
    (OVERLAY_OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    write_manifest(OVERLAY_OUT)


def main() -> None:
    ensure_dirs()
    build_plan()
    build_atlas()
    build_overlay_feasibility()


if __name__ == '__main__':
    main()
