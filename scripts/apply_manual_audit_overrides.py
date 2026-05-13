#!/usr/bin/env python3
import argparse, csv, json, hashlib
from pathlib import Path
from collections import Counter

LABELS={"actually_true","actually_false","uncertain"}
VP={"yes","no"}
CONF={"high","medium","low"}
STATUS={"human_confirmed"}
ID_COLS={
    "boundary_challenge/audit_boundary_challenge_500_ai_prefill_for_human_review.csv": "boundary_sample_id",
    "audit2000_reannotation/audit2000_blind_reannotation_ai_prefill_for_human_review.csv": "reannotation_sample_id",
}
BASE=Path("outputs/milestones/reliability_fortress/audit_review")

def read_csv(path):
    with path.open(newline="") as f:
        r=csv.DictReader(f)
        return r.fieldnames, list(r)

def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--overrides", required=True)
    args=ap.parse_args()
    root=Path(args.repo_root)
    overrides_path=root/args.overrides
    _, overrides=read_csv(overrides_path)
    overrides=[r for r in overrides if any((r.get(k) or "").strip() for k in r)]
    if not overrides:
        raise SystemExit("No overrides filled in; refusing to write output.")

    by_file={}
    for i,r in enumerate(overrides, start=2):
        tf=(r.get("target_file") or "").strip()
        sid=(r.get("sample_id") or "").strip()
        lab=(r.get("second_reviewer_label") or "").strip()
        vp=(r.get("second_reviewer_verified_positive_for_calibration") or "").strip()
        reason=(r.get("second_reviewer_reason") or "").strip()
        conf=(r.get("second_reviewer_confidence") or "").strip()
        status=(r.get("review_status") or "").strip()
        if tf not in ID_COLS:
            raise SystemExit(f"row {i}: unsupported target_file {tf!r}")
        if not sid:
            raise SystemExit(f"row {i}: sample_id is required")
        if lab not in LABELS:
            raise SystemExit(f"row {i}: invalid label {lab!r}")
        if vp not in VP:
            raise SystemExit(f"row {i}: invalid verified-positive flag {vp!r}")
        if lab == "uncertain" and vp != "no":
            raise SystemExit(f"row {i}: uncertain rows must have verified-positive=no")
        if not reason:
            raise SystemExit(f"row {i}: second_reviewer_reason is required")
        if conf not in CONF:
            raise SystemExit(f"row {i}: invalid confidence {conf!r}")
        if status not in STATUS:
            raise SystemExit(f"row {i}: review_status must be human_confirmed for a real override")
        by_file.setdefault(tf, {})[sid]=r

    summaries=[]
    for tf, ov in by_file.items():
        in_path=root/BASE/tf
        id_col=ID_COLS[tf]
        fieldnames, rows=read_csv(in_path)
        ids={r[id_col] for r in rows}
        missing=sorted(set(ov)-ids)
        if missing:
            raise SystemExit(f"{tf}: unknown sample ids: {missing[:10]}")
        changed=0
        for r in rows:
            sid=r[id_col]
            if sid in ov:
                o=ov[sid]
                for col in ["second_reviewer_label","second_reviewer_verified_positive_for_calibration","second_reviewer_reason","second_reviewer_confidence","review_status"]:
                    r[col]=o[col].strip()
                changed+=1
        out_path=in_path.with_name(in_path.stem.replace("_ai_prefill_for_human_review", "") + "_human_reviewed_with_overrides.csv")
        write_csv(out_path, fieldnames, rows)
        sha=hashlib.sha256(out_path.read_bytes()).hexdigest()
        cnt=Counter(r["review_status"] for r in rows)
        lab=Counter(r["second_reviewer_label"] for r in rows)
        summary={"input": str(in_path), "output": str(out_path), "changed_rows": changed, "sha256": sha, "review_status_counts": dict(cnt), "label_counts": dict(lab)}
        (out_path.with_suffix(out_path.suffix+".summary.json")).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        summaries.append(summary)
    print(json.dumps(summaries, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
