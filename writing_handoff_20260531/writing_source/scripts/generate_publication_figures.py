from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patheffects as pe
import matplotlib.ticker as mticker
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
import scienceplots  # noqa: F401
import seaborn as sns
from PIL import Image, ImageOps
from figures.style import (
    C,
    COLOR_BASELINE,
    COLOR_GUARDRAIL,
    COLOR_HUMAN_AUDIT,
    COLOR_ORACLE,
    COLOR_PARC_RELEASE,
    COLOR_RAW_TOPK,
    COLOR_REFUSAL,
    COLOR_TARGET,
    TINT_AUDIT,
    TINT_REFUSE_ZONE,
    TINT_RELEASE_OK,
    TINT_UNSAFE,
    apply_nmi_style,
    panel_letter as style_panel_letter,
)


DATA = ROOT / "data"
FIG = ROOT / "figures"


apply_nmi_style(plt, sns)

COLORS = {
    "blue": COLOR_PARC_RELEASE,
    "sky": "#DCE9F4",
    "orange": COLOR_GUARDRAIL,
    "red": COLOR_GUARDRAIL,
    "green": COLOR_PARC_RELEASE,
    "gray": COLOR_REFUSAL,
    "audit": COLOR_HUMAN_AUDIT,
    "dark": COLOR_TARGET,
    "light": "#F3F4F6",
}

CARD_SHADOW = [
    pe.SimplePatchShadow(offset=(1.4, -1.4), shadow_rgbFace=(0.0, 0.0, 0.0), alpha=0.12),
    pe.Normal(),
]
TEXT_HALO = [pe.Stroke(linewidth=2.0, foreground="white", alpha=0.90), pe.Normal()]


def save(fig: plt.Figure, name: str) -> None:
    path = FIG / name
    fig.savefig(path, bbox_inches="tight")
    if path.suffix.lower() == ".pdf":
        fig.savefig(path.with_suffix(".png"), bbox_inches="tight", dpi=600)
    plt.close(fig)


def label_baseline(name: str) -> str:
    return {
        "Raw top-M": "Raw top-M",
        "Fixed score threshold": "Fixed threshold",
        "Per-generator calibrated score threshold": "Calibrated threshold",
        "Split conformal p-value threshold": "Split conformal",
        "Post-filter e-value threshold": "Post-filter e-value",
        "e-BH style selection": "e-BH style",
        "Full PARC": "Full PARC",
        "Oracle true upper bound": "Oracle upper bound",
    }.get(name, name)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    style_panel_letter(ax, label)


def clean_axis(ax: plt.Axes, grid: bool = True) -> None:
    sns.despine(ax=ax)
    ax.minorticks_off()
    if grid:
        ax.grid(True, axis="y", color="#E7E7E7", linewidth=0.35)
    else:
        ax.grid(False)


def add_round_box(
    ax: plt.Axes,
    xy,
    width,
    height,
    text: str = "",
    facecolor: str = "white",
    edgecolor: str = "#333333",
    textcolor: str | None = None,
    fontsize: float = 6.2,
    weight: str = "normal",
    radius: float = 0.035,
    shadow: bool = True,
) -> FancyBboxPatch:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=0.85,
    )
    if shadow:
        box.set_path_effects(CARD_SHADOW)
    ax.add_patch(box)
    if text:
        ax.text(
            xy[0] + width / 2,
            xy[1] + height / 2,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            color=textcolor or edgecolor,
            fontweight=weight,
        )
    return box


def add_box(ax: plt.Axes, xy, width, height, text, color, fontsize=6.1) -> None:
    rect = Rectangle(xy, width, height, facecolor=color, edgecolor="#333333", linewidth=0.7)
    ax.add_patch(rect)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=fontsize)


def add_arrow(ax: plt.Axes, start, end, color="#333333", lw=0.8) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8, lw=lw, color=color))


def _draw_status_card(
    ax: plt.Axes,
    title: str,
    subtitle: str,
    lines: list[str],
    decision: str,
    status: str,
    raw_note: str | None = None,
) -> None:
    """Draw one compact, decision-first certificate card."""
    palette = {
        "release": ("#DCEEF8", COLORS["blue"], "#0B5F89"),
        "diagnostic": ("#E8F3FA", COLORS["blue"], "#0B5F89"),
        "refusal": ("#ECEAF3", COLORS["gray"], "#4F4F5A"),
        "failure": ("#F8EDEA", COLORS["red"], "#7D3429"),
    }
    face, accent, text_color = palette.get(status, ("#F2F2F2", COLORS["gray"], "#333333"))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.add_patch(Rectangle((0.02, 0.04), 0.96, 0.92, facecolor=face, edgecolor="#C8C8C8", lw=0.45))
    ax.plot([0.045, 0.045], [0.13, 0.88], color=accent, lw=1.25)
    ax.text(0.08, 0.88, title, fontsize=6.8, fontweight="bold", color="#222222", ha="left", va="top")
    ax.text(0.08, 0.775, subtitle, fontsize=5.25, color="#555555", ha="left", va="top")
    ax.add_patch(Rectangle((0.08, 0.585), 0.86, 0.12, facecolor="white", edgecolor=accent, lw=0.55))
    ax.text(0.51, 0.645, decision, fontsize=5.75, fontweight="bold", color=text_color, ha="center", va="center")
    y = 0.475
    for line in lines[:3]:
        ax.text(0.08, y, line, fontsize=5.55, color="#333333", ha="left", va="top")
        y -= 0.122
    if raw_note:
        ax.text(0.94, 0.88, raw_note, fontsize=5.1, color=COLORS["red"], ha="right", va="top")


def _draw_small_check_panel(ax: plt.Axes, title: str, rows: list[tuple[str, str]], accent: str = COLOR_PARC_RELEASE) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.02, 0.96, title, fontsize=6.7, fontweight="bold", ha="left", va="top")
    y = 0.78
    for label, value in rows:
        ax.add_patch(Rectangle((0.03, y - 0.055), 0.028, 0.028, facecolor=accent, edgecolor=accent, lw=0.4))
        ax.text(0.08, y - 0.040, label, fontsize=5.55, color="#333333", ha="left", va="center")
        ax.text(0.96, y - 0.040, value, fontsize=5.55, color="#333333", ha="right", va="center")
        y -= 0.15


def _matrix_marker(ax: plt.Axes, x: float, y: float, decision: str, size: float, color: str = COLOR_PARC_RELEASE) -> None:
    """Draw compact release/refusal/control marker using the PARC marker contract."""
    if decision == "release":
        ax.scatter([x], [y], s=size, marker="o", facecolors=COLOR_PARC_RELEASE, edgecolors="white", linewidth=0.55, zorder=4)
    elif decision == "refusal":
        ax.scatter([x], [y], s=size, marker="o", facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=1.05, zorder=4)
    elif decision == "boundary":
        ax.scatter([x], [y], s=size, marker="^", facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=0.95, zorder=4)
    else:
        ax.scatter([x], [y], s=size, marker="^", facecolors=COLOR_GUARDRAIL, edgecolors=COLOR_GUARDRAIL, linewidth=0.7, zorder=4)


def plot_primary_certificate_matrix() -> None:
    """Money figure: reported releases dominate; counterfactual failures recede."""
    domains = ["CTC", "Materials", "iWildCam", "SpaceNet 7"]
    roles = ["Reported endpoint", "Boundary request", "Destroyed evidence"]
    entries = {
        ("CTC", "Reported endpoint"): dict(decision="release", release=100, realized="0.000", raw=None, evidence=1.34, tag="20/20"),
        ("Materials", "Reported endpoint"): dict(decision="release", release=100, realized="0.030", raw=None, evidence=1.34, tag="20/20"),
        ("iWildCam", "Reported endpoint"): dict(decision="release", release=50, realized="0.000", raw=None, evidence=1.29, tag="20/20"),
        ("SpaceNet 7", "Reported endpoint"): dict(decision="release", release=44, realized="0.000", raw=None, evidence=1.16, tag="18/20"),
        ("CTC", "Boundary request"): dict(decision="refusal", release=0, realized=None, raw="0.361", raw_value=0.361, evidence=0.28, tag="K=5000"),
        ("Materials", "Boundary request"): dict(decision="refusal", release=0, realized=None, raw="0.407", raw_value=0.407, evidence=0.28, tag="K=5000"),
        ("iWildCam", "Boundary request"): dict(decision="refusal", release=0, realized=None, raw="strict", raw_value=0.00, evidence=0.62, tag="a=.10"),
        ("SpaceNet 7", "Boundary request"): dict(decision="refusal", release=0, realized=None, raw="K100", raw_value=0.00, evidence=0.64, tag="K=100"),
        ("CTC", "Destroyed evidence"): dict(decision="control", release=0, realized=None, raw="0.808", raw_value=0.808, evidence=0.00, tag="random"),
        ("Materials", "Destroyed evidence"): dict(decision="control", release=0, realized=None, raw="0.855", raw_value=0.855, evidence=0.00, tag="random"),
        ("iWildCam", "Destroyed evidence"): dict(decision="boundary", release=0, realized=None, raw="semantic", raw_value=0.00, evidence=0.00, tag="species"),
        ("SpaceNet 7", "Destroyed evidence"): dict(decision="control", release=0, realized=None, raw="0.658", raw_value=0.658, evidence=0.00, tag="random"),
    }
    fig, ax = plt.subplots(figsize=(7.2, 2.65))
    ax.set_xlim(-0.65, len(roles) - 0.22)
    ax.set_ylim(len(domains) - 0.34, -0.78)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for j, role in enumerate(roles):
        ax.text(j, -0.50, role, ha="center", va="bottom", fontsize=7.0, color=COLOR_TARGET, fontweight="bold")
    for i, domain in enumerate(domains):
        ax.text(-0.54, i, domain, ha="right", va="center", fontsize=7.0, color=COLOR_TARGET, fontweight="bold")
    for i in range(len(domains)):
        for j in range(len(roles)):
            face = "#F8FAFC" if j == 0 else "white"
            ax.add_patch(Rectangle((j - 0.44, i - 0.34), 0.88, 0.68, facecolor=face, edgecolor="#E0E0E0", lw=0.45, zorder=0))

    for i, d in enumerate(domains):
        for j, r in enumerate(roles):
            e = entries[(d, r)]
            size = 62 if e["decision"] != "release" else 132
            _matrix_marker(ax, j, i - 0.03, e["decision"], size)
            if e["realized"] is not None:
                ax.text(j, i + 0.25, e["realized"], ha="center", va="center", fontsize=6.5, color=COLOR_PARC_RELEASE, fontweight="bold")
                # Micro evidence bar: observed max-e/mass margin relative to the
                # self-consistency boundary.  It adds within-cell density without
                # letting a failure channel dominate the reported endpoint.
                track_x0, track_y = j - 0.27, i + 0.105
                ax.plot([track_x0, track_x0 + 0.54], [track_y, track_y], color="#DDE3EA", lw=2.0, solid_capstyle="butt", zorder=1)
                ax.plot(
                    [track_x0, track_x0 + 0.54 * min(float(e["evidence"]) / 1.5, 1.0)],
                    [track_y, track_y],
                    color=COLOR_PARC_RELEASE,
                    lw=2.0,
                    solid_capstyle="butt",
                    zorder=2,
                )
                ax.text(j - 0.27, i + 0.165, f"e/req {float(e['evidence']):.2f}", ha="left", va="center", fontsize=4.9, color="#5B6670")
                ax.text(j + 0.25, i - 0.245, e["tag"], ha="right", va="center", fontsize=4.9, color="#5B6670")
            if e["raw"] is not None:
                if isinstance(e.get("raw_value"), (float, int)) and e["raw_value"] > 0:
                    bx, by = j + 0.115, i + 0.205
                    ax.plot([bx, bx + 0.27], [by, by], color="#E5E5E5", lw=2.0, solid_capstyle="butt")
                    ax.plot([bx, bx + 0.27 * min(float(e["raw_value"]) / 0.90, 1.0)], [by, by], color=COLOR_BASELINE, lw=2.0, solid_capstyle="butt")
                ax.text(j + 0.11, i + 0.115, e["raw"], ha="left", va="center", fontsize=5.7, color="#6F6F6F")
                ax.text(j - 0.25, i - 0.245, e["tag"], ha="left", va="center", fontsize=4.9, color="#6F6F6F")

    ax.set_xticks([])
    ax.set_yticks([])
    legend_y = len(domains) - 0.02
    legend_items = [("release", "certified release"), ("refusal", "certified refusal"), ("control", "unsafe-source control")]
    for k, (decision, label) in enumerate(legend_items):
        x = -0.12 + k * 0.70
        _matrix_marker(ax, x, legend_y, decision, 58)
        ax.text(x + 0.12, legend_y, label, fontsize=6.0, ha="left", va="center", color=COLOR_TARGET)
    ax.plot([2.08, 2.32], [legend_y, legend_y], color=COLOR_BASELINE, lw=2.0, solid_capstyle="butt")
    ax.text(2.37, legend_y, "gray mini-bar = counterfactual raw FTR", fontsize=6.0, ha="left", va="center", color="#666666")
    save(fig, "figure_2_primary_certificate_matrix.pdf")
    print("Figure 2 self-check: most salient mark is the large filled PARC-primary certified-release circle in the reported-endpoint column.")


def plot_strict_scientific_flagships() -> None:
    """Two strict alpha=0.10 flagships with uncertainty and raw-release contrasts."""
    ctc = pd.read_csv(DATA / "table_ctc_learned_strict_alpha010_smallK.csv")
    ctc_rev = pd.read_csv(DATA / "table_ctc_learned_reverse_split.csv")
    ctc_rand = pd.read_csv(DATA / "table_ctc_learned_negative_control.csv")
    mat = pd.read_csv(DATA / "table_materials_primary_results.csv")
    mat_modern = pd.read_csv(DATA / "table_materials_modern_model_sensitivity.csv")
    mat_rand = pd.read_csv(DATA / "table_materials_random_score_control.csv")
    prevented = pd.read_csv(DATA / "table_prevented_false_releases.csv")

    ctc = ctc[(ctc["rho"].eq(0.10)) & (ctc["alpha"].eq(0.10))].sort_values("M")
    ctc_rev = ctc_rev[(ctc_rev["rho"].eq(0.10)) & (ctc_rev["alpha"].eq(0.10))].sort_values("M")
    ctc_rand = ctc_rand[(ctc_rand["rho"].eq(0.10)) & (ctc_rand["alpha"].eq(0.10))].sort_values("M")
    mat = mat[(mat["rho"].eq(0.10)) & (mat["alpha"].eq(0.10)) & (mat["K"].isin([50, 100, 300, 500, 1000, 5000]))].sort_values("K")
    mat_modern = mat_modern[(mat_modern["alpha"].eq(0.10)) & (mat_modern["K"].isin([300, 500]))].sort_values("K")
    mat_rand = mat_rand[(mat_rand["alpha"].eq(0.10)) & (mat_rand["K"].isin([300, 1000]))].sort_values("K")

    fig = plt.figure(figsize=(7.2, 3.75))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.28, 1.0, 1.0], left=0.080, right=0.985, bottom=0.115, top=0.960, hspace=0.36, wspace=0.48)

    # a, Hero panel: modern materials source, raw versus PARC.
    ax = fig.add_subplot(gs[:, 0])
    add_panel_label(ax, "a")
    xpos = np.arange(len(mat_modern))
    width = 0.34
    ax.bar(xpos - width / 2, mat_modern["raw_topK_actual_FTR_mean"], width=width, color=COLOR_BASELINE, label="raw top-K")
    ax.bar(xpos + width / 2, mat_modern["actual_FTR_mean"], width=width, color=COLOR_PARC_RELEASE, label="PARC")
    ax.errorbar(
        xpos + width / 2,
        mat_modern["actual_FTR_mean"],
        yerr=[
            mat_modern["actual_FTR_mean"] - mat_modern["actual_FTR_bootstrap95_low"],
            mat_modern["actual_FTR_bootstrap95_high"] - mat_modern["actual_FTR_mean"],
        ],
        fmt="none",
        ecolor=COLOR_TARGET,
        elinewidth=0.65,
        capsize=2,
        zorder=4,
    )
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.70, ls=(0, (3, 2)))
    ax.text(1.50, 0.105, "alpha=0.10", fontsize=6.0, color=COLOR_TARGET, ha="right", va="bottom")
    ax.set_xticks(xpos)
    ax.set_xticklabels([f"K={int(k)}" for k in mat_modern["K"]])
    ax.set_ylim(0, 0.36)
    ax.set_ylabel("FTR")
    ax.legend(loc="upper left", fontsize=6.0, handlelength=1.0)
    clean_axis(ax)

    # b, Release volume at strict alpha.
    ax = fig.add_subplot(gs[0, 1])
    add_panel_label(ax, "b")
    mat_small = mat[mat["K"].le(1000)]
    x_ctc = np.log10(ctc["M"].to_numpy())
    x_ctc_rev = np.log10(ctc_rev["M"].to_numpy())
    x_mat = np.log10(mat_small["K"].to_numpy())
    ax.plot(x_ctc, ctc["released_mean"], marker="o", color=COLOR_PARC_RELEASE, lw=1.0, label="CTC")
    ax.plot(x_ctc_rev, ctc_rev["released_mean"], marker="o", mfc="white", mec=COLOR_PARC_RELEASE, color=COLOR_PARC_RELEASE, lw=0.8, alpha=0.9, label="CTC reverse")
    ax.plot(x_mat, mat_small["mean_release"], marker="s", color=COLOR_PARC_RELEASE, lw=0.9, ls=(0, (2, 1)), label="CGCNN")
    ax.set_ylabel("Mean release")
    ax.set_xticks(np.log10([10, 50, 100, 300, 1000]))
    ax.set_xticklabels(["10", "50", "100", "300", "1000"])
    ax.set_ylim(-4, 325)
    ax.legend(loc="upper left", fontsize=5.3, handlelength=1.0)
    clean_axis(ax)
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.tick_params(axis="x", which="minor", bottom=False, labelbottom=False)

    # c, FTR point estimates with bootstrap intervals.
    ax = fig.add_subplot(gs[0, 2])
    add_panel_label(ax, "c")
    endpoints = [
        ("CTC\nK=100", ctc[ctc["M"].eq(100)].iloc[0], "o"),
        ("CGCNN\nK=100", mat[mat["K"].eq(100)].iloc[0], "s"),
        ("ALIGNN\nK=300", mat_modern[mat_modern["K"].eq(300)].iloc[0], "^"),
        ("ALIGNN\nK=500", mat_modern[mat_modern["K"].eq(500)].iloc[0], "v"),
    ]
    x = np.arange(len(endpoints))
    means = np.array([float(row["actual_FTR_mean"]) for _, row, _ in endpoints])
    lows = np.array([float(row["actual_FTR_bootstrap95_low"]) for _, row, _ in endpoints])
    highs = np.array([float(row["actual_FTR_bootstrap95_high"]) for _, row, _ in endpoints])
    ax.errorbar(x, means, yerr=[means - lows, highs - means], fmt="none", ecolor="#555555", elinewidth=0.7, capsize=2.0, zorder=2)
    for xi, yi, (_, _, marker) in zip(x, means, endpoints):
        ax.scatter([xi], [yi], s=36, marker=marker, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.55, zorder=3)
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.set_xticks(x)
    ax.set_xticklabels([name for name, _, _ in endpoints], fontsize=5.8)
    ax.set_ylabel("Realized FTR")
    ax.set_ylim(-0.006, 0.13)
    clean_axis(ax)

    # d, Evidence mass curves.
    ax = fig.add_subplot(gs[1, 1])
    add_panel_label(ax, "d")
    ax.plot(x_ctc, ctc["best_mass_ratio_mean"], marker="o", color=COLOR_PARC_RELEASE, lw=1.05, label="CTC")
    ax.plot(x_mat, mat_small["best_mass_ratio_mean"], marker="s", color=COLOR_PARC_RELEASE, lw=0.90, ls=(0, (2, 1)), label="CGCNN")
    ax.axhline(1.0, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.set_yscale("log")
    ax.set_xticks(np.log10([10, 50, 100, 300, 1000]))
    ax.set_xticklabels(["10", "50", "100", "300", "1000"])
    ax.set_yticks([1, 10])
    ax.set_yticklabels(["", "10"])
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_ylim(0.6, 20)
    ax.set_xlabel("K")
    ax.set_ylabel("Best mass ratio")
    ax.legend(loc="upper right", fontsize=5.5, handlelength=1.1)
    clean_axis(ax)
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.tick_params(axis="x", which="minor", bottom=False, labelbottom=False)

    # e, Destroyed-ranking controls and unsafe-volume requests in one panel.
    ax = fig.add_subplot(gs[1, 2])
    add_panel_label(ax, "e")
    ctc_raw = float(prevented[prevented["unsafe_request"].astype(str).str.contains("K=5000", na=False)]["raw_topK_FTR"].iloc[0])
    mat_k5000 = mat[mat["K"].eq(5000)].iloc[0]
    labels = ["CTC\nrand100", "Mat.\nrand300", "Mat.\nrand1000", "CTC\nK5000", "Mat.\nK5000"]
    raw = [
        float(ctc_rand[ctc_rand["M"].eq(100)]["raw_topM_actual_FTR_mean"].iloc[0]),
        float(mat_rand[mat_rand["K"].eq(300)]["raw_topK_actual_FTR_mean"].iloc[0]),
        float(mat_rand[mat_rand["K"].eq(1000)]["raw_topK_actual_FTR_mean"].iloc[0]),
        ctc_raw,
        float(mat_k5000["raw_topK_actual_FTR_mean"]),
    ]
    rel_rate = [
        float(ctc_rand[ctc_rand["M"].eq(100)]["nonempty_seeds"].iloc[0]) / 20,
        float(mat_rand[mat_rand["K"].eq(300)]["non_empty_seeds"].iloc[0]) / 20,
        float(mat_rand[mat_rand["K"].eq(1000)]["non_empty_seeds"].iloc[0]) / 20,
        0.0,
        float(mat_k5000["mean_release"]) / 5000.0,
    ]
    xx = np.arange(len(labels))
    ax.bar(xx, raw, color=COLOR_BASELINE, width=0.60, label="counterfactual raw FTR")
    ax.scatter(xx, rel_rate, marker="o", s=38, facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=1.0, zorder=3, label="PARC release rate")
    ax.scatter(xx[:3], np.array(raw[:3]) + 0.035, marker="^", s=28, color=COLOR_GUARDRAIL, zorder=4, label="destroyed ranking")
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.set_xticks(xx)
    ax.set_xticklabels(labels, fontsize=5.2)
    ax.set_ylabel("FTR / release rate")
    ax.set_ylim(0, 0.95)
    ax.legend(loc="upper left", fontsize=5.2, handlelength=1.1)
    clean_axis(ax)

    save(fig, "figure_3_strict_scientific_flagships.pdf")
    print("Figure 3 self-check: largest panel is ALIGNN raw-vs-PARC because it is the clearest empirical lift over raw top-K.")


def _legacy_plot_human_audit_operating_envelopes() -> None:
    """Human-audited release/refusal envelope for iWildCam and SpaceNet."""
    iw = pd.read_csv(DATA / "table_iwildcam_human_audit_primary_results.csv")
    iw_counts = pd.read_csv(DATA / "table_iwildcam_calibration_label_counts.csv")
    iw_rel = pd.read_csv(DATA / "table_iwildcam_release_audit_summary.csv").iloc[0]
    iw_second = pd.read_csv(DATA / "table_iwildcam_second_review_agreement_summary.csv")
    sp_cal = pd.read_csv(DATA / "table_spacenet7_real_audit_calibration_summary.csv").iloc[0]
    sp_k100 = pd.read_csv(DATA / "table_spacenet7_real_audit_k100_failure_summary.csv").iloc[0]
    sp_k50 = pd.read_csv(DATA / "table_spacenet7_real_audit_k50_completed_summary.csv").iloc[0]
    sp_rel = pd.read_csv(DATA / "table_spacenet7_real_audit_k50_release_audit.csv").iloc[0]
    sp_raw = pd.read_csv(DATA / "table_spacenet7_real_audit_raw_topK_audit.csv").iloc[0]

    fig = plt.figure(figsize=(7.2, 4.35))
    gs = fig.add_gridspec(2, 4, left=0.075, right=0.985, bottom=0.100, top=0.875, hspace=0.58, wspace=0.56)
    axes = [[fig.add_subplot(gs[i, j]) for j in range(4)] for i in range(2)]

    # a, Calibration audit composition.
    ax = axes[0][0]
    add_panel_label(ax, "a")
    animal = int(iw_counts[iw_counts["human_label"].eq("animal")]["count"].iloc[0])
    not_animal = int(iw_counts[iw_counts["human_label"].eq("not_animal")]["count"].iloc[0])
    ax.bar([0], [animal], color=COLOR_HUMAN_AUDIT, width=0.48)
    ax.bar([0], [not_animal], bottom=[animal], color="#D6D6D6", width=0.48)
    ax.text(0, animal / 2, "1414\nanimal", ha="center", va="center", fontsize=5.6, color="white", fontweight="bold")
    ax.text(0, animal + not_animal / 2, "586\nnot animal", ha="center", va="center", fontsize=5.6)
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(0, 2050)
    ax.set_xticks([0])
    ax.set_xticklabels(["calibration"])
    ax.set_ylabel("Audited candidates")
    ax.set_title("Calibration audit")
    clean_axis(ax)

    ax = axes[1][0]
    true = int(sp_cal["n_true_same_building"])
    false = int(sp_cal["n_false_link"])
    ax.bar([0], [true], color=COLOR_HUMAN_AUDIT, width=0.48)
    ax.bar([0], [false], bottom=[true], color=COLOR_RAW_TOPK, width=0.48)
    ax.text(0, true / 2, "796 true", ha="center", va="center", fontsize=5.6, color="white", fontweight="bold")
    ax.text(0, true + false + 30, "4 false", ha="center", va="bottom", fontsize=5.4, color=COLOR_RAW_TOPK)
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(0, 850)
    ax.set_xticks([0])
    ax.set_xticklabels(["calibration"])
    ax.set_ylabel("Audited links")
    clean_axis(ax)

    # b, Release/refusal grids.
    ax = axes[0][1]
    add_panel_label(ax, "a")
    sub = iw[iw["K"].isin([25, 50, 100])].copy()
    sub["_order"] = sub.apply(lambda r: [(0.1, 25), (0.1, 50), (0.1, 100), (0.2, 25), (0.2, 50), (0.2, 100)].index((float(r["alpha"]), int(r["K"]))), axis=1)
    sub = sub.sort_values("_order")
    colors = [COLOR_REFUSAL if float(a) == 0.1 else COLOR_HUMAN_AUDIT for a in sub["alpha"]]
    x_grid = np.array([0, 1, 2, 3.7, 4.7, 5.7])
    ax.bar(x_grid, sub["mean_release"], color=colors, width=0.58)
    ax.axvline(2.85, color="#CFCFCF", lw=0.5)
    ax.set_xlim(-0.7, 6.4)
    ax.set_xticks(x_grid)
    ax.set_xticklabels([str(int(k)) for k in sub["K"]], fontsize=5.4)
    ax.set_xlabel("K", labelpad=1)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Mean release")
    ax.set_title("Risk endpoint grid")
    ax.text(1.0, 98, "alpha=.10", ha="center", va="top", fontsize=5.5, color=COLOR_REFUSAL)
    ax.text(4.7, 98, "alpha=.20", ha="center", va="top", fontsize=5.5, color=COLOR_HUMAN_AUDIT)
    clean_axis(ax)

    ax = axes[1][1]
    vals = [0, float(sp_k50["mean_release_across_seeds"])]
    ax.bar([0, 1], vals, color=[COLOR_REFUSAL, COLOR_HUMAN_AUDIT], width=0.55)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["K=100\nrefuse", "K=50\nrelease"], fontsize=5.5)
    ax.set_ylim(0, 55)
    ax.set_ylabel("Mean release")
    clean_axis(ax)

    # c, Release-audit confirmation and second-review reliability.
    ax = axes[0][2]
    add_panel_label(ax, "c")
    second_all = iw_second[iw_second["scope"].eq("all_rows")].iloc[0]
    rel_candidates = int(iw_rel["n_audited_unique_released_candidates"])
    ax.bar([0], [rel_candidates], color=COLOR_HUMAN_AUDIT, width=0.52)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["release\n167/167", "second\nreview"], fontsize=5.5)
    ax.set_ylabel("count / agreement")
    ax.set_title("Release audit and second review")
    ax.set_ylim(0, 180)
    ax2 = ax.twinx()
    ax2.bar([1], [float(second_all["label_agreement"])], color="#BFC9D4", width=0.52)
    ax2.errorbar(
        [1],
        [float(second_all["cohen_kappa"])],
        yerr=[
            [float(second_all["cohen_kappa"]) - float(second_all["cohen_kappa_bootstrap95_low"])],
            [float(second_all["cohen_kappa_bootstrap95_high"]) - float(second_all["cohen_kappa"])],
        ],
        fmt="D",
        color=COLOR_PARC_RELEASE,
        ecolor="#444444",
        elinewidth=0.65,
        capsize=2,
        markersize=3.2,
        zorder=4,
    )
    ax2.set_ylim(0, 1.0)
    ax2.set_yticks([0, 0.5, 1.0])
    ax2.tick_params(axis="y", labelsize=5.4, width=0.5, length=2.5)
    sns.despine(ax=ax2, right=False)
    clean_axis(ax)

    ax = axes[1][2]
    ax.bar([0, 1], [int(sp_rel["n_true_same_building"]), int(sp_raw["n_true_same_building"])], color=[COLOR_HUMAN_AUDIT, "#BFC9D4"], width=0.55)
    ax.bar([0, 1], [int(sp_rel["n_false_link"]) + int(sp_rel["n_uncertain"]), int(sp_raw["n_false_link"]) + int(sp_raw["n_uncertain"])], bottom=[int(sp_rel["n_true_same_building"]), int(sp_raw["n_true_same_building"])], color=COLOR_RAW_TOPK, width=0.55)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["K=50\n147/147", "raw\n199/200"], fontsize=5.5)
    ax.set_ylabel("Reviewed")
    ax.set_ylim(0, 225)
    clean_axis(ax)

    # d, Evidence mass explains refusal/release boundary.
    ax = axes[0][3]
    add_panel_label(ax, "d")
    strict = iw[iw["alpha"].eq(0.1)].sort_values("K")
    operational = iw[iw["alpha"].eq(0.2)].sort_values("K")
    x = np.arange(3)
    ax.plot(x, strict["mean_best_mass_ratio"], marker="o", color=COLOR_REFUSAL, lw=1.0, label="alpha=.10")
    ax.plot(x, operational["mean_best_mass_ratio"], marker="o", color=COLOR_HUMAN_AUDIT, lw=1.0, label="alpha=.20")
    ax.axhline(1.0, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(k)) for k in strict["K"]])
    ax.set_xlabel("K")
    ax.set_ylabel("Best mass ratio")
    ax.set_ylim(0, 1.45)
    ax.set_title("Evidence boundary")
    ax.legend(loc="upper left", fontsize=5.3, handlelength=1.1)
    clean_axis(ax)

    ax = axes[1][3]
    vals = [float(sp_k100["mean_best_mass_ratio"]), float(sp_k50["mean_mass_ratio"])]
    ax.bar([0, 1], vals, color=[COLOR_REFUSAL, COLOR_HUMAN_AUDIT], width=0.55)
    ax.axhline(1.0, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["K=100", "K=50"])
    ax.set_ylim(0, 1.35)
    ax.set_ylabel("Mass ratio")
    clean_axis(ax)

    fig.text(0.075, 0.985, "Human-audited operating envelopes", fontsize=8.0, fontweight="bold", ha="left", va="top")
    fig.text(0.435, 0.985, "Audits supply positives, quantify disagreement and expose unsupported release volumes.", fontsize=6.0, color="#555555", ha="left", va="top")
    save(fig, "figure_4_human_audit_operating_envelopes.pdf")


def plot_human_audit_operating_envelopes() -> None:
    """Three-panel human audit envelope: decisions, evidence mass and reliability."""
    iw = pd.read_csv(DATA / "table_iwildcam_human_audit_primary_results.csv")
    iw_rel = pd.read_csv(DATA / "table_iwildcam_release_audit_summary.csv").iloc[0]
    iw_second = pd.read_csv(DATA / "table_iwildcam_second_review_agreement_summary.csv")
    sp_k100 = pd.read_csv(DATA / "table_spacenet7_real_audit_k100_failure_summary.csv").iloc[0]
    sp_k50 = pd.read_csv(DATA / "table_spacenet7_real_audit_k50_completed_summary.csv").iloc[0]
    sp_rel = pd.read_csv(DATA / "table_spacenet7_real_audit_k50_release_audit.csv").iloc[0]

    fig = plt.figure(figsize=(7.2, 2.85))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.2, 1.0], left=0.075, right=0.985, bottom=0.17, top=0.88, wspace=0.42)

    # a, Release/refusal grid.
    ax = fig.add_subplot(gs[0, 0])
    add_panel_label(ax, "a")
    rows = ["iWildCam", "SpaceNet 7"]
    cols = ["strict /\nrequested", "operational /\ndiagnostic"]
    grid = {
        (0, 0): ("refusal", "a=.10", "0/20", 0.62, "mean 0"),
        (0, 1): ("release", "a=.20 K=50", "20/20", 1.29, "mean 50"),
        (1, 0): ("refusal", "K=100", "0/20", 0.64, "mean 0"),
        (1, 1): ("release", "K=50", "18/20", 1.16, "mean 44"),
    }
    ax.set_xlim(-0.55, 1.65)
    ax.set_ylim(1.55, -0.55)
    for i, row in enumerate(rows):
        ax.text(-0.42, i, row, ha="right", va="center", fontsize=7.0, fontweight="bold", color=COLOR_TARGET)
    for j, col in enumerate(cols):
        ax.text(j, -0.40, col, ha="center", va="bottom", fontsize=5.9, color=COLOR_TARGET, linespacing=0.95)
    for i in range(2):
        for j in range(2):
            outcome, label, seeds, mass, mean_txt = grid[(i, j)]
            ax.add_patch(Rectangle((j - 0.34, i - 0.25), 0.68, 0.50, facecolor="#F8FAFC", edgecolor="#E1E1E1", lw=0.45))
            _matrix_marker(ax, j - 0.18, i - 0.04, outcome, 82 if outcome == "release" else 68)
            ax.text(j - 0.03, i - 0.145, label, ha="left", va="center", fontsize=5.5, color=COLOR_TARGET if outcome == "refusal" else COLOR_PARC_RELEASE)
            ax.text(j - 0.03, i - 0.010, seeds, ha="left", va="center", fontsize=5.4, color=COLOR_TARGET)
            ax.text(j - 0.03, i + 0.105, mean_txt, ha="left", va="center", fontsize=5.2, color="#5B6670")
            bx0, by = j - 0.25, i + 0.205
            ax.plot([bx0, bx0 + 0.50], [by, by], color="#DDE3EA", lw=1.7, solid_capstyle="butt")
            ax.plot([bx0, bx0 + 0.50 * min(mass / 1.35, 1.0)], [by, by], color=COLOR_PARC_RELEASE if outcome == "release" else COLOR_REFUSAL, lw=1.7, solid_capstyle="butt")
            ax.text(j + 0.26, by, f"m {mass:.2f}", ha="right", va="center", fontsize=4.8, color="#5B6670")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_axis_off()

    # b, Evidence-mass ratio explains release/refusal.
    ax = fig.add_subplot(gs[0, 1])
    add_panel_label(ax, "b")
    iw_strict = iw[iw["alpha"].eq(0.1)].sort_values("K")
    iw_oper = iw[iw["alpha"].eq(0.2)].sort_values("K")
    x = np.array([0, 1, 2])
    ax.plot(x, iw_strict["mean_best_mass_ratio"], marker="o", mfc="white", mec=COLOR_REFUSAL, color=COLOR_REFUSAL, lw=0.9, label="iWildCam a=.10")
    ax.plot(x, iw_oper["mean_best_mass_ratio"], marker="o", color=COLOR_PARC_RELEASE, lw=0.95, label="iWildCam a=.20")
    ax.scatter([3.55], [float(sp_k100["mean_best_mass_ratio"])], s=56, facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=1.0, label="SpaceNet K=100")
    ax.scatter([4.20], [float(sp_k50["mean_mass_ratio"])], s=68, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.55, label="SpaceNet K=50")
    ax.axhline(1.0, color=COLOR_TARGET, lw=0.70, ls=(0, (3, 2)))
    ax.set_xticks([0, 1, 2, 3.55, 4.20])
    ax.set_xticklabels(["25", "50", "100", "SN\n100", "SN\n50"], fontsize=5.8)
    ax.set_ylabel("Best mass ratio")
    ax.set_ylim(0, 1.45)
    ax.legend(loc="upper left", fontsize=5.2, handlelength=1.0)
    clean_axis(ax)

    # c, Audit reliability without a mixed dual axis.
    ax = fig.add_subplot(gs[0, 2])
    add_panel_label(ax, "c")
    second_all = iw_second[iw_second["scope"].eq("all_rows")].iloc[0]
    values = [
        ("iWildCam\nrelease", 1.0, 0.0, 0.0, "167/167"),
        ("iWildCam\nkappa", float(second_all["cohen_kappa"]), float(second_all["cohen_kappa_bootstrap95_low"]), float(second_all["cohen_kappa_bootstrap95_high"]), "1123 rows"),
        ("SpaceNet\nrelease", 1.0, 0.0, 0.0, "147/147"),
    ]
    xx = np.arange(len(values))
    means = np.array([v[1] for v in values])
    lows = np.array([v[2] for v in values])
    highs = np.array([v[3] for v in values])
    ax.bar(xx, means, color=[COLOR_PARC_RELEASE, COLOR_BASELINE, COLOR_PARC_RELEASE], width=0.66)
    ax.errorbar([1], [means[1]], yerr=[[means[1] - lows[1]], [highs[1] - means[1]]], fmt="none", ecolor=COLOR_TARGET, elinewidth=0.70, capsize=2, zorder=4)
    for xi, (_, _, _, _, label) in zip(xx, values):
        ax.text(xi, min(means[xi] + 0.055, 1.08), label, ha="center", va="bottom", fontsize=5.7, color=COLOR_TARGET)
        ax.text(xi, max(means[xi] - 0.095, 0.055), f"{means[xi]:.3f}", ha="center", va="center", fontsize=5.6, color="white" if means[xi] > 0.88 else COLOR_TARGET, fontweight="bold")
    ax.set_xticks(xx)
    ax.set_xticklabels([v[0] for v in values], fontsize=5.8)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Agreement / confirmation")
    clean_axis(ax)

    save(fig, "figure_4_human_audit_operating_envelopes.pdf")


def plot_parc_overview() -> None:
    """Teaser: real candidate units plus the release/refusal interface."""
    assets = FIG / "figure5_assets"
    material_thumb = FIG / "figure1_assets" / "materials_cloud_wbm" / "wbm_crystal_thumbnail.png"
    fig = plt.figure(figsize=(7.2, 3.05))
    gs = fig.add_gridspec(
        2,
        4,
        width_ratios=[1.0, 1.0, 1.18, 1.18],
        left=0.035,
        right=0.985,
        bottom=0.08,
        top=0.94,
        wspace=0.18,
        hspace=0.18,
    )

    image_axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
    ]
    ax_flow = fig.add_subplot(gs[:, 2:])
    for ax in image_axes:
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

    # a, Real candidate units.
    add_panel_label(image_axes[0], "a")

    ctc_t = mpimg.imread(assets / "ctc_release_frame_t.png")
    ctc_tp1 = mpimg.imread(assets / "ctc_release_frame_tp1.png")
    ctc_meta = json.loads((assets / "ctc_release_link.json").read_text())
    ax = image_axes[0]
    ax.imshow(ctc_t, cmap="gray", extent=(0.00, 0.485, 0.08, 0.96), origin="upper")
    ax.imshow(ctc_tp1, cmap="gray", extent=(0.515, 1.00, 0.08, 0.96), origin="upper")
    h, w = ctc_t.shape[:2]
    p0 = (0.485 * ctc_meta["cell_t"][0] / w, 0.96 - 0.88 * ctc_meta["cell_t"][1] / h)
    p1 = (0.515 + 0.485 * ctc_meta["cell_tp1"][0] / w, 0.96 - 0.88 * ctc_meta["cell_tp1"][1] / h)
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=COLOR_PARC_RELEASE, lw=1.0)
    for p in [p0, p1]:
        ax.add_patch(Circle(p, 0.035, facecolor="none", edgecolor=COLOR_PARC_RELEASE, lw=1.0))
    ax.text(0.04, 0.90, "t", fontsize=6, color="white", ha="left", va="top", path_effects=TEXT_HALO)
    ax.text(0.56, 0.90, "t+1", fontsize=6, color="white", ha="left", va="top", path_effects=TEXT_HALO)
    ax.text(0.00, 0.00, "CTC cell link", fontsize=6.4, color=COLOR_TARGET, ha="left", va="bottom")

    ax = image_axes[1]
    ax.imshow(mpimg.imread(material_thumb), extent=(0.05, 0.95, 0.08, 0.96), origin="upper")
    ax.text(0.00, 0.00, "WBM crystal candidate", fontsize=6.4, color=COLOR_TARGET, ha="left", va="bottom")

    sp_t1 = mpimg.imread(assets / "spacenet_release_t1.png")
    sp_t2 = mpimg.imread(assets / "spacenet_release_t2.png")
    sp_meta = json.loads((assets / "spacenet_release_polygons.json").read_text())
    ax = image_axes[2]
    ax.imshow(sp_t1, extent=(0.00, 0.485, 0.08, 0.96), origin="upper")
    ax.imshow(sp_t2, extent=(0.515, 1.00, 0.08, 0.96), origin="upper")
    h, w = sp_t1.shape[:2]

    def transform_poly(poly, x0):
        arr = np.array(poly, dtype=float)
        xs = x0 + 0.485 * arr[:, 0] / w
        ys = 0.96 - 0.88 * arr[:, 1] / h
        return np.c_[xs, ys]

    poly0 = transform_poly(sp_meta["released"]["t1"], 0.0)
    poly1 = transform_poly(sp_meta["released"]["t2"], 0.515)
    for poly in [poly0, poly1]:
        ax.add_patch(Polygon(poly, closed=True, fill=False, edgecolor=COLOR_PARC_RELEASE, lw=1.0))
    c0, c1 = poly0.mean(axis=0), poly1.mean(axis=0)
    ax.plot([c0[0], c1[0]], [c0[1], c1[1]], color=COLOR_PARC_RELEASE, lw=0.9)
    ax.text(0.00, 0.00, "SpaceNet building link", fontsize=6.4, color=COLOR_TARGET, ha="left", va="bottom")

    ax = image_axes[3]
    iw_img = mpimg.imread(assets / "camera_trap_animal_present.png")
    # Remove the trail-camera vendor strip from the illustrative public-domain
    # fallback crop; the released unit is the animal-present box, not the device.
    iw_img = iw_img[:-22, ...]
    iw_meta = json.loads((assets / "camera_trap_boxes.json").read_text())["animal_present"]["box"]
    ax.imshow(iw_img, extent=(0.02, 0.98, 0.08, 0.96), origin="upper")
    h, w = iw_img.shape[:2]
    x0, y0, x1, y1 = iw_meta
    rect_xy = (0.02 + 0.96 * x0 / w, 0.96 - 0.88 * y1 / h)
    rect_w = 0.96 * (x1 - x0) / w
    rect_h = 0.88 * (y1 - y0) / h
    ax.add_patch(Rectangle(rect_xy, rect_w, rect_h, facecolor="none", edgecolor=COLOR_PARC_RELEASE, lw=1.0))
    ax.text(0.00, 0.00, "iWildCam animal box", fontsize=6.4, color=COLOR_TARGET, ha="left", va="bottom")

    # b, PARC decision flow.
    ax_flow.set_axis_off()
    ax_flow.set_xlim(0, 1)
    ax_flow.set_ylim(0, 1)
    add_panel_label(ax_flow, "b")
    xs = [0.095, 0.335, 0.575, 0.815]
    labels = [
        ("Frozen\nunits", "finite candidates"),
        ("One-sided\nsupport", "remove verified +"),
        ("Null\nblocks", "maxima -> e-values"),
        ("SCS\ntest", "e >= K/(alpha |R|)"),
    ]
    for idx, (x, (head, sub)) in enumerate(zip(xs, labels)):
        ax_flow.add_patch(Rectangle((x - 0.082, 0.55), 0.164, 0.165, facecolor="white", edgecolor="#B8C0C8", lw=0.65))
        ax_flow.text(x, 0.672, head, ha="center", va="center", fontsize=5.7, fontweight="bold", color=COLOR_TARGET, linespacing=0.92)
        ax_flow.text(x, 0.585, sub, ha="center", va="center", fontsize=4.7, color="#5A5A5A")
        if idx < len(xs) - 1:
            add_arrow(ax_flow, (x + 0.090, 0.635), (xs[idx + 1] - 0.090, 0.635), color="#666666", lw=0.7)

    # Minimal data glyphs inside stages, using the global marker contract.
    rng = np.random.default_rng(4)
    for dx, dy in rng.uniform(-0.045, 0.045, (14, 2)):
        ax_flow.scatter(0.10 + dx, 0.36 + dy, s=18, color=COLOR_BASELINE, edgecolor="white", linewidth=0.25)
    for dy in [0.32, 0.37, 0.42]:
        ax_flow.scatter([0.33 - 0.035], [dy], s=28, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.35)
    ax_flow.plot([0.33 - 0.060, 0.33 - 0.010], [0.295, 0.445], color=COLOR_PARC_RELEASE, lw=1.0)
    for b, height in enumerate([0.040, 0.065, 0.030]):
        x0 = 0.505 + b * 0.040
        ax_flow.add_patch(Rectangle((x0, 0.295), 0.030, 0.135, facecolor="#F5F6F7", edgecolor="#C7CCD2", lw=0.45))
        ax_flow.hlines(0.315 + height, x0 + 0.004, x0 + 0.026, color=COLOR_GUARDRAIL, lw=0.85)
    ax_flow.hlines(0.365, 0.735, 0.845, color=COLOR_TARGET, lw=0.70, ls=(0, (3, 2)))
    ax_flow.scatter([0.755, 0.785], [0.420, 0.398], s=30, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.35)
    ax_flow.scatter([0.815], [0.315], s=30, facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=0.9)

    # Reported-output mockup: the figure ends with the object PARC returns.
    tx, ty, tw, th = 0.505, 0.060, 0.465, 0.270
    ax_flow.add_patch(Rectangle((tx, ty), tw, th, facecolor="white", edgecolor="#AEB7C0", lw=0.65))
    header_h = 0.050
    ax_flow.add_patch(Rectangle((tx, ty + th - header_h), tw, header_h, facecolor="#F4F6F8", edgecolor="#AEB7C0", lw=0.45))
    cols = [0.015, 0.245, 0.415, 0.645, 0.830]
    headers = ["domain", "K", "decision", "FTR"]
    for cx, htxt in zip(cols, headers):
        ax_flow.text(tx + tw * cx, ty + th - 0.025, htxt, fontsize=4.7, fontweight="bold", color=COLOR_TARGET, ha="left", va="center")
    rows = [
        ("CTC", "100", "release", "0.000"),
        ("WBM", "100", "release", "0.030"),
        ("iWild", "100", "refuse", "--"),
        ("SN7", "50", "release", "0.000"),
    ]
    row_h = (th - header_h) / len(rows)
    for r, (dom, kval, decision, ftr) in enumerate(rows):
        y0 = ty + th - header_h - (r + 1) * row_h
        fill = "#F8FBFD" if decision == "release" else "#F5F5F5"
        ax_flow.add_patch(Rectangle((tx, y0), tw, row_h, facecolor=fill, edgecolor="#E1E5EA", lw=0.35))
        yc = y0 + row_h / 2
        ax_flow.text(tx + tw * cols[0], yc, dom, fontsize=4.9, color=COLOR_TARGET, ha="left", va="center")
        ax_flow.text(tx + tw * cols[1], yc, kval, fontsize=4.9, color=COLOR_TARGET, ha="left", va="center")
        if decision == "release":
            ax_flow.scatter([tx + tw * cols[2]], [yc], s=22, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.35, zorder=5)
            ax_flow.text(tx + tw * (cols[2] + 0.045), yc, "release", fontsize=4.9, color=COLOR_PARC_RELEASE, fontweight="bold", ha="left", va="center")
        else:
            ax_flow.scatter([tx + tw * cols[2]], [yc], s=22, facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=0.85, zorder=5)
            ax_flow.text(tx + tw * (cols[2] + 0.045), yc, "refuse", fontsize=4.9, color=COLOR_REFUSAL, fontweight="bold", ha="left", va="center")
        ax_flow.text(tx + tw * cols[3], yc, ftr, fontsize=4.9, color=COLOR_TARGET, ha="left", va="center")
    add_arrow(ax_flow, (0.79, 0.55), (tx + 0.08, ty + th + 0.012), color="#666666", lw=0.65)

    save(fig, "figure_1_pipeline_parc.pdf")


def plot_cross_domain_certification_atlas() -> None:
    """Main-text evidence atlas: domains, scale, releases, audits and controls."""
    cross = pd.read_csv(DATA / "table_main_cross_domain_results.csv")
    ctc = pd.read_csv(DATA / "table_ctc_learned_strict_alpha010_smallK.csv")
    materials = pd.read_csv(DATA / "table_materials_primary_results.csv")
    materials_modern = pd.read_csv(DATA / "table_materials_modern_model_sensitivity.csv")
    iwild = pd.read_csv(DATA / "table_iwildcam_human_audit_primary_results.csv")
    cal = pd.read_csv(DATA / "table_iwildcam_calibration_audit_summary.csv").iloc[0]
    rel = pd.read_csv(DATA / "table_iwildcam_release_audit_summary.csv").iloc[0]
    second = pd.read_csv(DATA / "table_iwildcam_second_review_agreement_summary.csv")
    second_all = second[second["scope"].eq("all_rows")].iloc[0]
    sp_k50 = pd.read_csv(DATA / "table_spacenet7_real_audit_k50_completed_summary.csv").iloc[0]
    sp_k100 = pd.read_csv(DATA / "table_spacenet7_real_audit_k100_failure_summary.csv").iloc[0]
    ow = pd.read_csv(DATA / "table_main_raw_vs_parc_summary.csv")


    def atlas_panel_label(ax: plt.Axes, label: str) -> None:
        ax.text(
            -0.20,
            1.12,
            label,
            transform=ax.transAxes,
            fontsize=8.0,
            fontweight="bold",
            va="top",
            ha="left",
        )

    fig = plt.figure(figsize=(7.2, 5.85))
    gs = fig.add_gridspec(3, 4, wspace=0.55, hspace=0.72)
    axes = [fig.add_subplot(gs[i, j]) for i in range(3) for j in range(4)]

    # a, Domain/source map.
    ax = axes[0]
    atlas_panel_label(ax, "a")
    ax.set_axis_off()
    ax.set_title("Evidence layers", fontsize=7.2, pad=2)
    layers = [
        ("CTC", "strict learned release"),
        ("Materials", "strict release"),
        ("iWildCam", "human-audited release"),
        ("SpaceNet 7", "audit/refusal check"),
        ("OVT/BURST/TAO/LVIS", "breadth/stress rows"),
    ]
    y = 0.82
    for idx, (domain, role) in enumerate(layers):
        color = COLORS["blue"] if idx < 2 else ("#4B5563" if idx < 4 else "#8A8A8A")
        ax.plot([0.06, 0.15], [y, y], color=color, lw=2.2, solid_capstyle="butt", transform=ax.transAxes)
        ax.text(0.18, y + 0.025, domain, fontsize=5.8, fontweight="bold", va="center", transform=ax.transAxes)
        ax.text(0.18, y - 0.045, role, fontsize=5.1, va="center", color="#444444", transform=ax.transAxes)
        y -= 0.16

    # b, Scale.
    ax = axes[1]
    atlas_panel_label(ax, "b")
    scale_names = ["iWildCam\naudit", "CTC\nlinks", "WBM\ncrystals", "SpaceNet\nlinks"]
    scale_vals = np.array([2000, 146230, 215486, 6341788], dtype=float)
    y_pos = np.arange(len(scale_names))
    ax.barh(y_pos, scale_vals, color=["#9AA3AA", COLORS["blue"], COLORS["blue"], "#6B7280"], alpha=0.82)
    ax.set_xscale("log")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(scale_names, fontsize=5.6)
    ax.invert_yaxis()
    ax.set_xlabel("Candidate/audit units")
    ax.set_title("Scale")
    ax.grid(True, axis="x", color="#E7E7E7", linewidth=0.35)
    clean_axis(ax, grid=False)

    # c, Primary realized FTR.
    ax = axes[2]
    atlas_panel_label(ax, "c")
    names = ["CTC", "Materials", "iWildCam", "SpaceNet"]
    ftr = np.array([0.0, 0.030, 0.0, 0.003])
    ax.bar(np.arange(len(names)), ftr, color=[COLORS["blue"], COLORS["blue"], "#4B5563", "#6B7280"], alpha=0.82, width=0.62)
    ax.axhline(0.10, color="#5F6A70", lw=0.6, ls=(0, (3, 2)))
    ax.text(3.45, 0.103, r"$\alpha=0.10$", fontsize=5.2, ha="right", va="bottom", color="#4E5A62")
    ax.set_xticks(np.arange(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=5.6)
    ax.set_ylim(0, 0.12)
    ax.set_ylabel("FTR")
    ax.set_title("Primary risk")
    clean_axis(ax, grid=True)

    # d, Non-empty release rate with mean release labels.
    ax = axes[3]
    atlas_panel_label(ax, "d")
    rates = np.array([1.0, 1.0, 1.0, 17 / 20])
    release_labels = [r"$K\leq300$", "100", "50", "82"]
    ax.bar(np.arange(len(names)), rates, color=[COLORS["blue"], COLORS["blue"], "#4B5563", "#6B7280"], alpha=0.82, width=0.62)
    for xi, ri, lab in zip(np.arange(len(names)), rates, release_labels):
        ax.text(xi, min(ri + 0.035, 1.06), lab, ha="center", va="bottom", fontsize=5.1)
    ax.set_ylim(0, 1.12)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_xticks(np.arange(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=5.6)
    ax.set_ylabel("Non-empty rate")
    ax.set_title("Release stability")
    clean_axis(ax, grid=True)

    # e, Unsafe controls.
    ax = axes[4]
    atlas_panel_label(ax, "e")
    unsafe_names = ["CTC\nrandom", "CTC\nK5000", "Mat.\nrandom", "Mat.\nK5000", "SpaceNet\nrandom"]
    unsafe_raw = np.array([0.785, 0.3606, 0.85, 0.4065, 0.6575])
    ax.bar(np.arange(len(unsafe_names)), unsafe_raw, color="#9A9A9A", alpha=0.74, width=0.62)
    ax.scatter(np.arange(len(unsafe_names)), np.zeros(len(unsafe_names)), marker="D", s=24, color=COLORS["blue"], zorder=3)
    ax.set_ylim(0, 0.92)
    ax.set_xticks(np.arange(len(unsafe_names)))
    ax.set_xticklabels(unsafe_names, fontsize=5.3)
    ax.set_ylabel("Raw FTR")
    ax.set_title("Unsafe raw lists refused")
    ax.text(4.85, 0.82, "PARC release=0", fontsize=5.0, ha="right", color=COLORS["blue"])
    clean_axis(ax, grid=True)

    # f, Evidence mass ratio.
    ax = axes[5]
    atlas_panel_label(ax, "f")
    ratio_names = ["CTC", "Mat.", "iWild\nop.", "Space\nK100", "Space\nK50"]
    ratios = np.array([1.338, 13.44, 1.291, float(sp_k100["mean_best_mass_ratio"]), float(sp_k50["mean_mass_ratio"])])
    colors = [COLORS["blue"], COLORS["blue"], "#4B5563", "#9A9A9A", "#6B7280"]
    ax.bar(np.arange(len(ratio_names)), ratios, color=colors, alpha=0.82, width=0.62)
    ax.axhline(1.0, color="#333333", lw=0.6, ls=(0, (3, 2)))
    ax.set_yscale("log")
    ax.set_ylim(0.45, 18)
    ax.set_xticks(np.arange(len(ratio_names)))
    ax.set_xticklabels(ratio_names, fontsize=5.3)
    ax.set_ylabel("Mass ratio")
    ax.set_title("Self-consistency evidence")
    clean_axis(ax, grid=True)

    # g, CTC strict K sweep.
    ax = axes[6]
    atlas_panel_label(ax, "g")
    ctc_strict = ctc[(ctc["rho"].eq(0.1)) & (ctc["alpha"].eq(0.1))].copy()
    ax.plot(ctc_strict["M"], ctc_strict["released_mean"], marker="o", color=COLORS["blue"], lw=1.0, ms=3)
    ax.plot(ctc_strict["M"], ctc_strict["M"], color="#B8B8B8", lw=0.55, ls=(0, (2, 2)))
    ax.set_xscale("log")
    ax.set_xlabel("K")
    ax.set_ylabel("Released")
    ax.set_title("CTC strict sweep")
    clean_axis(ax, grid=True)

    # h, Materials K sweep.
    ax = axes[7]
    atlas_panel_label(ax, "h")
    mat = materials[(materials["rho"].eq(0.1)) & (materials["alpha"].eq(0.1))].copy()
    ax.plot(mat["K"], mat["mean_release"], marker="o", color=COLORS["blue"], lw=1.0, ms=3, label="PARC release")
    ax2 = ax.twinx()
    ax2.plot(mat["K"], mat["actual_FTR_mean"], marker="s", color="#4B5563", lw=0.8, ms=2.8, label="FTR")
    ax.set_xscale("log")
    ax.set_xlabel("K")
    ax.set_ylabel("Released")
    ax2.set_ylabel("FTR")
    ax.set_title("Materials release boundary")
    ax2.set_ylim(0, 0.13)
    ax2.axhline(0.10, color="#687782", lw=0.5, ls=(0, (3, 2)))
    clean_axis(ax, grid=True)
    sns.despine(ax=ax2, right=False)

    # i, iWildCam strict vs operational.
    ax = axes[8]
    atlas_panel_label(ax, "i")
    iw = iwild[iwild["K"].isin([25, 50, 100])].copy()
    x = np.arange(3)
    strict = iw[iw["alpha"].eq(0.1)].sort_values("K")["mean_release"].to_numpy()
    operational = iw[iw["alpha"].eq(0.2)].sort_values("K")["mean_release"].to_numpy()
    ax.bar(x - 0.16, strict, width=0.32, color="#B0B0B0", label=r"$\alpha=0.10$")
    ax.bar(x + 0.16, operational, width=0.32, color="#4B5563", label=r"$\alpha=0.20$")
    ax.set_xticks(x)
    ax.set_xticklabels(["25", "50", "100"], fontsize=5.5)
    ax.set_xlabel("K")
    ax.set_ylabel("Mean release")
    ax.set_title("iWildCam operating point")
    ax.legend(fontsize=5.0, loc="upper left")
    clean_axis(ax, grid=True)

    # j, SpaceNet human audit.
    ax = axes[9]
    atlas_panel_label(ax, "j")
    ax.bar([0, 1], [0, float(sp_k50["mean_release_across_seeds"])], color=["#B0B0B0", "#6B7280"], width=0.58)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["K100\nrefuse", "K50\nrelease"], fontsize=5.5)
    ax.set_ylabel("Mean release")
    ax.set_title("SpaceNet audit check")
    ax.text(1, float(sp_k50["mean_release_across_seeds"]) + 3, "human FTR 0", ha="center", fontsize=5.0)
    clean_axis(ax, grid=True)

    # k, Human audit/review funnel.
    ax = axes[10]
    atlas_panel_label(ax, "k")
    ax.set_title("Human audit reliability", fontsize=7.2, pad=2)
    ax.set_xlim(0, 2000)
    ax.set_ylim(0, 1)
    ax.barh([0.68], [cal["n_animal"]], height=0.11, color="#4B5563")
    ax.barh([0.68], [cal["n_not_animal"]], left=[cal["n_animal"]], height=0.11, color="#B0B0B0")
    ax.set_axis_off()
    ax.text(0.02, 0.82, "2,000 calibration audit", transform=ax.transAxes, fontsize=5.6, fontweight="bold")
    ax.text(0.02, 0.54, "1,414 animal / 586 not-animal", transform=ax.transAxes, fontsize=5.4)
    ax.text(0.02, 0.34, "release audit: 167/167 animal", transform=ax.transAxes, fontsize=5.4)
    ax.text(0.02, 0.16, rf"second review: agreement {second_all['label_agreement']:.3f}; $\kappa$={second_all['cohen_kappa']:.3f}", transform=ax.transAxes, fontsize=5.4)

    # l, Control matrix.
    ax = axes[11]
    atlas_panel_label(ax, "l")
    ax.set_title("Controls and diagnostics", fontsize=7.2, pad=2)
    rows = ["CTC", "Materials", "iWildCam", "SpaceNet", "Breadth"]
    cols = ["strict\nrelease", "human\naudit", "source\ncontrol", "refusal\ncheck"]
    mat_ctrl = np.array([
        [1, 0, 1, 1],
        [1, 0, 1, 1],
        [0, 1, 1, 1],
        [0, 1, 1, 1],
        [0, 0, 1, 1],
    ])
    cmap = sns.light_palette(COLORS["blue"], as_cmap=True)
    sns.heatmap(mat_ctrl, ax=ax, cmap=cmap, vmin=0, vmax=1, cbar=False, linewidths=0.45, linecolor="white", square=False)
    ax.set_xticks(np.arange(len(cols)) + 0.5)
    ax.set_xticklabels(cols, fontsize=4.8, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(rows)) + 0.5)
    ax.set_yticklabels(rows, fontsize=5.4, rotation=0)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.subplots_adjust(left=0.055, right=0.965, bottom=0.08, top=0.94, wspace=0.58, hspace=0.82)
    save(fig, "figure_2_cross_domain_certification_atlas.pdf")


def plot_risk_utility() -> None:
    df = pd.read_csv(DATA / "table_baseline_comparison_summary.csv")
    main = pd.read_csv(DATA / "table_main_raw_vs_parc_summary.csv")
    fig = plt.figure(figsize=(7.2, 5.55), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, wspace=0.42, hspace=0.46)

    ax = fig.add_subplot(gs[0, 0])
    add_panel_label(ax, "a")
    mat = main.pivot_table(index="dataset", columns="generator", values="parc_released_mean", aggfunc="mean").fillna(0)
    mat = mat.reindex(index=["OVT-B", "TAO", "BURST"])
    mat = mat.rename(columns={
        "GroundingDINO": "GD\nplain",
        "GroundingDINO + tracker": "GD\n+ tracker",
        "GroundingDINO detector-only": "GD\ndetector",
        "OWL-ViT v1": "OWL-ViT",
        "OWLv2": "OWLv2",
    })
    sns.heatmap(mat, ax=ax, cmap="YlGnBu", annot=True, fmt=".0f", linewidths=0.4, linecolor="white", cbar_kws={"label": "PARC release"})
    ax.set_title("Main protocol matrix")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=35, labelsize=5.8)

    ax = fig.add_subplot(gs[0, 1])
    add_panel_label(ax, "b")
    threshold_family = ["Raw top-M", "Fixed score threshold", "Per-generator calibrated score threshold", "Split conformal p-value threshold"]
    thresh = df[df["baseline"].isin(threshold_family)]
    frontier = pd.concat(
        [
            pd.DataFrame(
                [
                    {
                        "label": "Raw / threshold\nfamily",
                        "released_mean": thresh["released_mean"].mean(),
                        "conservative_FTR_mean": thresh["conservative_FTR_mean"].mean(),
                        "marker": "o",
                        "color": COLORS["gray"],
                        "size": 72,
                    }
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "label": label_baseline(r["baseline"]),
                        "released_mean": r["released_mean"],
                        "conservative_FTR_mean": r["conservative_FTR_mean"],
                        "marker": {"Post-filter e-value threshold": "s", "e-BH style selection": "P", "Full PARC": "*", "Oracle true upper bound": "D"}[r["baseline"]],
                        "color": {"Post-filter e-value threshold": COLORS["orange"], "e-BH style selection": "#B8712F", "Full PARC": COLORS["blue"], "Oracle true upper bound": COLORS["green"]}[r["baseline"]],
                        "size": {"Full PARC": 130}.get(r["baseline"], 62),
                    }
                    for _, r in df[df["baseline"].isin(["Post-filter e-value threshold", "e-BH style selection", "Full PARC", "Oracle true upper bound"])].iterrows()
                ]
            ),
        ],
        ignore_index=True,
    )
    for _, r in frontier.iterrows():
        ax.scatter(r["released_mean"], r["conservative_FTR_mean"], s=r["size"], marker=r["marker"], color=r["color"], edgecolor="white", linewidth=0.6)
        dx = -21 if "Raw" in r["label"] else 2.5
        dy = 0.018 if "Full" in r["label"] else 0.0
        ax.text(r["released_mean"] + dx, r["conservative_FTR_mean"] + dy, r["label"], fontsize=5.8, va="center")
    ax.set_xlabel("Mean released paths")
    ax.set_ylabel("Conservative FTR")
    ax.set_title("Risk--utility frontier")
    ax.set_xlim(35, 166)
    ax.set_ylim(-0.035, 0.64)
    ax.grid(True, color="#E6E6E6", linewidth=0.5)

    subgs = gs[1, 0].subgridspec(2, 1, hspace=0.12)
    ax = fig.add_subplot(subgs[0, 0])
    add_panel_label(ax, "c")
    order = ["Raw top-M", "Post-filter e-value threshold", "e-BH style selection", "Full PARC", "Oracle true upper bound"]
    sub = df.set_index("baseline").loc[order].reset_index()
    sub.loc[sub["baseline"].eq("Raw top-M"), "baseline"] = "Raw / threshold family"
    short_labels = {
        "Raw / threshold family": "Raw/thr.",
        "Post-filter e-value threshold": "Post-e",
        "e-BH style selection": "e-BH",
        "Full PARC": "PARC",
        "Oracle true upper bound": "Oracle",
    }
    x = np.arange(len(sub))
    ax.bar(x, sub["released_mean"], width=0.62, color=COLORS["blue"], alpha=0.80)
    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_ylabel("Mean release")
    ax.set_title("Baseline summary")
    ax.set_ylim(0, 165)
    ax.grid(True, axis="y", color="#E6E6E6", linewidth=0.5)
    sns.despine(ax=ax)

    axc2 = fig.add_subplot(subgs[1, 0], sharex=ax)
    axc2.bar(x, sub["conservative_FTR_mean"], width=0.62, color=COLORS["red"], alpha=0.72)
    axc2.set_xticks(x)
    axc2.set_xticklabels([short_labels.get(v, label_baseline(v)) for v in sub["baseline"]], rotation=0, ha="center")
    axc2.set_ylabel("Cons. FTR")
    axc2.set_ylim(0, 0.64)
    axc2.grid(True, axis="y", color="#E6E6E6", linewidth=0.5)
    sns.despine(ax=axc2)

    ax = fig.add_subplot(gs[1, 1])
    add_panel_label(ax, "d")
    paired = main[main["paper_table_scope"].eq("main_protocol_summary")].copy()
    paired = paired.head(8)
    y = np.arange(len(paired))
    for yi, (_, r) in zip(y, paired.iterrows()):
        ax.plot([r["raw_topM_released_mean"], r["parc_released_mean"]], [yi, yi], color="#B9C1CC", lw=1.1)
        ax.scatter([r["raw_topM_released_mean"]], [yi], color=COLORS["gray"], s=24, zorder=3)
        ax.scatter([r["parc_released_mean"]], [yi], color=COLORS["blue"], s=24, zorder=3)
    labels = paired["dataset"].astype(str) + " / " + paired["generator"].astype(str).str.replace("GroundingDINO", "G-DINO", regex=False)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Released paths")
    ax.set_title("Raw top-M to PARC")
    ax.set_xlim(-5, 160)
    ax.grid(True, axis="x", color="#E6E6E6", linewidth=0.5)
    ax.invert_yaxis()

    for ax in [fig.axes[0], fig.axes[1], fig.axes[-1]]:
        sns.despine(ax=ax)
    save(fig, "figure_3_risk_utility_frontier.pdf")


def _legacy_plot_baseline_frontier_inset() -> None:
    """Comparator board: certificate matrix plus risk-utility frontiers."""
    df = pd.read_csv(DATA / "figure_table2b_baseline_frontier.csv")
    seeds = pd.read_csv(DATA / "table_pu_selective_conformal_benchmark_seed_rows.csv")
    df["release_fraction"] = pd.to_numeric(df["mean_release"], errors="coerce") / pd.to_numeric(df["K"], errors="coerce")
    seeds["release_fraction"] = pd.to_numeric(seeds["release_size"], errors="coerce") / pd.to_numeric(seeds["K"], errors="coerce")
    method_style = {
        "Raw top-K source ranking": ("raw", "o", "none", "#A8A8A8", 28),
        "nnPU classifier release": ("nnPU", "s", "none", "#A8A8A8", 32),
        "Bao-style selective conformal adaptation": ("Bao", "^", "none", "#A8A8A8", 36),
        "Bao-style selective conformal oracle-label diagnostic": ("oracle", "o", "none", "#D8A31A", 38),
        "PARC certified release": ("PARC", "D", COLORS["blue"], COLORS["blue"], 70),
    }
    method_x_offsets = {
        "Raw top-K source ranking": -0.020,
        "nnPU classifier release": -0.008,
        "Bao-style selective conformal adaptation": 0.008,
        "Bao-style selective conformal oracle-label diagnostic": 0.020,
        "PARC certified release": 0.000,
    }
    domain_order = [
        ("Biomedical cell tracking", "CTC learned"),
        ("Materials discovery", "Materials"),
        ("Ecological camera traps", "iWildCam"),
    ]
    domain_label = dict(domain_order)
    method_order = [
        "Raw top-K source ranking",
        "nnPU classifier release",
        "Bao-style selective conformal adaptation",
        "Bao-style selective conformal oracle-label diagnostic",
        "PARC certified release",
    ]

    fig = plt.figure(figsize=(7.2, 3.55))
    gs = fig.add_gridspec(
        2,
        1,
        height_ratios=[1.05, 1.05],
        hspace=0.36,
        left=0.070,
        right=0.985,
        bottom=0.095,
        top=0.925,
    )

    ax_matrix = fig.add_subplot(gs[0, 0])
    add_panel_label(ax_matrix, "a")
    ax_matrix.set_axis_off()
    matrix_methods = [
        ("Raw top-K source ranking", "Raw top-K"),
        ("nnPU classifier release", "nnPU"),
        ("Bao-style selective conformal adaptation", "Bao selective"),
        ("Bao-style selective conformal oracle-label diagnostic", "Oracle diagnostic"),
        ("PARC certified release", "PARC"),
    ]
    matrix_domains = [d for d, _ in domain_order]
    ax_matrix.set_xlim(0, 1)
    ax_matrix.set_ylim(0, 1)
    left = 0.255
    top = 0.70
    cell_w = 0.220
    cell_h = 0.135
    ax_matrix.text(0.010, 0.98, "Set-level certificate matrix", fontsize=7.0, fontweight="bold", ha="left", va="top")
    for j, domain in enumerate(matrix_domains):
        ax_matrix.text(left + j * cell_w + cell_w / 2, 0.87, domain_label[domain], fontsize=6.4, fontweight="bold", ha="center", va="bottom")
    for i, (method, label) in enumerate(matrix_methods):
        y = top - i * cell_h
        ax_matrix.text(0.03, y + cell_h / 2, label, fontsize=6.2, ha="left", va="center")
        for j, domain in enumerate(matrix_domains):
            row = df[(df["domain"].eq(domain)) & (df["method"].eq(method))]
            face = "#F1F1F1"
            color = "#555555"
            symbol = "x"
            if not row.empty:
                guarantee = str(row.iloc[0]["set_level_release_guarantee"])
                if guarantee == "yes":
                    face = "#DCEEF8"
                    color = COLORS["blue"]
                    symbol = "rel"
                elif "refusal" in guarantee:
                    face = "#EAF2F8"
                    color = COLORS["blue"]
                    symbol = "ref"
                elif "oracle" in guarantee:
                    face = "#FFF6DD"
                    color = "#B57B00"
                    symbol = "o"
            x = left + j * cell_w
            ax_matrix.add_patch(Rectangle((x, y), cell_w * 0.92, cell_h * 0.86, facecolor=face, edgecolor="#C7C7C7", lw=0.35))
            marker_x = x + cell_w * 0.46
            marker_y = y + cell_h * 0.43
            if symbol == "x":
                ax_matrix.plot([marker_x - 0.018, marker_x + 0.018], [marker_y - 0.018, marker_y + 0.018], color="#888888", lw=0.80)
                ax_matrix.plot([marker_x - 0.018, marker_x + 0.018], [marker_y + 0.018, marker_y - 0.018], color="#888888", lw=0.80)
            elif symbol == "o":
                ax_matrix.scatter([marker_x], [marker_y], s=36, marker="o", facecolors="none", edgecolors="#B57B00", linewidth=0.90)
            elif symbol == "rel":
                ax_matrix.scatter([marker_x], [marker_y], s=38, marker="D", facecolors=COLORS["blue"], edgecolors=COLORS["blue"], linewidth=0.70)
            else:
                ax_matrix.scatter([marker_x], [marker_y], s=38, marker="D", facecolors="white", edgecolors=COLORS["blue"], linewidth=0.95)

    legend_y = 0.045
    legend_items = [
        ("no certificate", "x", "#888888", "#F1F1F1"),
        ("oracle only", "o", "#B57B00", "#FFF6DD"),
        ("certified release", "D", COLORS["blue"], "#DCEEF8"),
        ("certified refusal", "D-open", COLORS["blue"], "#EAF2F8"),
    ]
    lx = 0.255
    for label, symbol, color, face in legend_items:
        ax_matrix.add_patch(Rectangle((lx, legend_y - 0.018), 0.030, 0.036, facecolor=face, edgecolor="#C7C7C7", lw=0.25))
        mx = lx + 0.015
        if symbol == "x":
            ax_matrix.plot([mx - 0.006, mx + 0.006], [legend_y - 0.006, legend_y + 0.006], color=color, lw=0.65)
            ax_matrix.plot([mx - 0.006, mx + 0.006], [legend_y + 0.006, legend_y - 0.006], color=color, lw=0.65)
        elif symbol == "o":
            ax_matrix.scatter([mx], [legend_y], s=18, marker="o", facecolors="none", edgecolors=color, linewidth=0.65)
        elif symbol == "D":
            ax_matrix.scatter([mx], [legend_y], s=18, marker="D", facecolors=color, edgecolors=color, linewidth=0.55)
        else:
            ax_matrix.scatter([mx], [legend_y], s=18, marker="D", facecolors="white", edgecolors=color, linewidth=0.75)
        ax_matrix.text(lx + 0.037, legend_y, label, fontsize=5.4, ha="left", va="center", color="#444444")
        lx += 0.165

    subgs = gs[1, 0].subgridspec(1, 3, wspace=0.24)
    axes = []
    for col, (domain, short) in enumerate(domain_order, start=1):
        ax = fig.add_subplot(subgs[0, col - 1])
        if col == 1:
            add_panel_label(ax, "b")
        axes.append(ax)
        ax.axhspan(0.10, 0.12, color="#F8EDEA", alpha=0.30, zorder=0)
        ax.axhline(0.10, color="#555555", lw=0.55, ls=(0, (3, 2)), zorder=1)
        cloud = seeds[seeds["domain"].eq(domain)].copy()
        for method in method_order[:-1]:
            method_cloud = cloud[cloud["method"].eq(method)].copy()
            if method_cloud.empty:
                continue
            _, marker, face, edge, _ = method_style[method]
            x = method_cloud["release_fraction"].astype(float) + method_x_offsets[method]
            x = x + ((method_cloud["seed"].astype(int) % 5) - 2) * 0.0015
            y = method_cloud["realized_FTR"].astype(float)
            ax.scatter(
                x,
                y,
                s=7,
                marker=marker,
                facecolors=face,
                edgecolors=edge,
                linewidth=0.35,
                alpha=0.20,
                zorder=2,
            )
        sub = df[df["domain"].eq(domain)].copy()
        for method in method_order:
            row = sub[sub["method"].eq(method)]
            if row.empty:
                continue
            label, marker, face, edge, size = method_style[method]
            r = row.iloc[0]
            x = float(r["release_fraction"]) + method_x_offsets[method]
            y = float(r["realized_FTR_mean"])
            is_parc_refusal = method == "PARC certified release" and "refusal" in str(r["set_level_release_guarantee"])
            if is_parc_refusal:
                continue
            ax.scatter(
                [x],
                [y],
                s=size,
                marker=marker,
                facecolors=face,
                edgecolors=edge,
                linewidth=0.75,
                alpha=0.96,
                zorder=4 if method == "PARC certified release" else 3,
            )
        if domain == "Ecological camera traps":
            badge = Rectangle((0.045, 0.013), 0.36, 0.027, facecolor="#EAF2F8", edgecolor=COLORS["blue"], lw=0.55, zorder=4)
            ax.add_patch(badge)
            ax.text(0.225, 0.0265, "refusal", fontsize=5.4, color=COLORS["blue"], ha="center", va="center", zorder=5)
            ax.text(0.61, 0.105, "alpha=0.10", fontsize=5.1, color="#555555", ha="left", va="bottom")
        elif domain == "Materials discovery":
            ax.text(0.73, 0.050, "release", fontsize=5.5, color=COLORS["blue"], ha="left", va="center")
            ax.text(0.08, 0.105, "alpha=0.10", fontsize=5.1, color="#555555", ha="left", va="bottom")
        else:
            ax.text(0.68, 0.018, "release", fontsize=5.5, color=COLORS["blue"], ha="left", va="center")
            ax.text(0.08, 0.105, "alpha=0.10", fontsize=5.1, color="#555555", ha="left", va="bottom")
        ax.set_title({"CTC learned": "CTC", "Materials": "Materials", "iWildCam": "iWildCam"}[short], fontsize=7.0)
        ax.set_xlim(-0.05, 1.07)
        ax.set_ylim(-0.006, 0.120)
        ax.set_xticks([0, 0.5, 1.0])
        ax.set_yticks([0, 0.05, 0.10])
        ax.set_xlabel("")
        if col == 1:
            ax.set_ylabel("Realized FTR")
        else:
            ax.set_yticklabels([])
        clean_axis(ax, grid=True)
    fig.text(0.51, 0.052, "Released fraction of K", fontsize=6.8, ha="center", va="center")

    for ax in axes:
        ax.tick_params(axis="both", pad=1.5)

    fig.text(0.070, 0.985, "Empirical filters versus set-level PARC decisions", fontsize=8.0, fontweight="bold", ha="left", va="top")
    fig.savefig(FIG / "figure_5_certified_decision_board.pdf", bbox_inches="tight")
    fig.savefig(FIG / "figure_baseline_frontier_inset.pdf", bbox_inches="tight")
    plt.close(fig)


def _write_set_level_certificate_table(df: pd.DataFrame) -> None:
    """Write the comparator certificate matrix as a proper LaTeX table body."""
    method_rows = [
        ("Raw top-K source ranking", "Raw top-\\(K\\)"),
        ("nnPU classifier release", "nnPU"),
        ("Bao-style selective conformal adaptation", "Bao selective conformal"),
        ("Bao-style selective conformal oracle-label diagnostic", "Oracle diagnostic"),
        ("PARC certified release", "\\textbf{PARC}"),
    ]
    domains = [
        ("Biomedical cell tracking", "CTC"),
        ("Materials discovery", "Materials"),
        ("Ecological camera traps", "iWildCam"),
    ]

    def cell_text(method: str, domain: str) -> str:
        row = df[(df["method"].eq(method)) & (df["domain"].eq(domain))]
        if row.empty:
            return "--"
        guarantee = str(row.iloc[0]["set_level_release_guarantee"])
        if guarantee == "yes":
            return "certified release"
        if "refusal" in guarantee:
            return "certified refusal"
        if "oracle" in guarantee:
            return "oracle-only (labels unavailable)"
        return "no certificate"

    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{\\textbf{Comparator target objects.} Empirical filters can release individual candidates but do not provide a finite set-level release/refusal certificate under one-sided partial verification. Oracle diagnostics use labels unavailable at deployment.}",
        "\\label{tab:comparatorcertificates}",
        "\\footnotesize",
        "\\begin{tabular}{llll}",
        "\\toprule",
        "Method & CTC & Materials & iWildCam \\\\",
        "\\midrule",
    ]
    for method, label in method_rows:
        values = [cell_text(method, domain) for domain, _ in domains]
        if method == "PARC certified release":
            row = f"\\textbf{{PARC}} & \\textbf{{{values[0]}}} & \\textbf{{{values[1]}}} & \\textbf{{{values[2]}}} \\\\"
        else:
            row = f"{label} & {values[0]} & {values[1]} & {values[2]} \\\\"
        lines.append(row)
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
        "",
    ]
    (ROOT / "table5.tex").write_text("\n".join(lines), encoding="utf-8")


def plot_baseline_frontier_inset() -> None:
    """Single risk-utility frontier plus a LaTeX comparator table."""
    df = pd.read_csv(DATA / "figure_table2b_baseline_frontier.csv")
    seeds = pd.read_csv(DATA / "table_pu_selective_conformal_benchmark_seed_rows.csv")
    _write_set_level_certificate_table(df)

    df["release_fraction"] = pd.to_numeric(df["mean_release"], errors="coerce") / pd.to_numeric(df["K"], errors="coerce")
    seeds["release_fraction"] = pd.to_numeric(seeds["release_size"], errors="coerce") / pd.to_numeric(seeds["K"], errors="coerce")
    domains = [
        ("Biomedical cell tracking", "CTC", "o"),
        ("Materials discovery", "Materials", "s"),
        ("Ecological camera traps", "iWildCam", "^"),
    ]
    comparator_methods = [
        "Raw top-K source ranking",
        "nnPU classifier release",
        "Bao-style selective conformal adaptation",
        "Bao-style selective conformal oracle-label diagnostic",
    ]

    fig, ax = plt.subplots(figsize=(3.55, 2.70))
    ax.axhspan(0.10, 0.125, color=TINT_UNSAFE, alpha=0.55, zorder=0)
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.70, ls=(0, (3, 2)), zorder=1)
    ax.text(0.02, 0.104, "alpha=0.10", fontsize=6.0, color=COLOR_TARGET, ha="left", va="bottom")

    for domain, _, marker in domains:
        cloud = seeds[(seeds["domain"].eq(domain)) & (seeds["method"].isin(comparator_methods))].copy()
        if not cloud.empty:
            jitter = ((cloud["seed"].astype(int) % 7) - 3) * 0.002
            ax.scatter(
                cloud["release_fraction"].astype(float) + jitter,
                cloud["realized_FTR"].astype(float),
                s=7,
                marker=marker,
                facecolors="none",
                edgecolors=COLOR_BASELINE,
                linewidth=0.35,
                alpha=0.22,
                zorder=2,
            )

    for domain, label, marker in domains:
        sub = df[(df["domain"].eq(domain)) & (df["method"].eq("PARC certified release"))]
        if sub.empty:
            continue
        row = sub.iloc[0]
        guarantee = str(row["set_level_release_guarantee"])
        x = float(row["release_fraction"])
        y = float(row["realized_FTR_mean"])
        if "refusal" in guarantee:
            ax.scatter([0.03], [0.012], s=58, marker=marker, facecolors="none", edgecolors=COLOR_REFUSAL, linewidth=1.05, zorder=5)
            ax.text(0.08, 0.012, label, fontsize=6.0, color=COLOR_REFUSAL, ha="left", va="center")
        else:
            ax.scatter([x], [y], s=72, marker=marker, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.60, zorder=5)
            ax.text(min(x + 0.028, 1.02), y + 0.004, label, fontsize=6.0, color=COLOR_PARC_RELEASE, ha="left", va="bottom")

    ax.set_xlim(-0.035, 1.08)
    ax.set_ylim(-0.006, 0.125)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_yticks([0, 0.05, 0.10])
    ax.set_xlabel("Released fraction of K")
    ax.set_ylabel("Realized FTR")
    clean_axis(ax, grid=True)
    save(fig, "figure_5b_risk_utility_frontier.pdf")

    # Backward-compatible filename while the manuscript migrates.
    import shutil

    shutil.copyfile(FIG / "figure_5b_risk_utility_frontier.pdf", FIG / "figure_5_certified_decision_board.pdf")
    shutil.copyfile(FIG / "figure_5b_risk_utility_frontier.png", FIG / "figure_5_certified_decision_board.png")


def plot_safe_refusal() -> None:
    df = pd.read_csv(DATA / "table_safe_refusal_diagnostics.csv")
    rows = df[df["release_feasible"].astype(str).str.lower().eq("false")].copy()
    rows["group"] = rows["dataset"].astype(str) + " / " + rows["generator"].astype(str)
    rows["mass"] = pd.to_numeric(rows["best_mass_ratio"], errors="coerce")
    grouped = (
        rows.dropna(subset=["mass"])
        .groupby("group", as_index=False)["mass"]
        .mean()
        .sort_values("mass")
    )
    grouped = grouped.tail(9)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), gridspec_kw={"width_ratios": [1.2, 1.0]})
    axes = axes.ravel()

    ax = axes[0]
    add_panel_label(ax, "a")
    y = np.arange(len(grouped))
    ax.barh(y, grouped["mass"], color=COLORS["red"], alpha=0.82)
    ax.axvline(1.0, color=COLORS["dark"], linestyle="--", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(grouped["group"].str.replace("GroundingDINO", "G-DINO", regex=False))
    ax.set_xlabel("Best evidence-mass ratio")
    ax.set_title("Below self-consistency threshold")
    ax.set_xlim(0, max(1.08, grouped["mass"].max() * 1.1))
    ax.grid(True, axis="x", color="#E6E6E6", linewidth=0.5)

    ax = axes[1]
    add_panel_label(ax, "b")
    evidence = df.dropna(subset=["max_observed_e", "required_emax"]).copy()
    evidence["group"] = evidence["dataset"].astype(str) + " / " + evidence["generator"].astype(str).str.replace("GroundingDINO", "G-DINO", regex=False) + " s" + evidence["seed"].astype(str)
    evidence = evidence.tail(5)
    x = np.arange(len(evidence))
    ax.bar(x - 0.18, evidence["max_observed_e"], width=0.36, color=COLORS["blue"], alpha=0.78, label="max observed")
    ax.bar(x + 0.18, evidence["required_emax"], width=0.36, color=COLORS["gray"], alpha=0.75, label="required")
    ax.set_xticks(x)
    ax.set_xticklabels(evidence["group"], rotation=35, ha="right")
    ax.set_ylabel("e-value")
    ax.set_title("Observed vs required e")
    ax.legend(fontsize=5.7, loc="upper right")
    ax.grid(True, axis="y", color="#E6E6E6", linewidth=0.5)

    ax = axes[2]
    add_panel_label(ax, "c")
    abl = pd.read_csv(DATA / "table_ablation_components.csv")
    policy = abl[abl["component"].isin(["conservative empty-block only", "coverage-conditional empty-block"])].copy()
    policy["Policy"] = policy["component"].replace(
        {
            "conservative empty-block only": "conservative\n+infinity",
            "coverage-conditional empty-block": "coverage\nconditional",
        }
    )
    policy = policy.groupby("Policy", as_index=False)[["released", "conservative_FTR"]].mean(numeric_only=True)
    order = ["conservative\n+infinity", "coverage\nconditional"]
    policy["Policy"] = pd.Categorical(policy["Policy"], categories=order, ordered=True)
    policy = policy.sort_values("Policy")
    x = np.arange(len(policy))
    ax.bar(x, policy["released"], color=[COLORS["gray"], COLORS["blue"]], alpha=0.82, width=0.58)
    for xi, (_, r) in zip(x, policy.iterrows()):
        ax.text(xi, r["released"] + 3.0, f"FTR {r['conservative_FTR']:.3f}", ha="center", fontsize=5.7)
    ax.set_xticks(x)
    ax.set_xticklabels(policy["Policy"])
    ax.set_ylabel("Mean release")
    ax.set_title("Empty-block policy tradeoff")
    ax.grid(True, axis="y", color="#E6E6E6", linewidth=0.5)

    ax = axes[3]
    add_panel_label(ax, "d")
    reason = rows["safe_refusal_reason"].fillna("unknown")
    reason = reason.replace({"no_k_satisfies_uniform_self_consistency": "No self-consistent\ncertified set"})
    counts = reason.value_counts()
    ax.bar(np.arange(len(counts)), counts.values, color=COLORS["sky"], edgecolor="white", linewidth=0.4)
    ax.set_xticks(np.arange(len(counts)))
    ax.set_xticklabels(counts.index, rotation=0, ha="center")
    ax.set_ylabel("Rows")
    ax.set_title("Refusal reason")
    ax.grid(True, axis="y", color="#E6E6E6", linewidth=0.5)
    sns.despine(fig=fig)
    fig.tight_layout(w_pad=1.4, h_pad=1.4)
    save(fig, "figure_4_safe_refusal_diagnostics.pdf")


def clean_shift_label(s: str) -> str:
    return {
        "calibrate_OVT-B_test_TAO": "OVT-B -> TAO",
        "calibrate_TAO_test_BURST": "TAO -> BURST",
        "clear_scenes_to_occluded_scenes": "clear -> occluded",
        "common_classes_to_tail_classes": "head -> tail",
        "large_objects_to_small_objects": "large -> small",
        "long_tracks_to_short_tracks": "long -> short",
        "severe_sparse_annotation_shift": "sparse annotation",
    }.get(str(s), str(s).replace("_", " "))


def plot_stress() -> None:
    null_df = pd.read_csv(DATA / "table_stress_null_inflation.csv")
    audit_df = pd.read_csv(DATA / "table_stress_audit_noise.csv")
    shift_df = pd.read_csv(DATA / "table_stress_nonexchangeability.csv")
    score_df = pd.read_csv(DATA / "table_stress_score_miscalibration.csv")

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.55))
    axes = axes.ravel()

    g = null_df.groupby("label_keep_rate", as_index=False)["released"].mean().sort_values("label_keep_rate")
    add_panel_label(axes[0], "a")
    axes[0].plot(g["label_keep_rate"], g["released"], marker="o", color=COLORS["blue"])
    axes[0].invert_xaxis()
    axes[0].set_xlabel("Verified-positive keep rate")
    axes[0].set_ylabel("Mean release")
    axes[0].set_title("Null inflation")
    axes[0].grid(True, color="#E6E6E6", linewidth=0.5)

    a = audit_df.groupby("noise_rate", as_index=False)["conservative_FTR"].mean().sort_values("noise_rate")
    add_panel_label(axes[1], "b")
    axes[1].plot(a["noise_rate"], a["conservative_FTR"], marker="o", color=COLORS["orange"])
    axes[1].set_xlabel("Audit-noise rate")
    axes[1].set_ylabel("Conservative FTR")
    axes[1].set_title("Audit noise")
    axes[1].grid(True, color="#E6E6E6", linewidth=0.5)

    s = shift_df.groupby("shift_scenario", as_index=False)["released"].mean()
    s["label"] = s["shift_scenario"].map(clean_shift_label)
    s = s.sort_values("released")
    y = np.arange(len(s))
    add_panel_label(axes[2], "c")
    axes[2].barh(y, s["released"], color=COLORS["green"], alpha=0.86)
    axes[2].set_yticks(y)
    axes[2].set_yticklabels(s["label"])
    axes[2].set_xlabel("Mean release")
    axes[2].set_title("Non-exchangeability")
    axes[2].grid(True, axis="x", color="#E6E6E6", linewidth=0.5)

    sc = score_df.groupby("transform_type", as_index=False)[["released", "mass_ratio"]].mean(numeric_only=True)
    order = ["rank_preserving", "rank_compressing", "rank_perturbing", "adversarial"]
    sc["transform_type"] = pd.Categorical(sc["transform_type"], categories=order, ordered=True)
    sc = sc.sort_values("transform_type")
    labels = {
        "rank_preserving": "rank\npreserving",
        "rank_compressing": "rank\ncompressing",
        "rank_perturbing": "rank\nperturbing",
        "adversarial": "adversarial",
    }
    x = np.arange(len(sc))
    add_panel_label(axes[3], "d")
    axes[3].bar(x, sc["mass_ratio"], color=COLORS["red"], alpha=0.76)
    axes[3].axhline(1.0, color=COLORS["dark"], linestyle="--", linewidth=0.8)
    axes[3].set_xticks(x)
    axes[3].set_xticklabels([labels.get(str(v), str(v)) for v in sc["transform_type"]])
    axes[3].set_ylabel("Evidence-mass ratio")
    axes[3].set_title("Score miscalibration")
    axes[3].grid(True, axis="y", color="#E6E6E6", linewidth=0.5)
    sns.despine(fig=fig)
    fig.tight_layout(w_pad=1.4, h_pad=1.4)
    save(fig, "figure_5_stress_tests.pdf")


def plot_stratified() -> None:
    df = pd.read_csv(DATA / "figure_stratified_reliability.csv")
    df = df[(df["dataset"] == "OVT-B") & (df["task"] == "tracking") & (df["alpha1"] == 0.1)]
    wanted = [
        ("object_size", "large"),
        ("object_size", "small"),
        ("motion_speed", "fast"),
        ("motion_speed", "slow"),
        ("track_length", "long"),
        ("track_length", "short"),
        ("category_frequency", "head"),
        ("category_frequency", "tail"),
    ]
    rows = []
    for dim, level in wanted:
        sub = df[(df["stratification_dimension"] == dim) & (df["stratum"] == level)]
        if sub.empty:
            continue
        rows.append(
            {
                "label": f"{dim.replace('_', ' ')}: {level}",
                "Official support": sub["official_support_rate"].mean(),
                "Human valid": sub["human_valid_rate"].mean(),
                "PARC release\nwithin scope": sub["PARC_release_rate_within_scope"].mean(),
            }
        )
    mat = pd.DataFrame(rows).set_index("label")
    fig, ax = plt.subplots(figsize=(5.9, 3.15))
    sns.heatmap(
        mat,
        ax=ax,
        vmin=0,
        vmax=1,
        cmap="Blues",
        annot=True,
        fmt=".2f",
        annot_kws={"fontsize": 6.5},
        linewidths=0.45,
        linecolor="white",
        cbar_kws={"label": "Rate", "fraction": 0.045, "pad": 0.02},
    )
    ax.set_title("Stratified reliability under partial annotations")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    save(fig, "figure_6_stratified_reliability.pdf")


def plot_qualitative_examples() -> None:
    assets = FIG / "qualitative_assets"
    examples = [
        ("official_matched_01.png", "Official matched", "safe verified positive"),
        ("real_unmatched_01.png", "Real but unmatched", "unsafe as a negative"),
        ("uncertain_01.png", "Uncertain", "counted conservatively"),
        ("false_tracklet_01.png", "False tracklet", "should not be released"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.25))
    for ax, (name, title, subtitle) in zip(axes, examples):
        img = mpimg.imread(assets / name)
        ax.imshow(img)
        ax.set_axis_off()
        ax.set_title(title, fontsize=8.2, pad=3)
        ax.text(0.5, -0.08, subtitle, transform=ax.transAxes, ha="center", va="top", fontsize=6.6)
    fig.text(
        0.5,
        0.02,
        "Official support / audit -> remove only verified positives -> null-superset calibration -> certified release or refusal",
        ha="center",
        va="bottom",
        fontsize=7.0,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1), w_pad=0.35)
    save(fig, "figure_6_qualitative_release_refusal.pdf")


def normalize_image(arr: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
    arr = arr.astype(float)
    lo, hi = np.percentile(arr, [low, high])
    return np.clip((arr - lo) / (hi - lo + 1e-6), 0, 1)


def crop_center(img: np.ndarray, center: tuple[int, int], size: int) -> np.ndarray:
    cy, cx = center
    h, w = img.shape[:2]
    half = size // 2
    y0 = max(0, min(h - size, cy - half))
    x0 = max(0, min(w - size, cx - half))
    return img[y0 : y0 + size, x0 : x0 + size].copy()


def crop_center_with_origin(img: np.ndarray, center: tuple[int, int], size: int) -> tuple[np.ndarray, int, int]:
    cy, cx = center
    h, w = img.shape[:2]
    half = size // 2
    y0 = max(0, min(h - size, cy - half))
    x0 = max(0, min(w - size, cx - half))
    return img[y0 : y0 + size, x0 : x0 + size].copy(), y0, x0


def save_rgb_asset(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    arr = np.clip(arr[..., :3], 0, 1)
    Image.fromarray((arr * 255).astype(np.uint8)).save(path)


def draw_frame_label(ax: plt.Axes, x: float, y: float, label: str) -> None:
    ax.text(
        x,
        y,
        label,
        ha="left",
        va="top",
        fontsize=6.4,
        color="white",
        bbox={"boxstyle": "round,pad=0.18", "facecolor": "#111111", "edgecolor": "none", "alpha": 0.74},
    )


def ensure_figure5_assets() -> Path:
    """Prepare stable image crops and metadata for the visual examples figure."""
    raw = FIG / "raw_visual_samples"
    assets = FIG / "figure5_assets"
    assets.mkdir(parents=True, exist_ok=True)

    ctc_dir = raw / "ctc" / "DIC-C2DH-HeLa"
    frame0 = np.array(Image.open(ctc_dir / "01" / "t000.tif"))
    frame1 = np.array(Image.open(ctc_dir / "01" / "t001.tif"))
    frame0 = np.stack([normalize_image(frame0)] * 3, axis=-1)
    frame1 = np.stack([normalize_image(frame1)] * 3, axis=-1)
    ctc0, y0, x0 = crop_center_with_origin(frame0, (190, 315), 200)
    ctc1, y1, x1 = crop_center_with_origin(frame1, (175, 318), 200)
    save_rgb_asset(ctc0, assets / "ctc_release_frame_t.png")
    save_rgb_asset(ctc1, assets / "ctc_release_frame_tp1.png")
    (assets / "ctc_release_link.json").write_text(
        json.dumps(
            {
                "cell_t": [315 - x0, 190 - y0],
                "cell_tp1": [318 - x1, 175 - y1],
                "source": "DIC-C2DH-HeLa/01/t000-t001",
            },
            indent=2,
        )
    )
    ctc_examples = [
        {"name": "link 1", "t": [190, 315], "tp1": [175, 318]},
        {"name": "link 2", "t": [245, 150], "tp1": [244, 154]},
        {"name": "link 3", "t": [340, 360], "tp1": [338, 365]},
    ]
    example_meta = []
    for i, ex in enumerate(ctc_examples, start=1):
        left, yy0, xx0 = crop_center_with_origin(frame0, tuple(ex["t"]), 124)
        right, yy1, xx1 = crop_center_with_origin(frame1, tuple(ex["tp1"]), 124)
        save_rgb_asset(left, assets / f"ctc_release_{i}_t.png")
        save_rgb_asset(right, assets / f"ctc_release_{i}_tp1.png")
        example_meta.append(
            {
                "name": ex["name"],
                "cell_t": [ex["t"][1] - xx0, ex["t"][0] - yy0],
                "cell_tp1": [ex["tp1"][1] - xx1, ex["tp1"][0] - yy1],
            }
        )
    (assets / "ctc_release_examples.json").write_text(json.dumps(example_meta, indent=2))

    ctc_ref0, yy0, xx0 = crop_center_with_origin(frame0, (245, 250), 140)
    ctc_ref1, yy1, xx1 = crop_center_with_origin(frame1, (285, 410), 140)
    save_rgb_asset(ctc_ref0, assets / "ctc_refusal_frame_t.png")
    save_rgb_asset(ctc_ref1, assets / "ctc_refusal_frame_tp1.png")
    (assets / "ctc_refusal_link.json").write_text(
        json.dumps(
            {
                "cell_t": [250 - xx0, 245 - yy0],
                "cell_tp1": [410 - xx1, 285 - yy1],
                "source": "DIC-C2DH-HeLa/01/t000-t001 counterfactual raw-link illustration",
            },
            indent=2,
        )
    )

    import tifffile

    sp0 = tifffile.imread(raw / "spacenet" / "spacenet7_sample.tif")[..., :3]
    sp1 = tifffile.imread(raw / "spacenet" / "spacenet7_sample_2018_02.tif")[..., :3]
    sp0 = normalize_image(sp0, 1, 99)
    sp1 = normalize_image(sp1, 1, 99)
    sp_crop_0 = crop_center(sp0, (145, 150), 260)
    sp_crop_1 = crop_center(sp1, (145, 150), 260)
    save_rgb_asset(sp_crop_0, assets / "spacenet_release_t1.png")
    save_rgb_asset(sp_crop_1, assets / "spacenet_release_t2.png")
    (assets / "spacenet_release_polygons.json").write_text(
        json.dumps(
            {
                "released": {
                    "t1": [[77, 112], [107, 112], [107, 134], [77, 134]],
                    "t2": [[77, 112], [107, 112], [107, 134], [77, 134]],
                },
                "unreleased": [
                    {"t1": [[156, 80], [180, 80], [180, 98], [156, 98]], "t2": [[156, 80], [180, 80], [180, 98], [156, 98]]}
                ],
                "months": ["Jan", "Feb"],
            },
            indent=2,
        )
    )
    sp_examples = [
        {"name": "link 1", "center": [145, 150]},
        {"name": "link 2", "center": [470, 470]},
    ]
    sp_example_meta = []
    for i, ex in enumerate(sp_examples, start=1):
        crop0 = crop_center(sp0, tuple(ex["center"]), 165)
        crop1 = crop_center(sp1, tuple(ex["center"]), 165)
        save_rgb_asset(crop0, assets / f"spacenet_release_{i}_t1.png")
        save_rgb_asset(crop1, assets / f"spacenet_release_{i}_t2.png")
        if i == 1:
            rel = [[55, 82], [77, 82], [77, 100], [55, 100]]
            unrel = [[105, 52], [123, 52], [123, 68], [105, 68]]
        else:
            rel = [[78, 72], [100, 72], [100, 90], [78, 90]]
            unrel = [[42, 104], [61, 104], [61, 120], [42, 120]]
        sp_example_meta.append({"name": ex["name"], "released": {"t1": rel, "t2": rel}, "unreleased": {"t1": unrel, "t2": unrel}})
    (assets / "spacenet_release_examples.json").write_text(json.dumps({"months": ["Jan", "Feb"], "examples": sp_example_meta}, indent=2))

    sp_ref0 = crop_center(sp0, (810, 850), 175)
    sp_ref1 = crop_center(sp1, (810, 850), 175)
    save_rgb_asset(sp_ref0, assets / "spacenet_refusal_t1.png")
    save_rgb_asset(sp_ref1, assets / "spacenet_refusal_t2.png")
    (assets / "spacenet_refusal_candidate.json").write_text(
        json.dumps(
            {
                "months": ["Jan", "Feb"],
                "candidate": {"t1": [[70, 74], [92, 74], [92, 94], [70, 94]], "t2": [[112, 78], [134, 78], [134, 98], [112, 98]]},
            },
            indent=2,
        )
    )

    # Public-domain NPS image used as a camera-trap-style substitute for
    # illustrating iWildCam failure modes without using CC BY-NC imagery.
    wildlife_path = raw / "public_domain" / "nps_mule_deer_public_domain.jpg"
    wildlife = Image.open(wildlife_path).convert("RGB")
    wildlife = ImageOps.fit(wildlife, (420, 300), method=Image.Resampling.LANCZOS, centering=(0.50, 0.48))
    wildlife.save(assets / "camera_trap_species_failure.png")
    fox_path = raw / "public_domain" / "nps_gray_fox_camera_trap_public_domain.jpg"
    fox = Image.open(fox_path).convert("RGB")
    fox = ImageOps.fit(fox, (420, 300), method=Image.Resampling.LANCZOS, centering=(0.50, 0.50))
    fox.save(assets / "camera_trap_animal_present.png")
    (assets / "camera_trap_boxes.json").write_text(
        json.dumps(
            {
                "species_failure": {"box": [88, 38, 218, 216], "prompt": "urocyon cinereoargenteus"},
                "animal_present": {"box": [86, 38, 222, 216], "prompt": "animal", "max_e": 1.99, "required_e": 10.0},
                "source": "public-domain NPS mule deer image; schematic substitute for iWildCam failure modes",
            },
            indent=2,
        )
    )
    return assets


def connect_axes_points(
    fig: plt.Figure,
    ax0: plt.Axes,
    xy0: tuple[float, float],
    ax1: plt.Axes,
    xy1: tuple[float, float],
    color: str,
    lw: float = 0.9,
) -> None:
    p0 = fig.transFigure.inverted().transform(ax0.transData.transform(xy0))
    p1 = fig.transFigure.inverted().transform(ax1.transData.transform(xy1))
    fig.add_artist(
        FancyArrowPatch(
            p0,
            p1,
            transform=fig.transFigure,
            arrowstyle="-|>",
            mutation_scale=8,
            lw=lw,
            color=color,
            alpha=0.88,
            connectionstyle="arc3,rad=-0.10",
        )
    )


def add_image_scale_bar(
    ax: plt.Axes,
    length_px: float,
    label: str,
    color: str = "white",
    pad_px: float = 12,
    linewidth: float = 1.3,
) -> None:
    """Draw a publication scale bar in image pixel coordinates."""
    if not ax.images:
        return
    arr = ax.images[0].get_array()
    h, w = arr.shape[:2]
    x0 = w - pad_px - length_px
    x1 = w - pad_px
    y = h - pad_px
    ax.plot([x0, x1], [y, y], color=color, linewidth=linewidth, solid_capstyle="butt", zorder=5)
    ax.text(
        (x0 + x1) / 2,
        y - 5,
        label,
        ha="center",
        va="bottom",
        fontsize=5.0,
        color=color,
        zorder=5,
        path_effects=TEXT_HALO if color != "black" else None,
    )


def add_group_label(fig: plt.Figure, axes: list[plt.Axes], label: str, title: str, subtitle: str | None = None) -> None:
    boxes = [ax.get_position() for ax in axes]
    x0 = min(b.x0 for b in boxes)
    x1 = max(b.x1 for b in boxes)
    y0 = min(b.y0 for b in boxes)
    y1 = max(b.y1 for b in boxes)
    fig.text(x0, y1 + 0.010, label, ha="left", va="bottom", fontsize=8.0, fontweight="bold")
    fig.text((x0 + x1) / 2, y1 + 0.010, title, ha="center", va="bottom", fontsize=7.0)
    if subtitle:
        fig.text((x0 + x1) / 2, y0 - 0.017, subtitle, ha="center", va="top", fontsize=5.8, style="italic", color="#333333")


def add_decision_card(
    ax: plt.Axes,
    label: str,
    title: str,
    params: str,
    decision: str,
    note: str,
    accent: str = COLOR_RAW_TOPK,
) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(-0.02, 1.05, label, ha="left", va="top", fontsize=8.0, fontweight="bold", transform=ax.transAxes)
    ax.plot([0.08, 0.08], [0.12, 0.88], color=accent, linewidth=1.1, solid_capstyle="butt")
    ax.text(0.15, 0.82, title, ha="left", va="top", fontsize=7.0, fontweight="bold")
    ax.text(0.15, 0.62, params, ha="left", va="top", fontsize=6.0, family="monospace", color="#333333", linespacing=1.35)
    ax.text(0.15, 0.39, decision, ha="left", va="top", fontsize=7.0, fontweight="bold", color=accent)
    ax.text(0.15, 0.20, note, ha="left", va="top", fontsize=5.8, style="italic", color="#333333", linespacing=1.15)


def add_compact_decision_card(
    ax: plt.Axes,
    title: str,
    params: str,
    decision: str,
    note: str,
    accent: str = COLOR_RAW_TOPK,
) -> None:
    """Small audit-trail card used below image examples."""
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.plot([0.04, 0.04], [0.16, 0.88], color=accent, linewidth=0.95, solid_capstyle="butt")
    ax.text(0.10, 0.86, title, ha="left", va="top", fontsize=6.6, fontweight="bold")
    ax.text(0.10, 0.61, params, ha="left", va="top", fontsize=5.6, family="monospace", color="#333333", linespacing=1.20)
    ax.text(0.10, 0.36, decision, ha="left", va="top", fontsize=6.6, fontweight="bold", color=accent)
    ax.text(0.10, 0.17, note, ha="left", va="top", fontsize=5.3, style="italic", color="#333333", linespacing=1.08)


def draw_polygon_with_halo(
    ax: plt.Axes,
    coords: list[list[float]] | np.ndarray,
    color: str,
    linewidth: float = 0.9,
    alpha: float = 1.0,
    linestyle: str = "-",
) -> np.ndarray:
    poly = np.asarray(coords, dtype=float)
    ax.add_patch(Polygon(poly, fill=False, edgecolor="white", linewidth=linewidth + 0.85, alpha=0.90 * alpha, linestyle=linestyle))
    ax.add_patch(Polygon(poly, fill=False, edgecolor=color, linewidth=linewidth, alpha=alpha, linestyle=linestyle))
    return poly


def load_figure5_assets() -> tuple[np.ndarray, np.ndarray, dict, np.ndarray, np.ndarray, dict, np.ndarray, np.ndarray, dict]:
    assets = ensure_figure5_assets()
    return (
        mpimg.imread(assets / "ctc_release_frame_t.png"),
        mpimg.imread(assets / "ctc_release_frame_tp1.png"),
        json.loads((assets / "ctc_release_link.json").read_text()),
        mpimg.imread(assets / "spacenet_release_t1.png"),
        mpimg.imread(assets / "spacenet_release_t2.png"),
        json.loads((assets / "spacenet_release_polygons.json").read_text()),
        mpimg.imread(assets / "camera_trap_species_failure.png"),
        mpimg.imread(assets / "camera_trap_animal_present.png"),
        json.loads((assets / "camera_trap_boxes.json").read_text()),
    )


def plot_ctc_visual_panel() -> None:
    assets = ensure_figure5_assets()
    examples = json.loads((assets / "ctc_release_examples.json").read_text())
    fig = plt.figure(figsize=(3.80, 1.78))
    gs = fig.add_gridspec(1, 3, left=0.01, right=0.99, top=0.80, bottom=0.22, wspace=0.16)
    for i, ex in enumerate(examples, start=1):
        sub = gs[0, i - 1].subgridspec(1, 2, wspace=0.035)
        ax0 = fig.add_subplot(sub[0, 0])
        ax1 = fig.add_subplot(sub[0, 1])
        img0 = mpimg.imread(assets / f"ctc_release_{i}_t.png")
        img1 = mpimg.imread(assets / f"ctc_release_{i}_tp1.png")
        for ax, img, frame_label in [(ax0, img0, "t"), (ax1, img1, "t+1")]:
            ax.imshow(img, cmap="gray")
            ax.set_axis_off()
            ax.text(0.05, 0.93, frame_label, transform=ax.transAxes, color="white", fontsize=5.5, va="top", path_effects=TEXT_HALO)
        p0 = tuple(ex["cell_t"])
        p1 = tuple(ex["cell_tp1"])
        ax0.add_patch(Circle(p0, 10, fill=False, edgecolor=COLOR_PARC_RELEASE, linewidth=0.95))
        ax1.add_patch(Circle(p1, 10, fill=False, edgecolor=COLOR_PARC_RELEASE, linewidth=0.95))
        connect_axes_points(fig, ax0, (p0[0] + 7, p0[1]), ax1, (p1[0] - 7, p1[1]), COLOR_PARC_RELEASE, lw=0.72)
        if i == len(examples):
            add_image_scale_bar(ax1, length_px=53, label=r"10 $\mu$m", color="white", pad_px=8, linewidth=1.1)
    fig.text(0.50, 0.94, "CTC certified cell-link releases", ha="center", va="top", fontsize=7.0)
    fig.text(0.50, 0.045, r"released-unit visualizations; strict row: $\alpha=0.10$, $K\leq300$, FTR=0.000", ha="center", va="bottom", fontsize=5.55, color="#333333")
    save(fig, "figure_5a_ctc_release.pdf")


def plot_ctc_refusal_card_panel() -> None:
    assets = ensure_figure5_assets()
    meta = json.loads((assets / "ctc_refusal_link.json").read_text())
    fig = plt.figure(figsize=(2.55, 1.78))
    gs = fig.add_gridspec(2, 1, left=0.04, right=0.98, top=0.94, bottom=0.06, height_ratios=[0.98, 0.82], hspace=0.10)
    sub = gs[0, 0].subgridspec(1, 2, wspace=0.035)
    ax0 = fig.add_subplot(sub[0, 0])
    ax1 = fig.add_subplot(sub[0, 1])
    img0 = mpimg.imread(assets / "ctc_refusal_frame_t.png")
    img1 = mpimg.imread(assets / "ctc_refusal_frame_tp1.png")
    for ax, img, frame_label in [(ax0, img0, "t"), (ax1, img1, "t+1")]:
        ax.imshow(img, cmap="gray")
        ax.set_axis_off()
        ax.text(0.05, 0.93, frame_label, transform=ax.transAxes, color="white", fontsize=5.5, va="top", path_effects=TEXT_HALO)
    p0 = tuple(meta["cell_t"])
    p1 = tuple(meta["cell_tp1"])
    ax0.add_patch(Circle(p0, 12, fill=False, edgecolor=COLOR_RAW_TOPK, linewidth=1.05, linestyle="--"))
    ax1.add_patch(Circle(p1, 12, fill=False, edgecolor=COLOR_RAW_TOPK, linewidth=1.05, linestyle="--"))
    connect_axes_points(fig, ax0, (p0[0] + 9, p0[1]), ax1, (p1[0] - 9, p1[1]), COLOR_RAW_TOPK, lw=0.80)
    ax_card = fig.add_subplot(gs[1, 0])
    add_compact_decision_card(
        ax_card,
        "CTC unsafe-volume request",
        "K=5000\nraw top-K FTR=0.3606",
        "REFUSED (0/20 seeds)",
        "Counterfactual raw-link release is unsafe.",
        COLOR_RAW_TOPK,
    )
    save(fig, "figure_5b_ctc_refusal_card.pdf")


def plot_spacenet_visual_panel() -> None:
    assets = ensure_figure5_assets()
    meta = json.loads((assets / "spacenet_release_examples.json").read_text())
    fig = plt.figure(figsize=(3.80, 1.78))
    gs = fig.add_gridspec(1, 2, left=0.01, right=0.99, top=0.80, bottom=0.22, wspace=0.13)
    for i, ex in enumerate(meta["examples"], start=1):
        sub = gs[0, i - 1].subgridspec(1, 2, wspace=0.035)
        ax0 = fig.add_subplot(sub[0, 0])
        ax1 = fig.add_subplot(sub[0, 1])
        img0 = mpimg.imread(assets / f"spacenet_release_{i}_t1.png")
        img1 = mpimg.imread(assets / f"spacenet_release_{i}_t2.png")
        for ax, img, month in [(ax0, img0, meta["months"][0]), (ax1, img1, meta["months"][1])]:
            ax.imshow(img)
            ax.set_axis_off()
            ax.text(0.04, 0.94, month, transform=ax.transAxes, color="white", fontsize=5.5, va="top", path_effects=TEXT_HALO)
        for ax, frame_key in [(ax0, "t1"), (ax1, "t2")]:
            draw_polygon_with_halo(ax, ex["released"][frame_key], COLOR_PARC_RELEASE, linewidth=0.95)
            draw_polygon_with_halo(ax, ex["unreleased"][frame_key], COLOR_REFUSAL, linewidth=0.55, alpha=0.65)
        left_poly = np.array(ex["released"]["t1"])
        right_poly = np.array(ex["released"]["t2"])
        connect_axes_points(fig, ax0, tuple(left_poly.mean(axis=0)), ax1, tuple(right_poly.mean(axis=0)), COLOR_PARC_RELEASE, lw=0.72)
        if i == len(meta["examples"]):
            add_image_scale_bar(ax1, length_px=25, label="100 m", color="white", pad_px=8, linewidth=1.1)
    fig.text(0.50, 0.94, "SpaceNet same-building releases", ha="center", va="top", fontsize=7.0)
    fig.text(0.50, 0.045, "released-unit visualizations; K=50 audit row human FTR=0.000", ha="center", va="bottom", fontsize=5.55, color="#333333")
    save(fig, "figure_5c_spacenet_release.pdf")


def plot_spacenet_refusal_card_panel() -> None:
    assets = ensure_figure5_assets()
    meta = json.loads((assets / "spacenet_refusal_candidate.json").read_text())
    fig = plt.figure(figsize=(2.55, 1.78))
    gs = fig.add_gridspec(2, 1, left=0.04, right=0.98, top=0.94, bottom=0.06, height_ratios=[0.98, 0.82], hspace=0.10)
    sub = gs[0, 0].subgridspec(1, 2, wspace=0.035)
    ax0 = fig.add_subplot(sub[0, 0])
    ax1 = fig.add_subplot(sub[0, 1])
    img0 = mpimg.imread(assets / "spacenet_refusal_t1.png")
    img1 = mpimg.imread(assets / "spacenet_refusal_t2.png")
    for ax, img, month in [(ax0, img0, meta["months"][0]), (ax1, img1, meta["months"][1])]:
        ax.imshow(img)
        ax.set_axis_off()
        ax.text(0.04, 0.94, month, transform=ax.transAxes, color="white", fontsize=5.5, va="top", path_effects=TEXT_HALO)
    left_poly = draw_polygon_with_halo(ax0, meta["candidate"]["t1"], COLOR_RAW_TOPK, linewidth=0.85, linestyle="--")
    right_poly = draw_polygon_with_halo(ax1, meta["candidate"]["t2"], COLOR_RAW_TOPK, linewidth=0.85, linestyle="--")
    connect_axes_points(fig, ax0, tuple(left_poly.mean(axis=0)), ax1, tuple(right_poly.mean(axis=0)), COLOR_RAW_TOPK, lw=0.72)
    add_image_scale_bar(ax1, length_px=25, label="100 m", color="white", pad_px=8, linewidth=1.1)
    ax_card = fig.add_subplot(gs[1, 0])
    add_compact_decision_card(
        ax_card,
        "SpaceNet audit request",
        r"K=100, alpha=0.20",
        "REFUSED (20/20 seeds)",
        "Evidence mass below threshold;\nK=50 diagnostic row was audit-supported.",
        COLOR_RAW_TOPK,
    )
    save(fig, "figure_5d_spacenet_refusal_card.pdf")


def plot_camera_trap_visual_panel() -> None:
    *_, deer_species, deer_animal, deer_meta = load_figure5_assets()
    fig = plt.figure(figsize=(6.65, 1.82))
    gs = fig.add_gridspec(1, 2, left=0.08, right=0.98, top=0.82, bottom=0.06, wspace=0.08)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    for ax, img in [(ax0, deer_species), (ax1, deer_animal)]:
        ax.imshow(img)
        ax.set_axis_off()
    species_box = deer_meta["species_failure"]["box"]
    animal_box = deer_meta["animal_present"]["box"]
    ax0.add_patch(Rectangle((species_box[0], species_box[1]), species_box[2], species_box[3], fill=False, edgecolor="white", linewidth=1.9))
    ax0.add_patch(Rectangle((species_box[0], species_box[1]), species_box[2], species_box[3], fill=False, edgecolor=COLOR_RAW_TOPK, linewidth=1.2))
    ax1.add_patch(Rectangle((animal_box[0], animal_box[1]), animal_box[2], animal_box[3], fill=False, edgecolor="white", linewidth=1.7))
    ax1.add_patch(Rectangle((animal_box[0], animal_box[1]), animal_box[2], animal_box[3], fill=False, edgecolor=COLOR_REFUSAL, linewidth=1.0))
    ax0.text(0.04, 0.08, "one-sided reliability failure", transform=ax0.transAxes, ha="left", va="bottom", fontsize=6.4, color=COLOR_RAW_TOPK, fontweight="bold", path_effects=TEXT_HALO)
    ax1.text(0.04, 0.13, "human-audited animal unit", transform=ax1.transAxes, ha="left", va="bottom", fontsize=6.4, color=COLOR_PARC_RELEASE, fontweight="bold", path_effects=TEXT_HALO)
    ax0.text(0.04, 0.93, "prompt: species name", transform=ax0.transAxes, ha="left", va="top", fontsize=5.8, color="white", path_effects=TEXT_HALO)
    ax1.text(0.04, 0.93, "prompt: animal", transform=ax1.transAxes, ha="left", va="top", fontsize=5.8, color="white", path_effects=TEXT_HALO)
    ax1.text(0.04, 0.04, "operational alpha=0.20 release", transform=ax1.transAxes, ha="left", va="bottom", fontsize=5.7, color="white", path_effects=TEXT_HALO)
    fig.text(0.50, 0.93, "Camera-trap release unit and boundary", ha="center", va="top", fontsize=7.0)
    save(fig, "figure_5e_camera_trap_boundary.pdf")


def plot_visual_release_refusal_panels() -> None:
    plot_ctc_visual_panel()
    plot_ctc_refusal_card_panel()
    plot_spacenet_visual_panel()
    plot_spacenet_refusal_card_panel()
    plot_camera_trap_visual_panel()


def plot_visual_release_refusal_examples() -> None:
    assets = ensure_figure5_assets()
    plot_visual_release_refusal_panels()

    ctc0 = mpimg.imread(assets / "ctc_release_frame_t.png")
    ctc1 = mpimg.imread(assets / "ctc_release_frame_tp1.png")
    ctc_meta = json.loads((assets / "ctc_release_link.json").read_text())
    sp0 = mpimg.imread(assets / "spacenet_release_t1.png")
    sp1 = mpimg.imread(assets / "spacenet_release_t2.png")
    sp_meta = json.loads((assets / "spacenet_release_polygons.json").read_text())
    deer_species = mpimg.imread(assets / "camera_trap_species_failure.png")
    deer_animal = mpimg.imread(assets / "camera_trap_animal_present.png")
    deer_meta = json.loads((assets / "camera_trap_boxes.json").read_text())

    fig = plt.figure(figsize=(7.2, 5.0))
    gs = fig.add_gridspec(
        3,
        2,
        height_ratios=[1.0, 1.0, 1.10],
        width_ratios=[1.0, 0.85],
        hspace=0.46,
        wspace=0.30,
        left=0.04,
        right=0.99,
        top=0.95,
        bottom=0.08,
    )

    # Panel a: CTC release.
    sub_a = gs[0, 0].subgridspec(1, 2, wspace=0.03)
    ax_a0 = fig.add_subplot(sub_a[0, 0])
    ax_a1 = fig.add_subplot(sub_a[0, 1])
    for ax, img, frame_label in [(ax_a0, ctc0, "t"), (ax_a1, ctc1, "t+1")]:
        ax.imshow(img, cmap="gray")
        ax.set_axis_off()
        ax.text(0.04, 0.94, frame_label, transform=ax.transAxes, color="white", fontsize=6.0, va="top", path_effects=TEXT_HALO)
    p0 = tuple(ctc_meta["cell_t"])
    p1 = tuple(ctc_meta["cell_tp1"])
    ax_a0.add_patch(Circle(p0, 18, fill=False, edgecolor=COLOR_PARC_RELEASE, linewidth=1.15))
    ax_a1.add_patch(Circle(p1, 18, fill=False, edgecolor=COLOR_PARC_RELEASE, linewidth=1.15))
    connect_axes_points(fig, ax_a0, (p0[0] + 14, p0[1]), ax_a1, (p1[0] - 14, p1[1]), COLOR_PARC_RELEASE, lw=0.95)
    add_image_scale_bar(ax_a1, length_px=53, label=r"10 $\mu$m", color="white")
    add_group_label(
        fig,
        [ax_a0, ax_a1],
        "a",
        "CTC certified cell-link release",
        r"$\alpha=0.10$, $\rho=0.10$, $K\leq300$; 20/20 seeds, FTR=0.000",
    )

    # Panel b: CTC refusal card.
    ax_b = fig.add_subplot(gs[0, 1])
    add_decision_card(
        ax_b,
        "b",
        "CTC unsafe-volume request",
        "K=5000\nraw top-K FTR=0.3606",
        "REFUSED (0/20 seeds)",
        "PARC refuses the ranked-list release\nwhen the requested volume is unsafe.",
        COLOR_RAW_TOPK,
    )

    # Panel c: SpaceNet release.
    sub_c = gs[1, 0].subgridspec(1, 2, wspace=0.03)
    ax_c0 = fig.add_subplot(sub_c[0, 0])
    ax_c1 = fig.add_subplot(sub_c[0, 1])
    months = sp_meta["months"]
    for ax, img, month in [(ax_c0, sp0, months[0]), (ax_c1, sp1, months[1])]:
        ax.imshow(img)
        ax.set_axis_off()
        ax.text(0.04, 0.94, month, transform=ax.transAxes, color="white", fontsize=6.0, va="top", path_effects=TEXT_HALO)
    for key, color, lw, alpha in [("released", COLOR_PARC_RELEASE, 1.1, 1.0)]:
        for ax, frame_key in [(ax_c0, "t1"), (ax_c1, "t2")]:
            poly = np.array(sp_meta[key][frame_key])
            ax.add_patch(Polygon(poly, fill=False, edgecolor="white", linewidth=lw + 0.75, alpha=0.95))
            ax.add_patch(Polygon(poly, fill=False, edgecolor=color, linewidth=lw, alpha=alpha))
    for candidate in sp_meta["unreleased"]:
        for ax, frame_key in [(ax_c0, "t1"), (ax_c1, "t2")]:
            poly = np.array(candidate[frame_key])
            ax.add_patch(Polygon(poly, fill=False, edgecolor="white", linewidth=0.85, alpha=0.75))
            ax.add_patch(Polygon(poly, fill=False, edgecolor=COLOR_REFUSAL, linewidth=0.55, alpha=0.65))
    left_poly = np.array(sp_meta["released"]["t1"])
    right_poly = np.array(sp_meta["released"]["t2"])
    connect_axes_points(fig, ax_c0, tuple(left_poly.mean(axis=0)), ax_c1, tuple(right_poly.mean(axis=0)), COLOR_PARC_RELEASE, lw=0.95)
    add_image_scale_bar(ax_c1, length_px=25, label="100 m", color="white")
    add_group_label(
        fig,
        [ax_c0, ax_c1],
        "c",
        "SpaceNet same-building release",
        "K=50 audit-supported diagnostic release; human FTR=0.000, n=147",
    )

    # Panel d: SpaceNet refusal card.
    ax_d = fig.add_subplot(gs[1, 1])
    add_decision_card(
        ax_d,
        "d",
        "SpaceNet audit request",
        r"K=100, alpha=0.20",
        "REFUSED (20/20 seeds)",
        "Lower-volume K=50 diagnostic row\nwas supported by blind visual audit.",
        COLOR_RAW_TOPK,
    )

    # Panel e: iWildCam operating-envelope illustration with a public-domain substitute image.
    sub_e = gs[2, :].subgridspec(1, 2, wspace=0.08)
    ax_e0 = fig.add_subplot(sub_e[0, 0])
    ax_e1 = fig.add_subplot(sub_e[0, 1])
    for ax, img in [(ax_e0, deer_species), (ax_e1, deer_animal)]:
        ax.imshow(img)
        ax.set_axis_off()
    species_box = deer_meta["species_failure"]["box"]
    animal_box = deer_meta["animal_present"]["box"]
    ax_e0.add_patch(Rectangle((species_box[0], species_box[1]), species_box[2], species_box[3], fill=False, edgecolor="white", linewidth=1.9))
    ax_e0.add_patch(Rectangle((species_box[0], species_box[1]), species_box[2], species_box[3], fill=False, edgecolor=COLOR_RAW_TOPK, linewidth=1.2))
    ax_e1.add_patch(Rectangle((animal_box[0], animal_box[1]), animal_box[2], animal_box[3], fill=False, edgecolor="white", linewidth=1.7))
    ax_e1.add_patch(Rectangle((animal_box[0], animal_box[1]), animal_box[2], animal_box[3], fill=False, edgecolor=COLOR_REFUSAL, linewidth=1.0))
    ax_e0.text(0.04, 0.08, "one-sided reliability failure", transform=ax_e0.transAxes, ha="left", va="bottom", fontsize=6.4, color=COLOR_RAW_TOPK, fontweight="bold", path_effects=TEXT_HALO)
    ax_e1.text(0.04, 0.13, "human-audited animal unit", transform=ax_e1.transAxes, ha="left", va="bottom", fontsize=6.4, color=COLOR_PARC_RELEASE, fontweight="bold", path_effects=TEXT_HALO)
    ax_e0.text(0.04, 0.93, "prompt: species name", transform=ax_e0.transAxes, ha="left", va="top", fontsize=5.8, color="white", path_effects=TEXT_HALO)
    ax_e1.text(0.04, 0.93, "prompt: animal", transform=ax_e1.transAxes, ha="left", va="top", fontsize=5.8, color="white", path_effects=TEXT_HALO)
    ax_e1.text(0.04, 0.04, "operational alpha=0.20 release", transform=ax_e1.transAxes, ha="left", va="bottom", fontsize=5.7, color="white", path_effects=TEXT_HALO)
    add_group_label(fig, [ax_e0, ax_e1], "e", "Camera-trap release unit and boundary")

    fig.text(
        0.5,
        0.018,
        "Visual examples illustrate candidate units and PARC decisions; statistical guarantees are the release-set certificates summarized in Tables 1--2.",
        ha="center",
        va="bottom",
        fontsize=5.8,
        color="#333333",
    )
    save(fig, "figure_5_visual_release_refusal_examples.pdf")


def plot_iwildcam_operating_envelope() -> None:
    proxy = pd.read_csv(DATA / "table_iwildcam_failure_mode_summary.csv")
    human = pd.read_csv(DATA / "table_iwildcam_human_audit_primary_results.csv")
    cal = pd.read_csv(DATA / "table_iwildcam_calibration_audit_summary.csv").iloc[0]
    rel = pd.read_csv(DATA / "table_iwildcam_release_audit_summary.csv").iloc[0]
    raw = pd.read_csv(DATA / "table_iwildcam_raw_topk_audit_summary.csv").iloc[0]

    proxy_animal = proxy[proxy["source"].eq("animal_present_prompt")].iloc[0]
    max_e_proxy = float(proxy_animal["max_observed_e_mean"])

    fig = plt.figure(figsize=(7.2, 4.05))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.2], height_ratios=[1.0, 0.95], hspace=0.55, wspace=0.42)

    ax = fig.add_subplot(gs[0, 0])
    add_panel_label(ax, "a")
    states = pd.DataFrame(
        {
            "One-sided\nreliability": [0.0, 1.0, 1.0],
            "Evidence / audit\nsupport": [np.nan, 0.0, 1.0],
            "Release at\nreported endpoint": [0.0, 0.0, 1.0],
        },
        index=["Species\nprompt", "Official/proxy\nanimal", "Human-audited\nanimal"],
    )
    annot = [["fails", "", "no"], ["passes", "weak", "refuse"], ["passes", "passes", "release"]]
    cmap = sns.color_palette(["#F4C7C3", "#F6E7A8", "#B7D9B1"], as_cmap=True)
    sns.heatmap(states, ax=ax, vmin=0, vmax=1, cmap=cmap, annot=annot, fmt="", cbar=False, linewidths=0.5, linecolor="white", annot_kws={"fontsize": 6.4})
    ax.set_title("Ecology operating envelope")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)

    ax = fig.add_subplot(gs[0, 1])
    add_panel_label(ax, "b")
    counts = [int(cal["n_animal"]), int(cal["n_not_animal"])]
    ax.bar([0], [counts[0]], color=COLORS["blue"], width=0.45, label="animal")
    ax.bar([0], [counts[1]], bottom=[counts[0]], color="#D6D6D6", width=0.45, label="not animal")
    ax.set_xlim(-0.6, 0.8)
    ax.set_xticks([0])
    ax.set_xticklabels(["calibration\naudit"])
    ax.set_ylabel("Human-audited candidates")
    ax.set_title("One-sided positives from human audit")
    ax.text(0, counts[0] / 2, f"{counts[0]} animal", fontsize=6.0, va="center", ha="center", color="white", fontweight="bold")
    ax.text(0, counts[0] + counts[1] / 2, f"{counts[1]} not animal", fontsize=6.0, va="center", ha="center", color="#333333")
    clean_axis(ax, grid=True)

    ax = fig.add_subplot(gs[1, 0])
    add_panel_label(ax, "c")
    subset = human[human["K"].isin([25, 50, 100])].copy()
    subset["label"] = subset.apply(lambda r: f"a={r['alpha']:.1f}\nK={int(r['K'])}", axis=1)
    order = [(0.1, 25), (0.1, 50), (0.1, 100), (0.2, 25), (0.2, 50), (0.2, 100)]
    subset["_order"] = subset.apply(lambda r: order.index((float(r["alpha"]), int(r["K"]))), axis=1)
    subset = subset.sort_values("_order")
    colors = [COLORS["gray"] if float(a) == 0.1 else COLORS["blue"] for a in subset["alpha"]]
    ax.bar(np.arange(len(subset)), subset["mean_release"], color=colors, width=0.65)
    ax.set_xticks(np.arange(len(subset)))
    ax.set_xticklabels(subset["label"], fontsize=5.6)
    ax.set_ylabel("Mean release")
    ax.set_title("Strict refusal, operational release")
    ax.set_ylim(0, 105)
    ax.axvline(2.5, color="#CFCFCF", lw=0.6)
    ax.text(1, 92, "strict refused", ha="center", fontsize=5.8, color=COLORS["gray"])
    ax.text(4, 92, "operational release", ha="center", fontsize=5.8, color=COLORS["blue"], fontweight="bold")
    clean_axis(ax, grid=True)

    ax = fig.add_subplot(gs[1, 1])
    add_panel_label(ax, "d")
    labels = ["release audit\nK=50", "raw top-K\naudit"]
    animal_counts = [int(rel["n_animal"]), int(raw["n_animal"])]
    false_counts = [int(rel["n_false"]) + int(rel["n_uncertain"]), int(raw["n_false"]) + int(raw["n_uncertain"])]
    x = np.arange(2)
    ax.bar(x, animal_counts, color=COLORS["blue"], width=0.55, label="animal")
    ax.bar(x, false_counts, bottom=animal_counts, color=COLORS["red"], width=0.55, label="false/uncertain")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Human-reviewed candidates")
    ax.set_title("Release audit supports animal-present row")
    ax.set_ylim(0, 330)
    ax.text(0, animal_counts[0] + 12, f"{animal_counts[0]}/{animal_counts[0]} animal\nhuman FTR=0", ha="center", fontsize=5.8)
    ax.text(1, animal_counts[1] + 12, f"{animal_counts[1]}/{animal_counts[1]} animal", ha="center", fontsize=5.8)
    ax.legend(loc="upper right", fontsize=5.8)
    clean_axis(ax, grid=True)

    fig.tight_layout()
    save(fig, "figure_4_iwildcam_operating_envelope.pdf")


def plot_ctc_release_certification() -> None:
    learned = pd.read_csv(DATA / "table_ctc_learned_strict_alpha010_smallK.csv")
    reverse = pd.read_csv(DATA / "table_ctc_learned_reverse_split.csv")
    ctc_negative = pd.read_csv(DATA / "table_ctc_learned_negative_control.csv")
    ctc_primary = pd.read_csv(DATA / "table_ctc_main_nonoracle.csv")

    fig = plt.figure(figsize=(7.2, 4.35))
    gs = fig.add_gridspec(
        nrows=2,
        ncols=4,
        height_ratios=[1.08, 0.88],
        width_ratios=[1.0, 1.0, 1.0, 1.0],
        hspace=0.50,
        wspace=0.55,
    )
    ax_a = fig.add_subplot(gs[0, 0:4])
    ax_b = fig.add_subplot(gs[1, 0:2])
    ax_c = fig.add_subplot(gs[1, 2])
    ax_d = fig.add_subplot(gs[1, 3])
    k_ticks = [10, 25, 50, 100, 300]
    release_ticks = [0, 100, 200, 300]

    ax = ax_a
    add_panel_label(ax, "a")
    panel = learned[(learned["rho"].eq(0.10)) & (learned["alpha"].eq(0.10))].sort_values("M")
    rev = reverse[(reverse["rho"].eq(0.10)) & (reverse["alpha"].eq(0.10))].sort_values("M")
    ax.fill_between(panel["M"], 0, panel["released_mean"], color=TINT_RELEASE_OK, alpha=0.95, zorder=0)
    ax.plot(panel["M"], panel["released_mean"], marker="o", color=COLOR_PARC_RELEASE, linewidth=1.5, label="train 01 -> certify 02")
    ax.plot(rev["M"], rev["released_mean"], marker="s", linestyle="--", color=COLOR_PARC_RELEASE, alpha=0.76, linewidth=1.15, label="reverse split")
    ax.plot(panel["M"], panel["M"], linestyle="--", color=COLOR_REFUSAL, linewidth=0.9, label="requested K")
    ax.set_xscale("log")
    ax.set_xlabel("Candidate budget K")
    ax.set_ylabel("Mean released cell links")
    ax.set_title("CTC strict learned release")
    ax.set_xticks(k_ticks)
    ax.set_xticklabels(["10", "25", "50", "100", "300"])
    ax.set_ylim(0, 305)
    ax.set_yticks(release_ticks)
    ax.legend(title="", loc="upper left", ncol=1)
    clean_axis(ax)

    ax = ax_b
    add_panel_label(ax, "b")
    ctc_neg = ctc_negative[(ctc_negative["rho"].eq(0.10)) & (ctc_negative["alpha"].eq(0.10))].sort_values("M")
    ax.bar(ctc_neg["M"], ctc_neg["raw_topM_actual_FTR_mean"], width=ctc_neg["M"] * 0.18, color=COLOR_RAW_TOPK, alpha=0.82, label="raw FTR")
    ax.plot(ctc_neg["M"], ctc_neg["nonempty_seeds"] / 20.0, marker="o", color=COLOR_PARC_RELEASE, linewidth=1.1, label="PARC non-empty")
    ax.set_xscale("log")
    ax.set_xticks(k_ticks)
    ax.set_xticklabels(["10", "25", "50", "100", "300"])
    ax.set_xlabel("Candidate budget K")
    ax.set_ylabel("Fraction")
    ax.set_title("Random-score refusal")
    ax.set_ylim(-0.02, 0.92)
    ax.set_yticks([0, 0.4, 0.8])
    ax.legend(title="", loc="upper right")
    clean_axis(ax)

    ax = ax_c
    add_panel_label(ax, "c")
    ctc_refusal = ctc_primary[ctc_primary["row_role"].eq("unsafe_high_volume_refusal")].iloc[0]
    ax.bar([0, 1], [0.0, float(ctc_refusal["raw_topM_actual_FTR"])], color=[COLOR_PARC_RELEASE, COLOR_RAW_TOPK], width=0.58)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["PARC", "raw\nK=5000"])
    ax.set_ylabel("False-link fraction")
    ax.set_ylim(0, 0.42)
    ax.set_yticks([0, 0.2, 0.4])
    ax.set_title("Unsafe volume")
    clean_axis(ax)

    ax = ax_d
    add_panel_label(ax, "d")
    ax.axis("off")
    ax.plot([0.08, 0.08], [0.10, 0.90], transform=ax.transAxes, color=COLOR_REFUSAL, lw=1.0)
    ax.text(0.16, 0.86, "Leakage checks", transform=ax.transAxes, fontsize=7, fontweight="bold", va="top")
    ax.text(
        0.16,
        0.67,
        "sequence-disjoint\nno GT identity\nno match labels\ntrain-only normalization\nfrozen before PARC",
        transform=ax.transAxes,
        fontsize=6,
        va="top",
        linespacing=1.35,
    )
    ax.text(0.16, 0.16, "passed", transform=ax.transAxes, fontsize=7, color=COLOR_PARC_RELEASE, fontweight="bold")

    fig.tight_layout()
    save(fig, "figure_2_ctc_release_certification.pdf")


def plot_materials_discovery_certification() -> None:
    materials = pd.read_csv(DATA / "table_materials_primary_results.csv")
    random_ctrl = pd.read_csv(DATA / "table_materials_random_score_control.csv")
    high_volume = pd.read_csv(DATA / "table_materials_high_volume_refusal.csv")
    modern = pd.read_csv(DATA / "table_materials_modern_model_sensitivity.csv")

    fig = plt.figure(figsize=(7.2, 4.45))
    gs = fig.add_gridspec(
        nrows=2,
        ncols=4,
        height_ratios=[1.08, 0.90],
        width_ratios=[1.0, 1.0, 1.0, 1.0],
        hspace=0.50,
        wspace=0.62,
    )
    ax_a = fig.add_subplot(gs[0, 0:4])
    ax_b = fig.add_subplot(gs[1, 0:2])
    ax_c = fig.add_subplot(gs[1, 2])
    ax_d = fig.add_subplot(gs[1, 3])

    mat = materials[(materials["rho"].eq(0.10)) & (materials["alpha"].eq(0.10))].sort_values("K")
    show = mat[mat["K"].isin([50, 100, 300, 500, 1000, 5000])]
    ax = ax_a
    add_panel_label(ax, "a")
    ax.fill_between(show["K"], 0, show["mean_release"], color=TINT_RELEASE_OK, alpha=0.95, zorder=0)
    ax.plot(show["K"], show["mean_release"], marker="o", color=COLOR_PARC_RELEASE, linewidth=1.45, label="PARC release")
    primary = show[show["K"].eq(100)].iloc[0]
    sensitivity = show[show["K"].eq(300)].iloc[0]
    hv = show[show["K"].eq(5000)].iloc[0]
    ax.scatter([100], [primary["mean_release"]], s=62, color=COLOR_HUMAN_AUDIT, edgecolor="white", linewidth=0.7, zorder=5, label="primary K=100")
    ax.scatter([300], [sensitivity["mean_release"]], s=46, color=COLOR_ORACLE, edgecolor="white", linewidth=0.7, zorder=5, label="K=300 sensitivity")
    ax.scatter([5000], [hv["mean_release"]], s=58, marker="X", color=COLOR_RAW_TOPK, edgecolor="white", linewidth=0.7, zorder=6, label="K=5000 refused")
    ax.set_xscale("log")
    ax.set_xticks([50, 100, 300, 1000, 5000])
    ax.set_xticklabels(["50", "100", "300", "1000", "5000"])
    ax.set_ylim(-6, 190)
    ax.set_yticks([0, 50, 100, 150])
    ax.set_xlabel("Candidate budget K")
    ax.set_ylabel("Mean released crystal candidates")
    ax.set_title("Strict materials release and volume boundary")
    ax.legend(title="", loc="upper left", ncol=2)
    clean_axis(ax)

    ax = ax_b
    add_panel_label(ax, "b")
    ftr_rows = show[show["K"].isin([50, 100, 300, 500, 1000])]
    colors = [COLOR_HUMAN_AUDIT if k == 100 else (COLOR_ORACLE if k == 300 else COLOR_PARC_RELEASE) for k in ftr_rows["K"]]
    ax.bar(np.arange(len(ftr_rows)), ftr_rows["actual_FTR_mean"], color=colors, alpha=0.86, width=0.62)
    ax.axhline(0.10, color=COLOR_TARGET, linestyle="--", linewidth=0.8)
    ax.set_xticks(np.arange(len(ftr_rows)))
    ax.set_xticklabels([str(int(k)) for k in ftr_rows["K"]])
    ax.set_xlabel("Candidate budget K")
    ax.set_ylabel("Held-out FTR")
    ax.set_ylim(0, 0.14)
    ax.set_yticks([0, 0.05, 0.10])
    ax.set_title("Primary and sensitivity FTR")
    clean_axis(ax)

    ax = ax_c
    add_panel_label(ax, "c")
    r = random_ctrl[(random_ctrl["alpha"].eq(0.10)) & (random_ctrl["K"].isin([300, 1000]))].sort_values("K")
    x = np.arange(len(r))
    ax.bar(x + 0.16, r["raw_topK_actual_FTR_mean"], color=COLOR_RAW_TOPK, alpha=0.82, width=0.32, label="raw FTR")
    ax.scatter(x - 0.16, r["non_empty_seeds"] / 20.0, s=24, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.6, zorder=5, label="PARC non-empty")
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(k)) for k in r["K"]])
    ax.set_xlabel("K")
    ax.set_ylabel("Fraction")
    ax.set_ylim(-0.02, 0.92)
    ax.set_yticks([0, 0.4, 0.8])
    ax.set_title("Random-score refusal")
    ax.legend(title="", loc="upper right", fontsize=5.6)
    clean_axis(ax)

    ax = ax_d
    add_panel_label(ax, "d")
    m = modern[(modern["alpha"].eq(0.10)) & (modern["K"].isin([300, 500]))].sort_values("K")
    x = np.arange(len(m))
    ax.bar(x - 0.16, m["actual_FTR_mean"], color=COLOR_PARC_RELEASE, alpha=0.86, width=0.32, label="PARC")
    ax.bar(x + 0.16, m["raw_topK_actual_FTR_mean"], color=COLOR_RAW_TOPK, alpha=0.72, width=0.32, label="raw top-K")
    ax.axhline(0.10, color=COLOR_TARGET, linestyle="--", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(k)) for k in m["K"]])
    ax.set_xlabel("K")
    ax.set_ylabel("FTR")
    ax.set_ylim(0, 0.36)
    ax.set_yticks([0, 0.1, 0.2, 0.3])
    ax.set_title("ALIGNN-FF sensitivity")
    ax.legend(title="", loc="upper left", fontsize=5.6)
    clean_axis(ax)

    fig.tight_layout()
    save(fig, "figure_3_materials_discovery_release.pdf")


def plot_spacenet_release_certification() -> None:
    geom = pd.read_csv(DATA / "table_spacenet7_geometry_partial_verification_sweep.csv")
    rand = pd.read_csv(DATA / "table_spacenet7_randomized_partial_verification_sweep.csv")
    k100 = pd.read_csv(DATA / "table_spacenet7_real_audit_k100_failure_summary.csv").iloc[0]
    k50 = pd.read_csv(DATA / "table_spacenet7_real_audit_k50_completed_summary.csv").iloc[0]
    coverage = pd.read_csv(DATA / "table_spacenet7_real_audit_block_coverage.csv")

    fig = plt.figure(figsize=(7.2, 4.10))
    gs = fig.add_gridspec(
        nrows=2,
        ncols=4,
        height_ratios=[1.05, 0.95],
        width_ratios=[1.0, 1.0, 1.0, 1.0],
        hspace=0.48,
        wspace=1.05,
    )
    ax_a = fig.add_subplot(gs[0, 0:2])
    ax_b = fig.add_subplot(gs[0, 2:4])
    ax_c = fig.add_subplot(gs[1, 0:2])
    ax_d = fig.add_subplot(gs[1, 2:4])

    ax = ax_a
    add_panel_label(ax, "a")
    panel = geom[(geom["alpha"].eq(0.2)) & (geom["rho"].lt(1.0)) & (geom["M"].isin([100, 300, 500, 5000]))]
    g = panel.groupby("M", as_index=False)["released"].mean().sort_values("M")
    release_g = g[g["M"].le(500)]
    refusal_g = g[g["M"].eq(5000)]
    ax.fill_between(release_g["M"], 0, release_g["released"], color=TINT_RELEASE_OK, alpha=0.95, zorder=0)
    ax.plot(release_g["M"], release_g["released"], marker="o", color=COLOR_PARC_RELEASE, linewidth=1.5)
    if not refusal_g.empty:
        ax.scatter(refusal_g["M"], refusal_g["released"], s=48, marker="X", color=COLOR_RAW_TOPK, edgecolor="white", linewidth=0.6, zorder=5)
    ax.set_xscale("log")
    ax.set_xlabel("Candidate budget K")
    ax.set_ylabel("Mean released links")
    ax.set_title("Geometry release and refusal")
    ax.set_xticks([100, 300, 500, 5000])
    ax.set_xticklabels(["100", "300", "500", "5000"])
    ax.set_ylim(-4, max(105, release_g["released"].max() * 1.12))
    clean_axis(ax)

    ax = ax_b
    add_panel_label(ax, "b")
    x = np.arange(2)
    releases = [0.0, float(k50["mean_release_across_seeds"])]
    ax.bar(x, releases, color=[COLOR_REFUSAL, COLOR_PARC_RELEASE], width=0.55, edgecolor="white", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(["K=100\nrequest", "K=50\nn=147"])
    ax.set_ylabel("Mean PARC release")
    ax.set_ylim(0, 55)
    ax.set_title("Human-audit operating check")
    ax2 = ax.twinx()
    ax2.scatter([1], [float(k50["audited_FTR_uncertain_as_false"])], s=40, marker="D", color=COLOR_HUMAN_AUDIT, edgecolor="white", linewidth=0.6, zorder=5)
    ax2.set_ylim(0, 0.08)
    ax2.set_yticks([0, 0.04, 0.08])
    ax2.set_ylabel("Human FTR", color=COLOR_HUMAN_AUDIT)
    ax2.tick_params(axis="y", colors=COLOR_HUMAN_AUDIT)
    clean_axis(ax)
    ax2.grid(False)
    sns.despine(ax=ax, right=False)

    ax = ax_c
    add_panel_label(ax, "c")
    rpanel = rand[(rand["alpha"].eq(0.2)) & (rand["rho"].eq(0.10)) & (rand["M"].isin([100, 300, 500]))]
    rg = rpanel.groupby("M", as_index=False)[["released", "raw_topM_actual_FTR"]].mean(numeric_only=True).sort_values("M")
    x = np.arange(len(rg))
    ax.bar(x - 0.18, rg["released"], color=COLOR_PARC_RELEASE, width=0.36, label="PARC release")
    ax.scatter(x - 0.18, rg["released"], s=22, color=COLOR_PARC_RELEASE, edgecolor="white", linewidth=0.6, zorder=4)
    ax2 = ax.twinx()
    ax2.plot(x + 0.18, rg["raw_topM_actual_FTR"], marker="o", color=COLOR_RAW_TOPK, linewidth=1.2, label="raw FTR")
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(v)) for v in rg["M"]])
    ax.set_xlabel("K")
    ax.set_ylabel("Mean release")
    ax2.set_ylabel("")
    ax2.tick_params(axis="y", colors=COLOR_RAW_TOPK)
    ax.set_ylim(0, max(10, rg["released"].max() + 10))
    ax2.set_ylim(0, 0.75)
    ax.set_title("Randomized linker refusal")
    clean_axis(ax)
    ax2.grid(False)
    sns.despine(ax=ax, right=False)

    ax = ax_d
    add_panel_label(ax, "d")
    cov_counts = pd.Series(
        {
            "verified\nblocks": coverage["has_verified_positive"].sum(),
            "K50 release\nblocks": coverage["has_k50_release_candidate"].sum(),
            "raw-audit\nblocks": coverage["has_raw_topk_candidate"].sum(),
        }
    )
    ax.bar(np.arange(len(cov_counts)), cov_counts.values, color=[COLOR_REFUSAL, COLOR_HUMAN_AUDIT, COLOR_RAW_TOPK], width=0.58)
    ax.set_xticks(np.arange(len(cov_counts)))
    ax.set_xticklabels(cov_counts.index)
    ax.set_ylabel("AOI-time blocks")
    ax.set_ylim(0, 145)
    ax.set_yticks([0, 50, 100, 150])
    ax.set_title("Audit block coverage")
    clean_axis(ax)

    fig.tight_layout()
    save(fig, "figure_3_spacenet7_release_certification.pdf")


def plot_scoped_openworld_generality() -> None:
    ow = pd.read_csv(DATA / "table_main_raw_vs_parc_summary.csv")
    ow = ow[ow["paper_table_scope"].eq("main_protocol_summary")].copy()
    ow["label"] = (
        ow["dataset"].astype(str)
        + " / "
        + ow["generator"].astype(str).str.replace("GroundingDINO", "GD", regex=False)
    )
    show_order = [
        "OVT-B / GD + tracker",
        "OVT-B / GD detector-only",
        "BURST / GD",
        "TAO / GD + tracker",
        "OVT-B / OWLv2",
        "TAO / OWLv2",
        "BURST / OWLv2",
    ]
    ow = ow[ow["label"].isin(show_order)].copy()
    ow["label"] = pd.Categorical(ow["label"], categories=show_order, ordered=True)
    ow = ow.sort_values("label")

    lvis = pd.read_csv(DATA / "table_lvis_raw_detector_vs_parc.csv")
    lvis_rows = []
    raw = lvis[lvis["policy"].eq("raw detector top-M")]
    for _, r in raw.iterrows():
        lvis_rows.append(
            {
                "label": f"{r['detector']} raw",
                "release": r["released"],
                "unsupported": r["official_unsupported_rate"],
                "kind": "raw",
            }
        )
    parc = lvis[(lvis["policy"].eq("PARC certified release")) & (lvis["certified_risk_target_alpha"].eq(0.1))]
    for det, g in parc.groupby("detector"):
        lvis_rows.append(
            {
                "label": f"{det} PARC\nalpha=0.10",
                "release": g["released"].mean(),
                "unsupported": g["official_unsupported_rate"].mean(),
                "kind": "PARC",
            }
        )
    lvis_df = pd.DataFrame(lvis_rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15), gridspec_kw={"width_ratios": [1.25, 1.0]})

    ax = axes[0]
    add_panel_label(ax, "a")
    y = np.arange(len(ow))
    colors = np.where(ow["parc_released_mean"] > 0, COLORS["blue"], COLORS["gray"])
    ax.barh(y, ow["parc_released_mean"], color=colors, alpha=0.86)
    ax.set_yticks(y)
    ax.set_yticklabels(ow["label"])
    ax.set_xlabel("Mean released candidates")
    ax.set_title("Path/track generality")
    ax.set_xlim(0, 160)
    ax.grid(True, axis="x", color="#E6E6E6", linewidth=0.5)
    for yi, (_, r) in zip(y, ow.iterrows()):
        if r["parc_released_mean"] == 0:
            ax.text(4, yi, "refusal", va="center", fontsize=6.4, color=COLORS["dark"])
    ax.invert_yaxis()
    sns.despine(ax=ax)

    ax = axes[1]
    add_panel_label(ax, "b")
    x = np.arange(len(lvis_df))
    bar_colors = [COLORS["gray"] if k == "raw" else COLORS["blue"] for k in lvis_df["kind"]]
    ax.bar(x, lvis_df["release"], color=bar_colors, alpha=0.82, width=0.64)
    ax2 = ax.twinx()
    ax2.plot(x, lvis_df["unsupported"], color=COLORS["red"], marker="o", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(lvis_df["label"], rotation=25, ha="right")
    ax.set_ylabel("Mean release")
    ax2.set_ylabel("Official-unsupported proxy", color=COLORS["red"])
    ax2.tick_params(axis="y", colors=COLORS["red"])
    ax.set_ylim(0, 165)
    ax2.set_ylim(0, 0.70)
    ax.set_title("LVIS detection scope")
    ax.grid(True, axis="y", color="#E6E6E6", linewidth=0.5)
    sns.despine(ax=ax, right=False)

    fig.tight_layout(w_pad=1.9)
    save(fig, "figure_5_scoped_openworld_generality.pdf")


def plot_extended_protocol_map() -> None:
    df = pd.read_csv(DATA / "table_main_protocol_coverage.csv")
    df["row"] = df["dataset"].astype(str) + " / " + df["generator"].astype(str)
    df["complete"] = pd.to_numeric(df["seeds_present"], errors="coerce").fillna(0)
    order = df.sort_values(["dataset", "generator"])["row"]
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    y = np.arange(len(order))
    colors = np.where(df.set_index("row").loc[order, "main_protocol_status"].str.contains("included", na=False), COLORS["blue"], COLORS["gray"])
    ax.barh(y, df.set_index("row").loc[order, "complete"], color=colors, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(order.str.replace("GroundingDINO", "G-DINO", regex=False))
    ax.set_xlabel("Seeds present")
    ax.set_xlim(0, 3.2)
    ax.set_title("Extended Data Fig. 1: main protocol coverage")
    ax.grid(True, axis="x", color="#E6E6E6", linewidth=0.5)
    sns.despine(fig=fig)
    save(fig, "extended_data_fig1_protocol_coverage.pdf")


def plot_extended_full_baselines() -> None:
    df = pd.read_csv(DATA / "table_baseline_comparison_summary.csv").copy()
    df["label"] = df["baseline"].map(label_baseline)
    fig, ax = plt.subplots(figsize=(6.1, 3.5))
    palette = [COLORS["gray"], "#A5A5A5", "#777777", "#BBBBBB", COLORS["orange"], "#B8712F", COLORS["blue"], COLORS["green"]]
    ax.scatter(df["released_mean"], df["conservative_FTR_mean"], s=58, c=palette[: len(df)], edgecolor="white", linewidth=0.5)
    for _, r in df.iterrows():
        ax.text(r["released_mean"] + 1.5, r["conservative_FTR_mean"], r["label"], fontsize=6.2, va="center")
    ax.set_xlabel("Mean released paths")
    ax.set_ylabel("Conservative FTR diagnostic")
    ax.set_title("Extended Data Fig. 2: full baseline frontier")
    ax.set_xlim(45, 166)
    ax.set_ylim(-0.035, 0.64)
    ax.grid(True, color="#E6E6E6", linewidth=0.5)
    sns.despine(fig=fig)
    save(fig, "extended_data_fig2_full_baseline_frontier.pdf")


def plot_extended_ablation_heatmap() -> None:
    df = pd.read_csv(DATA / "table_ablation_components.csv")
    keep = df.groupby("component", as_index=False)[["released", "conservative_FTR", "mass_ratio"]].mean(numeric_only=True)
    keep = keep.dropna(subset=["released"]).sort_values("released", ascending=False).head(12)
    mat = keep.set_index("component")[["released", "conservative_FTR", "mass_ratio"]]
    norm = mat.copy()
    norm["released"] = norm["released"] / max(norm["released"].max(), 1)
    norm["conservative_FTR"] = norm["conservative_FTR"] / max(norm["conservative_FTR"].max(), 1e-9)
    norm["mass_ratio"] = norm["mass_ratio"] / max(norm["mass_ratio"].max(), 1e-9)
    fig, ax = plt.subplots(figsize=(6.3, 4.0))
    sns.heatmap(norm, ax=ax, cmap="YlGnBu", annot=mat.round(3), fmt="", linewidths=0.4, linecolor="white", cbar_kws={"label": "Column-normalized value"})
    ax.set_title("Extended Data Fig. 3: ablation component map")
    ax.set_xlabel("")
    ax.set_ylabel("")
    save(fig, "extended_data_fig3_ablation_heatmap.pdf")


def plot_extended_null_inflation() -> None:
    df = pd.read_csv(DATA / "table_stress_null_inflation.csv")
    piv = df.pivot_table(index="label_keep_rate", columns="uncertain_rate_inflation", values="released", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    sns.heatmap(piv.sort_index(ascending=False), ax=ax, cmap="Blues", annot=True, fmt=".0f", linewidths=0.4, linecolor="white", cbar_kws={"label": "Mean release"})
    ax.set_xlabel("Uncertain-rate inflation")
    ax.set_ylabel("Label keep rate")
    ax.set_title("Extended Data Fig. 4: null-inflation sensitivity")
    save(fig, "extended_data_fig4_null_inflation.pdf")


def plot_extended_nonexchangeability() -> None:
    df = pd.read_csv(DATA / "table_stress_nonexchangeability.csv")
    g = df.groupby(["shift_scenario", "result_status"], as_index=False)["released"].mean()
    g["label"] = g["shift_scenario"].map(clean_shift_label)
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    sns.barplot(data=g, y="label", x="released", hue="result_status", ax=ax, palette=[COLORS["green"], COLORS["sky"]])
    ax.set_xlabel("Mean release")
    ax.set_ylabel("")
    ax.set_title("Extended Data Fig. 5: non-exchangeability shifts")
    ax.legend(title="", fontsize=6.0, loc="lower right")
    sns.despine(fig=fig)
    save(fig, "extended_data_fig5_nonexchangeability.pdf")


def plot_extended_audit_noise() -> None:
    df = pd.read_csv(DATA / "table_stress_audit_noise.csv")
    fig, ax = plt.subplots(figsize=(5.9, 3.3))
    sns.lineplot(data=df, x="noise_rate", y="conservative_FTR", hue="noise_type", marker="o", ax=ax)
    ax.set_xlabel("Noise rate")
    ax.set_ylabel("Conservative FTR")
    ax.set_title("Extended Data Fig. 6: audit-noise sensitivity")
    ax.legend(title="", fontsize=6.0)
    sns.despine(fig=fig)
    save(fig, "extended_data_fig6_audit_noise.pdf")


def plot_extended_audit_matrix() -> None:
    counts = pd.read_csv(DATA / "audit_labels_2000_human_reviewed_summary.csv")
    review = pd.read_csv(DATA / "audit2000_reannotation_agreement_summary.csv").iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.1), gridspec_kw={"width_ratios": [1.2, 1.0]})
    sns.barplot(data=counts, x="count", y="label", hue="dataset", ax=axes[0])
    axes[0].set_title("Audit2000 composition")
    axes[0].set_xlabel("Rows")
    axes[0].set_ylabel("")
    mat = pd.DataFrame(
        [[1902, 0, 25], [0, 33, 0], [0, 0, 40]],
        index=["true", "false", "uncertain"],
        columns=["true", "false", "uncertain"],
    )
    sns.heatmap(mat, ax=axes[1], cmap="Greens", annot=True, fmt="d", cbar=False, linewidths=0.4, linecolor="white")
    axes[1].set_title(f"Blind reannotation kappa={review['cohens_kappa']:.3f}")
    axes[1].set_xlabel("Round 2")
    axes[1].set_ylabel("Round 1")
    save(fig, "extended_data_fig7_audit_matrix.pdf")


def plot_extended_lvis() -> None:
    df = pd.read_csv(DATA / "table_lvis_detection_main.csv")
    g = df.groupby(["detector", "certified_risk_target_alpha", "interpretation"], as_index=False)["released"].mean()
    fig, ax = plt.subplots(figsize=(5.7, 3.0))
    sns.barplot(data=g, x="detector", y="released", hue="certified_risk_target_alpha", ax=ax, palette=[COLORS["blue"], COLORS["sky"]])
    ax.set_xlabel("Detector")
    ax.set_ylabel("Mean release")
    ax.set_title("Extended Data Fig. 8: scoped LVIS detection evidence")
    ax.legend(title="alpha", fontsize=6.0)
    sns.despine(fig=fig)
    save(fig, "extended_data_fig8_lvis_detection.pdf")


def plot_extended_mask_path() -> None:
    df = pd.read_csv(DATA / "table_mask_path_proof_of_principle.csv")
    g = df.groupby(["certified_risk_target_alpha", "mask_iou_threshold"], as_index=False)["released"].mean()
    fig, ax = plt.subplots(figsize=(5.7, 3.0))
    sns.lineplot(data=g, x="mask_iou_threshold", y="released", hue="certified_risk_target_alpha", marker="o", ax=ax)
    ax.set_xlabel("Mask IoU threshold")
    ax.set_ylabel("Mean release")
    ax.set_title("Extended Data Fig. 9: mask-path proof of principle")
    ax.legend(title="alpha", fontsize=6.0)
    sns.despine(fig=fig)
    save(fig, "extended_data_fig9_mask_path.pdf")


def main() -> None:
    plot_parc_overview()
    plot_primary_certificate_matrix()
    plot_strict_scientific_flagships()
    plot_human_audit_operating_envelopes()
    plot_cross_domain_certification_atlas()
    plot_ctc_release_certification()
    plot_materials_discovery_certification()
    plot_spacenet_release_certification()
    plot_risk_utility()
    plot_baseline_frontier_inset()
    plot_safe_refusal()
    plot_stress()
    plot_stratified()
    plot_qualitative_examples()
    plot_visual_release_refusal_examples()
    plot_iwildcam_operating_envelope()
    plot_scoped_openworld_generality()
    plot_extended_protocol_map()
    plot_extended_full_baselines()
    plot_extended_ablation_heatmap()
    plot_extended_null_inflation()
    plot_extended_nonexchangeability()
    plot_extended_audit_noise()
    plot_extended_audit_matrix()
    plot_extended_lvis()
    plot_extended_mask_path()


if __name__ == "__main__":
    main()
