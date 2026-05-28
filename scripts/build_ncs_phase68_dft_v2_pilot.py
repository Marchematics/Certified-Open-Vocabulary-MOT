#!/usr/bin/env python3
"""Freeze a blinded DFT v2 pilot package.

This phase starts the independent DFT v2 line without creating DFT evidence.
It freezes a blinded WBM queue recomputation manifest, exports CIF inputs, and
records the execution/failure policy.  The local environment is inspected for a
primary VASP/atomate2/custodian workflow, but no DFT outcomes are generated.
"""

from __future__ import annotations

import bz2
import csv
import hashlib
import json
import math
import random
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from pymatgen.core import Structure

import build_materials_threshold_robustness as materials_threshold


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase68_dft_v2_pilot"
CIF_DIR = OUT / "cifs"

PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation/table_materials_t1_mlip_candidate_audit.csv"
PHASE53 = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_materials_candidate_level_chgnet_mace_audit.csv"
PRIVATE_STEP1 = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2")
PRIVATE_WBM_FULL = Path("/home/waas/paper_experiments/private/wbm_raw_full")
STEP_CACHE: dict[int, list[dict[str, Any]]] = {}

SCOPE = (
    "DFT_v2_blinded_recomputation_pilot_pre_outcome;"
    "frozen_WBM_queue_structures;"
    "no_DFT_outcomes;"
    "not_prospective_materials_discovery;"
    "not_t1_alpha_certificate"
)

ARM_TARGETS = {
    "parc_release_core": 100,
    "parc_release_boundary_t1_false": 60,
    "raw_only_extra_tail": 150,
    "public_sanity_stable": 25,
    "public_sanity_unstable": 25,
}


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


def material_step_and_index(material_id: str) -> tuple[int, int]:
    prefix, step, index = str(material_id).split("-")
    if prefix != "wbm":
        raise ValueError(f"unexpected material id: {material_id}")
    return int(step), int(index) - 1


def step_path(step: int) -> Path:
    if step == 1:
        return PRIVATE_STEP1
    return PRIVATE_WBM_FULL / f"step_{step}.json.bz2"


def load_structure(material_id: str) -> Structure:
    step, idx = material_step_and_index(material_id)
    if step not in STEP_CACHE:
        path = step_path(step)
        if not path.exists():
            raise FileNotFoundError(f"missing local structure cache for {material_id}: step {step}")
        with bz2.open(path, "rt") as handle:
            STEP_CACHE[step] = json.load(handle)["entries"]
    entries = STEP_CACHE[step]
    return Structure.from_dict(entries[idx]["structure"])


def structure_sha256(structure: Structure) -> str:
    return hashlib.sha256(structure.to(fmt="cif").encode("utf-8")).hexdigest()


def detect_execution_environment() -> tuple[str, list[str], str]:
    commands = ["vasp_std", "vasp_gam", "atomate2", "custodian", "sbatch", "qsub", "pw.x", "mpirun"]
    found = [command for command in commands if shutil.which(command)]
    primary_found = any(command in found for command in ["vasp_std", "vasp_gam", "atomate2", "custodian"])
    if primary_found:
        return (
            "primary_local_execution_possible_but_not_started",
            found,
            "A primary VASP/atomate2/custodian-compatible command was detected. This script still only freezes inputs.",
        )
    if "pw.x" in found:
        return (
            "primary_execution_blocked_no_vasp_atomate2_custodian_secondary_QE_detected_not_started",
            found,
            "Quantum ESPRESSO is available, but the DFT v2 primary workflow is VASP/atomate2/custodian; no local DFT process was started.",
        )
    return (
        "local_execution_blocked_no_primary_DFT_engine",
        found,
        "No primary DFT engine or scheduler entry point was detected; transfer this package to HPC/collaborator/cloud execution.",
    )


def boolish(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().eq("true")


def load_candidate_tables() -> pd.DataFrame:
    phase51 = pd.read_csv(PHASE51)
    phase51["material_id"] = phase51["material_id"].astype(str)
    phase53 = pd.read_csv(PHASE53).rename(columns={"candidate_id": "material_id"})
    phase53["material_id"] = phase53["material_id"].astype(str)
    merged = phase51.merge(
        phase53[
            [
                "material_id",
                "K",
                "chgnet_mace_consensus_label",
                "chgnet_mace_disagreement",
                "near_hull_t1_25mev",
                "near_hull_t1_50mev",
            ]
        ],
        on=["material_id", "K"],
        how="left",
    )
    merged = merged[merged["K"].eq(500)].drop_duplicates("material_id").copy()
    for col in ["parc_seed_count", "raw_topK_seed_count", "raw_topR_seed_count", "raw_only_tail_seed_count", "raw_rank"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    for col in ["stable_exact_t0", "stable_exact_t1_current_mp", "t1_false_conservative", "near_hull_25mev_t1"]:
        merged[col] = boolish(merged[col])
    merged["chgnet_mace_disagreement"] = boolish(merged["chgnet_mace_disagreement"].fillna(False))
    merged["near_hull_t1_25mev"] = boolish(merged["near_hull_t1_25mev"].fillna(False))
    return merged


def stable_sanity_frame(exclude_ids: set[str], n_each: int) -> pd.DataFrame:
    class Args:
        wbm_summary = "/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz"
        cgcnn_predictions = "/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz"
        alignn_predictions = "/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz"
        cgcnn_pred_col = "e_form_per_atom_mp2020_corrected_pred_ens"
        alignn_pred_col = "e_form_per_atom_alignn_ff"

    frame, _meta = materials_threshold.load_frame(Args)
    frame = frame.rename(columns={"material_id": "candidate_id"}).copy()
    frame["candidate_id"] = frame["candidate_id"].astype(str)
    frame = frame[~frame["candidate_id"].isin(exclude_ids)].copy()
    frame["_step"] = frame["candidate_id"].str.split("-").str[1].astype(int)
    frame = frame[frame["_step"].between(1, 5)].copy()
    stable = frame[frame["stable_exact"].astype(bool)].sort_values(["e_hull", "candidate_id"]).head(n_each).copy()
    unstable = frame[~frame["stable_exact"].astype(bool)].sort_values(["e_hull", "candidate_id"], ascending=[False, True]).head(n_each).copy()
    stable["dft_v2_arm"] = "public_sanity_stable"
    unstable["dft_v2_arm"] = "public_sanity_unstable"
    out = pd.concat([stable, unstable], ignore_index=True)
    out["material_id"] = out["candidate_id"]
    out["chemical_system"] = ""
    out["drift_class"] = "public_sanity_control"
    out["t1_false_conservative"] = False
    out["near_hull_25mev_t1"] = False
    out["chgnet_mace_consensus_label"] = ""
    out["raw_rank"] = ""
    out["alignn_score"] = out["alignn_score"]
    out["parc_seed_count"] = 0
    out["raw_topK_seed_count"] = 0
    out["raw_topR_seed_count"] = 0
    out["raw_only_tail_seed_count"] = 0
    out["stable_exact_t0"] = out["stable_exact"].astype(bool)
    out["stable_exact_t1_current_mp"] = ""
    out["e_above_hull_t0"] = out["e_hull"]
    out["e_above_hull_t1_current_mp"] = ""
    return out


def take_unique(frame: pd.DataFrame, n: int, used: set[str]) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for _, row in frame.iterrows():
        candidate_id = str(row["material_id"])
        if candidate_id in used:
            continue
        rows.append(row)
        used.add(candidate_id)
        if len(rows) >= n:
            break
    return pd.DataFrame(rows)


def select_candidates() -> tuple[pd.DataFrame, pd.DataFrame]:
    queue = load_candidate_tables()
    used: set[str] = set()
    selected_frames: list[pd.DataFrame] = []

    parc = queue[queue["parc_seed_count"].gt(0)].copy()
    core = parc[
        parc["stable_exact_t0"]
        & parc["stable_exact_t1_current_mp"]
        & parc["drift_class"].eq("stable_to_stable")
    ].copy()
    core["_consensus_rank"] = core["chgnet_mace_consensus_label"].eq("consensus_score_supported").astype(int)
    core = core.sort_values(["_consensus_rank", "parc_seed_count", "alignn_score", "material_id"], ascending=[False, False, False, True])
    core = take_unique(core, ARM_TARGETS["parc_release_core"], used)
    core["dft_v2_arm"] = "parc_release_core"
    selected_frames.append(core)

    boundary = parc[
        parc["t1_false_conservative"] | parc["near_hull_25mev_t1"] | parc["chgnet_mace_disagreement"]
    ].copy()
    boundary["_false_rank"] = boundary["t1_false_conservative"].astype(int)
    boundary = boundary.sort_values(["_false_rank", "parc_seed_count", "raw_rank", "material_id"], ascending=[False, False, True, True])
    boundary = take_unique(boundary, ARM_TARGETS["parc_release_boundary_t1_false"], used)
    boundary["dft_v2_arm"] = "parc_release_boundary_t1_false"
    selected_frames.append(boundary)

    tail = queue[queue["raw_only_tail_seed_count"].gt(0)].copy()
    tail = tail.sort_values(["raw_rank", "alignn_score", "material_id"], ascending=[True, False, True])
    tail = take_unique(tail, ARM_TARGETS["raw_only_extra_tail"], used)
    tail["dft_v2_arm"] = "raw_only_extra_tail"
    selected_frames.append(tail)

    sanity = stable_sanity_frame(used, ARM_TARGETS["public_sanity_stable"])
    stable = sanity[sanity["dft_v2_arm"].eq("public_sanity_stable")].head(ARM_TARGETS["public_sanity_stable"]).copy()
    unstable = sanity[sanity["dft_v2_arm"].eq("public_sanity_unstable")].head(ARM_TARGETS["public_sanity_unstable"]).copy()
    selected_frames.extend([stable, unstable])

    selected = pd.concat(selected_frames, ignore_index=True, sort=False)
    selected["material_id"] = selected["material_id"].astype(str)
    rawr = queue[queue["raw_topR_seed_count"].gt(0)].copy()
    parc_ids = set(parc["material_id"].astype(str))
    rawr_nonoverlap = rawr[~rawr["material_id"].astype(str).isin(parc_ids)]
    feasibility = pd.DataFrame(
        [
            {"arm": arm, "target_n": target, "selected_n": int(selected["dft_v2_arm"].eq(arm).sum()), "status": "selected"}
            for arm, target in ARM_TARGETS.items()
        ]
        + [
            {
                "arm": "matched_raw_topR_nonoverlap",
                "target_n": 50,
                "selected_n": int(len(rawr_nonoverlap)),
                "status": "not_available_raw_topR_coextensive_with_PARC_release",
            }
        ]
    )
    return selected, feasibility


def export_cifs(selected: pd.DataFrame) -> pd.DataFrame:
    CIF_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(6802)
    indexes = list(range(len(selected)))
    rng.shuffle(indexes)
    blind_ids = {idx: f"DFTV2-{order:04d}" for order, idx in enumerate(indexes, start=1)}
    rows: list[dict[str, Any]] = []
    for idx, row in selected.iterrows():
        material_id = str(row["material_id"])
        structure = load_structure(material_id)
        blind_id = blind_ids[idx]
        cif_rel = Path("cifs") / f"{blind_id}.cif"
        cif_path = OUT / cif_rel
        cif_path.write_text(structure.to(fmt="cif"), encoding="utf-8")
        rows.append(
            {
                "blinded_job_id": blind_id,
                "candidate_id": material_id,
                "dft_v2_arm": row["dft_v2_arm"],
                "formula": row.get("formula", structure.composition.reduced_formula),
                "chemical_system": row.get("chemical_system", ""),
                "K_source": row.get("K", ""),
                "raw_rank": row.get("raw_rank", ""),
                "parc_seed_count": row.get("parc_seed_count", 0),
                "raw_topK_seed_count": row.get("raw_topK_seed_count", 0),
                "raw_topR_seed_count": row.get("raw_topR_seed_count", 0),
                "raw_only_tail_seed_count": row.get("raw_only_tail_seed_count", 0),
                "t0_label": "stable" if bool(row.get("stable_exact_t0", False)) else "unstable_or_unresolved",
                "t1_label": row.get("stable_exact_t1_current_mp", ""),
                "drift_class": row.get("drift_class", ""),
                "t1_false_conservative": row.get("t1_false_conservative", ""),
                "alignn_score": row.get("alignn_score", ""),
                "chgnet_mace_consensus_label": row.get("chgnet_mace_consensus_label", ""),
                "cif_path": cif_rel.as_posix(),
                "cif_sha256": sha256_file(cif_path),
                "structure_sha256": structure_sha256(structure),
                "n_sites": int(structure.num_sites),
                "selection_freeze_status": "frozen_pre_outcome",
                "failure_policy": "failed_or_missing_jobs_count_not_certified_stable_false_for_conservative_FTR",
                "evidence_scope": SCOPE,
            }
        )
    return pd.DataFrame(rows).sort_values("blinded_job_id")


def write_protocols(manifest: pd.DataFrame, feasibility: pd.DataFrame) -> None:
    status, found, reason = detect_execution_environment()
    transfer_manifest = manifest[
        ["blinded_job_id", "formula", "n_sites", "cif_path", "cif_sha256", "failure_policy", "evidence_scope"]
    ].copy()
    transfer_manifest.to_csv(OUT / "dft_v2_blinded_transfer_manifest.csv", index=False)
    manifest.to_csv(OUT / "dft_v2_analysis_arm_key.csv", index=False)
    manifest.to_csv(OUT / "dft_v2_candidate_selection_manifest.csv", index=False)
    feasibility.to_csv(OUT / "table_dft_v2_arm_feasibility.csv", index=False)
    arm_summary = manifest.groupby("dft_v2_arm", dropna=False).size().reset_index(name="n_jobs")
    arm_summary.to_csv(OUT / "table_dft_v2_arm_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "local_execution_status": status,
                "detected_commands": "|".join(found),
                "processes_started": 0,
                "reason": reason,
                "claim_scope": "pre_outcome_package_only_not_DFT_evidence",
            }
        ]
    ).to_csv(OUT / "LOCAL_EXECUTION_STATUS.csv", index=False)
    pd.DataFrame(
        columns=[
            "blinded_job_id",
            "completed",
            "failed",
            "failure_reason",
            "final_energy_per_atom",
            "e_above_hull_ev_per_atom",
            "stable_exact",
            "stable_25mev",
            "workflow_engine",
            "outcome_file",
        ]
    ).to_csv(OUT / "DFT_OUTCOME_TEMPLATE.csv", index=False)
    (OUT / "SETTINGS_TEMPLATE_MP_COMPATIBLE.yaml").write_text(
        """dft_engine_primary: VASP
workflow: atomate2/custodian MP-compatible relaxation and static
functional: PBE-GGA
encut_eV: 520
kpoint_density: MPRelaxSet-compatible
electronic_convergence_eV: 1.0e-5
force_convergence_eV_per_angstrom: 0.02
relaxation: full cell and ionic relaxation
static_after_relax: true
compatibility_corrections: fixed MP-compatible correction scheme recorded before analysis
arm_blinding: DFT executor receives only dft_v2_blinded_transfer_manifest.csv and CIFs
failure_policy: failed_or_missing_jobs_count_not_certified_stable_false_for_conservative_FTR
""",
        encoding="utf-8",
    )
    (OUT / "DFT_V2_PILOT_PREREGISTRATION.md").write_text(
        f"""# DFT v2 Pilot Preregistration

Status: frozen before any DFT v2 outcome.

Primary endpoint after outcomes return: independently recomputed DFT false-release burden of PARC release arms versus raw-only extra-tail under a blinded frozen manifest.

Arms are selected by PARC status, raw-rank/tail status, t1 boundary status and public sanity-control labels. CHGNet/MACE support is recorded but is not used as ground truth.

Matched raw top-R non-overlap controls are unavailable in the current K=300/500 tables because matched raw top-R is coextensive with the PARC release set; this is recorded as an arm-feasibility limitation rather than duplicated as new DFT jobs.

Frozen jobs: {len(manifest)}.

No prospective materials discovery claim is allowed before outcomes are returned and analyzed under the conservative failure policy.
""",
        encoding="utf-8",
    )
    (OUT / "DFT_V2_PROTOCOL.md").write_text(
        """# DFT v2 Pilot Protocol

The DFT executor should receive only:

- `dft_v2_blinded_transfer_manifest.csv`
- the `cifs/` directory
- `SETTINGS_TEMPLATE_MP_COMPATIBLE.yaml`
- `DFT_OUTCOME_TEMPLATE.csv`

The executor should not receive `dft_v2_analysis_arm_key.csv` until all outcomes are frozen.

Conservative analysis policy:

1. `completed && stable_exact` counts as certified stable.
2. `completed && !stable_exact` counts as false.
3. failed, missing, invalid, duplicate or unconverged jobs count as not-certified-stable / false in the primary conservative FTR.
4. completed-only FTR may be reported only as a secondary diagnostic.
5. 25/50 meV near-hull thresholds may be reported only as sensitivity.
""",
        encoding="utf-8",
    )
    (OUT / "TRANSFER_PACKAGE_README.md").write_text(
        """# DFT v2 Blinded Transfer Package

This is a pre-outcome execution package. It is not DFT evidence.

Send only the blinded transfer manifest, CIF files, settings template and outcome template to the DFT executor. Keep the analysis arm key sealed until all calculations and failures are frozen.
""",
        encoding="utf-8",
    )
    (OUT / "NCS_PHASE68_DFT_V2_PILOT_CLOSEOUT.md").write_text(
        f"""# Phase68 DFT v2 Pilot

Status: `pre_outcome_blinded_manifest_frozen`.

Frozen jobs: `{len(manifest)}`.

Local execution status: `{status}`. {reason}

This milestone starts the DFT v2 pilot by freezing the blinded manifest and CIF package. It does not produce DFT outcomes, does not support prospective materials discovery, and does not alter A3 selection or manifests.
""",
        encoding="utf-8",
    )


def write_package_hashes() -> None:
    write_manifest(OUT)
    digest = hashlib.sha256((OUT / "MANIFEST_SHA256.txt").read_bytes()).hexdigest()
    (OUT / "PACKAGE_HASH.txt").write_text(f"{digest}  phase68_dft_v2_pilot_manifest_content_sha256\n", encoding="utf-8")
    pd.DataFrame(
        [{"package_hash_sha256": digest, "hash_target": "MANIFEST_SHA256.txt content", "evidence_scope": SCOPE}]
    ).to_csv(OUT / "table_dft_v2_package_hashes.csv", index=False)
    write_manifest(OUT)


def write_provenance(manifest: pd.DataFrame, feasibility: pd.DataFrame) -> None:
    provenance = {
        "phase": "phase68",
        "milestone": "ncs_phase68_dft_v2_pilot",
        "status": "pre_outcome_blinded_manifest_frozen",
        "jobs": int(len(manifest)),
        "arms": {str(k): int(v) for k, v in manifest.groupby("dft_v2_arm").size().to_dict().items()},
        "arm_feasibility": feasibility.to_dict(orient="records"),
        "source_artifacts": {
            "phase51_candidate_t1_mlip_audit": {
                "path": rel(PHASE51),
                "sha256": sha256_file(PHASE51),
            },
            "phase53_chgnet_mace_candidate_audit": {
                "path": rel(PHASE53),
                "sha256": sha256_file(PHASE53),
            },
            "private_wbm_structure_cache": {
                "path": "local_private_WBM_structure_cache_not_distributed",
                "sha256": "not_public_safe",
            },
        },
        "blinding": {
            "executor_manifest": "dft_v2_blinded_transfer_manifest.csv",
            "sealed_analysis_key": "dft_v2_analysis_arm_key.csv",
            "executor_manifest_contains_arm_labels": False,
        },
        "claim_scope": SCOPE,
        "overclaim_guardrails": [
            "do_not_claim_DFT_outcome",
            "do_not_claim_prospective_materials_discovery",
            "do_not_claim_t1_alpha_certificate",
            "do_not_modify_A3_selection_or_manifests",
        ],
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upsert_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    row = {
        "milestone": "ncs_phase68_dft_v2_pilot",
        "path": rel(OUT) + "/",
        "evidence_state": "pre_outcome_blinded_DFT_v2_pilot_package",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase68_dft_v2_pilot",
    }
    df = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=row.keys())
    df = df[df["milestone"] != row["milestone"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)


def append_once(path: Path, marker: str, text: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker not in existing:
        path.write_text(existing.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def update_docs(manifest: pd.DataFrame) -> None:
    upsert_artifact_index()
    append_once(
        ROOT / "docs/claim_table.md",
        "## Phase68 DFT v2 Pilot",
        f"""## Phase68 DFT v2 Pilot

Status: `pre_outcome_blinded_manifest_frozen`.

Phase68 freezes a blinded DFT v2 pilot package with `{len(manifest)}` WBM structures. It is execution infrastructure only: no DFT outcomes, no prospective materials-discovery claim, and no t1 alpha certificate are supported until outcomes are returned and analyzed under the conservative failure policy.
""",
    )
    append_once(
        ROOT / "README.md",
        "NCS Phase68 DFT v2 pilot",
        "- NCS Phase68 DFT v2 pilot: freezes a blinded WBM recomputation manifest and CIF package; pre-outcome execution infrastructure only, not DFT evidence.",
    )
    append_once(
        ROOT / "REPRODUCIBILITY.md",
        "## NCS Phase68 DFT v2 Pilot",
        """## NCS Phase68 DFT v2 Pilot

Reproduce with:

```bash
make reproduce-ncs-phase68-dft-v2-pilot
python scripts/validate_public_bundle.py outputs/milestones/ncs_phase68_dft_v2_pilot
```

This produces a pre-outcome blinded DFT package. It does not run VASP/QE or create DFT outcomes.
""",
    )
    ledger = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    df = pd.read_csv(ledger)
    claim_id = "MAT-DFTV2-PILOT-001"
    df = df[df["claim_id"] != claim_id]
    artifact = OUT / "dft_v2_blinded_transfer_manifest.csv"
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "claim_id": claim_id,
                        "claim_text": "A blinded DFT v2 pilot manifest and CIF package are frozen before outcomes.",
                        "evidence_type": "pre_outcome_DFT_execution_package",
                        "positive_evidence": "no",
                        "scope": "pre_outcome_package_only_not_DFT_evidence",
                        "artifact_path": rel(artifact),
                        "hash": sha256_file(artifact),
                        "validation_command": "make reproduce-ncs-phase68-dft-v2-pilot",
                        "status": "PASS",
                        "overclaim_guardrail": "do_not_claim_DFT_outcome_prospective_discovery_or_alpha_control",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    df.to_csv(ledger, index=False)


def patch_makefile() -> None:
    path = ROOT / "Makefile"
    text = path.read_text(encoding="utf-8")
    target = "reproduce-ncs-phase68-dft-v2-pilot"
    if target not in text:
        text = text.replace(".PHONY: test validate-public-bundle verify-manifest", ".PHONY: test validate-public-bundle verify-manifest " + target)
        text = text.rstrip() + f"\n\n{target}:\n\t$(PYTHON) scripts/build_ncs_phase68_dft_v2_pilot.py\n"
    validation_line = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase68_dft_v2_pilot\n"
    if validation_line not in text:
        marker = "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65c_materials_active_audit_attempt\n"
        if marker in text:
            text = text.replace(marker, marker + validation_line)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    selected, feasibility = select_candidates()
    manifest = export_cifs(selected)
    write_protocols(manifest, feasibility)
    write_provenance(manifest, feasibility)
    write_package_hashes()
    update_docs(manifest)
    patch_makefile()
    write_root_manifest()
    print(
        json.dumps(
            {
                "status": "pre_outcome_blinded_manifest_frozen",
                "out_dir": rel(OUT),
                "jobs": int(len(manifest)),
                "arms": manifest.groupby("dft_v2_arm").size().to_dict(),
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
