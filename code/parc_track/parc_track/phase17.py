from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
RELIABILITY_DIR = DATA_ROOT / "outputs/milestones/reliability_fortress"
PAPER_DIR = RELIABILITY_DIR / "paper_tables"
REVIEW_DIR = RELIABILITY_DIR / "reviewer_closeout"
AUDIT_REVIEW_DIR = RELIABILITY_DIR / "audit_review"
LEGACY_DIR = RELIABILITY_DIR.parent / "legacy_core_results"

PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "gray": "#4D4D4D",
}


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=DATA_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def _rel(path: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(DATA_ROOT).as_posix()
    except Exception:
        return Path(path).as_posix()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path = ensure_data_output(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _write_provenance(path: Path, sources: list[Path], started: float, notes: str = "") -> None:
    existing_sources = [source for source in sources if source.exists()]
    _write_json(
        path.with_suffix(path.suffix + ".provenance.json"),
        {
            "table": path.name,
            "repo_commit": _git_commit(),
            "command": "python -m parc_track.cli phase17 reviewer-closeout",
            "runtime_sec": round(time.time() - started, 6),
            "environment": "python",
            "random_seed": "fixed_per_row",
            "sources": [{"path": _rel(source), "sha256": _sha256(source)} for source in existing_sources],
            "output_sha256": _sha256(path),
            "notes": notes,
        },
    )


def _write_csv(df: pd.DataFrame, path: Path, sources: list[Path], started: float, notes: str = "") -> Path:
    path = ensure_data_output(path)
    df.to_csv(path, index=False)
    _write_provenance(path, sources, started, notes)
    return path


def _set_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _save_figure(fig: plt.Figure, path: Path, sources: list[Path], started: float, notes: str = "") -> Path:
    path = ensure_data_output(path)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    _write_provenance(path, sources, started, notes)
    return path


def _uniform_scs_release(e_values: np.ndarray, alpha: float, m: int) -> np.ndarray:
    order = np.argsort(-e_values)
    sorted_e = e_values[order]
    best_k = 0
    for k in range(1, min(m, len(sorted_e)) + 1):
        tau = m / (alpha * k)
        if sorted_e[k - 1] >= tau:
            best_k = k
    if best_k == 0:
        return np.array([], dtype=int)
    return order[:best_k]


def _build_actual_ftr_validation(started: float) -> list[Path]:
    outputs: list[Path] = []
    rows: list[dict[str, Any]] = []
    m = 150
    n_trials = 100
    for alpha in (0.05, 0.10, 0.20):
        for seed in range(n_trials):
            rng = np.random.default_rng(20260513 + seed + int(alpha * 1000))
            # Oracle-known nulls. Null e-values have mean below one; alternatives have high evidence.
            is_false = rng.random(m) < 0.08
            null_e = rng.exponential(scale=0.8, size=m)
            alt_e = rng.lognormal(mean=3.65, sigma=0.28, size=m)
            e_values = np.where(is_false, null_e, alt_e)
            released_idx = _uniform_scs_release(e_values, alpha=alpha, m=m)
            released = int(len(released_idx))
            false_released = int(is_false[released_idx].sum()) if released else 0
            actual_ftr = false_released / released if released else 0.0
            rows.append(
                {
                    "validation_block": "controlled_simulation_known_ground_truth",
                    "dataset": "synthetic_oracle_paths",
                    "generator": "oracle_one_sided_score_model",
                    "certified_risk_level_alpha": alpha,
                    "seed": seed,
                    "M": m,
                    "released": released,
                    "false_released": false_released,
                    "actual_FTR": actual_ftr,
                    "actual_FTR_lower": actual_ftr,
                    "actual_FTR_upper": actual_ftr,
                    "actual_FTR_le_alpha": actual_ftr <= alpha + 1e-12,
                    "ground_truth_source": "simulated_complete_true_null_labels",
                    "paper_use": "main_empirical_validity_sanity_check",
                    "notes": "Controlled simulation with known H0; not a replacement for dense real-video annotation.",
                }
            )

    # Real-data anchor: released unsupported paths with human audit, plus official matches treated as true.
    real_sources = [
        LEGACY_DIR / "phase2h_first_real_nonempty/table_real_first_nonempty.csv",
        LEGACY_DIR / "core_results/table_m_sweep_parc_full_with_audit.csv",
        PAPER_DIR / "table_main_raw_vs_parc.csv",
    ]
    first = _read_csv(real_sources[0])
    if not first.empty:
        r = first.iloc[0]
        released = int(_num(r.get("released")))
        false = int(_num(r.get("unsupported_false")))
        uncertain = int(_num(r.get("unsupported_uncertain")))
        actual_lower = false / released if released else 0.0
        actual_upper = (false + uncertain) / released if released else 0.0
        rows.append(
            {
                "validation_block": "real_data_release_set_audit_anchor",
                "dataset": "OVT-B",
                "generator": "GroundingDINO + tracker",
                "certified_risk_level_alpha": _num(r.get("alpha1"), 0.1),
                "seed": "milestone_phase2h",
                "M": int(_num(r.get("candidate_budget_M"), 150)),
                "released": released,
                "false_released": false,
                "actual_FTR": actual_lower,
                "actual_FTR_lower": actual_lower,
                "actual_FTR_upper": actual_upper,
                "actual_FTR_le_alpha": actual_upper <= _num(r.get("alpha1"), 0.1) + 1e-12,
                "ground_truth_source": "official_matches_plus_full_audit_of_released_unsupported_paths",
                "paper_use": "real_data_anchor_not_dense_video_ground_truth",
                "notes": "All unsupported released paths in this milestone were audited; official supported matches are treated as true. This is a release-set anchor, not a dense-video actual-FTR benchmark.",
            }
        )
    sweep = _read_csv(real_sources[1])
    if not sweep.empty:
        for _, r in sweep.iterrows():
            released = int(_num(r.get("released")))
            if released <= 0:
                continue
            false = int(_num(r.get("unsupported_actually_false")))
            uncertain = int(_num(r.get("unsupported_uncertain")))
            actual_lower = false / released
            actual_upper = (false + uncertain) / released
            rows.append(
                {
                    "validation_block": "real_data_release_set_audit_anchor",
                    "dataset": "OVT-B",
                    "generator": "GroundingDINO + tracker",
                    "certified_risk_level_alpha": 0.10,
                    "seed": "M_sweep_milestone",
                    "M": int(_num(r.get("candidate_budget_M"))),
                    "released": released,
                    "false_released": false,
                    "actual_FTR": actual_lower,
                    "actual_FTR_lower": actual_lower,
                    "actual_FTR_upper": actual_upper,
                    "actual_FTR_le_alpha": actual_upper <= 0.10 + 1e-12,
                    "ground_truth_source": "official_matches_plus_full_audit_of_released_unsupported_paths",
                    "paper_use": "real_data_anchor_not_dense_video_ground_truth",
                    "notes": "Release-set actual-FTR interval from audited unsupported releases; still not a dense-video annotation study.",
                }
            )
    table = pd.DataFrame(rows)
    out = _write_csv(
        table,
        PAPER_DIR / "table_actual_ftr_validation.csv",
        real_sources,
        started,
        notes="Actual-FTR validation split into controlled known-ground-truth simulation and real release-set audit anchors.",
    )
    outputs.append(out)

    sim = table[table["validation_block"] == "controlled_simulation_known_ground_truth"].copy()
    summary = (
        sim.groupby("certified_risk_level_alpha", dropna=False)
        .agg(
            trials=("actual_FTR", "size"),
            mean_released=("released", "mean"),
            mean_actual_FTR=("actual_FTR", "mean"),
            max_actual_FTR=("actual_FTR", "max"),
            violation_rate=("actual_FTR_le_alpha", lambda s: 1.0 - float(s.mean())),
        )
        .reset_index()
    )
    outputs.append(
        _write_csv(
            summary,
            PAPER_DIR / "table_actual_ftr_validation_summary.csv",
            [out],
            started,
            notes="Controlled-simulation actual-FTR summary over 100 seeds per alpha.",
        )
    )
    fig_csv = summary.rename(columns={"certified_risk_level_alpha": "alpha"})[
        ["alpha", "mean_actual_FTR", "max_actual_FTR", "violation_rate", "mean_released"]
    ]
    fig_path = _write_csv(fig_csv, PAPER_DIR / "figure_actual_ftr_vs_alpha.csv", [out], started)
    _set_style()
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    ax.plot(fig_csv["alpha"], fig_csv["mean_actual_FTR"], marker="o", color=PALETTE["blue"], label="Mean actual FTR")
    ax.plot(fig_csv["alpha"], fig_csv["alpha"], linestyle="--", color=PALETTE["gray"], label="Target alpha")
    ax.scatter(fig_csv["alpha"], fig_csv["max_actual_FTR"], marker="x", color=PALETTE["orange"], label="Max over seeds")
    ax.set_xlabel("Certified risk target alpha")
    ax.set_ylabel("Actual FTR")
    ax.set_title("Known-ground-truth actual-FTR sanity check")
    ax.legend(frameon=False)
    outputs.append(_save_figure(fig, PAPER_DIR / "figure_actual_ftr_vs_alpha.pdf", [fig_path], started))
    return outputs


def _build_tao_sensitivity(started: float) -> list[Path]:
    outputs: list[Path] = []
    source = LEGACY_DIR / "tao_full_clean/table_baseline_expanded.csv"
    frame = _read_csv(source)
    if frame.empty:
        return outputs
    parc = frame[frame["method"].eq("parc_track_gamma_tuned_uniform_scs")].copy()
    parc = parc[parc["candidate_budget_M"].isin([75, 100, 125, 150, 175, 200, 250])]
    rows = []
    for (alpha, m), group in parc.groupby(["alpha1", "candidate_budget_M"]):
        released = pd.to_numeric(group["released"], errors="coerce").fillna(0)
        cons = pd.to_numeric(group.get("conservative_ftr_uncertain_and_unlabeled_false"), errors="coerce")
        mass = pd.to_numeric(group.get("best_margin"), errors="coerce")
        rows.append(
            {
                "dataset": "TAO",
                "generator": "GroundingDINO + tracker",
                "certified_risk_level_alpha": float(alpha),
                "M": int(m),
                "seeds": int(group["seed"].nunique()),
                "nonempty_seeds": int((released > 0).sum()),
                "mean_released": float(released.mean()),
                "max_released": float(released.max()),
                "mean_conservative_label_uncertainty_FTR": float(cons.mean(skipna=True)) if cons.notna().any() else np.nan,
                "mean_mass_margin": float(mass.mean(skipna=True)) if mass.notna().any() else np.nan,
                "positive_cell": bool((released > 0).any()),
                "recommended_framing": "main_positive_at_relaxed_risk" if (alpha >= 0.2 and int(m) == 150 and (released > 0).any()) else "stress_or_sensitivity",
            }
        )
    table = pd.DataFrame(rows).sort_values(["certified_risk_level_alpha", "M"])
    outputs.append(
        _write_csv(
            table,
            PAPER_DIR / "table_tao_sensitivity_framing.csv",
            [source],
            started,
            notes="TAO sensitivity used to decide whether TAO is a main positive benchmark or a stress-test/refusal benchmark.",
        )
    )
    note = REVIEW_DIR / "TAO_FRAMING_NOTE.md"
    ensure_data_output(note)
    alpha02 = table[(table["certified_risk_level_alpha"] == 0.2) & (table["M"] == 150)]
    alpha01 = table[(table["certified_risk_level_alpha"] == 0.1) & (table["M"] == 150)]
    note.write_text(
        "# TAO Framing Decision\n\n"
        "TAO should not be described as a uniform failure. Under the fixed main budget M=150, "
        "alpha=0.10 is a stress/refusal setting, while alpha=0.20 provides a positive sensitivity cell.\n\n"
        f"- TAO alpha=0.10, M=150: non-empty seeds = {int(alpha01['nonempty_seeds'].iloc[0]) if not alpha01.empty else 'NA'} / 3.\n"
        f"- TAO alpha=0.20, M=150: non-empty seeds = {int(alpha02['nonempty_seeds'].iloc[0]) if not alpha02.empty else 'NA'} / 3; "
        f"mean released = {float(alpha02['mean_released'].iloc[0]):.2f}.\n\n"
        "Paper framing: use TAO alpha=0.10 as a certified-refusal stress case and TAO alpha=0.20 as the positive TAO sensitivity result. "
        "Do not mix these two rows as if they were the same claim.\n",
        encoding="utf-8",
    )
    outputs.append(note)
    return outputs


def _build_second_review_and_dense_tasks(started: float) -> list[Path]:
    outputs: list[Path] = []
    second_source = DATA_ROOT / "outputs/benchmarks/parc_certification_benchmark/audit/second_rater_agreement_summary.csv"
    audit_source = RELIABILITY_DIR / "audit_labels_2000_human_reviewed.csv"
    second = _read_csv(second_source)
    audit = _read_csv(audit_source)
    rows = []
    if not second.empty:
        metrics = dict(zip(second["metric"], second["value"]))
        rows.append(
            {
                "evidence_block": "second_review_300",
                "rows": metrics.get("rows_total", "300"),
                "label_agreement_rate": metrics.get("label_agreement_rate", ""),
                "cohens_kappa": metrics.get("cohens_kappa", ""),
                "verified_positive_agreement_rate": metrics.get("verified_positive_agreement_rate", ""),
                "paper_placement": "main_or_appendix_with_protocol_details",
                "reviewer_risk": "near-perfect agreement can invite scrutiny; provide protocol and an additional challenge template",
            }
        )
    rows.append(
        {
            "evidence_block": "recommended_additional_blind_challenge",
            "rows": 500,
            "label_agreement_rate": "pending",
            "cohens_kappa": "pending",
            "verified_positive_agreement_rate": "pending",
            "paper_placement": "optional_before_submission_or_limitation",
            "reviewer_risk": "would directly address concern that perfect agreement is too easy or not independently blinded",
        }
    )
    out = _write_csv(
        pd.DataFrame(rows),
        PAPER_DIR / "table_second_review_credibility_positioning.csv",
        [second_source],
        started,
        notes="Positions the completed 300-row second review and the optional stricter challenge sample.",
    )
    outputs.append(out)
    if not audit.empty:
        pool = audit.copy()
        pool["score_bin"] = pool.get("score_bin", "unknown")
        minority = pool[pool["label"].isin(["actually_false", "uncertain"])].copy()
        true_pool = pool[pool["label"].eq("actually_true")].copy()
        samples = []
        if not minority.empty:
            samples.append(minority.sample(n=min(len(minority), 180), random_state=17, replace=False))
        if not true_pool.empty:
            need = 500 - sum(len(x) for x in samples)
            samples.append(true_pool.sample(n=min(len(true_pool), max(0, need)), random_state=18, replace=False))
        challenge = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()
        keep_cols = [c for c in ["dataset", "video_id", "path_id", "pending_montage_path"] if c in challenge.columns]
        challenge = challenge[keep_cols].copy() if keep_cols else challenge.head(0)
        challenge.insert(0, "challenge_sample_id", [f"sr_challenge_{i:04d}" for i in range(len(challenge))])
        challenge["second_reviewer_label"] = ""
        challenge["second_reviewer_verified_positive_for_calibration"] = ""
        challenge["second_reviewer_reason"] = ""
        challenge["second_reviewer_confidence"] = ""
        challenge["review_status"] = "requires_independent_blind_review"
        outputs.append(
            _write_csv(
                challenge,
                AUDIT_REVIEW_DIR / "second_review_challenge_template_500.csv",
                [audit_source],
                started,
                notes="Blind challenge template with labels withheld; generated to address near-perfect agreement scrutiny.",
            )
        )
    note = REVIEW_DIR / "SECOND_REVIEW_CREDIBILITY_NOTE.md"
    ensure_data_output(note)
    note.write_text(
        "# Second-Review Credibility Note\n\n"
        "The current release includes a 300-row human second-review table with very high agreement. "
        "Because near-perfect agreement can itself attract statistical scrutiny, the paper-facing package separates the completed agreement result from an optional stricter 500-row blind challenge template. "
        "If the stricter challenge is not completed before submission, report the 300-row result with full protocol details and list the additional challenge as an available reproducibility artifact rather than overstating it as a new independent study.\n",
        encoding="utf-8",
    )
    outputs.append(note)
    return outputs


def _binomial_zero_error_upper(n: int, alpha: float = 0.05) -> float:
    if n <= 0:
        return 1.0
    return 1.0 - alpha ** (1.0 / n)


def _build_theory_and_positioning(started: float) -> list[Path]:
    outputs: list[Path] = []
    audit_source = RELIABILITY_DIR / "audit_labels_2000_human_reviewed.csv"
    audit = _read_csv(audit_source)
    vp_count = 0
    vp_false = 0
    if not audit.empty and "verified_positive_for_calibration" in audit.columns:
        vp = audit[audit["verified_positive_for_calibration"].astype(str).str.lower().isin(["yes", "true", "1"])]
        vp_count = int(len(vp))
        vp_false = int(vp[vp["label"].eq("actually_false")].shape[0]) if "label" in vp.columns else 0
    eps95 = _binomial_zero_error_upper(vp_count - vp_false if vp_false == 0 else vp_count)
    robustness = REVIEW_DIR / "VERIFIED_POSITIVE_PRECISION_ROBUSTNESS.md"
    ensure_data_output(robustness)
    robustness.write_text(
        "# Verified-Positive Precision Robustness\n\n"
        "Let epsilon denote an upper bound on the false-tracklet rate inside the verified-positive set used for one-sided removal. "
        "The null-superset proof controls the nulls that remain in the calibrated null superset. If verified-positive removal has contamination epsilon, an operational additive sensitivity bound is\n\n"
        "```text\nactual FTR <= certified alpha + contamination_leakage,\ncontamination_leakage <= epsilon * N_removed / max(1, |R|).\n```\n\n"
        "A conservative paper-facing version can report this as a robustness margin rather than as the main theorem. "
        f"In Audit2000, verified-positive rows = {vp_count}, observed false verified positives = {vp_false}. "
        f"With zero observed false verified positives, the one-sided 95% binomial upper bound is approximately {eps95:.4f}. "
        "This bound is intentionally conservative and should be presented as sensitivity analysis, not as a replacement for the one-sided reliability assumption.\n",
        encoding="utf-8",
    )
    outputs.append(robustness)

    theorem = REVIEW_DIR / "THEOREM1_MAIN_TEXT.md"
    theorem.write_text(
        "# Theorem 1 Main-Text Statement Draft\n\n"
        "**Theorem 1 (Audit-aware null-superset certified release).** Fix a candidate universe, a score rule, a Mondrian cell rule, a release grid, and an SCS selector before observing calibration/test labels. Assume:\n\n"
        "1. **Video-level exchangeability.** Calibration and test videos are exchangeable within each reported protocol split.\n"
        "2. **One-sided verified-positive reliability.** Any path removed from the null superset by the audit protocol is truly non-null, except for the separately reported robustness sensitivity epsilon.\n"
        "3. **Frozen universe and selection rule.** Candidate generation, scoring, calibration, gamma selection, and SCS selection do not use test labels except through the released-set audit diagnostics reported after selection.\n\n"
        "Then the PARC release set R satisfies the target false-tracklet-rate control for the calibrated null-superset target,\n\n"
        "```text\nE[ |R ∩ H0| / max(1, |R|) ] <= alpha,\n```\n\n"
        "where H0 is the true false-tracklet null set under the one-sided audit reliability assumption. Empty releases are valid certified refusals. The full proof remains in the supplement; the main text should include this full statement and a proof sketch.\n",
        encoding="utf-8",
    )
    outputs.append(theorem)

    related = REVIEW_DIR / "RELATED_WORK_POSITIONING.md"
    related.write_text(
        "# Related-Work Positioning Notes\n\n"
        "Web-checked references (2026-05-13):\n\n"
        "- Angelopoulos, Bates, Fisch, Lei, and Schuster, *Conformal Risk Control*, arXiv:2208.02814, https://arxiv.org/abs/2208.02814. PARC differs by controlling set-level release under path conflicts and incomplete annotations.\n"
        "- Angelopoulos et al., *Conformal Risk Control for Non-Monotonic Losses*, arXiv:2602.20151, https://arxiv.org/abs/2602.20151. This is relevant for non-monotone/discrete-grid risk; PARC's SCS feasibility and null-superset audit mechanism are the tracking-specific additions.\n"
        "- Wang and Ramdas, *False discovery rate control with e-values*, arXiv:2009.02824 / JRSSB, https://arxiv.org/abs/2009.02824. PARC uses e-value-style evidence but couples it to path compatibility and a uniform SCS release rule rather than applying e-BH directly.\n"
        "- Vovk, *Conformal e-prediction*, arXiv:2001.05989 / Pattern Recognition, https://arxiv.org/abs/2001.05989. PARC is closest in spirit to e-value conformal evidence, but targets auditable release-time decisions under partial labels.\n\n"
        "Suggested prose: PARC is not a replacement for CRC or e-BH. It combines conformal/e-value evidence with a one-sided audit protocol and a compatibility-constrained selector for open-world perception outputs.\n",
        encoding="utf-8",
    )
    outputs.append(related)

    reframing = REVIEW_DIR / "NMI_REFRAMING_NOTES.md"
    reframing.write_text(
        "# NMI Reframing Notes\n\n"
        "**Abstract opening.** Open-world perception systems increasingly make release-time decisions from incomplete annotations: which detections, tracks, or mask paths should be trusted, sent to humans, or admitted into downstream datasets? PARC provides an auditable certification layer for these release decisions.\n\n"
        "**Intro framing.** Tracking is the main instantiation because it exposes path conflicts, temporal dependence, and partial labels, but the broader problem is release-time certification for open-vocabulary visual AI under incomplete supervision.\n\n"
        "**Deployment scenario.** A monitoring or dataset-curation system may prefer a certified subset plus explicit refusals over an uncalibrated top-M dump. PARC's value is the risk knob and the refusal diagnostic, not SOTA HOTA maximization.\n\n"
        "**TAO framing.** Use TAO alpha=0.10 as a hard partial-annotation stress/refusal setting and TAO alpha=0.20 as a positive sensitivity result.\n",
        encoding="utf-8",
    )
    outputs.append(reframing)
    return outputs


def _write_report(paths: list[Path], started: float) -> Path:
    report = REVIEW_DIR / "RUN_REPORT.md"
    ensure_data_output(report)
    report.write_text(
        "# Reviewer-Critical Closeout Report\n\n"
        "This closeout addresses the highest-risk review questions before manuscript polishing.\n\n"
        "## Completed artifacts\n\n"
        + "\n".join(f"- `{_rel(path)}`" for path in paths)
        + "\n\n## Interpretation\n\n"
        "- Actual-FTR evidence is split into a known-ground-truth controlled simulation and a real release-set audit anchor. The latter is not a dense-video ground-truth benchmark.\n"
        "- The near-perfect second-review result is retained with protocol details and supplemented by a stricter blind challenge template for external review if desired.\n"
        "- TAO should be framed as both a stress/refusal case at alpha=0.10 and a positive sensitivity result at alpha=0.20.\n"
        "- Theorem, robustness, and related-work notes are draft text for manuscript integration.\n",
        encoding="utf-8",
    )
    return report


def run_phase17_reviewer_closeout(output_dir: str | None = None) -> dict[str, Any]:
    del output_dir
    started = time.time()
    ensure_data_output(REVIEW_DIR / ".keep")
    paths: list[Path] = []
    paths.extend(_build_actual_ftr_validation(started))
    paths.extend(_build_tao_sensitivity(started))
    paths.extend(_build_second_review_and_dense_tasks(started))
    paths.extend(_build_theory_and_positioning(started))
    paths.append(_write_report(paths, started))
    return {
        "output_dir": _rel(REVIEW_DIR),
        "artifacts": [_rel(path) for path in paths],
        "runtime_sec": round(time.time() - started, 6),
    }
