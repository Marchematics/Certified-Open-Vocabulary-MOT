#!/usr/bin/env python3
"""Build the A3-v4 DFT execution package from frozen pre-outcome manifests.

This script deliberately does not modify A3 selection or manifest inputs:
`selection_frozen_v4.csv`, `dft_job_manifest_v4_addendum.csv`, and
`dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv` are read-only inputs.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"
PACKAGE = MILESTONE / "A3_DFT_RUN_PACKAGE"
GEN_ZIP = Path("/home/waas/paper_experiments/private/mattergen_v4_generation/pilot_5k_3gpu_merged/generated_crystals_cif.zip")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(path: Path, *, package_hash: bool = False) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name not in {"MANIFEST_SHA256.txt", "PACKAGE_HASH.txt"}:
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    manifest_text = "\n".join(rows) + "\n"
    (path / "MANIFEST_SHA256.txt").write_text(manifest_text, encoding="utf-8")
    if package_hash:
        digest = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
        (path / "PACKAGE_HASH.txt").write_text(
            f"{digest}  A3_DFT_RUN_PACKAGE manifest-content-sha256\n",
            encoding="utf-8",
        )


def write_root_manifest() -> None:
    rows: list[str] = []
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


def assert_no_dft_outcomes() -> None:
    for manifest_name in [
        "dft_job_manifest_v4.csv",
        "dft_job_manifest_v4_addendum.csv",
        "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv",
    ]:
        path = MILESTONE / manifest_name
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "outcome_available" in df.columns and df["outcome_available"].astype(bool).any():
            raise RuntimeError(f"{manifest_name} contains outcome_available=True; package must not be rebuilt as pre-outcome.")
        if "outcome_file" in df.columns and df["outcome_file"].fillna("").astype(str).str.strip().ne("").any():
            raise RuntimeError(f"{manifest_name} contains outcome_file values; package must not be rebuilt as pre-outcome.")
    for pattern in ["dft_results*.csv", "dft_results*.json", "vasp_outputs", "qe_outputs", "relax_outputs"]:
        for path in MILESTONE.glob(pattern):
            if path.is_file() and path.stat().st_size > 0:
                raise RuntimeError(f"Found possible DFT outcome file: {path.relative_to(ROOT)}")
            if path.is_dir() and any(path.rglob("*")):
                raise RuntimeError(f"Found possible DFT outcome directory: {path.relative_to(ROOT)}")


def executable_status() -> tuple[str, list[str], str]:
    candidates = ["vasp_std", "vasp_gam", "pw.x", "sbatch", "qsub", "mpirun"]
    found = [cmd for cmd in candidates if shutil.which(cmd)]
    if any(cmd in found for cmd in ["vasp_std", "vasp_gam", "pw.x"]):
        return "local_execution_possible_engine_detected", found, "A local DFT executable was detected; use the package with the local/private compute wrapper."
    return "local_execution_blocked_no_DFT_engine_or_scheduler", found, "No VASP/QE executable or scheduler command was detected in PATH; transfer this package to HPC, collaborator, or cloud DFT."


def member_from_ref(ref: str) -> str:
    return str(ref).rsplit("::", 1)[-1]


def safe_name(text: object) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(text))


def load_source_manifests() -> tuple[pd.DataFrame, pd.DataFrame]:
    addendum = pd.read_csv(MILESTONE / "dft_job_manifest_v4_addendum.csv")
    release = addendum[addendum["arm"].eq("PARC-release-full")].copy()
    extra = pd.read_csv(MILESTONE / "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv").copy()
    if len(release) != 75:
        raise RuntimeError(f"Expected 75 PARC-release-full jobs, found {len(release)}")
    if len(extra) != 25:
        raise RuntimeError(f"Expected 25 raw_top100_extra_tail jobs, found {len(extra)}")
    return release, extra


def copy_cifs(release: pd.DataFrame, extra: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not GEN_ZIP.exists():
        raise FileNotFoundError("private MatterGen CIF zip is required to build the DFT run package")
    rows_by_arm = [("PARC-release-full", release), ("raw_top100_extra_tail", extra)]
    updated_frames: list[pd.DataFrame] = []
    with ZipFile(GEN_ZIP) as archive:
        members = set(archive.namelist())
        for arm, frame in rows_by_arm:
            out_dir = PACKAGE / "cifs" / arm
            out_dir.mkdir(parents=True, exist_ok=True)
            records: list[dict] = []
            for _, row in frame.iterrows():
                member = member_from_ref(str(row["structure_ref"]))
                if member not in members:
                    raise FileNotFoundError(f"{member} missing from generated CIF zip")
                job_id = safe_name(row["dft_job_id"])
                candidate_id = safe_name(row["candidate_id"])
                cif_rel = Path("cifs") / arm / f"{job_id}__{candidate_id}.cif"
                cif_path = PACKAGE / cif_rel
                cif_path.write_bytes(archive.read(member))
                record = row.to_dict()
                record["package_cif_path"] = cif_rel.as_posix()
                record["package_cif_sha256"] = sha256_file(cif_path)
                record["source_cif_member"] = member
                record["package_role"] = "DFT_input_structure"
                records.append(record)
            updated_frames.append(pd.DataFrame(records))
    return updated_frames[0], updated_frames[1]


def write_protocol_files(package_manifest: pd.DataFrame, release: pd.DataFrame, extra: pd.DataFrame) -> None:
    status, commands, reason = executable_status()
    settings = """# A3-v4 DFT settings template
dft_engine: VASP-or-equivalent-MP-compatible-engine
input_set: MPRelaxSet-compatible
functional: PBE-GGA
encut_ev: 520
kpoint_policy: MPRelaxSet default or fixed equivalent recorded per job
electronic_convergence_ev: 1.0e-5
force_convergence_ev_per_angstrom: 0.02
spin_policy: same frozen magnetic-element rule for all arms
relaxation_policy: full cell plus ionic relaxation
static_calculation_policy: final static calculation after relaxation
compatibility_corrections: fixed Materials Project-compatible correction scheme if used
failure_policy: one standard rerun; unresolved failures count as not-certified-stable / false for FTR
outcome_required_fields:
  - dft_job_id
  - candidate_id
  - arm
  - completed
  - failed
  - failure_reason
  - final_energy_per_atom
  - e_above_hull_ev_per_atom
  - stable_exact
  - stable_25mev
"""
    (PACKAGE / "SETTINGS_TEMPLATE.yaml").write_text(settings, encoding="utf-8")
    protocol = f"""# A3-v4 DFT Run Protocol

Status: pre-outcome DFT execution package. This is not DFT evidence.

## Frozen inputs

- `selection_frozen_v4.csv` is not modified by this package.
- PARC release source: `dft_job_manifest_v4_addendum.csv`, arm `PARC-release-full`.
- Extra-tail source: `dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv`, arm `raw_top100_extra_tail`.
- Package composition: {len(release)} PARC-release CIFs and {len(extra)} raw-top100 extra-tail CIFs.

## Execution

Run all candidates with the same DFT engine and settings. The settings template is `SETTINGS_TEMPLATE.yaml`.
All jobs must use the same relaxation, static calculation and correction policy across arms.

## Conservative outcome policy

Failed, unconverged or missing jobs are counted as not-certified-stable / false for FTR in the conservative primary analysis.
Completed-only summaries may be reported only as secondary diagnostics.

## Claim boundary

No prospective DFT evidence or prospective materials discovery claim is allowed until outcome files are returned and analyzed.
The package hash must be recorded before DFT execution.
"""
    (PACKAGE / "DFT_PROTOCOL.md").write_text(protocol, encoding="utf-8")
    status_csv = pd.DataFrame(
        [
            {
                "package": "A3_DFT_RUN_PACKAGE",
                "local_execution_status": status,
                "detected_commands": "|".join(commands),
                "processes_started": 0 if status.startswith("local_execution_blocked") else "",
                "reason": reason,
                "claim_scope": "execution_package_only_not_DFT_evidence",
            }
        ]
    )
    status_csv.to_csv(PACKAGE / "LOCAL_EXECUTION_STATUS.csv", index=False)
    (PACKAGE / "LOCAL_EXECUTION_STATUS.md").write_text(
        f"# Local Execution Status\n\n"
        f"Status: `{status}`.\n\n"
        f"Detected commands: `{('|'.join(commands) or 'none')}`.\n\n"
        f"{reason}\n\n"
        f"No DFT outcome is included in this package.\n",
        encoding="utf-8",
    )
    outcome_template = pd.DataFrame(
        columns=[
            "dft_job_id",
            "candidate_id",
            "arm",
            "completed",
            "failed",
            "failure_reason",
            "final_energy_per_atom",
            "e_above_hull_ev_per_atom",
            "stable_exact",
            "stable_25mev",
            "outcome_file",
        ]
    )
    outcome_template.to_csv(PACKAGE / "DFT_OUTCOME_TEMPLATE.csv", index=False)
    package_manifest.to_csv(PACKAGE / "package_job_manifest.csv", index=False)
    readme = f"""# A3 DFT Run Package

This package contains the frozen structure inputs for the A3-v4 MatterGen DFT follow-up execution step.

Contents:

- `cifs/PARC-release-full/`: {len(release)} PARC-release CIF files.
- `cifs/raw_top100_extra_tail/`: {len(extra)} raw-top100 extra-tail CIF files.
- `manifests/PARC_release_full_manifest.csv`
- `manifests/raw_top100_extra_tail_manifest.csv`
- `package_job_manifest.csv`
- `DFT_PROTOCOL.md`
- `SETTINGS_TEMPLATE.yaml`
- `DFT_OUTCOME_TEMPLATE.csv`
- `LOCAL_EXECUTION_STATUS.*`
- `MANIFEST_SHA256.txt`
- `PACKAGE_HASH.txt`

Claim boundary: this is an execution package only. It is not DFT evidence and does not support a prospective materials discovery claim before outcomes are returned and analyzed under the conservative failure policy.
"""
    (PACKAGE / "README.md").write_text(readme, encoding="utf-8")


def update_repo_indexes() -> None:
    artifact_path = ROOT / "outputs" / "artifact_index.csv"
    artifact = pd.read_csv(artifact_path)
    if "mattergen_a3_dft_run_package" not in set(artifact["milestone"].astype(str)):
        artifact.loc[len(artifact)] = {
            "milestone": "mattergen_a3_dft_run_package",
            "path": "outputs/milestones/mattergen_parc_prospective_dft_followup/A3_DFT_RUN_PACKAGE/",
            "evidence_state": "DFT_execution_package_no_outcomes_not_positive_evidence",
            "manifest": "outputs/milestones/mattergen_parc_prospective_dft_followup/A3_DFT_RUN_PACKAGE/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/mattergen_parc_prospective_dft_followup/A3_DFT_RUN_PACKAGE",
        }
        artifact.to_csv(artifact_path, index=False)

    makefile = ROOT / "Makefile"
    make = makefile.read_text(encoding="utf-8")
    if "reproduce-a3-dft-run-package" not in make:
        make = make.replace(
            "reproduce-a3-v4-phase29c-extra-tail-manifest:\n\t$(PYTHON) scripts/build_a3_v4_phase29c_extra_tail_manifest.py\n",
            "reproduce-a3-v4-phase29c-extra-tail-manifest:\n\t$(PYTHON) scripts/build_a3_v4_phase29c_extra_tail_manifest.py\n\n"
            "reproduce-a3-dft-run-package:\n\t$(PYTHON) scripts/build_a3_dft_run_package.py\n",
        )
        make = make.replace(
            "reproduce-a3-v4-phase29c-extra-tail-manifest",
            "reproduce-a3-v4-phase29c-extra-tail-manifest reproduce-a3-dft-run-package",
            1,
        )
        makefile.write_text(make, encoding="utf-8")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    if "A3 DFT run package" not in readme_text:
        readme_text += (
            "\n- A3 DFT run package: `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_DFT_RUN_PACKAGE/` "
            "contains 75 PARC-release CIFs, 25 raw-top100 extra-tail CIFs, frozen manifests, protocol/settings templates, and package hashes. "
            "It contains no DFT outcomes and no prospective materials claim.\n"
        )
        readme.write_text(readme_text, encoding="utf-8")

    repro = ROOT / "REPRODUCIBILITY.md"
    repro_text = repro.read_text(encoding="utf-8")
    if "reproduce-a3-dft-run-package" not in repro_text:
        repro_text += (
            "\n## A3 DFT run package\n\n"
            "Run `make reproduce-a3-dft-run-package` after Phase29c to rebuild the DFT execution package. "
            "The package contains CIF inputs and frozen manifests only; it does not modify `selection_frozen_v4.csv` and includes no DFT outcomes.\n"
        )
        repro.write_text(repro_text, encoding="utf-8")


def main() -> None:
    assert_no_dft_outcomes()
    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    (PACKAGE / "manifests").mkdir(parents=True, exist_ok=True)
    release, extra = load_source_manifests()
    release_pkg, extra_pkg = copy_cifs(release, extra)
    release_pkg.to_csv(PACKAGE / "manifests" / "PARC_release_full_manifest.csv", index=False)
    extra_pkg.to_csv(PACKAGE / "manifests" / "raw_top100_extra_tail_manifest.csv", index=False)
    combined = pd.concat([release_pkg, extra_pkg], ignore_index=True)
    combined.insert(0, "package_freeze_timestamp", datetime.now(timezone.utc).isoformat())
    combined["completed_positive_result"] = False
    combined["claim_scope"] = "DFT_execution_package_only_no_outcomes"
    write_protocol_files(combined, release_pkg, extra_pkg)
    write_manifest(PACKAGE, package_hash=True)
    update_repo_indexes()
    stale_hash = MILESTONE / "PACKAGE_HASH.txt"
    if stale_hash.exists():
        stale_hash.unlink()
    write_manifest(MILESTONE)
    write_root_manifest()


if __name__ == "__main__":
    main()
