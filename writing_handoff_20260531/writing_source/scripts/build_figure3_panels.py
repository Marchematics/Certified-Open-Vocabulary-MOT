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
    COLOR_REFUSAL,
    COLOR_TARGET,
    apply_nmi_style,
)

DATA = ROOT / "data"
OUT = ROOT / "figures" / "figure3_assets" / "rebuild"


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


def add_alpha(ax: plt.Axes, alpha: float = 0.10, label: str | None = r"$\alpha=0.10$") -> None:
    ax.axhline(alpha, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75, zorder=1)
    if label:
        ax.text(
            0.98,
            alpha + 0.004,
            label,
            transform=ax.get_yaxis_transform(),
            fontsize=6.4,
            color=COLOR_TARGET,
            ha="right",
            va="bottom",
        )


def value_label(ax: plt.Axes, x, y, text, dy=0.015, color=COLOR_TARGET, size=6.0) -> None:
    ax.text(x, y + dy, text, color=color, fontsize=size, ha="center", va="bottom")


def short_block_name(s: str) -> str:
    return {
        "chemical_system": "chemical\nsystem",
        "composition_family_pair": "composition\nfamily",
        "wyckoff_family": "Wyckoff\nfamily",
    }.get(s, s)


def save_panel(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / f"{stem}.pdf"
    png = OUT / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.01)
    fig.savefig(png, bbox_inches="tight", pad_inches=0.01, dpi=600)
    plt.close(fig)
    print(f"wrote {pdf.relative_to(ROOT)} and {png.relative_to(ROOT)}")


def load_materials() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primary = df("table_materials_primary_results.csv")
    alignn = df("table_materials_modern_model_sensitivity.csv")
    blocks = df("table_materials_block_sensitivity.csv")
    random = df("table_materials_random_score_control.csv")
    high = df("table_materials_high_volume_refusal.csv")
    cg = primary[(primary["proposal_source"].str.contains("cgcnn")) & (primary["rho"] == 0.10) & (primary["alpha"] == 0.10)].sort_values("K")
    al = alignn[(alignn["rho"] == 0.10) & (alignn["alpha"] == 0.10)].sort_values("K")
    return primary, alignn, blocks, random, high, cg, al


def panel_a_alignn(hero: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.0, 2.45))
    hero = hero[hero["K"].isin([300, 500])].sort_values("K")
    x = np.arange(len(hero))
    w = 0.34
    ax.bar(x - w / 2, hero["raw_topK_actual_FTR_mean"], width=w, color=COLOR_BASELINE, label="raw requested K", zorder=2)
    ax.bar(x + w / 2, hero["actual_FTR_mean"], width=w, color=COLOR_PARC_RELEASE, label="PARC certified stop", zorder=3)
    yerr = np.vstack([
        hero["actual_FTR_mean"].to_numpy() - hero["actual_FTR_bootstrap95_low"].to_numpy(),
        hero["actual_FTR_bootstrap95_high"].to_numpy() - hero["actual_FTR_mean"].to_numpy(),
    ])
    ax.errorbar(x + w / 2, hero["actual_FTR_mean"], yerr=yerr, fmt="none", ecolor=COLOR_TARGET, elinewidth=0.8, capsize=2.2, zorder=4)
    for xi, raw, parc in zip(x, hero["raw_topK_actual_FTR_mean"], hero["actual_FTR_mean"]):
        value_label(ax, xi - w / 2, raw, f"{raw:.3f}", dy=0.015, color=COLOR_TARGET)
        value_label(ax, xi + w / 2, parc, f"{parc:.3f}", dy=0.015, color=COLOR_PARC_RELEASE)
    add_alpha(ax)
    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}\nR≈{r:.0f}" for k, r in zip(hero["K"], hero["mean_release"])])
    ax.set_ylabel("False-release fraction")
    ax.set_ylim(0, 0.36)
    ax.legend(loc="upper left", fontsize=5.9)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3a_alignn_raw_vs_parc")


def panel_b_cgcnn_primary(cg: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.55))
    row100 = cg[cg["K"] == 100].iloc[0]
    ax.bar([0], [row100["mean_release"] / row100["K"]], color=COLOR_PARC_RELEASE, width=0.5, zorder=3)
    ax.bar([1], [row100["actual_FTR_mean"]], color=COLOR_PARC_RELEASE, width=0.5, zorder=3)
    ax.errorbar(
        [1],
        [row100["actual_FTR_mean"]],
        yerr=[[row100["actual_FTR_mean"] - row100["actual_FTR_bootstrap95_low"]], [row100["actual_FTR_bootstrap95_high"] - row100["actual_FTR_mean"]]],
        fmt="none",
        ecolor=COLOR_TARGET,
        elinewidth=0.7,
        capsize=2,
        zorder=4,
    )
    ax.text(0, 1.04, "20/20", ha="center", fontsize=5.9, color=COLOR_PARC_RELEASE)
    ax.text(1, row100["actual_FTR_mean"] + 0.020, "0.030", ha="center", fontsize=5.9, color=COLOR_PARC_RELEASE)
    add_alpha(ax, label=None)
    ax.text(0.98, 0.104, r"$\alpha=0.10$", transform=ax.get_yaxis_transform(), fontsize=5.4, color=COLOR_TARGET, ha="right", va="bottom")
    ax.set_ylim(0, 1.10)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["release/K", "FTR"], rotation=25, ha="right")
    ax.set_ylabel("CGCNN K=100")
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3b_cgcnn_primary")


def panel_c_ftr_ci(cg: pd.DataFrame, al: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.85, 1.55))
    hero = al[al["K"].isin([300, 500])].sort_values("K")
    endpoints = [
        ("CGCNN\n100", cg[cg["K"] == 100].iloc[0]),
        ("CGCNN\n300", cg[cg["K"] == 300].iloc[0]),
        ("ALIGNN\n300", hero[hero["K"] == 300].iloc[0]),
        ("ALIGNN\n500", hero[hero["K"] == 500].iloc[0]),
    ]
    x = np.arange(len(endpoints))
    vals = np.array([r["actual_FTR_mean"] for _, r in endpoints])
    lo = np.array([r["actual_FTR_bootstrap95_low"] for _, r in endpoints])
    hi = np.array([r["actual_FTR_bootstrap95_high"] for _, r in endpoints])
    ax.errorbar(x, vals, yerr=[vals - lo, hi - vals], fmt="o", color=COLOR_PARC_RELEASE, ecolor=COLOR_TARGET, elinewidth=0.75, capsize=2, ms=4.2, zorder=3)
    for n, (xi, yi) in enumerate(zip(x, vals)):
        dy = 0.008 if n % 2 == 0 else 0.021
        xoff = -0.05 if n % 2 == 0 else 0.05
        ax.text(xi + xoff, yi + dy, f"{yi:.3f}", color=COLOR_TARGET, fontsize=5.0, ha="center", va="bottom")
    add_alpha(ax, label=None)
    ax.text(0.98, 0.145, r"$\alpha=0.10$", transform=ax.get_yaxis_transform(), fontsize=5.2, color=COLOR_TARGET, ha="right", va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels([k for k, _ in endpoints], rotation=0, fontsize=4.9)
    ax.set_ylabel("FTR (95% CI)")
    ax.set_ylim(0, 0.17)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3c_ftr_ci")


def panel_d_mass(cg: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.85, 1.55))
    ax.plot(cg["K"], cg["best_mass_ratio_mean"], "-o", color=COLOR_PARC_RELEASE, ms=4)
    ax.axhline(1, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    ax.set_xscale("log")
    ax.set_xticks([50, 100, 300, 1000, 5000])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("K")
    ax.set_ylabel("Mass ratio")
    ax.set_ylim(0, max(cg["best_mass_ratio_mean"].max() * 1.08, 1.2))
    ax.text(5000, 1.06, "boundary", fontsize=5.7, ha="right", color=COLOR_TARGET)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3d_mass_ratio")


def block_tables(blocks: pd.DataFrame) -> tuple[list[str], pd.DataFrame, pd.DataFrame, np.ndarray]:
    order = ["chemical_system", "composition_family_pair", "wyckoff_family"]
    block100 = blocks[(blocks["K"] == 100) & (blocks["rho"] == 0.10) & (blocks["alpha"] == 0.10)].copy()
    block300 = blocks[(blocks["K"] == 300) & (blocks["rho"] == 0.10) & (blocks["alpha"] == 0.10)].copy()
    b100 = block100.set_index("block_definition").loc[order]
    b300 = block300.set_index("block_definition").loc[order]
    return order, b100, b300, np.arange(len(order))


def panel_e_block_ftr(blocks: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.85, 1.55))
    order, b100, b300, x = block_tables(blocks)
    ax.bar(x - 0.18, b100["actual_FTR_mean"], width=0.34, color=COLOR_PARC_RELEASE, label="K=100", zorder=3)
    ax.bar(x + 0.18, b300["actual_FTR_mean"], width=0.34, color=COLOR_BASELINE, label="K=300", zorder=2)
    add_alpha(ax)
    ax.set_xticks(x)
    ax.set_xticklabels([short_block_name(k) for k in order], rotation=0, fontsize=5.0)
    ax.set_ylabel("Block-sensitivity FTR")
    ax.set_ylim(0, 0.31)
    ax.legend(loc="upper left", fontsize=5.5, ncols=1)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3e_block_ftr")


def panel_f_block_mass(blocks: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.65, 1.55))
    order, _, b300, x = block_tables(blocks)
    ax.bar(x, b300["best_mass_ratio_mean"], color=[COLOR_BASELINE, COLOR_PARC_RELEASE, COLOR_BASELINE], width=0.6, zorder=3)
    ax.axhline(1, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    for xi, yi in zip(x, b300["best_mass_ratio_mean"]):
        value_label(ax, xi, yi, f"{yi:.1f}", dy=0.18, size=5.5)
    ax.set_xticks(x)
    ax.set_xticklabels([short_block_name(k) for k in order], fontsize=5.0)
    ax.set_ylabel("Mass ratio, K=300")
    ax.set_ylim(0, max(32, b300["best_mass_ratio_mean"].max() * 1.15))
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3f_block_mass")


def panel_g_random(random: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(2.25, 1.55))
    rnd = random[(random["alpha"] == 0.10) & (random["K"].isin([300, 1000]))].copy().sort_values("K")
    x = np.arange(len(rnd))
    ax.bar(x - 0.18, rnd["raw_topK_actual_FTR_mean"], width=0.34, color=COLOR_BASELINE, label="raw FTR", zorder=2)
    ax.bar(x + 0.18, rnd["mean_release"] / rnd["K"], width=0.34, color="white", edgecolor=COLOR_REFUSAL, hatch="//", label="PARC release/K", zorder=3)
    for xi, yi in zip(x, rnd["raw_topK_actual_FTR_mean"]):
        value_label(ax, xi - 0.18, yi, f"{yi:.2f}", dy=0.03, size=5.7)
    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}" for k in rnd["K"]])
    ax.set_ylabel("Random-score fraction")
    ax.set_ylim(0, 1.0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.22), fontsize=5.1, ncols=2, handlelength=1.0, borderpad=0.1, columnspacing=0.6)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3g_random_score")


def panel_h_high_volume(high: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.55))
    hv = high[(high["alpha"] == 0.10) & (high["K"] == 5000)].iloc[0]
    vals = [hv["raw_topK_actual_FTR_mean"], hv["mean_release"] / hv["K"]]
    bars = ax.bar([0, 1], vals, width=0.58, color=[COLOR_BASELINE, "white"], edgecolor=[COLOR_BASELINE, COLOR_REFUSAL], zorder=3)
    bars[1].set_hatch("//")
    for xi, yi, lab in zip([0, 1], vals, [f"{vals[0]:.3f}", "0/20"]):
        value_label(ax, xi, yi, lab, dy=0.025, size=5.7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["raw FTR", "PARC\nrelease/K"], rotation=20, ha="right")
    ax.set_ylabel("K=5000")
    ax.set_ylim(0, 0.48)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_3h_high_volume")


def main() -> None:
    apply_nmi_style(plt)
    _, _, blocks, random, high, cg, al = load_materials()
    panel_a_alignn(al)
    panel_b_cgcnn_primary(cg)
    panel_c_ftr_ci(cg, al)
    panel_d_mass(cg)
    panel_e_block_ftr(blocks)
    panel_f_block_mass(blocks)
    panel_g_random(random)
    panel_h_high_volume(high)


if __name__ == "__main__":
    main()
