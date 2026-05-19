from __future__ import annotations

import hashlib
import io
import json
import math
import os
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from ase.io import read
from alignn.ff.ff import AlignnAtomwiseCalculator, default_path

ROOT = Path.cwd()
A3 = ROOT / "outputs/milestones/mattergen_parc_prospective_dft_followup"
OUT = ROOT / "outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot"
ZIP = Path("/home/waas/paper_experiments/private/mattergen_v4_generation/pilot_5k_3gpu_merged/generated_crystals_cif.zip")
MODEL = Path("/root/.cache/atomgptlab/alignn_ff/v12.2.2024_dft_3d_307k")
MODEL_ZIP = Path("/root/v12.2.2024_dft_3d_307k.zip")
MODEL_NAME = "v12.2.2024_dft_3d_307k"
SCORE_RULE = "alignnff_score = -alignnff_energy_per_atom; diagnostic only, not formal A3 selection scorer"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def member_from_ref(ref: str) -> str:
    return str(ref).split("::")[-1]

def score_candidates(df: pd.DataFrame, label: str) -> pd.DataFrame:
    # DGL in this environment is CPU-only; thread caps make scoring fast and reproducible.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    import torch

    torch.set_num_threads(1)
    calc = AlignnAtomwiseCalculator(path=default_path(), device="cpu", include_stress=False)
    rows = []
    started = time.time()
    with zipfile.ZipFile(ZIP) as zf:
        for i, row in enumerate(df.itertuples(index=False), start=1):
            t0 = time.time()
            member = member_from_ref(row.structure_ref)
            out = {
                "candidate_id": row.candidate_id,
                "formula": getattr(row, "formula", ""),
                "structure_ref": row.structure_ref,
                "structure_sha256": row.structure_sha256,
                "source_population": label,
                "alignnff_model_name": MODEL_NAME,
                "alignnff_score_rule": SCORE_RULE,
                "selected_before_DFT_outcome": True,
                "outcome_available": False,
                "evidence_status": "completed_pre_outcome_scorer_diagnostic_not_DFT_evidence",
            }
            try:
                atoms = read(io.StringIO(zf.read(member).decode()), format="cif")
                atoms.calc = calc
                energy = float(atoms.get_potential_energy())
                forces = np.asarray(atoms.get_forces(), dtype=float)
                n_atoms = len(atoms)
                epa = energy / n_atoms if n_atoms else np.nan
                out.update(
                    {
                        "n_atoms": n_atoms,
                        "alignnff_energy_eV": energy,
                        "alignnff_energy_per_atom": epa,
                        "alignnff_score": -epa,
                        "alignnff_force_abs_max": float(np.abs(forces).max()) if forces.size else np.nan,
                        "score_status": "scored" if math.isfinite(energy) and np.isfinite(forces).all() else "nonfinite_output",
                        "score_seconds": time.time() - t0,
                    }
                )
            except Exception as exc:  # preserve all failures as rows; do not drop candidates.
                out.update(
                    {
                        "n_atoms": np.nan,
                        "alignnff_energy_eV": np.nan,
                        "alignnff_energy_per_atom": np.nan,
                        "alignnff_score": np.nan,
                        "alignnff_force_abs_max": np.nan,
                        "score_status": f"failed:{type(exc).__name__}",
                        "score_error": str(exc)[:500],
                        "score_seconds": time.time() - t0,
                    }
                )
            rows.append(out)
            if i == 1 or i % 100 == 0 or i == len(df):
                elapsed = time.time() - started
                print(f"[{label}] {i}/{len(df)} elapsed={elapsed:.1f}s", flush=True)
    return pd.DataFrame(rows)

def rank(df: pd.DataFrame, score_col: str, rank_col: str) -> pd.Series:
    return df[score_col].rank(ascending=False, method="min")

def write_manifest(path: Path) -> None:
    lines = []
    for p in sorted(path.rglob("*")):
        if p.is_file() and p.name != "MANIFEST_SHA256.txt":
            lines.append(f"{sha256(p)}  {p.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> None:
    ensure_clean_dir(OUT)
    consensus = pd.read_csv(A3 / "candidate_scores_consensus.csv")
    strict = pd.read_csv(A3 / "candidate_universe_strict_public_label_free.csv")
    release_manifest = pd.read_csv(A3 / "dft_job_manifest_v4_addendum.csv")
    selection = release_manifest[release_manifest["arm"].eq("PARC-release-full")].copy()
    tail = pd.read_csv(A3 / "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv")

    if not ZIP.exists():
        raise FileNotFoundError(ZIP)
    if not MODEL.exists():
        raise FileNotFoundError(MODEL)

    all_scores = score_candidates(consensus, "mattergen_4039_consensus_scored")
    all_scores.to_csv(OUT / "candidate_scores_alignnff_4039.csv", index=False)

    strict_scores = strict[["candidate_id"]].merge(all_scores, on="candidate_id", how="left")
    strict_scores.to_csv(OUT / "candidate_scores_alignnff_strict_public_label_free_2990.csv", index=False)

    merged = consensus.merge(
        all_scores[["candidate_id", "alignnff_score", "alignnff_energy_per_atom", "score_status"]],
        on="candidate_id",
        how="left",
        suffixes=("", "_alignnff"),
    )
    merged["chgnet_rank"] = rank(merged, "chgnet_score", "chgnet_rank")
    merged["mace_rank"] = rank(merged, "mace_score", "mace_rank")
    merged["consensus_rank"] = rank(merged, "consensus_score", "consensus_rank")
    merged["alignnff_rank"] = rank(merged, "alignnff_score", "alignnff_rank")

    rank_rows = []
    for a, b in [
        ("chgnet_score", "mace_score"),
        ("chgnet_score", "alignnff_score"),
        ("mace_score", "alignnff_score"),
        ("consensus_score", "alignnff_score"),
    ]:
        sub = merged[[a, b]].dropna()
        rank_rows.append(
            {
                "score_a": a,
                "score_b": b,
                "n": len(sub),
                "spearman": sub[a].corr(sub[b], method="spearman"),
                "pearson": sub[a].corr(sub[b], method="pearson"),
                "evidence_status": "completed_pre_outcome_scorer_diagnostic_not_DFT_evidence",
            }
        )
    pd.DataFrame(rank_rows).to_csv(OUT / "table_alignnff_rank_correlation.csv", index=False)

    overlap_rows = []
    score_cols = ["chgnet_score", "mace_score", "consensus_score", "alignnff_score"]
    for k in [25, 50, 75, 100, 300, 500]:
        top_sets = {c: set(merged.nlargest(k, c)["candidate_id"]) for c in score_cols}
        for i, a in enumerate(score_cols):
            for b in score_cols[i + 1 :]:
                inter = len(top_sets[a] & top_sets[b])
                union = len(top_sets[a] | top_sets[b])
                overlap_rows.append(
                    {
                        "K": k,
                        "score_a": a,
                        "score_b": b,
                        "intersection_n": inter,
                        "overlap_fraction_of_K": inter / k,
                        "jaccard": inter / union if union else np.nan,
                    }
                )
    pd.DataFrame(overlap_rows).to_csv(OUT / "table_alignnff_topk_overlap.csv", index=False)

    arm = pd.concat(
        [
            selection.assign(snapshot_arm="PARC-release-full"),
            tail.assign(snapshot_arm="raw_top100_extra_tail"),
        ],
        ignore_index=True,
        sort=False,
    )
    arm_scores = arm.merge(
        merged[
            [
                "candidate_id",
                "formula",
                "chgnet_score",
                "mace_score",
                "consensus_score",
                "alignnff_score",
                "alignnff_energy_per_atom",
                "chgnet_rank",
                "mace_rank",
                "consensus_rank",
                "alignnff_rank",
            ]
        ],
        on="candidate_id",
        how="left",
        suffixes=("_manifest", ""),
    )
    arm_scores.to_csv(OUT / "table_alignnff_release_tail_scores.csv", index=False)

    contrast = []
    for score in ["chgnet_score", "mace_score", "consensus_score", "alignnff_score", "alignnff_energy_per_atom"]:
        for arm_name, g in arm_scores.groupby("snapshot_arm"):
            contrast.append(
                {
                    "score": score,
                    "arm": arm_name,
                    "n": int(g[score].notna().sum()),
                    "mean": float(g[score].mean()),
                    "median": float(g[score].median()),
                    "min": float(g[score].min()),
                    "max": float(g[score].max()),
                }
            )
    contrast_df = pd.DataFrame(contrast)
    release = arm_scores[arm_scores["snapshot_arm"].eq("PARC-release-full")]
    extra = arm_scores[arm_scores["snapshot_arm"].eq("raw_top100_extra_tail")]
    delta_rows = []
    for score in ["chgnet_score", "mace_score", "consensus_score", "alignnff_score", "alignnff_energy_per_atom"]:
        delta_rows.append(
            {
                "score": score,
                "arm": "PARC-release-full_minus_raw_top100_extra_tail",
                "n_release": int(release[score].notna().sum()),
                "n_tail": int(extra[score].notna().sum()),
                "mean_delta": float(release[score].mean() - extra[score].mean()),
                "median_delta": float(release[score].median() - extra[score].median()),
            }
        )
    pd.concat([contrast_df, pd.DataFrame(delta_rows)], ignore_index=True, sort=False).to_csv(
        OUT / "table_alignnff_release_vs_tail_score_contrast.csv", index=False
    )

    status = pd.DataFrame(
        [
            {
                "item": "ALIGNN_FF_checkpoint_local_cache",
                "status": "completed",
                "completed_positive_result": False,
                "claim_scope": "pre_outcome_scorer_diagnostic_not_DFT_evidence",
            },
            {
                "item": "candidate_scores_alignnff_4039",
                "status": "completed" if all_scores["score_status"].eq("scored").all() else "completed_with_failures",
                "n": len(all_scores),
                "completed_positive_result": False,
                "claim_scope": "pre_outcome_scorer_diagnostic_not_DFT_evidence",
            },
            {
                "item": "candidate_scores_alignnff_strict_public_label_free_2990",
                "status": "completed" if strict_scores["score_status"].eq("scored").all() else "completed_with_failures",
                "n": len(strict_scores),
                "completed_positive_result": False,
                "claim_scope": "pre_outcome_scorer_diagnostic_not_DFT_evidence",
            },
            {
                "item": "PARC_release_full_and_raw_top100_extra_tail_summary",
                "status": "completed",
                "n_parc_release_full": int((arm_scores["snapshot_arm"] == "PARC-release-full").sum()),
                "n_raw_top100_extra_tail": int((arm_scores["snapshot_arm"] == "raw_top100_extra_tail").sum()),
                "completed_positive_result": False,
                "claim_scope": "pre_outcome_scorer_diagnostic_not_DFT_evidence",
            },
        ]
    )
    status.to_csv(OUT / "table_alignnff_preoutcome_score_status.csv", index=False)

    provenance = {
        "status": "completed_pre_outcome_scorer_diagnostic_not_DFT_evidence",
        "does_not_modify": ["selection_frozen_v4.csv", "dft_job_manifest_v4.csv", "dft_job_manifest_v4_addendum.csv", "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv", "A3_DFT_RUN_PACKAGE/"],
        "alignn_package": "alignn==2026.4.2",
        "alignnff_model_name": MODEL_NAME,
        "checkpoint_dir": MODEL_NAME,
        "checkpoint_zip_sha256": sha256(MODEL_ZIP) if MODEL_ZIP.exists() else "not_recorded",
        "best_model_sha256": sha256(MODEL / "best_model.pt"),
        "config_sha256": sha256(MODEL / "config.json"),
        "source_zip_sha256": sha256(ZIP),
        "score_rule": SCORE_RULE,
        "dgl_device_note": "DGL is CPU-only in this environment; scoring used device=cpu and thread caps.",
        "no_dft_outcomes_used": True,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    (OUT / "A3_ALIGNNFF_PREOUTCOME_SCORING_SNAPSHOT.md").write_text(
        """# A3-v4 ALIGNN-FF Pre-Outcome Scoring Snapshot\n\nStatus: completed pre-outcome scorer diagnostic, not DFT evidence.\n\nThis milestone records a local ALIGNN-FF scoring snapshot after the official checkpoint became available locally. It does not modify `selection_frozen_v4.csv`, any DFT manifest, or the A3 DFT run package. Scores are used only to compare CHGNet, MACE-MP and ALIGNN-FF ranking behavior before DFT outcomes are analyzed.\n\n`alignnff_score` is defined as `-energy_per_atom` from the ALIGNN-FF force-field output. This is a diagnostic score, not the frozen scorer used to construct the already frozen A3-v4 release. No prospective materials discovery claim or DFT utility claim is made here.\n""",
        encoding="utf-8",
    )
    write_manifest(OUT)

if __name__ == "__main__":
    main()
