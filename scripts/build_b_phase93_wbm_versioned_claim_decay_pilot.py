#!/usr/bin/env python3
"""Build B Phase93 WBM versioned current-reference claim-decay pilot.

This phase uses the frozen B Phase87 WBM registry and the existing public
t0/t1 WBM/current-MP join to quantify versioned reference drift for the WBM
subset. It is not independent DFT, not prospective discovery, and not A-paper
main evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "outputs/milestones/b_phase87_minimal_claim_registry/table_phase87_minimal_claim_registry.csv"
T0T1 = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_t1_label_join.csv"
OUT = ROOT / "outputs/milestones/b_phase93_wbm_versioned_claim_decay_pilot"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "b_line_wbm_versioned_claim_decay_pilot;"
    "public_t0_t1_reference_drift;"
    "current_mp_public_reference;"
    "not_independent_DFT;"
    "not_prospective_discovery;"
    "not_A_paper_main_evidence"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def cp_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 1.0
    alpha = 1.0 - confidence
    low = 0.0 if successes == 0 else float(beta.ppf(alpha / 2.0, successes, total - successes + 1))
    high = 1.0 if successes == total else float(beta.ppf(1.0 - alpha / 2.0, successes + 1, total - successes))
    return low, high


def load_rows() -> pd.DataFrame:
    registry = pd.read_csv(REGISTRY)
    registry = registry[registry["source_family"].eq("matbench_discovery_wbm")].copy()
    registry["material_id"] = registry["claim_uid"].str.extract(r"::(.+)$", expand=False)
    t0t1 = pd.read_csv(T0T1)
    joined = registry.merge(t0t1, on="material_id", how="left", suffixes=("_registry", ""), validate="one_to_one")
    if joined["formula"].isna().any():
        missing = joined.loc[joined["formula"].isna(), "claim_uid"].head().tolist()
        raise RuntimeError(f"WBM registry rows missing from t0/t1 join: {missing}")

    joined["claim_decay_status"] = joined["drift_class"].map(
        {
            "stable_to_stable": "retained_current_reference_stable",
            "stable_to_unstable": "decayed_to_current_reference_unstable",
            "stable_to_unresolved": "unresolved_current_reference_label",
        }
    ).fillna("other_or_unresolved")
    joined["is_decayed"] = joined["drift_class"].eq("stable_to_unstable")
    joined["is_unresolved"] = joined["drift_class"].eq("stable_to_unresolved") | joined["t1_label_status"].ne(
        "labelable_current_MP_hull"
    )
    joined["is_retained_stable"] = joined["drift_class"].eq("stable_to_stable")
    joined["evidence_scope"] = SCOPE
    return joined


def build_tables(joined: pd.DataFrame) -> dict[str, pd.DataFrame]:
    row_cols = [
        "claim_uid",
        "source_family",
        "paper_or_leaderboard_id",
        "source_snapshot_date",
        "original_rank_or_priority",
        "material_id",
        "reduced_formula",
        "formula",
        "chemical_system",
        "prototype_or_wyckoff_label",
        "original_energy_or_margin",
        "stable_exact_t0",
        "e_above_hull_t0",
        "e_above_hull_t1_current_mp",
        "stable_exact_t1_current_mp",
        "t1_label_status",
        "drift_class",
        "claim_decay_status",
        "is_decayed",
        "is_unresolved",
        "K300_PARC_release_seed_count",
        "K500_PARC_release_seed_count",
        "K300_raw_topK_requested_budget_seed_count",
        "K500_raw_topK_requested_budget_seed_count",
        "t1_label_source",
        "evidence_scope",
    ]
    rows = joined[row_cols].copy()

    labelable = joined[~joined["is_unresolved"]].copy()
    decayed = int(labelable["is_decayed"].sum())
    retained = int(labelable["is_retained_stable"].sum())
    low, high = cp_interval(decayed, len(labelable))
    summary = pd.DataFrame(
        [
            {
                "source_family": "matbench_discovery_wbm",
                "registry_rows": len(joined),
                "joined_to_t0_t1_rows": int(joined["formula"].notna().sum()),
                "labelable_current_reference_rows": len(labelable),
                "retained_current_reference_stable": retained,
                "decayed_to_current_reference_unstable": decayed,
                "unresolved_current_reference_label": int(joined["is_unresolved"].sum()),
                "decay_fraction_labelable": decayed / len(labelable) if len(labelable) else 0.0,
                "decay_fraction_labelable_cp95_low": low,
                "decay_fraction_labelable_cp95_high": high,
                "evidence_state": "public_versioned_reference_decay_pilot_completed_not_independent_DFT",
                "evidence_scope": SCOPE,
            }
        ]
    )

    by_system = (
        joined.groupby("chemical_system", dropna=False)
        .agg(
            rows=("claim_uid", "size"),
            decayed=("is_decayed", "sum"),
            unresolved=("is_unresolved", "sum"),
            retained_stable=("is_retained_stable", "sum"),
        )
        .reset_index()
    )
    by_system["labelable_rows"] = by_system["rows"] - by_system["unresolved"]
    by_system["decay_fraction_labelable"] = by_system.apply(
        lambda r: float(r["decayed"] / r["labelable_rows"]) if r["labelable_rows"] else 0.0, axis=1
    )
    by_system["evidence_scope"] = SCOPE

    gate = pd.DataFrame(
        [
            {
                "claim_gate": "b_phase93_wbm_versioned_claim_decay_pilot",
                "status": "public_versioned_reference_decay_pilot_completed_not_independent_DFT",
                "positive_evidence": "weak_public_reference_pilot_only",
                "registry_rows": len(joined),
                "decayed_to_current_reference_unstable": decayed,
                "unresolved_current_reference_label": int(joined["is_unresolved"].sum()),
                "allowed_current_claim": "Phase93 reports public t0/t1 current-reference drift for the frozen WBM registry subset.",
                "forbidden_current_claim": "Do not claim independent DFT validation, exact-structure source claim decay, prospective discovery, A-paper main evidence, or physical ground truth.",
                "evidence_scope": SCOPE,
            }
        ]
    )

    figure = summary[
        [
            "source_family",
            "registry_rows",
            "labelable_current_reference_rows",
            "retained_current_reference_stable",
            "decayed_to_current_reference_unstable",
            "unresolved_current_reference_label",
            "decay_fraction_labelable",
            "decay_fraction_labelable_cp95_low",
            "decay_fraction_labelable_cp95_high",
            "evidence_scope",
        ]
    ].copy()
    return {"rows": rows, "summary": summary, "by_system": by_system, "gate": gate, "figure": figure}


def write_outputs(tables: dict[str, pd.DataFrame]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables["rows"].to_csv(OUT / "table_phase93_wbm_versioned_claim_decay_rows.csv", index=False)
    tables["summary"].to_csv(OUT / "table_phase93_wbm_versioned_claim_decay_summary.csv", index=False)
    tables["by_system"].to_csv(OUT / "table_phase93_wbm_decay_by_chemical_system.csv", index=False)
    tables["gate"].to_csv(OUT / "table_phase93_claim_gate.csv", index=False)
    tables["figure"].to_csv(OUT / "figure_phase93_wbm_versioned_claim_decay_inputs.csv", index=False)


def write_docs(tables: dict[str, pd.DataFrame]) -> None:
    summary = tables["summary"].iloc[0]
    readme = f"""# B Phase93 WBM Versioned Claim-Decay Pilot

Status: `public_versioned_reference_decay_pilot_completed_not_independent_DFT`.

Phase93 joins the frozen B Phase87 WBM registry subset to the existing WBM
t0/current-MP t1 public-reference snapshot. It reports versioned public-label
drift only.

Key pilot facts:

- registry rows: `{int(summary['registry_rows'])}`;
- labelable current-reference rows: `{int(summary['labelable_current_reference_rows'])}`;
- stable-to-unstable current-reference rows: `{int(summary['decayed_to_current_reference_unstable'])}`;
- unresolved rows: `{int(summary['unresolved_current_reference_label'])}`;
- labelable decay fraction: `{float(summary['decay_fraction_labelable']):.6f}`.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = """# Phase93 Protocol: WBM Versioned Claim-Decay Pilot

Inputs:

- B Phase87 frozen WBM registry rows;
- existing WBM t0/current-MP t1 public-reference join.

Procedure:

1. Extract WBM material IDs from frozen registry claim IDs.
2. Join one-to-one to the existing t0/t1 public-reference table.
3. Report stable-to-stable, stable-to-unstable and unresolved rows.
4. Do not claim independent DFT, exact-structure source claim decay, or
   prospective discovery.
"""
    (OUT / "PHASE93_WBM_VERSIONED_CLAIM_DECAY_PROTOCOL.md").write_text(protocol, encoding="utf-8")


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
        "milestone": "b_phase93_wbm_versioned_claim_decay_pilot",
        "path": "outputs/milestones/b_phase93_wbm_versioned_claim_decay_pilot/",
        "evidence_state": "public_versioned_reference_decay_pilot_completed_not_independent_DFT",
        "manifest": "outputs/milestones/b_phase93_wbm_versioned_claim_decay_pilot/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase93_wbm_versioned_claim_decay_pilot",
        "notes": "B-line WBM t0/t1 public-reference decay pilot; not independent DFT.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(
        ARTIFACT_INDEX, index=False
    )


def update_ledger() -> None:
    row = {
        "claim_id": "B-PHASE93-WBM-VERSIONED-CLAIM-DECAY-001",
        "claim_text": "Phase93 reports public t0/t1 current-reference drift for the frozen WBM registry subset.",
        "evidence_type": "public_versioned_reference_decay_pilot",
        "positive_evidence": "weak_smoke_only",
        "scope": "public_t0_t1_reference_drift;not_independent_DFT",
        "artifact_path": "outputs/milestones/b_phase93_wbm_versioned_claim_decay_pilot/table_phase93_wbm_versioned_claim_decay_summary.csv",
        "hash": sha256_file(OUT / "table_phase93_wbm_versioned_claim_decay_summary.csv"),
        "validation_command": "make reproduce-b-phase93-wbm-versioned-claim-decay-pilot",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_independent_DFT_exact_structure_claim_decay_or_A_paper_main_evidence_from_public_t0_t1_pilot",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase93 B-Line WBM Versioned Claim-Decay Pilot\n\nStatus: `public_versioned_reference_decay_pilot_completed_not_independent_DFT`.\n\nPhase93 joins the frozen B-line WBM registry subset to the existing public\nWBM t0/current-MP t1 reference snapshot and reports stable-to-stable,\nstable-to-unstable and unresolved current-reference rows. It is public\nversioned-reference drift evidence only, not independent DFT validation,\nexact-structure source claim decay, prospective discovery, A-paper main\nevidence, or physical ground truth.\n"""
    marker = "## Phase93 B-Line WBM Versioned Claim-Decay Pilot"
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
    joined = load_rows()
    tables = build_tables(joined)
    write_outputs(tables)
    write_docs(tables)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase93-b] wrote {rel(OUT)}")
    print("[phase93-b] status=public_versioned_reference_decay_pilot_completed_not_independent_DFT")


if __name__ == "__main__":
    main()
