"""
generator - Minecraft Custom Model Data Resourcepack Generator
(仕様書 3 準拠)
"""

import argparse
import csv
import json
import os
import shutil
import sys
import zipfile

RESOURCE_PACK_FORMAT = 15  # Minecraft 1.20 向け (必要に応じて変更可能)


def parse_registry_csv(csv_path):
    """registry.csv を読み込み、有効なデータ行のみを取り出します。"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    items = []
    with open(csv_path, "r", encoding="utf-8") as f:
        # # コメント行をスキップ
        lines = [line for line in f if not line.strip().startswith("#")]

    reader = csv.DictReader(lines)
    for row in reader:
        base_item = row["base_item"].strip()
        child_id = int(row["child_id"].strip())
        namespace = row["namespace"].strip()
        model_path = row["model_path"].strip()

        # namespace と model_path が埋まっているデータのみを生成対象とする
        if namespace and model_path:
            items.append({
                "base_item": base_item,
                "child_id": child_id,
                "namespace": namespace,
                "model_path": model_path,
            })

    return items


def build_resourcepack(
    csv_path="registry.csv",
    assets_dir="assets",
    output_zip="resourcepack.zip",
    build_dir="build_pack",
):
    """リソースパック構造を構築し、ZIPに圧縮します。"""
    items = parse_registry_csv(csv_path)
    if not items:
        print("⚠️ 有効なモデル指定（namespace / model_path）が存在しません。")
        return

    # クリーンな作業用ディレクトリを作成
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    # 1. pack.mcmeta の生成
    mcmeta_data = {
        "pack": {
            "pack_format": RESOURCE_PACK_FORMAT,
            "description": "Generated Custom Model Data Pack",
        }
    }
    with open(
        os.path.join(build_dir, "pack.mcmeta"), "w", encoding="utf-8"
    ) as f:
        json.dump(mcmeta_data, f, indent=2)

    # 2. クリエイター領域 (assets/<NS>/) のコピー
    target_assets_dir = os.path.join(build_dir, "assets")
    os.makedirs(target_assets_dir, exist_ok=True)

    if os.path.exists(assets_dir):
        for ns in os.listdir(assets_dir):
            src_ns_dir = os.path.join(assets_dir, ns)
            # minecraft フォルダ以外を対象にコピー
            if os.path.isdir(src_ns_dir) and ns != "minecraft":
                dst_ns_dir = os.path.join(target_assets_dir, ns)
                shutil.copytree(src_ns_dir, dst_ns_dir)

    # 3. base_item ごとに overrides JSON を自動生成
    grouped_items = {}
    for item in items:
        grouped_items.setdefault(item["base_item"], []).append(item)

    minecraft_item_models_dir = os.path.join(
        target_assets_dir, "minecraft", "models", "item"
    )
    os.makedirs(minecraft_item_models_dir, exist_ok=True)

    for base_item, child_list in grouped_items.items():
        overrides = []
        for child in sorted(child_list, key=lambda x: x["child_id"]):
            overrides.append({
                "predicate": {"custom_model_data": child["child_id"]},
                "model": f"{child['namespace']}:{child['model_path']}",
            })

        base_item_json = {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/{base_item}"},
            "overrides": overrides,
        }

        output_json_path = os.path.join(
            minecraft_item_models_dir, f"{base_item}.json"
        )
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(base_item_json, f, indent=2)

    # 4. ZIP へ圧縮
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(build_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, build_dir)
                zipf.write(file_path, arcname)

    # 作業用ディレクトリの削除
    shutil.rmtree(build_dir)
    print(f"✅ リソースパックの生成が完了しました: {output_zip}")


def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Resourcepack Generator"
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
        default="resourcepack.zip",
        help="出力 ZIP パス (デフォルト: resourcepack.zip)",
    )

    args = parser.parse_args()

    try:
        build_resourcepack(args.csv, args.assets, args.output)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
    