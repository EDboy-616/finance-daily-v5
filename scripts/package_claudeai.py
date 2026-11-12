#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
package_claudeai.py — 打出能直接上传 claude.ai / 提交 Skills API 的 zip。

用法:
  python scripts/package_claudeai.py                # → dist/finance-daily-v5-<version>.zip
  python scripts/package_claudeai.py --dry-run      # 只列会进包的文件与大小
  python scripts/package_claudeai.py --out D:\\x.zip

为什么需要它（这一步手工很容易错）:
  claude.ai 的上传接口要求 **压缩包根就是 skill 文件夹本身**：
      finance-daily-v5/SKILL.md
      finance-daily-v5/scripts/...
      finance-daily-v5/assets/...
  把 SKILL.md 直接压在 zip 根、或多套一层目录，导入都会失败。
  包内文件夹名必须与 frontmatter 的 name 一致（否则报 folder name doesn't match）。

打包前先跑 validate_skill.py：不合法就别浪费一次上传额度。
适配层（adapters/）、维护文件（maintainer/ HANDOFF.md README.md）、Claude Code 插件清单
（.claude-plugin/）与 git/CI 目录都不进包 —— claude.ai 只认 skill 本体。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "SKILL.md"

INCLUDE_TOP = ["SKILL.md", "LICENSE"]
INCLUDE_DIRS = ["scripts", "assets"]
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
# 维护者脚本不进上传包：claude.ai 的 skill 只需要「取数 + 渲染」两个运行时脚本。
# build_adapters / validate_skill / install / package_claudeai 只在本仓库维护时用。
MAINTAINER_ONLY = {"build_adapters.py", "validate_skill.py", "install.py", "package_claudeai.py"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".zip")


def skill_name() -> str:
    m = re.search(r"^name:\s*(\S+)\s*$", SKILL_MD.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("SKILL.md 里找不到 name: —— 无法确定压缩包内的文件夹名")
    return m.group(1)


def version() -> str:
    m = re.search(r'^\s*version:\s*"?([\w.\-]+)"?\s*$', SKILL_MD.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "0.0.0"


def collect(base: Path) -> list[Path]:
    """返回要进包的绝对路径（文件）。"""
    out: list[Path] = []
    for top in INCLUDE_TOP:
        p = ROOT / top
        if p.is_file():
            out.append(p)
        else:
            print(f"WARN: 缺少 {top}，跳过")
    for d in INCLUDE_DIRS:
        p = ROOT / d
        if not p.is_dir():
            print(f"WARN: 缺少目录 {d}/，跳过")
            continue
        for f in sorted(p.rglob("*")):
            if not f.is_file():
                continue
            if any(part in EXCLUDE_NAMES for part in f.parts):
                continue
            if f.suffix in EXCLUDE_SUFFIX or f.name in EXCLUDE_NAMES:
                continue
            if f.name in MAINTAINER_ONLY:
                continue
            out.append(f)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="打 claude.ai 可上传的 skill zip")
    ap.add_argument("--out", default=None, help="输出 zip 路径（默认 dist/<name>-<version>.zip）")
    ap.add_argument("--dry-run", action="store_true", help="只列文件，不落盘")
    ap.add_argument("--no-validate", action="store_true", help="跳过 validate_skill.py（不推荐）")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    name = skill_name()
    ver = version()
    out_path = Path(a.out).expanduser().resolve() if a.out else (ROOT / "dist" / f"{name}-{ver}.zip")

    if not a.no_validate and not a.dry_run:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_skill.py"), "--quiet"])
        if r.returncode != 0:
            print("ERROR: validate_skill.py 未通过 —— 先修掉再打包（急用可加 --no-validate）", file=sys.stderr)
            return 1

    files = collect(ROOT)
    total = sum(f.stat().st_size for f in files)
    print(f"skill name = {name}  version = {ver}")
    print(f"压缩包结构（根 = {name}/）:")
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        print(f"  {name}/{rel:<46} {f.stat().st_size:>8} B")
    print(f"合计 {len(files)} 个文件 / {total} 字节（未压缩）")

    if a.dry_run:
        print("\n--dry-run：未写文件")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=f"{name}/{f.relative_to(ROOT).as_posix()}")
    print(f"\n[ok] 已写出 {out_path}（{out_path.stat().st_size} 字节）")
    print("导入：claude.ai → Settings → Capabilities → Skills → Upload a skill；"
          "或 Claude API Skills 接口。上传前确认宿主已开 Code execution 与 File search。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
