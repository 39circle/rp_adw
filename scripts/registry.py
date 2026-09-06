"""registry.csv と option.json の読み書き。"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
HEADER = ["base_item", "variant_id", "namespace", "model_path"]
NAMESPACE_RE = re.compile(r"^[a-z0-9_]+$")

REPO_ROOT = Path(__file__).resolve().parent.parent
OPTION_PATH = REPO_ROOT / "option.json"
REGISTRY_PATH = REPO_ROOT / "registry.csv"


def load_option(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("option.json はオブジェクトでなければならない")
    option: dict[str, int] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key:
            raise ValueError("option.json のキーは空でない文字列でなければならない")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{key}: 枠数は 1 以上の整数でなければならない")
        option[key] = value
    return option


def write_registry(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# schema_version: {SCHEMA_VERSION}\n")
        writer = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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
