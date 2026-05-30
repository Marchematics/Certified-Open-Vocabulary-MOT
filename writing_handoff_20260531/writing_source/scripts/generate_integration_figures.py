"""Generate paper-facing integration figures from newly added diagnostics."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"
sys.path.insert(0, str(ROOT))

from figures.style import (  # noqa: E402
    COLOR_BASELINE,
    COLOR_GUARDRAIL,
    COLOR_PARC_RELEASE,
    COLOR_REFUSAL,
    COLOR_TARGET,
    TINT_UNSAFE,
    apply_nmi_style,
    panel_letter,
)


def clean_axis(ax, grid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(axis="y", color="#E7E7E7", lw=0.35)
        ax.set_axisbelow(True)


def save(fig, name: str) -> None:
    fig.savefig(FIG / name, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(FIG / name.replace(".pdf", ".png"), dpi=600, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def variant_label(v: str) -> str:
    return {
        "exact_stable": "exact",
        "exact_stable_primary": "exact",
        "tolerance_positive_25meV": "tol +25",
        "margin_excluded_25meV": "margin excl.",
        "conservative_clear_stable_observed_25meV": "clear stable",
    }.get(v, v.replace("_", " "))


def source_label(s: str) -> str:
    if "alignn" in s:
        return "ALIGNN"
    if "cgcnn" in s:
        return "CGCNN"
    return s


def generate_materials_robustness() -> None:
    apply_nmi_style(plt)
    thr = pd.read_csv(DATA / "materials_threshold_robustness_figure.csv")
    raw = pd.read_csv(DATA / "materials_raw_vs_parc_ftr_panel.csv")
    gamma = pd.read_csv(DATA / "materials_gamma_sensitivity_heatmap.csv")

    fig = plt.figure(figsize=(7.2, 4.25))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.35, 1.15, 1.05], height_ratios=[1.0, 0.95], hspace=0.55, wspace=0.42)

    # a, stability-definition robustness at the key low/mid-volume endpoints.
    ax_a = fig.add_subplot(gs[0, :2])
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
        vals = []
        lows = []
        highs = []
        for v in variants:
            row = thr[(thr["proposal_source"].eq(src)) & (thr["K"].eq(k)) & (thr["variant"].eq(v))].iloc[0]
            vals.append(float(row["actual_FTR_mean"]))
            lows.append(float(row["actual_FTR_bootstrap95_low"]))
            highs.append(float(row["actual_FTR_bootstrap95_high"]))
        xpos = x + (j - 0.5) * width
        color = COLOR_PARC_RELEASE if j == 0 else COLOR_GUARDRAIL
        ax_a.bar(xpos, vals, width=width, color=color, alpha=0.90 if j == 0 else 0.75, label=label)
        ax_a.errorbar(
            xpos,
            vals,
            yerr=[np.array(vals) - np.array(lows), np.array(highs) - np.array(vals)],
            fmt="none",
            ecolor=COLOR_TARGET,
            lw=0.55,
            capsize=1.5,
            zorder=4,
        )
        for xx, yy in zip(xpos, vals):
            ax_a.text(xx, yy + 0.006, f"{yy:.3f}", ha="center", va="bottom", fontsize=5.8, color=COLOR_TARGET)
    ax_a.axhspan(0.10, 0.155, color=TINT_UNSAFE, alpha=0.45, zorder=0)
    ax_a.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax_a.text(3.48, 0.104, "alpha=0.10", fontsize=6.0, color=COLOR_TARGET, ha="right", va="bottom")
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([variant_label(v) for v in variants], rotation=0)
    ax_a.set_ylabel("Realized FTR")
    ax_a.set_ylim(0, 0.155)
    ax_a.legend(loc="upper left", ncol=2, frameon=False)
    clean_axis(ax_a)
    panel_letter(ax_a, "a")

    # b, practical raw-vs-PARC FTR comparison, including a matched-volume
    # raw prefix diagnostic so the release-error reduction is not overread as
    # a pure method-vs-ranking gain when PARC releases fewer candidates.
    ax_b = fig.add_subplot(gs[0, 2])
    labels = [f"K={int(r.K)}\na={r.alpha:g}" for _, r in raw.iterrows()]
    xs = np.arange(len(labels))
    w = 0.23
    ax_b.bar(xs - w, raw["raw_topK_FTR"], width=w, color=COLOR_BASELINE, label="raw top-K")
    ax_b.bar(xs, raw["raw_topR_FTR"], width=w, color="white", edgecolor=COLOR_BASELINE, hatch="//", label="raw top-R")
    ax_b.bar(xs + w, raw["PARC_FTR"], width=w, color=COLOR_PARC_RELEASE, label="PARC")
    for offset, col, color in [(-w, "raw_topK_FTR", COLOR_TARGET), (0, "raw_topR_FTR", COLOR_TARGET), (w, "PARC_FTR", COLOR_PARC_RELEASE)]:
        for i, (xx, yy) in enumerate(zip(xs + offset, raw[col])):
            if col == "raw_topR_FTR" and abs(float(yy) - float(raw.iloc[i]["PARC_FTR"])) < 5e-4:
                continue
            ax_b.text(xx, yy + 0.009, f"{yy:.3f}", ha="center", va="bottom", fontsize=4.6, color=color, rotation=90 if yy > 0.20 else 0)
    ax_b.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels(labels)
    ax_b.set_ylim(0, 0.36)
    ax_b.set_ylabel("FTR")
    ax_b.legend(loc="upper left", frameon=False, fontsize=5.2, handlelength=0.9, borderpad=0.1, labelspacing=0.2)
    clean_axis(ax_b)
    panel_letter(ax_b, "b")

    # c, fixed-gamma sensitivity heatmap for ALIGNN.
    ax_c = fig.add_subplot(gs[1, :2])
    sub = gamma[gamma["proposal_source"].str.contains("alignn")].copy()
    ks = [100, 300, 500, 1000]
    gammas = sorted(sub["gamma"].unique())
    mat = np.full((len(ks), len(gammas)), np.nan)
    for i, k in enumerate(ks):
        for j, g in enumerate(gammas):
            row = sub[(sub["K"].eq(k)) & (sub["gamma"].eq(g))]
            if not row.empty:
                mat[i, j] = float(row.iloc[0]["actual_FTR_mean"])
    im = ax_c.imshow(mat, cmap="Blues", vmin=0, vmax=0.12, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isfinite(mat[i, j]):
                ax_c.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center", fontsize=5.2, color=COLOR_TARGET)
    ax_c.set_xticks(np.arange(len(gammas)))
    ax_c.set_xticklabels([f"{g:.2g}" for g in gammas])
    ax_c.set_yticks(np.arange(len(ks)))
    ax_c.set_yticklabels([str(k) for k in ks])
    ax_c.set_xlabel("fixed gamma")
    ax_c.set_ylabel("K")
    cb = fig.colorbar(im, ax=ax_c, fraction=0.026, pad=0.02)
    cb.set_label("FTR", fontsize=6)
    cb.ax.tick_params(labelsize=5.5, length=2)
    panel_letter(ax_c, "c")

    # d, boundary case annotation.
    ax_d = fig.add_subplot(gs[1, 2])
    boundary = thr[
        thr["variant"].eq("margin_excluded_25meV")
        & thr["proposal_source"].str.contains("alignn")
        & thr["K"].eq(100)
    ].iloc[0]
    val = float(boundary["actual_FTR_mean"])
    lo = float(boundary["actual_FTR_bootstrap95_low"])
    hi = float(boundary["actual_FTR_bootstrap95_high"])
    ax_d.bar([0], [val], color=COLOR_GUARDRAIL, width=0.45)
    ax_d.errorbar([0], [val], yerr=[[val - lo], [hi - val]], fmt="none", ecolor=COLOR_TARGET, lw=0.65, capsize=2)
    ax_d.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (3, 2)))
    ax_d.text(0.22, 0.104, "alpha=0.10", fontsize=6, color=COLOR_TARGET, va="bottom")
    ax_d.text(0, val + 0.014, f"{val:.3f}", ha="center", va="bottom", fontsize=6.2, color=COLOR_TARGET)
    ax_d.set_xticks([0])
    ax_d.set_xticklabels(["ALIGNN\nmargin excl.\nK=100"])
    ax_d.set_ylim(0, 0.155)
    ax_d.set_ylabel("")
    ax_d.text(0.0, 0.015, "boundary\nsensitivity", ha="center", va="bottom", fontsize=6, color=COLOR_TARGET)
    clean_axis(ax_d)
    panel_letter(ax_d, "d")

    save(fig, "figure_6_materials_robustness.pdf")


def generate_success_domain_map() -> None:
    """Colorblind-safe success-domain map from the paper-ready feature table.

    The remote diagnostic PDF used release/refuse colors and a very compressed
    coverage axis. For the main text, use variables that actually spread:
    evidence mass (x) and raw top-K risk (y), with filled blue markers for
    completed releases and hollow grey markers for certified refusal/boundary
    rows.
    """
    apply_nmi_style(plt)
    fmap = pd.read_csv(DATA / "figure_success_domain_map.csv").copy()
    fmap["phi_plot"] = fmap["phi"].clip(lower=0.02)

    fig, ax = plt.subplots(figsize=(4.05, 2.55))
    ax.axvspan(0.02, 1.0, color="#F4F4F4", alpha=0.9, zorder=0)
    ax.axvline(1.0, color=COLOR_TARGET, lw=0.75, ls=(0, (3, 2)), zorder=1)
    ax.axhline(0.10, color=COLOR_TARGET, lw=0.65, ls=(0, (2, 2)), zorder=1, alpha=0.75)

    ok = fmap["release_success_binary"].astype(bool)
    ax.scatter(
        fmap.loc[~ok, "phi_plot"],
        fmap.loc[~ok, "raw_risk"],
        s=32,
        facecolors="white",
        edgecolors=COLOR_REFUSAL,
        linewidths=0.9,
        alpha=0.95,
        label="refusal / boundary",
        zorder=3,
    )
    ax.scatter(
        fmap.loc[ok, "phi_plot"],
        fmap.loc[ok, "raw_risk"],
        s=42,
        color=COLOR_PARC_RELEASE,
        edgecolors="white",
        linewidths=0.45,
        alpha=0.96,
        label="release",
        zorder=4,
    )

    # Label only the anchor rows; dense diagnostics stay as points.
    anchors = [
        ("CTC", "biomedical_cell_tracking", 1.337801, 0.000000, (1.45, 0.055)),
        ("Materials\nALIGNN", "materials_discovery", 3.956975, 0.253167, (7.2, 0.34)),
        ("materials\nK=5000", "materials_discovery", 0.284823, 0.406510, (0.09, 0.47)),
        ("random\nCTC", "biomedical_cell_tracking", 0.056251, 0.807500, (0.075, 0.73)),
    ]
    for lab, _domain, phi, risk, xytext in anchors:
        nearest = ((np.log(fmap["phi_plot"]) - np.log(max(phi, 0.02))) ** 2 + (fmap["raw_risk"] - risk) ** 2).idxmin()
        ax.annotate(
            lab,
            xy=(fmap.loc[nearest, "phi_plot"], fmap.loc[nearest, "raw_risk"]),
            xytext=xytext,
            textcoords="data",
            arrowprops=dict(arrowstyle="-", lw=0.45, color=COLOR_TARGET),
            fontsize=5.6,
            color=COLOR_TARGET,
            ha="center",
            va="center",
        )

    ax.text(0.022, 0.112, r"$\alpha=0.10$", fontsize=5.6, color=COLOR_TARGET, ha="left", va="bottom")
    ax.set_xscale("log")
    ax.set_xlim(0.02, 22)
    ax.set_ylim(-0.02, 0.88)
    ax.set_xlabel("Evidence mass ratio, $\\Phi$")
    ax.set_ylabel("Raw top-$K$ FTR")
    ax.legend(loc="upper right", fontsize=5.6, handletextpad=0.25, borderpad=0.15)
    clean_axis(ax)
    fig.savefig(FIG / "figure_success_domain_map.pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(FIG / "figure_success_domain_map.png", dpi=600, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


if __name__ == "__main__":
    generate_materials_robustness()
    generate_success_domain_map()
