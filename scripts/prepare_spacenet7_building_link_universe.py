#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, urlretrieve

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.errors import GEOSException


S3_BASE = "https://spacenet-dataset.s3.amazonaws.com/"
S3_ROOT = "spacenet/SN7_buildings/train/"
S3_NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
MONTH_RE = re.compile(r"global_monthly_(\d{4})_(\d{2})_mosaic_(.+?)_Buildings\.geojson$")


@dataclass(frozen=True)
class Building:
    aoi: str
    year: int
    month: int
    time_index: int
    building_id: str
    geom_wkt_hash: str
    area: float
    cx: float
    cy: float
    bounds: tuple[float, float, float, float]
    geom: object


def stable_unit_interval(value: str) -> float:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12 - 1)


def s3_list(prefix: str, max_keys: int = 1000) -> list[str]:
    keys: list[str] = []
    token: str | None = None
    while True:
        url = f"{S3_BASE}?list-type=2&prefix={quote(prefix)}&max-keys={max_keys}"
        if token:
            url += f"&continuation-token={quote(token)}"
        root = ET.fromstring(urlopen(url, timeout=120).read())
        for content in root.findall("s:Contents", S3_NS):
            key_node = content.find("s:Key", S3_NS)
            if key_node is not None and key_node.text:
                keys.append(key_node.text)
        if root.findtext("s:IsTruncated", default="false", namespaces=S3_NS) != "true":
            break
        token = root.findtext("s:NextContinuationToken", default="", namespaces=S3_NS)
        if not token:
            break
    return keys


def list_aois() -> list[str]:
    url = f"{S3_BASE}?list-type=2&prefix={quote(S3_ROOT)}&delimiter=/&max-keys=1000"
    root = ET.fromstring(urlopen(url, timeout=120).read())
    aois: list[str] = []
    for common in root.findall("s:CommonPrefixes", S3_NS):
        prefix = common.findtext("s:Prefix", default="", namespaces=S3_NS)
        if prefix:
            aois.append(prefix.rstrip("/").split("/")[-1])
    return sorted(aois)


def download_labels(aoi: str, cache_dir: Path) -> list[Path]:
    prefix = f"{S3_ROOT}{aoi}/labels_match/"
    keys = [key for key in s3_list(prefix) if key.endswith(".geojson")]
    local_paths: list[Path] = []
    for key in keys:
        local = cache_dir / key
        if not local.exists() or local.stat().st_size == 0:
            local.parent.mkdir(parents=True, exist_ok=True)
            urlretrieve(S3_BASE + key, local)
        local_paths.append(local)
    return sorted(local_paths)


def parse_month(path: Path) -> tuple[int, int, str]:
    match = MONTH_RE.match(path.name)
    if not match:
        raise ValueError(f"cannot parse SpaceNet 7 monthly label name: {path.name}")
    return int(match.group(1)), int(match.group(2)), match.group(3)


def load_buildings(path: Path, time_index: int) -> list[Building]:
    year, month, aoi = parse_month(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    buildings: list[Building] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        building_id = str(props.get("Id", ""))
        if building_id == "":
            continue
        try:
            geom = shape(feature.get("geometry"))
            if not geom.is_valid:
                geom = geom.buffer(0)
        except (GEOSException, ValueError, TypeError):
            continue
        if geom.is_empty or geom.area <= 0:
            continue
        centroid = geom.centroid
        geom_hash = hashlib.sha256(geom.wkb).hexdigest()[:16]
        buildings.append(
            Building(
                aoi=aoi,
                year=year,
                month=month,
                time_index=time_index,
                building_id=building_id,
                geom_wkt_hash=geom_hash,
                area=float(geom.area),
                cx=float(centroid.x),
                cy=float(centroid.y),
                bounds=tuple(float(v) for v in geom.bounds),
                geom=geom,
            )
        )
    return buildings


def bbox_iou(a: Building, b: Building) -> float:
    ax0, ay0, ax1, ay1 = a.bounds
    bx0, by0, bx1, by1 = b.bounds
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    iw = max(0.0, ix1 - ix0)
    ih = max(0.0, iy1 - iy0)
    inter = iw * ih
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


def link_components(source: Building, target: Building) -> tuple[float, float, float, float]:
    iou = bbox_iou(source, target)
    dist = math.hypot(source.cx - target.cx, source.cy - target.cy)
    size_norm = math.sqrt(max(source.area, 1.0)) + math.sqrt(max(target.area, 1.0))
    dist_score = 1.0 / (1.0 + dist / max(size_norm, 1.0))
    area_ratio = min(source.area, target.area) / max(source.area, target.area)
    base = 0.62 * iou + 0.28 * dist_score + 0.10 * area_ratio
    return float(base), float(iou), float(dist_score), float(area_ratio)


def build_universe(
    cache_dir: Path,
    out_dir: Path,
    max_aois: int,
    topk_per_source: int,
    frame_window: int,
    noisy_linker_weight: float,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    aois = list_aois()
    if max_aois > 0:
        aois = aois[:max_aois]

    rows: list[dict[str, object]] = []
    node_rows: list[dict[str, object]] = []
    score_rows: list[dict[str, object]] = []
    report_rows: list[dict[str, object]] = []
    video_id_map: dict[tuple[str, int], int] = {}
    next_video_id = 1

    for aoi in aois:
        print(f"[spacenet7] downloading/loading {aoi}", flush=True)
        paths = download_labels(aoi, cache_dir)
        month_buildings: list[tuple[tuple[int, int], list[Building]]] = []
        for idx, path in enumerate(paths):
            year, month, _ = parse_month(path)
            buildings = load_buildings(path, time_index=idx)
            month_buildings.append(((year, month), buildings))
            for building in buildings:
                node_rows.append(
                    {
                        "dataset": "SpaceNet7",
                        "aoi": aoi,
                        "year": year,
                        "month": month,
                        "time_index": idx,
                        "building_id": building.building_id,
                        "area": building.area,
                        "cx": building.cx,
                        "cy": building.cy,
                        "bounds": json.dumps(building.bounds),
                        "geom_hash": building.geom_wkt_hash,
                    }
                )
        month_buildings.sort(key=lambda item: item[0])
        candidate_count = 0
        supported_count = 0
        for pair_idx, ((year0, month0), sources) in enumerate(month_buildings[:-1]):
            (year1, month1), targets = month_buildings[pair_idx + 1]
            if not sources or not targets:
                continue
            window = pair_idx // frame_window
            key = (aoi, window)
            if key not in video_id_map:
                video_id_map[key] = next_video_id
                next_video_id += 1
            video_id = video_id_map[key]
            target_xy = np.asarray([(target.cx, target.cy) for target in targets], dtype=float)
            tree = cKDTree(target_xy)
            targets_by_id_index = {target.building_id: idx for idx, target in enumerate(targets)}
            for source in sources:
                k = min(topk_per_source, len(targets))
                _, indices = tree.query((source.cx, source.cy), k=k)
                chosen = set(int(idx) for idx in np.atleast_1d(indices).tolist())
                same_id_index = targets_by_id_index.get(source.building_id)
                if same_id_index is not None:
                    chosen.add(int(same_id_index))
                for target_idx in sorted(chosen):
                    target = targets[target_idx]
                    base_score, iou, dist_score, area_ratio = link_components(source, target)
                    is_true = source.building_id == target.building_id
                    path_id = (
                        f"SN7::{aoi}::{year0:04d}-{month0:02d}->{year1:04d}-{month1:02d}"
                        f"::{source.building_id}->{target.building_id}::{source.geom_wkt_hash}->{target.geom_wkt_hash}"
                    )
                    noise = stable_unit_interval(path_id)
                    # Deterministic score perturbation models an imperfect geometry-only linker while
                    # preserving interpretability of the link evidence.
                    score = (1.0 - noisy_linker_weight) * base_score + noisy_linker_weight * noise
                    candidate_count += 1
                    supported_count += int(is_true)
                    rows.append(
                        {
                            "dataset": "SpaceNet7",
                            "domain": "earth_observation_building_links",
                            "generator": "geometry_linker",
                            "aoi": aoi,
                            "video_id": video_id,
                            "path_id": path_id,
                            "source_building_id": source.building_id,
                            "target_building_id": target.building_id,
                            "frame_start": int(pair_idx),
                            "frame_end": int(pair_idx + 1),
                            "source_year": year0,
                            "source_month": month0,
                            "target_year": year1,
                            "target_month": month1,
                            "path_length": 2,
                            "score": float(score),
                            "objectness": float(base_score),
                            "semantic_margin": float(area_ratio),
                            "temporal_stability": float(dist_score),
                            "association_score": float(iou),
                            "candidate_rank": 0,
                            "matched_gt": bool(is_true),
                            "matched_category": "building_persistence" if is_true else "",
                            "is_matched_to_gt": bool(is_true),
                            "is_unmatched": not bool(is_true),
                            "cell_id": "building_link",
                            "bbox_iou": float(iou),
                            "centroid_distance_score": float(dist_score),
                            "area_ratio": float(area_ratio),
                            "base_geometry_score": float(base_score),
                            "deterministic_noise": float(noise),
                        }
                    )
                    score_rows.append(
                        {
                            "path_id": path_id,
                            "score": float(score),
                            "base_geometry_score": float(base_score),
                            "bbox_iou": float(iou),
                            "centroid_distance_score": float(dist_score),
                            "area_ratio": float(area_ratio),
                            "deterministic_noise": float(noise),
                        }
                    )
        report_rows.append(
            {
                "aoi": aoi,
                "months": len(month_buildings),
                "candidate_links": candidate_count,
                "gt_supported_links": supported_count,
                "support_rate": float(supported_count / candidate_count) if candidate_count else 0.0,
            }
        )

    universe = pd.DataFrame(rows)
    if universe.empty:
        raise RuntimeError("SpaceNet 7 building-link universe is empty")
    universe = universe.sort_values(["score", "path_id"], ascending=[False, True]).reset_index(drop=True)
    universe["candidate_rank"] = np.arange(1, len(universe) + 1)
    universe.to_csv(out_dir / "candidate_universe.csv", index=False)
    pd.DataFrame(node_rows).to_csv(out_dir / "candidate_nodes.csv", index=False)
    pd.DataFrame(score_rows).to_csv(out_dir / "candidate_scores.csv", index=False)
    report_df = pd.DataFrame(report_rows)
    report_df.to_csv(out_dir / "dataset_adapter_report_spacenet7.csv", index=False)
    report = {
        "status": "completed",
        "source": "SpaceNet 7 labels_match GeoJSON from public S3",
        "raw_labels_cache": str(cache_dir),
        "aoi_count": len(aois),
        "candidate_links": int(len(universe)),
        "gt_supported_links": int((~universe["is_unmatched"]).sum()),
        "blocks": int(universe["video_id"].nunique()),
        "topk_per_source": topk_per_source,
        "frame_window": frame_window,
        "noisy_linker_weight": noisy_linker_weight,
        "outputs": {
            "candidate_universe": str(out_dir / "candidate_universe.csv"),
            "candidate_nodes": str(out_dir / "candidate_nodes.csv"),
            "candidate_scores": str(out_dir / "candidate_scores.csv"),
            "adapter_report": str(out_dir / "dataset_adapter_report_spacenet7.csv"),
        },
    }
    with (out_dir / "SPACENET7_BUILDING_LINK_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="data/SpaceNet7")
    parser.add_argument("--out-dir", default="outputs/spacenet7_building_links/universe_geometry_w35")
    parser.add_argument("--max-aois", type=int, default=20)
    parser.add_argument("--topk-per-source", type=int, default=3)
    parser.add_argument("--frame-window", type=int, default=3)
    parser.add_argument("--noisy-linker-weight", type=float, default=0.35)
    args = parser.parse_args()
    report = build_universe(
        cache_dir=Path(args.cache_dir),
        out_dir=Path(args.out_dir),
        max_aois=args.max_aois,
        topk_per_source=args.topk_per_source,
        frame_window=args.frame_window,
        noisy_linker_weight=args.noisy_linker_weight,
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
