#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_adapters.py — 从 SKILL.md 单一事实源生成各宿主适配文件（adapters/）

用法:
  python scripts/build_adapters.py            # 重新生成全部适配文件
  python scripts/build_adapters.py --check    # 只校验 adapters/ 与 SKILL.md 是否同步（CI 可用）

原则:
  1. SKILL.md 是唯一正文事实源；本脚本只做「剥离 frontmatter + 注入宿主引导头」，不改写正文语义。
  2. 生成的文件头部都带 DO NOT EDIT 标记，人工改动会在下次生成时被覆盖。
  3. 各宿主的差异只体现在引导头（安装路径、触发方式、能力说明），正文完全一致。

适配目标（国内外主流 agent 宿主）:
  AGENTS.md            OpenAI Codex CLI / 及一切读取 AGENTS.md 约定的 agent（开源通用约定）
  GEMINI.md            Gemini CLI（extensions/commands 约定读取项目上下文文件）
  QWEN.md              Qwen Code（Qwen Code CLI，fork 自 Gemini CLI，同读 QWEN.md）
  CLAUDE.md            Claude Code / Claude Desktop 项目级引用（供不想装 skills 目录的用户）
  cursor-rules.mdc     Cursor（Project Rules, .cursor/rules/，Agent 自动按描述匹配加载）
  system-prompt.md     纯对话型宿主（GPTs / Kimi / DeepSeek / GLM / 豆包 等）：整篇贴进系统提示词
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "SKILL.md"
ADAPTERS_DIR = ROOT / "adapters"

SKILL_NAME = "finance-daily-v5"
REPO_URL = "https://github.com/<你的用户名>/finance-daily-v5"

# 每个适配文件 = HEADER（宿主专属引导）+ BODY（SKILL.md 正文，无 frontmatter）
ADAPTERS = {
    "AGENTS.md": {
        "title": "AGENTS.md 适配（OpenAI Codex CLI 及一切读取 AGENTS.md 约定的 Agent）",
        "install": (
            "安装：把本仓库整体克隆到任意位置，将本文件内容放入你的项目根目录 `AGENTS.md`"
            "（或全局 `~/.codex/AGENTS.md`）。Codex CLI 与其他遵循 AGENTS.md 约定的 agent "
            "会在会话开始时自动读取。"
        ),
        "trigger": (
            "触发：会话中说「金融日报」「市场要闻」等触发词（见下方触发词一节），"
            "agent 按下方正文流程执行。"
        ),
    },
    "GEMINI.md": {
        "title": "GEMINI.md 适配（Gemini CLI）",
        "install": (
            "安装：把本文件内容放入项目根目录 `GEMINI.md`（或全局 `~/.gemini/GEMINI.md`）。"
            "Gemini CLI 每次会话自动加载该上下文文件。"
        ),
        "trigger": (
            "触发：对话中说「金融日报」「市场要闻」等触发词；Gemini 自带 google_web_search 工具，"
            "满足正文 §9 的「检索网页」能力。"
        ),
    },
    "QWEN.md": {
        "title": "QWEN.md 适配（Qwen Code）",
        "install": (
            "安装：把本文件内容放入项目根目录 `QWEN.md`（或全局 `~/.qwen/QWEN.md`）。"
            "Qwen Code 沿用 Gemini CLI 上下文约定，每次会话自动加载。"
        ),
        "trigger": (
            "触发：对话中说「金融日报」「市场要闻」等触发词。"
        ),
    },
    "CLAUDE.md": {
        "title": "CLAUDE.md 适配（Claude Code / Claude Desktop 项目引用版）",
        "install": (
            "安装：把本文件内容追加到项目根目录 `CLAUDE.md`（或 `~/.claude/CLAUDE.md` 全局）。"
            "适合不想把仓库放进 .claude/skills/ 的用户。若已作为 skill 安装，则无需本文件。"
        ),
        "trigger": (
            "触发：对话中说「金融日报」「市场要闻」等触发词，Claude 按下方正文流程执行。"
        ),
    },
    "cursor-rules.mdc": {
        "title": "Cursor Project Rules 适配",
        "install": (
            "安装：把本文件复制为 `.cursor/rules/finance-daily-v5.mdc`。"
            "Cursor Agent 根据下方 description 在匹配到金融日报类请求时自动加载本规则。"
        ),
        "trigger": (
            "触发：当用户请求生成金融日报/市场要闻类内容时自动生效，按下方正文流程执行。"
        ),
    },
    "system-prompt.md": {
        "title": "系统提示词适配（GPTs / Kimi / DeepSeek / GLM / 豆包 等纯对话型宿主）",
        "install": (
            "安装：把本文件「-- 正文开始 --」之后的全部内容，整篇粘贴到宿主的系统提示词/"
            "自定义指令中（GPTs 的 Instructions、Kimi/豆包的智能体人设、DeepSeek/GLM 的系统提示等）。"
            "这些宿主通常没有命令执行能力，按正文 §9 档位 4「只读版」运行："
            "让用户本地跑 fetch_public.py 后把 JSON 粘回来，再产出 HTML。"
        ),
        "trigger": (
            "触发：用户消息中出现「金融日报」「市场要闻」等触发词时按流程执行。"
        ),
    },
}

CURSOR_HEADER = """---
description: 生成「金融日报」金融市场要闻日报（报刊风 HTML+PNG 长图）。当用户要求金融日报、市场要闻、要闻更新、今天的金融要闻时使用。纯公开数据源（新浪/CNBC/深交所/美国财政部），多源交叉核对，禁止编造数据。
alwaysApply: false
---
"""


def read_body() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"\A---\n.*?\n---\n", text, re.S)
    if not m:
        raise SystemExit("SKILL.md frontmatter missing")
    body = text[m.end():].lstrip("\n")
    return body


def render_header(meta: dict) -> str:
    lines = [
        f"<!-- DO NOT EDIT: 本文件由 scripts/build_adapters.py 从 SKILL.md 自动生成，"
        f"改动会在下次生成时被覆盖。改正文请改 SKILL.md 后重新运行脚本。 -->",
        "",
        f"# {SKILL_NAME} · {meta['title']}",
        "",
        "## 安装与触发",
        "",
        meta["install"],
        "",
        meta["trigger"],
        "",
        "## 能力自查",
        "",
        "开始前先确认宿主具备哪些能力（执行命令 / 检索网页 / 打开网页 / 渲染 PNG），"
        "按正文 §9 的降级档位执行；缺能力不等于可以编数。",
        "",
        "---",
        "",
        "-- 正文开始（与 SKILL.md 逐字一致）--",
        "",
    ]
    return "\n".join(lines)


def render_body_only() -> str:
    """去掉正文顶部针对 skill 维护者的注释（不适配 Cursor .mdc 场景）。"""
    body = read_body()
    return re.sub(r"\A<!--.*?-->\n\n?", "", body, count=1, flags=re.S)


def build(force: bool, check: bool) -> int:
    body = read_body()
    changed = []
    for fname, meta in ADAPTERS.items():
        if fname == "cursor-rules.mdc":
            # Cursor .mdc 要求 YAML frontmatter 在文件最前
            inner = render_body_only()
            content = (
                CURSOR_HEADER
                + "\n# finance-daily-v5 · Cursor Project Rules 适配\n\n"
                + "由 scripts/build_adapters.py 从 SKILL.md 自动生成，勿手改。安装：复制为"
                + " `.cursor/rules/finance-daily-v5.mdc`，Cursor Agent 匹配到金融日报类请求时自动加载。"
                + "能力自查与降级策略见正文 §9。\n\n---\n\n"
                + inner
            )
        else:
            content = render_header(meta) + body
        out = ADAPTERS_DIR / fname
        if check:
            if not out.exists() or out.read_text(encoding="utf-8") != content:
                print(f"[drift] {fname}")
                changed.append(fname)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8", newline="\n")
            print(f"[ok] {fname}")
    if check:
        if changed:
            print(f"DRIFT: {len(changed)} 个适配文件与 SKILL.md 不同步: {', '.join(changed)}")
            return 1
        print("OK: 所有适配文件与 SKILL.md 一致")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="从 SKILL.md 生成各宿主适配文件")
    ap.add_argument("--check", action="store_true", help="只校验是否同步，不写入")
    a = ap.parse_args()
    sys.exit(build(force=True, check=a.check))


if __name__ == "__main__":
    main()
