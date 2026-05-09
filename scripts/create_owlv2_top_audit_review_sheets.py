#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/home/waas/paper_experiments")
AUDIT_DIR = ROOT / "outputs/phase4_owlv2_top_audit"
CANDIDATES_CSV = AUDIT_DIR / "owlv2_top150_mini_audit_candidates.csv"
LABELS_CSV = AUDIT_DIR / "owlv2_top150_mini_audit_labels.csv"
OUT_DIR = AUDIT_DIR / "review_sheets"
MONTAGE_DIR = AUDIT_DIR / "montages"

NODE_FILES = {
    "OVT-B": ROOT / "outputs/phase3_ovtb_owlv2/candidate_nodes.csv",
    "TAO": ROOT / "outputs/phase3_tao_owlv2/candidate_nodes.csv",
}


def font(size: int = 16) -> ImageFont.ImageFont:
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]:
        p = Path(name)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


FONT = font(16)
SMALL = font(13)


def clamp_box(x: float, y: float, w: float, h: float, im_w: int, im_h: int) -> tuple[int, int, int, int]:
    x1 = max(0, min(im_w - 1, int(round(x))))
    y1 = max(0, min(im_h - 1, int(round(y))))
    x2 = max(0, min(im_w - 1, int(round(x + w))))
    y2 = max(0, min(im_h - 1, int(round(y + h))))
    if x2 <= x1:
        x2 = min(im_w - 1, x1 + 1)
    if y2 <= y1:
        y2 = min(im_h - 1, y1 + 1)
    return x1, y1, x2, y2


def load_nodes() -> pd.DataFrame:
    parts = []
    for dataset, path in NODE_FILES.items():
        df = pd.read_csv(path)
        df["dataset"] = dataset
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def make_tile(node: pd.Series, query: str, tile_w: int = 210, tile_h: int = 160) -> Image.Image:
    p = Path(str(node["image_path"]))
    try:
        im = Image.open(p).convert("RGB")
    except Exception:
        im = Image.new("RGB", (tile_w, tile_h), "white")
        d = ImageDraw.Draw(im)
        d.text((8, 8), f"missing image\n{p.name}", fill=(180, 0, 0), font=SMALL)
        return im
    d = ImageDraw.Draw(im)
    x1, y1, x2, y2 = clamp_box(
        float(node["bbox_x"]),
        float(node["bbox_y"]),
        float(node["bbox_w"]),
        float(node["bbox_h"]),
        im.width,
        im.height,
    )
    for off in range(3):
        d.rectangle((x1 - off, y1 - off, x2 + off, y2 + off), outline=(255, 20, 20))
    d.rectangle((0, 0, min(im.width, 380), 24), fill=(255, 255, 255))
    d.text((4, 3), f"f={int(node['frame_index'])} s={float(node['score']):.2f}", fill=(0, 0, 0), font=SMALL)
    im.thumbnail((tile_w, tile_h - 22))
    canvas = Image.new("RGB", (tile_w, tile_h), (250, 250, 250))
    canvas.paste(im, ((tile_w - im.width) // 2, 0))
    dc = ImageDraw.Draw(canvas)
    dc.text((4, tile_h - 19), query[:28], fill=(0, 0, 0), font=SMALL)
    return canvas


def make_montage(row: pd.Series, nodes: pd.DataFrame) -> Path:
    ds = str(row["dataset"])
    pid = str(row["path_id"])
    sub = nodes[(nodes["dataset"] == ds) & (nodes["path_id"] == pid)].sort_values(["frame_index", "node_index"])
    if len(sub) == 0:
        tiles = [Image.new("RGB", (210, 160), (255, 255, 255))]
        d = ImageDraw.Draw(tiles[0])
        d.text((8, 8), "no nodes", fill=(180, 0, 0), font=FONT)
    else:
        take = min(6, len(sub))
        idx = sorted(set(int(round(i)) for i in pd.Series(range(take)).map(lambda z: z * (len(sub) - 1) / max(1, take - 1))))
        picked = sub.iloc[idx]
        tiles = [make_tile(n, str(row["query"])) for _, n in picked.iterrows()]
    header_h = 44
    tile_w, tile_h = 210, 160
    cols = 3
    rows = math.ceil(len(tiles) / cols)
    canvas = Image.new("RGB", (cols * tile_w, header_h + rows * tile_h), "white")
    d = ImageDraw.Draw(canvas)
    title = (
        f"{ds} {pid} | query={row['query']} | rank={int(row['candidate_rank'])} "
        f"| score={float(row['score']):.3f} | IoU={float(row['matched_iou']):.2f}"
    )
    d.text((6, 6), title[:110], fill=(0, 0, 0), font=FONT)
    d.text((6, 25), f"matched_gt={bool(row['is_matched_to_gt'])} path_len={int(row['path_length'])}", fill=(50, 50, 50), font=SMALL)
    for i, tile in enumerate(tiles):
        x = (i % cols) * tile_w
        y = header_h + (i // cols) * tile_h
        canvas.paste(tile, (x, y))
    out = MONTAGE_DIR / f"{ds.replace('-', '')}_{pid}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=92)
    return out


def make_sheets(review: pd.DataFrame, rows_per_sheet: int = 10) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    montage_paths = [Path(p) for p in review["montage_path"]]
    sheet_w = 1260
    row_h = 368
    label_w = 260
    for s in range(math.ceil(len(review) / rows_per_sheet)):
        chunk = review.iloc[s * rows_per_sheet : (s + 1) * rows_per_sheet]
        canvas = Image.new("RGB", (sheet_w, row_h * len(chunk)), (240, 240, 240))
        d = ImageDraw.Draw(canvas)
        for j, (_, r) in enumerate(chunk.iterrows()):
            y = j * row_h
            d.rectangle((0, y, sheet_w - 1, y + row_h - 1), outline=(120, 120, 120))
            info = (
                f"#{int(r['review_index']):03d}\n"
                f"{r['dataset']}\nvid={r['video_id']}\n{r['path_id']}\n"
                f"query={r['query']}\nrank={int(r['candidate_rank'])}\nscore={float(r['score']):.3f}\n"
                f"IoU={float(r['matched_iou']):.2f}"
            )
            d.multiline_text((8, y + 8), info, fill=(0, 0, 0), font=FONT, spacing=4)
            try:
                im = Image.open(str(r["montage_path"])).convert("RGB")
                im.thumbnail((sheet_w - label_w - 20, row_h - 10))
                canvas.paste(im, (label_w, y + 5))
            except Exception as exc:
                d.text((label_w + 8, y + 8), f"missing montage: {exc}", fill=(200, 0, 0), font=FONT)
        out = OUT_DIR / f"owlv2_top150_sheet_{s:02d}.jpg"
        canvas.save(out, quality=92)


def main() -> None:
    candidates = pd.read_csv(CANDIDATES_CSV)
    labels = pd.read_csv(LABELS_CSV)
    labels = labels.drop(columns=[c for c in ["montage_path", "review_index"] if c in labels.columns], errors="ignore")
    nodes = load_nodes()
    review = candidates.copy()
    review.insert(0, "review_index", range(len(review)))
    paths = []
    for _, row in review.iterrows():
        paths.append(str(make_montage(row, nodes)))
    review["montage_path"] = paths
    labels.insert(0, "review_index", range(len(labels)))
    labels["montage_path"] = paths
    review_csv = AUDIT_DIR / "owlv2_top150_mini_audit_review.csv"
    labels_csv = AUDIT_DIR / "owlv2_top150_mini_audit_labels_with_montages.csv"
    review.to_csv(review_csv, index=False)
    labels.to_csv(labels_csv, index=False)
    make_sheets(review)
    print({"review_csv": str(review_csv), "labels_csv": str(labels_csv), "sheets": len(list(OUT_DIR.glob('*.jpg'))), "montages": len(paths)})


if __name__ == "__main__":
    main()
