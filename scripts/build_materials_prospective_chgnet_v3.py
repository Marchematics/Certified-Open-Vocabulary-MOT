#!/usr/bin/env python3
"""Build A3-v3 CHGNet near-hull prospective DFT follow-up gate.

A3-v3 formalizes the near-hull parent-prototype substitution route:

* parent structures are low-energy WBM step-1 unique prototypes;
* substitutions are isovalent or chemically similar;
* public-label exclusion is conservative over locally available indexes;
* CHGNet is used only as a frozen utility scorer;
* DFT job manifests are exported only if a predeclared endpoint has a
  nonempty PARC release large enough for the analyzable DFT budget.

The script intentionally creates a no-go artifact rather than a fake DFT
manifest if the strict/operational gates remain empty.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from chgnet.model.model import CHGNet
from pymatgen.core import Composition, Element, Structure

from build_materials_prospective_chgnet_v2 import (
    DEFAULT_WBM_STEP1,
    DEFAULT_WBM_SUMMARY,
    DFT_JOB_COLUMNS,
    SELECTION_COLUMNS,
    add_formation_proxy_scores,
    build_wbm_calibration_subset,
    compute_prospective_release,
    export_jobs,
    freeze_selection,
    load_wbm_step1_entries,
    material_id_step_index,
    score_with_checkpoint,
    sha256_file,
    write_manifest,
)
from run_materials_discovery_parc_flagship import add_blocks


DEFAULT_OUT = Path("outputs/milestones/materials_prospective_dft_followup_chgnet_v3")
DEFAULT_V2 = Path("outputs/milestones/materials_prospective_dft_followup_chgnet_v2")
DEFAULT_PRIVATE = Path("/home/waas/paper_experiments/private/materials_prospective_dft_followup_chgnet_v3")

CHEMICALLY_SIMILAR_GROUPS = [
    ["Li", "Na", "K", "Rb", "Cs"],
    ["Be", "Mg", "Ca", "Sr", "Ba"],
    ["Sc", "Y", "La", "Lu"],
    ["Ti", "Zr", "Hf"],
    ["V", "Nb", "Ta"],
    ["Cr", "Mo", "W"],
    ["Mn", "Re"],
    ["Fe", "Ru", "Os"],
    ["Co", "Rh", "Ir"],
    ["Ni", "Pd", "Pt"],
    ["Cu", "Ag", "Au"],
    ["Zn", "Cd"],
    ["B", "Al", "Ga", "In"],
    ["C", "Si", "Ge", "Sn", "Pb"],
    ["N", "P", "As", "Sb", "Bi"],
    ["O", "S", "Se", "Te"],
    ["F", "Cl", "Br", "I"],
]

ELEMENT_TO_GROUP = {
    element: tuple(group)
    for group in CHEMICALLY_SIMILAR_GROUPS
    for element in group
}

EXCLUDED_ELEMENTS = {
    "H",
    "He",
    "Ne",
    "Ar",
    "Kr",
    "Xe",
    "Rn",
    "Tc",
    "Pm",
    "Po",
    "At",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
}


def structure_digest(structure: Structure) -> str:
    return hashlib.sha256(structure.to(fmt="cif").encode("utf-8")).hexdigest()


def normalized_formula(formula: str) -> str:
    return str(formula).replace(" ", "")


def safe_reduced_formula(formula: str) -> str:
    try:
        return Composition(formula).reduced_formula
    except Exception:  # noqa: BLE001 - public artifact should keep going.
        return normalized_formula(formula)


def chemical_system(formula: str) -> str:
    try:
        return "-".join(sorted(str(el) for el in Composition(formula).elements))
    except Exception:  # noqa: BLE001
        return ""


def formula_elements(formula: str) -> set[str]:
    return {str(el) for el in Composition(formula).elements}


def is_allowed_parent(formula: str) -> bool:
    try:
        elements = formula_elements(formula)
    except Exception:  # noqa: BLE001
        return False
    return bool(elements) and not (elements & EXCLUDED_ELEMENTS)


def load_near_hull_parents(summary_path: Path, parent_ehull_mev: float, max_sites: int) -> pd.DataFrame:
    cols = [
        "material_id",
        "formula",
        "n_sites",
        "e_above_hull_mp2020_corrected_ppd_mp",
        "e_form_per_atom_mp2020_corrected",
        "wyckoff_spglib",
        "unique_prototype",
    ]
    frame = pd.read_csv(summary_path, usecols=cols)
    frame["n_sites"] = pd.to_numeric(frame["n_sites"], errors="coerce")
    frame["parent_e_above_hull"] = pd.to_numeric(frame["e_above_hull_mp2020_corrected_ppd_mp"], errors="coerce")
    frame = frame[
        frame["material_id"].astype(str).str.startswith("wbm-1-")
        & frame["unique_prototype"].astype(bool)
        & frame["n_sites"].le(max_sites)
        & frame["parent_e_above_hull"].le(parent_ehull_mev / 1000.0)
        & frame["formula"].astype(str).map(is_allowed_parent)
    ].copy()
    frame = add_blocks(frame)
    frame = frame.sort_values(
        ["parent_e_above_hull", "n_sites", "material_id"],
        ascending=[True, True, True],
        key=lambda s: s.str.split("-").str[2].astype(int) if s.name == "material_id" else s,
    )
    return frame.reset_index(drop=True)


def substitution_options(elements: list[str], max_pair_replacements_per_element: int) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    element_set = set(elements)
    for old in elements:
        group = ELEMENT_TO_GROUP.get(old)
        if not group:
            continue
        for new in group:
            if new == old or new in element_set or new in EXCLUDED_ELEMENTS:
                continue
            options.append({old: new})

    # Add small deterministic two-site substitutions for parents with multiple
    # replaceable species. This expands the near-hull pool while preserving the
    # isovalent/chemically similar rule.
    per_element: dict[str, list[str]] = {}
    for old in elements:
        group = ELEMENT_TO_GROUP.get(old)
        if not group:
            continue
        choices = [new for new in group if new != old and new not in element_set and new not in EXCLUDED_ELEMENTS]
        if choices:
            per_element[old] = choices[:max_pair_replacements_per_element]
    for old_a, old_b in combinations(sorted(per_element), 2):
        for new_a in per_element[old_a]:
            for new_b in per_element[old_b]:
                if new_a == new_b:
                    continue
                options.append({old_a: new_a, old_b: new_b})
    return options


def apply_substitution(parent: Structure, mapping: dict[str, str]) -> Structure:
    structure = parent.copy()
    structure.replace_species({Element(old): Element(new) for old, new in mapping.items()})
    return structure


def build_near_hull_pool(
    *,
    parents: pd.DataFrame,
    entries: list[dict],
    known_formulas: set[str],
    target_candidates: int,
    max_candidates_per_parent: int,
    max_pair_replacements_per_element: int,
) -> tuple[pd.DataFrame, dict[str, Structure], pd.DataFrame]:
    records: list[dict] = []
    structures: dict[str, Structure] = {}
    rejection_rows: list[dict] = []
    seen_formulas: set[str] = set()
    seen_structure_hashes: set[str] = set()

    for parent_rank, parent_row in parents.iterrows():
        if len(records) >= target_candidates:
            break
        material_id = str(parent_row["material_id"])
        try:
            parent_structure = Structure.from_dict(entries[material_id_step_index(material_id)]["structure"])
            elements = sorted(str(el) for el in parent_structure.composition.elements)
        except Exception as exc:  # noqa: BLE001
            rejection_rows.append(
                {
                    "parent_material_id": material_id,
                    "candidate_id": "",
                    "status": f"parent_failed_{type(exc).__name__}",
                    "reason": str(exc)[:200],
                }
            )
            continue
        parent_count = 0
        for mapping in substitution_options(elements, max_pair_replacements_per_element):
            if len(records) >= target_candidates or parent_count >= max_candidates_per_parent:
                break
            mapping_label = ";".join(f"{old}->{new}" for old, new in sorted(mapping.items()))
            try:
                candidate_structure = apply_substitution(parent_structure, mapping)
                formula = normalized_formula(candidate_structure.composition.reduced_formula)
                full_formula = normalized_formula(candidate_structure.composition.formula)
                n_sites = int(len(candidate_structure))
                digest = structure_digest(candidate_structure)
            except Exception as exc:  # noqa: BLE001
                rejection_rows.append(
                    {
                        "parent_material_id": material_id,
                        "candidate_id": "",
                        "status": f"substitution_failed_{type(exc).__name__}",
                        "reason": mapping_label,
                    }
                )
                continue
            if formula in known_formulas or full_formula in known_formulas:
                rejection_rows.append(
                    {
                        "parent_material_id": material_id,
                        "candidate_id": "",
                        "status": "rejected_public_wbm_formula_match",
                        "reason": formula,
                    }
                )
                continue
            if formula in seen_formulas or digest in seen_structure_hashes:
                rejection_rows.append(
                    {
                        "parent_material_id": material_id,
                        "candidate_id": "",
                        "status": "rejected_internal_duplicate",
                        "reason": formula,
                    }
                )
                continue
            candidate_id = hashlib.sha256(f"{material_id}|{mapping_label}|{digest}".encode("utf-8")).hexdigest()[:16]
            seen_formulas.add(formula)
            seen_structure_hashes.add(digest)
            structures[candidate_id] = candidate_structure
            records.append(
                {
                    "candidate_id": f"nh-{candidate_id}",
                    "formula": formula,
                    "reduced_formula": formula,
                    "chemical_system": chemical_system(formula),
                    "anonymous_formula": candidate_structure.composition.anonymized_formula,
                    "n_sites": n_sites,
                    "source_parent_material_id": material_id,
                    "source_parent_rank": int(parent_rank) + 1,
                    "parent_formula": normalized_formula(str(parent_row["formula"])),
                    "parent_e_above_hull": float(parent_row["parent_e_above_hull"]),
                    "parent_block_id": str(parent_row["composition_family_pair"]),
                    "wyckoff_spglib": str(parent_row.get("wyckoff_spglib", "")),
                    "substitution_rule": mapping_label,
                    "generation_rule": "near_hull_parent_isovalent_or_chemically_similar_substitution",
                    "structure_ref": f"wbm_step1::{material_id}::{mapping_label}",
                    "structure_sha256": digest,
                    "public_label_status": "no_known_public_stability_label_in_available_indexes",
                    "public_label_index_scope": "WBM_Matbench_formula_exclusion; other public indexes unavailable locally",
                    "keep_for_followup": True,
                    "evidence_status": "generated_before_DFT_outcomes",
                }
            )
            parent_count += 1
    frame = pd.DataFrame(records)
    if not frame.empty:
        frame = add_blocks(frame)
        frame["block_id"] = frame["composition_family_pair"]
    return frame, structures, pd.DataFrame(rejection_rows)


def public_label_index_summary(summary_path: Path, out: Path) -> set[str]:
    summary = pd.read_csv(summary_path, usecols=["formula", "material_id"])
    formulas = set(summary["formula"].astype(str).map(normalized_formula))
    rows = [
        {
            "source_name": "WBM_Matbench_summary",
            "status": "available_formula_level_exclusion",
            "n_entries": len(summary),
            "hash": sha256_file(summary_path),
            "matching_method": "formula/reduced-formula exclusion plus generated-pool internal structure hash dedup",
        },
        {
            "source_name": "Materials_Project",
            "status": "unavailable_locally_for_this_gate",
            "n_entries": 0,
            "hash": "",
            "matching_method": "not_run",
        },
        {
            "source_name": "OQMD",
            "status": "unavailable_locally_for_this_gate",
            "n_entries": 0,
            "hash": "",
            "matching_method": "not_run",
        },
        {
            "source_name": "Alexandria",
            "status": "unavailable_locally_for_this_gate",
            "n_entries": 0,
            "hash": "",
            "matching_method": "not_run",
        },
        {
            "source_name": "GNoME",
            "status": "unavailable_locally_for_this_gate",
            "n_entries": 0,
            "hash": "",
            "matching_method": "not_run",
        },
    ]
    pd.DataFrame(rows).to_csv(out / "table_public_label_index_scope_chgnet_v3.csv", index=False)
    return formulas


def endpoint_grid(alpha: float, budget: int) -> list[dict]:
    return [
        {
            "endpoint_id": "v3_strict_K500",
            "endpoint_role": "primary_strict",
            "alpha": alpha,
            "K": budget,
            "interpretation": "strict alpha=0.10 K=500 near-hull follow-up gate",
        },
        {
            "endpoint_id": "v3a_strict_K300",
            "endpoint_role": "strict_lower_budget",
            "alpha": alpha,
            "K": 300,
            "interpretation": "strict alpha=0.10 K=300 fallback before risk relaxation",
        },
        {
            "endpoint_id": "v3b_operational_K500",
            "endpoint_role": "operational_relaxed_risk",
            "alpha": 0.20,
            "K": budget,
            "interpretation": "operational alpha=0.20 K=500 fallback, not a strict pass",
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM_SUMMARY))
    parser.add_argument("--wbm-step1-json-bz2", default=str(DEFAULT_WBM_STEP1))
    parser.add_argument("--v2-dir", default=str(DEFAULT_V2))
    parser.add_argument("--private-dir", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--parent-ehull-mev", type=float, default=25.0)
    parser.add_argument("--max-sites", type=int, default=40)
    parser.add_argument("--target-candidates", type=int, default=5000)
    parser.add_argument("--max-candidates-per-parent", type=int, default=8)
    parser.add_argument("--max-pair-replacements-per-element", type=int, default=2)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--K", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-per-arm", type=int, default=40)
    parser.add_argument("--minimum-analyzable-per-arm", type=int, default=25)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--dft-engine", default="VASP-or-equivalent-MP-compatible-engine")
    args = parser.parse_args()

    out = Path(args.out_dir)
    private = Path(args.private_dir)
    out.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    protocol = {
        "trial_name": "materials_prospective_dft_followup_chgnet_v3_near_hull",
        "scorer": "CHGNet",
        "model_load_rule": "CHGNet.load()",
        "candidate_pool": "near-hull WBM parent prototype substitutions",
        "parent_selection": {
            "source": "WBM step-1 unique prototypes",
            "e_above_hull_max_meV_per_atom": args.parent_ehull_mev,
            "max_sites": args.max_sites,
        },
        "substitution": "isovalent_or_chemically_similar_groups_only",
        "public_label_exclusion": "WBM/Matbench formula-level exclusion plus internal structural dedup; missing external public indexes are recorded as unavailable",
        "alpha": args.alpha,
        "rho": args.rho,
        "K": args.K,
        "seed": args.seed,
        "block": "composition-family",
        "endpoint_hierarchy": endpoint_grid(args.alpha, args.K),
        "arms": {
            "PARC-release": args.n_per_arm,
            "raw-only rejected tail": args.n_per_arm,
            "raw top-R matched": args.n_per_arm,
        },
        "minimum_analyzable_per_arm": args.minimum_analyzable_per_arm,
        "no_dft_outcomes_used": True,
    }
    (out / "protocol_v3_chgnet_near_hull.yaml").write_text(yaml.safe_dump(protocol, sort_keys=False), encoding="utf-8")
    (out / "A3_V3_CHGNET_NEAR_HULL_PROTOCOL.md").write_text(
        "# A3-v3 CHGNet Near-Hull Prospective DFT Follow-Up Protocol\n\n"
        "A3-v3 generates a prospective candidate pool from WBM near-hull parent prototypes using only "
        "isovalent or chemically similar substitutions. Public-label exclusion is conservative over locally "
        "available indexes. CHGNet scores are frozen before any new DFT outcomes. A DFT manifest is produced "
        "only if a predeclared strict or operational endpoint has a sufficiently large PARC release.\n",
        encoding="utf-8",
    )

    known_formulas = public_label_index_summary(Path(args.wbm_summary), out)
    parents = load_near_hull_parents(Path(args.wbm_summary), args.parent_ehull_mev, args.max_sites)
    parents.to_csv(out / "table_near_hull_parent_prototypes_chgnet_v3.csv", index=False)
    entries = load_wbm_step1_entries(Path(args.wbm_step1_json_bz2))
    candidates, structures_by_id, rejections = build_near_hull_pool(
        parents=parents,
        entries=entries,
        known_formulas=known_formulas,
        target_candidates=args.target_candidates,
        max_candidates_per_parent=args.max_candidates_per_parent,
        max_pair_replacements_per_element=args.max_pair_replacements_per_element,
    )
    candidates.to_csv(out / "candidate_universe_chgnet_v3.csv", index=False)
    rejections.to_csv(out / "table_near_hull_candidate_rejections_chgnet_v3.csv", index=False)
    pd.DataFrame(
        [
            {
                "n_parents_available": len(parents),
                "n_generated_candidates": len(candidates),
                "n_blocks_generated": int(candidates["block_id"].nunique()) if not candidates.empty else 0,
                "n_formula_exclusion_rejections": int((rejections.get("status", pd.Series(dtype=str)) == "rejected_public_wbm_formula_match").sum()),
                "n_internal_duplicate_rejections": int((rejections.get("status", pd.Series(dtype=str)) == "rejected_internal_duplicate").sum()),
            }
        ]
    ).to_csv(out / "table_chgnet_v3_pool_summary.csv", index=False)

    print("loading CHGNet", flush=True)
    model = CHGNet.load()
    calibration_subset = build_wbm_calibration_subset(Path(args.wbm_summary), args.max_sites)
    calibration_subset.to_csv(out / "table_wbm_calibration_subset_chgnet_v3.csv", index=False)

    def get_wbm_structure(row: pd.Series) -> Structure:
        return Structure.from_dict(entries[material_id_step_index(str(row["candidate_id"]))]["structure"])

    calibration_scores = score_with_checkpoint(
        calibration_subset,
        model=model,
        source="WBM_step1_one_per_composition_family",
        out_private=private / "wbm_calibration_scores_chgnet_v3_private.csv",
        structure_getter=get_wbm_structure,
        checkpoint_every=args.checkpoint_every,
    )

    structure_lookup = {f"nh-{key}": value for key, value in structures_by_id.items()}

    def get_candidate_structure(row: pd.Series) -> Structure:
        return structure_lookup[str(row["candidate_id"])]

    generated_scores = score_with_checkpoint(
        candidates,
        model=model,
        source="near_hull_isovalent_generated_candidates",
        out_private=private / "near_hull_candidate_scores_chgnet_v3_private.csv",
        structure_getter=get_candidate_structure,
        checkpoint_every=args.checkpoint_every,
    )
    calibration_scores, generated_scores, element_refs = add_formation_proxy_scores(calibration_scores, generated_scores)
    calibration_scores.to_csv(out / "calibration_scores_chgnet_v3.csv", index=False)
    generated_scores.to_csv(out / "candidate_scores_chgnet_v3.csv", index=False)
    element_refs.to_csv(out / "table_chgnet_v3_element_reference_fit.csv", index=False)

    raw_tables: dict[str, pd.DataFrame] = {}
    diagnostics: list[dict] = []
    selected_endpoint = None
    selected_raw = pd.DataFrame()
    for endpoint in endpoint_grid(args.alpha, args.K):
        raw, diag = compute_prospective_release(
            calibration_scores,
            generated_scores,
            alpha=float(endpoint["alpha"]),
            rho=args.rho,
            budget=int(endpoint["K"]),
            seed=args.seed,
        )
        raw = raw.reset_index(drop=True)
        raw["raw_rank"] = np.arange(1, len(raw) + 1)
        raw["endpoint_id"] = endpoint["endpoint_id"]
        raw_tables[endpoint["endpoint_id"]] = raw
        diag = {**endpoint, **diag}
        diag["passes_minimum_analyzable_gate"] = int(diag["released"]) >= args.minimum_analyzable_per_arm
        diagnostics.append(diag)
        if selected_endpoint is None and diag["passes_minimum_analyzable_gate"]:
            selected_endpoint = endpoint
            selected_raw = raw
    pd.DataFrame(diagnostics).to_csv(out / "table_chgnet_v3_endpoint_diagnostics.csv", index=False)
    for endpoint_id, raw in raw_tables.items():
        raw.to_csv(out / f"table_chgnet_v3_raw_topK_{endpoint_id}.csv", index=False)

    if selected_endpoint is None:
        selection = pd.DataFrame(columns=SELECTION_COLUMNS)
        jobs = pd.DataFrame(columns=DFT_JOB_COLUMNS)
        status = "blocked_no_endpoint_release_for_DFT_arm"
        selected_endpoint_id = ""
    else:
        selection = freeze_selection(selected_raw, args.n_per_arm, args.minimum_analyzable_per_arm)
        parc_primary = selection[
            selection.get("arm", pd.Series(dtype=str)).eq("PARC-release")
            & selection.get("selected_for_dft", pd.Series(dtype=bool)).astype(bool)
        ]
        if selection.empty or len(parc_primary) < args.minimum_analyzable_per_arm:
            selection = pd.DataFrame(columns=SELECTION_COLUMNS)
            jobs = pd.DataFrame(columns=DFT_JOB_COLUMNS)
            status = "blocked_nonempty_selection_gate_failed"
            selected_endpoint_id = str(selected_endpoint["endpoint_id"])
        else:
            selection, jobs = export_jobs(selection, args.dft_engine)
            jobs["dft_job_id"] = jobs["dft_job_id"].astype(str).str.replace("chgnetv2", "chgnetv3", regex=False)
            selection["dft_job_id"] = selection["dft_job_id"].astype(str).str.replace("chgnetv2", "chgnetv3", regex=False)
            status = "nonempty_selection_frozen_before_DFT"
            selected_endpoint_id = str(selected_endpoint["endpoint_id"])
    selection = selection.reindex(columns=SELECTION_COLUMNS)
    jobs = jobs.reindex(columns=DFT_JOB_COLUMNS)
    selection.to_csv(out / "selection_frozen_chgnet_v3.csv", index=False)
    jobs.to_csv(out / "dft_job_manifest_chgnet_v3.csv", index=False)

    status_rows = pd.DataFrame(
        [
            {
                "item": "near_hull_candidate_pool",
                "status": "completed" if len(candidates) else "blocked_empty_candidate_pool",
                "blocks_DFT_submission": False,
                "completed_positive_result": False,
                "reason": f"generated {len(candidates)} public-label-excluded near-hull candidates from {len(parents)} parents",
            },
            {
                "item": "CHGNet_scoring_v3",
                "status": "completed" if int(generated_scores["score_status"].eq("scored").sum()) else "blocked",
                "blocks_DFT_submission": False,
                "completed_positive_result": False,
                "reason": f"scored {int(generated_scores['score_status'].eq('scored').sum())} near-hull candidates and {int(calibration_scores['score_status'].eq('scored').sum())} calibration candidates",
            },
            {
                "item": "selection_frozen_chgnet_v3",
                "status": status,
                "blocks_DFT_submission": status != "nonempty_selection_frozen_before_DFT",
                "completed_positive_result": False,
                "reason": f"selected_endpoint={selected_endpoint_id or 'none'}; no DFT outcomes are present",
            },
        ]
    )
    status_rows.to_csv(out / "table_chgnet_v3_freeze_status.csv", index=False)
    max_release = int(max((row["released"] for row in diagnostics), default=0))
    max_ratio = float(max((row["best_mass_ratio"] for row in diagnostics), default=0.0))
    (out / "CHGNET_V3_CLOSEOUT.md").write_text(
        "# CHGNet A3-v3 Near-Hull Closeout\n\n"
        f"Status: `{status}`.\n\n"
        "This milestone tests a larger, more systematic near-hull parent-prototype substitution pool. "
        "It does not contain DFT outcomes. DFT jobs are exported only when a predeclared endpoint has "
        f"at least `{args.minimum_analyzable_per_arm}` PARC-release candidates.\n\n"
        f"- Near-hull parents available: `{len(parents)}`.\n"
        f"- Generated public-label-excluded candidates: `{len(candidates)}`.\n"
        f"- Near-hull candidates scored by CHGNet: `{int(generated_scores['score_status'].eq('scored').sum())}`.\n"
        f"- WBM calibration representatives scored: `{int(calibration_scores['score_status'].eq('scored').sum())}`.\n"
        f"- Maximum release across predeclared endpoints: `{max_release}`.\n"
        f"- Maximum evidence-mass ratio across endpoints: `{max_ratio:.6f}`.\n"
        f"- Selected endpoint: `{selected_endpoint_id or 'none'}`.\n"
        f"- DFT jobs exported: `{len(jobs)}`.\n\n"
        "Completed evidence / diagnostic / protocol-only distinction: this is a prospective gate artifact. "
        "If `selection_frozen_chgnet_v3.csv` and `dft_job_manifest_chgnet_v3.csv` are empty, it is a no-go "
        "diagnostic and not a completed positive result.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
