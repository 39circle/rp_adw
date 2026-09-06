#!/usr/bin/env python3
"""option.json から registry.csv の枠を展開する。"""

from __future__ import annotations

import argparse
import sys

from registry import (
    NAMESPACE_RE,
    OPTION_PATH,
    REGISTRY_PATH,
    SCHEMA_VERSION,
    load_option,
    parse_registry,
    write_registry,
)


def build_rows(option: dict[str, int]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for base_item, count in option.items():
        for variant_id in range(1, count + 1):
            rows.append(
                {
                    "base_item": base_item,
                    "variant_id": str(variant_id),
                    "namespace": "",
                    "model_path": "",
                }
            )
    return rows


def cmd_init(force: bool) -> int:
    if not OPTION_PATH.exists():
        print(f"option.json がない: {OPTION_PATH}", file=sys.stderr)
        return 1
    option = load_option(OPTION_PATH)
    if REGISTRY_PATH.exists() and not force:
        _, existing = parse_registry(REGISTRY_PATH)
        assigned = [
            row
            for row in existing
            if row["namespace"] or row["model_path"]
        ]
        if assigned:
            print(
                "registry.csv に割当がある。上書きするには --force が必要",
                file=sys.stderr,
            )
            return 1
    write_registry(REGISTRY_PATH, build_rows(option))
    print(f"wrote {REGISTRY_PATH}")
    return 0


def validate(option: dict[str, int], version: str, rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    if version != SCHEMA_VERSION:
        errors.append(f"schema_version が不正: {version}")

    csv_items: list[str] = []
    seen: set[tuple[str, str]] = set()
    grouped: dict[str, list[int]] = {}

    for i, row in enumerate(rows, start=2):
        loc = f"行 {i}"
        base_item = row["base_item"]
        variant_raw = row["variant_id"]
        namespace = row["namespace"]
        model_path = row["model_path"]

        if not base_item:
            errors.append(f"{loc}: base_item が空")
            continue
        csv_items.append(base_item)
        if base_item not in option:
            errors.append(f"{loc}: {base_item} は option.json にない")

        try:
            variant_id = int(variant_raw)
        except ValueError:
            errors.append(f"{loc}: variant_id が整数でない: {variant_raw}")
            continue
        if variant_id < 1:
            errors.append(f"{loc}: variant_id は 1 以上: {variant_id}")

        key = (base_item, str(variant_id))
        if key in seen:
            errors.append(f"{loc}: {base_item}+{variant_id} が重複")
        seen.add(key)
        grouped.setdefault(base_item, []).append(variant_id)

        ns_filled = bool(namespace)
        path_filled = bool(model_path)
        if ns_filled != path_filled:
            errors.append(f"{loc}: namespace と model_path は両方入るか両方空")
        if ns_filled and not NAMESPACE_RE.fullmatch(namespace):
            errors.append(f"{loc}: namespace が不正: {namespace}")

    if csv_items != [
        item for item, count in option.items() for _ in range(count)
    ]:
        errors.append("option.json のキー順・枠数と CSV の行が一致しない")

    for base_item, count in option.items():
        ids = grouped.get(base_item, [])
        expected = list(range(1, count + 1))
        if sorted(ids) != expected:
            errors.append(f"{base_item}: variant_id は 1..{count} が連続でなければならない")

    return errors


def cmd_validate() -> int:
    if not OPTION_PATH.exists():
        print(f"option.json がない: {OPTION_PATH}", file=sys.stderr)
        return 1
    if not REGISTRY_PATH.exists():
        print(f"registry.csv がない: {REGISTRY_PATH}", file=sys.stderr)
        return 1
    option = load_option(OPTION_PATH)
    version, rows = parse_registry(REGISTRY_PATH)
    errors = validate(option, version, rows)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="registry.csv の枠を option.json から展開する")
    sub = parser.add_subparsers(dest="command", required=True)
    init_p = sub.add_parser("init", help="未割当の registry.csv を生成する")
    init_p.add_argument(
        "--force",
        action="store_true",
        help="既存の割当を破棄して再生成する",
    )
    sub.add_parser("validate", help="option.json と registry.csv を検証する")
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(force=args.force)
    if args.command == "validate":
        return cmd_validate()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
