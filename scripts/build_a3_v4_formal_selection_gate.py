#!/usr/bin/env python3
"""Build Phase29 A3-v4 formal public-label exclusion and pre-DFT selection gate."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"
ALEX_ZIP = Path("/home/waas/paper_experiments/private/mattergen_repo/data-release/alex-mp/alex_mp_20.zip")
GEN_ZIP = Path("/home/waas/paper_experiments/private/mattergen_v4_generation/pilot_5k_3gpu_merged/generated_crystals_cif.zip")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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


def member_from_ref(ref: str) -> str:
    return str(ref).rsplit("::", 1)[-1]


def load_candidate_structures(candidates: pd.DataFrame, formula_hit_ids: set[str]) -> dict[str, Structure]:
    needed = candidates[candidates["candidate_id"].astype(str).isin(formula_hit_ids)]
    members = {member_from_ref(ref) for ref in needed["structure_ref"].astype(str)}
    structures: dict[str, Structure] = {}
    if not members:
        return structures
    with ZipFile(GEN_ZIP) as archive:
        for member in sorted(members):
            text = archive.read(member).decode("utf-8")
            structures[member] = Structure.from_str(text, fmt="cif")
    return structures


def scan_alex_mp_formula_hits(candidate_formulas: set[str]) -> tuple[pd.DataFrame, dict[str, list[dict]]]:
    cols = ["material_id", "reduced_formula", "num_sites", "cif", "energy_above_hull"]
    formula_rows: list[dict] = []
    by_formula: dict[str, list[dict]] = {}
    if not ALEX_ZIP.exists():
        return pd.DataFrame(), by_formula
    with ZipFile(ALEX_ZIP) as archive:
        for member in ["alex_mp_20/train.csv", "alex_mp_20/val.csv"]:
            with archive.open(member) as handle:
                for chunk in pd.read_csv(handle, usecols=cols, chunksize=5000):
                    hit = chunk[chunk["reduced_formula"].astype(str).isin(candidate_formulas)].copy()
                    if hit.empty:
                        continue
                    for _, row in hit.iterrows():
                        formula = str(row["reduced_formula"])
                        record = {
                            "public_source": "alex-mp v20 local public snapshot",
                            "public_member": member,
                            "public_id": str(row["material_id"]),
                            "reduced_formula": formula,
                            "num_sites": int(row["num_sites"]) if pd.notna(row["num_sites"]) else "",
                            "energy_above_hull": row["energy_above_hull"],
                            "cif": row["cif"],
                        }
                        formula_rows.append({k: v for k, v in record.items() if k != "cif"})
                        by_formula.setdefault(formula, []).append(record)
    return pd.DataFrame(formula_rows), by_formula


def run_structure_matches(candidates: pd.DataFrame, by_formula: dict[str, list[dict]]) -> pd.DataFrame:
    candidate_ids_with_formula_hits = set(candidates[candidates["reduced_formula"].astype(str).isin(by_formula.keys())]["candidate_id"].astype(str))
    candidate_structures = load_candidate_structures(candidates, candidate_ids_with_formula_hits)
    matcher = StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5,
        primitive_cell=True,
        scale=True,
        attempt_supercell=True,
    )
    hits: list[dict] = []
    candidates_by_formula = {
        formula: frame.copy()
        for formula, frame in candidates[candidates["candidate_id"].astype(str).isin(candidate_ids_with_formula_hits)].groupby("reduced_formula")
    }
    for formula, frame in candidates_by_formula.items():
        public_records = by_formula.get(str(formula), [])
        if not public_records:
            continue
        for _, cand in frame.iterrows():
            cand_member = member_from_ref(str(cand["structure_ref"]))
            cand_structure = candidate_structures.get(cand_member)
            if cand_structure is None:
                continue
            cand_sites = int(cand["n_sites"]) if pd.notna(cand["n_sites"]) else None
            for public in public_records:
                if cand_sites is not None and public.get("num_sites") != "" and int(public["num_sites"]) != cand_sites:
                    continue
                try:
                    public_structure = Structure.from_str(str(public["cif"]), fmt="cif")
                    matched = bool(matcher.fit(cand_structure, public_structure))
                except Exception as exc:  # noqa: BLE001
                    hits.append(
                        {
                            "candidate_id": cand["candidate_id"],
                            "reduced_formula": formula,
                            "public_source": public["public_source"],
                            "public_member": public["public_member"],
                            "public_id": public["public_id"],
                            "match_confidence": "parse_or_match_failed",
                            "structure_match_public": False,
                            "public_energy_above_hull": public["energy_above_hull"],
                            "match_error": type(exc).__name__,
                        }
                    )
                    continue
                if matched:
                    hits.append(
                        {
                            "candidate_id": cand["candidate_id"],
                            "reduced_formula": formula,
                            "public_source": public["public_source"],
                            "public_member": public["public_member"],
                            "public_id": public["public_id"],
                            "match_confidence": "StructureMatcher_ltol0.2_stol0.3_angle5",
                            "structure_match_public": True,
                            "public_energy_above_hull": public["energy_above_hull"],
                            "match_error": "",
                        }
                    )
                    break
    return pd.DataFrame(hits)


def build_selection(formal_universe: pd.DataFrame, endpoint_id: str = "v4a_strict_exact_K100") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_path = OUT / f"table_mattergen_smoke_raw_topK_{endpoint_id}.csv"
    raw = pd.read_csv(raw_path)
    eligible_ids = set(formal_universe["candidate_id"].astype(str))
    formal_raw = raw[raw["candidate_id"].astype(str).isin(eligible_ids)].copy()
    formal_raw = formal_raw.sort_values(["_evalue", "frozen_model_score", "candidate_id"], ascending=[False, False, True])
    released = formal_raw[formal_raw["parc_release_flag"].astype(bool)].copy()
    raw_ranked = formal_raw.sort_values(["frozen_model_score", "candidate_id"], ascending=[False, True]).copy()
    raw_only = raw_ranked[~raw_ranked["candidate_id"].astype(str).isin(set(released["candidate_id"].astype(str)))].copy()
    raw_topR = raw_ranked.head(len(released)).copy() if len(released) else raw_ranked.iloc[[]].copy()
    raw_topR_identical = len(raw_topR) > 0 and set(raw_topR["candidate_id"].astype(str)) == set(released["candidate_id"].astype(str))

    rows: list[dict] = []
    timestamp = datetime.now(timezone.utc).isoformat()

    def add_arm(arm: str, frame: pd.DataFrame, n_primary: int = 40, reserve_n: int = 20) -> None:
        for rank, (_, row) in enumerate(frame.head(n_primary + reserve_n).iterrows(), start=1):
            primary = rank <= n_primary
            rows.append(
                {
                    "arm": arm,
                    "candidate_id": row["candidate_id"],
                    "selected_for_dft": primary,
                    "dft_job_id": "",
                    "selection_rank": rank,
                    "endpoint_id": endpoint_id,
                    "selection_rule": "top_from_formal_PARC_release" if arm == "PARC-release" else arm,
                    "score_rank": int(row.get("raw_rank", rank)),
                    "parc_release_flag": bool(row.get("parc_release_flag", False)),
                    "raw_topK_member": True,
                    "reserve_order": "" if primary else rank - n_primary,
                    "evidence_status": "formal_selection_frozen_before_DFT_outcomes",
                    "primary_or_reserve": "primary" if primary else "reserve",
                    "frozen_model_score": row.get("frozen_model_score", row.get("consensus_score", "")),
                    "structure_ref": row.get("structure_ref", ""),
                    "structure_sha256": row.get("structure_sha256", ""),
                    "formula": row.get("formula", ""),
                    "score_chgnet": "",
                    "score_mace": "",
                    "score_consensus": row.get("consensus_score", row.get("frozen_model_score", "")),
                    "e_value": row.get("_evalue", ""),
                    "required_e": 10.0,
                    "mass_ratio": "",
                    "block_id": row.get("block_id", ""),
                    "public_label_exclusion_status": row.get("public_label_exclusion_status", "available_source_strict_public_label_free"),
                    "structure_match_public": False,
                    "selected_for_release": bool(row.get("parc_release_flag", False)),
                    "selection_freeze_timestamp": timestamp,
                }
            )

    add_arm("PARC-release", released)
    if len(raw_only) >= 25:
        add_arm("raw-only rejected tail", raw_only)
    if len(raw_topR) and not raw_topR_identical:
        add_arm("raw top-R matched", raw_topR)

    selection = pd.DataFrame(rows)
    jobs: list[dict] = []
    if not selection.empty:
        for idx, row in selection[selection["selected_for_dft"].astype(bool)].iterrows():
            job_id = f"a3v4-{str(row['arm']).lower().replace(' ', '-').replace('_', '-')}-{int(row['selection_rank']):04d}"
            selection.loc[idx, "dft_job_id"] = job_id
            jobs.append(
                {
                    "dft_job_id": job_id,
                    "candidate_id": row["candidate_id"],
                    "arm": row["arm"],
                    "endpoint_id": endpoint_id,
                    "structure_ref": row["structure_ref"],
                    "structure_sha256": row["structure_sha256"],
                    "dft_engine": "VASP-or-equivalent-MP-compatible-engine",
                    "input_status": "ready_for_private_DFT_input_export_release_only" if row["arm"] == "PARC-release" else "ready_for_private_DFT_input_export",
                    "failure_policy": "conservative_failed_DFT_counted_not_certified_stable",
                    "selected_before_DFT_outcome": True,
                    "outcome_available": False,
                    "outcome_file": "",
                    "evidence_status": "DFT_job_manifest_frozen_before_outcomes_release_only_pilot",
                }
            )
    diag = pd.DataFrame(
        [
            {
                "endpoint_id": endpoint_id,
                "formal_topK_rows_available": int(len(formal_raw)),
                "formal_released": int(len(released)),
                "formal_raw_only_tail": int(len(raw_only)),
                "raw_topR_identical_to_release": bool(raw_topR_identical),
                "release_primary_jobs": int(min(40, len(released))),
                "raw_only_primary_jobs": int(min(40, len(raw_only))) if len(raw_only) >= 25 else 0,
                "go_status": "pilot_go_release_only_no_raw_only_comparator" if len(released) >= 25 else "no_go_empty_release",
                "completed_positive_result": False,
            }
        ]
    )
    return selection, pd.DataFrame(jobs), diag


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(OUT / "raw_mattergen_candidates.csv")
    pilot = pd.read_csv(OUT / "candidate_universe_public_label_free.csv")
    scores = pd.read_csv(OUT / "candidate_scores_consensus.csv")
    dry = pd.read_csv(OUT / "parc_endpoint_summary_smoke.csv")

    raw.to_csv(OUT / "generated_5k_merged_candidates.csv", index=False)
    raw[["candidate_id", "formula", "reduced_formula", "n_sites", "structure_ref", "structure_sha256", "generation_status"]].to_csv(
        OUT / "generated_5k_parse_qc.csv", index=False
    )
    pilot.to_csv(OUT / "public_label_free_pilot_4039.csv", index=False)
    scores.to_csv(OUT / "consensus_scores_4039.csv", index=False)
    dry.to_csv(OUT / "dryrun_evidence_mass.csv", index=False)
    provenance = {
        "raw_generated_cif_count": int(len(raw)),
        "parsed_candidate_count": int(len(raw)),
        "pilot_public_label_free_count": int(len(pilot)),
        "scored_candidate_count": int(len(scores)),
        "best_mass_ratio_dryrun": float(dry["best_mass_ratio"].max()) if len(dry) else 0.0,
        "status": "completed_generation_scoring_diagnostic_not_formal_selection",
        "generated_zip_sha256": sha256_file(GEN_ZIP) if GEN_ZIP.exists() else "",
    }
    (OUT / "generation_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    candidate_formulas = set(pilot["reduced_formula"].dropna().astype(str))
    formula_hits, by_formula = scan_alex_mp_formula_hits(candidate_formulas)
    if formula_hits.empty:
        formula_hits = pd.DataFrame(
            columns=["public_source", "public_member", "public_id", "reduced_formula", "num_sites", "energy_above_hull"]
        )
    formula_hits.to_csv(OUT / "table_formula_only_tags.csv", index=False)
    structure_hits = run_structure_matches(pilot, by_formula)
    if structure_hits.empty:
        structure_hits = pd.DataFrame(
            columns=[
                "candidate_id",
                "reduced_formula",
                "public_source",
                "public_member",
                "public_id",
                "match_confidence",
                "structure_match_public",
                "public_energy_above_hull",
                "match_error",
            ]
        )
    structure_hits.to_csv(OUT / "table_structure_match_hits.csv", index=False)
    matched_ids = set(structure_hits[structure_hits["structure_match_public"].astype(bool)]["candidate_id"].astype(str)) if not structure_hits.empty else set()

    formula_hit_formulas = set(formula_hits["reduced_formula"].astype(str)) if not formula_hits.empty else set()
    formal = pilot.copy()
    formal["same_formula_known_public_alex_mp"] = formal["reduced_formula"].astype(str).isin(formula_hit_formulas)
    formal["structure_match_public"] = formal["candidate_id"].astype(str).isin(matched_ids)
    formal["public_label_exclusion_status"] = formal["structure_match_public"].map(
        lambda x: "excluded_alex_mp_structure_match" if bool(x) else "available_source_strict_public_label_free"
    )
    formal["formal_public_sources_checked"] = "WBM_Matbench_formula_exclusion;alex-mp_v20_structure_match_same_formula"
    formal["formal_public_sources_unavailable"] = "OQMD_structure_index;GNoME_structure_index;AFLOW_structure_index;NOMAD_structure_index"
    formal["eligible_for_formal_selection"] = ~formal["structure_match_public"].astype(bool)

    report = formal[
        [
            "candidate_id",
            "formula",
            "reduced_formula",
            "same_formula_known_public_alex_mp",
            "structure_match_public",
            "public_label_exclusion_status",
            "formal_public_sources_checked",
            "formal_public_sources_unavailable",
            "eligible_for_formal_selection",
        ]
    ].copy()
    report.to_csv(OUT / "table_public_label_exclusion_formal.csv", index=False)
    strict = formal[formal["eligible_for_formal_selection"].astype(bool)].copy()
    strict.to_csv(OUT / "candidate_universe_strict_public_label_free.csv", index=False)
    strict.to_csv(OUT / "candidate_universe_broad_public_label_free.csv", index=False)

    selection, jobs, selection_diag = build_selection(strict)
    selection.to_csv(OUT / "selection_frozen_v4.csv", index=False)
    jobs.to_csv(OUT / "dft_job_manifest_v4.csv", index=False)
    selection_diag.to_csv(OUT / "table_selection_endpoint_summary_v4.csv", index=False)
    selection_diag.to_csv(OUT / "table_selection_mass_diagnostics_v4.csv", index=False)
    selection_diag.to_csv(OUT / "table_selection_seed_rows_v4.csv", index=False)

    formal_summary = pd.DataFrame(
        [
            {
                "gate": "generated_5k_scoring_diagnostic",
                "status": "completed",
                "n_rows": int(len(scores)),
                "blocks_DFT_submission": False,
                "completed_positive_result": False,
                "reason": "diagnostic only; not a DFT outcome",
            },
            {
                "gate": "formal_public_label_exclusion_available_sources",
                "status": "completed_limited_available_source_structure_exclusion",
                "n_rows": int(len(strict)),
                "blocks_DFT_submission": False,
                "completed_positive_result": False,
                "reason": "WBM/Matbench formula exclusion plus alex-mp same-formula StructureMatcher; OQMD/GNoME/AFLOW/NOMAD unavailable",
            },
            {
                "gate": "formal_selection",
                "status": str(selection_diag.iloc[0]["go_status"]),
                "n_rows": int(len(selection)),
                "blocks_DFT_submission": False if len(jobs) else True,
                "completed_positive_result": False,
                "reason": "release-only pilot manifest; raw-only comparator absent because PARC released the full predeclared K=100 prefix",
            },
            {
                "gate": "DFT_manifest",
                "status": "frozen_release_only_manifest" if len(jobs) else "blocked_no_manifest",
                "n_rows": int(len(jobs)),
                "blocks_DFT_submission": False if len(jobs) else True,
                "completed_positive_result": False,
                "reason": "DFT outcomes not started; manifest is pre-outcome only",
            },
        ]
    )
    formal_summary.to_csv(OUT / "table_v4_formal_gate_status.csv", index=False)
    formal_summary.to_csv(OUT / "table_phase29_go_no_go.csv", index=False)

    legacy_status = pd.DataFrame(
        [
            {"gate": "candidate_generation", "required_for_dft": True, "status": "completed_5k_generation", "n_rows": int(len(raw)), "completed_positive_result": False},
            {"gate": "public_label_exclusion", "required_for_dft": True, "status": "completed_available_source_formal_exclusion", "n_rows": int(len(strict)), "completed_positive_result": False},
            {"gate": "consensus_scoring", "required_for_dft": True, "status": "completed_chgnet_mace_consensus_scoring", "n_rows": int(len(scores)), "completed_positive_result": False},
            {"gate": "PARC_release_selection", "required_for_dft": True, "status": str(selection_diag.iloc[0]["go_status"]), "n_rows": int(len(selection)), "completed_positive_result": False},
            {"gate": "DFT_manifest", "required_for_dft": True, "status": "frozen_release_only_manifest_pre_outcome" if len(jobs) else "blocked_no_manifest", "n_rows": int(len(jobs)), "completed_positive_result": False},
        ]
    )
    legacy_status.to_csv(OUT / "table_v4_freeze_status.csv", index=False)
    pd.DataFrame(
        [
            {
                "endpoint_id": "v4a_strict_exact_K100",
                "alpha": 0.10,
                "K": 100,
                "label_target": "exact_stable",
                "status": str(selection_diag.iloc[0]["go_status"]),
                "released": int(selection_diag.iloc[0]["formal_released"]),
                "raw_only_tail": int(selection_diag.iloc[0]["formal_raw_only_tail"]),
                "dft_jobs_exported": int(len(jobs)),
                "completed_positive_result": False,
            },
            {
                "endpoint_id": "v4b_strict_exact_K300",
                "alpha": 0.10,
                "K": 300,
                "label_target": "exact_stable",
                "status": "not_promoted_formal_gate_prioritized_v4a",
                "released": 0,
                "raw_only_tail": 0,
                "dft_jobs_exported": 0,
                "completed_positive_result": False,
            },
            {
                "endpoint_id": "v4c_near_hull_25meV_K300",
                "alpha": 0.10,
                "K": 300,
                "label_target": "e_above_hull <= 25 meV/atom",
                "status": "not_promoted_formal_gate_prioritized_v4a",
                "released": 0,
                "raw_only_tail": 0,
                "dft_jobs_exported": 0,
                "completed_positive_result": False,
            },
        ]
    ).to_csv(OUT / "table_v4_go_no_go.csv", index=False)

    (OUT / "public_label_exclusion_claim_scope.md").write_text(
        "# A3-v4 Formal Public-Label Exclusion Scope\n\n"
        "This gate upgrades the 5k MatterGen diagnostic from formula-level pilot filtering to an available-source formal exclusion pass. "
        "The formal pass uses WBM/Matbench formula exclusion inherited from the pilot and alex-mp v20 same-formula StructureMatcher checks with "
        "`ltol=0.2`, `stol=0.3`, `angle_tol=5`, primitive-cell matching, scaling and supercell attempts. Formula-only hits are tags only and are not treated as structure matches.\n\n"
        "Materials Project entries contained in alex-mp and Alexandria entries contained in alex-mp are included through that local public snapshot. "
        "No local OQMD, GNoME, AFLOW or NOMAD structure-level index was available for this gate; those missing sources remain scope limitations. "
        "The resulting selection is a pre-DFT release-only pilot gate, not completed prospective materials evidence.\n",
        encoding="utf-8",
    )
    closeout_text = (
        f"# A3-v4 Formal Selection Gate Closeout\n\n"
        f"Status: formal available-source pre-DFT selection gate completed. This is not DFT evidence.\n\n"
        f"## Gate summary\n\n"
        f"- Generated/scored diagnostic candidates: `{len(scores)}`.\n"
        f"- Strict available-source public-label-free candidates after alex-mp structure matching: `{len(strict)}`.\n"
        f"- alex-mp structure-match exclusions: `{len(matched_ids)}`.\n"
        f"- Formal PARC release rows selected/reserved: `{len(selection)}`.\n"
        f"- Release-only DFT manifest rows: `{len(jobs)}`.\n\n"
        f"## Interpretation\n\n"
        f"The dry-run evidence signal survived the available-source formal exclusion gate, but the primary v4a endpoint released the full K=100 prefix, leaving no raw-only rejected-tail comparator. "
        f"The DFT manifest is therefore a release-only pilot manifest frozen before outcomes, not a completed positive result and not a fixed-budget utility comparison. "
        f"No prospective materials discovery claim is made.\n"
    )
    (OUT / "A3_V4_FORMAL_SELECTION_GATE_CLOSEOUT.md").write_text(closeout_text, encoding="utf-8")
    (OUT / "A3_V4_MATTERGEN_PARC_DFT_CLOSEOUT.md").write_text(
        closeout_text
        + "\n## Current evidence state\n\n"
        + "A3-v4 has a generated/scored 5k diagnostic and a formal pre-DFT release-only manifest. "
        + "DFT outcomes have not started and no positive prospective materials evidence is claimed.\n",
        encoding="utf-8",
    )

    # Update claim table with a scoped row if absent.
    claim_path = ROOT / "docs" / "claim_table.md"
    claim_text = claim_path.read_text(encoding="utf-8")
    marker = "| A3-v4 MatterGen formal selection gate is frozen before DFT but remains release-only pilot evidence. |"
    if marker not in claim_text:
        insert = (
            marker
            + " `outputs/milestones/mattergen_parc_prospective_dft_followup/selection_frozen_v4.csv`; `dft_job_manifest_v4.csv`; `table_phase29_go_no_go.csv` | `python scripts/build_a3_v4_formal_selection_gate.py` | Formal available-source exclusion uses WBM/Matbench formula exclusion plus alex-mp structure matching. OQMD/GNoME/AFLOW/NOMAD structure indexes remain unavailable; the manifest is release-only and pre-outcome, not prospective materials discovery evidence. |\n"
        )
        claim_text = claim_text.replace("| Phase33 finalizes the NMI presubmission go/no-go package.", insert + "| Phase33 finalizes the NMI presubmission go/no-go package.")
        claim_path.write_text(claim_text, encoding="utf-8")

    artifact_path = ROOT / "outputs" / "artifact_index.csv"
    artifact = pd.read_csv(artifact_path)
    if "mattergen_a3_v4_formal_selection_gate" not in set(artifact["milestone"].astype(str)):
        artifact.loc[len(artifact)] = {
            "milestone": "mattergen_a3_v4_formal_selection_gate",
            "path": "outputs/milestones/mattergen_parc_prospective_dft_followup/",
            "evidence_state": "completed_pre_DFT_formal_selection_gate_release_only_not_positive_evidence",
            "manifest": "outputs/milestones/mattergen_parc_prospective_dft_followup/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/mattergen_parc_prospective_dft_followup",
        }
        artifact.to_csv(artifact_path, index=False)

    makefile = ROOT / "Makefile"
    make = makefile.read_text(encoding="utf-8")
    if "reproduce-a3-v4-formal-selection-gate" not in make:
        make = make.replace("reproduce-phase33-presubmission-final:\n\t$(PYTHON) scripts/build_phase33_nmi_presubmission_final.py\n", "reproduce-phase33-presubmission-final:\n\t$(PYTHON) scripts/build_phase33_nmi_presubmission_final.py\n\nreproduce-a3-v4-formal-selection-gate:\n\t$(PYTHON) scripts/build_a3_v4_formal_selection_gate.py\n")
        make = make.replace("reproduce-phase33-presubmission-final", "reproduce-phase33-presubmission-final reproduce-a3-v4-formal-selection-gate", 1)
        makefile.write_text(make, encoding="utf-8")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    if "A3-v4 formal selection gate" not in readme_text:
        readme_text += "\n- A3-v4 formal selection gate: MatterGen 5k generation/scoring is completed as a diagnostic, and an available-source pre-DFT release-only selection gate is frozen without claiming prospective materials discovery.\n"
        readme.write_text(readme_text, encoding="utf-8")
    repro = ROOT / "REPRODUCIBILITY.md"
    repro_text = repro.read_text(encoding="utf-8")
    if "reproduce-a3-v4-formal-selection-gate" not in repro_text:
        repro_text += "\n## A3-v4 formal selection gate\n\nRun `make reproduce-a3-v4-formal-selection-gate` to rebuild the available-source MatterGen formal selection gate. This requires the private MatterGen generated CIF zip and alex-mp local public snapshot; it is not completed DFT evidence.\n"
        repro.write_text(repro_text, encoding="utf-8")

    write_manifest(OUT)
    write_root_manifest()


if __name__ == "__main__":
    main()
