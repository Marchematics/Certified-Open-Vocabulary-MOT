"""Render a small WBM crystal-candidate thumbnail for the Fig. 1 teaser.

The input is the public Materials Cloud WBM step_1.json.bz2 archive.  We keep
this script intentionally lightweight: it parses one selected
ComputedStructureEntry JSON record and renders the unit-cell atoms directly
with matplotlib, avoiding heavyweight materials-visualization dependencies.
"""

from __future__ import annotations

import bz2
import json
import sys
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from figures.style import C, apply_nmi_style


ASSET_DIR = ROOT / "figures" / "figure1_assets" / "materials_cloud_wbm"
SOURCE = ASSET_DIR / "step_1.json.bz2"
OUT_PNG = ASSET_DIR / "wbm_crystal_thumbnail.png"
OUT_JSON = ASSET_DIR / "wbm_crystal_thumbnail_source.json"
PROVENANCE = ASSET_DIR / "wbm_crystal_thumbnail_provenance.json"

# Chosen for a compact, ordinary-element unit cell in the public WBM step-1
# archive: FeBO4-like composition, 6 sites.  This is an illustrative crystal
# candidate thumbnail, not an additional statistical result.
SELECTED_ENTRY_INDEX = 5293

ATOM_COLORS = {
    "Fe": "#B36B2C",
    "B": "#4C78A8",
    "O": "#E5E5E5",
}
ATOM_SIZES = {
    "Fe": 150,
    "B": 85,
    "O": 70,
}


def load_entry() -> dict:
    with bz2.open(SOURCE, "rt") as handle:
        data = json.load(handle)
    entry = data["entries"][SELECTED_ENTRY_INDEX]
    OUT_JSON.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return entry


def unit_cell_edges(lattice: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    corners = []
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                corners.append(i * lattice[0] + j * lattice[1] + k * lattice[2])
    corners = np.array(corners)
    edges = []
    for a, b in combinations(range(8), 2):
        diff = np.abs((corners[a] - corners[b]) @ np.linalg.pinv(lattice))
        if np.isclose(diff.sum(), 1.0) and np.count_nonzero(np.round(diff, 6)) == 1:
            edges.append((corners[a], corners[b]))
    return edges


def plausible_bonds(labels: list[str], coords: np.ndarray) -> list[tuple[int, int]]:
    bonds = []
    for i, j in combinations(range(len(coords)), 2):
        pair = {labels[i], labels[j]}
        dist = np.linalg.norm(coords[i] - coords[j])
        if pair == {"B", "O"} and dist <= 1.85:
            bonds.append((i, j))
        elif pair == {"Fe", "O"} and dist <= 2.45:
            bonds.append((i, j))
    return bonds


def equal_3d_bounds(ax, coords: np.ndarray, lattice: np.ndarray) -> None:
    all_pts = np.vstack([coords, np.zeros((1, 3)), lattice])
    mins = all_pts.min(axis=0)
    maxs = all_pts.max(axis=0)
    center = (mins + maxs) / 2
    radius = (maxs - mins).max() / 2 * 1.12
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)


def render() -> None:
    apply_nmi_style(plt)
    entry = load_entry()
    structure = entry["structure"]
    lattice = np.array(structure["lattice"]["matrix"], dtype=float)
    labels = [site["label"] for site in structure["sites"]]
    coords = np.array([site["xyz"] for site in structure["sites"]], dtype=float)
    formula_order = ["Fe", "B", "O"]
    formula = "".join(
        f"{el}{int(entry['composition'][el]) if int(entry['composition'][el]) > 1 else ''}"
        for el in formula_order
        if el in entry["composition"]
    )

    fig = plt.figure(figsize=(1.85, 1.85), dpi=600)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    for start, end in unit_cell_edges(lattice):
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            [start[2], end[2]],
            color=C["ref"],
            linewidth=0.45,
            alpha=0.55,
            zorder=1,
        )

    for i, j in plausible_bonds(labels, coords):
        p, q = coords[i], coords[j]
        ax.plot(
            [p[0], q[0]],
            [p[1], q[1]],
            [p[2], q[2]],
            color=C["base"],
            linewidth=0.9,
            alpha=0.85,
            zorder=2,
        )

    for label in sorted(set(labels)):
        mask = np.array([x == label for x in labels])
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            coords[mask, 2],
            s=ATOM_SIZES.get(label, 80),
            c=ATOM_COLORS.get(label, C["parc"]),
            edgecolors=C["ref"],
            linewidths=0.35,
            depthshade=True,
            label=label,
            zorder=3,
        )

    ax.view_init(elev=18, azim=38)
    equal_3d_bounds(ax, coords, lattice)
    ax.set_axis_off()
    fig.savefig(OUT_PNG, dpi=600, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)

    PROVENANCE.write_text(
        json.dumps(
            {
                "source": "Materials Cloud materialscloud:2021.68",
                "source_url": "https://archive.materialscloud.org/record/2021.68",
                "license": "Creative Commons Attribution 4.0 International",
                "downloaded_file": str(SOURCE.relative_to(ROOT)),
                "selected_entry_index": SELECTED_ENTRY_INDEX,
                "composition": entry["composition"],
                "display_formula": formula,
                "thumbnail": str(OUT_PNG.relative_to(ROOT)),
                "note": "Illustrative WBM crystal-candidate thumbnail for Figure 1; not a new PARC result.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    render()
