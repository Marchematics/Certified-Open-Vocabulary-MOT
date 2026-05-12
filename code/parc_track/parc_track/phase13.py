from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path
from typing import Any

import pandas as pd

from .adapters.datasets import ensure_data_output, write_json


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
RELIABILITY_DIR = DATA_ROOT / "outputs/milestones/reliability_fortress"
GENERALITY_DIR = DATA_ROOT / "outputs/milestones/generality_reliability"
LVVIS_DIR = DATA_ROOT / "outputs/milestones/lvvis_certification"
LVVIS_MASK_DIR = DATA_ROOT / "outputs/milestones/lvvis_mask_certification"
LEGACY_DIR = DATA_ROOT / "outputs/milestones/legacy_core_results"
PHASE13_DIR = DATA_ROOT / "outputs/phase13_nmi_release_story"
MILESTONE_DIR = DATA_ROOT / "outputs/milestones/nmi_release_story"
PACKAGE_PATH = DATA_ROOT / "outputs/packages/nmi_release_story.tar.gz"


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize_public_text_files(root: Path) -> None:
    replacements = {
        str(DATA_ROOT): "${PARC_TRACK_ROOT}",
        "/home/" + "waas" + "/paper_experiments": "${PARC_TRACK_ROOT}",
        "/" + "root" + "/parc_data": "${PARC_RAW_DATA_ROOT}",
        "/" + "root": "${HOME}",
    }
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix.lower() not in {".csv", ".json", ".md", ".txt", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        if cleaned != text:
            path.write_text(cleaned, encoding="utf-8")


def _write_manifest(root: Path) -> Path:
    manifest = ensure_data_output(root / "MANIFEST_SHA256.txt")
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path == manifest:
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return manifest


def _copy_if_exists(src: Path, dst: Path) -> Path | None:
    if not src.exists() or not src.is_file():
        return None
    out = ensure_data_output(dst)
    if src.resolve() != out.resolve():
        shutil.copy2(src, out)
    return out


def _mean_or_blank(frame: pd.DataFrame, column: str) -> float | str:
    if frame.empty or column not in frame:
        return ""
    series = frame[column]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, -1]
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if not values.empty else ""


def _sum_or_blank(frame: pd.DataFrame, column: str) -> float | str:
    if frame.empty or column not in frame:
        return ""
    series = frame[column]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, -1]
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.sum()) if not values.empty else ""


def _summarize_group(
    frame: pd.DataFrame,
    *,
    dataset: str,
    task: str,
    modality: str,
    source: str,
    alpha: float | str,
    evidence_role: str,
    paper_scope: str,
    source_table: str,
) -> dict[str, Any]:
    released = pd.to_numeric(frame.get("released", pd.Series(dtype=float)), errors="coerce")
    status_col = frame.get("empty_reason", pd.Series("", index=frame.index)).fillna("").astype(str)
    release_state = "positive_certified_release" if released.fillna(0).gt(0).any() else "certified_refusal_or_empty"
    if released.fillna(0).gt(0).any() and pd.to_numeric(frame.get("UTR", pd.Series(0, index=frame.index)), errors="coerce").fillna(0).max() > 0.2:
        release_state = "high_utr_stress_release"
    return {
        "dataset": dataset,
        "task": task,
        "modality": modality,
        "source": source,
        "alpha1": alpha,
        "seeds": int(frame["seed"].nunique()) if "seed" in frame and not frame.empty else "",
        "M": int(pd.to_numeric(frame.get("M", frame.get("candidate_budget_M", pd.Series([150]))), errors="coerce").dropna().iloc[0])
        if not frame.empty and not pd.to_numeric(frame.get("M", frame.get("candidate_budget_M", pd.Series([150]))), errors="coerce").dropna().empty
        else 150,
        "released_mean": _mean_or_blank(frame, "released"),
        "released_min": float(released.min()) if not released.dropna().empty else "",
        "released_max": float(released.max()) if not released.dropna().empty else "",
        "UTR_mean": _mean_or_blank(frame, "UTR") if "UTR" in frame else _mean_or_blank(frame, "utr"),
        "conservative_FTR_mean": _mean_or_blank(frame, "conservative_FTR")
        if "conservative_FTR" in frame
        else _mean_or_blank(frame, "conservative_ftr"),
        "mass_ratio_mean": _mean_or_blank(frame, "mass_ratio") if "mass_ratio" in frame else _mean_or_blank(frame, "best_mass_ratio"),
        "release_state": release_state,
        "empty_reason_examples": ";".join(sorted(set(status_col[status_col.ne("")].head(3)))),
        "evidence_role": evidence_role,
        "paper_scope": paper_scope,
        "source_table": source_table,
    }


def build_nontracking_positive_table(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE13_DIR)
    rows: list[dict[str, Any]] = []

    lvis = _read_csv(GENERALITY_DIR / "table_lvis_detection_certification.csv")
    if not lvis.empty:
        for (detector, alpha), group in lvis.groupby(["detector", "alpha1"], dropna=False):
            role = "single_frame_detection_positive" if str(detector) == "GroundingDINO" else "single_frame_detection_stress_or_refusal"
            scope = "generality_evidence_not_sota_detection_benchmark"
            rows.append(
                _summarize_group(
                    group,
                    dataset="LVIS",
                    task="single_frame_open_vocabulary_detection",
                    modality="box",
                    source=str(detector),
                    alpha=float(alpha),
                    evidence_role=role,
                    paper_scope=scope,
                    source_table="generality_reliability/table_lvis_detection_certification.csv",
                )
            )

    lvvis = _read_csv(LVVIS_DIR / "table_lvvis_parc_summary.csv")
    if not lvvis.empty:
        converted = lvvis.rename(
            columns={
                "released_mean": "released",
                "utr_mean": "UTR",
                "conservative_ftr_mean": "conservative_FTR",
                "margin_mean": "mass_ratio",
            }
        ).copy()
        converted["seed"] = "mean"
        converted["M"] = 150
        for alpha, group in converted.groupby("alpha1", dropna=False):
            rows.append(
                _summarize_group(
                    group,
                    dataset="LVVIS",
                    task="open_vocabulary_video_instance_scaffold",
                    modality="box_path",
                    source="GroundingDINO",
                    alpha=float(alpha),
                    evidence_role="non_tracking_or_weak_tracking_positive_scaffold",
                    paper_scope="generality_evidence_not_sota_video_instance_benchmark",
                    source_table="lvvis_certification/table_lvvis_parc_summary.csv",
                )
            )

    mask = _read_csv(LVVIS_MASK_DIR / "table_lvvis_mask_certification.csv")
    if mask.empty:
        mask = _read_csv(GENERALITY_DIR / "table_ovvis_mask_certification.csv")
    if not mask.empty:
        mask = mask.copy()
        if "utr" in mask and "UTR" not in mask:
            mask["UTR"] = mask["utr"]
        if "conservative_ftr" in mask and "conservative_FTR" not in mask:
            mask["conservative_FTR"] = mask["conservative_ftr"]
        group_cols = ["dataset", "alpha1", "mask_iou_threshold"] if "mask_iou_threshold" in mask else ["dataset", "alpha1"]
        for keys, group in mask.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            dataset = str(keys[0])
            alpha = float(keys[1])
            threshold = keys[2] if len(keys) > 2 else ""
            rows.append(
                _summarize_group(
                    group,
                    dataset=dataset,
                    task="mask_path_certification",
                    modality=f"mask_path_iou_{threshold}" if threshold != "" else "mask_path",
                    source="SAM_box_prompt_or_rectangle_mask_scaffold",
                    alpha=alpha,
                    evidence_role="mask_morphology_extension",
                    paper_scope="proof_of_principle_not_full_mask_sota_benchmark",
                    source_table="lvvis_mask_certification/table_lvvis_mask_certification.csv"
                    if (LVVIS_MASK_DIR / "table_lvvis_mask_certification.csv").exists()
                    else "generality_reliability/table_ovvis_mask_certification.csv",
                )
            )

    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_nmi_nontracking_positive.csv")
    table.to_csv(out_csv, index=False)
    return {"status": "completed" if not table.empty else "missing_nontracking_sources", "table": str(out_csv), "rows": int(len(table))}


def _policy_row(
    *,
    dataset: str,
    task: str,
    source: str,
    policy: str,
    alpha: float | str,
    frame: pd.DataFrame,
    source_table: str,
    has_alpha_control: bool,
    release_decision: str,
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "task": task,
        "source": source,
        "policy": policy,
        "alpha1": alpha,
        "rows": int(len(frame)),
        "released_mean": _mean_or_blank(frame, "released"),
        "released_sum": _sum_or_blank(frame, "released"),
        "UTR_mean": _mean_or_blank(frame, "UTR") if "UTR" in frame else _mean_or_blank(frame, "utr"),
        "audited_FTR_mean": _mean_or_blank(frame, "audited_ftr_on_labeled_released"),
        "conservative_FTR_mean": _mean_or_blank(frame, "conservative_FTR")
        if "conservative_FTR" in frame
        else _mean_or_blank(frame, "conservative_ftr_uncertain_and_unlabeled_false")
        if "conservative_ftr_uncertain_and_unlabeled_false" in frame
        else _mean_or_blank(frame, "conservative_ftr"),
        "mass_ratio_mean": _mean_or_blank(frame, "mass_ratio") if "mass_ratio" in frame else _mean_or_blank(frame, "best_mass_ratio"),
        "empty_reason_examples": ";".join(
            sorted(
                set(
                    frame.get("empty_reason", pd.Series("", index=frame.index))
                    .fillna("")
                    .astype(str)
                    .loc[lambda s: s.ne("")]
                    .head(3)
                )
            )
        )
        if not frame.empty
        else "",
        "has_alpha_control": bool(has_alpha_control),
        "release_decision": release_decision,
        "source_table": source_table,
    }


def build_release_policy_value_table(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE13_DIR)
    rows: list[dict[str, Any]] = []

    lvvis_baselines = _read_csv(LVVIS_DIR / "table_baseline_expanded.csv")
    if not lvvis_baselines.empty and "method" in lvvis_baselines:
        for (method, alpha), group in lvvis_baselines.groupby(["method", "alpha1"], dropna=False):
            method_s = str(method)
            policy = {
                "confidence_threshold": "score_threshold",
                "greedy_score_no_risk": "topM_no_risk",
                "parc_track_gamma_tuned_uniform_scs": "PARC_certified_release",
                "unmatched_as_false_block": "wrong_negative_certified_baseline",
                "null_superset_no_audit": "PARC_no_audit_variant",
            }.get(method_s, method_s)
            rows.append(
                _policy_row(
                    dataset="LVVIS",
                    task="open_vocabulary_visual_release",
                    source="GroundingDINO",
                    policy=policy,
                    alpha=float(alpha),
                    frame=group,
                    source_table="lvvis_certification/table_baseline_expanded.csv",
                    has_alpha_control=policy.startswith("PARC") or "certified" in policy,
                    release_decision="release",
                )
            )

    published = _read_csv(RELIABILITY_DIR / "table_published_tracker_certification.csv")
    if not published.empty and {"method", "tracker", "dataset", "alpha1"}.issubset(published.columns):
        selected = published[published["method"].isin(["raw_tracker_topM", "parc_wrapped"])].copy()
        for (tracker, dataset, method, alpha), group in selected.groupby(["tracker", "dataset", "method", "alpha1"], dropna=False):
            rows.append(
                _policy_row(
                    dataset=str(dataset),
                    task="published_tracker_output",
                    source=str(tracker),
                    policy="raw_tracker_topM" if str(method) == "raw_tracker_topM" else "PARC_certified_wrapper",
                    alpha=float(alpha),
                    frame=group.rename(columns={"parc_release": "released"}) if str(method) != "raw_tracker_topM" else group,
                    source_table="reliability_fortress/table_published_tracker_certification.csv",
                    has_alpha_control=str(method) != "raw_tracker_topM",
                    release_decision="refusal" if pd.to_numeric(group.get("released", group.get("parc_release", pd.Series(0))), errors="coerce").fillna(0).sum() == 0 else "release",
                )
            )

    blackbox = _read_csv(RELIABILITY_DIR / "table_blackbox_generator_certification.csv")
    if not blackbox.empty and {"generator", "dataset", "alpha1"}.issubset(blackbox.columns):
        for (generator, dataset, alpha), group in blackbox.groupby(["generator", "dataset", "alpha1"], dropna=False):
            released_total = pd.to_numeric(group.get("released", pd.Series(0, index=group.index)), errors="coerce").fillna(0).sum()
            rows.append(
                _policy_row(
                    dataset=str(dataset),
                    task="blackbox_generator_output",
                    source=str(generator),
                    policy="PARC_certified_release_or_refusal",
                    alpha=float(alpha),
                    frame=group,
                    source_table="reliability_fortress/table_blackbox_generator_certification.csv",
                    has_alpha_control=True,
                    release_decision="refusal" if released_total == 0 else "release",
                )
            )

    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "table_release_policy_value.csv")
    fig_csv = ensure_data_output(output_dir / "figure_release_policy_decision_curve.csv")
    table.to_csv(out_csv, index=False)
    figure_cols = [
        "dataset",
        "task",
        "source",
        "policy",
        "alpha1",
        "released_mean",
        "UTR_mean",
        "conservative_FTR_mean",
        "mass_ratio_mean",
        "has_alpha_control",
        "release_decision",
    ]
    table[[col for col in figure_cols if col in table.columns]].to_csv(fig_csv, index=False)
    return {"status": "completed" if not table.empty else "missing_policy_sources", "table": str(out_csv), "figure_csv": str(fig_csv), "rows": int(len(table))}


def _relative_public_reference(value: Any) -> str:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return ""
    raw = str(value)
    path = Path(raw)
    try:
        if path.is_absolute():
            return path.relative_to(DATA_ROOT).as_posix()
    except ValueError:
        return ""
    if raw.startswith("outputs/"):
        return raw
    return raw if not raw.startswith("/") else ""


def _pick_examples(frame: pd.DataFrame, label: str | None, count: int = 8) -> pd.DataFrame:
    if frame.empty:
        return frame
    data = frame.copy()
    if label is not None and "label" in data:
        data = data[data["label"].astype(str).eq(label)].copy()
    sort_cols = [col for col in ("confidence", "score", "candidate_rank") if col in data]
    if "candidate_rank" in sort_cols:
        data["_rank"] = pd.to_numeric(data["candidate_rank"], errors="coerce")
        data = data.sort_values("_rank", ascending=True)
    elif "score" in sort_cols:
        data["_score"] = pd.to_numeric(data["score"], errors="coerce")
        data = data.sort_values("_score", ascending=False)
    return data.head(count)


def build_teaser_manifest(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE13_DIR)
    rows: list[dict[str, Any]] = []

    audit = _read_csv(RELIABILITY_DIR / "audit_labels_2000_human_reviewed.csv")
    released = _read_csv(LEGACY_DIR / "phase2h_first_real_nonempty/released_tracks.csv")
    owlv2 = _read_csv(LEGACY_DIR / "phase4_third_generator_and_owlv2_audit/owlv2_top150_mini_audit_labels_with_montages.csv")

    def add_rows(source: pd.DataFrame, case_type: str, label: str, rationale: str, limit: int = 8) -> None:
        for _, row in _pick_examples(source, label, limit).iterrows():
            montage = _relative_public_reference(row.get("montage_path", row.get("pending_montage_path", "")))
            rows.append(
                {
                    "case_type": case_type,
                    "dataset": row.get("dataset", ""),
                    "video_id": row.get("video_id", row.get("image_id", "")),
                    "path_id": row.get("path_id", ""),
                    "query": row.get("query", ""),
                    "score": row.get("score", ""),
                    "label": row.get("label", ""),
                    "verified_positive_for_calibration": row.get("verified_positive_for_calibration", ""),
                    "rationale": rationale,
                    "visual_asset_ref": montage,
                    "visual_asset_status": "public_manifest_reference" if montage else "missing_visual_asset",
                    "paper_use": "qualitative_candidate_pool",
                }
            )

    if not released.empty:
        supported = released.copy()
        if "is_unmatched" in supported:
            supported = supported[supported["is_unmatched"].astype(str).str.lower().isin(["false", "0"])].copy()
        supported["label"] = "official_matched"
        add_rows(supported, "official_matched_positive", "official_matched", "normal officially supported reference", 8)

    add_rows(audit, "real_official_unmatched", "actually_true", "real object that official matching would treat as unsupported", 8)
    add_rows(audit, "uncertain", "uncertain", "kept conservative and never used as verified positive", 8)
    add_rows(audit, "actually_false", "actually_false", "false tracklet that should not be released", 8)

    if not owlv2.empty:
        stress = owlv2.copy()
        stress["label"] = stress.get("label", "")
        add_rows(stress, "high_score_topM_parc_refusal_candidate", None, "high-score stress candidate used to explain certified refusal", 8)

    if not released.empty:
        cert = released.copy()
        cert["label"] = "certified_release"
        add_rows(cert, "PARC_certified_release", "certified_release", "candidate selected by self-consistent certified release", 8)

    table = pd.DataFrame(rows)
    out_csv = ensure_data_output(output_dir / "figure_nmi_teaser_manifest.csv")
    table.to_csv(out_csv, index=False)
    return {"status": "completed" if not table.empty else "missing_teaser_sources", "manifest": str(out_csv), "rows": int(len(table))}


def _write_no_raw_report(milestone: Path) -> Path:
    forbidden_suffixes = {".mp4", ".mov", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".webp", ".pth", ".pt", ".safetensors"}
    hits = []
    for path in milestone.rglob("*"):
        if path.is_file() and path.suffix.lower() in forbidden_suffixes:
            hits.append(path.relative_to(milestone).as_posix())
    report = {
        "raw_videos_images_weights_included": bool(hits),
        "forbidden_file_hits": hits,
        "policy": "package contains public-safe CSV/JSON/MD/TXT artifacts only; raw datasets, image crops, videos, weights, and caches are excluded",
    }
    out = ensure_data_output(milestone / "NO_RAW_DATA_SAFETY_REPORT.json")
    write_json(out, report)
    return out


def _write_run_report(milestone: Path, summary: dict[str, Any]) -> Path:
    report = ensure_data_output(milestone / "RUN_REPORT.md")
    report.write_text(
        "# NMI Release Story\n\n"
        "This milestone reframes PARC-Track as auditable release-time certification for open-vocabulary "
        "visual AI under incomplete annotations. It is intentionally compact: it does not add more MOT "
        "grids, and it does not claim SOTA tracking, detection, or segmentation performance.\n\n"
        "## Included Evidence\n\n"
        "1. Non-tracking positive evidence from LVIS/LVVIS detection and mask-path scaffolds.\n"
        "2. Release-policy value tables contrasting score/top-M style release with PARC release/refusal.\n"
        "3. A qualitative teaser manifest for official matches, real official-unmatched objects, uncertain "
        "cases, false tracklets, high-score refusal candidates, and certified releases.\n\n"
        "## Scope\n\n"
        "- Detection and mask rows are generality evidence, not SOTA benchmark claims.\n"
        "- Visual examples are represented as public-safe manifests; raw images/videos are not packaged.\n"
        "- Existing Audit2000 and reliability-fortress results remain the reliability foundation.\n\n"
        f"## Summary JSON\n\n```json\n{json.dumps(summary, indent=2, ensure_ascii=False)}\n```\n",
        encoding="utf-8",
    )
    return report


def run_phase13_nmi_release_story(out_dir: str | Path | None = None) -> dict[str, Any]:
    phase_dir = ensure_data_output(PHASE13_DIR)
    nontracking = build_nontracking_positive_table(phase_dir)
    policy = build_release_policy_value_table(phase_dir)
    teaser = build_teaser_manifest(phase_dir)

    milestone = ensure_data_output(out_dir or MILESTONE_DIR)
    milestone.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for src in (Path(nontracking["table"]), Path(policy["table"]), Path(policy["figure_csv"]), Path(teaser["manifest"])):
        out = _copy_if_exists(src, milestone / src.name)
        if out is not None:
            copied.append(out.name)

    summary = {
        "status": "completed",
        "milestone": "outputs/milestones/nmi_release_story",
        "nontracking_positive": nontracking,
        "release_policy_value": policy,
        "teaser_manifest": teaser,
        "copied_files": copied,
        "raw_data_included": False,
        "model_weights_included": False,
        "package": "outputs/packages/nmi_release_story.tar.gz",
    }
    write_json(milestone / "nmi_release_story_summary.json", summary)
    _write_run_report(milestone, summary)
    _write_no_raw_report(milestone)
    _sanitize_public_text_files(milestone)
    _write_manifest(milestone)

    package = ensure_data_output(PACKAGE_PATH)
    if package.exists():
        package.unlink()
    with tarfile.open(package, "w:gz") as tar:
        for path in sorted(milestone.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=Path("nmi_release_story") / path.relative_to(milestone))
    summary["package_sha256"] = _sha256(package)
    write_json(milestone / "nmi_release_story_summary.json", summary)
    _sanitize_public_text_files(milestone)
    _write_manifest(milestone)
    return summary
