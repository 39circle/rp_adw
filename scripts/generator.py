#!/usr/bin/env python3
"""registry.csv と素材から resourcepack.zip を組み立てる。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from registry import OPTION_PATH, REGISTRY_PATH, REPO_ROOT, assigned_rows, load_option, parse_registry

TMP_DIR = REPO_ROOT / "tmp"
ZIP_PATH = REPO_ROOT / "resourcepack.zip"
BASE_PACK_DIR = REPO_ROOT / "base_pack"
MODULES_DIR = REPO_ROOT / "modules"
ITEM_DISPATCH_PATH = REPO_ROOT / "item_dispatch.json"
MODERN_PACK_FORMAT = 46
LEGACY_PACK_FORMAT = 15
LEGACY_SPECIALS = {
    "black_concrete": {
        "parent": "minecraft:block/black_concrete",
    },
    "diamond_pickaxe": {
        "parent": "minecraft:item/handheld",
        "textures": {"layer0": "minecraft:item/diamond_pickaxe"},
    },
    "iron_trapdoor": {
        "parent": "minecraft:block/iron_trapdoor_bottom",
        "textures": {"layer0": "minecraft:block/iron_trapdoor"},
    },
    "stone_shovel": {
        "parent": "item/handheld",
        "textures": {"layer0": "item/stone_hoe"},
    },
}


class GeneratorError(Exception):
    pass


def ns_assets_dir(namespace: str) -> Path:
    return MODULES_DIR / f"rp_{namespace}" / "assets" / namespace


def model_file(namespace: str, model_path: str) -> Path:
    return ns_assets_dir(namespace) / "models" / f"{model_path}.json"


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["base_item"]].append(row)
    for base_item, items in grouped.items():
        try:
            items.sort(key=lambda row: int(row["variant_id"]))
        except ValueError as exc:
            raise GeneratorError(f"{base_item}: variant_id が整数でない") from exc
    return grouped


def load_dispatch_config() -> dict[str, dict[str, object]]:
    if not ITEM_DISPATCH_PATH.exists():
        raise GeneratorError(f"item_dispatch.json がない: {ITEM_DISPATCH_PATH}")
    data = json.loads(ITEM_DISPATCH_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GeneratorError("item_dispatch.json はオブジェクトでなければならない")
    return data


def base_item_model(base_item: str) -> dict[str, str]:
    return {
        "type": "minecraft:model",
        "model": f"minecraft:item/{base_item}",
    }


def base_item_model_ref(base_item: str) -> str:
    return f"minecraft:item/{base_item}"


def entry_threshold(
    *,
    base_item: str,
    variant_id: int,
    dispatch: dict[str, object],
    count: int,
) -> int | float:
    prop = dispatch.get("property")
    if prop == "minecraft:custom_model_data":
        return variant_id
    if prop == "minecraft:damage":
        normalize = dispatch.get("normalize", True)
        if not isinstance(normalize, bool):
            raise GeneratorError(f"{base_item}: normalize は boolean でなければならない")
        if normalize:
            return variant_id / (count + 1)
        return variant_id
    raise GeneratorError(f"{base_item}: 未対応の property: {prop}")


def build_items_json(base_item: str, rows: list[dict[str, str]], dispatch: dict[str, object]) -> dict:
    count = len(rows)
    entries = []
    for row in rows:
        variant_id = int(row["variant_id"])
        if row["namespace"] and row["model_path"]:
            model = {
                "type": "minecraft:model",
                "model": f"{row['namespace']}:{row['model_path']}",
            }
        else:
            model = base_item_model(base_item)
        entries.append(
            {
                "threshold": entry_threshold(
                    base_item=base_item,
                    variant_id=variant_id,
                    dispatch=dispatch,
                    count=count,
                ),
                "model": model,
            }
        )
    return {
        "model": {
            "type": "minecraft:range_dispatch",
            "property": dispatch["property"],
            "entries": entries,
            "fallback": base_item_model(base_item),
        }
    }


def apply_dispatch_options(base_item: str, data: dict, dispatch: dict[str, object]) -> dict:
    prop = dispatch.get("property")
    if prop == "minecraft:damage":
        normalize = dispatch.get("normalize", True)
        if not isinstance(normalize, bool):
            raise GeneratorError(f"{base_item}: normalize は boolean でなければならない")
        data["model"]["normalize"] = normalize
        return data
    if prop == "minecraft:custom_model_data":
        return data
    raise GeneratorError(f"{base_item}: 未対応の property: {prop}")


def legacy_item_meta(base_item: str) -> dict[str, object]:
    meta = LEGACY_SPECIALS.get(base_item)
    if meta:
        return meta
    return {
        "parent": "item/handheld",
        "textures": {"layer0": f"item/{base_item}"},
    }


def normalize_resource_location(value: str) -> str:
    if ":" in value:
        return value
    return f"minecraft:{value}"


def build_modern_base_item_model_json(base_item: str) -> dict[str, object]:
    meta = legacy_item_meta(base_item)
    data: dict[str, object] = {
        "parent": normalize_resource_location(str(meta["parent"])),
    }
    textures = meta.get("textures")
    if isinstance(textures, dict):
        data["textures"] = {
            key: normalize_resource_location(str(value))
            for key, value in textures.items()
        }
    return data


def build_legacy_json(base_item: str, rows: list[dict[str, str]], dispatch: dict[str, object]) -> dict:
    meta = legacy_item_meta(base_item)
    data: dict[str, object] = {
        "parent": meta["parent"],
        "overrides": [],
    }
    textures = meta.get("textures")
    if textures is not None:
        data["textures"] = textures

    count = len(rows)
    overrides: list[dict[str, object]] = []
    prop = dispatch["property"]
    if prop == "minecraft:custom_model_data":
        for row in rows:
            if not (row["namespace"] and row["model_path"]):
                continue
            overrides.append(
                {
                    "predicate": {"custom_model_data": int(row["variant_id"])},
                    "model": f"{row['namespace']}:{row['model_path']}",
                }
            )
    elif prop == "minecraft:damage":
        for row in rows:
            variant_id = int(row["variant_id"])
            threshold = variant_id / (count + 1)
            model = (
                f"{row['namespace']}:{row['model_path']}"
                if row["namespace"] and row["model_path"]
                else base_item_model_ref(base_item)
            )
            overrides.append(
                {
                    "predicate": {"damaged": 0, "damage": threshold},
                    "model": model,
                }
            )
        overrides.append(
            {
                "predicate": {"damaged": 1, "damage": 0},
                "model": base_item_model_ref(base_item),
            }
        )
    else:
        raise GeneratorError(f"{base_item}: 未対応の property: {prop}")

    data["overrides"] = overrides
    return data


def merge_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for path in src.rglob("*"):
        if path.name == ".gitkeep":
            continue
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def write_zip_file(tmp: Path, zip_path: Path) -> None:
    partial = zip_path.with_suffix(".zip.partial")
    try:
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(tmp.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(tmp).as_posix())
        partial.replace(zip_path)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def prepare_tmp() -> Path:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)
    return TMP_DIR


def generate(*, write_zip: bool = True, generation: str = "modern") -> None:
    if not OPTION_PATH.exists():
        raise GeneratorError(f"option.json がない: {OPTION_PATH}")
    if not REGISTRY_PATH.exists():
        raise GeneratorError(f"registry.csv がない: {REGISTRY_PATH}")
    option = load_option(OPTION_PATH)
    dispatch_config = load_dispatch_config()
    _, rows = parse_registry(REGISTRY_PATH)
    assigned, errors = assigned_rows(rows)
    if errors:
        raise GeneratorError("\n".join(errors))

    grouped = group_rows(rows)
    namespaces = sorted({row["namespace"] for row in assigned})
    for row in assigned:
        path = model_file(row["namespace"], row["model_path"])
        if not path.is_file():
            raise GeneratorError(f"モデルがない: {path}")
    for namespace in namespaces:
        src = ns_assets_dir(namespace)
        if not src.is_dir():
            raise GeneratorError(f"NS 素材がない: {src}")

    tmp = prepare_tmp()
    pack_format = MODERN_PACK_FORMAT if generation == "modern" else LEGACY_PACK_FORMAT
    pack_meta = {
        "pack": {
            "pack_format": pack_format,
            "description": "adw resource pack",
        }
    }
    (tmp / "pack.mcmeta").write_text(
        json.dumps(pack_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if generation == "modern":
        item_output_dir = tmp / "assets" / "minecraft" / "items"
    else:
        item_output_dir = tmp / "assets" / "minecraft" / "models" / "item"
    if grouped:
        item_output_dir.mkdir(parents=True)
    for base_item, count in option.items():
        item_rows = grouped.get(base_item)
        if not item_rows:
            raise GeneratorError(f"{base_item}: registry.csv に行がない")
        if len(item_rows) != count:
            raise GeneratorError(f"{base_item}: registry.csv の行数が option.json と一致しない")
        dispatch = dispatch_config.get(base_item)
        if not isinstance(dispatch, dict):
            raise GeneratorError(f"{base_item}: item_dispatch.json の設定がない")
        dest = item_output_dir / f"{base_item}.json"
        if generation == "modern":
            data = build_items_json(base_item, item_rows, dispatch)
            data = apply_dispatch_options(base_item, data, dispatch)
        else:
            data = build_legacy_json(base_item, item_rows, dispatch)
        dest.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    for namespace in namespaces:
        merge_tree(ns_assets_dir(namespace), tmp / "assets" / namespace)
    merge_tree(BASE_PACK_DIR, tmp / "assets")
    if generation == "modern":
        modern_item_model_dir = tmp / "assets" / "minecraft" / "models" / "item"
        modern_item_model_dir.mkdir(parents=True, exist_ok=True)
        for base_item in option:
            dest = modern_item_model_dir / f"{base_item}.json"
            data = build_modern_base_item_model_json(base_item)
            dest.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    if write_zip:
        write_zip_file(tmp, ZIP_PATH)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="registry.csv から resourcepack.zip を組み立てる")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="tmp まで組み立て、zip は出さない",
    )
    parser.add_argument(
        "--generation",
        default="2",
        help="生成世代。1/legacy は -1.20、2/modern は 1.20-",
    )
    args = parser.parse_args(argv)
    generation_aliases = {
        "1": "legacy",
        "legacy": "legacy",
        "2": "modern",
        "modern": "modern",
    }
    generation = generation_aliases.get(args.generation)
    if generation is None:
        print("generation は 1/legacy または 2/modern", file=sys.stderr)
        return 1
    if not args.dry_run and ZIP_PATH.exists():
        ZIP_PATH.unlink()
    try:
        generate(write_zip=not args.dry_run, generation=generation)
    except GeneratorError as exc:
        print(str(exc), file=sys.stderr)
        if ZIP_PATH.exists():
            ZIP_PATH.unlink()
        return 1
    if args.dry_run:
        print(f"assembled {TMP_DIR}")
    else:
        print(f"wrote {ZIP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
