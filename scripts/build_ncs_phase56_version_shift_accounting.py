#!/usr/bin/env python3
"""Build Phase56 version-shift accounting lemma and decomposition tables."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
OUT = ROOT / "outputs/milestones/ncs_phase56_version_shift_accounting"
SCOPE = (
    "completed_version_shift_accounting;"
    "not_new_alpha_certificate;"
    "not_prospective_discovery;"
    "versioned_truth_decomposition"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def policy_mask(df: pd.DataFrame, policy: str) -> pd.Series:
    if policy == "PARC":
        return df["parc_seed_count"] > 0
    if policy == "raw_topK":
        return df["raw_topK_seed_count"] > 0
    if policy == "raw_topR":
        return df["raw_topR_seed_count"] > 0
    raise ValueError(f"unknown policy: {policy}")


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    rows: list[dict[str, object]] = []
    for k in [300, 500]:
        k_rows = candidates[candidates["K"].eq(k)].copy()
        for policy in ["PARC", "raw_topK", "raw_topR"]:
            subset = k_rows[policy_mask(k_rows, policy)].copy()
            n = int(len(subset))
            t0_stable = subset["stable_exact_t0"].astype(bool)
            t1_stable = subset["stable_exact_t1_current_mp"].astype(bool)
            labelable = subset["t1_label_status"].eq("labelable_current_MP_hull")

            t0_false = int((~t0_stable).sum())
            t1_false = int((~t1_stable).sum())
            stable_to_not_stable_t1 = int((t0_stable & ~t1_stable).sum())
            not_stable_to_stable_t1 = int((~t0_stable & t1_stable).sum())
            stable_to_unstable_labelable = int((t0_stable & ~t1_stable & labelable).sum())
            unstable_to_stable_labelable = int((~t0_stable & t1_stable & labelable).sum())
            stable_to_unmatched_or_uncertain = int((t0_stable & ~labelable).sum())
            not_stable_to_unmatched_or_uncertain = int((~t0_stable & ~labelable).sum())

            ftr_t0 = t0_false / n if n else 0.0
            ftr_t1 = t1_false / n if n else 0.0
            stable_to_not_stable_rate = stable_to_not_stable_t1 / n if n else 0.0
            not_stable_to_stable_rate = not_stable_to_stable_t1 / n if n else 0.0
            rhs = ftr_t0 + stable_to_not_stable_rate - not_stable_to_stable_rate
            conservative_bound = ftr_t0 + stable_to_not_stable_rate
            rows.append(
                {
                    "K": k,
                    "policy": policy,
                    "n_candidates": n,
                    "FTR_t0": ftr_t0,
                    "FTR_t1_conservative": ftr_t1,
                    "stable_to_current_not_stable_count": stable_to_not_stable_t1,
                    "stable_to_current_not_stable_rate": stable_to_not_stable_rate,
                    "not_stable_to_current_stable_count": not_stable_to_stable_t1,
                    "not_stable_to_current_stable_rate": not_stable_to_stable_rate,
                    "stable_to_unstable_labelable_only_count": stable_to_unstable_labelable,
                    "stable_to_unstable_labelable_only_rate": stable_to_unstable_labelable / n if n else 0.0,
                    "unstable_to_stable_labelable_only_count": unstable_to_stable_labelable,
                    "unstable_to_stable_labelable_only_rate": unstable_to_stable_labelable / n if n else 0.0,
                    "stable_to_unmatched_or_uncertain_count": stable_to_unmatched_or_uncertain,
                    "stable_to_unmatched_or_uncertain_rate": stable_to_unmatched_or_uncertain / n if n else 0.0,
                    "not_stable_to_unmatched_or_uncertain_count": not_stable_to_unmatched_or_uncertain,
                    "not_stable_to_unmatched_or_uncertain_rate": not_stable_to_unmatched_or_uncertain / n if n else 0.0,
                    "accounting_rhs": rhs,
                    "accounting_residual": ftr_t1 - rhs,
                    "conservative_upper_bound": conservative_bound,
                    "bound_slack": conservative_bound - ftr_t1,
                    "evidence_scope": SCOPE,
                }
            )

    fieldnames = list(rows[0].keys())
    write_csv(OUT / "table_version_shift_decomposition.csv", rows, fieldnames)

    fig_rows = []
    for row in rows:
        for component, value in [
            ("FTR_t0", row["FTR_t0"]),
            ("plus_stable_to_current_not_stable", row["stable_to_current_not_stable_rate"]),
            ("minus_not_stable_to_current_stable", -row["not_stable_to_current_stable_rate"]),
            ("FTR_t1_conservative", row["FTR_t1_conservative"]),
        ]:
            fig_rows.append(
                {
                    "K": row["K"],
                    "policy": row["policy"],
                    "component": component,
                    "component_value": value,
                    "evidence_scope": SCOPE,
                }
            )
    write_csv(
        OUT / "figure_version_shift_decomposition_inputs.csv",
        fig_rows,
        ["K", "policy", "component", "component_value", "evidence_scope"],
    )

    tex = r"""\paragraph{Version-shift accounting.}
Let \(Y_p^{t}\in\{0,1\}\) denote whether candidate \(p\) is stable under
truth version \(t\), and let \(R\) be a fixed release set selected before the
current-version audit. The false-release fraction under version \(t\) is
\[
\mathrm{FTR}_{t}(R)=\frac{1}{|R|}\sum_{p\in R}(1-Y_p^{t}).
\]
For two truth versions \(t_0,t_1\),
\[
\mathrm{FTR}_{t_1}(R)=\mathrm{FTR}_{t_0}(R)
+\frac{|\{p\in R:Y_p^{t_0}=1,Y_p^{t_1}=0\}|}{|R|}
-\frac{|\{p\in R:Y_p^{t_0}=0,Y_p^{t_1}=1\}|}{|R|}.
\]
Consequently,
\[
\mathrm{FTR}_{t_1}(R)\le
\mathrm{FTR}_{t_0}(R)
+\frac{|\{p\in R:Y_p^{t_0}=1,Y_p^{t_1}=0\}|}{|R|}.
\]
This is an accounting identity, not a new PARC guarantee. In the current-MP
audit, unmatched or unresolved current-version entries are conservatively
treated as \(Y_p^{t_1}=0\), so the exact table reports both the labelable-only
stable-to-unstable drift and the conservative stable-to-current-not-stable term.
Thus the t1 audit decomposes current-label burden into original t0 release
error plus reference-hull drift accounting; it does not certify
\(\alpha=0.10\) under the t1 truth definition.
"""
    (OUT / "supplement_version_shift_accounting.tex").write_text(tex, encoding="utf-8")

    closeout = """# Phase56 Version-Shift Accounting

Status: `completed_version_shift_accounting_not_new_certificate`

This milestone adds a deterministic accounting identity for a fixed release set
under two label versions. It explains why the current-MP t1 audit must be read
as version-shift utility accounting rather than a new alpha certificate.

Allowed claim: the t1 false-release burden decomposes into t0 release error plus
stable-to-current-not-stable drift minus not-stable-to-current-stable drift.

Forbidden claim: this lemma provides t1 alpha control or prospective materials
discovery.
"""
    (OUT / "NCS_PHASE56_VERSION_SHIFT_ACCOUNTING.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase56_version_shift_accounting",
        "source_table": rel(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv"),
        "status": "completed_version_shift_accounting_not_new_certificate",
        "evidence_scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    build()
