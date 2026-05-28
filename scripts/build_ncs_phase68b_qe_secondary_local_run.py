#!/usr/bin/env python3
"""Build and optionally launch a QE secondary-sensitivity run for DFT v2.

This is intentionally not the primary VASP/atomate2 DFT v2 workflow.  It
creates local Quantum ESPRESSO inputs from the blinded Phase68 package and can
launch them in tmux as a secondary sensitivity run.  The resulting calculations
must not be described as prospective materials-discovery evidence or as the
primary DFT v2 validity endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
from pymatgen.core import Element, Structure


ROOT = Path(__file__).resolve().parents[1]
PHASE68 = ROOT / "outputs/milestones/ncs_phase68_dft_v2_pilot"
DEFAULT_OUT = Path("/home") / "waas" / "paper_experiments" / "runtime" / "ncs_phase68b_qe_secondary_local_run"
PHASE68B = ROOT / "outputs/milestones/ncs_phase68b_qe_secondary_launch"

SCOPE = (
    "QE_secondary_sensitivity_local_execution;"
    "not_primary_DFT_v2_validity_endpoint;"
    "not_VASP_MP_compatible_workflow;"
    "not_prospective_materials_discovery;"
    "not_t1_alpha_certificate"
)

PSEUDO_DIRS = [
    Path("/") / "root" / "dft_pseudos" / "sssp_efficiency" / "SSSP_efficiency_pseudos",
    ROOT / "outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/pseudos",
]

ACTINIDE_URLS = {
    "Ac": "https://pseudopotentials.quantum-espresso.org/upf_files/Ac.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "Np": "https://pseudopotentials.quantum-espresso.org/upf_files/Np.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "Pa": "https://pseudopotentials.quantum-espresso.org/upf_files/Pa.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "Pu": "https://pseudopotentials.quantum-espresso.org/upf_files/Pu.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "Th": "https://pseudopotentials.quantum-espresso.org/upf_files/Th.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "U": "https://pseudopotentials.quantum-espresso.org/upf_files/U.pbe-spfn-kjpaw_psl.1.0.0.UPF",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def find_pseudo(element: str) -> Path | None:
    prefixes = tuple(f"{prefix}{sep}" for prefix in {element, element.lower()} for sep in [".", "_", "-"])
    for directory in PSEUDO_DIRS:
        if not directory.exists():
            continue
        matches = [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".upf" and path.name.startswith(prefixes)
        ]
        if matches:
            return sorted(matches)[0]
    return None


def download_pseudo(element: str, pseudo_dir: Path) -> Path | None:
    url = ACTINIDE_URLS.get(element)
    if not url:
        return None
    target = pseudo_dir / Path(url).name
    if target.exists() and target.stat().st_size > 0:
        return target
    with urllib.request.urlopen(url, timeout=30) as response:
        target.write_bytes(response.read())
    return target


def load_manifest() -> pd.DataFrame:
    manifest = pd.read_csv(PHASE68 / "dft_v2_blinded_transfer_manifest.csv")
    required = {"blinded_job_id", "formula", "n_sites", "cif_path", "cif_sha256"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Phase68 blinded manifest missing columns: {sorted(missing)}")
    return manifest


def elements_for_jobs(manifest: pd.DataFrame) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in manifest.itertuples(index=False):
        structure = Structure.from_file(PHASE68 / row.cif_path)
        out[row.blinded_job_id] = {str(element) for element in structure.composition.elements}
    return out


def build_pseudo_map(elements: set[str], out_dir: Path) -> pd.DataFrame:
    pseudo_dir = out_dir / "pseudos"
    pseudo_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for element in sorted(elements):
        source = find_pseudo(element)
        downloaded = False
        if source is None:
            source = download_pseudo(element, pseudo_dir)
            downloaded = source is not None
        if source is None:
            rows.append(
                {
                    "element": element,
                    "pseudo_file": "",
                    "pseudo_path": "",
                    "pseudo_sha256": "",
                    "status": "missing",
                    "source": "not_found",
                }
            )
            continue
        target = pseudo_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        rows.append(
            {
                "element": element,
                "pseudo_file": target.name,
                "pseudo_path": target.relative_to(out_dir).as_posix(),
                "pseudo_sha256": sha256_file(target),
                "status": "available",
                "source": "downloaded_QE_upf_files" if downloaded else "local_SSSP_efficiency_cache",
            }
        )
    return pd.DataFrame(rows)


def write_qe_input(job_id: str, structure: Structure, pseudo_files: dict[str, str], input_path: Path) -> None:
    species = sorted({str(element) for element in structure.composition.elements})
    atomic_species = "\n".join(
        f"  {element}  {float(Element(element).atomic_mass):.4f} {pseudo_files[element]}" for element in species
    )
    atomic_positions = "\n".join(
        f"  {site.specie.symbol} {site.frac_coords[0]:.8f} {site.frac_coords[1]:.8f} {site.frac_coords[2]:.8f}"
        for site in structure
    )
    cell = "\n".join(f"  {vec[0]:.10f} {vec[1]:.10f} {vec[2]:.10f}" for vec in structure.lattice.matrix)
    text = f"""&CONTROL
  calculation = 'vc-relax',
  outdir = '../../qe_outputs/{job_id}/scratch',
  prefix = '{job_id}',
  pseudo_dir = '../../pseudos',
  restart_mode = 'from_scratch',
  tprnfor = .TRUE.,
  tstress = .TRUE.,
  verbosity = 'high',
/
&SYSTEM
  degauss = 0.02,
  ecutrho = 480,
  ecutwfc = 60,
  input_dft = 'PBE',
  nosym = .TRUE.,
  occupations = 'smearing',
  smearing = 'mv',
  ibrav = 0,
  nat = {len(structure)},
  ntyp = {len(species)},
/
&ELECTRONS
  conv_thr = 1d-06,
  electron_maxstep = 100,
  mixing_beta = 0.3,
/
&IONS
  ion_dynamics = 'bfgs',
/
&CELL
  cell_dynamics = 'bfgs',
  press_conv_thr = 1.0,
/
ATOMIC_SPECIES
{atomic_species}
ATOMIC_POSITIONS crystal
{atomic_positions}
K_POINTS automatic
  4 4 4 0 0 0
CELL_PARAMETERS angstrom
{cell}
"""
    input_path.write_text(text, encoding="utf-8")


def write_inputs(manifest: pd.DataFrame, pseudo_map: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    pseudo_lookup = dict(zip(pseudo_map["element"], pseudo_map["pseudo_file"]))
    available = set(pseudo_map[pseudo_map["status"].eq("available")]["element"])
    input_dir = out_dir / "qe_inputs"
    output_dir = out_dir / "qe_outputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for row in manifest.itertuples(index=False):
        structure = Structure.from_file(PHASE68 / row.cif_path)
        elements = {str(element) for element in structure.composition.elements}
        missing = sorted(elements - available)
        job_dir = input_dir / row.blinded_job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / row.blinded_job_id).mkdir(parents=True, exist_ok=True)
        status = "input_ready" if not missing else "blocked_missing_pseudopotential"
        if not missing:
            write_qe_input(row.blinded_job_id, structure, pseudo_lookup, job_dir / "pw.vc-relax.in")
        rows.append(
            {
                "blinded_job_id": row.blinded_job_id,
                "formula": row.formula,
                "n_sites": int(row.n_sites),
                "cif_path": row.cif_path,
                "qe_input_path": f"qe_inputs/{row.blinded_job_id}/pw.vc-relax.in" if not missing else "",
                "qe_output_dir": f"qe_outputs/{row.blinded_job_id}",
                "elements": "|".join(sorted(elements)),
                "missing_pseudopotentials": "|".join(missing),
                "status": status,
                "evidence_scope": SCOPE,
            }
        )
    jobs = pd.DataFrame(rows)
    ready_jobs = jobs[jobs["status"].eq("input_ready")]["blinded_job_id"].tolist()
    (out_dir / "job_list_input_ready.txt").write_text("\n".join(ready_jobs) + "\n", encoding="utf-8")
    return jobs


def write_shell_scripts(out_dir: Path) -> None:
    (out_dir / "run_qe_job.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
JOB_ID="${1:?job id required}"
NP="${2:-4}"
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$RUN_DIR/qe_inputs/$JOB_ID"
OUTPUT_DIR="$RUN_DIR/qe_outputs/$JOB_ID"
mkdir -p "$OUTPUT_DIR"
if [ ! -f "$INPUT_DIR/pw.vc-relax.in" ]; then
  echo "missing input for $JOB_ID" >&2
  exit 2
fi
if grep -q "JOB DONE." "$OUTPUT_DIR/pw.vc-relax.out" 2>/dev/null; then
  echo "$(date -Is) skipping completed $JOB_ID"
  exit 0
fi
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
cd "$INPUT_DIR"
"${MPIRUN_CMD:-mpirun.openmpi}" --allow-run-as-root -np "$NP" "${PWX_CMD:-pw.x}" -in pw.vc-relax.in > "$OUTPUT_DIR/pw.vc-relax.out" 2> "$OUTPUT_DIR/pw.vc-relax.err"
""",
        encoding="utf-8",
    )
    (out_dir / "run_qe_batch_tmux.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
NP="${NP:-4}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
LIMIT="${LIMIT:-0}"
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB_LIST="$RUN_DIR/job_list_input_ready.txt"
count=0
while read -r job_id; do
  [ -z "$job_id" ] && continue
  if [ "$LIMIT" -gt 0 ] && [ "$count" -ge "$LIMIT" ]; then
    break
  fi
  while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do
    sleep 10
  done
  echo "$(date -Is) starting $job_id np=$NP"
  bash "$RUN_DIR/run_qe_job.sh" "$job_id" "$NP" &
  count=$((count + 1))
done < "$JOB_LIST"
wait
echo "$(date -Is) completed QE secondary batch count=$count"
""",
        encoding="utf-8",
    )
    for script in ["run_qe_job.sh", "run_qe_batch_tmux.sh"]:
        path = out_dir / script
        path.chmod(path.stat().st_mode | 0o755)


def write_status_artifacts(out_dir: Path, pseudo_map: pd.DataFrame, jobs: pd.DataFrame, session: str, launch_state: str) -> None:
    PHASE68B.mkdir(parents=True, exist_ok=True)
    pseudo_map.to_csv(PHASE68B / "qe_secondary_pseudopotential_coverage.csv", index=False)
    summary = jobs.groupby("status", dropna=False).size().reset_index(name="n_jobs")
    summary.to_csv(PHASE68B / "qe_secondary_job_manifest_summary.csv", index=False)
    public_runtime = "external_runtime/ncs_phase68b_qe_secondary_local_run_not_distributed"
    pd.DataFrame(
        [
            {
                "tmux_session": session,
                "launch_state": launch_state,
                "runtime_dir": public_runtime,
                "input_ready_jobs": int(jobs["status"].eq("input_ready").sum()),
                "blocked_jobs": int(jobs["status"].ne("input_ready").sum()),
                "command": f"tmux session {session} runs the external runtime package with NP=4 MAX_PARALLEL=3 LIMIT=0",
                "claim_scope": SCOPE,
            }
        ]
    ).to_csv(PHASE68B / "qe_secondary_launch_status.csv", index=False)
    (PHASE68B / "QE_SECONDARY_LOCAL_LAUNCH.md").write_text(
        f"""# Phase68b QE Secondary Local Launch

Status: `{launch_state}`.

Runtime directory: `{public_runtime}`.

tmux session: `{session}`.

This is a Quantum ESPRESSO secondary-sensitivity execution path. It is not the primary VASP/atomate2/custodian DFT v2 workflow, not DFT v2 primary validity evidence, not prospective materials discovery, and not a t1 alpha certificate.
""",
        encoding="utf-8",
    )


def launch_tmux(out_dir: Path, session: str, np: int, max_parallel: int, limit: int) -> str:
    existing = subprocess.run(["tmux", "has-session", "-t", session], check=False, capture_output=True, text=True)
    if existing.returncode == 0:
        return "already_running_in_tmux"
    command = f"cd {out_dir} && NP={np} MAX_PARALLEL={max_parallel} LIMIT={limit} bash run_qe_batch_tmux.sh 2>&1 | tee qe_batch.log"
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "bash", "-lc", command], check=True)
    return "launched_in_tmux"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--launch-tmux", action="store_true")
    parser.add_argument("--session", default="ncs68b_qe")
    parser.add_argument("--np", type=int, default=4)
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    job_elements = elements_for_jobs(manifest)
    all_elements = set().union(*job_elements.values())
    pseudo_map = build_pseudo_map(all_elements, args.out_dir)
    jobs = write_inputs(manifest, pseudo_map, args.out_dir)
    jobs.to_csv(args.out_dir / "qe_secondary_job_manifest.csv", index=False)
    pseudo_map.to_csv(args.out_dir / "qe_secondary_pseudopotential_coverage.csv", index=False)
    write_shell_scripts(args.out_dir)
    launch_state = "package_built_not_launched"
    if args.launch_tmux:
        launch_state = launch_tmux(args.out_dir, args.session, args.np, args.max_parallel, args.limit)
    write_status_artifacts(args.out_dir, pseudo_map, jobs, args.session, launch_state)
    print(
        json.dumps(
            {
                "status": launch_state,
                "runtime_dir": args.out_dir.as_posix(),
                "tmux_session": args.session,
                "input_ready_jobs": int(jobs["status"].eq("input_ready").sum()),
                "blocked_jobs": int(jobs["status"].ne("input_ready").sum()),
                "scope": SCOPE,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
