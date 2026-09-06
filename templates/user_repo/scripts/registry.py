"""registry.csv の読み書き。"""

from __future__ import annotations

import csv
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
HEADER = ["base_item", "variant_id", "namespace", "model_path"]

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "registry.csv"


def parse_registry(path: Path) -> tuple[str, list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# schema_version:"):
        raise ValueError("先頭行に schema_version がなければならない")
    version = lines[0].split(":", 1)[1].strip()
    reader = csv.DictReader(lines[1:])
    if reader.fieldnames != HEADER:
        raise ValueError(f"ヘッダは {HEADER} でなければならない")
    rows = []
    for row in reader:
        rows.append({key: (row.get(key) or "").strip() for key in HEADER})
    return version, rows


def assigned_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    assigned: list[dict[str, str]] = []
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        namespace = row["namespace"]
        model_path = row["model_path"]
        if namespace and model_path:
            assigned.append(row)
        elif namespace or model_path:
            errors.append(f"行 {i}: namespace と model_path は両方入るか両方空")
    return assigned, errors
