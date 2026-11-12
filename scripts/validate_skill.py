#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_skill.py — 零依赖自检：把本仓库按 Agent Skills 开放规范 + 宿主上限过一遍。

用法:
  python scripts/validate_skill.py            # 人读报告，有问题退出码 1
  python scripts/validate_skill.py --strict    # 把 WARN 也当失败
  python scripts/validate_skill.py --quiet     # 只打印 ERROR/WARN 与结论

为什么要有这个脚本（不要依赖外部校验器）:
  官方参考实现 skills-ref 既不在 PyPI 也不在 npm，离线/国内网络装不上；
  而本仓库最容易翻车的三件事恰好都能静态查出来：
    1) frontmatter 越界（宿主上传接口硬校验，多一个键就报错）
    2) 正文混进宿主专有工具名（换宿主即失效，见 SKILL.md §9 能力声明式铁律）
    3) 正文引用的脚本/模板路径不存在（或写成了相对 CWD 的路径，装到 ~/.claude/skills 后必然找不到）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "SKILL.md"
ADAPTERS_DIR = ROOT / "adapters"

# --- 规范常量（Agent Skills spec）-------------------------------------------------
NAME_MAX = 64
DESC_MIN, DESC_MAX = 1, 1024
COMPAT_MAX = 500
BODY_SOFT_MAX_LINES = 500          # 规范建议正文 < 500 行
ALLOWED_FM_KEYS = {
    "name", "description", "license", "compatibility", "metadata", "allowed-tools",
}
NAME_RE = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
GENERATED_MARKER = "build_adapters.py"

# 宿主专有工具名黑名单：出现即说明正文与宿主耦合了（维护注释里也别写，宿主同样能看到）。
HOST_TOOL_DENY = [
    "WebSearch", "WebFetch", "google_web_search", "read_url", "web_fetch",
    "mcp__", "skill(", "$finance-daily", "/skill:", "/plugin", "str_replace_editor",
]

# 各宿主对「要贴进去的那一坨文本」的实测上限（2026-11-12 逐条查官方文档；单位不同，别混用）
HOST_LIMITS = [
    # (文件, 上限字符, 上限说明)
    ("adapters/system-prompt-slim.md", 3500, "豆包 4000 token / GPTs 8000 字符 / Kimi 5000 字 — 取最紧的一档"),
    ("adapters/AGENTS.md", 32768, "Codex project_doc_max_bytes=32768（字节）"),
]
WARN_OVER = [
    ("adapters/AGENTS.md", 8000, "GitHub Copilot 默认 customInstructionLimit=8000 字符，超出需用户手动调大"),
    ("adapters/CLAUDE.md", 8000, "同上：Copilot 也读 AGENTS.md/CLAUDE.md 系文件时受 8000 字符默认上限约束"),
]

errors: list[str] = []
warnings: list[str] = []
oks: list[str] = []


def ok(msg: str) -> None:
    oks.append(msg)


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# --- 极简 YAML（只够读 skill frontmatter 的两层结构，不引入 PyYAML 依赖）------------
def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        raise ValueError("SKILL.md 缺少 frontmatter")
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("frontmatter 没有闭合的 ---")
    data: dict = {}
    cur_key = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"frontmatter 行无法解析: {raw!r}")
        key, _, val = stripped.partition(":")
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if indent == 0:
            if val == "":
                data[key] = {}
                cur_key = key
            else:
                data[key] = val
                cur_key = None
        else:
            if cur_key is None or not isinstance(data[cur_key], dict):
                raise ValueError(f"frontmatter 缩进异常: {raw!r}")
            data[cur_key][key] = val
    return {"__end_line__": end, **data}


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent Skills 规范 + 宿主上限自检")
    ap.add_argument("--strict", action="store_true", help="WARN 也算失败")
    ap.add_argument("--quiet", action="store_true", help="只输出 ERROR/WARN 与结论")
    a = ap.parse_args()

    if not SKILL_MD.is_file():
        print(f"ERROR: 找不到 {SKILL_MD}")
        return 1

    text = SKILL_MD.read_text(encoding="utf-8")
    try:
        fm = parse_frontmatter(text)
    except ValueError as e:
        print(f"ERROR: frontmatter 解析失败 — {e}")
        return 1
    end_line = fm.pop("__end_line__")
    body = "\n".join(lines_[end_line + 1:]) if (lines_ := text.split("\n")) else ""

    # 1. frontmatter 键白名单
    extra = set(fm) - ALLOWED_FM_KEYS
    if extra:
        err(f"frontmatter 含规范外键 {sorted(extra)}（claude.ai 上传接口与 skills-ref 都会拒）")
    else:
        ok(f"frontmatter 键合法: {sorted(fm)}")
    if "allowed-tools" in fm:
        warn("allowed-tools 在规范里标注 Experimental，跨宿主支持不一；不要依赖它做能力开关")

    # 2. name
    name = str(fm.get("name", ""))
    if not name:
        err("frontmatter 缺 name")
    else:
        if len(name) > NAME_MAX:
            err(f"name 长度 {len(name)} > {NAME_MAX}")
        if not NAME_RE.match(name):
            err(f"name {name!r} 不符合 ^[a-z0-9]+(-[a-z0-9]+)*$（禁止大写/下划线/连续连字符/首尾连字符）")
        # claude.ai 上传接口的额外硬约束（规范表格里没写，但会直接拒）
        for bad_word in ("anthropic", "claude"):
            if bad_word in name.lower():
                err(f"name 含保留词 {bad_word!r} —— Anthropic 上传接口会拒（官方市场会覆盖掉自家名字）")
        if re.search(r"<[^>]*>", name):
            err("name 不得含 XML 标签")
        if any(ord(c) < 0x20 or c in "\u200b\u200c\u200d\u202a\u202b\u202c" for c in name):
            err("name 含控制字符/零宽字符/bidi 覆盖符（Claude Code 会静默不加载）")
        parent = SKILL_MD.parent.name
        if name != parent:
            err(f"name {name!r} 必须等于父目录名 {parent!r}（规范要求；改名会断掉已安装用户的更新链）")
        else:
            ok(f"name = 父目录名 = {name}")

    # 3. description
    desc = str(fm.get("description", ""))
    if not (DESC_MIN <= len(desc) <= DESC_MAX):
        err(f"description 长度 {len(desc)} 不在 [{DESC_MIN},{DESC_MAX}]")
    else:
        ok(f"description {len(desc)}/{DESC_MAX} 字符")
    if "<" in desc or ">" in desc:
        # Anthropic 校验器原文报错：Description cannot contain angle brackets (< or >)
        err("description 含尖括号 —— Anthropic 上传校验直接拒；正文里描述占位符请改用「」或 <>以外的记号")
    if re.search(r"</?[A-Za-z][A-Za-z0-9]*\s*/?>", desc):
        err("description 含 XML 标签（上传接口拒绝）")
    # description 是宿主唯一的自动路由依据（Claude/Cursor 靠它决定要不要加载本 skill）
    missing_triggers = [t for t in ("金融日报", "市场要闻", "要闻更新") if t not in desc]
    if missing_triggers:
        err(f"description 缺少触发词 {missing_triggers} —— 触发词不在 description 里，宿主不会自动加载本 skill")
    else:
        ok("description 含全部主触发词（金融日报 / 市场要闻 / 要闻更新）")

    # 4. compatibility / metadata
    if "compatibility" in fm:
        n = len(str(fm["compatibility"]))
        if n > COMPAT_MAX:
            err(f"compatibility {n} > {COMPAT_MAX}")
        else:
            ok(f"compatibility {n}/{COMPAT_MAX} 字符（能力要求已声明）")
    meta = fm.get("metadata", {})
    if not isinstance(meta, dict):
        err("metadata 必须是 string→string 映射")
    else:
        bad = [k for k, v in meta.items() if not isinstance(v, str)]
        if bad:
            err(f"metadata 存在非字符串值: {bad}")
        ver = meta.get("version")
        if ver is None:
            warn("metadata.version 缺失：发布时建议写并加引号（version: \"5.0.0\"）")
        else:
            raw = re.search(r"^\s*version:\s*(.+?)\s*$", text, re.M)
            if raw and raw.group(1)[:1] not in "\"'":
                warn(f'metadata.version 未加引号（{ver}）：形如 1.0 的值会被 YAML 解析成 float，建议 version: "{ver}"')
            else:
                ok(f"metadata.version = {ver}")

    # 5. 正文规模
    body_lines = [ln for ln in body.split("\n") if ln.strip()]
    if len(body_lines) > BODY_SOFT_MAX_LINES:
        warn(f"正文 {len(body_lines)} 行 > 规范建议 {BODY_SOFT_MAX_LINES} 行（考虑把长表拆到 references/）")
    else:
        ok(f"正文 {len(body_lines)} 行 / {len(body)} 字符（< {BODY_SOFT_MAX_LINES} 行）")

    # 6. 宿主专有工具名
    hits = [t for t in HOST_TOOL_DENY if t in body]
    if hits:
        locs = []
        for i, ln in enumerate(body.split("\n"), start=end_line + 2):
            for t in hits:
                if t in ln:
                    locs.append(f"L{i}:{t}")
        err(f"正文出现宿主专有工具名（换宿主即失效）：{', '.join(sorted(set(locs)))[:400]}")
    else:
        ok("正文无宿主专有工具名（能力声明式）")

    # 7. 正文引用的本地文件必须存在；且不得出现裸相对调用（宿主 CWD 不是 skill 目录）
    normalized = body.replace("<SKILL_DIR>/", "").replace("`./", "`")
    refs = set(re.findall(r"(?:scripts|assets|references)/[A-Za-z0-9_.\-/\u4e00-\u9fff]+", normalized))
    missing = sorted(r for r in refs if not (ROOT / r).exists())
    if missing:
        err(f"正文引用了不存在的文件: {missing}")
    elif refs:
        ok(f"正文引用的 {len(refs)} 个本地文件全部存在: {sorted(refs)}")
    for i, ln in enumerate(body.split("\n"), start=end_line + 2):
        if re.search(r"^\s*python scripts/", ln) or re.search(r"^\s*python3 scripts/", ln):
            err(f"L{i} 命令用了相对 CWD 的脚本路径，装到宿主 skills 目录后必然失败：应写 <SKILL_DIR>/scripts/...")
    render_py = ROOT / "scripts" / "render.py"
    if render_py.is_file() and ('file:///" +' in render_py.read_text(encoding="utf-8")):
        err("scripts/render.py 又用 \"file:///\" + 拼路径了：相对路径会解析到根目录，必须用 Path.resolve().as_uri()")

    # 8. 适配文件：marker + 宿主上限
    if ADAPTERS_DIR.is_dir():
        files = sorted(p for p in ADAPTERS_DIR.iterdir() if p.is_file())
        if not files:
            err("adapters/ 为空，运行 python scripts/build_adapters.py 生成")
        for p in files:
            content = p.read_text(encoding="utf-8")
            rel = f"adapters/{p.name}"
            head = "\n".join(content.split("\n")[:6])
            if GENERATED_MARKER not in head:
                err(f"{rel} 前 6 行缺少生成器标记（{GENERATED_MARKER}），会被误当手写文件改动")
            if "\r\n" in content:
                err(f"{rel} 含 CRLF：build_adapters.py 必须写 newline='\\n'，否则跨平台漂移")
            nbytes = len(content.encode("utf-8"))
            if nbytes > 32768:
                err(f"{rel} {nbytes} 字节 > Codex project_doc_max_bytes 默认 32768")
            for f_, cap, note in HOST_LIMITS:
                if f_ == rel and len(content) > cap:
                    err(f"{rel} {len(content)} 字符 > 上限 {cap}（{note}）")
            for f_, cap, note in WARN_OVER:
                if f_ == rel and len(content) > cap:
                    warn(f"{rel} {len(content)} 字符 > {cap}（{note}）")
        ok(f"adapters/ {len(files)} 个文件 marker/换行符/上限检查通过")
    else:
        warn("没有 adapters/ 目录（若刻意只发原生 skill，可忽略）")

    # 8b. install.py 里引用的适配文件名必须真实存在（两处 HOSTS 表容易各改各的）
    install_py = ROOT / "scripts" / "install.py"
    if install_py.is_file():
        src_text = install_py.read_text(encoding="utf-8")
        declared = set(re.findall(r'"inject": \("[^"]+", "([^"]+)"\)', src_text))
        missing_ad = sorted(d for d in declared if not (ADAPTERS_DIR / d).is_file())
        if missing_ad:
            err(f"install.py HOSTS 引用了不存在的适配文件: {missing_ad} —— 先跑 build_adapters.py 或改表")
        elif declared:
            ok(f"install.py HOSTS 的 {len(declared)} 个注入源文件均存在")

    # 8c. Claude Code 插件市场清单（若提供）
    mp = ROOT / ".claude-plugin" / "marketplace.json"
    if mp.is_file():
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
            for key in ("name", "owner", "plugins"):
                if key not in data:
                    err(f".claude-plugin/marketplace.json 缺 {key}")
            if not str(data.get("owner", {}).get("name", "")).strip():
                err("marketplace.json owner.name 不能为空")
            for e in data.get("plugins", []):
                if not e.get("name") or not e.get("source"):
                    err(f"marketplace.json 插件条目缺 name/source: {e}")
                src = str(e.get("source", ""))
                if src.startswith("./"):
                    tgt = ROOT / src[2:] if len(src) > 2 else ROOT
                    if not tgt.exists():
                        err(f"marketplace.json source {src!r} 指向的路径不存在")
            if name and data.get("plugins") and all(p.get("name") != name for p in data["plugins"]):
                warn(f"marketplace.json 插件名与 skill name {name!r} 不一致（可以，但命令会变成 /<plugin>:<skill>）")
            ok(".claude-plugin/marketplace.json 结构合法")
        except Exception as e:
            err(f".claude-plugin/marketplace.json 解析失败: {e}")

    # 9. 运行产物不得混进版本库
    for junk in ("raw", "outputs", "__pycache__"):
        if (ROOT / junk).exists():
            warn(f"{junk}/ 存在于工作区（确认已被 .gitignore 排除，不要提交）")

    if not a.quiet:
        for m in oks:
            print(f"  \u2713 {m}")
    for m in warnings:
        print(f"  WARN {m}")
    for m in errors:
        print(f"  ERROR {m}")
    if errors or (a.strict and warnings):
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: 规范自检通过（{len(warnings)} warning）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
