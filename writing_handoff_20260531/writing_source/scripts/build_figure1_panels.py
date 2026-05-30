from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from matplotlib.patches import Circle, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
sys.path.insert(0, str(ROOT))

from figures.style import COLOR_PARC_RELEASE, apply_nmi_style


FIG = ROOT / "figures"
ASSETS = FIG / "figure5_assets"
OUT = FIG / "figure1_assets" / "rebuild"


def _prep_axis(ax: plt.Axes) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def _draw_ctc(ax: plt.Axes) -> None:
    t = mpimg.imread(ASSETS / "ctc_release_frame_t.png")
    tp1 = mpimg.imread(ASSETS / "ctc_release_frame_tp1.png")
    meta = json.loads((ASSETS / "ctc_release_link.json").read_text())
    ax.imshow(t, cmap="gray", extent=(0.00, 0.485, 0.05, 0.97), origin="upper")
    ax.imshow(tp1, cmap="gray", extent=(0.515, 1.00, 0.05, 0.97), origin="upper")
    h, w = t.shape[:2]
    p0 = (0.485 * meta["cell_t"][0] / w, 0.97 - 0.92 * meta["cell_t"][1] / h)
    p1 = (0.515 + 0.485 * meta["cell_tp1"][0] / w, 0.97 - 0.92 * meta["cell_tp1"][1] / h)
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=COLOR_PARC_RELEASE, lw=1.3)
    for p in (p0, p1):
        ax.add_patch(Circle(p, 0.043, facecolor="none", edgecolor=COLOR_PARC_RELEASE, lw=1.3))


def _draw_wbm(ax: plt.Axes) -> None:
    img = mpimg.imread(FIG / "figure1_assets" / "materials_cloud_wbm" / "wbm_crystal_thumbnail.png")
    rgb = img[..., :3]
    alpha = img[..., 3] if img.shape[-1] == 4 else np.ones(img.shape[:2])
    non_white = (alpha > 0.05) & (np.max(np.abs(rgb - 1.0), axis=2) > 0.04)
    ys, xs = np.where(non_white)
    if len(xs):
        pad = 42
        y0, y1 = max(0, ys.min() - pad), min(img.shape[0], ys.max() + pad)
        x0, x1 = max(0, xs.min() - pad), min(img.shape[1], xs.max() + pad)
        img = img[y0:y1, x0:x1, ...]
    ax.imshow(img, extent=(0.03, 0.97, 0.05, 0.97), origin="upper")


def _draw_spacenet(ax: plt.Axes) -> None:
    t1 = mpimg.imread(ASSETS / "spacenet_release_t1.png")
    t2 = mpimg.imread(ASSETS / "spacenet_release_t2.png")
    meta = json.loads((ASSETS / "spacenet_release_polygons.json").read_text())
    ax.imshow(t1, extent=(0.00, 0.485, 0.05, 0.97), origin="upper")
    ax.imshow(t2, extent=(0.515, 1.00, 0.05, 0.97), origin="upper")
    h, w = t1.shape[:2]

    def transform(poly: list[list[float]], x0: float) -> np.ndarray:
        arr = np.array(poly, dtype=float)
        xs = x0 + 0.485 * arr[:, 0] / w
        ys = 0.97 - 0.92 * arr[:, 1] / h
        return np.c_[xs, ys]

    poly0 = transform(meta["released"]["t1"], 0.0)
    poly1 = transform(meta["released"]["t2"], 0.515)
    for poly in (poly0, poly1):
        ax.add_patch(Polygon(poly, closed=True, fill=False, edgecolor=COLOR_PARC_RELEASE, lw=1.3))
    c0, c1 = poly0.mean(axis=0), poly1.mean(axis=0)
    ax.plot([c0[0], c1[0]], [c0[1], c1[1]], color=COLOR_PARC_RELEASE, lw=1.2)


def _draw_iwild(ax: plt.Axes) -> None:
    img = mpimg.imread(ASSETS / "camera_trap_animal_present.png")
    img = img[:-22, ...]
    box = json.loads((ASSETS / "camera_trap_boxes.json").read_text())["animal_present"]["box"]
    ax.imshow(img, extent=(0.02, 0.98, 0.05, 0.97), origin="upper")
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    rect_xy = (0.02 + 0.96 * x0 / w, 0.97 - 0.92 * y1 / h)
    rect_w = 0.96 * (x1 - x0) / w
    rect_h = 0.92 * (y1 - y0) / h
    ax.add_patch(Rectangle(rect_xy, rect_w, rect_h, facecolor="none", edgecolor=COLOR_PARC_RELEASE, lw=1.3))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    apply_nmi_style(plt)
    fig, axes = plt.subplots(2, 2, figsize=(3.1, 2.65))
    for ax in axes.flat:
        _prep_axis(ax)
    _draw_ctc(axes[0, 0])
    _draw_wbm(axes[0, 1])
    _draw_spacenet(axes[1, 0])
    _draw_iwild(axes[1, 1])
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99, wspace=0.06, hspace=0.08)
    fig.savefig(OUT / "figure_1a_units_plate.pdf", bbox_inches="tight", pad_inches=0.0)
    fig.savefig(OUT / "figure_1a_units_plate.png", bbox_inches="tight", pad_inches=0.0, dpi=600)
    plt.close(fig)


if __name__ == "__main__":
    main()
