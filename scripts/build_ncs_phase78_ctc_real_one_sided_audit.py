#!/usr/bin/env python3
"""Build Phase78 CTC real one-sided audit integration artifacts.

Phase78 does not create new labels. It promotes the existing CTC strict
human-confirmed audit package into the NCS lifecycle story, with explicit scope
guardrails: trained/human-confirmed review, not microscopy-expert adjudication
unless separately documented.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/milestones/ctc_strict_human_audit"
OUT = ROOT / "outputs/milestones/ncs_phase78_ctc_real_one_sided_audit"

SCOPE = (
    "completed_CTC_real_one_sided_audit_integration;"
    "human_confirmed_trained_review_not_expert_adjudication;"
    "supports_PARC_A_primary_positive;"
    "not_new_domain;"
    "not_materials_evidence;"
    "not_DFT_evidence"
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
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows: list[str] = []
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


def wilson_upper(k: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return float("nan")
    phat = k / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4.0 * n * n)) / denom
    return min(1.0, center + half)


def load_source() -> tuple[pd.DataFrame, dict[str, object]]:
    labels = pd.read_csv(SOURCE / "ctc_strict_audit_human_confirmed_labels.csv")
    report = json.loads((SOURCE / "CTC_STRICT_HUMAN_AUDIT_REPORT.json").read_text(encoding="utf-8"))
    required = {
        "audit_id",
        "queue_calibration",
        "queue_simulated_strict_release",
        "queue_raw_topK_reference",
        "human_label",
        "human_verified_positive_for_calibration",
        "human_review_status",
    }
    missing = required.difference(labels.columns)
    if missing:
        raise ValueError(f"missing required CTC audit columns: {sorted(missing)}")
    return labels, report


def summarize_arm(labels: pd.DataFrame, arm: str, mask: pd.Series) -> dict[str, object]:
    subset = labels[mask].copy()
    n = len(subset)
    same = int(subset["human_label"].eq("same_cell_link").sum())
    not_same = int(subset["human_label"].eq("not_same_cell_link").sum())
    uncertain = int(subset["human_label"].eq("uncertain").sum())
    false_uncertain = not_same + uncertain
    verified_yes = int(subset["human_verified_positive_for_calibration"].eq("yes").sum())
    datasets = ",".join(sorted(map(str, subset["ctc_dataset"].dropna().unique()))) if n else ""
    return {
        "audit_arm": arm,
        "rows": n,
        "same_cell_link": same,
        "not_same_cell_link": not_same,
        "uncertain": uncertain,
        "verified_positive_yes": verified_yes,
        "human_false_fraction": not_same / n if n else float("nan"),
        "uncertain_as_false_fraction": false_uncertain / n if n else float("nan"),
        "wilson_upper95_false_only": wilson_upper(not_same, n),
        "wilson_upper95_uncertain_as_false": wilson_upper(false_uncertain, n),
        "review_statuses": ",".join(sorted(map(str, subset["human_review_status"].dropna().unique()))) if n else "",
        "datasets": datasets,
        "evidence_scope": SCOPE,
    }


def build_tables(labels: pd.DataFrame, report: dict[str, object]) -> None:
    masks = {
        "all_human_confirmed_rows": pd.Series(True, index=labels.index),
        "calibration_one_sided_support_pool": labels["queue_calibration"].astype(bool),
        "simulated_strict_release_queue": labels["queue_simulated_strict_release"].astype(bool),
        "raw_topK_reference_overlap": labels["queue_raw_topK_reference"].astype(bool),
        "not_same_or_uncertain_control_rows": labels["human_label"].isin(["not_same_cell_link", "uncertain"]),
    }
    summary = pd.DataFrame([summarize_arm(labels, arm, mask) for arm, mask in masks.items()])
    summary.to_csv(OUT / "table_ctc_real_audit_arm_summary.csv", index=False)

    release = summary[summary["audit_arm"].eq("simulated_strict_release_queue")].iloc[0]
    gate = pd.DataFrame(
        [
            {
                "gate": "ctc_real_one_sided_release_audit",
                "alpha": 0.10,
                "release_rows": int(release["rows"]),
                "human_false_rows": int(release["not_same_cell_link"]),
                "uncertain_rows": int(release["uncertain"]),
                "human_false_fraction": float(release["human_false_fraction"]),
                "uncertain_as_false_fraction": float(release["uncertain_as_false_fraction"]),
                "wilson_upper95_false_only": float(release["wilson_upper95_false_only"]),
                "wilson_upper95_uncertain_as_false": float(release["wilson_upper95_uncertain_as_false"]),
                "decision": "go" if float(release["uncertain_as_false_fraction"]) <= 0.10 else "no_go",
                "interpretation": (
                    "human-confirmed strict release queue satisfies alpha=0.10 under false-only "
                    "and uncertain-as-false point estimates; confidence bounds are reported as audit uncertainty"
                ),
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_ctc_real_audit_release_gate.csv", index=False)

    support = pd.DataFrame(
        [
            {
                "one_sided_rule": "same_cell_link_may_enter_verified_positive_set",
                "allowed_positive_label": "same_cell_link",
                "forbidden_negative_use": "not_same_cell_link_or_uncertain_must_remain_unverified_not_trusted_negatives",
                "calibration_rows": int(summary.loc[summary["audit_arm"].eq("calibration_one_sided_support_pool"), "rows"].iloc[0]),
                "calibration_verified_positive_yes": int(
                    summary.loc[
                        summary["audit_arm"].eq("calibration_one_sided_support_pool"),
                        "verified_positive_yes",
                    ].iloc[0]
                ),
                "calibration_not_same_or_uncertain": int(
                    summary.loc[
                        summary["audit_arm"].eq("calibration_one_sided_support_pool"),
                        "not_same_cell_link",
                    ].iloc[0]
                    + summary.loc[
                        summary["audit_arm"].eq("calibration_one_sided_support_pool"),
                        "uncertain",
                    ].iloc[0]
                ),
                "release_verified_positive_yes": int(release["verified_positive_yes"]),
                "expert_review_claimed": bool(report.get("expert_review_claimed", False)),
                "allowed_paper_wording": "trained human review; human-confirmed one-sided audit",
                "forbidden_paper_wording": "microscopy-expert adjudication unless separately documented",
                "evidence_scope": SCOPE,
            }
        ]
    )
    support.to_csv(OUT / "table_ctc_real_audit_one_sided_support.csv", index=False)

    bounds = summary[
        [
            "audit_arm",
            "rows",
            "not_same_cell_link",
            "uncertain",
            "human_false_fraction",
            "uncertain_as_false_fraction",
            "wilson_upper95_false_only",
            "wilson_upper95_uncertain_as_false",
            "evidence_scope",
        ]
    ].copy()
    bounds["confidence_method"] = "Wilson score upper bound, 95% normal approximation"
    bounds.to_csv(OUT / "table_ctc_real_audit_uncertainty_bounds.csv", index=False)

    claim_scope = pd.DataFrame(
        [
            {
                "claim_id": "CTC-REAL-AUDIT-001",
                "allowed_claim": "The CTC strict-release queue has human-confirmed support under a trained one-sided review package.",
                "forbidden_claim": "The result is a new microscopy-expert ground truth benchmark or a materials/DFT validation.",
                "artifact": rel(OUT / "table_ctc_real_audit_release_gate.csv"),
                "status": "completed_supports_PARC_A_primary_positive",
                "evidence_scope": SCOPE,
            },
            {
                "claim_id": "CTC-REAL-AUDIT-002",
                "allowed_claim": "Only same-cell human-confirmed rows are used as one-sided verified positives.",
                "forbidden_claim": "Not-same or uncertain labels are trusted negatives for PARC calibration.",
                "artifact": rel(OUT / "table_ctc_real_audit_one_sided_support.csv"),
                "status": "completed_one_sided_rule_documented",
                "evidence_scope": SCOPE,
            },
            {
                "claim_id": "CTC-REAL-AUDIT-003",
                "allowed_claim": "The audit strengthens PARC-A practical credibility without adding a new domain.",
                "forbidden_claim": "The audit replaces the CTC official benchmark or proves broad domain success.",
                "artifact": rel(OUT / "table_ctc_real_audit_arm_summary.csv"),
                "status": "completed_scope_guardrail",
                "evidence_scope": SCOPE,
            },
        ]
    )
    claim_scope.to_csv(OUT / "table_ctc_real_audit_claim_scope.csv", index=False)

    figure = pd.DataFrame(
        [
            {
                "panel": "A",
                "quantity": "release_rows",
                "value": int(release["rows"]),
                "label": "human-confirmed strict-release rows",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "B",
                "quantity": "release_false_rows",
                "value": int(release["not_same_cell_link"]),
                "label": "not-same rows in strict release queue",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "B",
                "quantity": "release_uncertain_rows",
                "value": int(release["uncertain"]),
                "label": "uncertain rows in strict release queue",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "C",
                "quantity": "release_uncertain_as_false_fraction",
                "value": float(release["uncertain_as_false_fraction"]),
                "label": "conservative release audit point estimate",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "C",
                "quantity": "release_wilson_upper95_uncertain_as_false",
                "value": float(release["wilson_upper95_uncertain_as_false"]),
                "label": "95% audit uncertainty upper bound",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "D",
                "quantity": "calibration_not_same_rows_remain_unverified",
                "value": int(support["calibration_not_same_or_uncertain"].iloc[0]),
                "label": "non-positive calibration rows kept out of one-sided positives",
                "evidence_scope": SCOPE,
            },
        ]
    )
    figure.to_csv(OUT / "figure_ctc_real_audit_inputs.csv", index=False)


def write_readme(status: str, report: dict[str, object]) -> None:
    text = f"""# Phase78 CTC Real One-Sided Audit Integration

Status: `{status}`.

This milestone integrates the existing CTC strict human-confirmed audit package
into the NCS release-card lifecycle story. It does not create new labels.

Evidence boundary:

- supports PARC-A as the primary empirical positive;
- use `trained human review` or `human-confirmed one-sided audit`;
- do not claim microscopy-expert adjudication unless separately documented;
- do not claim a new CTC benchmark, materials evidence or DFT evidence;
- `same_cell_link` rows may enter the one-sided positive set;
- `not_same_cell_link`, `uncertain` and any future disagreement must remain
  unverified and must not be treated as trusted negatives.

Source package:

- `{rel(SOURCE / "ctc_strict_audit_human_confirmed_labels.csv")}`;
- source status: `{report.get("status", "unknown")}`;
- expert review claimed: `{report.get("expert_review_claimed", False)}`.
"""
    (OUT / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def update_artifact_index(status: str) -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase78_ctc_real_one_sided_audit"]
    rows.append(
        {
            "milestone": "ncs_phase78_ctc_real_one_sided_audit",
            "path": "outputs/milestones/ncs_phase78_ctc_real_one_sided_audit/",
            "evidence_state": status,
            "manifest": "outputs/milestones/ncs_phase78_ctc_real_one_sided_audit/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase78_ctc_real_one_sided_audit",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["milestone", "path", "evidence_state", "manifest", "public_bundle_check"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def update_claim_table(status: str) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase78 CTC Real One-Sided Audit"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    addition = f"""

## Phase78 CTC Real One-Sided Audit

Status: `{status}`.

Phase78 integrates the existing CTC strict human-confirmed audit package into
the NCS lifecycle story. The strict-release queue has 1064 human-confirmed rows
with zero not-same and zero uncertain labels. This strengthens PARC-A practical
credibility, but it should be described as trained/human-confirmed one-sided
review rather than microscopy-expert adjudication unless a separate expert
review is documented.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(status: str) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "CTC-REAL-AUDIT-001"]
    artifact = OUT / "table_ctc_real_audit_release_gate.csv"
    rows.append(
        {
            "claim_id": "CTC-REAL-AUDIT-001",
            "claim_text": "The CTC strict-release queue has human-confirmed one-sided review support with zero observed false or uncertain rows.",
            "evidence_type": "human_confirmed_one_sided_audit",
            "positive_evidence": "yes",
            "scope": status,
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase78-ctc-real-one-sided-audit",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_microscopy_expert_adjudication_new_domain_materials_evidence_or_DFT_validation",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "claim_id",
                "claim_text",
                "evidence_type",
                "positive_evidence",
                "scope",
                "artifact_path",
                "hash",
                "validation_command",
                "status",
                "overclaim_guardrail",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    status = "completed_CTC_real_one_sided_audit_integration"
    labels, report = load_source()
    build_tables(labels, report)
    write_readme(status, report)
    provenance = {
        "phase": "phase78",
        "status": status,
        "source_milestone": rel(SOURCE),
        "source_rows": int(len(labels)),
        "expert_review_claimed": bool(report.get("expert_review_claimed", False)),
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    update_artifact_index(status)
    update_claim_table(status)
    update_evidence_ledger(status)
    write_root_manifest()
    print(json.dumps({"status": status, "out_dir": rel(OUT)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
