#!/bin/sh
set -e
cd "$(dirname "$0")"

if [ -n "$1" ]; then
  TARGET_NS="$1"
else
  printf "namespace を入力してください: "
  read -r TARGET_NS
fi

if [ -z "$TARGET_NS" ]; then
  echo "namespace が空です。" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python が見つかりません。Python 3 をインストールしてください。" >&2
  exit 1
fi

"$PY" scripts/build_user_template.py "$TARGET_NS"
