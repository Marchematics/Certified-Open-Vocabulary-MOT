#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_AUDIT = ROOT / 'outputs/milestones/external_blind_audit_packet'
OUT_ROUTE_C = ROOT / 'outputs/milestones/route_c_reduced_frontier_panel_diagnostic'
DISC = Path(os.environ.get('MATERIALS_DISCORDANCE_REPO', ROOT.parent / 'materials-stability-label-discordance'))
DISC_PRE = DISC / 'outputs/milestones/materials_label_discordance_preregistration'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(path: Path) -> None:
    lines = []
    for p in sorted(path.rglob('*')):
        if p.is_file() and p.name != 'MANIFEST_SHA256.txt':
            lines.append(f'{sha256(p)}  {p.relative_to(path).as_posix()}')
    (path / 'MANIFEST_SHA256.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def sample_rows(df: pd.DataFrame, n: int, seed: int, label: str) -> pd.DataFrame:
    if len(df) <= n:
        out = df.copy()
    else:
        out = df.sample(n=n, random_state=seed).sort_values('audit_id').copy()
    out['packet_source_arm'] = label
    return out


def normalize_iwild(df: pd.DataFrame, source_arm: str) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            'source_audit_id': r.get('audit_id'),
            'domain': 'ecological_camera_traps',
            'dataset': 'iWildCam2022',
            'task': 'animal_present_box_review',
            'candidate_unit': 'animal-present detection box',
            'source_arm': source_arm,
            'asset_ref': r.get('path_id'),
            'context_ref': f"location={r.get('location_id')} video={r.get('video_id')} frame={r.get('frame_start')}",
            'audit_question': 'Does the localized candidate show an animal present? label animal / not_animal / uncertain.',
            'support_semantics': r.get('support_semantics'),
            'score_recorded_in_key_only': r.get('score'),
            'candidate_rank_recorded_in_key_only': r.get('candidate_rank'),
            'source_template': source_arm,
        })
    return pd.DataFrame(rows)


def normalize_spacenet(df: pd.DataFrame, source_arm: str) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            'source_audit_id': r.get('audit_id'),
            'domain': 'earth_observation',
            'dataset': 'SpaceNet7',
            'task': 'same_building_temporal_link_review',
            'candidate_unit': 'same-building temporal link',
            'source_arm': source_arm,
            'asset_ref': r.get('path_id'),
            'context_ref': f"aoi={r.get('aoi')} {r.get('source_year')}-{r.get('source_month')}->{r.get('target_year')}-{r.get('target_month')}",
            'audit_question': 'Do the source and target footprints correspond to the same building? label same_building / not_same_building / uncertain.',
            'support_semantics': 'visual_same_building_temporal_link_support',
            'score_recorded_in_key_only': r.get('score'),
            'candidate_rank_recorded_in_key_only': r.get('candidate_rank'),
            'source_template': source_arm,
        })
    return pd.DataFrame(rows)


def build_external_audit_packet() -> None:
    OUT_AUDIT.mkdir(parents=True, exist_ok=True)
    iw = ROOT / 'outputs/milestones/scientific_domain_iwildcam_human_audit'
    sp = ROOT / 'outputs/milestones/scientific_domain_spacenet7_prospective'

    iw_rel = pd.read_csv(iw / 'release_audit_blind_template.csv')
    iw_raw = pd.read_csv(iw / 'raw_topk_audit_blind_template.csv')
    sp_rel = pd.read_csv(sp / 'release_audit_blind_template.csv')
    sp_raw = pd.read_csv(sp / 'raw_topk_audit_blind_template.csv')

    packet = pd.concat([
        normalize_iwild(iw_rel, 'PARC_release_iwildcam_alpha0.20_K50'),
        normalize_iwild(sample_rows(iw_raw, len(iw_rel), 73421, 'raw_topK_iwildcam_matched_count'), 'raw_topK_iwildcam_matched_count'),
        normalize_spacenet(sp_rel, 'PARC_release_spacenet_prospective_packet'),
        normalize_spacenet(sample_rows(sp_raw, len(sp_rel), 73422, 'raw_topK_spacenet_matched_count'), 'raw_topK_spacenet_matched_count'),
    ], ignore_index=True)

    packet = packet.sample(frac=1.0, random_state=20260522).reset_index(drop=True)
    packet.insert(0, 'blinded_item_id', [f'EXTAUD-{i:05d}' for i in range(1, len(packet) + 1)])
    packet['packet_freeze_status'] = 'frozen_before_external_labels'
    packet['external_label_status'] = 'pending_not_completed_evidence'
    packet['asset_locator_status'] = 'requires_restricted_dataset_asset_resolver_raw_media_not_in_public_repo'
    packet['claim_role'] = 'external_blind_audit_packet_not_completed_audit_evidence'

    key_cols = [
        'blinded_item_id', 'source_audit_id', 'domain', 'dataset', 'task', 'candidate_unit', 'source_arm',
        'asset_ref', 'context_ref', 'audit_question', 'support_semantics', 'score_recorded_in_key_only',
        'candidate_rank_recorded_in_key_only', 'packet_freeze_status', 'external_label_status',
        'asset_locator_status', 'claim_role', 'source_template'
    ]
    packet[key_cols].to_csv(OUT_AUDIT / 'external_blind_audit_packet_manifest.csv', index=False)

    auditor_cols = ['blinded_item_id', 'domain', 'dataset', 'task', 'candidate_unit', 'asset_ref', 'context_ref', 'audit_question', 'external_label', 'external_uncertain_reason', 'external_confidence', 'external_reviewer_id', 'external_review_timestamp']
    template = packet[auditor_cols[:8]].copy()
    for c in auditor_cols[8:]:
        template[c] = ''
    template.to_csv(OUT_AUDIT / 'external_blind_auditor_A_template.csv', index=False)
    template.to_csv(OUT_AUDIT / 'external_blind_auditor_B_template.csv', index=False)

    adjudication = packet[['blinded_item_id', 'domain', 'dataset', 'task', 'candidate_unit']].copy()
    for c in ['auditor_A_label', 'auditor_B_label', 'adjudicated_label', 'adjudication_reason', 'conservative_false_release_flag', 'adjudicator_id', 'adjudication_timestamp']:
        adjudication[c] = ''
    adjudication.to_csv(OUT_AUDIT / 'external_blind_adjudication_template.csv', index=False)

    summary = packet.groupby(['domain', 'dataset', 'task', 'source_arm']).size().reset_index(name='n_items')
    summary['external_labels_completed'] = False
    summary['completed_positive_evidence'] = False
    summary['paper_role'] = 'audit_ready_packet_only'
    summary.to_csv(OUT_AUDIT / 'table_external_blind_audit_packet_summary.csv', index=False)

    checks = [
        {'invariant': 'auditor_templates_do_not_include_source_arm', 'status': str('source_arm' not in template.columns)},
        {'invariant': 'auditor_templates_do_not_include_scores', 'status': str(not any('score' in c for c in template.columns))},
        {'invariant': 'auditor_templates_do_not_include_existing_human_labels', 'status': str(not any(c.startswith('human_') for c in template.columns))},
        {'invariant': 'spacenet_hidden_true_not_exported', 'status': str('_true' not in template.columns and '_true' not in packet.columns)},
        {'invariant': 'external_labels_pending', 'status': 'True'},
    ]
    pd.DataFrame(checks).to_csv(OUT_AUDIT / 'table_external_blind_audit_packet_integrity.csv', index=False)

    (OUT_AUDIT / 'EXTERNAL_BLIND_AUDIT_RUBRIC.md').write_text(
        '# External Blind Audit Rubric\n\n'
        'Status: frozen audit packet, not completed audit evidence.\n\n'
        'Auditors receive only blinded item ids, dataset/task context, asset references, and the audit question. They do not receive PARC/raw arm, score, rank, existing human labels, official labels, or DFT/benchmark truth.\n\n'
        'Allowed labels:\n\n'
        '- iWildCam animal-present boxes: `animal`, `not_animal`, `uncertain`.\n'
        '- SpaceNet7 temporal links: `same_building`, `not_same_building`, `uncertain`.\n\n'
        'Conservative adjudication policy: disagreements and uncertain labels are counted as false/unsupported for conservative FTR unless adjudicated otherwise with a recorded reason.\n\n'
        'Raw media are not redistributed in this public-safe repository. External auditors require a restricted dataset asset resolver keyed by `asset_ref`.\n',
        encoding='utf-8',
    )
    (OUT_AUDIT / 'EXTERNAL_BLIND_AUDIT_PACKET_CLOSEOUT.md').write_text(
        '# External Blind Audit Packet\n\n'
        f'This milestone freezes `{len(packet)}` blinded audit items spanning iWildCam and SpaceNet7 release/raw comparators. It is audit-ready but not completed audit evidence because external auditor labels and adjudication are pending.\n\n'
        'Claim boundary: no new primary human-audit claim is made from this packet until labels are returned, adjudicated, and summarized under the conservative policy.\n',
        encoding='utf-8',
    )
    provenance = {
        'status': 'external_blind_audit_packet_frozen_labels_pending',
        'randomization_seed': 20260522,
        'iwildcam_release_template_sha256': sha256(iw / 'release_audit_blind_template.csv'),
        'iwildcam_raw_template_sha256': sha256(iw / 'raw_topk_audit_blind_template.csv'),
        'spacenet_release_template_sha256': sha256(sp / 'release_audit_blind_template.csv'),
        'spacenet_raw_template_sha256': sha256(sp / 'raw_topk_audit_blind_template.csv'),
        'no_completed_external_labels': True,
        'not_primary_evidence_until_labels_return': True,
    }
    (OUT_AUDIT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    write_manifest(OUT_AUDIT)


def build_route_c() -> None:
    OUT_ROUTE_C.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(DISC_PRE / 'table_route_c_existing_probe_ranking_metrics.csv')
    flips = pd.read_csv(DISC_PRE / 'table_route_c_existing_probe_flip_summary.csv')
    scores = pd.read_csv(DISC_PRE / 'table_route_c_existing_probe_model_scores.csv')
    gate = pd.read_csv(DISC_PRE / 'table_route_c_go_no_go_gate.csv')
    protocol = pd.read_csv(DISC_PRE / 'table_route_c_frontier_panel_protocol.csv')

    metrics.assign(
        source_artifact='external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_route_c_existing_probe_ranking_metrics.csv',
        source_sha256=sha256(DISC_PRE / 'table_route_c_existing_probe_ranking_metrics.csv'),
        paper_role='route_c_reduced_frontier_panel_diagnostic_only',
    ).to_csv(OUT_ROUTE_C / 'table_route_c_reduced_panel_model_metrics.csv', index=False)
    flips.assign(
        source_artifact='external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_route_c_existing_probe_flip_summary.csv',
        source_sha256=sha256(DISC_PRE / 'table_route_c_existing_probe_flip_summary.csv'),
        paper_role='completed_no_go_diagnostic_not_headline',
    ).to_csv(OUT_ROUTE_C / 'table_route_c_reduced_panel_flip_summary.csv', index=False)

    # Keep scores public-safe: identifiers/formulas/scores only, no structures.
    scores.assign(
        paper_role='public_safe_score_snapshot_diagnostic_only'
    ).to_csv(OUT_ROUTE_C / 'table_route_c_reduced_panel_scores_public_safe.csv', index=False)
    gate.to_csv(OUT_ROUTE_C / 'table_route_c_reduced_panel_go_no_go_gate.csv', index=False)
    protocol.to_csv(OUT_ROUTE_C / 'table_route_c_reduced_panel_protocol.csv', index=False)

    summary = flips.iloc[0].to_dict()
    rows = [{
        'diagnostic': 'Route_C_plus_existing_probe_reduced_frontier_panel',
        'n_common': int(summary['n_common_floor']),
        'models_eligible': summary['models_eligible'],
        'top_model_flip': bool(summary['top_model_flip']),
        'ordering_flip': bool(summary['ordering_flip']),
        'max_abs_F1_delta': float(summary['max_abs_F1_delta']),
        'go_no_go': summary['go_no_go'],
        'claim_scope': summary['claim_scope'],
        'paper_role': 'bonus_no_go_diagnostic_only',
    }]
    pd.DataFrame(rows).to_csv(OUT_ROUTE_C / 'table_route_c_reduced_frontier_panel_summary.csv', index=False)

    (OUT_ROUTE_C / 'ROUTE_C_REDUCED_FRONTIER_PANEL_DIAGNOSTIC.md').write_text(
        '# Route C+ Reduced Frontier Panel Diagnostic\n\n'
        'Status: completed no-go diagnostic from the existing WBM-vs-alex probe, not a full MP-Alex Route C primary result.\n\n'
        f"The reduced panel scored `{summary['n_common_floor']}` common structures with `{summary['models_eligible']}`. The maximum absolute stable-F1 delta was `{float(summary['max_abs_F1_delta']):.4f}`, but top-model flip and ordering flip were both false. Decision: `{summary['go_no_go']}`.\n\n"
        'Claim boundary: this is optional bonus diagnostic evidence only. It should not be promoted to a headline materials result or used to revive A3.\n',
        encoding='utf-8',
    )
    provenance = {
        'status': 'completed_route_c_reduced_panel_no_go_diagnostic',
        'source_repo': 'Marchematics/materials-stability-label-discordance',
        'metrics_sha256': sha256(DISC_PRE / 'table_route_c_existing_probe_ranking_metrics.csv'),
        'flip_summary_sha256': sha256(DISC_PRE / 'table_route_c_existing_probe_flip_summary.csv'),
        'not_full_MP_Alex_route_c_primary': True,
        'not_headline_positive_evidence': True,
    }
    (OUT_ROUTE_C / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    write_manifest(OUT_ROUTE_C)


def main() -> None:
    build_external_audit_packet()
    build_route_c()


if __name__ == '__main__':
    main()
