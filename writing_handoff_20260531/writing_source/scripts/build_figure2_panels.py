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
    C,
    COLOR_BASELINE,
    COLOR_GUARDRAIL,
    COLOR_PARC_RELEASE,
    COLOR_REFUSAL,
    COLOR_TARGET,
    TINT_RELEASE_OK,
    TINT_UNSAFE,
    apply_nmi_style,
)

DATA = ROOT / "data"
OUT = ROOT / "figures" / "figure2_assets" / "rebuild"


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
            fontsize=6.5,
            color=COLOR_TARGET,
            ha="right",
            va="bottom",
        )


def value_label(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    dy: float = 0.015,
    color: str = COLOR_TARGET,
    ha: str = "center",
    va: str = "bottom",
    size: float = 6.2,
) -> None:
    ax.text(x, y + dy, text, color=color, fontsize=size, ha=ha, va=va)


def save_panel(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / f"{stem}.pdf"
    png = OUT / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.01)
    fig.savefig(png, bbox_inches="tight", pad_inches=0.01, dpi=600)
    plt.close(fig)
    print(f"wrote {pdf.relative_to(ROOT)} and {png.relative_to(ROOT)}")


def load_ctc() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    main = df("table_ctc_learned_strict_alpha010_smallK.csv")
    rev = df("table_ctc_learned_reverse_split.csv")
    neg = df("table_ctc_learned_negative_control.csv")
    leak = df("table_ctc_learned_leakage_audit.csv")
    unsafe = df("table_prevented_false_releases.csv")
    main = main[(main["alpha"] == 0.10) & (main["rho"] == 0.10)].sort_values("M")
    rev = rev[(rev["alpha"] == 0.10) & (rev["rho"] == 0.10)].sort_values("M")
    neg = neg[(neg["alpha"] == 0.10) & (neg["rho"] == 0.10)].sort_values("M")
    ctc_unsafe = unsafe[unsafe["domain"].str.contains("CTC", na=False)].iloc[0]
    return main, rev, neg, leak, ctc_unsafe


def panel_a_release_volume(main: pd.DataFrame, rev: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.2, 1.85))
    ax.plot(main["M"], main["released_mean"], "-o", color=COLOR_PARC_RELEASE, ms=4.2, label="train 01 -> certify 02")
    ax.plot(rev["M"], rev["released_mean"], "--o", color=COLOR_PARC_RELEASE, ms=3.7, alpha=0.70, label="train 02 -> certify 01")
    ax.plot(main["M"], main["M"], ":", color=COLOR_BASELINE, linewidth=1.1, label="requested K")
    for _, row in main.iterrows():
        if row["M"] in [10, 100, 300]:
            value_label(ax, row["M"], row["released_mean"], f"{int(row['released_mean'])}", dy=7, color=COLOR_PARC_RELEASE, size=6)
    ax.set_xscale("log")
    ax.set_xticks([10, 25, 50, 100, 300])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("Requested links K")
    ax.set_ylabel("Mean released links")
    ax.set_ylim(-10, 325)
    ax.set_yticks([0, 100, 200, 300])
    ax.legend(loc="upper left", fontsize=5.8, handlelength=1.4)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_2a_release_volume")


def panel_b_heldout_ftr(main: pd.DataFrame, rev: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.95, 1.85))
    endpoints = [(f"{int(r['M'])}", r, "main") for _, r in main.iterrows()]
    endpoints += [(f"r{int(r['M'])}", r, "reverse") for _, r in rev.iterrows()]
    x = np.arange(len(endpoints))
    vals = np.array([r["actual_FTR_mean"] for _, r, _ in endpoints])
    lo = np.array([r["actual_FTR_bootstrap95_low"] for _, r, _ in endpoints])
    hi = np.array([r["actual_FTR_bootstrap95_high"] for _, r, _ in endpoints])
    is_rev = np.array([kind == "reverse" for _, _, kind in endpoints])
    ax.errorbar(
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
    ax.errorbar(
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
    for xi in x:
        ax.text(xi, 0.006, "0", ha="center", va="bottom", fontsize=4.8, color=COLOR_PARC_RELEASE)
    add_alpha(ax)
    ax.set_xticks(x)
    ax.set_xticklabels([k for k, _, _ in endpoints], rotation=45, ha="right", fontsize=4.9)
    ax.set_ylabel("Held-out FTR")
    ax.set_ylim(0, 0.12)
    ax.legend(loc="upper left", fontsize=5.0, handlelength=1.0, borderpad=0.1)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_2b_heldout_ftr")


def panel_c_evidence_mass(main: pd.DataFrame, neg: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.95, 1.85))
    ax.plot(main["M"], main["best_mass_ratio_mean"], "-o", color=COLOR_PARC_RELEASE, ms=4)
    ax.plot(neg["M"], neg["best_mass_ratio_mean"], "^", color=COLOR_GUARDRAIL, ms=4.2, alpha=0.85)
    ax.axhline(1.0, color=COLOR_TARGET, linestyle=(0, (3, 2)), linewidth=0.75)
    ax.text(0.98, 1.03, "boundary", transform=ax.get_yaxis_transform(), fontsize=6.1, ha="right", va="bottom", color=COLOR_TARGET)
    ax.set_xscale("log")
    ax.set_xticks([10, 50, 100, 300])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("K")
    ax.set_ylabel("Evidence mass ratio")
    ax.set_ylim(0, 1.55)
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_2c_evidence_mass")


def panel_d_reverse_split() -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.58))
    ks = np.array([10, 25, 50, 75, 100, 300])
    y = np.ones(len(ks))
    ax.scatter(ks, y, s=38, color=COLOR_PARC_RELEASE, zorder=3)
    ax.plot(ks, y, color=COLOR_PARC_RELEASE, linewidth=0.9, alpha=0.7)
    for k in ks:
        ax.text(k, 1.055, "20/20", fontsize=4.6, ha="center", color=COLOR_PARC_RELEASE)
    ax.text(0.04, 0.12, "reverse split\nFTR=0.000", transform=ax.transAxes, fontsize=5.8, color=COLOR_TARGET, ha="left", va="bottom")
    ax.set_xscale("log")
    ax.set_xticks([10, 50, 100, 300])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_ylim(-0.08, 1.20)
    ax.set_xlabel("Reverse-split K")
    ax.set_ylabel("Non-empty seed rate")
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_2d_reverse_split")


def panel_e_leakage(leak: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.58))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    sequence_rows = leak["check_name"].str.contains("sequence_disjoint", na=False)
    checks = [
        ("sequence split", leak.loc[sequence_rows, "train_eval_overlap"].eq("none").all()),
        ("no GT features", leak["forbidden_GT_or_match_columns_used"].eq("no").all()),
        ("frozen scorer", leak["scorer_frozen_before_PARC"].eq("yes").all()),
        ("held-out eval", leak["held_out_GT_use"].str.contains("after_release").all()),
    ]
    for i, (label, ok) in enumerate(checks):
        y0 = 0.84 - i * 0.21
        ax.add_patch(Rectangle((0.03, y0 - 0.07), 0.94, 0.14, facecolor=TINT_RELEASE_OK if ok else TINT_UNSAFE, edgecolor="#E2E2E2", linewidth=0.45))
        ax.scatter([0.10], [y0], s=30, color=COLOR_PARC_RELEASE if ok else COLOR_GUARDRAIL, zorder=3)
        ax.text(0.18, y0, label, fontsize=6.0, va="center", color=COLOR_TARGET)
        ax.text(0.90, y0, "pass" if ok else "check", fontsize=5.8, va="center", ha="right", color=COLOR_PARC_RELEASE if ok else COLOR_GUARDRAIL)
    fig.tight_layout(pad=0.10)
    save_panel(fig, "figure_2e_leakage_strip")


def panel_f_random_score(neg: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(1.75, 1.58))
    rand = neg[neg["M"].isin([10, 50, 100, 300])].copy()
    x = np.arange(len(rand))
    w = 0.34
    ax.bar(x - w / 2, rand["raw_topM_actual_FTR_mean"], width=w, color=COLOR_BASELINE, label="raw top-K FTR", zorder=2)
    ax.bar(x + w / 2, rand["released_mean"] / rand["M"], width=w, color=COLOR_REFUSAL, alpha=0.35, edgecolor=COLOR_REFUSAL, label="PARC release fraction", zorder=3)
    for xi, raw in zip(x, rand["raw_topM_actual_FTR_mean"]):
        value_label(ax, xi - w / 2, raw, f"{raw:.2f}", dy=0.025, color=COLOR_TARGET, size=5.5)
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(k)) for k in rand["M"]])
    ax.set_xlabel("Random-score K")
    ax.set_ylabel("Fraction")
    ax.set_ylim(0, 0.95)
    ax.legend(loc="upper center", bbox_to_anchor=(0.50, 1.22), fontsize=4.9, handlelength=0.9, ncols=1, borderpad=0.1)
    style_axis(ax)
    fig.tight_layout(pad=0.18)
    save_panel(fig, "figure_2f_random_score")


def panel_g_high_volume(ctc_unsafe: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(1.55, 1.58))
    vals = [float(ctc_unsafe["raw_topK_FTR"]), float(ctc_unsafe["PARC_release"])]
    bars = ax.bar(np.arange(2), vals, color=[COLOR_BASELINE, COLOR_REFUSAL], width=0.58, edgecolor=[COLOR_BASELINE, COLOR_REFUSAL], zorder=3)
    bars[1].set_facecolor("white")
    bars[1].set_hatch("//")
    for xi, yi in enumerate(vals):
        value_label(ax, xi, yi, f"{yi:.3f}" if yi else "0/20", dy=0.02, color=COLOR_TARGET, size=5.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["raw FTR", "PARC\nrelease"], rotation=20, ha="right")
    ax.set_ylabel("K=5000 fraction")
    ax.set_ylim(0, 0.43)
    ax.text(0.48, 0.36, "~1,803 false links\nprevented per seed", fontsize=5.6, color=COLOR_TARGET, ha="center", va="top")
    style_axis(ax)
    fig.tight_layout(pad=0.25)
    save_panel(fig, "figure_2g_high_volume")


def main() -> None:
    apply_nmi_style(plt)
    main_df, rev, neg, leak, ctc_unsafe = load_ctc()
    panel_a_release_volume(main_df, rev)
    panel_b_heldout_ftr(main_df, rev)
    panel_c_evidence_mass(main_df, neg)
    panel_d_reverse_split()
    panel_e_leakage(leak)
    panel_f_random_score(neg)
    panel_g_high_volume(ctc_unsafe)


if __name__ == "__main__":
    main()
