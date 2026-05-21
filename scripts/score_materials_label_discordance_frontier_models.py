from __future__ import annotations

import csv
import hashlib
import math
import sys
from pathlib import Path

import pandas as pd
from pymatgen.io.ase import AseAtomsAdaptor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_materials_alex_mp_a1_a2_validation import load_wbm_structures  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "materials_label_discordance_preregistration"
MATCHES = ROOT / "outputs/milestones/materials_alex_mp_a1_a2_validation/table_alex_mp_a2_candidate_matches.csv"
STEP1 = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2")
STEP_DIR = Path("/home/waas/paper_experiments/private/wbm_raw_full")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(OUT)}")
    (OUT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    from chgnet.model.model import CHGNet
    from mace.calculators import mace_mp
    import torch

    matches = pd.read_csv(MATCHES)
    exact = matches[matches["match_confidence"].eq("exact_structure_match")].copy()
    material_ids = set(exact["material_id"].astype(str))
    structures = load_wbm_structures(material_ids, step1=STEP1, step_dir=STEP_DIR)

    chgnet = CHGNet.load()
    mace = mace_mp(model="small", device="cuda" if torch.cuda.is_available() else "cpu", default_dtype="float32")

    rows: list[dict] = []
    for idx, row in enumerate(exact.sort_values("material_id").itertuples(index=False), start=1):
        material_id = str(row.material_id)
        structure = structures.get(material_id)
        if structure is None:
            for model in ["CHGNet", "MACE-MP"]:
                rows.append(
                    {
                        "material_id": material_id,
                        "formula": row.formula,
                        "model": model,
                        "score_status": "failed_missing_wbm_structure",
                        "energy_per_atom": "",
                        "score": "",
                        "score_type": "raw_energy_per_atom_lower_is_more_stable",
                    }
                )
            continue

        try:
            pred = chgnet.predict_structure(structure)
            energy = float(pred["e"])
            status = "scored" if math.isfinite(energy) and abs(energy) < 1e6 else "failed_nonfinite_or_nonphysical"
        except Exception as exc:  # noqa: BLE001
            energy = math.nan
            status = f"failed_{type(exc).__name__}"
        rows.append(
            {
                "material_id": material_id,
                "formula": row.formula,
                "model": "CHGNet",
                "score_status": status,
                "energy_per_atom": energy if math.isfinite(energy) else "",
                "score": energy if math.isfinite(energy) else "",
                "score_type": "raw_energy_per_atom_lower_is_more_stable",
            }
        )

        try:
            atoms = AseAtomsAdaptor.get_atoms(structure)
            atoms.calc = mace
            energy = float(atoms.get_potential_energy()) / max(1, len(atoms))
            status = "scored" if math.isfinite(energy) and abs(energy) < 1e6 else "failed_nonfinite_or_nonphysical"
        except Exception as exc:  # noqa: BLE001
            energy = math.nan
            status = f"failed_{type(exc).__name__}"
        rows.append(
            {
                "material_id": material_id,
                "formula": row.formula,
                "model": "MACE-MP",
                "score_status": status,
                "energy_per_atom": energy if math.isfinite(energy) else "",
                "score": energy if math.isfinite(energy) else "",
                "score_type": "raw_energy_per_atom_lower_is_more_stable",
            }
        )
        if idx % 25 == 0:
            print(f"scored {idx}/{len(exact)} exact-match structures", flush=True)

    with (OUT / "table_frontier_model_scores.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_manifest()


if __name__ == "__main__":
    main()
