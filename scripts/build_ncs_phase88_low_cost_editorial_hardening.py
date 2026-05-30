#!/usr/bin/env python3
"""Build Phase88 low-cost NCS editorial hardening package.

This is an editor-facing synthesis bundle, not a new experiment. It packages
the low-cost actions that can be done without new labels, DFT, or new domains:
first-screen framing, existing real-audit positioning, Phase83 necessity and
prevented-harm placement, capability contrast, and overclaim guardrails.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase88_low_cost_editorial_hardening"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

PHASE80 = ROOT / "outputs/milestones/ncs_phase80_finding_first_submission_package"
PHASE81 = ROOT / "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"
PHASE83 = ROOT / "outputs/milestones/ncs_phase83_necessity_and_prevented_harm"
PHASE84 = ROOT / "outputs/milestones/ncs_phase84_real_audit_parc_a_replication"

SCOPE = (
    "NCS_phase88_low_cost_editorial_hardening;"
    "editorial_synthesis_only;"
    "no_new_empirical_result;"
    "no_new_human_labels;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_action_matrix() -> None:
    rows = [
        {
            "priority": "high",
            "action": "rewrite_first_screen",
            "artifact": "cover_letter_core.md;intro_first_screen.md;caption_first_lines.md",
            "goal": "define the paper as scientific AI release infrastructure before statistical machinery",
            "time_cost": "2-3 days",
            "new_evidence_required": "no",
            "status": "ready_for_manuscript_edit",
            "guardrail": "do_not_turn_materials_stress_test_into_headline_discovery",
            "evidence_scope": SCOPE,
        },
        {
            "priority": "high",
            "action": "front_existing_real_audit_envelopes",
            "artifact": "phase81_phase83_write_permissions.csv",
            "goal": "make existing human-audit operating envelopes visible without claiming pending Phase81 labels",
            "time_cost": "0.5-1 day",
            "new_evidence_required": "no",
            "status": "ready_with_pending_boundary",
            "guardrail": "do_not_claim_external_CTC_audit_success_until_labels_pass_gate",
            "evidence_scope": SCOPE,
        },
        {
            "priority": "high",
            "action": "front_phase83_necessity_and_prevented_harm",
            "artifact": "editorial_first_screen_package.md",
            "goal": "make the harm object concrete: false lineage edges, unstable follow-ups, false persistence links",
            "time_cost": "1-2 days",
            "new_evidence_required": "no",
            "status": "ready_for_main_text",
            "guardrail": "use_only_completed_prevented_harm_numbers",
            "evidence_scope": SCOPE,
        },
        {
            "priority": "medium_high",
            "action": "insert_capability_table",
            "artifact": "table_editorial_capability_table.csv",
            "goal": "separate release-card lifecycle capability from raw top-K, thresholding, and e-BH selection",
            "time_cost": "1 day",
            "new_evidence_required": "no",
            "status": "ready_for_figure_6_or_extended_data",
            "guardrail": "capability_comparison_not_FTR_leaderboard",
            "evidence_scope": SCOPE,
        },
        {
            "priority": "medium_high",
            "action": "overclaim_scrub",
            "artifact": "table_editorial_overclaim_scrub.csv",
            "goal": "prevent materials, Phase81, and DFT-v2 pending evidence from becoming visible weak claims",
            "time_cost": "0.5-1 day",
            "new_evidence_required": "no",
            "status": "ready_for_claim_audit",
            "guardrail": "pending_evidence_never_used_as_positive_claim",
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(rows).to_csv(OUT / "table_low_cost_action_matrix.csv", index=False)


def write_capability_table() -> None:
    rows = [
        ("finite candidate queue release", "no", "partial", "partial", "yes"),
        ("one-sided verified positives", "no", "weak", "weak", "yes"),
        ("unverified rows retained in null superset", "no", "no", "no", "yes"),
        ("certified refusal state", "no", "weak", "weak", "yes"),
        ("active audit acquisition interface", "no", "no", "no", "yes"),
        ("reference-version expiry", "no", "no", "no", "yes"),
        ("recertification lifecycle", "no", "no", "no", "yes"),
        ("release card with scope guardrails", "no", "no", "no", "yes"),
    ]
    pd.DataFrame(
        [
            {
                "capability": cap,
                "raw_topK": raw,
                "threshold_or_conformal": thresh,
                "eBH_or_evalue_selection": ebh,
                "PARC_release_card_lifecycle": parc,
                "comparison_scope": "capability_comparison_not_equal_target_object",
                "evidence_scope": SCOPE,
            }
            for cap, raw, thresh, ebh, parc in rows
        ]
    ).to_csv(OUT / "table_editorial_capability_table.csv", index=False)


def write_permissions_and_scrub() -> None:
    permissions = [
        {
            "item": "Phase81 external CTC blind audit packet",
            "current_status": "packet_frozen_labels_pending",
            "submission_permission": "internal_ledger_only_until_labels_pass_gate",
            "allowed_sentence": "A frozen external CTC audit packet exists but is not used as positive evidence in this submission.",
            "forbidden_sentence": "External blind audit confirms CTC release.",
            "evidence_scope": SCOPE,
        },
        {
            "item": "Phase83 one-sided necessity",
            "current_status": "completed_synthesis",
            "submission_permission": "main_text_methods_and_discussion",
            "allowed_sentence": "With one-sided verification, unverified candidates must remain possible false releases; refusal is a valid lifecycle state.",
            "forbidden_sentence": "PARC is universally optimal.",
            "evidence_scope": SCOPE,
        },
        {
            "item": "Phase83 prevented harm",
            "current_status": "completed_synthesis_from_completed_artifacts",
            "submission_permission": "cover_letter_figure_caption_discussion",
            "allowed_sentence": "Uncertified top-K release can insert false lineage edges, unstable follow-up candidates, and false persistence links.",
            "forbidden_sentence": "PARC universally improves upstream ranking.",
            "evidence_scope": SCOPE,
        },
        {
            "item": "materials current-reference drift",
            "current_status": "stress_test_and_boundary",
            "submission_permission": "materials_lifecycle_stress_test_only",
            "allowed_sentence": "Materials release cards expire, refuse, or enter risk triage under current-reference drift.",
            "forbidden_sentence": "PARC controls current-MP FTR at alpha or discovers stable materials.",
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(permissions).to_csv(OUT / "table_phase81_phase83_write_permissions.csv", index=False)

    scrub = [
        ("prospective materials discovery", "versioned materials release-card stress test"),
        ("current-MP alpha certificate", "current-reference audit / expiry / triage boundary"),
        ("external CTC audit confirms release", "external CTC audit packet pending labels"),
        ("DFT v2 validates PARC", "DFT v2 checkpoint pending stable_exact outcomes"),
        ("PARC is an e-BH variant with extra tables", "PARC is a release-card lifecycle interface with refusal, audit, expiry, and recertification states"),
    ]
    pd.DataFrame(
        [
            {
                "forbidden_or_risky_phrase": bad,
                "replacement": good,
                "guardrail": "use_replacement_or_delete",
                "evidence_scope": SCOPE,
            }
            for bad, good in scrub
        ]
    ).to_csv(OUT / "table_editorial_overclaim_scrub.csv", index=False)


def write_text_package() -> None:
    cover = """# Cover Letter Core Paragraph

This manuscript addresses a computational-science bottleneck: scientific AI
systems now generate finite candidate queues faster than those candidates can
be exhaustively verified, yet the queues can directly enter downstream
scientific artifacts such as lineage graphs, materials follow-up queues,
building-persistence maps, and ecological records. PARC release cards provide a
release layer between candidate generation and downstream use: under scarce
one-sided verification they record certified release, certified refusal, active
audit, reference-version expiry, recertification, and risk-triage states. The
main positive result shows that targeted one-sided verification can unlock CTC
release at very small audit budgets, while completed consequence tables show
that uncertified top-K release can propagate concrete scientific harms. The
materials experiments are deliberately scoped as reference-drift stress tests,
not as current-reference alpha certificates, prospective discovery, or DFT
validation.
"""
    (OUT / "cover_letter_core.md").write_text(cover, encoding="utf-8")

    intro = """# Introduction First-Screen Replacement

Scientific AI pipelines increasingly produce candidate queues before the
candidates can be fully verified. The missing object is therefore not another
top-K list, but a release card: a versioned record that says which candidates
may enter downstream scientific workflows, when the evidence instead requires
refusal, what targeted audit would change the decision, and when a later
reference update expires the certificate.
"""
    (OUT / "intro_first_screen.md").write_text(intro, encoding="utf-8")

    captions = pd.DataFrame(
        [
            {
                "display_item": "Figure 1",
                "first_caption_sentence": "Release cards, rather than static top-K lists, are the object of computational scientific release under scarce one-sided verification.",
            },
            {
                "display_item": "Figure 2",
                "first_caption_sentence": "Targeted one-sided audit unlocks certified CTC release, whereas same-budget random audit leaves the release unsupported.",
            },
            {
                "display_item": "Figure 3",
                "first_caption_sentence": "Uncertified top-K release changes downstream scientific artifacts, while release cards shrink or refuse unsupported queues.",
            },
            {
                "display_item": "Figure 4",
                "first_caption_sentence": "Materials release cards stop unsafe t0 queues but expire under later reference drift rather than inheriting a new certificate.",
            },
            {
                "display_item": "Figure 5",
                "first_caption_sentence": "Existing human-audit operating envelopes show release/refusal behavior under real partial verification without upgrading pending CTC labels.",
            },
            {
                "display_item": "Figure 6",
                "first_caption_sentence": "PARC differs from ranking, thresholding, and e-value selection baselines by supporting the full release-card lifecycle.",
            },
        ]
    )
    captions["evidence_scope"] = SCOPE
    captions.to_csv(OUT / "table_caption_first_lines.csv", index=False)

    package = """# Phase88 Low-Cost Editorial Hardening

Status: `completed_editorial_synthesis_not_new_evidence`.

Primary use:

1. replace the first-screen NCS framing with release-card infrastructure;
2. move Phase83 necessity and prevented-harm language into the visible story;
3. insert a capability table that separates lifecycle capability from e-BH;
4. keep Phase81, materials, and DFT-v2 inside their allowed evidence scopes.

This package does not add labels, DFT, current-reference verdicts, or any new
positive empirical result.
"""
    (OUT / "NCS_PHASE88_LOW_COST_EDITORIAL_HARDENING.md").write_text(package, encoding="utf-8")


def write_gate_and_docs() -> None:
    gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase88_low_cost_editorial_hardening",
                "status": "completed_editorial_synthesis_not_new_evidence",
                "positive_evidence": "synthesis_only",
                "allowed_current_claim": "Phase88 packages low-cost NCS editorial hardening actions around completed artifacts and explicit guardrails.",
                "forbidden_current_claim": "Do not claim new labels, completed Phase81 external audit, current-MP alpha control, prospective materials discovery, DFT validation, or new empirical evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase88_editorial_claim_gate.csv", index=False)

    readme = f"""# Phase88 Low-Cost Editorial Hardening

Status: `completed_editorial_synthesis_not_new_evidence`.

This is an A-paper submission-package hardening artifact. It packages low-cost
editorial actions only. It does not add new empirical evidence, human labels,
DFT results, or B-line claim-decay evidence.

Inputs checked as existing artifacts:

- `{rel(PHASE80)}`
- `{rel(PHASE81)}`
- `{rel(PHASE83)}`
- `{rel(PHASE84)}`

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")


def update_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase88_low_cost_editorial_hardening",
        "path": "outputs/milestones/ncs_phase88_low_cost_editorial_hardening/",
        "evidence_state": "completed_editorial_synthesis_not_new_evidence",
        "manifest": "outputs/milestones/ncs_phase88_low_cost_editorial_hardening/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase88_low_cost_editorial_hardening",
        "notes": "Low-cost NCS first-screen, capability, Phase81/83 permission, and overclaim hardening package.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "NCS-PHASE88-EDITORIAL-HARDENING-001",
        "claim_text": "Phase88 packages low-cost NCS editorial hardening actions without adding new empirical evidence.",
        "evidence_type": "editorial_synthesis",
        "positive_evidence": "synthesis_only",
        "scope": "not_new_evidence;not_completed_phase81;not_DFT;not_materials_discovery",
        "artifact_path": "outputs/milestones/ncs_phase88_low_cost_editorial_hardening/table_phase88_editorial_claim_gate.csv",
        "hash": sha256_file(OUT / "table_phase88_editorial_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase88-low-cost-editorial-hardening",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_new_labels_or_completed_external_audit",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """
## Phase88 Low-Cost Editorial Hardening

Status: `completed_editorial_synthesis_not_new_evidence`.

Phase88 packages low-cost NCS submission hardening actions: first-screen
release-card framing, Phase83 necessity/prevented-harm placement, lifecycle
capability table, Phase81/83 write-permission boundaries, and overclaim scrub.
It is synthesis only and must not be used as new empirical evidence.
"""
    marker = "## Phase88 Low-Cost Editorial Hardening"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        if next_idx >= 0:
            text = before + "\n" + section + after[next_idx:]
        else:
            text = before + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    for required in [PHASE80, PHASE81, PHASE83, PHASE84]:
        if not required.exists():
            raise FileNotFoundError(f"Required artifact missing: {required}")
    OUT.mkdir(parents=True, exist_ok=True)
    write_action_matrix()
    write_capability_table()
    write_permissions_and_scrub()
    write_text_package()
    write_gate_and_docs()
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase88-a] wrote {rel(OUT)}")
    print("[phase88-a] status=completed_editorial_synthesis_not_new_evidence")


if __name__ == "__main__":
    main()
