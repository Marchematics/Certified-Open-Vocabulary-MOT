from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "materials_label_discordance_preregistration"


def version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not_installed"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def update_manifest(directory: Path) -> None:
    lines = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(directory)}")
    (directory / "MANIFEST_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    key = os.environ.get("MP_API_KEY", "")
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "check_id": "materials_project_mp149_summary_smoke",
        "checked_at_utc": now,
        "source": "Materials Project",
        "credential_env_present": str(bool(key)).lower(),
        "mp_api_version": version("mp-api"),
        "pymatgen_version": version("pymatgen"),
        "query_target": "mp-149",
        "query_fields": "material_id,formula_pretty,energy_above_hull",
        "status": "not_run",
        "returned_n": "0",
        "returned_material_id": "",
        "returned_formula": "",
        "returned_energy_above_hull": "",
        "error_type": "",
        "error_message_redacted": "",
        "secret_written_to_artifact": "false",
    }

    if not key:
        row["status"] = "blocked_missing_MP_API_KEY_env"
    else:
        try:
            from mp_api.client import MPRester

            with MPRester(key) as mpr:
                docs = mpr.materials.summary.search(
                    material_ids=["mp-149"],
                    fields=["material_id", "formula_pretty", "energy_above_hull"],
                )
            row["returned_n"] = str(len(docs))
            if docs:
                doc = docs[0]
                row["returned_material_id"] = str(getattr(doc, "material_id", ""))
                row["returned_formula"] = str(getattr(doc, "formula_pretty", ""))
                row["returned_energy_above_hull"] = str(getattr(doc, "energy_above_hull", ""))
                row["status"] = "pass"
            else:
                row["status"] = "failed_empty_response"
        except Exception as exc:  # pragma: no cover - depends on external service
            row["status"] = "failed_exception"
            row["error_type"] = type(exc).__name__
            row["error_message_redacted"] = str(exc).replace(key, "<redacted>")[:240]

    write_csv(OUT / "table_data_access_smoke.csv", [row])
    update_manifest(OUT)


if __name__ == "__main__":
    main()
