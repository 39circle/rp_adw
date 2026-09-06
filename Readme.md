# rp_adw

二島サーバーのリソースパックを組み立てるための共有リポジトリです。完成したパックそのものではなく、管理情報と共有素材の置き場です。

## 置くもの

- `option.json` … バニラアイテムごとの枠数
- `registry.csv` … ID割り当ての管理表（人が触るのは `namespace` と `model_path` だけ）
- `modules/<user_repo>/` … 各ユーザーリポジトリの submodule
- `base_pack/` … ベースリソースパックに含める共通素材
- `scripts/` … マイグレーターと Generator

`pack.mcmeta` や `items/<item>.json` などの生成物はここへ置きません。

Python 3 が入っていれば、あとの操作はファイルを実行するだけでよい。Windows は `.bat`、macOS / Linux は `.sh` を使う。

## 枠の展開

- 未割当の `registry.csv` を作る: `migrater-init.bat` / `migrater-init.sh`
- 内容を確認する: `migrater-validate.bat` / `migrater-validate.sh`

## パックの組み立て

`generate.bat` / `generate.sh` を実行する。`base_pack/` と各 submodule の素材を `tmp/` に組み立て、`resourcepack.zip` を出す。どちらも Git 管理しない。

旧パックからモデルを移植するときは、モデル JSON 内の texture 参照に namespace を明示すること。共用するテクスチャは `base_pack/minecraft/textures/` に置き、参照は `minecraft:item/...` または `minecraft:block/...` にそろえる。モジュール側には、そのモジュール固有のテクスチャだけを残す。

## 開発者向け雛形 zip

管理部は `build-user-template.bat` / `build-user-template.sh` を実行し、対象 namespace を入れる。`dist/user_templates/rp_<ns>.zip` ができ、開発者へそのまま渡せる。

zip の中には、`registry.csv` スライス、`build_local`、`pack.mcmeta`、空の `assets/<ns>/` が入る。開発者は展開後に `build_local.bat` / `build_local.sh` を実行して `assets/minecraft/items/` を生成する。

## CI

- `main` または `dev` への PR: `registry.csv` の検証と Generator の dry-run
- `main` へのマージ: `resourcepack.zip` を成果物として保存し、GitHub Pages へ配布する

GitHub Pages は、リポジトリ設定で配信元を `GitHub Actions` にする。
