#!/usr/bin/env python3
"""Shared helpers for the prospective materials DFT follow-up pipeline.

The helpers in this module deliberately avoid generating scientific evidence.
They normalize user-supplied candidate, score, public-label and release files
into a public-safe milestone layout, and otherwise write explicit blocked
status tables.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from build_materials_prospective_dft_followup_protocol import (
    CANDIDATE_COLUMNS,
    DEFAULT_OUT,
    DFT_JOB_COLUMNS,
    LABEL_COLUMNS,
    PUBLIC_LABEL_COLUMNS,
    SELECTION_COLUMNS,
    anonymous_formula,
    parse_elements,
    sha256_file,
    write_csv,
    write_manifest,
    write_provenance,
)


RAW_POOL_COLUMNS = CANDIDATE_COLUMNS + [
    "structure_ref",
    "structure_sha256",
    "has_structure_ref",
    "raw_pool_rank",
    "generation_status",
]

SCORE_COLUMNS = CANDIDATE_COLUMNS + [
    "structure_ref",
    "structure_sha256",
    "raw_rank",
    "score_status",
]

SELECTION_EXTENDED_COLUMNS = SELECTION_COLUMNS + [
    "primary_or_reserve",
    "source_rank",
    "frozen_model_score",
    "structure_ref",
    "structure_sha256",
]


def safe_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "t"}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def input_hash(path: Path | None) -> str:
    if path is None:
        return ""
    return sha256_file(path)


def file_sha_if_available(path_text: object) -> str:
    text = str(path_text).strip()
    if not text:
        return ""
    path = Path(text)
    if path.exists() and path.is_file():
        return sha256_file(path)
    return ""


def sanitize_structure_ref(row: pd.Series) -> str:
    for col in ["structure_ref", "structure_id", "cif_id", "poscar_id"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    for col in ["structure_path", "cif_path", "poscar_path", "structure_file"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return Path(str(row[col]).strip()).name
    return ""


def structure_sha(row: pd.Series) -> str:
    for col in ["structure_sha256", "cif_sha256", "poscar_sha256"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    for col in ["structure_path", "cif_path", "poscar_path", "structure_file"]:
        if col in row:
            found = file_sha_if_available(row[col])
            if found:
                return found
    return ""


def candidate_id_for(row: pd.Series, index: int) -> str:
    for col in ["candidate_id", "material_id", "structure_id"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    formula = str(row.get("formula", "")).strip()
    digest = hashlib.sha256(f"{index}:{formula}:{sanitize_structure_ref(row)}".encode("utf-8")).hexdigest()[:12]
    return f"prospective-candidate-{digest}"


def first_present(row: pd.Series, names: list[str], default: object = "") -> object:
    for name in names:
        if name in row and pd.notna(row[name]) and str(row[name]).strip():
            return row[name]
    return default


def normalize_raw_pool(raw: pd.DataFrame, primary_model: str, score_column: str | None = None) -> pd.DataFrame:
    rows: list[dict] = []
    duplicated_candidates = raw.duplicated(subset=[c for c in ["candidate_id"] if c in raw.columns], keep=False) if "candidate_id" in raw.columns else pd.Series(False, index=raw.index)
    for idx, row in raw.iterrows():
        formula = str(first_present(row, ["formula", "reduced_formula"], "")).strip()
        elements = "|".join(parse_elements(formula))
        structure_ref = sanitize_structure_ref(row)
        structure_digest = structure_sha(row)
        chosen_score = score_column
        if chosen_score is None:
            for col in ["frozen_model_score", "alignn_ff_score", "score", "model_score", "predicted_score", "stability_score"]:
                if col in raw.columns:
                    chosen_score = col
                    break
        label_present = any(col in raw.columns and pd.notna(row[col]) for col in LABEL_COLUMNS)
        duplicate_status = "duplicate_candidate_id" if bool(duplicated_candidates.loc[idx]) else "unique_candidate_id"
        has_structure = bool(structure_ref or structure_digest)
        keep = (not label_present) and duplicate_status == "unique_candidate_id" and has_structure
        exclusion_reasons = []
        if label_present:
            exclusion_reasons.append("public_label_column_present")
        if duplicate_status != "unique_candidate_id":
            exclusion_reasons.append("duplicate_candidate_id")
        if not has_structure:
            exclusion_reasons.append("missing_structure_ref")
        rows.append(
            {
                "candidate_id": candidate_id_for(row, idx),
                "formula": formula,
                "reduced_formula": str(first_present(row, ["reduced_formula"], formula)),
                "elements": elements,
                "anonymous_formula": str(first_present(row, ["anonymous_formula"], anonymous_formula(formula))),
                "n_sites": first_present(row, ["n_sites", "num_sites"], ""),
                "space_group": first_present(row, ["space_group", "spacegroup", "sg"], ""),
                "source_prototype_id": first_present(row, ["source_prototype_id", "prototype_id", "wyckoff_spglib"], ""),
                "model_family": primary_model,
                "frozen_model_score": row[chosen_score] if chosen_score and chosen_score in raw.columns else "",
                "block_id": str(first_present(row, ["block_id"], "")) or f"{anonymous_formula(formula)}::{ '-'.join(sorted(parse_elements(formula))) }",
                "public_label_status": "excluded_public_label_column_present" if label_present else "pending_public_label_index_crossmatch",
                "novelty_status": "pending_public_structure_crossmatch",
                "duplicate_status": duplicate_status,
                "keep_for_followup": keep,
                "exclusion_reason": "" if keep else "|".join(exclusion_reasons),
                "evidence_status": "candidate_pool_frozen_pending_public_crossmatch",
                "structure_ref": structure_ref,
                "structure_sha256": structure_digest,
                "has_structure_ref": has_structure,
                "raw_pool_rank": idx + 1,
                "generation_status": "external_unlabeled_pool_normalized",
            }
        )
    out = pd.DataFrame(rows, columns=RAW_POOL_COLUMNS)
    return out


def status_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def write_with_provenance(path: Path, df: pd.DataFrame, command: str, inputs: dict) -> None:
    write_csv(df, path)
    write_provenance(path, command, inputs)


def refresh_manifest(out_dir: Path) -> None:
    write_manifest(out_dir)


def coerce_score(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def sort_by_score(df: pd.DataFrame, score_col: str = "frozen_model_score") -> pd.DataFrame:
    out = df.copy()
    out["_score_numeric"] = coerce_score(out[score_col])
    out = out.sort_values(["_score_numeric", "candidate_id"], ascending=[False, True], na_position="last")
    return out.drop(columns=["_score_numeric"])


def public_safe_inputs(**kwargs: object) -> dict:
    safe: dict[str, object] = {}
    for key, value in kwargs.items():
        if isinstance(value, Path):
            safe[f"{key}_sha256"] = input_hash(value)
            safe[f"{key}_name"] = value.name
        else:
            safe[key] = value
    return safe


def selected_primary(selection: pd.DataFrame) -> pd.DataFrame:
    if selection.empty:
        return empty_frame(SELECTION_EXTENDED_COLUMNS)
    return selection[
        selection["selected_for_dft"].map(safe_bool)
        & selection.get("primary_or_reserve", pd.Series(["primary"] * len(selection), index=selection.index)).eq("primary")
    ].copy()


def write_empty_blocked(out_dir: Path, filename: str, columns: list[str], command: str, reason: str, inputs: dict) -> None:
    path = out_dir / filename
    write_with_provenance(path, empty_frame(columns), command, inputs)
    status_name = filename.replace(".csv", "_status.csv")
    write_with_provenance(
        out_dir / status_name,
        status_frame(
            [
                {
                    "artifact": filename,
                    "status": "blocked",
                    "completed_positive_result": False,
                    "blocks_DFT_submission": True,
                    "reason": reason,
                }
            ]
        ),
        command,
        inputs,
    )
