#!/usr/bin/env python3
"""registry.csv から対象 namespace のスライスを出力する。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from registry import HEADER, REGISTRY_PATH, SCHEMA_VERSION, parse_registry, write_registry


def select_rows(namespace: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["namespace"] == namespace]


def cmd_export(namespace: str, output: Path) -> int:
    if not REGISTRY_PATH.exists():
        print(f"registry.csv がない: {REGISTRY_PATH}", file=sys.stderr)
        return 1

    version, rows = parse_registry(REGISTRY_PATH)
    if version != SCHEMA_VERSION:
        print(f"schema_version が不正: {version}", file=sys.stderr)
        return 1

    selected = select_rows(namespace, rows)
    if not selected:
        print(f"{namespace} の割当行がない", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    write_registry(output, selected)
    print(f"wrote {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="対象 namespace の registry.csv スライスを出力する")
    parser.add_argument("namespace", help="切り出す namespace")
    parser.add_argument("output", nargs="?", help="出力先。省略時は dist/registry_<ns>.csv")
    args = parser.parse_args(argv)

    output = (
        Path(args.output)
        if args.output
        else REGISTRY_PATH.parent / "dist" / f"registry_{args.namespace}.csv"
    )
    return cmd_export(args.namespace, output)


if __name__ == "__main__":
    raise SystemExit(main())
