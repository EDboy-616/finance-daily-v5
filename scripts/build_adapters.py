#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_adapters.py — 从 SKILL.md 单一事实源生成各宿主适配文件（adapters/）

用法:
  python scripts/build_adapters.py            # 重新生成全部适配文件
  python scripts/build_adapters.py --check    # 只校验是否与源文件同步（CI 用，漂移退出码 1）

原则:
  1. SKILL.md 是唯一**全文**正文事实源；本脚本只做「剥离 frontmatter + 注入宿主引导头」，不改写正文语义。
  2. 唯一的人工摘编是 maintainer/prompt-slim.src.md（给字数受限的对话宿主）。
     它必须通过「原子覆盖检查」：SKILL.md 里的颜色令牌与铁律关键短语必须在摘编里原样存在，
     否则视为漂移 → 本脚本退出码 1。这样摘编就不会悄悄落后于正文。
  3. 生成文件头部都带 DO NOT EDIT 标记 + 源版本号；人工改动会在下次生成时被覆盖。
  4. 宿主差异只体现在引导头（安装路径、触发方式、字数上限、已知坑），正文逐字一致。
  5. 一律写 newline="\n"，避免 Windows 上生成 CRLF 造成跨平台漂移。

适配目标（2026-11-12 逐宿主查官方文档后确认的机制）:
  AGENTS.md                OpenAI Codex CLI / GitHub Copilot / Amp / 及一切读 AGENTS.md 的 agent
                           （AGENTS.md 规范里没有 skill 机制 → 整篇注入是触发词自动生效的唯一途径）
  GEMINI.md                Gemini CLI 上下文文件（context.fileName 可改；不会自动执行，只提供背景）
  QWEN.md                  Qwen Code（与 AGENTS.md 同时存在时 QWEN.md 优先）
  CLAUDE.md                Claude Code / Agent SDK 项目级兜底（首选仍是 .claude/skills/<name>/SKILL.md）
  cursor-rules.mdc         Cursor Project Rules（alwaysApply:false + description 作路由键）
  system-prompt.md         纯对话宿主全文版：Claude Projects / GLM 智能体（无公开字数上限）
  system-prompt-slim.md    纯对话宿主精简版：GPTs 8000 字符 / Kimi 5000 字 / DeepSeek 8000 字符 / 豆包 4000 token
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "SKILL.md"
SLIM_SRC = ROOT / "maintainer" / "prompt-slim.src.md"
REPO_FILE = ROOT / "maintainer" / "repo.txt"
ADAPTERS_DIR = ROOT / "adapters"

# Windows 控制台默认 GBK/cp1252，中文与 ✓ 直接抛 UnicodeEncodeError（CI 上真炸过）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_NAME = "finance-daily-v5"

# 「整篇 NNNN 字符」的占位符：整篇拼完才知道真实长度，先占位再回填（等长替换，不引入漂移）
TOTAL_LEN_SLOT = "####"


def fill_total_len(content: str) -> str:
    """把 TOTAL_LEN_SLOT 换成整篇最终字符数。

    槽位字符数与真实位数通常不同（4 位占位 vs 5 位数字），替换后总长会变，
    所以迭代到不动点：n 稳定时，填进去的数字就等于整篇真实长度。
    """
    n = len(content)
    for _ in range(8):
        filled = content.replace(TOTAL_LEN_SLOT, str(n))
        if len(filled) == n:
            return filled
        n = len(filled)
    return content.replace(TOTAL_LEN_SLOT, str(n))


def detect_repo_slug() -> str:
    """仓库 slug 只从 maintainer/repo.txt 读。

    曾经这里读 `git remote get-url origin`，后果是生成物依赖运行环境：
    本地还没加 remote 时生成一版、CI checkout 后又有 remote 生成另一版，
    --check 在 CI 里必然报「7 个文件全部漂移」。生成物必须可复现，
    所以唯一来源是签入仓库的 repo.txt（环境变量仅供临时覆盖）。
    """
    env = os.environ.get("FINANCE_DAILY_REPO", "").strip()
    if env:
        return env.split("github.com/")[-1].removesuffix(".git").strip("/")
    if REPO_FILE.is_file():
        line = REPO_FILE.read_text(encoding="utf-8").strip().splitlines()
        return line[0].strip() if line else ""
    return ""


def read_skill() -> tuple[str, str, str]:
    """返回 (version, body, frontmatter_text)。"""
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit("SKILL.md frontmatter missing")
    fm_text = m.group(1)
    vm = re.search(r"^\s{2}version:\s*\"?([^\"\n]+)\"?\s*$", fm_text, re.M)
    version = vm.group(1).strip() if vm else "0.0.0"
    body = text[m.end():].lstrip("\n")
    return version, body, fm_text


def read_body_without_maintainer_note() -> str:
    """去掉正文顶部那段「给 skill 维护者看」的注释（宿主页面无用，且 Cursor .mdc 不便嵌注释）。"""
    _, body, _ = read_skill()
    return re.sub(r"\A<!--.*?-->\n\n?", "", body, count=1, flags=re.S)


# --- 原子覆盖检查：摘编不得落后于正文 ----------------------------------------------
MUST_KEEP_PHRASES = [
    "待核", "禁止编造", "数据说明", "红涨绿跌", "双交付", "盘中", "收盘", "≥2",
    "T-1", "新华社", "证券时报", "东方财富", "美联储", "CNBC", "深交所", "AP News",
    "top5", "WATCH", "汇率", "成交额", "机构观点", "ticker", "dateline",
]


def slim_coverage_check(slim: str, body: str) -> list[str]:
    """返回缺失项列表（空 = 通过）。"""
    missing: list[str] = []
    low = slim.lower()
    for hexc in sorted(set(re.findall(r"#[0-9a-fA-F]{6}", body))):
        if hexc.lower() not in low and hexc not in slim:
            missing.append(f"颜色令牌 {hexc}")
    for phrase in MUST_KEEP_PHRASES:
        if phrase.lower() not in low:
            missing.append(f"关键短语「{phrase}」")
    return missing


def marker(version: str, src: str) -> str:
    return (
        f"<!-- DO NOT EDIT · 由 scripts/build_adapters.py 从 {src} v{version} 自动生成。"
        f"改内容请改源文件后重跑该脚本；--check 会抓出漂移。 -->"
    )


def install_lines(slug: str, native_dir: str | None, inject_path: str | None) -> list[str]:
    lines: list[str] = []
    if inject_path:
        lines.append(f"1. **注入式（触发词自动生效的唯一途径）**：把本文件整篇放到 `{inject_path}`。")
    if native_dir:
        lines.append(
            f"2. **原生 skills（按需加载，省上下文）**：把整个仓库复制为 `{native_dir}/{SKILL_NAME}/`，"
            f"由宿主按 description 自动加载或按各家语法显式调用。"
        )
    if slug:
        lines.append(f"3. **通用安装器**：`npx skills add {slug}`，GitHub CLI 也可 `gh skill install {slug}`（v2.90+，装前可 `gh skill preview` 审阅）；或 `python scripts/install.py --list` 看全部目标。")
    return lines


# 每个适配文件 = HEADER（宿主专属引导）+ BODY（SKILL.md 正文，逐字一致）
ADAPTERS = {
    "AGENTS.md": {
        "title": "AGENTS.md 适配（OpenAI Codex CLI / GitHub Copilot / 一切读 AGENTS.md 的 Agent）",
        "inject": "AGENTS.md（仓库根）或 ~/.codex/AGENTS.md",
        "native": "~/.agents/skills",
        "trigger": (
            "触发：会话里说「金融日报」「市场要闻」等触发词（见下方正文触发词一节）。"
            "注意 Codex 对原生 skill 只认显式 `$finance-daily-v5`，不会按关键词自己跑流程 —— "
            "所以想让触发词生效，必须走「注入式」。"
        ),
        "notes": [
            "AGENTS.md 规范本身没有 skill 机制，也没有 `## Skills` 段的官方定义 —— 整篇注入是当前唯一可靠的通道。",
            "Codex 官方上限 `project_doc_max_bytes = 32768`（可在 config.toml 调）；且**全局 ~/.codex/AGENTS.md 与仓库 AGENTS.md 同时存在时只用第一个命中的**，别两处都放。",
            "GitHub Copilot Chat 默认只吃 8000 字符（`chat.agent.customInstructionLimit`），本文件超出的部分需要在 VS Code 设置里调大。",
        ],
    },
    "GEMINI.md": {
        "title": "GEMINI.md 适配（Gemini CLI）",
        "inject": "GEMINI.md（项目根）或 ~/.gemini/GEMINI.md",
        "native": "~/.gemini/skills",
        "trigger": (
            "触发：对话里说「金融日报」「市场要闻」等触发词。Gemini CLI 自带联网检索工具，"
            "满足正文 §9 的「检索网页」能力；官方文档明写上下文文件不会自动执行动作，"
            "所以要把正文放进来才谈得上按流程走。"
        ),
        "notes": [
            "文件名可在 `.gemini/settings.json` 的 `context.fileName` 改；扩展包用 `gemini-extension.json` + `contextFileName`。",
            "原生 skill 需要显式 `/skill:finance-daily-v5` 调用；关键词自动路由只能靠注入式。",
        ],
    },
    "QWEN.md": {
        "title": "QWEN.md 适配（Qwen Code）",
        "inject": "QWEN.md（项目根）或 ~/.qwen/QWEN.md",
        "native": "~/.qwen/skills",
        "trigger": "触发：对话里说「金融日报」「市场要闻」等触发词，Qwen Code 按下方正文流程执行。",
        "notes": [
            "Qwen Code 同时存在 QWEN.md 与 AGENTS.md 时**优先读 QWEN.md**，所以本文件比 AGENTS.md 更可靠。",
            "上下文文件带校验和缓存，改完用 `/memory` 重载；`.qwen/rules/**/*.md` 是它更强的条件加载机制（按文件路径命中）。",
        ],
    },
    "CLAUDE.md": {
        "title": "CLAUDE.md 适配（Claude Code / Agent SDK 项目级兜底）",
        "inject": "CLAUDE.md（项目根）或 ~/.claude/CLAUDE.md",
        "native": ".claude/skills",
        "trigger": "触发：对话里说「金融日报」「市场要闻」等触发词。",
        "notes": [
            "**Claude Code 的首选不是本文件**：把仓库复制成 `.claude/skills/finance-daily-v5/`，"
            "Claude 会按 SKILL.md 的 description 自动判定何时读全文，正文不常驻上下文。本文件只给不想建 skills 目录的场景兜底。",
            "Agent SDK 建议 CLAUDE.md 保持在 10k tokens 内（本文件约 5k tokens，安全）。",
        ],
    },
    "cursor-rules.mdc": {
        "title": "Cursor Project Rules 适配",
        "inject": ".cursor/rules/finance-daily-v5.mdc",
        "native": ".cursor/skills",
        "trigger": "触发：用户请求金融日报 / 市场要闻类内容时由 Agent 按 description 匹配加载。",
        "mdc_frontmatter": True,
        "notes": [
            "MDC 的 `description` 就是路由键，已把触发词写全；`alwaysApply: false` = Agent requested（按需加载，别设 true，会每轮吃掉 9k 字符）。",
            "Cursor 官方建议规则写短（单个 .mdc 上限 1MB，超 500 行建议拆分）。要长期用 Cursor，更合身的做法是装成原生 skill：`.cursor/skills/finance-daily-v5/SKILL.md`，本规则退化成一条索引。",
        ],
    },
    "system-prompt.md": {
        "title": "系统提示词全文版（Claude Projects / GLM 智能体 等无公开字数上限的宿主）",
        "inject": "宿主的系统提示词 / 自定义指令 / Project instructions",
        "native": None,
        "trigger": "触发：用户消息出现「金融日报」「市场要闻」等触发词时按流程执行。",
        "notes": [
            "本文件 ~9.7k 字符：ChatGPT GPTs（8000 字符）、Kimi 智能体（5000 字）、DeepSeek 助手（8000 字符）、"
            "豆包/Coze（4000 **token**）都放不下 —— 这些宿主请改用 `system-prompt-slim.md`。",
            "纯对话宿主一般没有「执行命令」能力 → 按正文 §9 档位 4「只读版」：让用户本地跑 fetch_public.py 再把 JSON 粘回来。",
        ],
    },
    "system-prompt-slim.md": {
        "title": "系统提示词精简版（GPTs / Kimi / DeepSeek / 豆包 等有字数上限的宿主）",
        "inject": "宿主的系统提示词 / 人设与回复逻辑 / 自定义指令",
        "native": None,
        "slim": True,
        "trigger": "触发：用户消息出现「金融日报」「市场要闻」等触发词时按流程执行。",
        "notes": [
            "本文件是 SKILL.md 的人工摘编（源文件 maintainer/prompt-slim.src.md），控制在 ~3.4k 字符内，"
            "以满足豆包 4000 token / Kimi 5000 字 / GPTs 8000 字符中最紧的一档；脚本会检查铁律短语与配色令牌没有丢失。",
            "摘编只删了宿主用不上的东西（脚本端点表、渲染命令、路径基准）；数据铁律、板块结构、配色令牌、已知坑全部保留。",
            "需要完整口径（例如让用户本地跑脚本取硬数据）时，把 SKILL.md 的 §1/§2 贴在对话里补充说明。",
        ],
    },
}

CURSOR_FM = """---
description: 生成「金融日报」金融市场要闻日报（报刊风 HTML+PNG 长图）。当用户要求金融日报、市场要闻、要闻更新、今天的金融要闻、金融市场要闻时使用。纯公开数据源（新浪/CNBC/深交所/美国财政部），多源交叉核对，禁止编造数据。
alwaysApply: false
---
"""

CAPABILITY_LINE = (
    "开始前先确认宿主具备哪些能力（执行命令 / 检索网页 / 打开网页 / 渲染 PNG），"
    "按正文 §9 的降级档位执行；缺能力不等于可以编数。"
)


def render_header(meta: dict, version: str, slug: str, body_len: int, src_note: str, with_marker: bool = True) -> str:
    lines = ([marker(version, src_note), ""] if with_marker else [])
    lines += [f"# {SKILL_NAME} · {meta['title']}", ""]
    # 占位符先占位，整篇拼完后再回填真实总长度（宿主按整篇字符数算上下文预算）
    lines += [f"> 由 SKILL.md v{version} 生成 · 整篇 {TOTAL_LEN_SLOT} 字符", ""]
    lines += ["## 安装", ""]
    lines += install_lines(slug, meta.get("native"), meta.get("inject"))
    lines += ["", "## 触发", "", meta["trigger"], ""]
    if meta.get("notes"):
        lines += ["## 本宿主须知", ""]
        lines += [f"- {n}" for n in meta["notes"]]
        lines += [""]
    if not meta.get("slim"):
        lines += ["## 能力自查", "", CAPABILITY_LINE, ""]
    lines += ["---", "", ("-- 正文开始（摘编自 maintainer/prompt-slim.src.md，覆盖 SKILL.md 全部硬约束）--"
                          if meta.get("slim") else
                          "-- 正文开始（SKILL.md 正文逐字复制，仅去掉其文件级维护注释）--"), ""]
    return "\n".join(lines)


def build(check: bool) -> int:
    version, body, _ = read_skill()
    body_plain = read_body_without_maintainer_note()
    slug = detect_repo_slug()
    drift: list[str] = []
    problems: list[str] = []

    if not SLIM_SRC.is_file():
        problems.append(f"缺少摘编源文件 {SLIM_SRC.relative_to(ROOT)}")
        slim_body = ""
    else:
        slim_body = SLIM_SRC.read_text(encoding="utf-8").strip() + "\n"
        missing = slim_coverage_check(slim_body, body)
        if missing:
            problems.append(
                "maintainer/prompt-slim.src.md 丢失了正文里的关键内容：" + "、".join(missing)
                + " —— 请把新增的铁律/配色补进摘编"
            )
        if len(slim_body) > 3400:
            problems.append(f"摘编正文 {len(slim_body)} 字符，超 3400 预算（豆包 4000 token 最紧一档）")

    for fname, meta in ADAPTERS.items():
        inner = slim_body if meta.get("slim") else body_plain
        src_note = "maintainer/prompt-slim.src.md" if meta.get("slim") else "SKILL.md"
        if meta.get("mdc_frontmatter"):
            # Cursor 的 YAML frontmatter 必须严格在文件最前，生成标记放它后面第一行
            header = render_header(meta, version, slug, len(inner), src_note, with_marker=False)
            content = CURSOR_FM + "\n" + marker(version, src_note) + "\n\n" + header + inner
        else:
            content = render_header(meta, version, slug, len(inner), src_note) + inner
        if not content.endswith("\n"):
            content += "\n"
        content = fill_total_len(content)
        out = ADAPTERS_DIR / fname
        if check:
            if not out.exists():
                drift.append(fname)
            elif out.read_text(encoding="utf-8") != content:
                drift.append(fname)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8", newline="\n")
        print(f"[ok] {fname:24s} {len(content):6d} chars")

    if check:
        if problems:
            for p in problems:
                print(f"ERROR: {p}")
            return 1
        if drift:
            print(f"DRIFT: {len(drift)} 个适配文件与源文件不同步: {', '.join(drift)} — 跑 python scripts/build_adapters.py")
            return 1
        print(f"OK: 全部适配文件与 SKILL.md v{version} / 摘编一致")
        return 0
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        return 1
    print(f"\n生成完成（SKILL.md v{version}" + (f"，repo={slug}" if slug else "，未配置 maintainer/repo.txt，安装器一行已省略") + "）")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="从 SKILL.md 生成各宿主适配文件")
    ap.add_argument("--check", action="store_true", help="只校验是否同步，不写入（CI 用）")
    a = ap.parse_args()
    sys.exit(build(check=a.check))


if __name__ == "__main__":
    main()
