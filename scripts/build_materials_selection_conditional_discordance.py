#!/usr/bin/env python3
"""Build the selection-conditional materials-label discordance go/no-go.

This is a no-new-data diagnostic for the hypothesis that MP/Alexandria label
discordance is amplified in the high-confidence region selected by ML
materials-stability models.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/materials_selection_conditional_discordance"
SOURCE_ROOT = Path("/home/waas/paper_experiments/github/discordance-/outputs/milestones/materials_label_discordance_preregistration")
MATCHES = SOURCE_ROOT / "table_route_b_full_snapshot_matches.csv"
SCORES = SOURCE_ROOT / "table_route_b_full_snapshot_model_scores.csv"
SUMMARY = SOURCE_ROOT / "table_route_b_full_snapshot_summary.csv"
MODELS = ["ALIGNN-FF", "CHGNet", "MACE-MP"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return math.nan, math.nan
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def spearman_rank_corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(ys) < 2:
        return math.nan
    xr = pd.Series(xs).rank(method="average").to_numpy()
    yr = pd.Series(ys).rank(method="average").to_numpy()
    xbar = float(xr.mean())
    ybar = float(yr.mean())
    num = float(((xr - xbar) * (yr - ybar)).sum())
    den = math.sqrt(float(((xr - xbar) ** 2).sum()) * float(((yr - ybar) ** 2).sum()))
    return num / den if den else math.nan


def bin_rows(model: str, sub: pd.DataFrame, baseline: float, bins: list[tuple[str, int, int]], family: str) -> list[dict]:
    rows: list[dict] = []
    for label, start, stop in bins:
        chunk = sub.iloc[start:stop]
        k = int(chunk["discordant"].sum())
        n = int(len(chunk))
        lo, hi = wilson(k, n)
        rows.append(
            {
                "source_pair": "Materials_Project_vs_alex_mp_v20",
                "match_basis": "strict_structure_match",
                "model": model,
                "score_direction": "lower_score_more_stable",
                "bin_family": family,
                "score_bin": label,
                "rank_start_inclusive": int(start + 1),
                "rank_stop_inclusive": int(stop),
                "n": n,
                "discordant_n": k,
                "discordance_rate": k / n if n else math.nan,
                "wilson95_low": lo,
                "wilson95_high": hi,
                "baseline_discordance": baseline,
                "enrichment_vs_baseline": (k / n) / baseline if n and baseline else math.nan,
                "paper_role": "selection_conditional_go_no_go_diagnostic",
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    matches = pd.read_csv(MATCHES)
    scores = pd.read_csv(SCORES)
    summary = pd.read_csv(SUMMARY).iloc[0].to_dict()

    labels = matches[
        matches["match_status"].eq("strict_structure_match")
        & matches["mp_stable_exact"].notna()
        & matches["alex_stable_exact"].notna()
    ].copy()
    labels["mp_stable_exact"] = labels["mp_stable_exact"].astype(str).str.lower().eq("true")
    labels["alex_stable_exact"] = labels["alex_stable_exact"].astype(str).str.lower().eq("true")
    labels["discordant"] = labels["mp_stable_exact"] != labels["alex_stable_exact"]
    baseline = float(labels["discordant"].mean())

    score_wide = scores[scores["score_status"].eq("scored")].pivot(index="material_id", columns="model", values="score")
    data = labels.merge(score_wide, left_on="material_id", right_index=True, how="inner")
    data = data.dropna(subset=MODELS).copy()

    denominator_fields = [
        "material_id",
        "formula",
        "mp_e_above_hull",
        "alex_e_above_hull",
        "mp_stable_exact",
        "alex_stable_exact",
        "discordant",
        "ALIGNN-FF",
        "CHGNet",
        "MACE-MP",
    ]
    write_csv(
        OUT / "table_selection_conditional_denominator.csv",
        data[denominator_fields].rename(
            columns={"ALIGNN-FF": "score_alignn_ff", "CHGNet": "score_chgnet", "MACE-MP": "score_mace_mp"}
        ).to_dict("records"),
    )

    coarse_rows: list[dict] = []
    decile_rows: list[dict] = []
    top_rows: list[dict] = []
    trend_rows: list[dict] = []

    for model in MODELS:
        sub = data.sort_values(model, ascending=True).reset_index(drop=True)
        n = len(sub)
        coarse_bins = [
            ("top_10pct", 0, math.ceil(0.10 * n)),
            ("top_10_to_25pct", math.ceil(0.10 * n), math.ceil(0.25 * n)),
            ("top_25_to_50pct", math.ceil(0.25 * n), math.ceil(0.50 * n)),
            ("bottom_50pct", math.ceil(0.50 * n), n),
        ]
        decile_bins = [
            (f"decile_{idx + 1}", math.floor(idx * n / 10), math.floor((idx + 1) * n / 10))
            for idx in range(10)
        ]
        coarse_rows.extend(bin_rows(model, sub, baseline, coarse_bins, "coarse"))
        model_deciles = bin_rows(model, sub, baseline, decile_bins, "decile")
        decile_rows.extend(model_deciles)
        top = [row for row in model_deciles if row["score_bin"] == "decile_1"][0]
        top_rows.append(
            {
                "model": model,
                "top_decile_n": top["n"],
                "top_decile_discordant_n": top["discordant_n"],
                "top_decile_discordance": top["discordance_rate"],
                "baseline_discordance": baseline,
                "top_decile_enrichment": top["enrichment_vs_baseline"],
                "top_decile_ge_0_30": bool(top["discordance_rate"] >= 0.30),
                "top_decile_ge_2x_baseline": bool(top["enrichment_vs_baseline"] >= 2.0),
            }
        )
        decile_rates = [float(row["discordance_rate"]) for row in model_deciles]
        # Decile index is ordered from high-confidence to low-confidence. A
        # negative rho would indicate higher discordance in the high-confidence
        # region; positive/near-zero does not support concentration at the top.
        rho = spearman_rank_corr(list(range(1, 11)), decile_rates)
        trend_rows.append(
            {
                "model": model,
                "n_common": n,
                "baseline_discordance": baseline,
                "top_decile_discordance": top["discordance_rate"],
                "top_decile_enrichment": top["enrichment_vs_baseline"],
                "decile_spearman_rho_rank_vs_discordance": rho,
                "supports_high_score_amplification": bool(
                    top["discordance_rate"] >= 0.30 and top["enrichment_vs_baseline"] >= 2.0 and rho < 0
                ),
            }
        )

    models_supporting = sum(bool(row["supports_high_score_amplification"]) for row in trend_rows)
    top_decile_ge_030 = sum(bool(row["top_decile_ge_0_30"]) for row in top_rows)
    top_decile_ge_2x = sum(bool(row["top_decile_ge_2x_baseline"]) for row in top_rows)
    go = models_supporting >= 2 and top_decile_ge_030 >= 2 and top_decile_ge_2x >= 2

    gate_rows = [
        {
            "hypothesis": "B_selection_conditional_discordance",
            "source_pair": "Materials_Project_vs_alex_mp_v20",
            "n_common": int(len(data)),
            "baseline_discordance": baseline,
            "models_tested": "|".join(MODELS),
            "pass_rule": "at_least_2_models_with_top_decile_discordance_ge_0_30_and_ge_2x_baseline_and_negative_decile_trend",
            "models_supporting_rule": models_supporting,
            "models_top_decile_ge_0_30": top_decile_ge_030,
            "models_top_decile_ge_2x_baseline": top_decile_ge_2x,
            "go_no_go": "GO_reopen_NMI_discordance_nugget" if go else "NO_GO_hypothesis_B_not_supported",
            "claim_scope": (
                "selection-conditional amplification supported"
                if go
                else "MP-vs-alex full snapshot discordance is not concentrated in the high-confidence model-score region"
            ),
            "paper_role": "completed_go_no_go_diagnostic",
        }
    ]

    write_csv(OUT / "table_score_stratified_discordance.csv", coarse_rows)
    write_csv(OUT / "table_decile_discordance.csv", decile_rows)
    write_csv(OUT / "table_top_decile_discordance.csv", top_rows)
    write_csv(OUT / "table_model_trend_tests.csv", trend_rows)
    write_csv(OUT / "table_selection_conditional_go_no_go.csv", gate_rows)

    provenance = {
        "source_matches": "external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_route_b_full_snapshot_matches.csv",
        "source_matches_sha256": sha256_file(MATCHES),
        "source_scores": "external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_route_b_full_snapshot_model_scores.csv",
        "source_scores_sha256": sha256_file(SCORES),
        "source_summary": "external_discordance_repo::outputs/milestones/materials_label_discordance_preregistration/table_route_b_full_snapshot_summary.csv",
        "source_summary_sha256": sha256_file(SUMMARY),
        "source_summary_row": summary,
        "n_common": int(len(data)),
        "baseline_discordance": baseline,
        "models": MODELS,
        "score_direction": "lower_score_more_stable",
        "claim_boundary": "No new data, no new DFT, no new training; diagnostic only unless pass gate holds.",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")

    closeout = [
        "# Selection-Conditional Materials Label Discordance Go/No-Go\n\n",
        "This milestone tests Proposition B: whether MP/Alexandria exact-stability discordance is amplified in the high-confidence region selected by ML materials-stability scores.\n\n",
        "## Inputs\n\n",
        f"- Source pair: Materials Project vs alex-mp v20.\n",
        f"- Exact matched denominator: `{len(data)}` structures.\n",
        f"- Baseline discordance: `{baseline:.3f}`.\n",
        f"- Models: `{', '.join(MODELS)}`.\n",
        "- Score direction: lower score means more model-favored / more stable.\n\n",
        "## Result\n\n",
    ]
    for row in top_rows:
        closeout.append(
            f"- {row['model']}: top-decile discordance `{row['top_decile_discordance']:.3f}` "
            f"({row['top_decile_discordant_n']}/{row['top_decile_n']}), enrichment `{row['top_decile_enrichment']:.2f}x`.\n"
        )
    closeout.extend(
        [
            "\n## Go/No-Go\n\n",
            f"- Decision: `{gate_rows[0]['go_no_go']}`.\n",
            f"- Interpretation: {gate_rows[0]['claim_scope']}.\n\n",
            "## Claim Boundary\n\n",
            "This is a completed diagnostic, not a positive independent-validation result and not prospective materials discovery. It uses existing frozen MP/Alex exact-match labels and existing frozen model scores only.\n",
        ]
    )
    (OUT / "SELECTION_CONDITIONAL_DISCORDANCE_CLOSEOUT.md").write_text("".join(closeout), encoding="utf-8")

    manifest_lines = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            manifest_lines.append(f"{sha256_file(path)}  {path.relative_to(OUT)}")
    (OUT / "MANIFEST_SHA256.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(json.dumps(gate_rows[0], indent=2))


if __name__ == "__main__":
    main()
