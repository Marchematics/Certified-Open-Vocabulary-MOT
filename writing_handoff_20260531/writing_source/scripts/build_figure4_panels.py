from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from figures.style import (
    COLOR_BASELINE,
    COLOR_GUARDRAIL,
    COLOR_PARC_RELEASE,
    COLOR_REFUSAL,
    COLOR_TARGET,
    TINT_REFUSE_ZONE,
    TINT_RELEASE_OK,
    apply_nmi_style,
)

DATA = ROOT / "data"
OUT = ROOT / "figures" / "figure4_assets" / "rebuild"


def df(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def style_axis(ax: plt.Axes, grid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_TARGET)
    ax.spines["bottom"].set_color(COLOR_TARGET)
    ax.tick_params(colors=COLOR_TARGET, width=0.6, length=2.5)
    if grid:
        ax.grid(axis="y", color="#E7E7E7", linewidth=0.35, zorder=0)


def value_label(ax: plt.Axes, x, y, text, dy=0.015, color=COLOR_TARGET, size=6.0) -> None:
    ax.text(x, y + dy, text, color=color, fontsize=size, ha="center", va="bottom")


def save_panel(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / f"{stem}.pdf"
    png = OUT / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.01)
    fig.savefig(png, bbox_inches="tight", pad_inches=0.01, dpi=600)
    plt.close(fig)
    print(f"wrote {pdf.relative_to(ROOT)} and {png.relative_to(ROOT)}")


def load_audit():
    iw_counts = df("table_iwildcam_calibration_label_counts.csv")
    iw_primary = df("table_iwildcam_human_audit_primary_results.csv")
    iw_second = df("table_iwildcam_second_review_agreement_summary.csv")
    sn_cal = df("table_spacenet7_real_audit_calibration_summary.csv").iloc[0]
    sn_k50 = df("table_spacenet7_real_audit_k50_completed_summary.csv").iloc[0]
    sn_k100 = df("table_spacenet7_real_audit_k100_failure_summary.csv").iloc[0]
    sn_release = df("table_spacenet7_real_audit_k50_release_audit.csv").iloc[0]
    return iw_counts, iw_primary, iw_second, sn_cal, sn_k50, sn_k100, sn_release


def panel_a_iwild_counts(iw_counts: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.55))
    animal = int(iw_counts[iw_counts["human_label"] == "animal"]["count"].iloc[0])
    not_animal = int(iw_counts[iw_counts["human_label"] == "not_animal"]["count"].iloc[0])
    ax.bar([0], [animal], color=COLOR_PARC_RELEASE, width=0.6, label="animal", zorder=3)
    ax.bar([0], [not_animal], bottom=[animal], color=COLOR_BASELINE, width=0.6, label="not animal", zorder=2)
    ax.text(0, animal / 2, f"{animal}", color="white", ha="center", va="center", fontsize=7, fontweight="bold")
    ax.text(0, animal + not_animal / 2, f"{not_animal}", color=COLOR_TARGET, ha="center", va="center", fontsize=7, fontweight="bold")
    ax.set_xticks([0])
    ax.set_xticklabels(["iWildCam\ncalibration"])
    ax.set_ylabel("Audited candidates")
    ax.set_ylim(0, 2150)
    ax.legend(loc="upper right", fontsize=5.4)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_4a_iwild_counts")


def panel_b_spacenet_counts(sn_cal: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.55))
    true = int(sn_cal["n_true_same_building"])
    false = int(sn_cal["n_false_link"])
    ax.bar([0], [true], color=COLOR_PARC_RELEASE, width=0.6, label="same building", zorder=3)
    ax.bar([0], [false], bottom=[true], color=COLOR_GUARDRAIL, width=0.6, label="false link", zorder=4)
    ax.text(0, true / 2, f"{true}", color="white", ha="center", va="center", fontsize=7, fontweight="bold")
    ax.text(0, true + false + 24, f"{false}", color=COLOR_GUARDRAIL, ha="center", fontsize=6.1)
    ax.set_xticks([0])
    ax.set_xticklabels(["SpaceNet\ncalibration"])
    ax.set_ylabel("Audited links")
    ax.set_ylim(0, 860)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_4b_spacenet_counts")


def panel_c_grid() -> None:
    fig, ax = plt.subplots(figsize=(2.05, 1.55))
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["strict / high\nrequest", "operational /\ndiagnostic"], fontsize=5.6)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["SpaceNet", "iWildCam"], fontsize=5.8)
    cells = [
        (0, 1, "refuse", r"$\alpha=.10$", "0/20"),
        (1, 1, "release", r"$\alpha=.20,K=50$", "20/20"),
        (0, 0, "refuse", "K=100", "0/20"),
        (1, 0, "release", "K=50", "18/20"),
    ]
    for x0, y0, outcome, line1, line2 in cells:
        ax.add_patch(Rectangle((x0 - 0.39, y0 - 0.32), 0.78, 0.64, facecolor=TINT_RELEASE_OK if outcome == "release" else TINT_REFUSE_ZONE, edgecolor="#E1E1E1", linewidth=0.55, zorder=0))
        if outcome == "release":
            ax.scatter([x0], [y0 + 0.08], s=58, color=COLOR_PARC_RELEASE, zorder=3)
            txt_color = COLOR_PARC_RELEASE
            decision = "release"
        else:
            ax.scatter([x0], [y0 + 0.08], s=58, facecolors="white", edgecolors=COLOR_REFUSAL, linewidths=1.1, zorder=3)
            txt_color = COLOR_REFUSAL
            decision = "refusal"
        ax.text(x0, y0 - 0.08, line1, ha="center", va="center", fontsize=5.9, color=COLOR_TARGET)
        ax.text(x0, y0 - 0.24, f"{decision}, {line2}", ha="center", va="center", fontsize=5.3, color=txt_color)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout(pad=0.20)
    save_panel(fig, "figure_4c_release_refuse_grid")


def panel_d_mass(iw_primary: pd.DataFrame, sn_k50: pd.Series, sn_k100: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(1.75, 1.55))
    pts = [
        ("iWild\nstrict", iw_primary[(iw_primary["alpha"] == 0.10) & (iw_primary["K"] == 50)].iloc[0]["mean_best_mass_ratio"], "refuse"),
        ("iWild\nop.", iw_primary[(iw_primary["alpha"] == 0.20) & (iw_primary["K"] == 50)].iloc[0]["mean_best_mass_ratio"], "release"),
        ("SN\nK100", sn_k100["mean_best_mass_ratio"], "refuse"),
        ("SN\nK50", sn_k50["mean_mass_ratio"], "release"),
    ]
    for xi, (_, yi, outcome) in enumerate(pts):
        if outcome == "release":
            ax.scatter([xi], [yi], s=54, color=COLOR_PARC_RELEASE, zorder=3)
        else:
            ax.scatter([xi], [yi], s=54, facecolors="white", edgecolors=COLOR_REFUSAL, linewidths=1.1, zorder=3)
        value_label(ax, xi, yi, f"{yi:.2f}", dy=0.06, size=5.6)
    ax.axhline(1, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    ax.set_xticks(np.arange(len(pts)))
    ax.set_xticklabels([p[0] for p in pts], fontsize=5.2)
    ax.set_ylabel("Mass ratio")
    ax.set_ylim(0, 1.55)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_4d_mass_ratio")


def panel_e_reliability(iw_second: pd.DataFrame, sn_release: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(3.0, 1.55))
    rows = iw_second.set_index("scope")
    rel_agree = float(rows.loc["all_release_candidates", "label_agreement"])
    all_agree = float(rows.loc["all_rows", "label_agreement"])
    kappa = float(rows.loc["all_rows", "cohen_kappa"])
    klo = float(rows.loc["all_rows", "cohen_kappa_bootstrap95_low"])
    khi = float(rows.loc["all_rows", "cohen_kappa_bootstrap95_high"])
    sn_agree = sn_release["n_true_same_building"] / sn_release["n_audited"]
    vals = [rel_agree, sn_agree, all_agree, kappa]
    labels = ["iWild release\n167/167", "SpaceNet release\n147/147", "iWild all\n1,123 rows", "Cohen's\nkappa"]
    cols = [COLOR_PARC_RELEASE, COLOR_PARC_RELEASE, COLOR_BASELINE, COLOR_PARC_RELEASE]
    ax.bar(np.arange(4), vals, color=cols, width=0.58, zorder=3)
    ax.errorbar([3], [kappa], yerr=[[kappa - klo], [khi - kappa]], fmt="none", ecolor=COLOR_TARGET, capsize=2.2, elinewidth=0.75, zorder=4)
    for xi, yi in enumerate(vals):
        lab = "1.000" if yi == 1 else f"{yi:.3f}"
        value_label(ax, xi, yi, lab, dy=0.018, size=5.7)
    ax.set_xticks(np.arange(4))
    ax.set_xticklabels(labels, fontsize=5.3)
    ax.set_ylabel("Agreement / reliability")
    ax.set_ylim(0, 1.12)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_4e_reliability")


def panel_f_strict_boundary(iw_primary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.55))
    strict = iw_primary[(iw_primary["alpha"] == 0.10) & (iw_primary["K"] == 50)].iloc[0]
    vals = [strict["max_observed_e"], strict["required_e"]]
    bars = ax.bar([0, 1], vals, color=[COLOR_REFUSAL, COLOR_TARGET], width=0.55, zorder=3)
    bars[0].set_facecolor("white")
    bars[0].set_edgecolor(COLOR_REFUSAL)
    bars[0].set_hatch("//")
    for xi, yi in enumerate(vals):
        value_label(ax, xi, yi, f"{yi:.2f}" if xi == 0 else f"{yi:.0f}", dy=0.25, size=5.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["max e", "required e"], rotation=15, ha="right")
    ax.set_ylabel(r"Strict $\alpha=0.10$")
    ax.set_ylim(0, 11.5)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_4f_strict_boundary")


def panel_g_second_review(iw_second: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.55))
    rows = iw_second.set_index("scope")
    all_rows = rows.loc["all_rows"]
    n_rows = int(all_rows["n_rows"])
    n_dis = int(all_rows["n_disagreements"])
    n_agree = n_rows - n_dis
    ax.bar([0], [n_agree], color=COLOR_PARC_RELEASE, width=0.55, zorder=3)
    ax.bar([0], [n_dis], bottom=[n_agree], color=COLOR_GUARDRAIL, width=0.55, zorder=4)
    ax.text(0, n_agree / 2, f"{n_agree}", ha="center", va="center", color="white", fontsize=7, fontweight="bold")
    ax.text(0, n_agree + n_dis / 2, f"{n_dis}", ha="center", va="center", color=COLOR_TARGET, fontsize=6)
    ax.set_xticks([0])
    ax.set_xticklabels(["blind\nsecond review"])
    ax.set_ylabel("Rows")
    ax.set_ylim(0, n_rows * 1.12)
    ax.text(0.50, 1.045, "agreement 0.902", transform=ax.transAxes, ha="center", va="bottom", fontsize=5.6, color=COLOR_TARGET, clip_on=False)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_4g_second_review")


def main() -> None:
    apply_nmi_style(plt)
    iw_counts, iw_primary, iw_second, sn_cal, sn_k50, sn_k100, sn_release = load_audit()
    panel_a_iwild_counts(iw_counts)
    panel_b_spacenet_counts(sn_cal)
    panel_c_grid()
    panel_d_mass(iw_primary, sn_k50, sn_k100)
    panel_e_reliability(iw_second, sn_release)
    panel_f_strict_boundary(iw_primary)
    panel_g_second_review(iw_second)


if __name__ == "__main__":
    main()
