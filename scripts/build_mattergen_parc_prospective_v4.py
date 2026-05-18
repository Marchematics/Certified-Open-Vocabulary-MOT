#!/usr/bin/env python3
"""Build the A3-v4 MatterGen + consensus-scorer prospective DFT gate.

This artifact is deliberately conservative.  It freezes the intended
frontier-generator protocol and records local executability checks, but it
does not fabricate generated candidates, PARC release arms, DFT manifests or
DFT outcomes.  A nonempty `selection_frozen_v4.csv` may only appear after a
real MatterGen candidate pool, public-label exclusion table, CHGNet/MACE
consensus scores, and PARC release gate all exist before DFT outcome access.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_OUT = Path("outputs/milestones/mattergen_parc_prospective_dft_followup")

MATTERGEN_ENV = Path("/home/waas/paper_experiments/private/mattergen_v4_conda")

RAW_CANDIDATE_COLUMNS = [
    "candidate_id",
    "generator",
    "generator_mode",
    "formula",
    "reduced_formula",
    "chemical_system",
    "anonymous_formula",
    "n_sites",
    "space_group",
    "structure_ref",
    "structure_sha256",
    "generation_rank",
    "generation_status",
]

PUBLIC_FREE_COLUMNS = RAW_CANDIDATE_COLUMNS + [
    "public_label_status",
    "public_label_sources_checked",
    "structure_match_status",
    "eligible_for_A3_v4",
]

SCORE_COLUMNS = [
    "candidate_id",
    "formula",
    "structure_ref",
    "structure_sha256",
    "score_model",
    "score_model_version",
    "score_status",
    "energy_per_atom",
    "formation_energy_proxy",
    "predicted_e_above_hull_proxy",
    "score",
    "raw_rank",
]

CONSENSUS_COLUMNS = [
    "candidate_id",
    "formula",
    "structure_ref",
    "structure_sha256",
    "chgnet_score",
    "mace_score",
    "consensus_score",
    "consensus_rule",
    "score_status",
    "raw_rank",
]

SELECTION_COLUMNS = [
    "arm",
    "candidate_id",
    "selected_for_dft",
    "dft_job_id",
    "selection_rank",
    "endpoint_id",
    "selection_rule",
    "score_rank",
    "parc_release_flag",
    "raw_topK_member",
    "reserve_order",
    "evidence_status",
    "primary_or_reserve",
    "frozen_model_score",
    "structure_ref",
    "structure_sha256",
]

DFT_JOB_COLUMNS = [
    "dft_job_id",
    "candidate_id",
    "arm",
    "endpoint_id",
    "structure_ref",
    "structure_sha256",
    "dft_engine",
    "input_status",
    "failure_policy",
    "selected_before_DFT_outcome",
    "outcome_available",
    "outcome_file",
    "evidence_status",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_command(command: list[str], timeout: int = 30) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return "blocked_executable_missing", str(exc)
    except subprocess.TimeoutExpired as exc:
        return "blocked_timeout", (exc.stdout or "")[-500:] + (exc.stderr or "")[-500:]
    status = "completed" if completed.returncode == 0 else f"blocked_exit_{completed.returncode}"
    detail = (completed.stdout + completed.stderr).strip().replace("\n", " ")
    return status, detail[:800]


def sanitize_detail(text: str, env_path: Path | None = None) -> str:
    """Remove local absolute paths from public-safe status text."""
    replacements = {
        str(Path.home()): "<HOME>",
        "/home/waas/paper_experiments/private": "<PRIVATE_WORKDIR>",
        "/home/waas/paper_experiments": "<WORKDIR>",
        "/root": "<HOME>",
    }
    if env_path is not None:
        replacements[str(env_path)] = "<MATTERGEN_ENV>"
    out = str(text)
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        out = out.replace(old, new)
    return out


def detect_mattergen(env_path: Path) -> tuple[str, str]:
    python_bin = env_path / "bin/python"
    command_bin = env_path / "bin/mattergen-generate"
    if not python_bin.exists():
        return "blocked_env_missing", sanitize_detail(f"{python_bin} does not exist", env_path)
    status, detail = run_command(
        [
            str(python_bin),
            "-c",
            "import mattergen, torch; print('mattergen_import_ok', getattr(mattergen, '__version__', 'unknown'), torch.__version__)",
        ],
        timeout=45,
    )
    if status != "completed":
        return status, sanitize_detail(detail, env_path)
    if not command_bin.exists():
        return "blocked_entrypoint_missing", "mattergen imports, but mattergen-generate entrypoint is absent"
    help_status, help_detail = run_command([str(command_bin), "--help"], timeout=45)
    if help_status != "completed":
        return help_status, sanitize_detail(help_detail, env_path)
    return "completed_smoke_import_and_help", sanitize_detail(help_detail[:800], env_path)


def detect_mace() -> tuple[str, str]:
    code = """
from pymatgen.core import Lattice, Structure
from pymatgen.io.ase import AseAtomsAdaptor
from mace.calculators import mace_mp
import torch, math
s = Structure(Lattice.cubic(5.64), ['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]])
atoms = AseAtomsAdaptor.get_atoms(s)
calc = mace_mp(model='small', device='cuda' if torch.cuda.is_available() else 'cpu', default_dtype='float32')
atoms.calc = calc
energy = float(atoms.get_potential_energy())
print('mace_smoke_energy', energy, 'torch_cuda', torch.cuda.is_available())
assert math.isfinite(energy) and abs(energy) < 1e6
"""
    status, detail = run_command(["python", "-c", code], timeout=120)
    return status, sanitize_detail(detail)


def empty_csv(path: Path, columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)


def build_protocol() -> dict:
    return {
        "trial_name": "mattergen_parc_prospective_dft_followup_v4",
        "evidence_status": "protocol_and_environment_gate_only",
        "generator": {
            "primary": "MatterGen",
            "candidate_pool_target": "frontier-generated public-label-free inorganic structures",
            "raw_generation_target": "20000-50000 candidates",
            "minimum_public_label_free_candidates": 5000,
            "minimum_consensus_scored_candidates": 2000,
        },
        "scorers": {
            "primary": "CHGNet + MACE-MP conservative consensus",
            "consensus_rule": "-max(predicted_e_above_hull_proxy_CHGNet, predicted_e_above_hull_proxy_MACE)",
            "calibration_requirement": "same consensus scorer must be applied to WBM/Matbench calibration representatives and generated candidates",
        },
        "public_label_exclusion": {
            "minimum_sources": ["WBM/Matbench", "Materials Project"],
            "preferred_sources": ["WBM/Matbench", "Materials Project", "OQMD", "Alexandria", "GNoME"],
            "rule": "exclude known public stability labels and public-structure matches before selection",
        },
        "endpoints": [
            {
                "endpoint_id": "v4a_strict_exact_K100",
                "alpha": 0.10,
                "rho": 0.10,
                "K": 100,
                "block": "composition-family",
                "label_target": "exact_stable",
                "minimum_release_for_dft": 25,
            },
            {
                "endpoint_id": "v4b_strict_exact_K300",
                "alpha": 0.10,
                "rho": 0.10,
                "K": 300,
                "block": "composition-family",
                "label_target": "exact_stable",
                "minimum_release_for_dft": 25,
            },
            {
                "endpoint_id": "v4c_near_hull_25meV_K300",
                "alpha": 0.10,
                "rho": 0.10,
                "K": 300,
                "block": "composition-family",
                "label_target": "e_above_hull <= 25 meV/atom",
                "minimum_release_for_dft": 25,
                "scope": "near-hull computational follow-up; not exact-stability strict pass",
            },
        ],
        "dft_arms": {
            "parc_release": 40,
            "raw_only_rejected_tail": 40,
            "raw_topR_matched": 40,
            "minimum_analyzable_per_arm": 25,
        },
        "dft_failure_policy": "conservative_failed_dft_counted_not_certified_stable",
        "promotion_rule": "no DFT jobs exported unless generated pool, public-label exclusion, consensus scores and a nonempty PARC release arm are frozen before DFT outcomes",
    }


def write_outputs(args: argparse.Namespace) -> None:
    root = Path(args.out_dir)
    root.mkdir(parents=True, exist_ok=True)

    mattergen_status, mattergen_detail = detect_mattergen(Path(args.mattergen_env))
    mace_status, mace_detail = detect_mace() if not args.skip_mace_smoke else ("not_checked", "skipped by CLI")

    protocol = build_protocol()
    with (root / "protocol_v4_mattergen.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(protocol, handle, sort_keys=False)

    (root / "PROTOCOL.md").write_text(
        """# A3-v4 MatterGen--PARC Prospective DFT Follow-up Protocol

This milestone freezes a frontier-candidate route for prospective in-silico
materials follow-up. It upgrades the candidate generator from PGCGM/near-hull
substitution to MatterGen and uses a conservative CHGNet + MACE-MP consensus
score before PARC release. It is not a completed DFT result.

## Evidence boundary

- MatterGen must generate a real public-label-free candidate pool before any
  DFT outcome is available.
- CHGNet and MACE-MP must score both calibration representatives and generated
  candidates under the same frozen score rule.
- PARC must produce a nonempty release arm satisfying the predeclared DFT gate.
- `selection_frozen_v4.csv` and `dft_job_manifest_v4.csv` remain empty until
  all gates above pass.
- No new DFT outcomes, synthesis claims or discovery claims are included in
  this protocol gate.

## Endpoints

Primary strict endpoint: `v4a_strict_exact_K100`, alpha=0.10, rho=0.10,
K=100, composition-family blocks, exact-stability target, minimum release for
DFT = 25.

Secondary endpoint: `v4b_strict_exact_K300`.

Near-hull operational endpoint: `v4c_near_hull_25meV_K300`, reported only as
near-hull computational follow-up.
""",
        encoding="utf-8",
    )

    pd.DataFrame(
        [
            {
                "component": "MatterGen",
                "role": "frontier candidate generator",
                "environment_path": "<MATTERGEN_ENV>",
                "status": mattergen_status,
                "detail": mattergen_detail,
                "completed_candidate_generation": False,
            }
        ]
    ).to_csv(root / "table_mattergen_environment_status.csv", index=False)

    pd.DataFrame(
        [
            {
                "component": "MACE-MP",
                "role": "independent consensus scorer",
                "status": mace_status,
                "detail": mace_detail,
                "completed_candidate_scoring": False,
            }
        ]
    ).to_csv(root / "table_mace_environment_status.csv", index=False)

    empty_csv(root / "raw_mattergen_candidates.csv", RAW_CANDIDATE_COLUMNS)
    empty_csv(root / "candidate_universe_public_label_free.csv", PUBLIC_FREE_COLUMNS)
    empty_csv(root / "candidate_scores_chgnet.csv", SCORE_COLUMNS)
    empty_csv(root / "candidate_scores_mace.csv", SCORE_COLUMNS)
    empty_csv(root / "candidate_scores_consensus.csv", CONSENSUS_COLUMNS)
    empty_csv(root / "selection_frozen_v4.csv", SELECTION_COLUMNS)
    empty_csv(root / "dft_job_manifest_v4.csv", DFT_JOB_COLUMNS)

    pd.DataFrame(
        [
            {
                "gate": "candidate_generation",
                "required_for_dft": True,
                "status": "blocked_no_mattergen_pool" if not mattergen_status.startswith("completed") else "pending_generation_run",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "public_label_exclusion",
                "required_for_dft": True,
                "status": "blocked_no_generated_pool",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "consensus_scoring",
                "required_for_dft": True,
                "status": "blocked_no_public_label_free_pool",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "PARC_release_selection",
                "required_for_dft": True,
                "status": "blocked_no_consensus_scores",
                "n_rows": 0,
                "completed_positive_result": False,
            },
            {
                "gate": "DFT_manifest",
                "required_for_dft": True,
                "status": "blocked_no_frozen_selection",
                "n_rows": 0,
                "completed_positive_result": False,
            },
        ]
    ).to_csv(root / "table_v4_freeze_status.csv", index=False)

    pd.DataFrame(
        [
            {
                "endpoint_id": row["endpoint_id"],
                "alpha": row["alpha"],
                "K": row["K"],
                "label_target": row["label_target"],
                "status": "not_evaluated_no_generated_pool",
                "released": 0,
                "raw_only_tail": 0,
                "dft_jobs_exported": 0,
                "completed_positive_result": False,
            }
            for row in protocol["endpoints"]
        ]
    ).to_csv(root / "table_v4_go_no_go.csv", index=False)

    pd.DataFrame(
        [
            {
                "source_name": "WBM_Matbench",
                "required_minimum": True,
                "status": "planned_for_public_label_exclusion",
                "available_in_current_v4_pool": False,
            },
            {
                "source_name": "Materials_Project",
                "required_minimum": True,
                "status": "planned_for_public_label_exclusion",
                "available_in_current_v4_pool": False,
            },
            {
                "source_name": "OQMD_Alexandria_GNoME",
                "required_minimum": False,
                "status": "preferred_if_local_indexes_available",
                "available_in_current_v4_pool": False,
            },
        ]
    ).to_csv(root / "table_public_label_index_scope_v4.csv", index=False)

    closeout = f"""# MatterGen--PARC A3-v4 Closeout

Status: protocol/environment gate only. No generated candidate pool, no PARC
selection, no DFT job manifest and no DFT outcomes are included.

## Environment checks

- MatterGen: `{mattergen_status}`. Detail: {mattergen_detail}
- MACE-MP: `{mace_status}`. Detail: {mace_detail}

## Interpretation

A3-v2 and A3-v3 showed that the PGCGM and near-hull substitution candidate
universes did not provide enough evidence mass for a prospective strict DFT
arm. A3-v4 therefore changes the candidate-generator protocol before DFT
outcome access: MatterGen-generated candidates, strict public-label exclusion
and CHGNet + MACE-MP conservative consensus scoring.

This milestone must not be cited as a completed positive result. It becomes a
prospective computational trial only after a real MatterGen pool is generated,
public-label-free candidates are frozen, consensus scores are computed, and a
nonempty PARC release arm is committed before any DFT outcomes.
"""
    (root / "A3_V4_MATTERGEN_PARC_DFT_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    write_manifest(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--mattergen-env", default=str(MATTERGEN_ENV))
    parser.add_argument("--skip-mace-smoke", action="store_true")
    args = parser.parse_args()
    write_outputs(args)


if __name__ == "__main__":
    main()
