from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], cwd=ROOT, check=True)


@pytest.fixture()
def prospective_pipeline(tmp_path: Path) -> Path:
    out = tmp_path / "a3"
    pool = tmp_path / "external_unlabeled_pool.csv"
    public_index = tmp_path / "public_label_index.csv"
    scores = tmp_path / "alignn_scores.csv"
    release = tmp_path / "parc_release.csv"

    pd.DataFrame(
        [
            {"candidate_id": f"cand-{i}", "formula": formula, "structure_ref": f"cand-{i}.cif", "structure_sha256": f"sha{i:02d}"}
            for i, formula in enumerate(["LiFeO2", "NaTiO2", "CaMnO3", "SrVO3", "BaZrO3", "MgSiO3", "KTaO3", "ZnSnO3"], start=1)
        ]
    ).to_csv(pool, index=False)
    pd.DataFrame([{"candidate_id": "cand-8", "formula": "ZnSnO3", "structure_sha256": "sha08"}]).to_csv(public_index, index=False)
    pd.DataFrame(
        [
            {"candidate_id": "cand-1", "frozen_model_score": 0.99},
            {"candidate_id": "cand-2", "frozen_model_score": 0.94},
            {"candidate_id": "cand-3", "frozen_model_score": 0.91},
            {"candidate_id": "cand-4", "frozen_model_score": 0.88},
            {"candidate_id": "cand-5", "frozen_model_score": 0.81},
            {"candidate_id": "cand-6", "frozen_model_score": 0.77},
            {"candidate_id": "cand-7", "frozen_model_score": 0.73},
        ]
    ).to_csv(scores, index=False)
    pd.DataFrame([{"candidate_id": "cand-1"}, {"candidate_id": "cand-3"}, {"candidate_id": "cand-4"}]).to_csv(release, index=False)

    run_script(
        "build_unlabeled_materials_candidate_pool.py",
        "--candidate-pool",
        str(pool),
        "--out",
        str(out),
        "--min-candidates",
        "5",
    )
    run_script(
        "filter_public_labeled_materials_candidates.py",
        "--raw-pool",
        str(out / "raw_generated_candidate_pool.csv"),
        "--public-label-index",
        str(public_index),
        "--out",
        str(out),
    )
    run_script(
        "score_unlabeled_pool_alignnff.py",
        "--candidates",
        str(out / "candidate_universe_frozen.csv"),
        "--scores",
        str(scores),
        "--out",
        str(out),
    )
    run_script(
        "select_prospective_dft_arms_from_pool.py",
        "--scores",
        str(out / "candidate_scores_alignnff.csv"),
        "--parc-release-file",
        str(release),
        "--out",
        str(out),
        "--K",
        "6",
        "--n-release",
        "2",
        "--n-raw-only",
        "2",
        "--n-raw-matched",
        "2",
        "--reserve-n",
        "1",
        "--min-analyzable-n",
        "2",
    )
    run_script("export_prospective_dft_jobs.py", "--selection", str(out / "selection_frozen.csv"), "--out", str(out))
    return out


def test_unlabeled_pool_has_structures(prospective_pipeline: Path) -> None:
    raw = pd.read_csv(prospective_pipeline / "raw_generated_candidate_pool.csv")
    status = pd.read_csv(prospective_pipeline / "table_unlabeled_pool_build_status.csv")
    assert len(raw) == 8
    assert raw["has_structure_ref"].astype(bool).all()
    assert raw["structure_ref"].str.endswith(".cif").all()
    assert status.iloc[0]["status"] == "ready_for_public_label_filter"


def test_public_label_exclusion_nonempty(prospective_pipeline: Path) -> None:
    candidates = pd.read_csv(prospective_pipeline / "candidate_universe_frozen.csv")
    status = pd.read_csv(prospective_pipeline / "table_public_label_filter_status.csv")
    assert not candidates.empty
    assert int(candidates["keep_for_followup"].astype(bool).sum()) == 7
    assert status.iloc[0]["status"] == "ready_for_alignnff_scoring"


def test_no_public_label_leakage(prospective_pipeline: Path) -> None:
    public = pd.read_csv(prospective_pipeline / "PUBLIC_LABEL_EXCLUSION_REPORT.csv")
    kept = public[public["keep_for_followup"].astype(bool)]
    assert not kept["WBM_label_available"].astype(bool).any()
    assert "cand-8" not in set(kept["candidate_id"])


def test_alignnff_scores_present(prospective_pipeline: Path) -> None:
    scored = pd.read_csv(prospective_pipeline / "candidate_scores_alignnff.csv")
    status = pd.read_csv(prospective_pipeline / "table_alignnff_score_status.csv")
    assert scored["score_status"].eq("score_present").sum() == 7
    assert scored["raw_rank"].min() == 1
    assert status.iloc[0]["status"] == "ready_for_PARC_selection"


def test_selection_frozen_nonempty(prospective_pipeline: Path) -> None:
    selection = pd.read_csv(prospective_pipeline / "selection_frozen.csv")
    status = pd.read_csv(prospective_pipeline / "table_selection_freeze_status.csv")
    assert not selection.empty
    assert {"PARC-release", "raw-only rejected tail", "raw top-R matched"}.issubset(set(selection["arm"]))
    assert status.iloc[0]["status"] == "selection_frozen_ready_for_DFT_export"


def test_dft_arms_balanced(prospective_pipeline: Path) -> None:
    jobs = pd.read_csv(prospective_pipeline / "dft_job_manifest.csv")
    status = pd.read_csv(prospective_pipeline / "table_dft_job_export_status.csv")
    counts = jobs.groupby("arm").size().to_dict()
    assert counts["PARC-release"] == 2
    assert counts["raw-only rejected tail"] == 2
    assert counts["raw top-R matched"] == 2
    assert status.iloc[0]["status"] == "DFT_manifest_ready"


def test_reserve_list_present(prospective_pipeline: Path) -> None:
    selection = pd.read_csv(prospective_pipeline / "selection_frozen.csv")
    reserves = selection[selection["primary_or_reserve"].eq("reserve")]
    assert {"PARC-release", "raw-only rejected tail"}.issubset(set(reserves["arm"]))
    assert (reserves["selected_for_dft"].astype(str).str.lower() == "false").all()
