#!/usr/bin/env python3
"""Build phase33 final NMI presubmission go/no-go package."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "outputs" / "milestones"
PHASE32 = MILESTONES / "nmi_presubmission_package"
OUT = MILESTONES / "nmi_presubmission_final"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def ensure_clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()


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
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def source(path: Path) -> tuple[str, str]:
    return rel(path), sha256_file(path)


def build_inquiry() -> None:
    text = """# Presubmission Inquiry Final

Dear Editors,

We would like to ask whether Nature Machine Intelligence would consider a manuscript on release-time certification for scientific AI candidate pipelines under one-sided partial verification. Scientific AI systems increasingly return ranked lists of candidate objects before exhaustive verification is available: stable-crystal candidates for DFT follow-up, cell-link evidence for lineage reconstruction, and visual detections or temporal links for ecological and geospatial monitoring. In these settings, the immediate deployment question is not only whether an upstream model ranks well. It is whether a frozen candidate list should release a finite subset to downstream scientists, or refuse because the available partial verification is insufficient.

We introduce PARC, a release/refuse interface for finite candidate universes. Given a frozen score, a block structure, and one-sided verified positives, PARC constructs null-superset evidence and returns either a certified release set or a certified refusal. The method is intended as a governance layer around existing scientific AI systems rather than a new generator, a new materials model, or a claim that all unverified candidates can be labelled. The package also includes explicit claim-scope guardrails: protocol-only rows, pending DFT pilots, and discordant external-source diagnostics are not promoted into headline evidence.

The first hard result is in cell tracking. PARC released sequence-disjoint learned cell-link candidates at alpha=0.10 with 20/20 non-empty seeds and zero held-out false-link fraction. In the downstream artifact view, the K=300 release has zero false lineage edges under official ground-truth consequence proxies. Corrupted rankings are refused: a random-score K=300 control avoids 237.00 false lineage edges entering the lineage graph. This makes CTC more than a link-level benchmark row; it shows that the release/refuse decision changes the evidence passed to a scientific artifact.

The second hard result is in materials-discovery follow-up under public DFT labels. For an ALIGNN-FF stability source, PARC changes fixed-budget follow-up queues; prospective materials discovery is not claimed. At K=300, raw top-K FTR is 0.253, PARC FTR is 0.087, and PARC prevents 64.25 unstable follow-ups on average. At K=500, raw top-K FTR is 0.327, PARC FTR is 0.048, and PARC prevents 158.30 unstable follow-ups on average. These numbers come from completed phase31-approved primary-headline artifacts with source SHA256 hashes. The claim is fixed-budget public-DFT utility: PARC determines where to stop releasing candidates under partial evidence.

We also include audited boundary settings. iWildCam provides an operational human-audited ecology release: 167/167 released candidates are animal-present, with second-review reliability reported separately. SpaceNet 7 provides a real-audit release/refusal vignette: the K=100 request is refused, while K=50 is a diagnostic lower-volume release. These rows demonstrate the release/refuse interface under real partial verification, but they are not overstated as four-domain universal success.

Finally, we report negative evidence honestly. OQMD and alex-mp joins are external-source stress tests, not positive independent validation. The alex-mp exact-structure diagnostic improves coverage but shows high WBM/alex-mp discordance, so we do not claim that external materials databases are interchangeable ground truth. The MatterGen/DFT A3 pilot remains a pending optional extension and is not used as positive evidence.

We believe this manuscript fits NMI because it addresses a growing AI-for-science governance problem: how to decide which AI-generated scientific candidates may responsibly enter downstream workflows when verification is partial, one-sided, and expensive. The intended audience is not only readers interested in e-values or conformal risk control, but also researchers building AI systems that generate scientific candidates faster than they can be checked. The presubmission question is therefore whether this release decision is a sufficiently general and timely AI-for-science object for NMI. We would appreciate your view on whether this release-time certification framing, together with completed artifact-level evidence and explicit no-overclaim guardrails, is suitable for a full submission.
"""
    count = word_count(text)
    if not 600 <= count <= 750:
        raise RuntimeError(f"presubmission_inquiry_final.md word count {count} outside [600, 750]")
    (OUT / "presubmission_inquiry_final.md").write_text(text, encoding="utf-8")


def build_final_evidence_table() -> pd.DataFrame:
    phase32 = read_csv(PHASE32 / "one_page_evidence_table.csv")
    stress = read_csv(MILESTONES / "materials_source_discordance_stress_test" / "table_materials_external_source_stress_summary.csv")
    a3_path = MILESTONES / "mattergen_parc_prospective_dft_followup" / "table_v4_freeze_status.csv"
    a3_artifact, a3_hash = source(a3_path)

    rows: list[dict[str, Any]] = []
    for _, row in phase32.iterrows():
        block = str(row["evidence_block"])
        if "Materials fixed-budget" in block or "CTC strict" in block:
            final_role = "hard_anchor"
        elif "iWildCam" in block or "SpaceNet" in block:
            final_role = "audited_boundary"
        elif "external-source" in block:
            final_role = "source_discordance_stress_test"
        else:
            final_role = "audited_boundary"
        if "external-source" not in block:
            rows.append({**row.to_dict(), "final_role": final_role})

    stress_artifact, stress_hash = source(
        MILESTONES / "materials_source_discordance_stress_test" / "table_materials_external_source_stress_summary.csv"
    )
    for _, row in stress.iterrows():
        rows.append(
            {
                "evidence_block": f"Materials external-source diagnostic: {row['source']}",
                "scientific_artifact_or_workflow": "cross-database materials stability-label stress test",
                "verification_regime": f"{row['source']} exact-structure join; formula-only excluded",
                "parc_decision": "stress test only; not positive independent validation",
                "comparator": "raw top-K exact-match subset",
                "lead_consequence": f"PARC matched FTR {float(row['PARC_matched_FTR']):.3f}; WBM/external discordance {float(row['WBM_external_discordance']):.3f}",
                "claim_scope": "external-source discordance stress test; not primary evidence",
                "manuscript_role": "stress_test",
                "source_artifact": stress_artifact,
                "source_sha256": stress_hash,
                "final_role": "source_discordance_stress_test",
            }
        )

    rows.append(
        {
            "evidence_block": "A3 MatterGen prospective DFT pilot",
            "scientific_artifact_or_workflow": "prospective in-silico materials follow-up",
            "verification_regime": "future DFT only if gates are met",
            "parc_decision": "pending; no positive evidence",
            "comparator": "none yet",
            "lead_consequence": "pending optional extension; no positive evidence and not used in presubmission claims",
            "claim_scope": "requires released_n>=25, frozen selection, DFT completed_n>=25, and primary FTR<=alpha",
            "manuscript_role": "pending",
            "source_artifact": a3_artifact,
            "source_sha256": a3_hash,
            "final_role": "pending_optional_extension",
        }
    )
    final = pd.DataFrame(rows)
    final.to_csv(OUT / "one_page_evidence_table_final.csv", index=False)
    return final


def build_abstract() -> None:
    text = """# NMI Abstract Presubmission Final

Scientific AI systems often produce finite ranked candidate lists before exhaustive verification is available. We study the release decision itself: which candidates may enter downstream workflows, and when should an AI system refuse to release any set? PARC is a release-time certification interface for one-sided partial verification over frozen candidate universes. In cell tracking, PARC releases learned cell-link candidates under strict alpha=0.10 and prevents corrupted rankings from entering lineage-graph artifacts. In materials discovery, PARC changes fixed-budget public-DFT follow-up queues from an ALIGNN-FF source, reducing unstable follow-ups at K=300 and K=500 without claiming prospective discovery. Human-audited iWildCam and SpaceNet 7 rows show operational release/refusal behavior under real partial verification. OQMD and alex-mp joins are reported only as source-discordance stress tests. PARC does not improve the upstream model; it governs release under partial evidence.
"""
    (OUT / "nmi_abstract_presubmission_final.md").write_text(text, encoding="utf-8")


def build_cold_read() -> None:
    risks = [
        ("scope risk", "medium", "This may look like a broad reliability claim across many scientific domains.", "Describe the paper as release-time certification for fixed, covered candidate universes under one-sided partial verification.", "Residual risk remains if the abstract sounds like universal scientific-AI reliability."),
        ("incrementality risk", "medium", "A desk editor may see only a technical variant of e-values, conformal prediction, or multiple testing.", "Lead with downstream release/refuse artifacts, then explain the e-value machinery as implementation.", "Residual risk remains with reviewers routed only to theory."),
        ("lack-of-prospective-discovery risk", "high", "The materials result is public-label fixed-budget utility, not prospective new materials discovery.", "State that prospective materials discovery is not claimed unless A3 DFT gates are met.", "This is the largest NMI risk if the editor expects a discovery paper."),
        ("breadth oversell risk", "medium", "The paper may appear to claim four-domain success when iWildCam and SpaceNet are boundary/audit rows.", "Use two hard anchors plus audited boundary settings, not four equal flagship successes.", "Residual risk remains if figures make secondary rows look like co-primary wins."),
        ("materials overclaim risk", "high", "Materials reviewers may object to treating external databases as ground truth or calling the replay prospective.", "Use fixed-budget public-DFT utility and source-discordance stress-test language.", "Residual risk remains because materials labels are known to be database- and workflow-sensitive."),
        ("reviewer routing risk", "medium", "Pure e-BH theorists or pure materials specialists may miss the release-certification object.", "Ask for reviewers in AI-for-science reliability, applied risk control, and downstream scientific workflow evaluation.", "Residual risk remains if one domain specialist treats other domains as distractions."),
    ]
    text = "# Editor Cold Read Final\n\n"
    for risk, level, objection, mitigation, residual in risks:
        text += f"## {risk}\n\n"
        text += f"- risk_level: {level}\n"
        text += f"- likely_editor_objection: {objection}\n"
        text += f"- mitigation_sentence: {mitigation}\n"
        text += f"- residual_risk: {residual}\n\n"
    (OUT / "editor_cold_read_final.md").write_text(text, encoding="utf-8")


def build_forbidden_claims() -> pd.DataFrame:
    rows = [
        ("prospective materials discovery before A3 DFT gates", "fixed-budget public-DFT follow-up utility; prospective DFT pilot pending"),
        ("independent materials validation success from OQMD/alex-mp", "OQMD/alex-mp source-discordance stress tests"),
        ("broad success across all domains", "two hard anchors plus audited boundary settings and diagnostics"),
        ("A3 positive evidence while pending", "A3 pending optional extension with no positive evidence"),
        ("external materials databases as interchangeable ground truth", "external databases are label-source stress tests with discordance"),
        ("PARC as a new generator", "PARC as a release-time certification layer around frozen upstream sources"),
    ]
    frame = pd.DataFrame(rows, columns=["forbidden_claim", "allowed_replacement"])
    frame.to_csv(OUT / "forbidden_claims_final.csv", index=False)
    text = "# Forbidden Claims Final\n\n"
    for forbidden, replacement in rows:
        text += f"- Forbidden: {forbidden}\n  Allowed replacement: {replacement}\n"
    (OUT / "forbidden_claims_final.md").write_text(text, encoding="utf-8")
    return frame


def build_cover_letter_positioning() -> None:
    text = """# Cover Letter Key Positioning

The manuscript addresses release-time certification for scientific AI candidate pipelines. The central contribution is a release/refuse interface for frozen candidate universes under one-sided partial verification, not a new generator and not a claim of prospective materials discovery.

The two hard anchors are CTC artifact consequence and materials fixed-budget public-DFT utility. CTC demonstrates strict alpha=0.10 release of learned link candidates and refusal of corrupted rankings before false lineage edges enter downstream graph artifacts. Materials demonstrates fixed-budget follow-up utility from an ALIGNN-FF source at K=300 and K=500, with source-hashed lead numbers.

iWildCam and SpaceNet are included as audited boundary settings: they show real partial-verification release/refusal behavior, but are not framed as equal flagship wins. OQMD and alex-mp are included as source-discordance stress tests, not as positive independent materials validation.
"""
    (OUT / "cover_letter_key_positioning.md").write_text(text, encoding="utf-8")


def build_checklist(final_table: pd.DataFrame) -> pd.DataFrame:
    inquiry = (OUT / "presubmission_inquiry_final.md").read_text(encoding="utf-8")
    abstract = (OUT / "nmi_abstract_presubmission_final.md").read_text(encoding="utf-8")
    lead = pd.read_csv(PHASE32 / "table_lead_numbers_for_editor.csv")
    referee = (PHASE32 / "suggested_referee_rationale.md").read_text(encoding="utf-8")
    rows = [
        ("lead_numbers_have_sha256", True, lead["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()),
        ("no_A3_positive_claim", True, "A3 positive" not in inquiry and "pending optional extension" in final_table.to_string()),
        ("no_prospective_materials_discovery_claim", True, "prospective materials discovery" not in abstract.lower() and "without claiming prospective discovery" in abstract),
        ("two_hard_anchors_visible", True, {"hard_anchor"}.issubset(set(final_table["final_role"])) and (final_table["final_role"] == "hard_anchor").sum() >= 2),
        ("audited_boundary_not_oversold", True, "audited_boundary" in set(final_table["final_role"]) and "not flagship positive" in final_table.to_string()),
        ("source_discordance_scoped_as_stress_test", True, "source_discordance_stress_test" in set(final_table["final_role"]) and "not positive independent validation" in final_table.to_string()),
        ("abstract_contains_release_refuse_language", True, "release-time certification" in abstract or "refuse" in abstract),
        ("abstract_does_not_claim_four_domain_success", True, "four-domain success" not in abstract.lower() and "across all domains" not in abstract.lower()),
        ("referee_rationale_balanced", True, "AI-for-science reliability" in referee and "Applied conformal/e-value risk control" in referee and "Scientific ML workflow" in referee),
    ]
    frame = pd.DataFrame(
        [
            {
                "check_id": check_id,
                "go_required": required,
                "status": "PASS" if passed else "FAIL",
                "details": "required presubmission guardrail satisfied" if passed else "guardrail failed",
            }
            for check_id, required, passed in rows
        ]
    )
    frame.to_csv(OUT / "submission_go_no_go_checklist.csv", index=False)
    return frame


def update_artifacts() -> None:
    path = ROOT / "outputs" / "artifact_index.csv"
    df = pd.read_csv(path)
    row = {
        "milestone": "nmi_presubmission_final",
        "path": "outputs/milestones/nmi_presubmission_final/",
        "evidence_state": "completed_presubmission_go_no_go_package",
        "manifest": "outputs/milestones/nmi_presubmission_final/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_final",
    }
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(path, index=False)

    claim = ROOT / "docs" / "claim_table.md"
    text = claim.read_text(encoding="utf-8")
    if "Phase33 finalizes the NMI presubmission go/no-go package." not in text:
        row_text = (
            "| Phase33 finalizes the NMI presubmission go/no-go package. | "
            "`outputs/milestones/nmi_presubmission_final/presubmission_inquiry_final.md`; "
            "`one_page_evidence_table_final.csv`; `submission_go_no_go_checklist.csv`; "
            "`forbidden_claims_final.md` | "
            "`python scripts/build_phase33_nmi_presubmission_final.py` | "
            "Final inquiry is 600-750 words; A3 remains pending, OQMD/alex-mp remain stress tests, and all required go/no-go checks must pass before using the package. |\n"
        )
        text = text.replace("| Phase32 packages", row_text + "| Phase32 packages", 1)
        claim.write_text(text, encoding="utf-8")

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if "milestones/nmi_presubmission_final/" not in text:
        text = text.replace(
            "│   ├── milestones/nmi_presubmission_package/\n",
            "│   ├── milestones/nmi_presubmission_package/\n│   ├── milestones/nmi_presubmission_final/\n",
        )
    if "Phase33 final NMI presubmission go/no-go package" not in text:
        text = text.replace(
            "- Phase32 NMI presubmission package:",
            "- Phase33 final NMI presubmission go/no-go package: compressed inquiry, final abstract, evidence table, forbidden claims, cold read, cover-letter positioning, and PASS checklist.\n- Phase32 NMI presubmission package:",
        )
    readme.write_text(text, encoding="utf-8")

    repro = ROOT / "REPRODUCIBILITY.md"
    text = repro.read_text(encoding="utf-8")
    if "outputs/milestones/nmi_presubmission_final/" not in text:
        text = text.replace(
            "outputs/milestones/nmi_presubmission_package/\n",
            "outputs/milestones/nmi_presubmission_package/\noutputs/milestones/nmi_presubmission_final/\n",
        )
    if "Regenerate the phase33 NMI presubmission final package" not in text:
        block = """
Regenerate the phase33 NMI presubmission final package:

```bash
python scripts/build_phase33_nmi_presubmission_final.py
```

This command builds the compressed final inquiry, final evidence table, final
abstract, editor cold read, forbidden-claims list, cover-letter positioning,
and go/no-go checklist. All go-required checks must be `PASS`.
"""
        text = text.replace("Regenerate the phase32 NMI presubmission package:", block + "\nRegenerate the phase32 NMI presubmission package:")
    repro.write_text(text, encoding="utf-8")

    makefile = ROOT / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    text = text.replace(
        "reproduce-phase32-presubmission reproduce-experimental-finalization",
        "reproduce-phase32-presubmission reproduce-phase33-presubmission-final reproduce-experimental-finalization",
    )
    if "reproduce-phase33-presubmission-final:" not in text:
        text = text.replace(
            "reproduce-phase32-presubmission:\n\t$(PYTHON) scripts/build_phase32_nmi_presubmission_package.py\n\n",
            "reproduce-phase32-presubmission:\n\t$(PYTHON) scripts/build_phase32_nmi_presubmission_package.py\n\nreproduce-phase33-presubmission-final:\n\t$(PYTHON) scripts/build_phase33_nmi_presubmission_final.py\n\n",
        )
    if "outputs/milestones/nmi_presubmission_final" not in text:
        text = text.replace(
            "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_package\n",
            "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_package\n\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_final\n",
        )
    makefile.write_text(text, encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    ensure_clean_dir(OUT)
    build_inquiry()
    final_table = build_final_evidence_table()
    build_abstract()
    build_cold_read()
    build_forbidden_claims()
    build_cover_letter_positioning()
    checklist = build_checklist(final_table)
    if not (checklist[checklist["go_required"].astype(bool)]["status"] == "PASS").all():
        raise RuntimeError("phase33 go/no-go checklist has failing required rows")
    update_artifacts()
    write_manifest(OUT)
    write_root_manifest()


if __name__ == "__main__":
    main()
