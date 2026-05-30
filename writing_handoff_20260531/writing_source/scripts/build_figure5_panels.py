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

from figures.style import (
    COLOR_BASELINE,
    COLOR_GUARDRAIL,
    COLOR_PARC_RELEASE,
    COLOR_TARGET,
    TINT_UNSAFE,
    apply_nmi_style,
)

DATA = ROOT / "data"
OUT = ROOT / "figures" / "figure5_assets" / "rebuild"


def clean_axis(ax: plt.Axes, grid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(axis="y", color="#E7E7E7", lw=0.35)
        ax.set_axisbelow(True)


def save_panel(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / f"{stem}.pdf"
    png = OUT / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.01)
    fig.savefig(png, bbox_inches="tight", pad_inches=0.01, dpi=600)
    plt.close(fig)
    print(f"wrote {pdf.relative_to(ROOT)} and {png.relative_to(ROOT)}")


def variant_label(v: str) -> str:
    return {
        "exact_stable": "exact",
        "exact_stable_primary": "exact",
        "tolerance_positive_25meV": "tol +25",
        "margin_excluded_25meV": "margin excl.",
        "conservative_clear_stable_observed_25meV": "clear stable",
    }.get(v, v.replace("_", " "))


def panel_a_threshold(thr: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.75, 1.65))
    endpoints = [
        ("cgcnn_ensemble_learned_materials_model", 100, "CGCNN K=100"),
        ("alignn_ff_modern_learned_materials_model", 300, "ALIGNN K=300"),
    ]
    variants = [
        "exact_stable_primary",
        "tolerance_positive_25meV",
        "margin_excluded_25meV",
        "conservative_clear_stable_observed_25meV",
    ]
    x = np.arange(len(variants))
    width = 0.34
    for j, (src, k, label) in enumerate(endpoints):
        vals, lows, highs = [], [], []
        for v in variants:
            row = thr[(thr["proposal_source"].eq(src)) & (thr["K"].eq(k)) & (thr["variant"].eq(v))].iloc[0]
            vals.append(float(row["actual_FTR_mean"]))
            lows.append(float(row["actual_FTR_bootstrap95_low"]))
            highs.append(float(row["actual_FTR_bootstrap95_high"]))
        xpos = x + (j - 0.5) * width
        color = COLOR_PARC_RELEASE if j == 0 else COLOR_GUARDRAIL
        ax.bar(xpos, vals, width=width, color=color, alpha=0.90 if j == 0 else 0.75, label=label)
        ax.errorbar(xpos, vals, yerr=[np.array(vals) - np.array(lows), np.array(highs) - np.array(vals)], fmt="none", ecolor=COLOR_TARGET, lw=0.55, capsize=1.5, zorder=4)
        for xx, yy in zip(xpos, vals):
            ax.text(xx, yy + 0.006, f"{yy:.3f}", ha="center", va="bottom", fontsize=5.5, color=COLOR_TARGET)
    ax.axhspan(0.10, 0.155, color=TINT_UNSAFE, alpha=0.45, zorder=0)
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.text(3.48, 0.104, r"$\alpha=0.10$", fontsize=5.8, color=COLOR_TARGET, ha="right", va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels([variant_label(v) for v in variants], rotation=0, fontsize=5.8)
    ax.set_ylabel("Realized FTR")
    ax.set_ylim(0, 0.155)
    ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=5.8)
    clean_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_5a_threshold_robustness")


def panel_b_raw_vs_parc(raw: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(2.05, 1.65))
    labels = [f"K={int(r.K)}\na={r.alpha:g}" for _, r in raw.iterrows()]
    xs = np.arange(len(labels))
    w = 0.23
    ax.bar(xs - w, raw["raw_topK_FTR"], width=w, color=COLOR_BASELINE, label="raw top-K")
    ax.bar(xs, raw["raw_topR_FTR"], width=w, color="white", edgecolor=COLOR_BASELINE, hatch="//", label="raw top-R")
    ax.bar(xs + w, raw["PARC_FTR"], width=w, color=COLOR_PARC_RELEASE, label="PARC")
    for offset, col, color in [(-w, "raw_topK_FTR", COLOR_TARGET), (0, "raw_topR_FTR", COLOR_TARGET), (w, "PARC_FTR", COLOR_PARC_RELEASE)]:
        for i, (xx, yy) in enumerate(zip(xs + offset, raw[col])):
            if col == "raw_topR_FTR" and abs(float(yy) - float(raw.iloc[i]["PARC_FTR"])) < 5e-4:
                continue
            ax.text(xx, yy + 0.009, f"{yy:.3f}", ha="center", va="bottom", fontsize=4.5, color=color, rotation=90 if yy > 0.20 else 0)
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=5.4)
    ax.set_ylim(0, 0.36)
    ax.set_ylabel("FTR")
    ax.legend(loc="upper left", frameon=False, fontsize=5.0, handlelength=0.9, borderpad=0.1, labelspacing=0.2)
    clean_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_5b_matched_volume")


def panel_c_gamma(gamma: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.75, 1.75))
    sub = gamma[gamma["proposal_source"].str.contains("alignn")].copy()
    ks = [100, 300, 500, 1000]
    gammas = sorted(sub["gamma"].unique())
    mat = np.full((len(ks), len(gammas)), np.nan)
    for i, k in enumerate(ks):
        for j, g in enumerate(gammas):
            row = sub[(sub["K"].eq(k)) & (sub["gamma"].eq(g))]
            if not row.empty:
                mat[i, j] = float(row.iloc[0]["actual_FTR_mean"])
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=0.12, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isfinite(mat[i, j]):
                ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center", fontsize=5.0, color=COLOR_TARGET)
    ax.set_xticks(np.arange(len(gammas)))
    ax.set_xticklabels([f"{g:.2g}" for g in gammas], fontsize=5.5)
    ax.set_yticks(np.arange(len(ks)))
    ax.set_yticklabels([str(k) for k in ks])
    ax.set_xlabel("fixed gamma")
    ax.set_ylabel("K")
    cb = fig.colorbar(im, ax=ax, fraction=0.026, pad=0.02)
    cb.set_label("FTR", fontsize=6)
    cb.ax.tick_params(labelsize=5.5, length=2)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_5c_gamma_heatmap")


def panel_d_boundary(thr: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(2.05, 1.75))
    boundary = thr[
        thr["variant"].eq("margin_excluded_25meV")
        & thr["proposal_source"].str.contains("alignn")
        & thr["K"].eq(100)
    ].iloc[0]
    val = float(boundary["actual_FTR_mean"])
    lo = float(boundary["actual_FTR_bootstrap95_low"])
    hi = float(boundary["actual_FTR_bootstrap95_high"])
    ax.bar([0], [val], color=COLOR_GUARDRAIL, width=0.45)
    ax.errorbar([0], [val], yerr=[[val - lo], [hi - val]], fmt="none", ecolor=COLOR_TARGET, lw=0.65, capsize=2)
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax.text(0.22, 0.104, r"$\alpha=0.10$", fontsize=5.8, color=COLOR_TARGET, va="bottom")
    ax.text(0, val + 0.014, f"{val:.3f}", ha="center", va="bottom", fontsize=6.0, color=COLOR_TARGET)
    ax.set_xticks([0])
    ax.set_xticklabels(["ALIGNN\nmargin excl.\nK=100"], fontsize=5.8)
    ax.set_ylim(0, 0.155)
    ax.text(0.0, 0.015, "boundary\nsensitivity", ha="center", va="bottom", fontsize=5.8, color=COLOR_TARGET)
    clean_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_5d_boundary_case")


def main() -> None:
    apply_nmi_style(plt)
    thr = pd.read_csv(DATA / "materials_threshold_robustness_figure.csv")
    raw = pd.read_csv(DATA / "materials_raw_vs_parc_ftr_panel.csv")
    gamma = pd.read_csv(DATA / "materials_gamma_sensitivity_heatmap.csv")
    panel_a_threshold(thr)
    panel_b_raw_vs_parc(raw)
    panel_c_gamma(gamma)
    panel_d_boundary(thr)


if __name__ == "__main__":
    main()
