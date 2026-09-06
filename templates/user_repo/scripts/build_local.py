#!/usr/bin/env python3
"""ユーザーリポジトリで items JSON を生成する。"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from registry import REGISTRY_PATH, SCHEMA_VERSION, assigned_rows, parse_registry

REPO_ROOT = Path(__file__).resolve().parent.parent


class BuildLocalError(Exception):
    pass


def model_file(namespace: str, model_path: str) -> Path:
    return REPO_ROOT / "assets" / namespace / "models" / f"{model_path}.json"


def build_items_json(base_item: str, rows: list[dict[str, str]]) -> dict:
    entries = []
    for row in rows:
        entries.append(
            {
                "threshold": int(row["variant_id"]),
                "model": {
                    "type": "minecraft:model",
                    "model": f"{row['namespace']}:{row['model_path']}",
                },
            }
        )
    return {
        "model": {
            "type": "minecraft:range_dispatch",
            "property": "minecraft:damage",
            "normalize": False,
            "entries": entries,
            "fallback": {
                "type": "minecraft:model",
                "model": f"minecraft:item/{base_item}",
            },
        }
    }


def generate() -> list[Path]:
    if not REGISTRY_PATH.exists():
        raise BuildLocalError(f"registry.csv がない: {REGISTRY_PATH}")
    version, rows = parse_registry(REGISTRY_PATH)
    if version != SCHEMA_VERSION:
        raise BuildLocalError(f"schema_version が不正: {version}")

    assigned, errors = assigned_rows(rows)
    if errors:
        raise BuildLocalError("\n".join(errors))

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in assigned:
        path = model_file(row["namespace"], row["model_path"])
        if not path.is_file():
            raise BuildLocalError(f"モデルがない: {path}")
        grouped[row["base_item"]].append(row)

    for items in grouped.values():
        items.sort(key=lambda row: int(row["variant_id"]))

    items_dir = REPO_ROOT / "assets" / "minecraft" / "items"
    items_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for base_item, item_rows in grouped.items():
        dest = items_dir / f"{base_item}.json"
        dest.write_text(
            json.dumps(build_items_json(base_item, item_rows), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        written.append(dest)
    return written


def main() -> int:
    try:
        written = generate()
    except BuildLocalError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
