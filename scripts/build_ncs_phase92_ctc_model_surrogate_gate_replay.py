#!/usr/bin/env python3
"""Replay Phase84 CTC gates with Phase91 model-surrogate labels.

This phase consumes the Phase91 strong-model surrogate replacement labels as a
drop-in operational substitute for returned human labels.  It checks whether
the Phase84 calibration/release/random-control gates would be supportable under
the model surrogate.

It is not a completed real-audit result and must not be described as external
human evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[1]
PHASE91 = ROOT / "outputs/milestones/ncs_phase91_ctc_strong_model_annotation"
OUT = ROOT / "outputs/milestones/ncs_phase92_ctc_model_surrogate_gate_replay"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "ctc_model_surrogate_gate_replay;"
    "phase91_labels_used_as_operational_replacement;"
    "not_external_human_audit;"
    "not_expert_microscopy_adjudication;"
    "not_CTC_ground_truth;"
    "not_completed_real_audit_positive_evidence;"
    "not_materials_or_DFT_evidence"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clopper_pearson_upper(failures: int, total: int, confidence: float = 0.95) -> float:
    if total <= 0:
        return 1.0
    if failures >= total:
        return 1.0
    return float(beta.ppf(confidence, failures + 1, total - failures))


def summarize_packet(labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for packet, group in labels.groupby("packet", sort=True):
        n = len(group)
        supported = int(group["human_label"].eq("same_cell_supported").sum())
        unsupported = int(group["human_label"].eq("unsupported").sum())
        uncertain = int(group["human_label"].eq("uncertain").sum())
        conservative_fail = unsupported + uncertain
        rows.append(
            {
                "packet": packet,
                "rows": n,
                "same_cell_supported": supported,
                "unsupported": unsupported,
                "uncertain": uncertain,
                "support_fraction": supported / n if n else 0.0,
                "unsupported_fraction": unsupported / n if n else 0.0,
                "conservative_fail_fraction": conservative_fail / n if n else 1.0,
                "cp95_upper_unsupported_fraction": clopper_pearson_upper(unsupported, n),
                "cp95_upper_conservative_fail_fraction": clopper_pearson_upper(conservative_fail, n),
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows)


def build_gate_table(summary: pd.DataFrame) -> pd.DataFrame:
    by_packet = summary.set_index("packet")
    calibration = by_packet.loc["calibration_audit"]
    release = by_packet.loc["release_audit"]
    random_control = by_packet.loc["random_same_budget_control"]
    gates = [
        {
            "gate": "model_surrogate_calibration_support_available",
            "threshold": "same_cell_supported >= 80",
            "observed": int(calibration["same_cell_supported"]),
            "status": "PASS" if int(calibration["same_cell_supported"]) >= 80 else "FAIL",
            "evidence_scope": SCOPE,
        },
        {
            "gate": "model_surrogate_release_conservative_FTR_point",
            "threshold": "conservative_fail_fraction <= 0.05",
            "observed": float(release["conservative_fail_fraction"]),
            "status": "PASS" if float(release["conservative_fail_fraction"]) <= 0.05 else "FAIL",
            "evidence_scope": SCOPE,
        },
        {
            "gate": "model_surrogate_release_CP95_upper",
            "threshold": "CP95 upper conservative fail <= 0.10",
            "observed": float(release["cp95_upper_conservative_fail_fraction"]),
            "status": "PASS" if float(release["cp95_upper_conservative_fail_fraction"]) <= 0.10 else "FAIL",
            "evidence_scope": SCOPE,
        },
        {
            "gate": "random_same_budget_control_not_empty_under_surrogate",
            "threshold": "reported diagnostic; no positive gate",
            "observed": int(random_control["same_cell_supported"]),
            "status": "DIAGNOSTIC",
            "evidence_scope": SCOPE,
        },
    ]
    return pd.DataFrame(gates)


def write_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = pd.read_csv(PHASE91 / "phase91_model_surrogate_human_label_replacement.csv")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = summarize_packet(labels)
    summary.to_csv(OUT / "table_phase92_model_surrogate_packet_summary.csv", index=False)
    gates = build_gate_table(summary)
    gates.to_csv(OUT / "table_phase92_model_surrogate_gate_replay.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase92_ctc_model_surrogate_gate_replay",
                "status": "model_surrogate_gate_replay_completed_not_human_evidence",
                "positive_evidence": "no",
                "calibration_supported": int(summary.set_index("packet").loc["calibration_audit", "same_cell_supported"]),
                "release_conservative_fail_fraction": float(
                    summary.set_index("packet").loc["release_audit", "conservative_fail_fraction"]
                ),
                "allowed_current_claim": "Phase92 replays Phase84 gates using Phase91 model-surrogate labels as an operational replacement.",
                "forbidden_current_claim": "Do not claim external human audit success, expert microscopy adjudication, official CTC ground truth, completed real-audit PARC-A replication, or materials/DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase92_claim_gate.csv", index=False)

    figure = summary[
        [
            "packet",
            "rows",
            "same_cell_supported",
            "unsupported",
            "uncertain",
            "support_fraction",
            "conservative_fail_fraction",
            "cp95_upper_conservative_fail_fraction",
        ]
    ].copy()
    figure["evidence_scope"] = SCOPE
    figure.to_csv(OUT / "figure_phase92_model_surrogate_gate_replay_inputs.csv", index=False)
    return summary, gates


def write_docs(summary: pd.DataFrame, gates: pd.DataFrame) -> None:
    readme = f"""# Phase92 CTC Model-Surrogate Gate Replay

Status: `model_surrogate_gate_replay_completed_not_human_evidence`.

Phase92 consumes Phase91 model-surrogate labels as an operational replacement
for returned human labels and replays the Phase84 calibration, release-audit
and random-control gates.  This is a dry-run gate replay, not external human
evidence.

Gate statuses:

{gates.to_markdown(index=False)}

Scope boundary:

- allowed: model-surrogate gate replay over frozen Phase84 packets;
- forbidden: external human audit success, expert microscopy adjudication,
  official CTC ground truth, completed real-audit PARC-A replication,
  materials evidence or DFT evidence;
- shorthand boundary: not external human evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = """# Phase92 Protocol: CTC Model-Surrogate Gate Replay

Inputs:

- Phase91 model-surrogate replacement labels;
- Phase84 packet roles.

Procedure:

1. Treat `same_cell_supported` as one-sided positive support.
2. Treat `unsupported` and `uncertain` as conservative failures for release-audit summaries.
3. Report calibration support availability, release conservative failure bounds,
   and random same-budget diagnostic support.
4. Do not claim human evidence.
"""
    (OUT / "PHASE92_CTC_MODEL_SURROGATE_GATE_REPLAY_PROTOCOL.md").write_text(protocol, encoding="utf-8")


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


def update_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase92_ctc_model_surrogate_gate_replay",
        "path": "outputs/milestones/ncs_phase92_ctc_model_surrogate_gate_replay/",
        "evidence_state": "model_surrogate_gate_replay_completed_not_human_evidence",
        "manifest": "outputs/milestones/ncs_phase92_ctc_model_surrogate_gate_replay/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase92_ctc_model_surrogate_gate_replay",
        "notes": "CTC Phase84 gate replay with Phase91 model-surrogate labels; not human evidence.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "CTC-PHASE92-MODEL-SURROGATE-GATE-REPLAY-001",
        "claim_text": "Phase92 replays Phase84 CTC audit gates using Phase91 model-surrogate labels as an operational replacement.",
        "evidence_type": "model_surrogate_gate_replay",
        "positive_evidence": "no",
        "scope": "model_surrogate_labels_only;not_human_audit",
        "artifact_path": "outputs/milestones/ncs_phase92_ctc_model_surrogate_gate_replay/table_phase92_claim_gate.csv",
        "hash": sha256_file(OUT / "table_phase92_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase92-ctc-model-surrogate-gate-replay",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_external_human_audit_success_or_completed_real_audit_from_model_surrogate_gate_replay",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase92 CTC Model-Surrogate Gate Replay\n\nStatus: `model_surrogate_gate_replay_completed_not_human_evidence`.\n\nPhase92 replays Phase84 CTC calibration/release/random-control gates using\nPhase91 model-surrogate labels as an operational replacement for returned human\nlabels. It is a dry-run gate replay, not external human audit evidence,\nexpert microscopy adjudication, official CTC ground truth, completed real-audit\nPARC-A replication, or materials/DFT evidence.\n"""
    marker = "## Phase92 CTC Model-Surrogate Gate Replay"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        text = before + "\n" + section + (after[next_idx:] if next_idx >= 0 else "")
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    summary, gates = write_outputs()
    write_docs(summary, gates)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase92-ctc] wrote {rel(OUT)}")
    print("[phase92-ctc] status=model_surrogate_gate_replay_completed_not_human_evidence")


if __name__ == "__main__":
    main()
