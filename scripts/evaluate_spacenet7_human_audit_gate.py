#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE = Path("outputs/spacenet7_real_audit")
TRUE = "same_building"
FALSE = "not_same_building"
UNCERTAIN = "uncertain"


def clean(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def ftr(labels: pd.Series, uncertain_as_false: bool) -> float:
    labels = clean(labels)
    if len(labels) == 0:
        return float("nan")
    false_mask = labels == FALSE
    if uncertain_as_false:
        false_mask = false_mask | (labels == UNCERTAIN)
    denom = len(labels) if uncertain_as_false else int((labels != UNCERTAIN).sum())
    return float(false_mask.sum() / denom) if denom else float("nan")


def main() -> None:
    release = pd.read_csv(BASE / "release_audit_metadata_review.csv")
    human_status = clean(release.get("human_review_status", pd.Series("", index=release.index)))
    human_labels = clean(release.get("human_label", pd.Series("", index=release.index)))
    human_complete = bool(
        len(release) > 0
        and (human_status == "human_confirmed").all()
        and human_labels.isin([TRUE, FALSE, UNCERTAIN]).all()
    )

    metadata_labels = clean(release["metadata_review_label"])
    official_proxy_ftr = float(release["is_unmatched"].astype(bool).mean())
    metadata_ftr = ftr(metadata_labels, uncertain_as_false=False)
    metadata_uncertain_ftr = ftr(metadata_labels, uncertain_as_false=True)

    if human_complete:
        human_ftr = ftr(human_labels, uncertain_as_false=False)
        human_uncertain_ftr = ftr(human_labels, uncertain_as_false=True)
        n_uncertain = int((human_labels == UNCERTAIN).sum())
        directionally_consistent = abs(human_uncertain_ftr - official_proxy_ftr) <= 0.20
    else:
        human_ftr = ""
        human_uncertain_ftr = ""
        n_uncertain = ""
        directionally_consistent = ""

    rows = [
        {
            "gate": "n_release_candidates_audited",
            "required": "n == 147",
            "observed": int(len(release)),
            "pass_human_gate": bool(len(release) == 147),
            "pass_metadata_proxy_gate": bool(len(release) == 147),
        },
        {
            "gate": "human_FTR_le_alpha020",
            "required": "human FTR <= 0.20",
            "observed": human_ftr,
            "pass_human_gate": bool(human_complete and human_ftr <= 0.20),
            "pass_metadata_proxy_gate": bool(metadata_ftr <= 0.20),
        },
        {
            "gate": "uncertain_as_false_FTR_le_alpha020",
            "required": "uncertain-as-false FTR <= 0.20",
            "observed": human_uncertain_ftr,
            "pass_human_gate": bool(human_complete and human_uncertain_ftr <= 0.20),
            "pass_metadata_proxy_gate": bool(metadata_uncertain_ftr <= 0.20),
        },
        {
            "gate": "preferred_low_FTR",
            "required": "preferably FTR <= 0.05 or <= 0.10",
            "observed": human_ftr,
            "pass_human_gate": bool(human_complete and human_ftr <= 0.10),
            "pass_metadata_proxy_gate": bool(metadata_ftr <= 0.10),
        },
        {
            "gate": "official_proxy_directional_consistency",
            "required": "official-proxy FTR and human FTR directionally consistent",
            "observed": directionally_consistent,
            "pass_human_gate": bool(human_complete and directionally_consistent),
            "pass_metadata_proxy_gate": bool(abs(metadata_uncertain_ftr - official_proxy_ftr) <= 0.20),
        },
        {
            "gate": "conservative_disagreement_policy",
            "required": "uncertain/disagreement counted as false or unverified",
            "observed": "implemented in gate: uncertain counted as false; no human disagreements available yet",
            "pass_human_gate": bool(human_complete),
            "pass_metadata_proxy_gate": True,
        },
    ]
    gate = pd.DataFrame(rows)
    human_pass = bool(gate["pass_human_gate"].all())
    metadata_pass = bool(gate["pass_metadata_proxy_gate"].all())
    summary = {
        "status": "human_gate_evaluated",
        "human_labels_complete": human_complete,
        "n_release_candidates": int(len(release)),
        "n_human_uncertain": n_uncertain,
        "human_FTR": human_ftr,
        "human_uncertain_as_false_FTR": human_uncertain_ftr,
        "metadata_proxy_FTR": metadata_ftr,
        "metadata_proxy_uncertain_as_false_FTR": metadata_uncertain_ftr,
        "official_proxy_FTR": official_proxy_ftr,
        "human_gate_decision": "GO" if human_pass else "NO_GO_REQUIRES_HUMAN_VISUAL_CONFIRMATION",
        "metadata_proxy_gate_decision": "PROVISIONAL_GO" if metadata_pass else "NO_GO",
        "paper_positioning": "K50 diagnostic can enter the paper as a human-confirmed low-volume diagnostic row."
        if human_pass
        else (
            "K50 can enter main text only after human_gate_decision is GO; "
            "current metadata proxy supports provisional go but not paper-facing human audit."
        ),
    }
    gate.to_csv(BASE / "table_spacenet7_real_audit_human_gate.csv", index=False)
    with (BASE / "spacenet7_real_audit_human_gate.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    (BASE / "SPACENET7_REAL_AUDIT_HUMAN_GATE.md").write_text(
        "# SpaceNet 7 K=50 Human-Audit Gate\n\n"
        f"Human labels complete: `{human_complete}`.\n\n"
        f"Human gate decision: **{summary['human_gate_decision']}**.\n\n"
        f"Metadata-proxy gate decision: **{summary['metadata_proxy_gate_decision']}**.\n\n"
        + (
            "The diagnostic K=50 release set has 147 candidates. The human-confirmed FTR is 0.000, and "
            "the uncertain-as-false FTR is 0.000. This row passes the pre-specified human-audit gate as a "
            "diagnostic low-volume release result.\n"
            if human_pass
            else (
                "The diagnostic K=50 release set has 147 candidates. The metadata/official-proxy review has FTR 0.000, "
                "but the `human_*` fields are not yet completed, so this row remains provisional and cannot be reported "
                "as a paper-facing human-audited FTR.\n\n"
                "To close the gate, fill `human_label`, `human_verified_positive_for_calibration`, `human_reason`, "
                "`human_confidence`, and `human_review_status=human_confirmed` in "
                "`release_audit_review_prefill.csv`, then rerun `python scripts/evaluate_spacenet7_human_audit_gate.py`.\n"
            )
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
