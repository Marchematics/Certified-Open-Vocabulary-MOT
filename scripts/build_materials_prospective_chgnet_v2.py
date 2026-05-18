#!/usr/bin/env python3
"""Build A3-v2 CHGNet prospective DFT follow-up selection.

This script is intentionally strict about the evidence boundary:

* ALIGNN-FF A3-v1 remains a blocked model-availability record.
* CHGNet is used as a locally executable frozen scorer for both the WBM
  calibration subset and the generated PGCGM candidate pool.
* The script does not read, create or infer new DFT outcomes.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import math
import tarfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from chgnet.model.model import CHGNet
from pymatgen.core import Composition
from pymatgen.core import Structure

from run_materials_discovery_parc_flagship import (
    add_blocks,
    emax_from_p,
    gamma_star_from_p,
    observed_positive_mask,
    scs_release_count,
)


DEFAULT_V1 = Path("outputs/milestones/materials_prospective_dft_followup")
DEFAULT_OUT = Path("outputs/milestones/materials_prospective_dft_followup_chgnet_v2")
DEFAULT_WBM_SUMMARY = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
DEFAULT_WBM_STEP1 = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2/wbm_raw/step_1.json.bz2")
DEFAULT_PGCGM_ARCHIVE = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup/pgcgm_raw_cifs/1.tar.gz")
SELECTION_COLUMNS = [
    "arm",
    "candidate_id",
    "selected_for_dft",
    "dft_job_id",
    "selection_rank",
    "selection_rule",
    "score_rank",
    "parc_release_flag",
    "raw_topK_member",
    "reserve_order",
    "evidence_status",
    "primary_or_reserve",
    "source_rank",
    "frozen_model_score",
    "structure_ref",
    "structure_sha256",
]
DFT_JOB_COLUMNS = [
    "dft_job_id",
    "candidate_id",
    "arm",
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


def material_id_step_index(material_id: str) -> int:
    parts = str(material_id).split("-")
    if len(parts) != 3 or parts[0] != "wbm" or parts[1] != "1":
        raise ValueError(f"Expected a step-1 WBM id, got {material_id!r}")
    return int(parts[2]) - 1


def load_wbm_step1_entries(path: Path) -> list[dict]:
    with bz2.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload["entries"])


def load_pgcgm_tar_index(path: Path) -> dict[str, str]:
    with tarfile.open(path, "r:gz") as archive:
        return {Path(name).name: name for name in archive.getnames()}


def read_pgcgm_structure_from_tar(archive: tarfile.TarFile, archive_index: dict[str, str], structure_ref: str) -> Structure:
    basename = str(structure_ref).split("::", 1)[-1]
    member = archive_index[basename]
    text = archive.extractfile(member).read().decode("utf-8")  # type: ignore[union-attr]
    return Structure.from_str(text, fmt="cif")


def score_structure(model: CHGNet, structure: Structure) -> tuple[float, str]:
    # CHGNet's default prediction path also computes forces/stress and expects
    # autograd to be available internally, so do not wrap this call in
    # torch.no_grad().
    pred = model.predict_structure(structure)
    value = float(pred["e"])
    if not math.isfinite(value) or abs(value) > 1e6:
        return math.nan, "failed_nonfinite_or_nonphysical_energy"
    return value, "scored"


def score_with_checkpoint(
    rows: pd.DataFrame,
    *,
    model: CHGNet,
    source: str,
    out_private: Path,
    structure_getter,
    checkpoint_every: int,
) -> pd.DataFrame:
    existing = pd.DataFrame()
    if out_private.exists():
        existing = pd.read_csv(out_private)
    done = set(existing["candidate_id"].astype(str)) if not existing.empty else set()
    records = [] if existing.empty else existing.to_dict("records")

    start = time.time()
    for pos, (_, row) in enumerate(rows.iterrows(), start=1):
        candidate_id = str(row["candidate_id"])
        if candidate_id in done:
            continue
        try:
            structure = structure_getter(row)
            energy, status = score_structure(model, structure)
            n_sites_scored = len(structure)
        except Exception as exc:  # noqa: BLE001 - status table should capture scorer failures.
            energy = math.nan
            status = f"failed_{type(exc).__name__}"
            n_sites_scored = row.get("n_sites", "")
        records.append(
            {
                "candidate_id": candidate_id,
                "source": source,
                "formula": row.get("formula", ""),
                "n_sites": row.get("n_sites", n_sites_scored),
                "block_id": row.get("composition_family_pair", row.get("block_id", "")),
                "stable_DFT": row.get("stable_DFT", ""),
                "e_form_per_atom_mp2020_corrected": row.get("e_form_per_atom_mp2020_corrected", ""),
                "structure_ref": row.get("structure_ref", ""),
                "structure_sha256": row.get("structure_sha256", ""),
                "chgnet_energy_per_atom": energy,
                "score_status": status,
            }
        )
        if len(records) % checkpoint_every == 0:
            pd.DataFrame(records).to_csv(out_private, index=False)
            print(f"[{source}] scored {len(records)} rows in {time.time() - start:.1f}s", flush=True)
    out = pd.DataFrame(records)
    out.to_csv(out_private, index=False)
    return out


def element_fraction_frame(formulas: pd.Series, elements: list[str]) -> np.ndarray:
    index = {element: idx for idx, element in enumerate(elements)}
    x = np.zeros((len(formulas), len(elements)), dtype=float)
    for row_idx, formula in enumerate(formulas.astype(str)):
        try:
            composition = Composition(formula)
            total = float(composition.num_atoms)
            for element, amount in composition.get_el_amt_dict().items():
                if element in index and total > 0:
                    x[row_idx, index[element]] = float(amount) / total
        except Exception:
            continue
    return x


def add_formation_proxy_scores(calibration: pd.DataFrame, generated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cal = calibration.copy()
    gen = generated.copy()
    all_elements = sorted(
        {
            str(element)
            for formula in pd.concat([cal["formula"], gen["formula"]], ignore_index=True).astype(str)
            for element in Composition(formula).elements
        }
    )
    fit_mask = cal["score_status"].eq("scored") & cal["e_form_per_atom_mp2020_corrected"].notna()
    x_fit = element_fraction_frame(cal.loc[fit_mask, "formula"], all_elements)
    y_fit = (
        cal.loc[fit_mask, "chgnet_energy_per_atom"].astype(float).to_numpy()
        - cal.loc[fit_mask, "e_form_per_atom_mp2020_corrected"].astype(float).to_numpy()
    )
    ridge = 1e-6
    coeff = np.linalg.solve(x_fit.T @ x_fit + ridge * np.eye(x_fit.shape[1]), x_fit.T @ y_fit)

    refs = pd.DataFrame({"element": all_elements, "reference_energy_per_atom": coeff})
    for frame in [cal, gen]:
        x = element_fraction_frame(frame["formula"], all_elements)
        reference = x @ coeff
        frame["element_reference_energy_per_atom"] = reference
        frame["predicted_formation_energy_proxy"] = frame["chgnet_energy_per_atom"].astype(float) - reference
        frame["frozen_model_score"] = -frame["predicted_formation_energy_proxy"]
        valid = frame["score_status"].eq("scored") & np.isfinite(frame["frozen_model_score"].astype(float))
        frame.loc[~valid, "frozen_model_score"] = np.nan
    return cal, gen, refs


def build_wbm_calibration_subset(summary_path: Path, max_sites: int) -> pd.DataFrame:
    cols = [
        "material_id",
        "formula",
        "n_sites",
        "e_form_per_atom_mp2020_corrected",
        "e_above_hull_mp2020_corrected_ppd_mp",
        "wyckoff_spglib",
        "unique_prototype",
    ]
    frame = pd.read_csv(summary_path, usecols=cols)
    frame = frame[
        frame["material_id"].astype(str).str.startswith("wbm-1-")
        & frame["unique_prototype"].astype(bool)
        & pd.to_numeric(frame["n_sites"], errors="coerce").le(max_sites)
    ].copy()
    frame = add_blocks(frame)
    frame["stable_DFT"] = frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= 0.0
    frame = frame.sort_values("material_id", key=lambda s: s.str.split("-").str[2].astype(int))
    # Deterministic one-representative-per-composition-family scored calibration subset.
    reps = frame.groupby("composition_family_pair", as_index=False, sort=True).head(1).copy()
    reps["candidate_id"] = reps["material_id"]
    reps["block_id"] = reps["composition_family_pair"]
    reps["structure_ref"] = reps["material_id"].map(lambda mid: f"step_1.json.bz2::entry_{material_id_step_index(mid)}")
    reps["structure_sha256"] = ""
    return reps.reset_index(drop=True)


def build_pgcgm_scoring_subset(v1_dir: Path, max_sites: int) -> pd.DataFrame:
    frame = pd.read_csv(v1_dir / "candidate_universe_frozen.csv")
    frame["n_sites"] = pd.to_numeric(frame["n_sites"], errors="coerce")
    subset = frame[
        frame["keep_for_followup"].astype(bool)
        & frame["n_sites"].le(max_sites)
        & frame["formula"].notna()
        & frame["structure_ref"].notna()
    ].copy()
    subset["candidate_id"] = subset["candidate_id"].astype(str)
    subset["block_id"] = subset["block_id"].astype(str)
    return subset.reset_index(drop=True)


def compute_prospective_release(
    calibration: pd.DataFrame,
    generated: pd.DataFrame,
    *,
    alpha: float,
    rho: float,
    budget: int,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    cal = calibration[calibration["score_status"].eq("scored") & calibration["frozen_model_score"].notna()].copy()
    gen = generated[generated["score_status"].eq("scored") & generated["frozen_model_score"].notna()].copy()
    cal["stable_DFT"] = cal["stable_DFT"].astype(bool)
    observed = observed_positive_mask(cal, "frozen_model_score", rho=rho, seed=seed, strategy="top_score")
    partial_null = ~observed
    maxima = (
        cal.loc[partial_null]
        .groupby("block_id", sort=False)["frozen_model_score"]
        .max()
        .astype(float)
        .to_numpy()
    )
    p_min = 1.0 / (len(maxima) + 1.0) if len(maxima) else 1.0
    gamma = gamma_star_from_p(p_min)
    emax = emax_from_p(gamma, p_min)
    raw = gen.sort_values(["frozen_model_score", "candidate_id"], ascending=[False, True]).head(budget).copy()
    if gamma is None or len(maxima) == 0 or raw.empty:
        raw["_evalue"] = 0.0
    else:
        sorted_max = np.sort(maxima)
        scores = raw["frozen_model_score"].to_numpy(dtype=float)
        exceed = len(sorted_max) - np.searchsorted(sorted_max, scores, side="left")
        p_block = (1.0 + exceed) / (len(sorted_max) + 1.0)
        raw["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    released, tau, margin, best_ratio = scs_release_count(raw["_evalue"].to_numpy(dtype=float), alpha=alpha, budget=budget)
    raw = raw.sort_values(["_evalue", "frozen_model_score", "candidate_id"], ascending=[False, False, True]).copy()
    raw["parc_release_flag"] = False
    if released:
        raw.iloc[:released, raw.columns.get_loc("parc_release_flag")] = True
    diag = {
        "alpha": alpha,
        "rho": rho,
        "K": budget,
        "seed": seed,
        "n_calibration_scored": int(len(cal)),
        "n_generated_scored": int(len(gen)),
        "n_observed_positive": int(observed.sum()),
        "n_null_calibration_blocks": int(len(maxima)),
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax,
        "required_e_for_one_release": float(budget / alpha),
        "required_e_for_40_release": float(budget / (alpha * 40.0)),
        "max_candidate_e": float(raw["_evalue"].max()) if len(raw) else 0.0,
        "best_mass_ratio": float(best_ratio),
        "released": int(released),
        "tau": float(tau) if math.isfinite(tau) else math.inf,
        "self_consistency_margin": float(margin),
    }
    return raw, diag


def freeze_selection(raw: pd.DataFrame, n_arm: int, min_arm: int) -> pd.DataFrame:
    released = raw[raw["parc_release_flag"].astype(bool)].copy()
    raw_only = raw[~raw["parc_release_flag"].astype(bool)].copy()
    raw_ranked = raw.sort_values(["frozen_model_score", "candidate_id"], ascending=[False, True]).copy()
    rows: list[dict] = []

    def add_arm(name: str, data: pd.DataFrame) -> None:
        for rank, (_, row) in enumerate(data.head(n_arm + min_arm).iterrows(), start=1):
            primary = rank <= n_arm
            rows.append(
                {
                    "arm": name,
                    "candidate_id": row["candidate_id"],
                    "selected_for_dft": bool(primary),
                    "dft_job_id": "",
                    "selection_rank": rank,
                    "selection_rule": name,
                    "score_rank": int(row.get("raw_rank", rank)) if not pd.isna(row.get("raw_rank", rank)) else rank,
                    "parc_release_flag": bool(row["parc_release_flag"]),
                    "raw_topK_member": True,
                    "reserve_order": "" if primary else rank - n_arm,
                    "evidence_status": "frozen_before_DFT_outcomes",
                    "primary_or_reserve": "primary" if primary else "reserve",
                    "source_rank": rank,
                    "frozen_model_score": row["frozen_model_score"],
                    "structure_ref": row.get("structure_ref", ""),
                    "structure_sha256": row.get("structure_sha256", ""),
                }
            )

    add_arm("PARC-release", released)
    add_arm("raw-only rejected tail", raw_only)
    matched = raw_ranked.head(len(released)).copy() if len(released) else raw_ranked.iloc[[]].copy()
    if len(matched) and set(matched["candidate_id"]) == set(released["candidate_id"]):
        matched = raw_ranked.iloc[[]].copy()
    add_arm("raw top-R matched", matched)
    selection = pd.DataFrame(rows)
    return selection


def export_jobs(selection: pd.DataFrame, dft_engine: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = selection[selection["selected_for_dft"].astype(bool)].copy()
    jobs = []
    updated = selection.copy()
    for idx, row in primary.iterrows():
        arm_slug = str(row["arm"]).lower().replace(" ", "_").replace("-", "_")
        job_id = f"chgnetv2-{arm_slug}-{int(row['selection_rank']):04d}"
        jobs.append(
            {
                "dft_job_id": job_id,
                "candidate_id": row["candidate_id"],
                "arm": row["arm"],
                "structure_ref": row["structure_ref"],
                "structure_sha256": row["structure_sha256"],
                "dft_engine": dft_engine,
                "input_status": "ready_for_private_DFT_input_export",
                "failure_policy": "conservative_failed_DFT_counted_not_certified_stable",
                "selected_before_DFT_outcome": True,
                "outcome_available": False,
                "outcome_file": "",
                "evidence_status": "frozen_selection_before_DFT_outcomes",
            }
        )
        updated.loc[idx, "dft_job_id"] = job_id
    return updated, pd.DataFrame(jobs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-dir", default=str(DEFAULT_V1))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM_SUMMARY))
    parser.add_argument("--wbm-step1-json-bz2", default=str(DEFAULT_WBM_STEP1))
    parser.add_argument("--pgcgm-archive", default=str(DEFAULT_PGCGM_ARCHIVE))
    parser.add_argument("--max-sites", type=int, default=80)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--K", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-per-arm", type=int, default=40)
    parser.add_argument("--minimum-analyzable-per-arm", type=int, default=25)
    parser.add_argument("--dft-engine", default="VASP-or-equivalent-MP-compatible-engine")
    parser.add_argument("--checkpoint-every", type=int, default=100)
    args = parser.parse_args()

    out = Path(args.out_dir)
    private = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v2")
    out.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    protocol = {
        "trial_name": "materials_prospective_dft_followup_chgnet_v2",
        "scorer": "CHGNet",
        "scorer_version_requested": "0.4.2",
        "model_load_rule": "CHGNet.load()",
        "primary_model_role": "locally_executable_frozen_scorer",
        "alpha": args.alpha,
        "rho": args.rho,
        "K": args.K,
        "seed": args.seed,
        "block": "composition-family",
        "max_sites_primary": args.max_sites,
        "arms": {"PARC-release": args.n_per_arm, "raw-only rejected tail": args.n_per_arm, "raw top-R matched": args.n_per_arm},
        "minimum_analyzable_per_arm": args.minimum_analyzable_per_arm,
        "failure_policy": "conservative_failed_DFT_counted_not_certified_stable",
        "no_dft_outcomes_used": True,
    }
    (out / "protocol_v2_chgnet.yaml").write_text(yaml.safe_dump(protocol, sort_keys=False), encoding="utf-8")
    (out / "A3_V2_CHGNET_PROTOCOL.md").write_text(
        "# A3-v2 CHGNet Prospective DFT Follow-Up Protocol\n\n"
        "This protocol replaces the blocked ALIGNN-FF A3 scorer with a locally executable CHGNet scorer. "
        "CHGNet scores are frozen before any new DFT outcomes are computed. The score is a frozen utility score "
        "(`-CHGNet energy per atom`), not a DFT stability label.\n",
        encoding="utf-8",
    )

    v1_block = pd.DataFrame(
        [
            {
                "trial": "A3-v1_ALIGNN_FF",
                "status": "blocked_model_unavailable",
                "download_status": "blocked_download_403_or_bad_zip",
                "invalid_model_smoke": "generative-materials-discovery checkpoint rejected; nonphysical outputs / incompatible architecture",
                "benchmark_csv_policy": "benchmark predictions are not arbitrary-candidate scorers",
                "completed_positive_result": False,
            }
        ]
    )
    v1_block.to_csv(out / "table_alignnff_v1_blocked_status.csv", index=False)

    calibration_subset = build_wbm_calibration_subset(Path(args.wbm_summary), args.max_sites)
    pgcgm_subset = build_pgcgm_scoring_subset(Path(args.v1_dir), args.max_sites)
    calibration_subset.to_csv(out / "table_wbm_calibration_subset_chgnet_v2.csv", index=False)
    pgcgm_subset.to_csv(out / "candidate_universe_chgnet_v2.csv", index=False)

    print("loading CHGNet", flush=True)
    model = CHGNet.load()
    entries = load_wbm_step1_entries(Path(args.wbm_step1_json_bz2))
    archive_index = load_pgcgm_tar_index(Path(args.pgcgm_archive))

    def get_wbm_structure(row: pd.Series) -> Structure:
        return Structure.from_dict(entries[material_id_step_index(str(row["material_id"]))]["structure"])

    calibration_scores = score_with_checkpoint(
        calibration_subset,
        model=model,
        source="WBM_step1_one_per_composition_family",
        out_private=private / "wbm_calibration_scores_chgnet_v2_private.csv",
        structure_getter=get_wbm_structure,
        checkpoint_every=args.checkpoint_every,
    )
    with tarfile.open(Path(args.pgcgm_archive), "r:gz") as pgcgm_archive:
        def get_pgcgm_structure(row: pd.Series) -> Structure:
            return read_pgcgm_structure_from_tar(pgcgm_archive, archive_index, str(row["structure_ref"]))

        generated_scores = score_with_checkpoint(
            pgcgm_subset,
            model=model,
            source="PGCGM_generated_candidates",
            out_private=private / "pgcgm_candidate_scores_chgnet_v2_private.csv",
            structure_getter=get_pgcgm_structure,
            checkpoint_every=args.checkpoint_every,
        )
    calibration_scores, generated_scores, element_refs = add_formation_proxy_scores(calibration_scores, generated_scores)
    calibration_scores.to_csv(out / "calibration_scores_chgnet_v2.csv", index=False)
    generated_scores.to_csv(out / "candidate_scores_chgnet_v2.csv", index=False)
    element_refs.to_csv(out / "table_chgnet_v2_element_reference_fit.csv", index=False)

    raw, diag = compute_prospective_release(
        calibration_scores,
        generated_scores,
        alpha=args.alpha,
        rho=args.rho,
        budget=args.K,
        seed=args.seed,
    )
    raw = raw.reset_index(drop=True)
    raw["raw_rank"] = np.arange(1, len(raw) + 1)
    raw.to_csv(out / "table_chgnet_v2_raw_topK_with_evalues.csv", index=False)
    pd.DataFrame([diag]).to_csv(out / "table_chgnet_v2_selection_diagnostics.csv", index=False)

    if int(diag["released"]) < args.minimum_analyzable_per_arm:
        selection = pd.DataFrame(columns=SELECTION_COLUMNS)
        jobs = pd.DataFrame(columns=DFT_JOB_COLUMNS)
        status = "blocked_no_parc_release_for_primary_arm"
    else:
        selection = freeze_selection(raw, args.n_per_arm, args.minimum_analyzable_per_arm)
        parc_primary = selection[
            selection.get("arm", pd.Series(dtype=str)).eq("PARC-release")
            & selection.get("selected_for_dft", pd.Series(dtype=bool)).astype(bool)
        ]
        if selection.empty or len(parc_primary) < args.minimum_analyzable_per_arm:
            status = "blocked_nonempty_selection_gate_failed"
            if selection.empty:
                selection = pd.DataFrame(columns=SELECTION_COLUMNS)
            jobs = pd.DataFrame(columns=DFT_JOB_COLUMNS)
        else:
            status = "nonempty_selection_frozen_before_DFT"
            selection, jobs = export_jobs(selection, args.dft_engine)
    selection = selection.reindex(columns=SELECTION_COLUMNS)
    jobs = jobs.reindex(columns=DFT_JOB_COLUMNS)
    selection.to_csv(out / "selection_frozen_chgnet_v2.csv", index=False)
    jobs.to_csv(out / "dft_job_manifest_chgnet_v2.csv", index=False)

    status_rows = pd.DataFrame(
        [
            {
                "item": "ALIGNN_FF_A3_v1",
                "status": "blocked_model_unavailable",
                "blocks_DFT_submission": False,
                "completed_positive_result": False,
                "reason": "kept as blocked record; no ALIGNN-FF A3 result claimed",
            },
            {
                "item": "CHGNet_scoring",
                "status": "completed" if len(generated_scores) else "blocked",
                "blocks_DFT_submission": False,
                "completed_positive_result": False,
                "reason": f"scored {int(generated_scores['score_status'].eq('scored').sum())} generated candidates and {int(calibration_scores['score_status'].eq('scored').sum())} calibration candidates",
            },
            {
                "item": "selection_frozen_chgnet_v2",
                "status": status,
                "blocks_DFT_submission": status != "nonempty_selection_frozen_before_DFT",
                "completed_positive_result": False,
                "reason": "selection is frozen before DFT outcomes; DFT outcomes are not present",
            },
        ]
    )
    status_rows.to_csv(out / "table_chgnet_v2_freeze_status.csv", index=False)
    (out / "CHGNET_V2_CLOSEOUT.md").write_text(
        "# CHGNet A3-v2 Closeout\n\n"
        f"Status: `{status}`.\n\n"
        "ALIGNN-FF A3-v1 remains blocked. CHGNet A3-v2 uses `CHGNet.load()` as a locally executable frozen scorer for both WBM calibration representatives and PGCGM generated candidates. "
        "The frozen score is a utility score, not a DFT stability label. No new DFT outcomes are included.\n\n"
        f"- Generated candidates scored: `{int(generated_scores['score_status'].eq('scored').sum())}`.\n"
        f"- WBM calibration representatives scored: `{int(calibration_scores['score_status'].eq('scored').sum())}`.\n"
        f"- PARC released candidates in raw top-{args.K}: `{diag['released']}`.\n"
        f"- DFT jobs exported: `{len(jobs)}`.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
