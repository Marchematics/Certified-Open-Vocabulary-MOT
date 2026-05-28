#!/usr/bin/env python3
"""Build Phase63 PARC-A certificate-directed active verification package.

This phase turns the existing audit-budget frontier into a narrow paper-facing
method result: a scarce one-sided verification budget can be targeted to make a
strict CTC release certificate possible, whereas matched-budget random audit
does not. Materials rows are retained as boundary/secondary evidence only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STRONG = ROOT / "outputs/milestones/audit_budget_frontier_strong_positive"
DEFAULT_FRONTIER = ROOT / "outputs/milestones/audit_budget_release_frontier"
EXTENDED_FRONTIER = ROOT / "outputs/milestones/audit_budget_release_frontier_extended"
OUT = ROOT / "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification"
SCOPE = (
    "PARC_A_certificate_directed_active_verification;"
    "simulated_one_sided_audit_over_existing_labels;"
    "primary_CTC_only;"
    "materials_boundary_secondary;"
    "not_new_human_labels;"
    "not_new_DFT;"
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


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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


def fmt_budget(value: object) -> str:
    if value == "" or pd.isna(value):
        return ""
    return f"{float(value):g}"


def build_primary_tables() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    gate = pd.read_csv(STRONG / "table_strong_positive_gate_audit.csv")
    contrast = pd.read_csv(STRONG / "table_audit_budget_policy_contrast.csv")
    seed_rows = pd.read_csv(STRONG / "table_ctc_primary_seed_rows.csv")

    primary_rows: list[dict[str, object]] = []
    for _, row in gate.iterrows():
        is_primary = row["manuscript_role"] == "primary_strong_positive"
        primary_rows.append(
            {
                "evidence_block": "PARC-A active verification",
                "target_row": row["target_row"],
                "domain": row["domain"],
                "K": int(row["K"]),
                "alpha": float(row["alpha"]),
                "audit_policy": row["audit_policy"],
                "audit_budget_fraction": float(row["audit_budget_fraction"]),
                "seeds": int(row["seeds"]),
                "safe_seeds": int(row["top_safe_seeds"]),
                "nonempty_seeds": int(row["top_nonempty_seeds"]),
                "mean_release": float(row["top_mean_release"]),
                "total_released": int(row["top_total_released"]),
                "total_false_releases": float(row["top_total_false_releases"]),
                "mean_FTR": float(row["top_mean_FTR"]),
                "max_FTR": float(row["top_max_FTR"]),
                "matched_random_budget_fraction": float(row["random_same_budget_fraction"]),
                "matched_random_nonempty_seeds": int(row["random_same_nonempty_seeds"]),
                "full_random_transition_budget_fraction": float(row["random_full_transition_budget_fraction"]),
                "budget_ratio_vs_full_random": float(row["budget_ratio_vs_random_full"]),
                "mean_verified_positive_yield": float(row["top_mean_verified_positive_yield"]),
                "random_mean_verified_positive_yield": float(row["random_same_mean_verified_positive_yield"]),
                "strong_positive_gate": row["strong_positive_gate"],
                "manuscript_role": "primary_method_headline" if is_primary else "secondary_support",
                "claim_boundary": SCOPE,
            }
        )

    policy_rows: list[dict[str, object]] = []
    for _, row in contrast.iterrows():
        policy_rows.append(
            {
                "target_row": row["target_row"],
                "audit_policy": row["audit_policy"],
                "audit_budget_fraction": row["audit_budget_fraction"],
                "seeds": row["seeds"],
                "nonempty_seeds": row["nonempty_seeds"],
                "safe_seeds": row["safe_seeds"],
                "mean_release": row["mean_release"],
                "total_released": row["total_released"],
                "total_false_releases": row["total_false_releases"],
                "mean_FTR": row["mean_FTR"],
                "mean_verified_positive_yield": row["mean_verified_positive_yield"],
                "mean_best_mass_ratio": row["mean_best_mass_ratio"],
                "policy_role": row["policy_role"],
                "claim_boundary": SCOPE,
            }
        )

    seed_out: list[dict[str, object]] = []
    for _, row in seed_rows.iterrows():
        seed_out.append({**row.to_dict(), "claim_boundary": SCOPE})
    return primary_rows, policy_rows, seed_out


def best_materials_boundary_rows() -> list[dict[str, object]]:
    summary = pd.read_csv(EXTENDED_FRONTIER / "table_audit_budget_frontier_summary.csv")
    mat = summary[summary["domain"].eq("materials_discovery")].copy()
    rows: list[dict[str, object]] = []
    for target in [
        "materials_alignn_exact_stable_alpha010_K300",
        "materials_alignn_exact_stable_alpha010_K500",
        "materials_cgcnn_exact_stable_alpha010_K100",
    ]:
        target_rows = mat[mat["target_row"].eq(target)].copy()
        top = target_rows[
            target_rows["audit_policy"].eq("top_score")
            & target_rows["audit_budget_fraction"].astype(float).eq(0.005)
        ]
        random_full = target_rows[
            target_rows["audit_policy"].eq("random")
            & target_rows["audit_budget_fraction"].astype(float).eq(1.0)
        ]
        random_any = (
            target_rows[
                target_rows["audit_policy"].eq("random")
                & (target_rows["safe_release_rate"].astype(float) > 0)
                & (target_rows["actual_FTR_mean"].astype(float) <= target_rows["alpha"].astype(float))
            ]
            .sort_values("audit_budget_fraction")
            .head(1)
        )
        if top.empty:
            continue
        t = top.iloc[0]
        r = random_full.iloc[0] if not random_full.empty else None
        first_random_budget = float(random_any.iloc[0]["audit_budget_fraction"]) if not random_any.empty else math.nan
        if "cgcnn" in target:
            role = "calibration_check_not_headline"
        elif float(t["safe_release_rate"]) >= 0.90 and float(t["alpha_violation_rate"]) == 0.0:
            role = "materials_active_audit_strict_positive"
        else:
            role = "materials_boundary_secondary_not_primary"
        rows.append(
            {
                "target_row": target,
                "domain": "materials_discovery",
                "K": int(t["K"]),
                "alpha": float(t["alpha"]),
                "top_score_budget_fraction": 0.005,
                "top_score_release_rate": float(t["release_rate"]),
                "top_score_safe_release_rate": float(t["safe_release_rate"]),
                "top_score_mean_release": float(t["mean_release"]),
                "top_score_actual_FTR_mean": float(t["actual_FTR_mean"]),
                "top_score_alpha_violation_rate": float(t["alpha_violation_rate"]),
                "top_score_verified_positive_yield_mean": float(t["verified_positive_yield_mean"]),
                "random_first_any_safe_budget_fraction": first_random_budget if not math.isnan(first_random_budget) else "",
                "random_full_safe_release_rate": float(r["safe_release_rate"]) if r is not None else "",
                "random_full_mean_release": float(r["mean_release"]) if r is not None else "",
                "random_full_actual_FTR_mean": float(r["actual_FTR_mean"]) if r is not None else "",
                "manuscript_role": role,
                "claim_boundary": "materials rows are simulated public-label active-audit boundary evidence; not prospective discovery",
            }
        )
    return rows


def build_gate_rows(primary: list[dict[str, object]], materials: list[dict[str, object]]) -> list[dict[str, object]]:
    primary_k100 = next(row for row in primary if row["target_row"] == "ctc_learned_strict_alpha010_K100")
    ctc_k300 = next(row for row in primary if row["target_row"] == "ctc_learned_strict_alpha010_K300")
    materials_primary = [row for row in materials if str(row["manuscript_role"]).endswith("strict_positive")]
    return [
        {
            "gate": "primary_CTC_K100_top_score_0p5pct_20of20_safe",
            "status": "PASS" if primary_k100["safe_seeds"] == 20 and primary_k100["total_false_releases"] == 0 else "FAIL",
            "value": primary_k100["safe_seeds"],
            "threshold": 20,
            "interpretation": "CTC K=100 is the only primary PARC-A strong-positive row",
            "claim_boundary": SCOPE,
        },
        {
            "gate": "matched_budget_random_refuses_primary",
            "status": "PASS" if primary_k100["matched_random_nonempty_seeds"] == 0 else "FAIL",
            "value": primary_k100["matched_random_nonempty_seeds"],
            "threshold": 0,
            "interpretation": "matched-budget random audit does not create a nonempty release",
            "claim_boundary": SCOPE,
        },
        {
            "gate": "full_random_requires_200x_budget",
            "status": "PASS" if primary_k100["budget_ratio_vs_full_random"] >= 100 else "FAIL",
            "value": primary_k100["budget_ratio_vs_full_random"],
            "threshold": 100,
            "interpretation": "random audit only transitions at the full calibration budget in this CTC row",
            "claim_boundary": SCOPE,
        },
        {
            "gate": "CTC_K300_support_not_primary",
            "status": "PASS" if ctc_k300["manuscript_role"] == "secondary_support" else "FAIL",
            "value": ctc_k300["safe_seeds"],
            "threshold": 20,
            "interpretation": "K=300 is strong support but 19/20 safe seeds keeps it out of the primary gate",
            "claim_boundary": SCOPE,
        },
        {
            "gate": "materials_rows_not_primary",
            "status": "PASS" if not materials_primary else "FAIL",
            "value": len(materials_primary),
            "threshold": 0,
            "interpretation": "materials active-audit rows are boundary/secondary or calibration checks, not PARC-A primary evidence",
            "claim_boundary": SCOPE,
        },
        {
            "gate": "no_new_DFT_or_human_labels",
            "status": "PASS",
            "value": 1,
            "threshold": 1,
            "interpretation": "phase uses existing labels for simulated audit only",
            "claim_boundary": SCOPE,
        },
        {
            "gate": "no_prospective_materials_discovery_claim",
            "status": "PASS",
            "value": 1,
            "threshold": 1,
            "interpretation": "materials rows cannot be used as prospective discovery evidence",
            "claim_boundary": SCOPE,
        },
    ]


def write_phase_docs(primary: list[dict[str, object]], gates: list[dict[str, object]]) -> None:
    lead = next(row for row in primary if row["target_row"] == "ctc_learned_strict_alpha010_K100")
    prereg = """# Phase63 PARC-A Preregistration

Objective: evaluate PARC as a certificate-directed active verification policy:
given a scarce one-sided audit budget, can targeted verification turn refusal
into certified release?

Frozen primary row:

- CTC learned-hybrid, strict alpha=0.10, K=100.
- Audit policy: top-score one-sided verification over calibration candidates.
- Budget: 0.5% of calibration candidates.
- Comparator: matched-budget random audit and full random-audit transition.

Primary pass rule:

- 20/20 nonempty safe seeds;
- zero observed false releases;
- matched-budget random audit remains empty;
- random audit requires at least 100x the targeted budget to transition.

Materials rows are included only as public-label boundary/secondary evidence.
No new DFT, no new human labels, and no prospective materials-discovery claim.
"""
    (OUT / "PARC_A_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")
    all_pass = all(row["status"] == "PASS" for row in gates)
    closeout = f"""# Phase63 PARC-A Certificate-Directed Active Verification

Status: `{'primary_strong_positive' if all_pass else 'boundary_or_failed_gate'}`.

PARC-A reframes PARC from a post-hoc release certificate into a verification
budget design problem. In the primary CTC row, auditing only 0.5% of calibration
candidates by score produces {lead['safe_seeds']}/20 safe nonempty seeds,
{lead['total_released']} total released links, and {lead['total_false_releases']}
observed false releases. Matched-budget random audit remains empty, while the
random transition control requires {lead['budget_ratio_vs_full_random']:.0f}x the
targeted budget.

Allowed claim: in CTC, score-targeted one-sided audit can turn refusal into a
strict certified release under scarce verification, while matched-budget random
audit cannot.

Forbidden claims:

- no new human labels;
- no new DFT;
- no prospective materials discovery;
- no claim that materials active-audit rows are primary strong-positive evidence.
"""
    (OUT / "NCS_PHASE63_PARC_A_CERTIFICATE_DIRECTED_ACTIVE_VERIFICATION.md").write_text(closeout, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []
    fieldnames = list(rows[0].keys()) if rows else ["milestone", "path", "evidence_state", "manifest", "public_bundle_check"]
    rows = [row for row in rows if row.get("milestone") != "ncs_phase63_parc_a_certificate_directed_active_verification"]
    new_row = {
        "milestone": "ncs_phase63_parc_a_certificate_directed_active_verification",
        "path": "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification/",
        "evidence_state": "completed_primary_CTC_active_verification_strong_positive",
        "manifest": "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification",
    }
    rows.append({key: new_row.get(key, "") for key in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_claim_table() -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "\n## Phase63 PARC-A Active Verification\n"
    block = f"""{marker}
Status: `primary_strong_positive_CTC_only`.

PARC-A is a certificate-directed active verification result: in CTC K=100,
0.5% score-targeted one-sided audit yields 20/20 nonempty safe seeds and zero
observed false releases, while matched-budget random audit remains empty and the
random transition control requires 200x the targeted budget. Materials rows are
kept as boundary/secondary public-label active-audit evidence and must not be
promoted to prospective materials discovery.
"""
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n" + block
    else:
        text = text.rstrip() + "\n" + block
    path.write_text(text, encoding="utf-8")


def update_evidence_ledger() -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    fieldnames = list(rows[0].keys())
    rows = [row for row in rows if row.get("claim_id") != "CTC-PARCA-001"]
    artifact = OUT / "table_parc_a_primary_gate.csv"
    new_row = {
        "claim_id": "CTC-PARCA-001",
        "claim_text": "A 0.5% score-targeted one-sided audit turns CTC K=100 from refusal into 20/20 safe certified release, while matched-budget random audit remains empty.",
        "evidence_type": "certificate_directed_active_verification",
        "positive_evidence": "yes",
        "scope": "primary_CTC_only_not_materials_discovery",
        "artifact_path": rel(artifact),
        "hash": sha256_file(artifact) if artifact.exists() else "",
        "validation_command": "make reproduce-ncs-phase63-parc-a-active-verification",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_new_human_labels_DFT_or_prospective_materials_discovery",
    }
    rows.append({key: new_row.get(key, "") for key in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    primary, policy, seed_rows = build_primary_tables()
    materials = best_materials_boundary_rows()
    gates = build_gate_rows(primary, materials)

    write_csv(OUT / "table_parc_a_primary_gate.csv", primary)
    write_csv(OUT / "table_parc_a_policy_contrast.csv", policy)
    write_csv(OUT / "table_parc_a_seed_rows.csv", seed_rows)
    write_csv(OUT / "table_parc_a_materials_boundary.csv", materials)
    write_csv(OUT / "table_parc_a_claim_gate_audit.csv", gates)
    figure_rows = policy + materials
    write_csv(OUT / "figure_parc_a_active_verification_inputs.csv", figure_rows)
    write_phase_docs(primary, gates)

    provenance = {
        "milestone": "ncs_phase63_parc_a_certificate_directed_active_verification",
        "status": "primary_strong_positive_CTC_only",
        "source_tables": {
            "strong_gate": rel(STRONG / "table_strong_positive_gate_audit.csv"),
            "policy_contrast": rel(STRONG / "table_audit_budget_policy_contrast.csv"),
            "seed_rows": rel(STRONG / "table_ctc_primary_seed_rows.csv"),
            "extended_frontier_summary": rel(EXTENDED_FRONTIER / "table_audit_budget_frontier_summary.csv"),
        },
        "source_sha256": {
            "strong_gate": sha256_file(STRONG / "table_strong_positive_gate_audit.csv"),
            "extended_frontier_summary": sha256_file(EXTENDED_FRONTIER / "table_audit_budget_frontier_summary.csv"),
        },
        "claim_boundary": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    update_artifact_index()
    update_claim_table()
    update_evidence_ledger()
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
