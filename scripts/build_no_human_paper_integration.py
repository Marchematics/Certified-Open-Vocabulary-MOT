#!/usr/bin/env python3
"""Build paper-facing phase20 consequence summaries.

This script is deliberately downstream-only: it reads completed phase20
milestone tables and writes editorial/paper-facing summaries. It does not
create new experimental rows, does not add labels, and does not promote
not-run model sources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def num(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.1f}"


def write_provenance(path: Path, artifact: Path, inputs: dict[str, str], role: str) -> None:
    payload = {
        "status": "completed",
        "evidence_status": "paper_facing_summary_from_completed_phase20_tables",
        "role": role,
        "artifact": artifact.name,
        "command": "python scripts/build_no_human_paper_integration.py",
        "input_hashes": inputs,
        "output_sha256": sha256_file(artifact),
        "scope": "paper-facing integration; no new labels; no new experimental rows",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_tables(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    materials = pd.read_csv(root / "table_materials_computational_followup.csv")
    model_zoo = pd.read_csv(root / "table_materials_model_zoo_release_frontier.csv")
    ctc = pd.read_csv(root / "table_ctc_lineage_consequence.csv")
    spacenet = pd.read_csv(root / "table_spacenet_map_consequence.csv")
    return materials, model_zoo, ctc, spacenet


def select_rows(
    materials: pd.DataFrame, ctc: pd.DataFrame, spacenet: pd.DataFrame
) -> dict[str, pd.Series]:
    alignn_k500 = materials[
        (materials["model_family"] == "ALIGNN-FF")
        & np.isclose(materials["alpha"].astype(float), 0.10)
        & (materials["K"].astype(int) == 500)
    ].iloc[0]
    alignn_k5000 = materials[
        (materials["model_family"] == "ALIGNN-FF")
        & np.isclose(materials["alpha"].astype(float), 0.10)
        & (materials["K"].astype(int) == 5000)
    ].iloc[0]
    ctc_noisy = ctc[
        (ctc["proposal_source"] == "ctc_noisy_geometric_linker")
        & (ctc["K"].astype(int) == 5000)
    ].iloc[0]
    ctc_random = ctc[
        (ctc["proposal_source"] == "ctc_random_score_negative_control")
        & (ctc["K"].astype(int) == 5000)
    ].iloc[0]
    spacenet_geometry = spacenet[
        (spacenet["proposal_source"] == "geometry_linker")
        & (spacenet["K"].astype(int) == 5000)
    ].iloc[0]
    spacenet_random = spacenet[
        (spacenet["proposal_source"] == "randomized_linker")
        & (spacenet["K"].astype(int) == 5000)
    ].iloc[0]
    return {
        "alignn_k500": alignn_k500,
        "alignn_k5000": alignn_k5000,
        "ctc_noisy": ctc_noisy,
        "ctc_random": ctc_random,
        "spacenet_geometry": spacenet_geometry,
        "spacenet_random": spacenet_random,
    }


def build_summary(rows: dict[str, pd.Series], model_zoo: pd.DataFrame) -> pd.DataFrame:
    alignn_k500 = rows["alignn_k500"]
    alignn_k5000 = rows["alignn_k5000"]
    ctc_noisy = rows["ctc_noisy"]
    spacenet_random = rows["spacenet_random"]
    alpha010 = model_zoo[np.isclose(model_zoo["alpha"].astype(float), 0.10)].copy()
    completed_models = sorted(alpha010["model_family"].dropna().unique().tolist())
    certified = alpha010[alpha010["release_status"] == "certified_release_low_FTR"]
    refused = alpha010[alpha010["release_status"] == "certified_refusal_or_low_power"]
    summary = [
        {
            "domain": "Materials",
            "scientific_workflow": "DFT / computational follow-up queue",
            "raw_decision_consequence": (
                f"ALIGNN-FF raw top-500 admits {num(alignn_k500['raw_unstable_count_mean'])} "
                f"unstable candidates on average ({pct(alignn_k500['raw_topK_FTR_mean'])} raw FTR)."
            ),
            "PARC_decision": (
                f"PARC releases {num(alignn_k500['mean_release'])} candidates with "
                f"{num(alignn_k500['PARC_unstable_count_mean'])} unstable candidates "
                f"({pct(alignn_k500['PARC_FTR_mean'])} FTR)."
            ),
            "consequence_prevented": (
                f"{num(alignn_k500['prevented_unstable_followups_mean'])} unstable follow-ups "
                "prevented per seed relative to raw top-K."
            ),
            "headline_value": float(alignn_k500["prevented_unstable_followups_mean"]),
            "evidence_status": "completed_public_DFT_label_followup",
            "paper_scope": "retrospective public-label computational follow-up; not experimental synthesis",
        },
        {
            "domain": "Materials high-volume",
            "scientific_workflow": "High-volume DFT / computational follow-up queue",
            "raw_decision_consequence": (
                f"ALIGNN-FF raw top-5000 admits {num(alignn_k5000['raw_unstable_count_mean'])} "
                f"unstable candidates on average ({pct(alignn_k5000['raw_topK_FTR_mean'])} raw FTR)."
            ),
            "PARC_decision": "PARC returns certified refusal at K=5000 under alpha=0.10.",
            "consequence_prevented": (
                f"{num(alignn_k5000['prevented_unstable_followups_mean'])} unstable follow-ups "
                "prevented per seed by refusing the unsupported high-volume request."
            ),
            "headline_value": float(alignn_k5000["prevented_unstable_followups_mean"]),
            "evidence_status": "completed_public_DFT_label_followup",
            "paper_scope": "retrospective public-label computational follow-up; not experimental synthesis",
        },
        {
            "domain": "Materials model zoo",
            "scientific_workflow": "Model-agnostic release governance",
            "raw_decision_consequence": (
                f"Completed local public-prediction sources: {', '.join(completed_models)}; "
                "raw risk and power vary across model/K."
            ),
            "PARC_decision": (
                f"At alpha=0.10, {len(certified)} model-budget rows are certified-release rows "
                f"and {len(refused)} model-budget rows are certified-refusal rows."
            ),
            "consequence_prevented": (
                "The same release/refusal interface applies across available learned materials sources; "
                "missing modern-model prediction files remain not-run rows."
            ),
            "headline_value": float(len(certified)),
            "evidence_status": "completed_for_available_public_prediction_files",
            "paper_scope": "model-zoo frontier is limited to locally available public prediction files",
        },
        {
            "domain": "CTC",
            "scientific_workflow": "Cell lineage graph",
            "raw_decision_consequence": (
                f"Noisy high-volume raw K=5000 inserts {num(ctc_noisy['raw_false_links_mean'])} "
                f"false lineage edges and {num(ctc_noisy['raw_component_corruption_proxy_mean'])} "
                "component-corruption proxy units per seed."
            ),
            "PARC_decision": "PARC refuses the unsupported high-volume request.",
            "consequence_prevented": (
                f"{num(ctc_noisy['prevented_false_links_mean'])} false lineage edges and "
                f"{num(ctc_noisy['prevented_component_corruption_proxy_mean'])} "
                "component-corruption proxy units prevented per seed."
            ),
            "headline_value": float(ctc_noisy["prevented_false_links_mean"]),
            "evidence_status": "completed_official_GT_lineage_consequence",
            "paper_scope": "official CTC GT consequence proxy; no new manual review",
        },
        {
            "domain": "SpaceNet 7",
            "scientific_workflow": "Building-persistence map",
            "raw_decision_consequence": (
                f"Randomized same-building K=5000 inserts {num(spacenet_random['raw_false_persistence_links'])} "
                f"false persistence links ({pct(spacenet_random['raw_false_link_fraction'])} raw false-link fraction)."
            ),
            "PARC_decision": "Existing SpaceNet randomized-source sweeps support refusal for unsupported requests.",
            "consequence_prevented": (
                f"{num(spacenet_random['raw_false_persistence_links'])} false map-persistence links are "
                "quantified as avoidable map pollution under refusal."
            ),
            "headline_value": float(spacenet_random["raw_false_persistence_links"]),
            "evidence_status": "completed_official_GT_map_consequence",
            "paper_scope": "official SpaceNet identity labels; randomized source is a stress/control source",
        },
    ]
    return pd.DataFrame(summary)


def build_figure_source(rows: dict[str, pd.Series], model_zoo: pd.DataFrame) -> pd.DataFrame:
    records: list[dict] = []
    a500 = rows["alignn_k500"]
    a5000 = rows["alignn_k5000"]
    for setting, row in [("ALIGNN K=500", a500), ("ALIGNN K=5000", a5000)]:
        records.extend(
            [
                {
                    "panel": "a_materials_followup",
                    "group": setting,
                    "metric": "raw_unstable",
                    "value": float(row["raw_unstable_count_mean"]),
                    "unit": "unstable candidates per seed",
                    "display_label": "Raw top-K unstable",
                },
                {
                    "panel": "a_materials_followup",
                    "group": setting,
                    "metric": "parc_unstable",
                    "value": float(row["PARC_unstable_count_mean"]),
                    "unit": "unstable candidates per seed",
                    "display_label": "PARC unstable",
                },
                {
                    "panel": "a_materials_followup",
                    "group": setting,
                    "metric": "prevented_unstable",
                    "value": float(row["prevented_unstable_followups_mean"]),
                    "unit": "unstable candidates per seed",
                    "display_label": "Prevented",
                },
            ]
        )
    alpha010 = model_zoo[np.isclose(model_zoo["alpha"].astype(float), 0.10)].copy()
    for _, row in alpha010.iterrows():
        records.append(
            {
                "panel": "b_materials_model_zoo",
                "group": str(row["model_family"]),
                "metric": f"K={int(row['K'])}",
                "value": float(row["non_empty_seeds"]),
                "unit": "non-empty seeds out of 20",
                "display_label": str(row["release_status"]),
            }
        )
    for source_key, source_label in [
        ("ctc_noisy", "Noisy geometric K=5000"),
        ("ctc_random", "Random-score K=5000"),
    ]:
        row = rows[source_key]
        records.extend(
            [
                {
                    "panel": "c_ctc_lineage",
                    "group": source_label,
                    "metric": "raw_false_links",
                    "value": float(row["raw_false_links_mean"]),
                    "unit": "false links per seed",
                    "display_label": "Raw false lineage edges",
                },
                {
                    "panel": "c_ctc_lineage",
                    "group": source_label,
                    "metric": "prevented_false_links",
                    "value": float(row["prevented_false_links_mean"]),
                    "unit": "false links per seed",
                    "display_label": "Prevented false lineage edges",
                },
                {
                    "panel": "c_ctc_lineage",
                    "group": source_label,
                    "metric": "component_corruption_proxy",
                    "value": float(row["prevented_component_corruption_proxy_mean"]),
                    "unit": "component-corruption proxy per seed",
                    "display_label": "Prevented component-corruption proxy",
                },
            ]
        )
    for source_key, source_label in [
        ("spacenet_geometry", "Geometry K=5000"),
        ("spacenet_random", "Randomized K=5000"),
    ]:
        row = rows[source_key]
        records.extend(
            [
                {
                    "panel": "d_spacenet_map",
                    "group": source_label,
                    "metric": "raw_false_persistence_links",
                    "value": float(row["raw_false_persistence_links"]),
                    "unit": "false persistence links",
                    "display_label": "Raw false persistence links",
                },
                {
                    "panel": "d_spacenet_map",
                    "group": source_label,
                    "metric": "false_persistence_chain_proxy",
                    "value": float(row["raw_false_persistence_chain_proxy"]),
                    "unit": "false chain proxy",
                    "display_label": "False chain proxy",
                },
            ]
        )
    return pd.DataFrame(records)


def status_code(status: str) -> int:
    if status == "certified_release_low_FTR":
        return 2
    if status == "boundary_or_partial_release":
        return 1
    return 0


def build_model_zoo_frontier(model_zoo: pd.DataFrame) -> pd.DataFrame:
    alpha010 = model_zoo[np.isclose(model_zoo["alpha"].astype(float), 0.10)].copy()
    alpha010["status_code"] = alpha010["release_status"].map(status_code)
    alpha010["cell_label"] = alpha010.apply(
        lambda row: f"{int(row['non_empty_seeds'])}/20\nFTR {row['PARC_FTR_mean']:.3f}",
        axis=1,
    )
    return alpha010[
        [
            "model_family",
            "K",
            "alpha",
            "release_status",
            "status_code",
            "non_empty_seeds",
            "mean_release",
            "PARC_FTR_mean",
            "raw_topK_FTR_mean",
            "prevented_unstable_followups_mean",
            "cell_label",
            "evidence_status",
        ]
    ].copy()


def plot_main_figure(figure_source: pd.DataFrame, model_frontier: pd.DataFrame, out_pdf: Path) -> None:
    plt.rcParams.update(
        {
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.2))

    # Panel A
    ax = axes[0, 0]
    data = figure_source[figure_source["panel"] == "a_materials_followup"]
    groups = ["ALIGNN K=500", "ALIGNN K=5000"]
    metrics = ["raw_unstable", "parc_unstable", "prevented_unstable"]
    colors = {"raw_unstable": "#d95f02", "parc_unstable": "#1b9e77", "prevented_unstable": "#7570b3"}
    x = np.arange(len(groups))
    width = 0.24
    for idx, metric in enumerate(metrics):
        vals = [
            float(data[(data["group"] == group) & (data["metric"] == metric)]["value"].iloc[0])
            for group in groups
        ]
        ax.bar(x + (idx - 1) * width, vals, width=width, color=colors[metric], label=metric.replace("_", " "))
    ax.set_xticks(x)
    ax.set_xticklabels(groups, rotation=15, ha="right")
    ax.set_ylabel("Unstable candidates per seed")
    ax.set_title("a  Materials follow-up queue")
    ax.legend(fontsize=6, frameon=False)

    # Panel B
    ax = axes[0, 1]
    models = sorted(model_frontier["model_family"].unique().tolist())
    budgets = sorted(model_frontier["K"].astype(int).unique().tolist())
    mat = np.full((len(models), len(budgets)), np.nan)
    labels: dict[tuple[int, int], str] = {}
    for i, model in enumerate(models):
        for j, budget in enumerate(budgets):
            row = model_frontier[(model_frontier["model_family"] == model) & (model_frontier["K"] == budget)]
            if len(row):
                mat[i, j] = float(row["status_code"].iloc[0])
                labels[(i, j)] = str(row["cell_label"].iloc[0])
    cmap = matplotlib.colors.ListedColormap(["#d9d9d9", "#fee08b", "#1b9e77"])
    ax.imshow(mat, cmap=cmap, vmin=0, vmax=2, aspect="auto")
    for (i, j), label in labels.items():
        ax.text(j, i, label, ha="center", va="center", fontsize=5.7)
    ax.set_xticks(np.arange(len(budgets)))
    ax.set_xticklabels([str(k) for k in budgets])
    ax.set_yticks(np.arange(len(models)))
    ax.set_yticklabels(models)
    ax.set_xlabel("K")
    ax.set_title("b  Materials model-zoo frontier")

    # Panel C
    ax = axes[1, 0]
    data = figure_source[figure_source["panel"] == "c_ctc_lineage"]
    groups = ["Noisy geometric K=5000", "Random-score K=5000"]
    metrics = ["raw_false_links", "prevented_false_links"]
    x = np.arange(len(groups))
    for idx, metric in enumerate(metrics):
        vals = [
            float(data[(data["group"] == group) & (data["metric"] == metric)]["value"].iloc[0])
            for group in groups
        ]
        ax.bar(x + (idx - 0.5) * 0.32, vals, width=0.32, label=metric.replace("_", " "))
    ax.set_xticks(x)
    ax.set_xticklabels(["Noisy geom.", "Random score"])
    ax.set_ylabel("False lineage edges per seed")
    ax.set_title("c  CTC lineage consequence")
    ax.legend(fontsize=6, frameon=False)

    # Panel D
    ax = axes[1, 1]
    data = figure_source[figure_source["panel"] == "d_spacenet_map"]
    groups = ["Geometry K=5000", "Randomized K=5000"]
    vals = [
        float(
            data[(data["group"] == group) & (data["metric"] == "raw_false_persistence_links")][
                "value"
            ].iloc[0]
        )
        for group in groups
    ]
    ax.bar(["Geometry", "Randomized"], vals, color=["#1b9e77", "#d95f02"])
    ax.set_ylabel("False persistence links")
    ax.set_title("d  SpaceNet map consequence")
    for idx, value in enumerate(vals):
        ax.text(idx, value, num(value), ha="center", va="bottom", fontsize=7)
    fig.suptitle("Scientific consequences without new human annotation", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(out_pdf)
    plt.close(fig)


def plot_model_frontier(model_frontier: pd.DataFrame, out_pdf: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 2.5))
    models = sorted(model_frontier["model_family"].unique().tolist())
    budgets = sorted(model_frontier["K"].astype(int).unique().tolist())
    mat = np.full((len(models), len(budgets)), np.nan)
    for i, model in enumerate(models):
        for j, budget in enumerate(budgets):
            row = model_frontier[(model_frontier["model_family"] == model) & (model_frontier["K"] == budget)]
            if len(row):
                mat[i, j] = float(row["status_code"].iloc[0])
    cmap = matplotlib.colors.ListedColormap(["#d9d9d9", "#fee08b", "#1b9e77"])
    ax.imshow(mat, cmap=cmap, vmin=0, vmax=2, aspect="auto")
    for i, model in enumerate(models):
        for j, budget in enumerate(budgets):
            row = model_frontier[(model_frontier["model_family"] == model) & (model_frontier["K"] == budget)]
            if len(row):
                ax.text(j, i, row["cell_label"].iloc[0], ha="center", va="center", fontsize=6)
    ax.set_xticks(np.arange(len(budgets)))
    ax.set_xticklabels([str(k) for k in budgets])
    ax.set_yticks(np.arange(len(models)))
    ax.set_yticklabels(models)
    ax.set_xlabel("K")
    ax.set_title("Materials release/refusal frontier, alpha=0.10")
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def write_integration_note(root: Path, summary: pd.DataFrame, rows: dict[str, pd.Series]) -> Path:
    a500 = rows["alignn_k500"]
    a5000 = rows["alignn_k5000"]
    ctc_noisy = rows["ctc_noisy"]
    spacenet_random = rows["spacenet_random"]
    text = f"""# Phase20 Paper Integration: Scientific Consequences Without New Human Annotation

This note converts `outputs/milestones/no_human_scientific_consequence/` from a reproducibility milestone into paper-facing impact evidence. It is downstream-only: no new human labels, no new experimental rows, and no protocol-only rows are promoted.

## Four Headline Numbers

1. **Materials follow-up queue.** ALIGNN-FF raw top-500 would send {num(a500['raw_unstable_count_mean'])} unstable candidates to computational follow-up per seed ({pct(a500['raw_topK_FTR_mean'])} raw FTR). PARC releases {num(a500['mean_release'])} candidates with {num(a500['PARC_unstable_count_mean'])} unstable candidates ({pct(a500['PARC_FTR_mean'])} FTR), preventing {num(a500['prevented_unstable_followups_mean'])} unstable follow-ups per seed.
2. **Materials high-volume refusal.** ALIGNN-FF raw top-5000 would send {num(a5000['raw_unstable_count_mean'])} unstable candidates to follow-up per seed ({pct(a5000['raw_topK_FTR_mean'])} raw FTR). PARC refuses the unsupported high-volume request, preventing {num(a5000['prevented_unstable_followups_mean'])} unstable follow-ups per seed under the release/refusal interpretation.
3. **CTC lineage consequence.** In the noisy high-volume CTC link queue, raw K=5000 inserts {num(ctc_noisy['raw_false_links_mean'])} false lineage edges and {num(ctc_noisy['raw_component_corruption_proxy_mean'])} component-corruption proxy units per seed; PARC refuses before those edges enter the lineage graph.
4. **SpaceNet map consequence.** In the randomized SpaceNet same-building stress source, raw K=5000 inserts {num(spacenet_random['raw_false_persistence_links'])} false persistence links ({pct(spacenet_random['raw_false_link_fraction'])} raw false-link fraction), quantifying avoidable building-persistence map pollution under refusal.

## Proposed Results Section

### Release decisions change downstream scientific artifacts

We next asked whether the release-or-refuse decision changes downstream scientific objects without introducing new human audit. We therefore evaluated consequence-level endpoints using only public labels, official ground truth or existing model predictions. In materials discovery, the endpoint is the composition of a computational follow-up queue; in CTC, it is false lineage-edge insertion and component corruption; and in SpaceNet 7, it is false same-building persistence links. These analyses do not create new annotation sources. They translate the same certified release/refusal decisions into the scientific artifacts that would be passed downstream.

In the materials follow-up analysis, PARC reduced the number of unstable candidates that would enter the follow-up queue relative to the raw top-K decision, while preserving the distinction between certified release and certified refusal. Across the model-zoo frontier, CGCNN, ALIGNN-FF and MEGNet showed different raw-risk and power profiles, but the same release interface applied: supported budgets produced certified queues and unsupported high-volume requests were refused. In CTC, raw high-volume link lists inserted false lineage edges and corrupted lineage components, whereas PARC refused or restricted release before those edges entered the lineage graph. In SpaceNet 7, the same logic quantified false persistence links that can enter building-change maps under unsupported sources.

Thus the main consequence of PARC is not improved upstream prediction, but a changed scientific decision: which candidates are allowed to enter a downstream workflow under partial verification.

## Abstract Last-Sentence Replacement

PARC converts unconstrained ranked lists into auditable release-or-refuse decisions, preventing unsupported AI candidates from entering downstream scientific workflows when partial verification is insufficient.

## Figure 6 Caption Draft

**Figure 6 | Scientific consequences without new human annotation.** a, Materials follow-up queues under public WBM/Matbench labels: raw top-K unstable candidates, PARC-release unstable candidates and unstable follow-ups prevented for ALIGNN-FF at K=500 and K=5000. b, Materials model-zoo release/refusal frontier for locally available public prediction files (CGCNN, ALIGNN-FF and MEGNet) at alpha=0.10. Contemporary models without local public prediction files are listed as not-run in the supplement, not as completed evidence. c, CTC official-GT lineage consequence: false lineage edges prevented when high-volume or uninformative link queues are refused. d, SpaceNet 7 official-GT map consequence: false same-building persistence links quantified for geometry and randomized sources. All panels use completed public/official-label diagnostics and introduce no new human labels.

## Cover Letter Impact Block

Scientific AI systems increasingly produce candidate objects that can enter downstream workflows before exhaustive verification is available. This manuscript addresses the release decision itself: which AI-generated candidates should be published, and when should a system refuse to publish any candidate set?

We introduce PARC, a release-time certification layer for one-sided partial verification. PARC does not replace the upstream model. It converts a frozen ranked candidate list into either a certified release set or a certified refusal.

The manuscript now includes consequence-level analyses that require no new human annotation: public WBM/Matbench labels show how PARC changes materials follow-up queues; official CTC ground truth quantifies false lineage edges avoided; and SpaceNet building identities quantify false persistence links avoided. These analyses show that PARC changes the scientific artifacts passed downstream, not merely a benchmark score.

## Model-Zoo Provenance Language

The model-zoo frontier uses public prediction sources available in the local reproducibility package: CGCNN, ALIGNN-FF and MEGNet. Other contemporary sources are listed as not-run when public prediction files were not locally available under the same provenance constraints.

## Paper-Facing Tables

- `table_no_human_consequence_summary.csv`
- `figure_no_human_consequence_main.csv`
- `figure_no_human_consequence_main.pdf`
- `figure_materials_model_zoo_frontier.csv`
- `figure_materials_model_zoo_frontier.pdf`
"""
    path = root / "NO_HUMAN_PAPER_INTEGRATION.md"
    path.write_text(text, encoding="utf-8")
    return path


def update_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="outputs/milestones/no_human_scientific_consequence")
    args = parser.parse_args()
    root = Path(args.root)
    materials, model_zoo, ctc, spacenet = load_tables(root)
    inputs = {
        "table_materials_computational_followup.csv": sha256_file(
            root / "table_materials_computational_followup.csv"
        ),
        "table_materials_model_zoo_release_frontier.csv": sha256_file(
            root / "table_materials_model_zoo_release_frontier.csv"
        ),
        "table_ctc_lineage_consequence.csv": sha256_file(root / "table_ctc_lineage_consequence.csv"),
        "table_spacenet_map_consequence.csv": sha256_file(root / "table_spacenet_map_consequence.csv"),
    }
    rows = select_rows(materials, ctc, spacenet)
    summary = build_summary(rows, model_zoo)
    figure_source = build_figure_source(rows, model_zoo)
    model_frontier = build_model_zoo_frontier(model_zoo)

    outputs = {
        "table_no_human_consequence_summary.csv": summary,
        "figure_no_human_consequence_main.csv": figure_source,
        "figure_materials_model_zoo_frontier.csv": model_frontier,
    }
    for name, frame in outputs.items():
        frame.to_csv(root / name, index=False)

    plot_main_figure(figure_source, model_frontier, root / "figure_no_human_consequence_main.pdf")
    plot_model_frontier(model_frontier, root / "figure_materials_model_zoo_frontier.pdf")
    note_path = write_integration_note(root, summary, rows)

    for name, role in [
        ("table_no_human_consequence_summary.csv", "paper_headline_summary"),
        ("figure_no_human_consequence_main.csv", "figure6_source"),
        ("figure_no_human_consequence_main.pdf", "figure6_pdf"),
        ("figure_materials_model_zoo_frontier.csv", "materials_frontier_source"),
        ("figure_materials_model_zoo_frontier.pdf", "materials_frontier_pdf"),
        ("NO_HUMAN_PAPER_INTEGRATION.md", "paper_integration_text"),
    ]:
        artifact = root / name
        write_provenance(artifact.with_suffix(artifact.suffix + ".provenance.json"), artifact, inputs, role)

    update_manifest(root)
    print(
        json.dumps(
            {
                "status": "completed",
                "root": str(root),
                "summary_rows": int(len(summary)),
                "figure_rows": int(len(figure_source)),
                "note": str(note_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
