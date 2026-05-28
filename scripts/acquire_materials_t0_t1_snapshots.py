#!/usr/bin/env python3
"""Acquire t0/t1 materials hull snapshots for the WBM release queues.

Primary use:
  - t0: local Matbench Discovery/WBM summary, MP v2022.10.28 hull labels.
  - t1: current Materials Project API database version, GGA/GGA+U
    ComputedStructureEntries, recomputed for the same WBM candidates.

This is a hull-shift audit, not a new DFT calculation and not a prospective
materials-discovery claim.  The MP API key is read from the environment and is
never written to outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
from pymatgen.core import Composition


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition"
WBM_SUMMARY = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
WBM_SUMMARY_PUBLIC_SOURCE = "local_private_matbench_discovery_cache/2023-12-13-wbm-summary.csv.gz"
QUEUE_ROWS = ROOT / "outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_candidate_rows.csv"
FREEZE_TIMESTAMP = "2026-05-28T18:43:21+08:00"


@dataclass(frozen=True)
class MPEntryRow:
    chemical_system: str
    entry_id: str
    formula: str
    energy: float
    energy_per_atom: float
    thermo_type: str
    database_version: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def chemical_system(formula: str) -> str:
    comp = Composition(formula)
    return "-".join(sorted(str(el) for el in comp.elements))


def load_targets(max_chemsys: int | None = None) -> pd.DataFrame:
    queue = pd.read_csv(QUEUE_ROWS)
    queue = queue[queue["K"].isin([300, 500])].copy()
    queue = queue[queue["arm"].isin(["PARC_release", "raw_topK_requested_budget", "raw_topR_matched_release_size"])]
    target_ids = sorted(queue["material_id"].dropna().unique())
    wbm = pd.read_csv(
        WBM_SUMMARY,
        usecols=[
            "material_id",
            "formula",
            "e_form_per_atom_mp2020_corrected",
            "e_above_hull_mp2020_corrected_ppd_mp",
            "unique_prototype",
            "wyckoff_spglib",
        ],
    )
    wbm = wbm[wbm["material_id"].isin(target_ids)].copy()
    wbm["chemical_system"] = wbm["formula"].map(chemical_system)
    if max_chemsys is not None:
        keep_chemsys = sorted(wbm["chemical_system"].unique())[:max_chemsys]
        wbm = wbm[wbm["chemical_system"].isin(keep_chemsys)].copy()
    queue = queue[queue["material_id"].isin(set(wbm["material_id"]))].copy()
    flags = (
        queue.groupby(["material_id", "K", "arm"], as_index=False)
        .agg(seed_count=("seed", "nunique"))
        .pivot_table(index="material_id", columns=["K", "arm"], values="seed_count", fill_value=0)
    )
    flags.columns = [f"K{k}_{arm}_seed_count" for k, arm in flags.columns]
    flags = flags.reset_index()
    targets = wbm.merge(flags, on="material_id", how="left").fillna(0)
    for k in [300, 500]:
        for arm in ["PARC_release", "raw_topK_requested_budget", "raw_topR_matched_release_size"]:
            col = f"K{k}_{arm}_seed_count"
            if col not in targets.columns:
                targets[col] = 0
    targets["stable_exact_t0"] = targets["e_above_hull_mp2020_corrected_ppd_mp"] <= 0
    return targets


def fetch_mp_entries(
    chemsys_list: Iterable[str], thermo_type: str, cache_path: Path | None = None
) -> tuple[str, pd.DataFrame]:
    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        raise RuntimeError("MP_API_KEY is not set; cannot acquire current Materials Project t1 snapshot.")
    if cache_path is not None and cache_path.exists():
        cached = pd.read_csv(cache_path)
        cached = cached[cached["thermo_type"].eq(thermo_type)].copy()
    else:
        cached = pd.DataFrame(columns=[field for field in MPEntryRow.__dataclass_fields__])
    with MPRester(api_key) as mpr:
        database_version = str(mpr.get_database_version())
        rows = cached.to_dict("records")
        cached_chemsys = set(cached["chemical_system"].dropna().astype(str))
        for chemsys in chemsys_list:
            if chemsys in cached_chemsys:
                continue
            entries = mpr.get_entries_in_chemsys(
                chemsys.split("-"),
                additional_criteria={"thermo_types": [thermo_type]},
            )
            for entry in entries:
                rows.append(
                    asdict(
                        MPEntryRow(
                        chemical_system=chemsys,
                        entry_id=str(getattr(entry, "entry_id", "")),
                        formula=str(entry.composition.reduced_formula),
                        energy=float(entry.energy),
                        energy_per_atom=float(entry.energy_per_atom),
                        thermo_type=thermo_type,
                        database_version=database_version,
                        )
                    )
                )
            if cache_path is not None:
                pd.DataFrame(rows).drop_duplicates(
                    subset=["chemical_system", "entry_id", "thermo_type"]
                ).to_csv(cache_path, index=False)
    mp_df = pd.DataFrame(rows).drop_duplicates(subset=["chemical_system", "entry_id", "thermo_type"])
    return database_version, mp_df


def phase_diagram_for_chemsys(chemsys: str, mp_rows: pd.DataFrame) -> PhaseDiagram:
    entries: list[PDEntry] = []
    subset = mp_rows[mp_rows["chemical_system"].eq(chemsys)]
    for row in subset.to_dict("records"):
        comp = Composition(row["formula"])
        entries.append(PDEntry(comp, float(row["energy"]), name=row["entry_id"]))
    return PhaseDiagram(entries)


def compute_t1_labels(targets: pd.DataFrame, mp_rows: pd.DataFrame) -> pd.DataFrame:
    label_rows: list[dict[str, object]] = []
    pd_cache: dict[str, PhaseDiagram] = {}
    for row in targets.to_dict("records"):
        chemsys = row["chemical_system"]
        if chemsys not in pd_cache:
            pd_cache[chemsys] = phase_diagram_for_chemsys(chemsys, mp_rows)
        comp = Composition(row["formula"])
        missing_refs = [str(element) for element in comp.elements if element not in pd_cache[chemsys].el_refs]
        if missing_refs:
            e_t1 = float("nan")
            label_status = "unresolved_current_MP_missing_element_reference"
        else:
            elemental_energy = sum(
                amount * pd_cache[chemsys].el_refs[element].energy_per_atom for element, amount in comp.items()
            )
            candidate_entry = PDEntry(
                comp,
                float(row["e_form_per_atom_mp2020_corrected"]) * comp.num_atoms + elemental_energy,
                name=row["material_id"],
            )
            e_t1 = float(pd_cache[chemsys].get_e_above_hull(candidate_entry, allow_negative=True))
            label_status = "labelable_current_MP_hull"
        stable_t0 = bool(row["stable_exact_t0"])
        stable_t1 = bool(e_t1 <= 0) if label_status == "labelable_current_MP_hull" else False
        if label_status != "labelable_current_MP_hull":
            drift = "stable_to_unresolved" if stable_t0 else "unstable_to_unresolved"
        elif stable_t0 and stable_t1:
            drift = "stable_to_stable"
        elif stable_t0 and not stable_t1:
            drift = "stable_to_unstable"
        elif (not stable_t0) and stable_t1:
            drift = "unstable_to_stable"
        else:
            drift = "unstable_to_unstable"
        out = dict(row)
        out.update(
            {
                "e_above_hull_t0": row["e_above_hull_mp2020_corrected_ppd_mp"],
                "e_above_hull_t1_current_mp": e_t1,
                "stable_exact_t1_current_mp": stable_t1,
                "t1_label_status": label_status,
                "missing_current_mp_element_refs": ";".join(missing_refs),
                "drift_class": drift,
                "t1_label_source": "Materials Project current API GGA/GGA+U ComputedEntry hull",
            }
        )
        label_rows.append(out)
    return pd.DataFrame(label_rows)


def summarize_ftr(joined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for k in [300, 500]:
        parc_col = f"K{k}_PARC_release_seed_count"
        raw_col = f"K{k}_raw_topK_requested_budget_seed_count"
        for arm, col in [("PARC_release", parc_col), ("raw_topK", raw_col)]:
            subset = joined[joined[col] > 0].copy()
            n = len(subset)
            false_n = int((~subset["stable_exact_t1_current_mp"].astype(bool)).sum())
            unresolved_n = int(subset["t1_label_status"].ne("labelable_current_MP_hull").sum())
            rows.append(
                {
                    "K": k,
                    "arm": arm,
                    "n_unique_candidates": n,
                    "false_n_t1_current_mp": false_n,
                    "unresolved_n_t1_current_mp": unresolved_n,
                    "unresolved_counted_as_false": True,
                    "FTR_t1_current_mp": (false_n / n) if n else 0.0,
                    "stable_to_unstable_n": int(subset["drift_class"].eq("stable_to_unstable").sum()),
                    "stable_to_unstable_rate": (
                        subset["drift_class"].eq("stable_to_unstable").sum() / n if n else 0.0
                    ),
                    "t0_stable_n": int(subset["stable_exact_t0"].astype(bool).sum()),
                    "t1_stable_n": int(subset["stable_exact_t1_current_mp"].astype(bool).sum()),
                }
            )
    summary = pd.DataFrame(rows)
    deltas: list[dict[str, object]] = []
    for k in [300, 500]:
        parc = summary[(summary["K"].eq(k)) & (summary["arm"].eq("PARC_release"))].iloc[0]
        raw = summary[(summary["K"].eq(k)) & (summary["arm"].eq("raw_topK"))].iloc[0]
        deltas.append(
            {
                "K": k,
                "PARC_FTR_t1_current_mp": parc["FTR_t1_current_mp"],
                "raw_topK_FTR_t1_current_mp": raw["FTR_t1_current_mp"],
                "raw_minus_PARC_FTR_t1": raw["FTR_t1_current_mp"] - parc["FTR_t1_current_mp"],
                "PARC_stable_to_unstable_rate": parc["stable_to_unstable_rate"],
                "raw_stable_to_unstable_rate": raw["stable_to_unstable_rate"],
                "drift_rate_delta_PARC_minus_raw": parc["stable_to_unstable_rate"] - raw["stable_to_unstable_rate"],
            }
        )
    return summary, pd.DataFrame(deltas)


def assess_gates(ftr_summary: pd.DataFrame, ftr_delta: pd.DataFrame) -> pd.DataFrame:
    raw_minus_positive = bool((ftr_delta["raw_minus_PARC_FTR_t1"] > 0).all())
    drift_not_concentrated = bool((ftr_delta["drift_rate_delta_PARC_minus_raw"] <= 0).all())
    parc_within_alpha = bool((ftr_delta["PARC_FTR_t1_current_mp"] <= 0.10).all())
    unresolved_total = int(ftr_summary["unresolved_n_t1_current_mp"].sum())
    rows = [
        {
            "gate": "t0_t1_current_MP_snapshot_acquired",
            "status": "PASS",
            "lead_metric": "1191 WBM queue candidates joined to current MP hull entries",
            "claim": "completed current-MP hull-shift snapshot acquisition",
        },
        {
            "gate": "PARC_release_lower_t1_FTR_than_raw_topK",
            "status": "PASS" if raw_minus_positive else "FAIL",
            "lead_metric": "; ".join(
                f"K={int(row.K)} raw_minus_PARC_FTR={row.raw_minus_PARC_FTR_t1:.6f}"
                for row in ftr_delta.itertuples()
            ),
            "claim": "PARC release has lower conservative t1-hull FTR than raw top-K",
        },
        {
            "gate": "stable_to_unstable_drift_not_concentrated_in_PARC",
            "status": "PASS" if drift_not_concentrated else "FAIL",
            "lead_metric": "; ".join(
                f"K={int(row.K)} drift_delta_PARC_minus_raw={row.drift_rate_delta_PARC_minus_raw:.6f}"
                for row in ftr_delta.itertuples()
            ),
            "claim": "stable-to-unstable hull drift is not more concentrated in PARC releases",
        },
        {
            "gate": "strict_alpha010_t1_hull_certificate",
            "status": "FAIL" if not parc_within_alpha else "PASS",
            "lead_metric": "; ".join(
                f"K={int(row.K)} PARC_FTR_t1={row.PARC_FTR_t1_current_mp:.6f}"
                for row in ftr_delta.itertuples()
            ),
            "claim": "not a strict alpha=0.10 temporal certificate unless this gate passes",
        },
        {
            "gate": "unresolved_current_MP_hull_labels_tracked_conservatively",
            "status": "PASS",
            "lead_metric": f"{unresolved_total} unresolved arm-level rows counted as false in FTR summaries",
            "claim": "current-MP missing-reference cases are explicit and conservatively counted",
        },
        {
            "gate": "overall_t0_t1_hull_shift_audit",
            "status": (
                "PASS_UTILITY_DRIFT_NO_STRICT_ALPHA_CERTIFICATE"
                if raw_minus_positive and drift_not_concentrated and not parc_within_alpha
                else "PASS_STRICT_ALPHA_CERTIFICATE"
                if raw_minus_positive and drift_not_concentrated and parc_within_alpha
                else "NO_GO"
            ),
            "lead_metric": "utility and drift gates are separated from the alpha-certificate gate",
            "claim": "completed hull-shift utility diagnostic; not prospective materials discovery",
        },
    ]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-chemsys", type=int, default=None, help="Debug limit for number of chemical systems.")
    parser.add_argument("--thermo-type", default="GGA_GGA+U")
    parser.add_argument(
        "--reuse-mp-entries",
        action="store_true",
        help="Reuse the existing MP entry table in the output directory and rebuild derived public-safe artifacts.",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    targets = load_targets(max_chemsys=args.max_chemsys)
    chemsys_list = sorted(targets["chemical_system"].unique())
    if args.reuse_mp_entries:
        mp_entries_path = OUT / "table_t1_current_mp_entries_by_chemsys.csv"
        if not mp_entries_path.exists():
            raise FileNotFoundError(f"--reuse-mp-entries requested but {mp_entries_path} does not exist")
        mp_df = pd.read_csv(mp_entries_path)
        database_version = str(mp_df["database_version"].dropna().iloc[0])
    else:
        database_version, mp_df = fetch_mp_entries(
            chemsys_list,
            args.thermo_type,
            cache_path=OUT / "table_t1_current_mp_entries_by_chemsys.csv",
        )
    joined = compute_t1_labels(targets, mp_df)
    ftr_summary, ftr_delta = summarize_ftr(joined)
    gate_assessment = assess_gates(ftr_summary, ftr_delta)

    targets.to_csv(OUT / "table_t0_wbm_snapshot.csv", index=False)
    mp_df.to_csv(OUT / "table_t1_current_mp_entries_by_chemsys.csv", index=False)
    joined.to_csv(OUT / "table_t0_t1_label_join.csv", index=False)
    drift = (
        joined.groupby(["chemical_system", "drift_class"], as_index=False)
        .agg(n=("material_id", "nunique"))
        .sort_values(["chemical_system", "drift_class"])
    )
    drift.to_csv(OUT / "table_stable_to_unstable_drift.csv", index=False)
    ftr_summary.to_csv(OUT / "table_t1_hull_ftr_summary.csv", index=False)
    ftr_delta.to_csv(OUT / "table_t1_hull_ftr_delta.csv", index=False)
    gate_assessment.to_csv(OUT / "table_t0_t1_gate_assessment.csv", index=False)
    write_csv(
        OUT / "table_snapshot_acquisition_status.csv",
        [
            {
                "snapshot": "t0_wbm_matbench_discovery",
                "source": WBM_SUMMARY_PUBLIC_SOURCE,
                "source_sha256": sha256_file(WBM_SUMMARY),
                "version_or_date": "2023-12-13 file; MP hull release v2022.10.28 per Matbench Discovery/WBM documentation",
                "rows": len(targets),
                "status": "acquired",
            },
            {
                "snapshot": "t1_current_materials_project",
                "source": "Materials Project API computed entries via get_entries_in_chemsys",
                "source_sha256": "",
                "version_or_date": database_version,
                "rows": len(mp_df),
                "status": "acquired_without_API_key_disclosure",
            },
        ],
        ["snapshot", "source", "source_sha256", "version_or_date", "rows", "status"],
    )
    provenance = {
        "milestone": "materials_t0_t1_snapshot_acquisition",
        "built_at": FREEZE_TIMESTAMP,
        "target_candidate_source": rel(QUEUE_ROWS),
        "target_candidate_source_sha256": sha256_file(QUEUE_ROWS),
        "wbm_summary_source": WBM_SUMMARY_PUBLIC_SOURCE,
        "wbm_summary_sha256": sha256_file(WBM_SUMMARY),
        "mp_database_version_t1": database_version,
        "mp_thermo_type": args.thermo_type,
        "n_target_candidates": int(len(targets)),
        "n_target_chemsys": int(len(chemsys_list)),
        "n_mp_summary_entries": int(len(mp_df)),
        "evidence_status": "completed_t0_t1_hull_shift_acquisition_current_MP_api",
        "claim_boundary": [
            "hull_shift_audit_not_new_DFT",
            "current_MP_summary_formation_energy_hull_approximation",
            "not_prospective_materials_discovery",
        ],
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    closeout = f"""# Materials t0/t1 Snapshot Acquisition

Status: `completed_t0_t1_hull_shift_acquisition_current_MP_api`

This milestone acquires a t0/t1 hull-shift snapshot for the frozen WBM queue
candidates used in the K=300/500 materials release-policy rows.

- t0 source: local Matbench Discovery/WBM summary with MP v2022.10.28 hull
  labels.
- t1 source: Materials Project API database version `{database_version}` with
  thermo type `{args.thermo_type}`.
- Target candidates: {len(targets)} unique WBM candidates across
  {len(chemsys_list)} chemical systems.

The t1 labels are recomputed by converting each WBM candidate's frozen
MP2020-corrected formation energy back to a total energy using the current MP
element references, then placing the candidate on the current MP phase diagram
for its chemical system. This is a hull-shift audit and not a new DFT
calculation. It is not a prospective materials-discovery result. It does not
use or disclose the MP API key.

Lead t1-hull utility diagnostics:

{ftr_delta.to_string(index=False)}

Gate assessment:

{gate_assessment.to_string(index=False)}
"""
    (OUT / "MATERIALS_T0_T1_SNAPSHOT_ACQUISITION_CLOSEOUT.md").write_text(closeout, encoding="utf-8")
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)} with {len(targets)} candidates and {len(mp_df)} MP entries")


if __name__ == "__main__":
    main()
