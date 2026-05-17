#!/usr/bin/env python3
"""Freeze the A3 prospective in-silico DFT follow-up protocol.

This script intentionally does not create DFT outcomes.  If no unlabeled
candidate pool is supplied, it writes schema-complete empty candidate,
selection, public-label exclusion, novelty, and job-manifest files plus an
explicit go/no-go status.  This keeps the A3 milestone usable without
promoting protocol-only artifacts as completed evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_OUT = Path("outputs/milestones/materials_prospective_dft_followup")
DEFAULT_PROTOCOL_DATE = "2026-05-18"


LABEL_COLUMNS = {
    "e_above_hull",
    "e_above_hull_wbm",
    "e_above_hull_mp2020_corrected_ppd_mp",
    "stability_label",
    "stable_label",
    "is_stable",
    "dft_stable",
}

CANDIDATE_COLUMNS = [
    "candidate_id",
    "formula",
    "reduced_formula",
    "elements",
    "anonymous_formula",
    "n_sites",
    "space_group",
    "source_prototype_id",
    "model_family",
    "frozen_model_score",
    "block_id",
    "public_label_status",
    "novelty_status",
    "duplicate_status",
    "keep_for_followup",
    "exclusion_reason",
    "evidence_status",
]

SELECTION_COLUMNS = [
    "candidate_id",
    "arm",
    "arm_rank",
    "reserve_rank",
    "selection_rule",
    "selected_for_dft",
    "dft_job_id",
    "evidence_status",
]

DFT_JOB_COLUMNS = [
    "dft_job_id",
    "candidate_id",
    "arm",
    "dft_engine",
    "input_set",
    "functional",
    "encut_ev",
    "kpoint_policy",
    "electronic_convergence_ev",
    "force_convergence_ev_per_angstrom",
    "spin_policy",
    "relaxation_policy",
    "static_calculation_policy",
    "failure_policy",
    "evidence_status",
]

PUBLIC_LABEL_COLUMNS = [
    "candidate_id",
    "formula",
    "WBM_label_available",
    "Materials_Project_label_available",
    "OQMD_label_available",
    "Alexandria_label_available",
    "GNoME_label_available",
    "keep_for_followup",
    "exclusion_reason",
    "evidence_status",
]

NOVELTY_COLUMNS = [
    "candidate_id",
    "formula",
    "composition_key",
    "structure_matcher_status",
    "matched_public_source",
    "matched_public_id",
    "pool_duplicate_status",
    "keep_for_followup",
    "evidence_status",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def simple_yaml(obj: dict, indent: int = 0) -> str:
    lines: list[str] = []
    pad = " " * indent
    for key, value in obj.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(simple_yaml(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{pad}  -")
                    lines.append(simple_yaml(item, indent + 4))
                else:
                    lines.append(f"{pad}  - {item}")
        elif value is None:
            lines.append(f"{pad}{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{pad}{key}: {'true' if value else 'false'}")
        else:
            text = str(value)
            if text == "" or any(ch in text for ch in [":", "#", "{", "}", "[", "]", ","]):
                text = json.dumps(text)
            lines.append(f"{pad}{key}: {text}")
    return "\n".join(lines)


def parse_elements(formula: str) -> list[str]:
    return re.findall(r"[A-Z][a-z]?", str(formula))


def anonymous_formula(formula: str) -> str:
    elems = parse_elements(formula)
    if not elems:
        return ""
    labels = [chr(ord("A") + i) for i in range(min(len(elems), 26))]
    return "".join(labels)


def normalize_candidate_pool(path: Path | None, score_column: str | None, model_family: str) -> tuple[pd.DataFrame, dict]:
    if path is None:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS), {
            "status": "not_supplied",
            "input_sha256": "",
            "n_input_rows": 0,
            "n_kept_rows": 0,
        }

    raw = pd.read_csv(path)
    df = pd.DataFrame()
    df["formula"] = raw["formula"] if "formula" in raw.columns else ""
    if "candidate_id" in raw.columns:
        df["candidate_id"] = raw["candidate_id"].astype(str)
    elif "material_id" in raw.columns:
        df["candidate_id"] = raw["material_id"].astype(str)
    else:
        df["candidate_id"] = [
            "prospective-candidate-" + hashlib.sha256(f"{i}-{formula}".encode("utf-8")).hexdigest()[:12]
            for i, formula in enumerate(df["formula"].astype(str))
        ]
    df["reduced_formula"] = raw["reduced_formula"] if "reduced_formula" in raw.columns else df["formula"]
    df["elements"] = df["formula"].map(lambda x: "|".join(parse_elements(str(x))))
    df["anonymous_formula"] = raw["anonymous_formula"] if "anonymous_formula" in raw.columns else df["formula"].map(anonymous_formula)
    df["n_sites"] = raw["n_sites"] if "n_sites" in raw.columns else ""
    df["space_group"] = raw["space_group"] if "space_group" in raw.columns else ""
    df["source_prototype_id"] = raw["source_prototype_id"] if "source_prototype_id" in raw.columns else raw.get("wyckoff_spglib", "")
    df["model_family"] = model_family
    chosen_score = score_column
    if chosen_score is None:
        for candidate in ["score", "model_score", "predicted_score", "stability_score", "e_form_per_atom_alignn", "e_form_per_atom"]:
            if candidate in raw.columns:
                chosen_score = candidate
                break
    df["frozen_model_score"] = raw[chosen_score] if chosen_score and chosen_score in raw.columns else ""
    df["block_id"] = (
        df["anonymous_formula"].astype(str)
        + "::"
        + df["elements"].astype(str).map(lambda x: "-".join(sorted([e for e in x.split("|") if e])))
    )
    label_present = raw[[c for c in raw.columns if c in LABEL_COLUMNS]].notna().any(axis=1) if any(c in raw.columns for c in LABEL_COLUMNS) else pd.Series(False, index=raw.index)
    df["public_label_status"] = label_present.map(lambda x: "excluded_public_label_column_present" if bool(x) else "no_public_label_column_detected")
    df["novelty_status"] = "not_crossmatched_without_public_db_index"
    df["duplicate_status"] = df["candidate_id"].duplicated(keep=False).map(lambda x: "duplicate_candidate_id" if bool(x) else "unique_candidate_id")
    keep = (~label_present) & (~df["candidate_id"].duplicated(keep=False))
    df["keep_for_followup"] = keep
    df["exclusion_reason"] = [
        "" if ok else "public_label_or_duplicate_or_missing_crossmatch"
        for ok in keep
    ]
    df["evidence_status"] = "candidate_pool_frozen_pending_public_crossmatch"
    df = df[CANDIDATE_COLUMNS]
    return df, {
        "status": "supplied_schema_normalized",
        "input_sha256": sha256_file(path),
        "n_input_rows": int(len(raw)),
        "n_kept_rows": int(keep.sum()),
    }


def build_protocol(args: argparse.Namespace, pool_info: dict) -> dict:
    return {
        "protocol_id": "A3_prospective_in_silico_DFT_followup",
        "protocol_freeze_date": args.protocol_date,
        "evidence_status": "protocol_frozen_no_DFT_outcomes",
        "primary_model": args.primary_model,
        "alpha": args.alpha,
        "rho": args.rho,
        "requested_K": args.K,
        "block_definition": args.block,
        "arms": {
            "PARC_release": {
                "target_n": args.n_release,
                "minimum_analyzable_n": args.min_analyzable_n,
                "selection_rule": "top_n_from_PARC_certified_release_by_frozen_utility",
            },
            "raw_only_rejected_tail": {
                "target_n": args.n_raw_only,
                "minimum_analyzable_n": args.min_analyzable_n,
                "selection_rule": "top_n_from_raw_topK_minus_PARC_release_by_frozen_utility",
            },
            "raw_topR_matched": {
                "target_n": args.n_raw_matched,
                "minimum_analyzable_n": args.min_analyzable_n,
                "selection_rule": "top_n_from_raw_prefix_of_size_equal_to_PARC_release_size_when_nonredundant",
            },
        },
        "candidate_pool": {
            "status": pool_info["status"],
            "input_sha256": pool_info["input_sha256"],
            "n_input_rows": pool_info["n_input_rows"],
            "n_kept_rows_after_schema_filter": pool_info["n_kept_rows"],
            "requires_public_label_exclusion": True,
            "requires_structure_crossmatch": True,
        },
        "public_label_exclusion": {
            "exclude_WBM_labeled_structures": True,
            "exclude_Materials_Project_labeled_matches": True,
            "exclude_OQMD_labeled_matches": True,
            "exclude_Alexandria_labeled_matches": True,
            "exclude_GNoME_labeled_matches": True,
        },
        "structure_matcher": {
            "ltol": 0.2,
            "stol": 0.3,
            "angle_tol": 5,
            "primitive_cell": True,
            "scale": True,
            "attempt_supercell": True,
        },
        "DFT": {
            "engine": args.dft_engine,
            "input_set": "MPRelaxSet-compatible",
            "functional": "PBE-GGA",
            "encut_ev": 520,
            "kpoint_policy": "MPRelaxSet default or fixed equivalent recorded per job",
            "electronic_convergence_ev": "1e-5",
            "force_convergence_ev_per_angstrom": "0.02",
            "spin_policy": "same frozen magnetic-element rule for all arms",
            "relaxation_policy": "full cell plus ionic relaxation",
            "static_calculation_policy": "final static calculation after relaxation",
            "compatibility_corrections": "MaterialsProject2020Compatibility or fixed chosen correction scheme",
            "failure_policy": "one standard rerun; unresolved failures count as not-certified-stable in the conservative primary analysis",
        },
        "stability_endpoint": {
            "primary": "DFT-stable if energy above hull <= 0 eV/atom under frozen reference hull",
            "sensitivity_25meV": "DFT-stable if energy above hull <= 25 meV/atom",
            "margin_excluded": "report secondary analysis excluding 0 < energy above hull <= 25 meV/atom",
            "hull_unavailable_policy": "count as not-certified-stable in conservative primary analysis and report separately",
        },
        "success_interpretation": {
            "strong_positive": [
                "PARC release instability rate <= alpha under exact-stable primary label",
                "PARC stable hit rate exceeds raw-only tail by at least 20 percentage points",
                "raw-only tail instability rate is at least 2x PARC-release instability rate",
                "PARC prevents at least 50 unstable follow-ups per K=500-equivalent queue",
            ],
            "supportive": "PARC stable hit rate exceeds raw-only tail but intervals overlap or exact-stable result is boundary-sensitive",
            "boundary_or_negative": "PARC-release instability rate exceeds alpha or is not better than raw-only tail",
        },
    }


def build_selection_tables(candidates: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    if candidates.empty or not bool(candidates["keep_for_followup"].astype(bool).any()):
        return pd.DataFrame(columns=SELECTION_COLUMNS), pd.DataFrame(columns=DFT_JOB_COLUMNS)

    # We do not infer PARC membership from a raw candidate pool. A valid A3
    # selection requires a frozen PARC release file or explicit arm assignments.
    return pd.DataFrame(columns=SELECTION_COLUMNS), pd.DataFrame(columns=DFT_JOB_COLUMNS)


def build_public_label_report(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=PUBLIC_LABEL_COLUMNS)
    out = pd.DataFrame()
    out["candidate_id"] = candidates["candidate_id"]
    out["formula"] = candidates["formula"]
    out["WBM_label_available"] = candidates["public_label_status"].eq("excluded_public_label_column_present")
    out["Materials_Project_label_available"] = False
    out["OQMD_label_available"] = False
    out["Alexandria_label_available"] = False
    out["GNoME_label_available"] = False
    out["keep_for_followup"] = candidates["keep_for_followup"]
    out["exclusion_reason"] = candidates["exclusion_reason"]
    out["evidence_status"] = candidates["evidence_status"]
    return out[PUBLIC_LABEL_COLUMNS]


def build_novelty_report(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame(columns=NOVELTY_COLUMNS)
    out = pd.DataFrame()
    out["candidate_id"] = candidates["candidate_id"]
    out["formula"] = candidates["formula"]
    out["composition_key"] = candidates["block_id"]
    out["structure_matcher_status"] = "not_run_without_public_db_index"
    out["matched_public_source"] = ""
    out["matched_public_id"] = ""
    out["pool_duplicate_status"] = candidates["duplicate_status"]
    out["keep_for_followup"] = candidates["keep_for_followup"]
    out["evidence_status"] = candidates["evidence_status"]
    return out[NOVELTY_COLUMNS]


def write_provenance(path: Path, command: str, inputs: dict) -> None:
    payload = {
        "artifact": path.name,
        "command": command,
        "inputs": inputs,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifact_sha256": sha256_file(path),
    }
    path.with_suffix(path.suffix + ".provenance.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_manifest(out_dir: Path) -> None:
    lines = []
    for path in sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name != "MANIFEST_SHA256.txt"):
        rel = path.relative_to(out_dir)
        lines.append(f"{sha256_file(path)}  {rel.as_posix()}")
    (out_dir / "MANIFEST_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown(out_dir: Path, protocol: dict, status: pd.DataFrame) -> None:
    pool_status = protocol["candidate_pool"]["status"]
    primary_status = status[status["item"] == "candidate_pool"].iloc[0]["status"]
    protocol_md = f"""# Prospective In-Silico DFT Follow-Up Protocol

This milestone freezes the A3 protocol before any new DFT outcomes are known.
It is a protocol and selection-freeze package, not a completed DFT result.

## Primary Operating Point

- Model: `{protocol['primary_model']}`
- Alpha: `{protocol['alpha']}`
- Rho: `{protocol['rho']}`
- Requested K: `{protocol['requested_K']}`
- Block definition: `{protocol['block_definition']}`
- Primary arm size: `{protocol['arms']['PARC_release']['target_n']}` candidates per arm
- Minimum analyzable arm size: `{protocol['arms']['PARC_release']['minimum_analyzable_n']}` candidates

## Required Arms

1. `PARC-release`: top candidates from the certified release set.
2. `raw-only rejected tail`: raw top-K candidates not released by PARC.
3. `raw top-R matched`: raw prefix matched to the PARC release size when nonredundant.

## No-Leakage Rules

- Candidate selection must be frozen before new DFT outcomes are computed.
- Candidates with public WBM, Materials Project, OQMD, Alexandria or GNoME
  stability labels are excluded from the prospective follow-up pool.
- Structure-level public duplicate filtering must be documented before DFT.
- K, alpha, rho, gamma, block definition and selection arms must not be changed
  after DFT outcomes are observed.
- Failed DFT jobs are counted as not-certified-stable in the conservative
  primary analysis after one standard rerun.

## Current Freeze Status

- Candidate-pool status: `{pool_status}`
- Candidate-pool gate: `{primary_status}`

If the candidate-pool gate is not `ready_for_selection`, this milestone must
not be described as a completed prospective DFT follow-up result.
"""
    closeout = f"""# Materials Prospective DFT Follow-Up Closeout

Evidence status: protocol freeze / input gate only.

This package freezes the prospective in-silico DFT follow-up design and writes
schema-complete candidate, selection, public-label exclusion, novelty, and DFT
job-manifest files. It does not contain new DFT results, does not claim
experimental synthesis, and does not promote a protocol-only positive result.

## Status Summary

{status.to_markdown(index=False)}

## Interpretation

The current package is ready to receive an unlabeled generated crystal pool and
public database crossmatch outputs. Until those inputs exist, `selection_frozen`
and `dft_job_manifest` remain empty by design.
"""
    (out_dir / "PROTOCOL.md").write_text(protocol_md, encoding="utf-8")
    (out_dir / "MATERIALS_PROSPECTIVE_DFT_FOLLOWUP_CLOSEOUT.md").write_text(closeout, encoding="utf-8")


def build_status(pool_info: dict, candidates: pd.DataFrame, selection: pd.DataFrame, jobs: pd.DataFrame) -> pd.DataFrame:
    candidate_ready = pool_info["status"] != "not_supplied" and int(pool_info["n_kept_rows"]) > 0
    rows = [
        {
            "item": "protocol",
            "status": "frozen",
            "completed_positive_result": False,
            "blocks_DFT_submission": False,
            "reason": "protocol and failure policy are frozen before DFT outcomes",
        },
        {
            "item": "candidate_pool",
            "status": "ready_for_selection" if candidate_ready else "blocked_missing_unlabeled_candidate_pool",
            "completed_positive_result": False,
            "blocks_DFT_submission": not candidate_ready,
            "reason": "requires unlabeled generated candidates with public-label exclusion and structure crossmatch",
        },
        {
            "item": "public_label_exclusion",
            "status": "pending_public_db_crossmatch" if candidate_ready else "pending_candidate_pool",
            "completed_positive_result": False,
            "blocks_DFT_submission": True,
            "reason": "must exclude public WBM/MP/OQMD/Alexandria/GNoME stability labels before DFT",
        },
        {
            "item": "selection_frozen",
            "status": "frozen" if not selection.empty else "not_started_no_candidates",
            "completed_positive_result": False,
            "blocks_DFT_submission": selection.empty,
            "reason": "selection arms require a valid PARC release and raw-only tail before job export",
        },
        {
            "item": "dft_job_manifest",
            "status": "ready" if not jobs.empty else "empty_until_selection_exists",
            "completed_positive_result": False,
            "blocks_DFT_submission": jobs.empty,
            "reason": "DFT jobs are exported only after nonempty frozen selection arms exist",
        },
        {
            "item": "dft_results",
            "status": "not_started",
            "completed_positive_result": False,
            "blocks_DFT_submission": False,
            "reason": "new DFT outcomes must be collected after protocol and selection freeze",
        },
    ]
    return pd.DataFrame(rows)


def write_readme_placeholders(out_dir: Path) -> None:
    for subdir, text in {
        "dft_inputs": "DFT input files are exported here only after `selection_frozen.csv` is nonempty.\n",
        "dft_outputs": "Raw DFT outputs are not part of the public-safe package unless explicitly sanitized.\n",
    }.items():
        target = out_dir / subdir
        target.mkdir(parents=True, exist_ok=True)
        (target / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", "--out-dir", dest="out_dir", default=str(DEFAULT_OUT))
    parser.add_argument("--candidate-pool", default=None)
    parser.add_argument("--score-column", default=None)
    parser.add_argument("--primary-model", default="ALIGNN-FF")
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--K", type=int, default=500)
    parser.add_argument("--block", default="composition-family")
    parser.add_argument("--n-release", type=int, default=40)
    parser.add_argument("--n-raw-only", type=int, default=40)
    parser.add_argument("--n-raw-matched", type=int, default=40)
    parser.add_argument("--min-analyzable-n", type=int, default=25)
    parser.add_argument("--dft-engine", default="VASP-or-equivalent-MP-compatible-engine")
    parser.add_argument("--protocol-date", default=DEFAULT_PROTOCOL_DATE)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_pool_path = Path(args.candidate_pool) if args.candidate_pool else None
    candidates, pool_info = normalize_candidate_pool(candidate_pool_path, args.score_column, args.primary_model)
    protocol = build_protocol(args, pool_info)
    selection, jobs = build_selection_tables(candidates, args)
    public_label = build_public_label_report(candidates)
    novelty = build_novelty_report(candidates)
    status = build_status(pool_info, candidates, selection, jobs)

    arm_plan = pd.DataFrame(
        [
            {
                "arm": "PARC-release",
                "target_n": args.n_release,
                "minimum_analyzable_n": args.min_analyzable_n,
                "selection_rule": protocol["arms"]["PARC_release"]["selection_rule"],
                "status": "pending_nonempty_selection",
            },
            {
                "arm": "raw-only rejected tail",
                "target_n": args.n_raw_only,
                "minimum_analyzable_n": args.min_analyzable_n,
                "selection_rule": protocol["arms"]["raw_only_rejected_tail"]["selection_rule"],
                "status": "pending_nonempty_selection",
            },
            {
                "arm": "raw top-R matched",
                "target_n": args.n_raw_matched,
                "minimum_analyzable_n": args.min_analyzable_n,
                "selection_rule": protocol["arms"]["raw_topR_matched"]["selection_rule"],
                "status": "pending_nonempty_selection",
            },
        ]
    )
    failure_policy = pd.DataFrame(
        [
            {
                "policy_item": "non_convergence",
                "rule": "one standard rerun; unresolved failures count as not-certified-stable in primary conservative analysis",
            },
            {
                "policy_item": "hull_unavailable",
                "rule": "count as not-certified-stable in primary conservative analysis and report separately",
            },
            {
                "policy_item": "completed_only_secondary",
                "rule": "report completed-only analysis only as secondary sensitivity",
            },
        ]
    )

    files: dict[str, str] = {
        "protocol.yaml": simple_yaml(protocol) + "\n",
    }
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")

    write_csv(candidates, out_dir / "candidate_universe_frozen.csv")
    write_csv(selection, out_dir / "selection_frozen.csv")
    write_csv(jobs, out_dir / "dft_job_manifest.csv")
    write_csv(public_label, out_dir / "PUBLIC_LABEL_EXCLUSION_REPORT.csv")
    write_csv(novelty, out_dir / "NOVELTY_CROSSMATCH_REPORT.csv")
    write_csv(status, out_dir / "table_dft_followup_freeze_status.csv")
    write_csv(arm_plan, out_dir / "table_dft_followup_arm_plan.csv")
    write_csv(failure_policy, out_dir / "table_dft_failure_policy.csv")
    write_readme_placeholders(out_dir)
    write_markdown(out_dir, protocol, status)

    command = "python scripts/build_materials_prospective_dft_followup_protocol.py"
    input_meta = {
        "candidate_pool_status": pool_info["status"],
        "candidate_pool_sha256": pool_info["input_sha256"],
        "protocol_hash": sha256_text(json.dumps(protocol, sort_keys=True)),
    }
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt" and not path.name.endswith(".provenance.json"):
            write_provenance(path, command, input_meta)
    write_manifest(out_dir)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
