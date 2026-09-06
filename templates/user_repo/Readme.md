# rp___NS__

このリポジトリは `__NS__` のユーザーリポジトリ雛形です。

## 使い方

1. `assets/__NS__/` 配下へモデルとテクスチャを置く
2. `build_local.bat` または `build_local.sh` を実行する
3. `assets/minecraft/items/` に生成された JSON をゲーム内確認に使う

## 注意

- `registry.csv` は管理部から渡されたスライスです
- `assets/minecraft/items/` は生成物です
- モデル移植時は texture 参照へ namespace を明示してください
- 共用するテクスチャは共有側で管理し、このリポジトリには固有テクスチャだけを置いてください
