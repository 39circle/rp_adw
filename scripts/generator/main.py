"""
generator - Minecraft Custom Model Data Resourcepack Generator
(1.20.x 旧仕様 & 1.21.4+ 新仕様 バージョン別分割出力版)
"""

import argparse
import csv
import json
import os
import shutil
import sys

# pack_format 定義
PACK_FORMAT_1_20 = 15  # 1.20.1
PACK_FORMAT_1_21 = 53  # 1.21.4


def parse_registry_csv(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    items = []
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("#")]

    reader = csv.DictReader(lines)
    for row in reader:
        base_item = row["base_item"].strip()
        child_id = int(row["child_id"].strip())
        namespace = row["namespace"].strip()
        model_path = row["model_path"].strip()

        if namespace and model_path:
            items.append({
                "base_item": base_item,
                "child_id": child_id,
                "namespace": namespace,
                "model_path": model_path,
            })

    return items


def copy_custom_assets(assets_dir, target_assets_dir):
    """クリエイター領域 (assets/<NS>/) のコピー"""
    if os.path.exists(assets_dir):
        for ns in os.listdir(assets_dir):
            src_ns_dir = os.path.join(assets_dir, ns)
            if os.path.isdir(src_ns_dir) and ns != "minecraft":
                dst_ns_dir = os.path.join(target_assets_dir, ns)
                if os.path.exists(dst_ns_dir):
                    shutil.rmtree(dst_ns_dir)
                shutil.copytree(src_ns_dir, dst_ns_dir)


def build_1_20_pack(grouped_items, output_dir, assets_dir):
    """1.20.x 以前向けパッケージ生成 (models/item/<item>.json + overrides)"""
    pack_dir = os.path.join(output_dir, "1.20")
    target_assets_dir = os.path.join(pack_dir, "assets")

    # pack.mcmeta
    os.makedirs(pack_dir, exist_ok=True)
    with open(
        os.path.join(pack_dir, "pack.mcmeta"), "w", encoding="utf-8"
    ) as f:
        json.dump(
            {
                "pack": {
                    "pack_format": PACK_FORMAT_1_20,
                    "description": "Resource Pack for 1.20.x",
                }
            },
            f,
            indent=2,
        )

    copy_custom_assets(assets_dir, target_assets_dir)

    # models/item/<base_item>.json
    models_dir = os.path.join(target_assets_dir, "minecraft", "models", "item")
    os.makedirs(models_dir, exist_ok=True)

    for base_item, child_list in grouped_items.items():
        #【ここを追加】そのアイテムに割り当てられている最大個数 (max_count) を自動取得
        max_count = max(child["child_id"] for child in child_list)

        # 1.20 向け overrides 生成ロジック
        overrides = [
            {
                "predicate": {"damage": 0.0},
                "model": f"minecraft:item/{base_item}",
            }
        ]
        for child in sorted(child_list, key=lambda x: x["child_id"]):
            # child_id (例: 1, 2...) を最大個数 (例: 28) で割って割合を計算
            damage_rate = round(child["child_id"] / max_count, 6)

            overrides.append({
                "predicate": {
                    "custom_model_data": child["child_id"],
                    "damage": damage_rate,  # 例: 1/28 = 0.035714
                },
                "model": f"{child['namespace']}:{child['model_path']}",
            })

        base_item_json = {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/{base_item}"},
            "overrides": overrides,
        }

        with open(
            os.path.join(models_dir, f"{base_item}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(base_item_json, f, indent=2)


def build_1_21_pack(grouped_items, output_dir, assets_dir):
    """1.21.4+ 向けパッケージ生成 (items/<item>.json + select 構造)"""
    pack_dir = os.path.join(output_dir, "1.21")
    target_assets_dir = os.path.join(pack_dir, "assets")

    # pack.mcmeta
    os.makedirs(pack_dir, exist_ok=True)
    with open(
        os.path.join(pack_dir, "pack.mcmeta"), "w", encoding="utf-8"
    ) as f:
        json.dump(
            {
                "pack": {
                    "pack_format": PACK_FORMAT_1_21,
                    "description": "Resource Pack for 1.21.4+",
                }
            },
            f,
            indent=2,
        )

    copy_custom_assets(assets_dir, target_assets_dir)

    # items/<base_item>.json
    items_dir = os.path.join(target_assets_dir, "minecraft", "items")
    os.makedirs(items_dir, exist_ok=True)

    for base_item, child_list in grouped_items.items():
        cases = [
            {
                "when": child["child_id"],
                "model": {
                    "type": "minecraft:model",
                    "model": f"{child['namespace']}:{child['model_path']}",
                },
            }
            for child in sorted(child_list, key=lambda x: x["child_id"])
        ]

        base_item_json = {
            "model": {
                "type": "minecraft:select",
                "property": "minecraft:custom_model_data",
                "cases": cases,
                "fallback": {
                    "type": "minecraft:model",
                    "model": f"minecraft:item/{base_item}",
                },
            }
        }

        with open(
            os.path.join(items_dir, f"{base_item}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(base_item_json, f, indent=2)


def build_resourcepack_dir(
    csv_path="registry.csv", assets_dir="assets", output_dir="dist"
):
    items = parse_registry_csv(csv_path)
    if not items:
        print("⚠️ 有効なモデル指定（namespace / model_path）が存在しません。")
        return

    grouped_items = {}
    for item in items:
        grouped_items.setdefault(item["base_item"], []).append(item)

    # 各バージョンのパックをビルド
    build_1_20_pack(grouped_items, output_dir, assets_dir)
    build_1_21_pack(grouped_items, output_dir, assets_dir)

    print(f"✅ 生成完了: {output_dir}/")
    print(f"  ├─ 1.20/  (1.20.x 以前向け)")
    print(f"  └─ 1.21/  (1.21.4+ 向け)")


def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Resourcepack Generator (Multi-Version Output)"
    )
    parser.add_argument(
        "-c",
        "--csv",
        default="registry.csv",
        help="registry.csv のパス (デフォルト: registry.csv)",
    )
    parser.add_argument(
        "-a",
        "--assets",
        default="assets",
        help="入力 assets ディレクトリ (デフォルト: assets)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="dist",
        help="出力ディレクトリ (デフォルト: dist)",
    )

    args = parser.parse_args()

    try:
        build_resourcepack_dir(args.csv, args.assets, args.output)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
