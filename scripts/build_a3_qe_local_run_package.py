#!/usr/bin/env python3
"""Build a local Quantum ESPRESSO execution layer for the frozen A3 package.

This script derives QE input decks from the pre-outcome A3 DFT run package.
It deliberately does not modify `selection_frozen_v4.csv` or any frozen A3
selection/manifest inputs. The output is an execution layer only: no DFT
outcomes and no prospective materials claim.
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pymatgen.core import Structure
from pymatgen.io.pwscf import PWInput


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"
PACKAGE = MILESTONE / "A3_DFT_RUN_PACKAGE"
RUN = MILESTONE / "A3_QE_LOCAL_RUN"
SSSP_DIR = Path("/root/dft_pseudos/sssp_efficiency")
QE_APT_PSEUDO_DIR = Path("/usr/share/espresso/pseudo")
PWX = Path(shutil.which("pw.x") or "/usr/bin/pw.x")
MPIRUN = Path(shutil.which("mpirun") or shutil.which("mpiexec") or "/usr/bin/mpirun.openmpi")


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
        if ".git" in path.parts or "__pycache__" in path.parts or ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def assert_pre_outcome() -> None:
    manifest = pd.read_csv(PACKAGE / "package_job_manifest.csv")
    if "outcome_available" in manifest and manifest["outcome_available"].astype(bool).any():
        raise RuntimeError("A3 package already contains outcome_available=True; do not rebuild pre-outcome QE layer.")
    if "outcome_file" in manifest and manifest["outcome_file"].fillna("").astype(str).str.strip().ne("").any():
        raise RuntimeError("A3 package already contains outcome_file values; do not rebuild pre-outcome QE layer.")
    for pattern in ["dft_results*.csv", "qe_results*.csv", "vasp_results*.csv"]:
        for path in MILESTONE.glob(pattern):
            if path.is_file() and path.stat().st_size > 0:
                raise RuntimeError(f"Found possible DFT outcome file: {rel(path)}")


def element_from_pseudo_name(path: Path) -> str | None:
    match = re.match(r"([A-Z][a-z]?|[a-z]{1,2})(?:[._-]|$)", path.name)
    if not match:
        return None
    return match.group(1).capitalize()


def pseudo_priority(path: Path) -> tuple[int, int, int, str]:
    name = path.name.lower()
    # Prefer SSSP over apt-provided mixed examples, then PBE, then shorter names.
    in_sssp = 0 if SSSP_DIR in path.parents else 1
    pbe = 0 if "pbe" in name else 1
    avoid_rel = 1 if "rel-" in name or ".rel" in name else 0
    return (in_sssp, pbe, avoid_rel, name)


def build_pseudo_map(required_elements: set[str]) -> dict[str, Path]:
    candidates: dict[str, list[Path]] = {}
    for root in [SSSP_DIR, QE_APT_PSEUDO_DIR]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() != ".upf":
                continue
            element = element_from_pseudo_name(path)
            if element:
                candidates.setdefault(element, []).append(path)
    missing = sorted(required_elements - set(candidates))
    if missing:
        raise RuntimeError(f"Missing QE pseudopotentials for: {', '.join(missing)}")
    return {element: sorted(candidates[element], key=pseudo_priority)[0] for element in sorted(required_elements)}


def k_grid(structure: Structure) -> tuple[int, int, int]:
    # Conservative, simple local grid: roughly 25 A real-space length product,
    # capped to keep generated-candidate screening tractable on this machine.
    grid = []
    for length in structure.lattice.abc:
        grid.append(max(1, min(6, int(round(25.0 / max(float(length), 1.0))))))
    return tuple(grid)  # type: ignore[return-value]


def qe_input(structure: Structure, pseudo: dict[str, str], outdir: str, calculation: str) -> PWInput:
    control = {
        "calculation": calculation,
        "restart_mode": "from_scratch",
        "pseudo_dir": "../../pseudos",
        "outdir": outdir,
        "prefix": "a3",
        "verbosity": "high",
        "tprnfor": True,
        "tstress": True,
    }
    system = {
        "input_dft": "PBE",
        "ecutwfc": 60,
        "ecutrho": 480,
        "occupations": "smearing",
        "smearing": "mv",
        "degauss": 0.02,
        "nosym": True,
    }
    electrons = {
        "conv_thr": 1e-6,
        "mixing_beta": 0.3,
        "electron_maxstep": 100,
    }
    ions = {"ion_dynamics": "bfgs"}
    cell = {"cell_dynamics": "bfgs", "press_conv_thr": 1.0}
    return PWInput(
        structure,
        pseudo=pseudo,
        control=control,
        system=system,
        electrons=electrons,
        ions=ions,
        cell=cell,
        kpoints_grid=k_grid(structure),
    )


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def update_indexes() -> None:
    artifact_path = ROOT / "outputs" / "artifact_index.csv"
    artifact = pd.read_csv(artifact_path)
    milestone = "mattergen_a3_qe_local_run"
    if milestone not in set(artifact["milestone"].astype(str)):
        artifact.loc[len(artifact)] = {
            "milestone": milestone,
            "path": "outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/",
            "evidence_state": "local_QE_execution_layer_no_outcomes_not_positive_evidence",
            "manifest": "outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN",
        }
        artifact.to_csv(artifact_path, index=False)

    claim_path = ROOT / "docs" / "claim_table.md"
    claim_text = claim_path.read_text(encoding="utf-8")
    claim_row = (
        "| A3-v4 local QE execution layer is prepared on this machine but remains pre-outcome non-evidence. "
        "| `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/qe_job_manifest.csv`; "
        "`QE_ENVIRONMENT_STATUS.csv` | `python scripts/build_a3_qe_local_run_package.py` "
        "| Quantum ESPRESSO and SSSP pseudopotentials are used to create local QE input decks and tmux launch scripts. "
        "No DFT outcome or prospective discovery claim is made until returned outcomes are analyzed under the conservative failure policy. |\n"
    )
    if "A3-v4 local QE execution layer" not in claim_text:
        claim_path.write_text(claim_text.rstrip() + "\n" + claim_row, encoding="utf-8")

    makefile = ROOT / "Makefile"
    make = makefile.read_text(encoding="utf-8")
    if "reproduce-a3-qe-local-run" not in make:
        make = make.replace(
            "reproduce-a3-dft-run-package:\n\t$(PYTHON) scripts/build_a3_dft_run_package.py\n",
            "reproduce-a3-dft-run-package:\n\t$(PYTHON) scripts/build_a3_dft_run_package.py\n\n"
            "reproduce-a3-qe-local-run:\n\t$(PYTHON) scripts/build_a3_qe_local_run_package.py\n",
        )
        make = make.replace(
            "reproduce-a3-dft-run-package",
            "reproduce-a3-dft-run-package reproduce-a3-qe-local-run",
            1,
        )
        makefile.write_text(make, encoding="utf-8")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    if "A3 QE local run layer" not in readme_text:
        readme_text += (
            "\n- A3 QE local run layer: `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/` "
            "contains Quantum ESPRESSO input decks, SSSP pseudopotential mapping, and tmux launch scripts for the frozen A3 package. "
            "It contains no DFT outcomes and no prospective materials claim.\n"
        )
        readme.write_text(readme_text, encoding="utf-8")

    repro = ROOT / "REPRODUCIBILITY.md"
    repro_text = repro.read_text(encoding="utf-8")
    if "reproduce-a3-qe-local-run" not in repro_text:
        repro_text += (
            "\n## A3 local Quantum ESPRESSO execution layer\n\n"
            "Run `make reproduce-a3-qe-local-run` after `make reproduce-a3-dft-run-package` to derive local QE input decks from the frozen A3 CIF package. "
            "This target does not modify `selection_frozen_v4.csv`, does not contain outcomes, and must not be cited as prospective DFT evidence.\n"
        )
        repro.write_text(repro_text, encoding="utf-8")


def main() -> None:
    assert_pre_outcome()
    if not PACKAGE.exists():
        raise FileNotFoundError("Run scripts/build_a3_dft_run_package.py first.")
    if not PWX.exists():
        raise FileNotFoundError("pw.x was not found; install Quantum ESPRESSO before building the local run layer.")
    if not SSSP_DIR.exists():
        raise FileNotFoundError("SSSP pseudopotential directory is missing: /root/dft_pseudos/sssp_efficiency")

    if RUN.exists():
        shutil.rmtree(RUN)
    (RUN / "qe_inputs").mkdir(parents=True, exist_ok=True)
    (RUN / "qe_outputs").mkdir(parents=True, exist_ok=True)
    (RUN / "job_lists").mkdir(parents=True, exist_ok=True)
    (RUN / "pseudos").mkdir(parents=True, exist_ok=True)

    source_manifest = pd.read_csv(PACKAGE / "package_job_manifest.csv")
    required_elements: set[str] = set()
    structures: dict[str, Structure] = {}
    for _, row in source_manifest.iterrows():
        cif_path = PACKAGE / str(row["package_cif_path"])
        structure = Structure.from_file(cif_path)
        structures[str(row["dft_job_id"])] = structure
        required_elements.update(str(element) for element in structure.composition.elements)
    pseudo_map = build_pseudo_map(required_elements)
    local_pseudo_map: dict[str, Path] = {}
    for element, source in pseudo_map.items():
        target = RUN / "pseudos" / source.name
        shutil.copy2(source, target)
        local_pseudo_map[element] = target

    records: list[dict[str, object]] = []
    for _, row in source_manifest.iterrows():
        job_id = str(row["dft_job_id"])
        arm = str(row["arm"])
        structure = structures[job_id]
        job_dir = RUN / "qe_inputs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (RUN / "qe_outputs" / job_id / "scratch").mkdir(parents=True, exist_ok=True)
        pseudo = {str(element): local_pseudo_map[str(element)].name for element in structure.composition.elements}
        input_obj = qe_input(structure, pseudo, f"../../qe_outputs/{job_id}/scratch", "vc-relax")
        input_path = job_dir / "pw.vc-relax.in"
        input_path.write_text(str(input_obj), encoding="utf-8")
        species = sorted(str(element) for element in structure.composition.elements)
        records.append(
            {
                "dft_job_id": job_id,
                "candidate_id": row["candidate_id"],
                "arm": arm,
                "formula": row.get("formula", structure.composition.reduced_formula),
                "n_sites": len(structure),
                "elements": "|".join(species),
                "qe_input_path": rel(input_path),
                "qe_output_dir": rel(RUN / "qe_outputs" / job_id),
                "kpoints_grid": " ".join(map(str, k_grid(structure))),
                "ecutwfc_ry": 60,
                "ecutrho_ry": 480,
                "pseudo_files": "|".join(pseudo[element] for element in species),
                "pseudo_sha256": "|".join(sha256_file(local_pseudo_map[element]) for element in species),
                "pw_x": "pw.x",
                "mpirun": "mpirun.openmpi",
                "selected_before_DFT_outcome": True,
                "outcome_available": False,
                "completed_positive_result": False,
                "claim_scope": "local_QE_input_deck_only_no_DFT_outcome",
            }
        )

    qe_manifest = pd.DataFrame(records)
    qe_manifest.to_csv(RUN / "qe_job_manifest.csv", index=False)
    for arm, frame in qe_manifest.groupby("arm"):
        (RUN / "job_lists" / f"{arm}.txt").write_text("\n".join(frame["dft_job_id"].astype(str)) + "\n", encoding="utf-8")

    pseudo_rows = [
        {
            "element": element,
            "pseudo_path": rel(local_pseudo_map[element]),
            "pseudo_file": path.name,
            "pseudo_sha256": sha256_file(local_pseudo_map[element]),
            "source": "SSSP_efficiency_v1.1" if SSSP_DIR in path.parents else "Ubuntu_QE_package",
        }
        for element, path in pseudo_map.items()
    ]
    pd.DataFrame(pseudo_rows).to_csv(RUN / "table_qe_pseudopotential_map.csv", index=False)

    status = pd.DataFrame(
        [
            {
                "component": "Quantum ESPRESSO",
                "status": "available_local_cpu_qe",
                "detail": "pw.x command and mpirun.openmpi command detected on the local host",
                "n_jobs": len(qe_manifest),
                "n_release_jobs": int(qe_manifest["arm"].eq("PARC-release-full").sum()),
                "n_extra_tail_jobs": int(qe_manifest["arm"].eq("raw_top100_extra_tail").sum()),
                "n_required_elements": len(required_elements),
                "n_pseudo_elements_covered": len(pseudo_map),
                "outcomes_present": False,
                "claim_scope": "environment_and_input_deck_only_not_DFT_evidence",
            }
        ]
    )
    status.to_csv(RUN / "QE_ENVIRONMENT_STATUS.csv", index=False)

    write_executable(
        RUN / "run_qe_job.sh",
        f"""#!/usr/bin/env bash
set -euo pipefail
JOB_ID="${{1:?job id required}}"
NP="${{2:-4}}"
RUN_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
INPUT_DIR="$RUN_DIR/qe_inputs/$JOB_ID"
OUTPUT_DIR="$RUN_DIR/qe_outputs/$JOB_ID"
mkdir -p "$OUTPUT_DIR"
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
cd "$INPUT_DIR"
"${{MPIRUN_CMD:-mpirun.openmpi}}" --allow-run-as-root -np "$NP" "${{PWX_CMD:-pw.x}}" -in pw.vc-relax.in > "$OUTPUT_DIR/pw.vc-relax.out" 2> "$OUTPUT_DIR/pw.vc-relax.err"
""",
    )
    write_executable(
        RUN / "run_qe_batch_tmux.sh",
        f"""#!/usr/bin/env bash
set -euo pipefail
ARM="${{1:-PARC-release-full}}"
NP="${{NP:-4}}"
MAX_PARALLEL="${{MAX_PARALLEL:-3}}"
LIMIT="${{LIMIT:-0}}"
RUN_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
JOB_LIST="$RUN_DIR/job_lists/$ARM.txt"
if [ ! -f "$JOB_LIST" ]; then
  echo "missing job list: $JOB_LIST" >&2
  exit 2
fi
count=0
while read -r job_id; do
  [ -z "$job_id" ] && continue
  if [ "$LIMIT" -gt 0 ] && [ "$count" -ge "$LIMIT" ]; then
    break
  fi
  while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do
    sleep 10
  done
  echo "$(date -Is) starting $job_id arm=$ARM np=$NP"
  bash "$RUN_DIR/run_qe_job.sh" "$job_id" "$NP" &
  count=$((count + 1))
done < "$JOB_LIST"
wait
echo "$(date -Is) completed batch arm=$ARM count=$count"
""",
    )
    write_executable(
        RUN / "launch_parc_release_tmux.sh",
        f"""#!/usr/bin/env bash
set -euo pipefail
SESSION="${{SESSION:-a3_qe_parc_release}}"
RUN_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
tmux has-session -t "$SESSION" 2>/dev/null && {{
  echo "tmux session already exists: $SESSION" >&2
  exit 3
}}
tmux new-session -d -s "$SESSION" "cd '$RUN_DIR' && NP=${{NP:-4}} MAX_PARALLEL=${{MAX_PARALLEL:-3}} bash '$RUN_DIR/run_qe_batch_tmux.sh' PARC-release-full"
echo "$SESSION"
""",
    )
    (RUN / "QE_LOCAL_RUN_PROTOCOL.md").write_text(
        f"""# A3-v4 Local Quantum ESPRESSO Run Layer

Status: local execution environment and QE input decks prepared; no DFT outcomes are included.

## Frozen source

Inputs are derived from `A3_DFT_RUN_PACKAGE/package_job_manifest.csv`.
This script does not modify `selection_frozen_v4.csv`, `dft_job_manifest_v4_addendum.csv`, or `dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv`.

## Local engine

- QE executable: `pw.x`
- MPI launcher: `mpirun.openmpi`
- Pseudopotential library: copied SSSP efficiency v1.1 UPF files under `pseudos/`
- Required elements covered: {len(pseudo_map)} / {len(required_elements)}
- Jobs prepared: {len(qe_manifest)} total ({int(qe_manifest['arm'].eq('PARC-release-full').sum())} release, {int(qe_manifest['arm'].eq('raw_top100_extra_tail').sum())} extra-tail)

## Local settings

Generated input decks use QE `vc-relax`, PBE, SSSP UPF pseudopotentials, `ecutwfc=60 Ry`, `ecutrho=480 Ry`, Methfessel-Paxton smearing, and a fixed deterministic k-point grid derived from lattice lengths.

These settings are a local executable DFT route, not a Materials Project compatibility claim. Any manuscript DFT claim must report this engine/settings scope.

## Claim boundary

This layer is not DFT evidence. It only records that local QE input decks and launch scripts were prepared before outcomes. Prospective materials discovery claims remain forbidden until DFT outcomes are returned and analyzed under the conservative failure policy.

## Launch

Start the full PARC-release arm in tmux:

```bash
NP=4 MAX_PARALLEL=3 bash {rel(RUN / 'launch_parc_release_tmux.sh')}
```

Run the extra-tail arm only after the release arm policy decision:

```bash
NP=4 MAX_PARALLEL=3 bash {rel(RUN / 'run_qe_batch_tmux.sh')} raw_top100_extra_tail
```
""",
        encoding="utf-8",
    )

    update_indexes()
    write_manifest(RUN)
    write_manifest(MILESTONE)
    write_root_manifest()
    print(f"wrote {rel(RUN / 'qe_job_manifest.csv')}")


if __name__ == "__main__":
    main()
