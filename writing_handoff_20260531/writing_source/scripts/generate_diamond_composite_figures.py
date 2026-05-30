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
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from figures.style import (
    C,
    COLOR_BASELINE,
    COLOR_GUARDRAIL,
    COLOR_PARC_RELEASE,
    COLOR_REFUSAL,
    COLOR_TARGET,
    TINT_REFUSE_ZONE,
    TINT_RELEASE_OK,
    TINT_UNSAFE,
    apply_nmi_style,
    panel_letter,
)


DATA = ROOT / "data"
FIG = ROOT / "figures"

apply_nmi_style(plt)


def df(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def save(fig: plt.Figure, name: str) -> None:
    pdf = FIG / f"{name}.pdf"
    png = FIG / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=600)
    plt.close(fig)
    print(f"wrote {pdf.relative_to(ROOT)} and {png.relative_to(ROOT)}")


def style_axis(ax, grid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_TARGET)
    ax.spines["bottom"].set_color(COLOR_TARGET)
    ax.tick_params(colors=COLOR_TARGET, width=0.6, length=2.5)
    if grid:
        ax.grid(axis="y", color="#E7E7E7", linewidth=0.35, zorder=0)


def add_alpha(ax, alpha: float = 0.10, label: str | None = r"$\alpha=0.10$") -> None:
    ax.axhline(alpha, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75, zorder=1)
    if not label:
        return
    ax.text(
        0.98,
        alpha + 0.004,
        label,
        transform=ax.get_yaxis_transform(),
        fontsize=6.5,
        color=COLOR_TARGET,
        ha="right",
        va="bottom",
    )


def value_label(ax, x, y, text, dy=0.015, color=COLOR_TARGET, ha="center", va="bottom", size=6.2):
    ax.text(x, y + dy, text, color=color, fontsize=size, ha=ha, va=va)


def percent(v: float, nd: int = 1) -> str:
    return f"{100 * v:.{nd}f}%"


def short_block_name(s: str) -> str:
    return {
        "chemical_system": "chemical\nsystem",
        "composition_family_pair": "composition\nfamily",
        "wyckoff_family": "Wyckoff\nfamily",
    }.get(s, s)


def plot_ctc_flagship() -> None:
    main = df("table_ctc_learned_strict_alpha010_smallK.csv")
    rev = df("table_ctc_learned_reverse_split.csv")
    neg = df("table_ctc_learned_negative_control.csv")
    leak = df("table_ctc_learned_leakage_audit.csv")
    unsafe = df("table_prevented_false_releases.csv")

    main = main[(main["alpha"] == 0.10) & (main["rho"] == 0.10)].sort_values("M")
    rev = rev[(rev["alpha"] == 0.10) & (rev["rho"] == 0.10)].sort_values("M")
    neg = neg[(neg["alpha"] == 0.10) & (neg["rho"] == 0.10)].sort_values("M")
    ctc_unsafe = unsafe[unsafe["domain"].str.contains("CTC", na=False)].iloc[0]

    fig = plt.figure(figsize=(7.2, 5.55))
    gs = fig.add_gridspec(
        2,
        4,
        width_ratios=[1.35, 1.0, 1.05, 1.05],
        height_ratios=[1.05, 1.0],
        left=0.055,
        right=0.985,
        top=0.96,
        bottom=0.105,
        wspace=0.48,
        hspace=0.58,
    )

    ax_a = fig.add_subplot(gs[0, 0:2])
    ax_b = fig.add_subplot(gs[0, 2])
    ax_c = fig.add_subplot(gs[0, 3])
    ax_d = fig.add_subplot(gs[1, 0])
    ax_e = fig.add_subplot(gs[1, 1])
    ax_f = fig.add_subplot(gs[1, 2])
    ax_g = fig.add_subplot(gs[1, 3])

    # a. strict-release volume across K and reverse split.
    ax_a.plot(main["M"], main["released_mean"], "-o", color=COLOR_PARC_RELEASE, ms=4.2, label="train 01 -> certify 02")
    ax_a.plot(rev["M"], rev["released_mean"], "--o", color=COLOR_PARC_RELEASE, ms=3.7, alpha=0.70, label="train 02 -> certify 01")
    ax_a.plot(main["M"], main["M"], ":", color=COLOR_BASELINE, linewidth=1.1, label="requested K")
    for _, row in main.iterrows():
        if row["M"] in [10, 100, 300]:
            value_label(ax_a, row["M"], row["released_mean"], f"{int(row['released_mean'])}", dy=7, color=COLOR_PARC_RELEASE, size=6)
    ax_a.set_xscale("log")
    ax_a.set_xticks([10, 25, 50, 100, 300])
    ax_a.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax_a.set_xlabel("Requested links K")
    ax_a.set_ylabel("Mean released links")
    ax_a.set_ylim(-10, 325)
    ax_a.legend(loc="upper left", fontsize=6.2, handlelength=1.5)
    style_axis(ax_a)
    panel_letter(ax_a, "a")

    # b. held-out FTR with bootstrap intervals; use all requested K values so
    # the zero-FTR result reads as a dense certificate row rather than a sparse
    # three-number panel.
    endpoints = []
    for _, r in main.iterrows():
        endpoints.append((f"{int(r['M'])}", r, "main"))
    for _, r in rev.iterrows():
        endpoints.append((f"r{int(r['M'])}", r, "reverse"))
    x = np.arange(len(endpoints))
    vals = np.array([r["actual_FTR_mean"] for _, r, _ in endpoints])
    lo = np.array([r["actual_FTR_bootstrap95_low"] for _, r, _ in endpoints])
    hi = np.array([r["actual_FTR_bootstrap95_high"] for _, r, _ in endpoints])
    is_rev = np.array([kind == "reverse" for _, _, kind in endpoints])
    ax_b.errorbar(
        x[~is_rev],
        vals[~is_rev],
        yerr=[vals[~is_rev] - lo[~is_rev], hi[~is_rev] - vals[~is_rev]],
        fmt="o",
        color=COLOR_PARC_RELEASE,
        ecolor=COLOR_TARGET,
        elinewidth=0.65,
        capsize=1.8,
        ms=3.8,
        zorder=4,
        label="primary",
    )
    ax_b.errorbar(
        x[is_rev],
        vals[is_rev],
        yerr=[vals[is_rev] - lo[is_rev], hi[is_rev] - vals[is_rev]],
        fmt="s",
        mfc="white",
        mec=COLOR_PARC_RELEASE,
        color=COLOR_PARC_RELEASE,
        ecolor=COLOR_TARGET,
        elinewidth=0.65,
        capsize=1.8,
        ms=3.6,
        zorder=4,
        label="reverse",
    )
    for xi, yi in zip(x, vals):
        ax_b.text(xi, 0.006, "0", ha="center", va="bottom", fontsize=4.9, color=COLOR_PARC_RELEASE)
    add_alpha(ax_b)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels([k for k, _, _ in endpoints], rotation=45, ha="right", fontsize=5.0)
    ax_b.set_ylabel("Held-out FTR")
    ax_b.set_ylim(0, 0.12)
    ax_b.legend(loc="upper left", fontsize=5.2, handlelength=1.0, borderpad=0.1)
    style_axis(ax_b)
    panel_letter(ax_b, "b")

    # c. evidence mass ratio.
    ax_c.plot(main["M"], main["best_mass_ratio_mean"], "-o", color=COLOR_PARC_RELEASE, ms=4)
    ax_c.plot(neg["M"], neg["best_mass_ratio_mean"], "^", color=COLOR_GUARDRAIL, ms=4.2, alpha=0.85)
    ax_c.axhline(1.0, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    ax_c.text(0.98, 1.03, "self-consistency", transform=ax_c.get_yaxis_transform(), fontsize=6.2, ha="right", va="bottom", color=COLOR_TARGET)
    ax_c.set_xscale("log")
    ax_c.set_xticks([10, 50, 100, 300])
    ax_c.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax_c.set_xlabel("K")
    ax_c.set_ylabel("Evidence mass ratio")
    ax_c.set_ylim(0, 1.55)
    style_axis(ax_c)
    panel_letter(ax_c, "c")

    # d. reverse split status, shown as a compact release-rate strip.
    ks = [10, 25, 50, 75, 100, 300]
    y = np.ones(len(ks))
    ax_d.scatter(ks, y, s=48, color=COLOR_PARC_RELEASE, zorder=3)
    ax_d.plot(ks, y, color=COLOR_PARC_RELEASE, linewidth=0.9, alpha=0.7)
    for k in ks:
        ax_d.text(k, 1.055, "20/20", fontsize=4.9, ha="center", color=COLOR_PARC_RELEASE)
    ax_d.text(0.04, 0.12, "reverse split\nFTR=0.000", transform=ax_d.transAxes, fontsize=6.0, color=COLOR_TARGET, ha="left", va="bottom")
    ax_d.set_xscale("log")
    ax_d.set_xticks([10, 50, 100, 300])
    ax_d.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax_d.set_yticks([0, 0.5, 1.0])
    ax_d.set_ylim(-0.08, 1.20)
    ax_d.set_xlabel("Reverse-split K")
    ax_d.set_ylabel("Non-empty seed rate")
    style_axis(ax_d)
    panel_letter(ax_d, "d")

    # e. leakage audit status strip.
    ax_e.set_xlim(0, 1)
    ax_e.set_ylim(0, 1)
    ax_e.axis("off")
    checks = [
        ("sequence split", leak["train_eval_overlap"].eq("none").all()),
        ("no GT features", leak["forbidden_GT_or_match_columns_used"].eq("no").all()),
        ("frozen scorer", leak["scorer_frozen_before_PARC"].eq("yes").all()),
        ("held-out eval", leak["held_out_GT_use"].str.contains("after_release").all()),
    ]
    for i, (label, ok) in enumerate(checks):
        y0 = 0.84 - i * 0.21
        ax_e.add_patch(Rectangle((0.03, y0 - 0.07), 0.94, 0.14, facecolor=TINT_RELEASE_OK if ok else TINT_UNSAFE, edgecolor="#E2E2E2", linewidth=0.45))
        ax_e.scatter([0.10], [y0], s=34, color=COLOR_PARC_RELEASE if ok else COLOR_GUARDRAIL, zorder=3)
        ax_e.text(0.18, y0, label, fontsize=6.3, va="center", color=COLOR_TARGET)
        ax_e.text(0.90, y0, "pass" if ok else "check", fontsize=6.0, va="center", ha="right", color=COLOR_PARC_RELEASE if ok else COLOR_GUARDRAIL)
    panel_letter(ax_e, "e")

    # f. random-score negative control.
    random_ks = [10, 50, 100, 300]
    rand = neg[neg["M"].isin(random_ks)].copy()
    x = np.arange(len(rand))
    w = 0.34
    ax_f.bar(x - w / 2, rand["raw_topM_actual_FTR_mean"], width=w, color=COLOR_BASELINE, label="raw top-K FTR", zorder=2)
    ax_f.bar(x + w / 2, rand["released_mean"] / rand["M"], width=w, color=COLOR_REFUSAL, alpha=0.35, edgecolor=COLOR_REFUSAL, label="PARC release fraction", zorder=3)
    for xi, raw in zip(x, rand["raw_topM_actual_FTR_mean"]):
        value_label(ax_f, xi - w / 2, raw, f"{raw:.2f}", dy=0.025, color=COLOR_TARGET, size=5.8)
    ax_f.set_xticks(x)
    ax_f.set_xticklabels([str(int(k)) for k in rand["M"]])
    ax_f.set_xlabel("Random-score K")
    ax_f.set_ylabel("Fraction")
    ax_f.set_ylim(0, 0.95)
    ax_f.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.03),
        fontsize=5.2,
        handlelength=0.9,
        ncols=1,
        borderpad=0.1,
        columnspacing=0.5,
    )
    style_axis(ax_f)
    panel_letter(ax_f, "f")

    # g. high-volume unsafe request.
    vals = [ctc_unsafe["raw_topK_FTR"], ctc_unsafe["PARC_release"]]
    colors = [COLOR_BASELINE, COLOR_REFUSAL]
    labels = ["raw FTR", "PARC release"]
    bars = ax_g.bar(np.arange(2), vals, color=colors, width=0.58, edgecolor=[COLOR_BASELINE, COLOR_REFUSAL], zorder=3)
    bars[1].set_facecolor("white")
    bars[1].set_hatch("//")
    for xi, yi in enumerate(vals):
        value_label(ax_g, xi, yi, f"{yi:.3f}" if yi else "0/20", dy=0.02, color=COLOR_TARGET)
    ax_g.set_xticks([0, 1])
    ax_g.set_xticklabels(labels, rotation=20, ha="right")
    ax_g.set_ylabel("K=5000 fraction")
    ax_g.set_ylim(0, 0.43)
    ax_g.text(0.48, 0.36, "~1,803 false links\nprevented per seed", fontsize=6.0, color=COLOR_TARGET, ha="center", va="top")
    style_axis(ax_g)
    panel_letter(ax_g, "g")

    save(fig, "figure_2_ctc_flagship_fullpage")


def plot_materials_flagship() -> None:
    primary = df("table_materials_primary_results.csv")
    alignn = df("table_materials_modern_model_sensitivity.csv")
    blocks = df("table_materials_block_sensitivity.csv")
    random = df("table_materials_random_score_control.csv")
    high = df("table_materials_high_volume_refusal.csv")

    cg = primary[(primary["proposal_source"].str.contains("cgcnn")) & (primary["rho"] == 0.10) & (primary["alpha"] == 0.10)].sort_values("K")
    al = alignn[(alignn["rho"] == 0.10) & (alignn["alpha"] == 0.10)].sort_values("K")

    fig = plt.figure(figsize=(7.2, 5.70))
    gs = fig.add_gridspec(
        3,
        4,
        width_ratios=[1.25, 1.05, 1.0, 1.0],
        height_ratios=[1.05, 1.0, 0.95],
        left=0.055,
        right=0.985,
        top=0.965,
        bottom=0.10,
        wspace=0.55,
        hspace=0.64,
    )

    ax_a = fig.add_subplot(gs[0:2, 0:2])
    ax_b = fig.add_subplot(gs[0, 2])
    ax_c = fig.add_subplot(gs[0, 3])
    ax_d = fig.add_subplot(gs[1, 2])
    ax_e = fig.add_subplot(gs[1, 3])
    ax_f = fig.add_subplot(gs[2, 0])
    ax_g = fig.add_subplot(gs[2, 1:3])
    ax_h = fig.add_subplot(gs[2, 3])

    # a. ALIGNN raw vs PARC FTR hero.
    hero = al[al["K"].isin([300, 500])].sort_values("K")
    x = np.arange(len(hero))
    w = 0.34
    ax_a.bar(x - w / 2, hero["raw_topK_actual_FTR_mean"], width=w, color=COLOR_BASELINE, label="raw requested K", zorder=2)
    ax_a.bar(x + w / 2, hero["actual_FTR_mean"], width=w, color=COLOR_PARC_RELEASE, label="PARC certified stop", zorder=3)
    yerr = np.vstack([
        hero["actual_FTR_mean"].to_numpy() - hero["actual_FTR_bootstrap95_low"].to_numpy(),
        hero["actual_FTR_bootstrap95_high"].to_numpy() - hero["actual_FTR_mean"].to_numpy(),
    ])
    ax_a.errorbar(x + w / 2, hero["actual_FTR_mean"], yerr=yerr, fmt="none", ecolor=COLOR_TARGET, elinewidth=0.8, capsize=2.2, zorder=4)
    for xi, raw, parc in zip(x, hero["raw_topK_actual_FTR_mean"], hero["actual_FTR_mean"]):
        value_label(ax_a, xi - w / 2, raw, f"{raw:.3f}", dy=0.015, color=COLOR_TARGET)
        value_label(ax_a, xi + w / 2, parc, f"{parc:.3f}", dy=0.015, color=COLOR_PARC_RELEASE)
    add_alpha(ax_a)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([f"K={int(k)}\nR≈{r:.0f}" for k, r in zip(hero["K"], hero["mean_release"])])
    ax_a.set_ylabel("False-release fraction")
    ax_a.set_ylim(0, 0.36)
    ax_a.legend(loc="upper left", fontsize=6.4)
    style_axis(ax_a)
    panel_letter(ax_a, "a")

    # b. CGCNN primary endpoint.
    row100 = cg[cg["K"] == 100].iloc[0]
    ax_b.bar([0], [row100["mean_release"] / row100["K"]], color=COLOR_PARC_RELEASE, width=0.5, zorder=3)
    ax_b.bar([1], [row100["actual_FTR_mean"]], color=COLOR_PARC_RELEASE, width=0.5, zorder=3)
    ax_b.errorbar([1], [row100["actual_FTR_mean"]], yerr=[[row100["actual_FTR_mean"] - row100["actual_FTR_bootstrap95_low"]], [row100["actual_FTR_bootstrap95_high"] - row100["actual_FTR_mean"]]], fmt="none", ecolor=COLOR_TARGET, elinewidth=0.7, capsize=2, zorder=4)
    ax_b.text(0, 1.04, "20/20", ha="center", fontsize=6.2, color=COLOR_PARC_RELEASE)
    ax_b.text(1, row100["actual_FTR_mean"] + 0.020, "0.030", ha="center", fontsize=6.2, color=COLOR_PARC_RELEASE)
    add_alpha(ax_b, label=None)
    ax_b.text(0.10, 0.104, r"$\alpha=0.10$", transform=ax_b.get_yaxis_transform(), fontsize=5.9, color=COLOR_TARGET, ha="left", va="bottom")
    ax_b.set_ylim(0, 1.10)
    ax_b.set_xticks([0, 1])
    ax_b.set_xticklabels(["release/K", "FTR"], rotation=25, ha="right")
    ax_b.set_ylabel("CGCNN K=100")
    style_axis(ax_b)
    panel_letter(ax_b, "b")

    # c. FTR + bootstrap across endpoints.
    endpoints = [
        ("CGCNN\n100", row100),
        ("CGCNN\n300", cg[cg["K"] == 300].iloc[0]),
        ("ALIGNN\n300", hero[hero["K"] == 300].iloc[0]),
        ("ALIGNN\n500", hero[hero["K"] == 500].iloc[0]),
    ]
    x = np.arange(len(endpoints))
    vals = np.array([r["actual_FTR_mean"] for _, r in endpoints])
    lo = np.array([r["actual_FTR_bootstrap95_low"] for _, r in endpoints])
    hi = np.array([r["actual_FTR_bootstrap95_high"] for _, r in endpoints])
    ax_c.errorbar(x, vals, yerr=[vals - lo, hi - vals], fmt="o", color=COLOR_PARC_RELEASE, ecolor=COLOR_TARGET, elinewidth=0.75, capsize=2, ms=4.2, zorder=3)
    for n, (xi, yi) in enumerate(zip(x, vals)):
        dy = 0.008 if n % 2 == 0 else 0.021
        xoff = -0.05 if n % 2 == 0 else 0.05
        ax_c.text(xi + xoff, yi + dy, f"{yi:.3f}", color=COLOR_TARGET, fontsize=5.3, ha="center", va="bottom")
    add_alpha(ax_c, label=None)
    ax_c.text(0.98, 0.145, r"$\alpha=0.10$", transform=ax_c.get_yaxis_transform(), fontsize=5.4, color=COLOR_TARGET, ha="right", va="bottom")
    ax_c.set_xticks(x)
    ax_c.set_xticklabels([k for k, _ in endpoints], rotation=0, fontsize=5.0)
    ax_c.set_ylabel("FTR (95% CI)")
    ax_c.set_ylim(0, 0.17)
    style_axis(ax_c)
    panel_letter(ax_c, "c")

    # d. CGCNN evidence mass.
    ax_d.plot(cg["K"], cg["best_mass_ratio_mean"], "-o", color=COLOR_PARC_RELEASE, ms=4, label="CGCNN")
    ax_d.axhline(1, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    ax_d.set_xscale("log")
    ax_d.set_xticks([50, 100, 300, 1000, 5000])
    ax_d.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax_d.set_xlabel("K")
    ax_d.set_ylabel("Mass ratio")
    ax_d.set_ylim(0, max(cg["best_mass_ratio_mean"].max() * 1.08, 1.2))
    ax_d.text(5000, 1.06, "boundary", fontsize=6.0, ha="right", color=COLOR_TARGET)
    style_axis(ax_d)
    panel_letter(ax_d, "d")

    # e. FTR by chemistry block.
    block100 = blocks[(blocks["K"] == 100) & (blocks["rho"] == 0.10) & (blocks["alpha"] == 0.10)].copy()
    block300 = blocks[(blocks["K"] == 300) & (blocks["rho"] == 0.10) & (blocks["alpha"] == 0.10)].copy()
    order = ["chemical_system", "composition_family_pair", "wyckoff_family"]
    b100 = block100.set_index("block_definition").loc[order]
    b300 = block300.set_index("block_definition").loc[order]
    x = np.arange(len(order))
    ax_e.bar(x - 0.18, b100["actual_FTR_mean"], width=0.34, color=COLOR_PARC_RELEASE, label="K=100", zorder=3)
    ax_e.bar(x + 0.18, b300["actual_FTR_mean"], width=0.34, color=COLOR_BASELINE, label="K=300", zorder=2)
    add_alpha(ax_e)
    ax_e.set_xticks(x)
    ax_e.set_xticklabels([short_block_name(k) for k in order], rotation=0)
    ax_e.set_ylabel("Block-sensitivity FTR")
    ax_e.set_ylim(0, 0.31)
    ax_e.legend(loc="upper left", fontsize=5.8, ncols=1)
    style_axis(ax_e)
    panel_letter(ax_e, "e")

    # f. mass ratio by block at K=300.
    ax_f.bar(x, b300["best_mass_ratio_mean"], color=[COLOR_BASELINE, COLOR_PARC_RELEASE, COLOR_BASELINE], width=0.6, zorder=3)
    ax_f.axhline(1, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    for xi, yi in zip(x, b300["best_mass_ratio_mean"]):
        value_label(ax_f, xi, yi, f"{yi:.1f}", dy=0.18, size=5.8)
    ax_f.set_xticks(x)
    ax_f.set_xticklabels([short_block_name(k) for k in order])
    ax_f.set_ylabel("Mass ratio, K=300")
    ax_f.set_ylim(0, max(32, b300["best_mass_ratio_mean"].max() * 1.15))
    style_axis(ax_f)
    panel_letter(ax_f, "f")

    # g. random-score controls.
    rnd = random[(random["alpha"] == 0.10) & (random["K"].isin([300, 1000]))].copy().sort_values("K")
    x = np.arange(len(rnd))
    ax_g.bar(x - 0.18, rnd["raw_topK_actual_FTR_mean"], width=0.34, color=COLOR_BASELINE, label="raw FTR", zorder=2)
    ax_g.bar(x + 0.18, rnd["mean_release"] / rnd["K"], width=0.34, color="white", edgecolor=COLOR_REFUSAL, hatch="//", label="PARC release/K", zorder=3)
    for xi, yi in zip(x, rnd["raw_topK_actual_FTR_mean"]):
        value_label(ax_g, xi - 0.18, yi, f"{yi:.2f}", dy=0.03, size=5.8)
    ax_g.set_xticks(x)
    ax_g.set_xticklabels([f"K={int(k)}" for k in rnd["K"]])
    ax_g.set_ylabel("Random-score fraction")
    ax_g.set_ylim(0, 1.0)
    ax_g.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.04),
        fontsize=5.4,
        ncols=2,
        handlelength=1.0,
        borderpad=0.1,
        columnspacing=0.6,
    )
    style_axis(ax_g)
    panel_letter(ax_g, "g")

    # h. high-volume refusal.
    hv = high[(high["alpha"] == 0.10) & (high["K"] == 5000)].iloc[0]
    vals = [hv["raw_topK_actual_FTR_mean"], hv["mean_release"] / hv["K"]]
    bars = ax_h.bar([0, 1], vals, width=0.58, color=[COLOR_BASELINE, "white"], edgecolor=[COLOR_BASELINE, COLOR_REFUSAL], zorder=3)
    bars[1].set_hatch("//")
    for xi, yi, lab in zip([0, 1], vals, [f"{vals[0]:.3f}", "0/20"]):
        value_label(ax_h, xi, yi, lab, dy=0.025, size=5.8)
    ax_h.set_xticks([0, 1])
    ax_h.set_xticklabels(["raw FTR", "PARC\nrelease/K"], rotation=20, ha="right")
    ax_h.set_ylabel("K=5000")
    ax_h.set_ylim(0, 0.48)
    style_axis(ax_h)
    panel_letter(ax_h, "h")

    save(fig, "figure_3_materials_flagship_fullpage")


def plot_human_audit_fullpage() -> None:
    iw_counts = df("table_iwildcam_calibration_label_counts.csv")
    iw_primary = df("table_iwildcam_human_audit_primary_results.csv")
    iw_release = df("table_iwildcam_release_audit_summary.csv").iloc[0]
    iw_second = df("table_iwildcam_second_review_agreement_summary.csv")
    sn_cal = df("table_spacenet7_real_audit_calibration_summary.csv").iloc[0]
    sn_k50 = df("table_spacenet7_real_audit_k50_completed_summary.csv").iloc[0]
    sn_k100 = df("table_spacenet7_real_audit_k100_failure_summary.csv").iloc[0]
    sn_release = df("table_spacenet7_real_audit_k50_release_audit.csv").iloc[0]

    fig = plt.figure(figsize=(7.2, 5.55))
    gs = fig.add_gridspec(
        2,
        4,
        width_ratios=[1.05, 1.05, 1.35, 1.15],
        height_ratios=[1.0, 1.0],
        left=0.055,
        right=0.985,
        top=0.96,
        bottom=0.105,
        wspace=0.55,
        hspace=0.58,
    )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[0, 3])
    ax_e = fig.add_subplot(gs[1, 0:2])
    ax_f = fig.add_subplot(gs[1, 2])
    ax_g = fig.add_subplot(gs[1, 3])

    # a. iWildCam audit composition.
    animal = int(iw_counts[iw_counts["human_label"] == "animal"]["count"].iloc[0])
    not_animal = int(iw_counts[iw_counts["human_label"] == "not_animal"]["count"].iloc[0])
    ax_a.bar([0], [animal], color=COLOR_PARC_RELEASE, width=0.6, label="animal", zorder=3)
    ax_a.bar([0], [not_animal], bottom=[animal], color=COLOR_BASELINE, width=0.6, label="not animal", zorder=2)
    ax_a.text(0, animal / 2, f"{animal}", color="white", ha="center", va="center", fontsize=7, fontweight="bold")
    ax_a.text(0, animal + not_animal / 2, f"{not_animal}", color=COLOR_TARGET, ha="center", va="center", fontsize=7, fontweight="bold")
    ax_a.set_xticks([0])
    ax_a.set_xticklabels(["iWildCam\ncalibration"])
    ax_a.set_ylabel("Audited candidates")
    ax_a.set_ylim(0, 2150)
    ax_a.legend(loc="upper right", fontsize=5.7)
    style_axis(ax_a)
    panel_letter(ax_a, "a")

    # b. SpaceNet audit composition.
    true = int(sn_cal["n_true_same_building"])
    false = int(sn_cal["n_false_link"])
    ax_b.bar([0], [true], color=COLOR_PARC_RELEASE, width=0.6, label="same building", zorder=3)
    ax_b.bar([0], [false], bottom=[true], color=COLOR_GUARDRAIL, width=0.6, label="false link", zorder=4)
    ax_b.text(0, true / 2, f"{true}", color="white", ha="center", va="center", fontsize=7, fontweight="bold")
    ax_b.text(0, true + false + 24, f"{false}", color=COLOR_GUARDRAIL, ha="center", fontsize=6.3)
    ax_b.set_xticks([0])
    ax_b.set_xticklabels(["SpaceNet\ncalibration"])
    ax_b.set_ylabel("Audited links")
    ax_b.set_ylim(0, 860)
    ax_b.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.04),
        fontsize=5.4,
        ncols=1,
        handlelength=1.0,
        borderpad=0.1,
    )
    style_axis(ax_b)
    panel_letter(ax_b, "b")

    # c. release/refuse grid.
    ax_c.set_xlim(-0.5, 1.5)
    ax_c.set_ylim(-0.5, 1.5)
    ax_c.set_xticks([0, 1])
    ax_c.set_xticklabels(["strict / high\nrequest", "operational /\ndiagnostic"])
    ax_c.set_yticks([0, 1])
    ax_c.set_yticklabels(["SpaceNet", "iWildCam"])
    cells = [
        (0, 1, "refuse", r"$\alpha=.10$", "0/20"),
        (1, 1, "release", r"$\alpha=.20,K=50$", "20/20"),
        (0, 0, "refuse", "K=100", "0/20"),
        (1, 0, "release", "K=50", "18/20"),
    ]
    for x0, y0, outcome, line1, line2 in cells:
        ax_c.add_patch(Rectangle((x0 - 0.39, y0 - 0.32), 0.78, 0.64, facecolor=TINT_RELEASE_OK if outcome == "release" else TINT_REFUSE_ZONE, edgecolor="#E1E1E1", linewidth=0.55, zorder=0))
        if outcome == "release":
            ax_c.scatter([x0], [y0 + 0.08], s=58, color=COLOR_PARC_RELEASE, zorder=3)
            txt_color = COLOR_PARC_RELEASE
            decision = "release"
        else:
            ax_c.scatter([x0], [y0 + 0.08], s=58, facecolors="white", edgecolors=COLOR_REFUSAL, linewidths=1.1, zorder=3)
            txt_color = COLOR_REFUSAL
            decision = "refusal"
        ax_c.text(x0, y0 - 0.08, line1, ha="center", va="center", fontsize=6.1, color=COLOR_TARGET)
        ax_c.text(x0, y0 - 0.24, f"{decision}, {line2}", ha="center", va="center", fontsize=5.7, color=txt_color)
    ax_c.grid(False)
    for spine in ax_c.spines.values():
        spine.set_visible(False)
    ax_c.tick_params(length=0)
    panel_letter(ax_c, "c")

    # d. evidence mass ratio.
    pts = [
        ("iWild\nstrict", iw_primary[(iw_primary["alpha"] == 0.10) & (iw_primary["K"] == 50)].iloc[0]["mean_best_mass_ratio"], "refuse"),
        ("iWild\nop.", iw_primary[(iw_primary["alpha"] == 0.20) & (iw_primary["K"] == 50)].iloc[0]["mean_best_mass_ratio"], "release"),
        ("SN\nK100", sn_k100["mean_best_mass_ratio"], "refuse"),
        ("SN\nK50", sn_k50["mean_mass_ratio"], "release"),
    ]
    x = np.arange(len(pts))
    y = np.array([p[1] for p in pts])
    for xi, (label, yi, outcome) in enumerate(pts):
        if outcome == "release":
            ax_d.scatter([xi], [yi], s=54, color=COLOR_PARC_RELEASE, zorder=3)
        else:
            ax_d.scatter([xi], [yi], s=54, facecolors="white", edgecolors=COLOR_REFUSAL, linewidths=1.1, zorder=3)
        value_label(ax_d, xi, yi, f"{yi:.2f}", dy=0.06, color=COLOR_TARGET, size=5.8)
    ax_d.axhline(1, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    ax_d.set_xticks(x)
    ax_d.set_xticklabels([p[0] for p in pts])
    ax_d.set_ylabel("Mass ratio")
    ax_d.set_ylim(0, 1.55)
    style_axis(ax_d)
    panel_letter(ax_d, "d")

    # e. audit reliability.
    scopes = ["all_release_candidates", "all_rows"]
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
    ax_e.bar(np.arange(4), vals, color=cols, width=0.58, zorder=3)
    ax_e.errorbar([3], [kappa], yerr=[[kappa - klo], [khi - kappa]], fmt="none", ecolor=COLOR_TARGET, capsize=2.2, elinewidth=0.75, zorder=4)
    for xi, yi in enumerate(vals):
        lab = "1.000" if yi == 1 else f"{yi:.3f}"
        value_label(ax_e, xi, yi, lab, dy=0.018, color=COLOR_TARGET, size=5.9)
    ax_e.set_xticks(np.arange(4))
    ax_e.set_xticklabels(labels)
    ax_e.set_ylabel("Agreement / reliability")
    ax_e.set_ylim(0, 1.12)
    style_axis(ax_e)
    panel_letter(ax_e, "e")

    # f. strict-alpha refusal boundary.
    strict = iw_primary[(iw_primary["alpha"] == 0.10) & (iw_primary["K"] == 50)].iloc[0]
    vals = [strict["max_observed_e"], strict["required_e"]]
    bars = ax_f.bar([0, 1], vals, color=[COLOR_REFUSAL, COLOR_TARGET], width=0.55, zorder=3)
    bars[0].set_facecolor("white")
    bars[0].set_edgecolor(COLOR_REFUSAL)
    bars[0].set_hatch("//")
    for xi, yi in enumerate(vals):
        value_label(ax_f, xi, yi, f"{yi:.2f}" if xi == 0 else f"{yi:.0f}", dy=0.25, size=6)
    ax_f.set_xticks([0, 1])
    ax_f.set_xticklabels(["max e", "required e"], rotation=15, ha="right")
    ax_f.set_ylabel(r"Strict $\alpha=0.10$")
    ax_f.set_ylim(0, 11.5)
    style_axis(ax_f)
    panel_letter(ax_f, "f")

    # g. second review disagreements.
    all_rows = rows.loc["all_rows"]
    n_rows = int(all_rows["n_rows"])
    n_dis = int(all_rows["n_disagreements"])
    n_agree = n_rows - n_dis
    ax_g.bar([0], [n_agree], color=COLOR_PARC_RELEASE, width=0.55, zorder=3)
    ax_g.bar([0], [n_dis], bottom=[n_agree], color=COLOR_GUARDRAIL, width=0.55, zorder=4)
    ax_g.text(0, n_agree / 2, f"{n_agree}", ha="center", va="center", color="white", fontsize=7, fontweight="bold")
    ax_g.text(0, n_agree + n_dis / 2, f"{n_dis}", ha="center", va="center", color=COLOR_TARGET, fontsize=6)
    ax_g.set_xticks([0])
    ax_g.set_xticklabels(["blind\nsecond review"])
    ax_g.set_ylabel("Rows")
    ax_g.set_ylim(0, n_rows * 1.12)
    ax_g.text(
        0.50,
        1.045,
        "agreement 0.902",
        transform=ax_g.transAxes,
        ha="center",
        va="bottom",
        fontsize=5.8,
        color=COLOR_TARGET,
        clip_on=False,
    )
    style_axis(ax_g)
    panel_letter(ax_g, "g")

    save(fig, "figure_4_human_audit_fullpage")


def main() -> None:
    plot_ctc_flagship()
    plot_materials_flagship()
    plot_human_audit_fullpage()


if __name__ == "__main__":
    main()
