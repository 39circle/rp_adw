#!/usr/bin/env python3
"""開発者向けユーザーリポジトリ雛形 zip を生成する。"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

from export_slice import select_rows
from registry import REGISTRY_PATH, SCHEMA_VERSION, parse_registry, write_registry

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "user_repo"
DIST_DIR = REPO_ROOT / "dist" / "user_templates"
TMP_DIR = REPO_ROOT / "tmp" / "user_template"


class TemplateError(Exception):
    pass


def copy_template_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        text_exts = {".md", ".txt", ".py", ".sh", ".bat", ".gitignore", ".json"}
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in text_exts or path.name == ".gitignore":
            text = path.read_text(encoding="utf-8")
            text = text.replace("__NS__", dst.name.removeprefix("rp_"))
            target.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(path, target)


def add_empty_dirs(root: Path, namespace: str) -> None:
    for rel in [
        Path("assets") / "minecraft",
        Path("assets") / namespace / "models",
        Path("assets") / namespace / "textures",
    ]:
        path = root / rel
        path.mkdir(parents=True, exist_ok=True)
        keep = path / ".gitkeep"
        keep.write_text("", encoding="utf-8")


def write_zip_from_dir(src: Path, dest: Path) -> None:
    partial = dest.with_suffix(".zip.partial")
    try:
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(src.rglob("*")):
                arcname = path.relative_to(src.parent).as_posix()
                if path.is_dir():
                    if any(path.iterdir()):
                        continue
                    zf.writestr(f"{arcname}/", "")
                else:
                    zf.write(path, arcname)
        partial.replace(dest)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def build_template(namespace: str) -> Path:
    if not REGISTRY_PATH.exists():
        raise TemplateError(f"registry.csv がない: {REGISTRY_PATH}")
    if not TEMPLATES_DIR.is_dir():
        raise TemplateError(f"テンプレートがない: {TEMPLATES_DIR}")

    version, rows = parse_registry(REGISTRY_PATH)
    if version != SCHEMA_VERSION:
        raise TemplateError(f"schema_version が不正: {version}")

    selected = select_rows(namespace, rows)
    if not selected:
        raise TemplateError(f"{namespace} の割当行がない")

    repo_name = f"rp_{namespace}"
    target_root = TMP_DIR / repo_name
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    target_root.mkdir(parents=True, exist_ok=True)

    copy_template_tree(TEMPLATES_DIR, target_root)
    add_empty_dirs(target_root, namespace)
    write_registry(target_root / "registry.csv", selected)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / f"{repo_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    write_zip_from_dir(target_root, zip_path)
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="開発者向けの個別雛形 zip を生成する")
    parser.add_argument("namespace", help="対象 namespace")
    args = parser.parse_args(argv)
    try:
        zip_path = build_template(args.namespace)
    except TemplateError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"wrote {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
