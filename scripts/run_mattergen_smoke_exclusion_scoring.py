#!/usr/bin/env python3
"""Run Phase24f smoke public-label exclusion and consensus scoring diagnostics.

The output is intentionally scoped as a smoke diagnostic.  It uses the
MatterGen 100-candidate smoke batch to validate public-label filtering,
CHGNet/MACE scoring, and PARC evidence-mass plumbing before any large
candidate-generation or DFT follow-up run.  It does not export a formal
selection or DFT manifest.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import hashlib
import json
import math
import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import torch
from chgnet.model.model import CHGNet
from mace.calculators import mace_mp
from pymatgen.core import Composition, Structure
from pymatgen.io.ase import AseAtomsAdaptor

from build_materials_prospective_chgnet_v2 import (
    add_formation_proxy_scores,
    compute_prospective_release,
    material_id_step_index,
)
from run_materials_discovery_parc_flagship import add_blocks


DEFAULT_ROOT = Path("outputs/milestones/mattergen_parc_prospective_dft_followup")
DEFAULT_GENERATION_DIR = Path("/home/waas/paper_experiments/private/mattergen_v4_generation/smoke_100")
DEFAULT_WBM_SUMMARY = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
DEFAULT_WBM_STEP1 = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2")


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


def structure_member_from_ref(structure_ref: str) -> str:
    return str(structure_ref).rsplit("::", 1)[-1]


def load_smoke_structures(generation_dir: Path) -> dict[str, Structure]:
    zip_path = generation_dir / "generated_crystals_cif.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"missing MatterGen smoke zip: {zip_path}")
    structures: dict[str, Structure] = {}
    with ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.endswith(".cif"):
                continue
            text = archive.read(name).decode("utf-8")
            structures[name] = Structure.from_str(text, fmt="cif")
    return structures


def reduced_formula(formula: str) -> str:
    try:
        return Composition(str(formula)).reduced_formula
    except Exception:
        return str(formula)


def load_wbm_step1_entries(path: Path) -> list[dict]:
    with bz2.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload["entries"])


def build_public_formula_index(wbm_summary: Path) -> set[str]:
    formulas = pd.read_csv(wbm_summary, usecols=["formula"])["formula"].dropna().astype(str)
    return {reduced_formula(formula) for formula in formulas}


def build_calibration_subset(wbm_summary: Path, max_rows: int, max_sites: int) -> pd.DataFrame:
    cols = [
        "material_id",
        "formula",
        "n_sites",
        "e_form_per_atom_mp2020_corrected",
        "e_above_hull_mp2020_corrected_ppd_mp",
        "wyckoff_spglib",
        "unique_prototype",
    ]
    frame = pd.read_csv(wbm_summary, usecols=cols)
    frame = frame[
        frame["material_id"].astype(str).str.startswith("wbm-1-")
        & frame["unique_prototype"].astype(bool)
        & pd.to_numeric(frame["n_sites"], errors="coerce").le(max_sites)
    ].copy()
    frame = add_blocks(frame)
    frame["stable_DFT"] = frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= 0.0
    frame = frame.sort_values(
        ["e_above_hull_mp2020_corrected_ppd_mp", "material_id"],
        ascending=[True, True],
        key=lambda series: series.str.split("-").str[2].astype(int)
        if series.name == "material_id"
        else series,
    )
    reps = frame.groupby("composition_family_pair", as_index=False, sort=True).head(1).head(max_rows).copy()
    reps["candidate_id"] = reps["material_id"]
    reps["block_id"] = reps["composition_family_pair"]
    reps["structure_ref"] = reps["material_id"].map(lambda mid: f"step_1.json.bz2::entry_{material_id_step_index(mid)}")
    reps["structure_sha256"] = ""
    return reps.reset_index(drop=True)


def chgnet_energy(model: CHGNet, structure: Structure) -> tuple[float, str]:
    try:
        pred = model.predict_structure(structure)
        value = float(pred["e"])
        if not math.isfinite(value) or abs(value) > 1e6:
            return math.nan, "failed_nonfinite_or_nonphysical_energy"
        return value, "scored"
    except Exception as exc:  # noqa: BLE001 - smoke diagnostics should capture failures.
        return math.nan, f"failed_{type(exc).__name__}"


def mace_energy_per_atom(calculator, structure: Structure) -> tuple[float, str]:
    try:
        atoms = AseAtomsAdaptor.get_atoms(structure)
        atoms.calc = calculator
        energy = float(atoms.get_potential_energy()) / max(1, len(atoms))
        if not math.isfinite(energy) or abs(energy) > 1e6:
            return math.nan, "failed_nonfinite_or_nonphysical_energy"
        return energy, "scored"
    except Exception as exc:  # noqa: BLE001
        return math.nan, f"failed_{type(exc).__name__}"


def score_rows(
    rows: pd.DataFrame,
    structures: dict[str, Structure],
    *,
    scorer: str,
    chgnet_model: CHGNet | None = None,
    mace_calculator=None,
    source: str,
) -> pd.DataFrame:
    records = []
    for _, row in rows.iterrows():
        member = structure_member_from_ref(str(row["structure_ref"]))
        structure = structures[member]
        if scorer == "CHGNet":
            assert chgnet_model is not None
            energy, status = chgnet_energy(chgnet_model, structure)
        elif scorer == "MACE-MP-small":
            energy, status = mace_energy_per_atom(mace_calculator, structure)
        else:
            raise ValueError(scorer)
        records.append(
            {
                "candidate_id": row["candidate_id"],
                "source": source,
                "formula": row["formula"],
                "n_sites": row["n_sites"],
                "block_id": row.get("composition_family_pair", row.get("block_id", "")),
                "stable_DFT": row.get("stable_DFT", ""),
                "e_form_per_atom_mp2020_corrected": row.get("e_form_per_atom_mp2020_corrected", ""),
                "structure_ref": row["structure_ref"],
                "structure_sha256": row["structure_sha256"],
                "model_energy_per_atom": energy,
                "score_status": status,
                "score_model": scorer,
            }
        )
    return pd.DataFrame(records)


def score_calibration_rows(
    rows: pd.DataFrame,
    entries: list[dict],
    *,
    scorer: str,
    chgnet_model: CHGNet | None = None,
    mace_calculator=None,
    source: str,
) -> pd.DataFrame:
    records = []
    for _, row in rows.iterrows():
        structure = Structure.from_dict(entries[material_id_step_index(str(row["material_id"]))]["structure"])
        if scorer == "CHGNet":
            assert chgnet_model is not None
            energy, status = chgnet_energy(chgnet_model, structure)
        elif scorer == "MACE-MP-small":
            energy, status = mace_energy_per_atom(mace_calculator, structure)
        else:
            raise ValueError(scorer)
        records.append(
            {
                "candidate_id": row["candidate_id"],
                "source": source,
                "formula": row["formula"],
                "n_sites": row["n_sites"],
                "block_id": row["block_id"],
                "stable_DFT": row["stable_DFT"],
                "e_form_per_atom_mp2020_corrected": row["e_form_per_atom_mp2020_corrected"],
                "structure_ref": row["structure_ref"],
                "structure_sha256": row["structure_sha256"],
                "model_energy_per_atom": energy,
                "score_status": status,
                "score_model": scorer,
            }
        )
    return pd.DataFrame(records)


def add_proxy_for_model(calibration: pd.DataFrame, generated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cal = calibration.rename(columns={"model_energy_per_atom": "chgnet_energy_per_atom"}).copy()
    gen = generated.rename(columns={"model_energy_per_atom": "chgnet_energy_per_atom"}).copy()
    cal, gen, _ = add_formation_proxy_scores(cal, gen)
    cal = cal.rename(
        columns={
            "chgnet_energy_per_atom": "model_energy_per_atom",
            "predicted_formation_energy_proxy": "predicted_formation_energy_proxy",
            "frozen_model_score": "model_score",
        }
    )
    gen = gen.rename(
        columns={
            "chgnet_energy_per_atom": "model_energy_per_atom",
            "predicted_formation_energy_proxy": "predicted_formation_energy_proxy",
            "frozen_model_score": "model_score",
        }
    )
    return cal, gen


def build_score_export(frame: pd.DataFrame, model_name: str, version: str) -> pd.DataFrame:
    out = frame.copy()
    out["score_model"] = model_name
    out["score_model_version"] = version
    out["energy_per_atom"] = out["model_energy_per_atom"]
    out["formation_energy_proxy"] = out["predicted_formation_energy_proxy"]
    out["predicted_e_above_hull_proxy"] = out["predicted_formation_energy_proxy"]
    out["score"] = out["model_score"]
    out = out.sort_values(["score", "candidate_id"], ascending=[False, True]).reset_index(drop=True)
    out["raw_rank"] = np.arange(1, len(out) + 1)
    return out[
        [
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
    ]


def update_main_status(root: Path, n_public_free: int, n_consensus: int) -> None:
    status = pd.read_csv(root / "table_v4_freeze_status.csv")
    status.loc[status["gate"].eq("public_label_exclusion"), "status"] = "completed_smoke_formula_level_public_label_exclusion_only"
    status.loc[status["gate"].eq("public_label_exclusion"), "n_rows"] = n_public_free
    status.loc[status["gate"].eq("consensus_scoring"), "status"] = "completed_smoke_consensus_scoring_only"
    status.loc[status["gate"].eq("consensus_scoring"), "n_rows"] = n_consensus
    status.loc[status["gate"].eq("PARC_release_selection"), "status"] = "blocked_smoke_dry_run_not_formal_selection"
    status.loc[status["gate"].eq("DFT_manifest"), "status"] = "blocked_no_frozen_selection"
    status["completed_positive_result"] = False
    status.to_csv(root / "table_v4_freeze_status.csv", index=False)

    go = pd.read_csv(root / "table_v4_go_no_go.csv")
    go["status"] = "not_evaluated_smoke_diagnostic_only"
    go["released"] = 0
    go["raw_only_tail"] = 0
    go["dft_jobs_exported"] = 0
    go["completed_positive_result"] = False
    go.to_csv(root / "table_v4_go_no_go.csv", index=False)


def write_closeout(root: Path, n_raw: int, n_public_free: int, n_consensus: int, best_mass: float) -> None:
    text = f"""# MatterGen Smoke Exclusion and Consensus-Scoring Closeout

Status: smoke diagnostic only. The 100-candidate MatterGen smoke batch was
passed through formula-level WBM/Matbench public-label exclusion, CHGNet/MACE
scoring and a PARC evidence-mass dry run. No formal A3-v4 selection, DFT job
manifest, DFT outcome or positive prospective release is claimed.

## Smoke diagnostic summary

- Raw smoke candidates: `{n_raw}`.
- Public-label-free under the available WBM/Matbench formula-level pilot index:
  `{n_public_free}`.
- CHGNet/MACE consensus-scored smoke candidates: `{n_consensus}`.
- Best smoke dry-run evidence-mass ratio: `{best_mass:.4f}`.

## Scope

Hash uniqueness is not novelty. The public-label exclusion here is a pilot using
the locally available WBM/Matbench formula-level index; Materials Project,
OQMD, Alexandria and GNoME structure-level indexes remain unavailable in this
public-safe smoke artifact. A formal A3-v4 trial still requires a larger
candidate pool, stricter public-label exclusion, full consensus scoring and a
nonempty PARC selection committed before DFT outcomes.
"""
    (root / "A3_V4_MATTERGEN_SMOKE_EXCLUSION_SCORING_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_ROOT))
    parser.add_argument("--generation-dir", default=str(DEFAULT_GENERATION_DIR))
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM_SUMMARY))
    parser.add_argument("--wbm-step1-json-bz2", default=str(DEFAULT_WBM_STEP1))
    parser.add_argument("--max-calibration-rows", type=int, default=240)
    parser.add_argument("--max-sites", type=int, default=80)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    root = Path(args.out_dir)
    raw = pd.read_csv(root / "raw_mattergen_candidates.csv")
    structures = load_smoke_structures(Path(args.generation_dir))

    public_formulas = build_public_formula_index(Path(args.wbm_summary))
    raw = raw.copy()
    raw["public_label_status"] = raw["reduced_formula"].astype(str).isin(public_formulas).map(
        lambda match: "excluded_wbm_matbench_formula_match" if bool(match) else "no_wbm_matbench_formula_match"
    )
    raw["public_label_sources_checked"] = "WBM_Matbench_formula_level;MP_OQMD_Alexandria_GNoME_unavailable_in_smoke"
    raw["structure_match_status"] = "not_run_smoke_formula_level_only"
    raw["eligible_for_A3_v4"] = raw["public_label_status"].eq("no_wbm_matbench_formula_match")
    public_free = raw[raw["eligible_for_A3_v4"].astype(bool)].copy()

    public_free.to_csv(root / "candidate_universe_public_label_free_smoke.csv", index=False)
    public_free.to_csv(root / "candidate_universe_public_label_free.csv", index=False)

    pd.DataFrame(
        {
            "candidate_id": raw["candidate_id"],
            "formula": raw["formula"],
            "reduced_formula": raw["reduced_formula"],
            "WBM_Matbench_formula_label_available": raw["public_label_status"].eq("excluded_wbm_matbench_formula_match"),
            "Materials_Project_label_available": "unavailable_in_smoke_pilot",
            "OQMD_label_available": "unavailable_in_smoke_pilot",
            "Alexandria_label_available": "unavailable_in_smoke_pilot",
            "GNoME_label_available": "unavailable_in_smoke_pilot",
            "keep_for_followup": raw["eligible_for_A3_v4"],
            "exclusion_reason": raw["public_label_status"].map(
                lambda value: "wbm_matbench_formula_match" if value == "excluded_wbm_matbench_formula_match" else ""
            ),
            "evidence_status": "smoke_formula_level_public_label_exclusion_only",
        }
    ).to_csv(root / "PUBLIC_LABEL_EXCLUSION_REPORT_smoke.csv", index=False)
    pd.DataFrame(
        {
            "candidate_id": raw["candidate_id"],
            "formula": raw["formula"],
            "composition_key": raw["chemical_system"],
            "structure_matcher_status": "not_run_smoke_formula_level_only",
            "matched_public_source": raw["public_label_status"].map(
                lambda value: "WBM_Matbench_formula_index" if value == "excluded_wbm_matbench_formula_match" else ""
            ),
            "matched_public_id": "",
            "pool_duplicate_status": "hash_unique_in_smoke_batch",
            "keep_for_followup": raw["eligible_for_A3_v4"],
            "evidence_status": "smoke_formula_level_public_label_exclusion_only",
        }
    ).to_csv(root / "NOVELTY_CROSSMATCH_REPORT_smoke.csv", index=False)

    calibration = build_calibration_subset(Path(args.wbm_summary), args.max_calibration_rows, args.max_sites)
    entries = load_wbm_step1_entries(Path(args.wbm_step1_json_bz2))
    chgnet_model = CHGNet.load()
    mace_calculator = mace_mp(model="small", device=args.device, default_dtype="float32")

    chgnet_cal = score_calibration_rows(
        calibration,
        entries,
        scorer="CHGNet",
        chgnet_model=chgnet_model,
        source="WBM_step1_smoke_calibration_subset",
    )
    chgnet_gen = score_rows(
        public_free,
        structures,
        scorer="CHGNet",
        chgnet_model=chgnet_model,
        source="MatterGen_smoke_public_label_free",
    )
    chgnet_cal, chgnet_gen = add_proxy_for_model(chgnet_cal, chgnet_gen)

    mace_cal = score_calibration_rows(
        calibration,
        entries,
        scorer="MACE-MP-small",
        mace_calculator=mace_calculator,
        source="WBM_step1_smoke_calibration_subset",
    )
    mace_gen = score_rows(
        public_free,
        structures,
        scorer="MACE-MP-small",
        mace_calculator=mace_calculator,
        source="MatterGen_smoke_public_label_free",
    )
    mace_cal, mace_gen = add_proxy_for_model(mace_cal, mace_gen)

    chgnet_export = build_score_export(chgnet_gen, "CHGNet", "CHGNet.load_smoke")
    mace_export = build_score_export(mace_gen, "MACE-MP-small", "mace_mp_small_smoke")
    chgnet_export.to_csv(root / "candidate_scores_chgnet_smoke.csv", index=False)
    mace_export.to_csv(root / "candidate_scores_mace_smoke.csv", index=False)
    chgnet_export.to_csv(root / "candidate_scores_chgnet.csv", index=False)
    mace_export.to_csv(root / "candidate_scores_mace.csv", index=False)

    score_join = chgnet_export[
        ["candidate_id", "formula", "structure_ref", "structure_sha256", "score", "score_status"]
    ].rename(columns={"score": "chgnet_score", "score_status": "chgnet_score_status"})
    score_join = score_join.merge(
        mace_export[["candidate_id", "score", "score_status"]].rename(
            columns={"score": "mace_score", "score_status": "mace_score_status"}
        ),
        on="candidate_id",
        how="inner",
    )
    score_join["consensus_rule"] = "-max(CHGNet_formation_proxy,MACE_formation_proxy)"
    score_join["score_status"] = np.where(
        score_join["chgnet_score_status"].eq("scored") & score_join["mace_score_status"].eq("scored"),
        "scored",
        "failed",
    )
    score_join["consensus_score"] = np.minimum(score_join["chgnet_score"].astype(float), score_join["mace_score"].astype(float))
    score_join = score_join.sort_values(["consensus_score", "candidate_id"], ascending=[False, True]).reset_index(drop=True)
    score_join["raw_rank"] = np.arange(1, len(score_join) + 1)
    consensus_export = score_join[
        [
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
    ]
    consensus_export.to_csv(root / "candidate_scores_consensus_smoke.csv", index=False)
    consensus_export.to_csv(root / "candidate_scores_consensus.csv", index=False)

    cal_consensus = chgnet_cal[
        ["candidate_id", "formula", "block_id", "stable_DFT", "e_form_per_atom_mp2020_corrected", "model_score", "score_status"]
    ].rename(columns={"model_score": "chgnet_score", "score_status": "chgnet_status"})
    cal_consensus = cal_consensus.merge(
        mace_cal[["candidate_id", "model_score", "score_status"]].rename(
            columns={"model_score": "mace_score", "score_status": "mace_status"}
        ),
        on="candidate_id",
        how="inner",
    )
    cal_consensus["score_status"] = np.where(
        cal_consensus["chgnet_status"].eq("scored") & cal_consensus["mace_status"].eq("scored"),
        "scored",
        "failed",
    )
    cal_consensus["frozen_model_score"] = np.minimum(
        cal_consensus["chgnet_score"].astype(float), cal_consensus["mace_score"].astype(float)
    )
    gen_consensus = public_free.merge(
        consensus_export[["candidate_id", "consensus_score", "score_status", "raw_rank"]],
        on="candidate_id",
        how="inner",
    )
    gen_consensus["frozen_model_score"] = gen_consensus["consensus_score"]
    gen_consensus["block_id"] = gen_consensus["chemical_system"]

    endpoint_rows = []
    for endpoint_id, alpha, budget, target in [
        ("v4a_strict_exact_K100", 0.10, 100, "exact_stable"),
        ("v4b_strict_exact_K300", 0.10, 300, "exact_stable"),
        ("v4c_near_hull_25meV_K300", 0.10, 300, "near_hull_25meV"),
    ]:
        cal_for_endpoint = cal_consensus.copy()
        if target == "near_hull_25meV":
            stable_map = calibration.set_index("candidate_id")["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= 0.025
            cal_for_endpoint["stable_DFT"] = cal_for_endpoint["candidate_id"].map(stable_map).fillna(False)
        raw_endpoint, diag = compute_prospective_release(
            cal_for_endpoint,
            gen_consensus,
            alpha=alpha,
            rho=0.10,
            budget=budget,
            seed=0,
        )
        diag["endpoint_id"] = endpoint_id
        diag["label_target"] = target
        diag["diagnostic_scope"] = "smoke_diagnostic_only_not_formal_selection"
        diag["candidate_pool_n"] = int(len(raw))
        diag["public_label_free_n"] = int(len(public_free))
        diag["consensus_scored_n"] = int(consensus_export["score_status"].eq("scored").sum())
        diag["dft_jobs_exported"] = 0
        diag["completed_positive_result"] = False
        endpoint_rows.append(diag)
        raw_endpoint.to_csv(root / f"table_mattergen_smoke_raw_topK_{endpoint_id}.csv", index=False)

    endpoint_summary = pd.DataFrame(endpoint_rows)
    endpoint_summary.to_csv(root / "parc_endpoint_summary_smoke.csv", index=False)

    update_main_status(root, len(public_free), int(consensus_export["score_status"].eq("scored").sum()))
    write_closeout(
        root,
        n_raw=len(raw),
        n_public_free=len(public_free),
        n_consensus=int(consensus_export["score_status"].eq("scored").sum()),
        best_mass=float(endpoint_summary["best_mass_ratio"].max()) if len(endpoint_summary) else 0.0,
    )
    write_manifest(root)


if __name__ == "__main__":
    main()
