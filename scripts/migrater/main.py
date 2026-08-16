import argparse
import csv
import json
import sys


def parse_option_file(file_path):
    """ファイル（JSONまたは簡易YAML）を読み込んで辞書として返す"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # JSON形式の場合
    if content.startswith("{"):
        return json.loads(content)

    # 簡易YAML形式（`key: value` 行）の場合
    data = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            data[key.strip()] = int(val.strip())

    return data


def convert_to_csv(input_path, output_path):
    # オプションファイルの読み込み
    data = parse_option_file(input_path)

    headers = ["base_item", "child_id", "namespace", "model_path"]

    # CSVの出力
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for item, count in data.items():
            for child_id in range(1, count + 1):
                writer.writerow([item, child_id, "", ""])

    print(f"変換が完了しました: {input_path} -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Option (YAML/JSON) を読み込んで CSV に変換するツール"
    )

    # 引数の定義
    parser.add_argument(
        "-i",
        "--input",
        default="option.yaml",
        help="入力ファイルのパス (デフォルト: option.yaml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output.csv",
        help="出力CSVファイルのパス (デフォルト: output.csv)",
    )

    args = parser.parse_args()

    try:
        convert_to_csv(args.input, args.output)
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)
