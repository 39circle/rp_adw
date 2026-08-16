"""
migrater - Minecraft Registry Manager & CSV Migrator (child_id: 1開始版)
"""

import argparse
import csv
import json
import os
import re
import sys

SCHEMA_VERSION = "1.0.0"


def parse_option_json(json_path):
    """option.json を読み込み、構文・型・値のバリデーションを行います。"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"option.json のJSON構文エラー: {e}")

    if not isinstance(data, dict):
        raise ValueError(
            "option.json のルート要素は JSON オブジェクトである必要があります。"
        )

    validated_data = {}
    valid_key_pattern = re.compile(r"^[a-z0-9_.]+$")

    for raw_key, count in data.items():
        key = raw_key.strip()
        if key.startswith("minecraft:"):
            key = key[10:]

        if not key or not valid_key_pattern.match(key):
            raise ValueError(
                f"無効な base_item キーです: '{raw_key}' (小文字英数字・ドット・アンダースコアのみ)"
            )

        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(
                f"'{key}' の個数指定が無効です: {count} (0以上の整数が必要)"
            )

        validated_data[key] = count

    return validated_data


def generate_csv(data, csv_path):
    """
    データから registry.csv を生成します。
    child_id は 1 から始まるインデックスを割り当てます (1, 2, ... count)。
    """
    headers = ["base_item", "child_id", "namespace", "model_path"]

    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"# schema_version: {SCHEMA_VERSION}\n")

        writer = csv.writer(f)
        writer.writerow(headers)

        for base_item, count in data.items():
            # 1 から count までを割り当て
            for child_id in range(1, count + 1):
                writer.writerow([base_item, child_id, "", ""])

    print(f"✅ registry.csv を正常に生成しました: {csv_path}")


def parse_registry_csv(csv_path):
    """既存の registry.csv をパースします。"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    schema_version = None
    rows = []

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    csv_content = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if "schema_version:" in stripped:
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    schema_version = parts[1].strip()
            continue
        if stripped:
            csv_content.append(line)

    reader = csv.DictReader(csv_content)
    expected_fields = ["base_item", "child_id", "namespace", "model_path"]

    if reader.fieldnames is None or any(
        field not in reader.fieldnames for field in expected_fields
    ):
        raise ValueError(
            f"CSVヘッダーが無効です。期待されるヘッダー: {', '.join(expected_fields)}"
        )

    ns_pattern = re.compile(r"^[a-z0-9_]*$")

    for idx, row in enumerate(reader, start=2):
        base_item = row["base_item"].strip()
        child_id_str = row["child_id"].strip()
        namespace = row["namespace"].strip()
        model_path = row["model_path"].strip()

        if not base_item:
            raise ValueError(f"CSV {idx} 行目: base_item が空です。")

        try:
            child_id = int(child_id_str)
            if child_id < 1:  # 1 以上の整数に修正
                raise ValueError
        except ValueError:
            raise ValueError(
                f"CSV {idx} 行目: child_id ('{child_id_str}') は1以上の整数である必要があります。"
            )

        if namespace and not ns_pattern.match(namespace):
            raise ValueError(
                f"CSV {idx} 行目: namespace ('{namespace}') は小文字英数字およびアンダースコアのみ利用可能です。"
            )

        rows.append({
            "base_item": base_item,
            "child_id": child_id,
            "namespace": namespace,
            "model_path": model_path,
        })

    return schema_version, rows


def validate_csv(csv_path, json_path=None):
    """registry.csv の整合性チェックを行います。"""
    schema_version, rows = parse_registry_csv(csv_path)

    if not schema_version:
        print("⚠️  警告: CSVに # schema_version コメントが存在しません。")
    elif schema_version != SCHEMA_VERSION:
        print(
            f"⚠️  警告: スキーマバージョンが一致しません (ファイル: {schema_version}, ツール期待値: {SCHEMA_VERSION})"
        )

    # 1. 重複チェック
    seen_ids = set()
    counts_in_csv = {}

    for row in rows:
        key = (row["base_item"], row["child_id"])
        if key in seen_ids:
            raise ValueError(
                f"重複エラー: {row['base_item']} の child_id {row['child_id']} が重複しています。"
            )
        seen_ids.add(key)

        counts_in_csv[row["base_item"]] = (
            counts_in_csv.get(row["base_item"], 0) + 1
        )

    # 2. child_id の連続性チェック (1, 2, ... N で欠損がないか)
    for base_item, count in counts_in_csv.items():
        item_child_ids = sorted(
            [r["child_id"] for r in rows if r["base_item"] == base_item]
        )
        expected_ids = list(range(1, count + 1))  # 1 開始に修正
        if item_child_ids != expected_ids:
            raise ValueError(
                f"不整合エラー: '{base_item}' の child_id 割り当てが不連続または非1開始です。現在: {item_child_ids}, 期待値: {expected_ids}"
            )

    print(
        f"✅ CSVフォーマット検証成功: {csv_path} (総レコード数: {len(rows)})"
    )

    # 3. option.json との整合性検証
    if json_path and os.path.exists(json_path):
        json_data = parse_option_json(json_path)
        mismatches = []

        for item, expected_count in json_data.items():
            actual_count = counts_in_csv.get(item, 0)
            if actual_count != expected_count:
                mismatches.append(
                    f"  - {item}: option.json={expected_count}個 vs registry.csv={actual_count}個"
                )

        for item in counts_in_csv:
            if item not in json_data:
                mismatches.append(
                    f"  - {item}: registry.csv にのみ存在 ({counts_in_csv[item]}個)"
                )

        if mismatches:
            print(
                "\n❌ option.json と registry.csv の間に差分（不一致）が検出されました:"
            )
            for m in mismatches:
                print(m)
            return False
        else:
            print("✅ option.json と registry.csv の整合性が一致しています。")

    return True


def cmd_init(args):
    if os.path.exists(args.output) and not args.force:
        print(
            f"❌ エラー: '{args.output}' は既に存在します。上書きする場合は --force を指定してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        data = parse_option_json(args.input)
        generate_csv(data, args.output)
        validate_csv(args.output, args.input)
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args):
    try:
        success = validate_csv(args.csv, args.json)
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ バリデーション失敗: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="migrater", description="Minecraft Registry Manager & CSV Migrator"
    )

    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    parser_init = subparsers.add_parser(
        "init", help="option.json から registry.csv を新規生成します"
    )
    parser_init.add_argument(
        "-i",
        "--input",
        default="option.json",
        help="入力設定ファイル (デフォルト: option.json)",
    )
    parser_init.add_argument(
        "-o",
        "--output",
        default="registry.csv",
        help="出力CSVファイル (デフォルト: registry.csv)",
    )
    parser_init.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="既存の registry.csv を強制上書きします",
    )
    parser_init.set_defaults(func=cmd_init)

    parser_val = subparsers.add_parser(
        "validate",
        help="registry.csv のフォーマットおよび option.json との整合性をチェックします",
    )
    parser_val.add_argument(
        "-c",
        "--csv",
        default="registry.csv",
        help="チェック対象のCSV (デフォルト: registry.csv)",
    )
    parser_val.add_argument(
        "-j",
        "--json",
        default="option.json",
        help="比較対照のoption.json (デフォルト: option.json)",
    )
    parser_val.set_defaults(func=cmd_validate)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
