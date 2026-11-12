#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py — 把本 skill 装进各家 agent 宿主（Windows / macOS / Linux 同一份脚本）

用法:
  python scripts/install.py --list                      # 只打印支持的目标与路径，不动文件
  python scripts/install.py --target claude             # 在**当前目录**这个项目里装成原生 skill（.claude/skills/）
  python scripts/install.py --target codex --global     # 装到 ~/.agents/skills/（Codex 官方 skill 路径）
  python scripts/install.py --target agents --mode inject   # 把适配正文写进 ./AGENTS.md 的受管块
  python scripts/install.py --target all --dry-run      # 全跑一遍看看会写哪里

基准目录：项目级目标一律相对**当前工作目录**解析（在你的项目根里跑本脚本），不是 skill 仓库自己。
全局级（--global）相对用户主目录。--dest / --project 可显式覆盖。

两种安装模式（对应两种真实机制，别混）:
  skill   把整个 skill 目录按字节复制到宿主的原生 skills 根 → 正文按需加载、省上下文。
          代价：多数宿主对原生 skill 只认显式调用（Codex `$finance-daily-v5`、Gemini `/skill:...`），
          说「金融日报」不会自动触发。
  inject  把 adapters/ 里对应宿主的整篇正文写进该宿主**唯一常驻注入**的上下文文件
          （AGENTS.md / GEMINI.md / QWEN.md / CLAUDE.md），用 BEGIN/END 受管块包住，
          块外内容一律不碰。这是「触发词自动生效」在这些宿主上唯一的实现方式。
  两者可以同时装：注入负责自动触发，原生 skill 负责显式调用与版本升级。

安全约束:
  - inject 只增删自己 `<!-- BEGIN finance-daily-v5 -->` / `<!-- END finance-daily-v5 -->` 之间的内容。
  - skill 模式默认不覆盖已存在的目标目录；加 --force 时，也只覆盖内容里带本 skill 标识（name: finance-daily-v5）的目录。
  - 不跟随符号链接跑出源目录，不复制 raw/ outputs/ __pycache__ .git adapters/ maintainer/。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = ROOT / "adapters"
SKILL_NAME = "finance-daily-v5"
BLOCK_BEGIN = f"<!-- BEGIN {SKILL_NAME} -->"
BLOCK_END = f"<!-- END {SKILL_NAME} -->"

COPY_ITEMS = ["SKILL.md", "scripts", "assets", "LICENSE"]
# 装进宿主的副本只带运行时要用的脚本；维护脚本（生成/校验/安装/打包）留在仓库里，
# 否则装出去的 skill 目录里会躺着一堆指向不存在的 adapters/ maintainer/ 的脚本。
MAINTAINER_ONLY = ("build_adapters.py", "validate_skill.py", "install.py", "package_claudeai.py")
COPY_IGNORE = ("__pycache__", "*.pyc", "raw", "outputs", *MAINTAINER_ONLY)

# id: 标题 / inject 目标（项目相对路径 + 适配文件）/ skill 目标（项目级、全局级）/ 说明
HOSTS = {
    "claude": {
        "label": "Claude Code / Claude Desktop",
        "inject": ("CLAUDE.md", "CLAUDE.md"),
        "skills_project": ".claude/skills",
        "skills_global": "~/.claude/skills",
        "note": "首选 skill 模式：Claude 按 description 自动判定何时读全文，正文不常驻上下文。",
    },
    "codex": {
        "label": "OpenAI Codex CLI",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".agents/skills",
        "skills_global": "~/.agents/skills",
        "note": "Codex 的 skill 路径是 .agents/skills（没有 .codex/skills）；原生 skill 要显式 $finance-daily-v5，自动触发请用 inject。",
    },
    "agents": {
        "label": "AGENTS.md 通用系（Amp / Warp / Zed / 一切读 AGENTS.md 的 agent）",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".agents/skills",
        "skills_global": "~/.agents/skills",
        "note": "AGENTS.md 规范本身没有 skill 机制，inject 是唯一可靠通道。",
    },
    "copilot": {
        "label": "GitHub Copilot Chat / VS Code",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".github/skills",
        "skills_global": "~/.copilot/skills",
        "note": "Copilot 默认只吃 8000 字符（chat.agent.customInstructionLimit），本 skill 全文更长，需要在设置里调大。",
    },
    "gemini": {
        "label": "Gemini CLI",
        "inject": ("GEMINI.md", "GEMINI.md"),
        "skills_project": ".gemini/skills",
        "skills_global": "~/.gemini/skills",
        "note": "上下文文件不会自动执行动作（官方原文）；原生 skill 需 /skill: 显式调用。",
    },
    "qwen": {
        "label": "Qwen Code",
        "inject": ("QWEN.md", "QWEN.md"),
        "skills_project": ".qwen/skills",
        "skills_global": "~/.qwen/skills",
        "note": "QWEN.md 与 AGENTS.md 同时存在时优先 QWEN.md；改完用 /memory 重载。",
    },
    "cursor": {
        "label": "Cursor",
        "inject": (".cursor/rules/finance-daily-v5.mdc", "cursor-rules.mdc"),
        "skills_project": ".cursor/skills",
        "skills_global": None,
        "note": "inject 模式直接写成 .mdc 规则文件（不是受管块）；skill 模式更适合长期使用。",
    },
    "codebuddy": {
        "label": "Tencent CodeBuddy",
        "inject": ("CODEBUDDY.md", "AGENTS.md"),
        "skills_project": ".codebuddy/skills",
        "skills_global": "~/.codebuddy/skills",
        "note": "与 VS Code/Copilot 同源，路径由 skillfish 宿主表提供，未逐字核对官方文档。",
    },
    "opencode": {
        "label": "OpenCode",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".opencode/skills",
        "skills_global": "~/.config/opencode/skills",
        "note": "",
    },
    "trae": {
        "label": "TRAE",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".trae/skills",
        "skills_global": "~/.trae/skills",
        "note": "",
    },
    "kiro": {
        "label": "Kiro",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".kiro/skills",
        "skills_global": "~/.kiro/skills",
        "note": "",
    },
    "roo": {
        "label": "Roo Code",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".roo/skills",
        "skills_global": "~/.roo/skills",
        "note": "",
    },
    "goose": {
        "label": "Goose",
        "inject": ("AGENTS.md", "AGENTS.md"),
        "skills_project": ".goose/skills",
        "skills_global": "~/.goose/skills",
        "note": "",
    },
    "antigravity": {
        "label": "Google Antigravity",
        "inject": None,
        "skills_project": ".agent/skills",
        "skills_global": "~/.gemini/antigravity/skills",
        "note": "官方文档：antigravity/skills/ 也支持。",
    },
    "prompt": {
        "label": "纯对话宿主（GPTs / Kimi / DeepSeek / 豆包 / GLM）",
        "inject": None,
        "skills_project": None,
        "skills_global": None,
        "note": "无法脚本安装：把 adapters/system-prompt-slim.md 整篇粘进宿主系统提示词"
               "（Claude Projects / GLM 可用全文版 adapters/system-prompt.md）。",
    },
}


def info(msg: str) -> None:
    print(msg)


def fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def expand(p: str | Path) -> Path:
    return Path(str(p)).expanduser().resolve()


def read_src(host: dict, mode: str, project: Path) -> tuple[Path, str]:
    """返回 (目标文件, 要写入的正文)。"""
    if mode == "inject":
        rel, adapter = host["inject"]
        src = ADAPTERS / adapter
        if not src.is_file():
            raise SystemExit(f"缺少适配文件 {src}，先跑 python scripts/build_adapters.py")
        return (project / rel).resolve(), src.read_text(encoding="utf-8")
    raise ValueError(mode)


def cmd_list() -> int:
    info(f"{'id':<12} {'inject 目标':<34} {'skill 项目级':<22} skill 全局级")
    info("-" * 104)
    for hid, h in HOSTS.items():
        inj = h["inject"][0] if h.get("inject") else "—"
        sp = h.get("skills_project") or "—"
        sg = h.get("skills_global") or "—"
        info(f"{hid:<12} {inj:<34} {sp:<22} {sg}")
    info("\n说明：inject = 常驻注入（触发词自动生效）；skill = 复制到宿主原生 skills 目录（按需加载，多需显式调用）。")
    info("     两种模式可以共存。纯对话宿主（prompt）只能手工粘贴。")
    return 0


def apply_inject(host_id: str, host: dict, dry: bool, force: bool, project: Path) -> int:
    rel, adapter = host["inject"]
    target, content = read_src(host, "inject", project)
    if target.suffix == ".mdc":
        # Cursor 规则文件整体由生成器产出，不做受管块包裹
        if target.exists() and not force and not dry:
            if adapter_marker_missing(target):
                return fail(f"{target} 已存在且不带生成标记；确认后可加 --force 覆盖")
        if dry:
            info(f"[dry-run] 写入 {target}")
            return 0
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        info(f"[ok] inject {host_id}: {target}（{len(content)} 字符，整文件由 build_adapters.py 管理）")
        return 0

    block = f"{BLOCK_BEGIN}\n\n{content.rstrip()}\n\n{BLOCK_END}\n"
    if dry:
        info(f"[dry-run] 在 {target} 中写入/替换 {BLOCK_BEGIN} 块（{len(content)} 字符）")
        return 0
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    if BLOCK_BEGIN in existing and BLOCK_END in existing:
        pre, _, rest = existing.partition(BLOCK_BEGIN)
        _, _, post = rest.partition(BLOCK_END)
        new = pre + block.rstrip("\n") + post
        action = "替换受管块"
    elif existing.strip():
        new = existing.rstrip("\n") + "\n\n" + block
        action = "追加受管块"
    else:
        new = block
        action = "新建"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding="utf-8", newline="\n")
    info(f"[ok] inject {host_id}: {target} — {action}（{len(content)} 字符，块外内容未动）")
    return 0


def adapter_marker_missing(target: Path) -> bool:
    try:
        head = "\n".join(target.read_text(encoding="utf-8").split("\n")[:6])
    except Exception:
        return True
    return "build_adapters.py" not in head


def apply_skill(host_id: str, host: dict, use_global: bool, dest_override: str | None, dry: bool, force: bool, project: Path) -> int:
    base = dest_override or (host["skills_global"] if use_global else host["skills_project"])
    if not base:
        return fail(f"{host_id} 没有{'全局' if use_global else '项目级'} skills 路径，改用 --dest 指定或走 inject 模式")
    if dest_override or use_global:
        base_dir = expand(base)
    else:
        base_dir = (project / base).resolve()
    target = base_dir / SKILL_NAME
    if base_dir == ROOT:
        info("NOTE: 目标就在 skill 仓库自身内（自测/开发用）；正式使用请装到你的项目目录或 --global。")
    if dry:
        info(f"[dry-run] 复制 {', '.join(COPY_ITEMS)} → {target}")
        return 0
    if target.exists():
        marker_file = target / "SKILL.md"
        ours = marker_file.is_file() and f"name: {SKILL_NAME}" in marker_file.read_text(encoding="utf-8")
        if not ours:
            return fail(f"{target} 已存在但不是本 skill（SKILL.md 里没有 name: {SKILL_NAME}）— 拒绝覆盖")
        if not force:
            return fail(f"{target} 已存在；要覆盖请加 --force")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in COPY_ITEMS:
        src = ROOT / item
        if not src.exists():
            info(f"WARN: 源缺少 {item}，跳过")
            continue
        if src.is_dir():
            shutil.copytree(src, target / item, ignore=shutil.ignore_patterns(*COPY_IGNORE))
        else:
            shutil.copy2(src, target / item)
        copied.append(item)
    info(f"[ok] skill {host_id}: {target} ← {', '.join(copied)}")
    return 0


def main() -> int:
    try:  # Windows 控制台默认 GBK，中文提示会炸
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="把金融日报 skill 装进各家 agent 宿主",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="先跑 `python scripts/install.py --list` 看全部目标。",
    )
    ap.add_argument("--list", action="store_true", help="列出支持的宿主与路径")
    ap.add_argument("--target", default="", help=f"宿主 id 或 all；可选: {', '.join(HOSTS)}")
    ap.add_argument("--mode", default="auto", choices=["auto", "skill", "inject", "both"],
                    help="auto=有原生 skills 目录就装 skill，否则 inject（默认 auto）")
    ap.add_argument("--global", dest="use_global", action="store_true", help="装到用户目录（全局）而不是当前项目")
    ap.add_argument("--dest", default=None, help="自定义 skills 根目录（覆盖上两项的路径）")
    ap.add_argument("--project", default=None, help="项目根（默认当前工作目录）；inject 目标与项目级 skills 都相对它解析")
    ap.add_argument("--dry-run", action="store_true", help="只说会写哪里，不落盘")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的本 skill 目录 / 生成文件")
    a = ap.parse_args()

    if a.list or not a.target:
        return cmd_list()

    targets = list(HOSTS) if a.target == "all" else [a.target]
    for t in targets:
        if t not in HOSTS:
            return fail(f"未知宿主 {t!r}；用 --list 查看可选项")

    rc = 0
    project = expand(a.project) if a.project else Path.cwd().resolve()
    if not a.dest and not a.use_global:
        info(f"项目根 = {project}")
    # 多个宿主共用同一个落点（codex/agents → .agents/skills + AGENTS.md；copilot 也用 AGENTS.md）。
    # --target all 时只写一次，否则第二次会因“已存在且无 --force”报错。
    done: set[tuple[str, Path]] = set()
    for t in targets:
        h = HOSTS[t]
        if t == "prompt":
            info(f"[提示] {h['label']}：{h['note']}")
            continue
        can_skill = bool(a.dest or (h["skills_global"] if a.use_global else h["skills_project"]))
        can_inject = bool(h.get("inject"))
        mode = a.mode
        if mode == "auto":
            mode = "skill" if can_skill else ("inject" if can_inject else "")
        if not mode:
            rc = rc or fail(f"{t} 既没有 skills 路径也没有 inject 目标")
            continue
        if mode in ("skill", "both"):
            base = a.dest or (h["skills_global"] if a.use_global else h["skills_project"])
            base_dir = expand(base) if (a.dest or a.use_global) else (project / base).resolve()
            key = ("skill", base_dir / SKILL_NAME)
            if key in done:
                info(f"[skip] {t}: 落点与前面的宿主相同（{key[1]}），已写过")
            else:
                done.add(key)
                rc = apply_skill(t, h, a.use_global, a.dest, a.dry_run, a.force, project) or rc
        if mode in ("inject", "both"):
            if not can_inject:
                info(f"WARN: {t} 不支持 inject 模式，跳过")
                continue
            key = ("inject", (project / h["inject"][0]).resolve())
            if key in done:
                info(f"[skip] {t}: 注入目标与前面的宿主相同（{key[1].name}），已写过")
                continue
            done.add(key)
            rc = apply_inject(t, h, a.dry_run, a.force, project) or rc
        if h.get("note"):
            info(f"     ↳ {h['note']}")
    if not a.dry_run:
        info("\n完成。宿主若已在运行，重启会话或按其方式重载上下文（Qwen: /memory，Gemini: /skills reload，Claude Code: 重启）。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
