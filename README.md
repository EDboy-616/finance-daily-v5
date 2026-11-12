<div align="center">

<a href="https://github.com/EDboy-616/finance-daily-v5">
  <img src="docs/banner.png" alt="金融日报 V5" width="860">
</a>

<br>

<img src="https://img.shields.io/badge/Agent_Skills-v5.0.0-b08a2e?style=for-the-badge" alt="Agent Skills v5.0.0">
<img src="https://img.shields.io/badge/API_Key-不需要-b23b2e?style=for-the-badge" alt="无需 API Key">
<img src="https://img.shields.io/badge/第三方依赖-零-1e7a52?style=for-the-badge" alt="零第三方依赖">
<img src="https://img.shields.io/badge/宿主适配-14_类-1c2230?style=for-the-badge" alt="14 类宿主">
<img src="https://img.shields.io/badge/交付-HTML_+_3x_PNG-b08a2e?style=for-the-badge" alt="双交付">

<br>

<a href="https://github.com/EDboy-616/finance-daily-v5/actions/workflows/verify.yml">
  <img src="https://github.com/EDboy-616/finance-daily-v5/actions/workflows/verify.yml/badge.svg" alt="CI">
</a>
<a href="https://agentskills.io/specification">
  <img src="https://img.shields.io/badge/规范-agentskills.io-4a5366" alt="Agent Skills 规范">
</a>
<img src="https://img.shields.io/badge/python-3.8+-4a5366" alt="Python 3.8+">
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-4a5366" alt="MIT"></a>

<br><br>

说一句 <b>「金融日报」</b>，自动采集公开市场行情、检索权威媒体要闻，<br>
产出一份<b>报刊风（editorial）金融要闻日报</b>——网页 + 高清长图。

</div>

<br>

> [!NOTE]
> **接手的 agent 请先读 [HANDOFF.md](HANDOFF.md)** —— 项目状态、架构约定、验证方法、待办事项都在那里。本 README 面向使用者。

---

## ✦ 产出预览

**报头与头版** —— 日期 / 时段 / 数据时点，价格速览条十卡一屏看完，主稿配 TOP 5 要点。

<img src="docs/preview-top.png" alt="金融日报 · 报头与头版" width="100%">

**板块细节** —— 行业扫描、商品期货、资金流向、公司中报、机构观点，全部按报纸栏目排布。

<img src="docs/preview-detail.png" alt="金融日报 · 板块细节" width="100%">

<details>
<summary><b>展开查看整版长图（点击）</b></summary>
<br>
<img src="docs/preview-full.png" alt="金融日报 · 整版" width="100%">
</details>

一份日报固定包含 **13 个板块**：

| 板块 | 内容 | 板块 | 内容 |
|:--|:--|:--|:--|
| 报头 · 数据截至 | 日期、时段、数据时点 | 商品与期货 | 内盘夜盘、外盘持仓 |
| 价格速览条 | 10 个核心标的一屏看完 | 资金流向 | 两融、主力、南向 |
| 头版 FRONT PAGE | 主稿 + TOP 5 要点 | 公司与中报 | 业绩、IPO |
| 国内 · 宏观与政策 | 流动性、政策、产业 | 机构观点 | 券商与外资观点 |
| 国际 · 市场与央行 | 美股、美联储、债市 | 今日关注 | 事件、风险提示 |
| 汇率与外汇 | 人民币、美元、主要货币 | 数据说明 | 数据源披露（必填） |
| 行业扫描 | 领涨 / 领跌 / 题材 | | |

<sub>红涨绿跌（中国习惯）· 暖纸 <code>#f7f4ed</code> · 墨蓝 <code>#1c2230</code> · 金线 <code>#b08a2e</code> · 涨 <code>#b23b2e</code> · 跌 <code>#1e7a52</code></sub>

> 以上预览由 `assets/market_news_template.html` 以样例数据渲染，用于展示版面结构；真实产出会填入当日行情与新闻。

---

## ✦ 为什么是它

| 常见做法 | 代价 | 本技能 |
|:--|:--|:--|
| 接 Wind / 同花顺 连接器 | 账号、授权、按量计费 | **纯公开数据源**，脚本直连，零成本 |
| 让模型「凭记忆」写行情 | 数字编造，最危险的错 | 硬行情走脚本；取不到就**撤下或标「待核」** |
| 只给一段提示词 | 每次都要重新组织流程 | 完整 `SKILL.md`：取数 → 复核 → 排版 → 双交付 |
| 锁死在某一个 AI 工具 | 换宿主就废 | **14 类宿主**两套安装机制，一份源 |

**三条铁律**（任何降级都不放宽）

1. 每个数字要么来自脚本，要么有 **≥2 个权威源**一致；
2. 取不到 → **撤下或标「待核」，禁止编造、禁止取平均**；
3. 页面底部**必须**有「数据说明」，披露数据来源。

---

## ✦ 快速开始

```bash
git clone https://github.com/EDboy-616/finance-daily-v5.git
cd finance-daily-v5

python scripts/install.py --list          # 看 14 类宿主的落点
python scripts/install.py --target claude # 装成当前项目的 .claude/skills/ 原生 skill
```

然后在对话里说 **「金融日报」** 即可。产出落在工作目录：

```
outputs/market_news_20261112.html   # 网页版
outputs/market_news_20261112.png    # 3x 高清长图
raw/market_20261112.json            # 结构化行情（每字段带 src/status，供复核）
```

想单独验证数据源连通性：

```bash
python scripts/fetch_public.py --date 2026-11-12 --out-dir ./raw
```

> [!TIP]
> 渲染 PNG 需要额外装 `playwright` + `pillow`；**行情脚本零依赖**，只用 Python 标准库。
> ```bash
> pip install playwright pillow && playwright install chromium
> ```

---

## ✦ 跨宿主：两种机制，各有取舍

`SKILL.md` 是唯一事实源（[Agent Skills 开放规范](https://agentskills.io/specification)）。装到别的宿主有**两条路**，本仓库两条都支持：

<table>
<tr><th width="18%">机制</th><th width="30%">怎么生效</th><th width="26%">优点</th><th width="26%">代价</th></tr>
<tr>
<td><b>注入式</b><br><code>inject</code></td>
<td>把 <code>adapters/&lt;宿主&gt;.md</code> 整篇写进该宿主常驻注入的上下文文件（<code>AGENTS.md</code> / <code>GEMINI.md</code> / <code>QWEN.md</code> / <code>CLAUDE.md</code> / <code>.cursor/rules/*.mdc</code>）</td>
<td><b>说「金融日报」就自动跑完整流程</b>——非 Claude 宿主没有关键词路由，正文不常驻就不会执行</td>
<td>每次会话固定吃 ~10k 字符上下文</td>
</tr>
<tr>
<td><b>原生 skills</b><br><code>skill</code></td>
<td>把整个 skill 目录复制进宿主的 skills 根（<code>~/.claude/skills/</code>、<code>~/.agents/skills/</code>、<code>~/.qwen/skills/</code> …）</td>
<td>正文按需加载、省上下文，可用宿主的 skill 管理/更新</td>
<td>多数宿主对原生 skill <b>只认显式调用</b>（Codex <code>$finance-daily-v5</code>、Gemini <code>/skill:finance-daily-v5</code>），触发词不会自动执行</td>
</tr>
</table>

> [!TIP]
> 想两者兼得：注入一份到项目 `AGENTS.md`（自动触发）+ 复制一份到宿主 skills 目录（显式调用与升级）。
> ```bash
> python scripts/install.py --target agents --mode inject   # 自动触发
> python scripts/install.py --target agents --mode skill    # 省上下文的显式调用
> python scripts/install.py --target all --global           # 全部宿主，全局装
> ```

### 各宿主落点与坑

| 宿主 | inject 目标 | 原生 skills（项目 / 全局） |
|:--|:--|:--|
| **Claude Code / claude.ai** | `CLAUDE.md` | `.claude/skills/` · `~/.claude/skills/` |
| **OpenAI Codex CLI** | `AGENTS.md` | `.agents/skills/` · `~/.agents/skills/` |
| **GitHub Copilot / VS Code** | `AGENTS.md` | `.github/skills/` · `~/.copilot/skills/` |
| **Gemini CLI** | `GEMINI.md` | `.gemini/skills/` · `~/.gemini/skills/` |
| **Qwen Code** | `QWEN.md` | `.qwen/skills/` · `~/.qwen/skills/` |
| **Cursor** | `.cursor/rules/finance-daily-v5.mdc` | `.cursor/skills/` |
| **OpenCode / TRAE / Kiro / Roo / Goose / CodeBuddy / Antigravity** | `AGENTS.md` | 各自的 `<宿主>/.skills/`（见 `install.py --list`） |
| **GPTs / Kimi / DeepSeek / 豆包 / GLM（纯对话）** | 手工粘贴系统提示词 | — |

**装之前值得知道的六个坑**

- **Claude Code** 是唯一按 `description` 自动判定的宿主；但正文里不能写 `${CLAUDE_SKILL_DIR}` 这类宿主特性，否则会污染其他宿主。
- **Codex CLI** 没有 `.codex/skills/` 这个路径；`project_doc_max_bytes=32768`；全局与仓库的 `AGENTS.md` **只取第一个命中**。
- **Copilot / VS Code** 默认只吃 **8000 字符**（`chat.agent.customInstructionLimit`），而本适配文件约 10k，需调大；调不动就用原生 skills 模式。
- **Qwen Code** 在 `QWEN.md` 与 `AGENTS.md` 并存时**优先 QWEN.md**，改完要 `/memory` 重载；**Gemini CLI** 的上下文文件不会自动执行动作，原生 skill 需 `/skill:` 显式调用。
- **Cursor** 只加载 `.mdc`；`alwaysApply:false` 时靠 `description` 命中，规则文件上限 1MB。
- **纯对话型（GPTs / Kimi / DeepSeek / 豆包 / GLM）装不了 skill**，只能贴系统提示词：最紧的豆包 4000 token 用 `adapters/system-prompt-slim.md`（2.3k 字符），能放长文的用 `adapters/system-prompt.md`。

### 能力降级（铁律不降）

| 档位 | 所需能力 | 产出 |
|:--|:--|:--|
| 完整版 | 命令 + 检索 + 打开网页 + Playwright | HTML + PNG 双交付 |
| 标准版 | 命令 + 检索 | HTML（新闻数字须 ≥2 源一致） |
| 行情版 | 仅命令 | 纯行情 HTML（新闻板块标注未采集） |
| 只读版 | 无（纯对话） | 用户本地跑 `fetch_public.py` 贴回 JSON，产出 HTML 文本 |

---

## ✦ 数据源与复核矩阵

| 指标 | 主源 | 复核源 |
|:--|:--|:--|
| A股三大指数 | 新浪 `hq.sinajs.cn` | 新闻通稿 |
| 两市成交额 | 新浪（沪+深） | 深交所官方 + 新闻 |
| 恒生指数 | 新浪 `rt_hk*` | 新闻 / 港交所 |
| 美股三大指数 | CNBC 公开报价（标注盘中/收盘） | 新闻通稿 + FRED（T-1） |
| 10Y/2Y 美债 | 美国财政部官方 CSV | Fed H.15 / 新闻 |
| 人民币汇率 | 新浪 | 央行中间价 / 中国货币网 |
| 商品期货 | 新浪 内盘 + 外盘 | 交易所官网 / 新闻 |
| 新闻与政策 | 新华社、证券时报、上海证券报、中国证券报、财联社、第一财经、东方财富、AP News | 6 主题检索 + 2~4 个核心数字定点复核 |

冲突处理：两源不一致 → **不编造、不取平均**，写「X 源报 A，Y 源报 B（待核）」或撤下该指标。

---

## ✦ 目录结构

```
finance-daily-v5/
|-- SKILL.md                          # 技能定义与完整流程（唯一事实源）
|-- README.md                         # 本文件
|-- HANDOFF.md                        # 维护者交接：约定、验证、待办
|-- .claude-plugin/marketplace.json   # Claude Code 插件市场清单
|-- adapters/                         # 各宿主注入文件（生成物，勿手改）
|   |-- AGENTS.md                     # Codex / Copilot / 一切读 AGENTS.md 的 agent
|   |-- GEMINI.md                     # Gemini CLI
|   |-- QWEN.md                       # Qwen Code
|   |-- CLAUDE.md                     # Claude Code
|   |-- cursor-rules.mdc              # Cursor Project Rules
|   |-- system-prompt.md              # 纯对话型全文版（GLM / Claude Projects）
|   `-- system-prompt-slim.md         # 纯对话型精简版（GPTs/Kimi/DeepSeek/豆包）
|-- maintainer/                       # 维护侧（不随 skill 安装）
|   |-- prompt-slim.src.md            # system-prompt-slim.md 的人工源（带覆盖率校验）
|   |-- repo.txt                      # 安装器展示的仓库地址（生成物不依赖 git remote）
|   `-- make_docs_images.py           # 生成本 README 的徽标 / 横幅 / 预览图
|-- docs/                             # README 用图（banner.png / preview-*.png / emblem.svg）
|-- assets/market_news_template.html  # 报刊风渲染模板
|-- scripts/
|   |-- fetch_public.py               # 公开源硬行情抓取（纯标准库）
|   |-- render.py                     # Playwright 3x 渲染 PNG + 自动裁边
|   |-- build_adapters.py             # 从 SKILL.md 生成 adapters/（--check 校验漂移）
|   |-- validate_skill.py             # 规范 + 宿主上限 + 路径引用自检
|   |-- install.py                    # 一键装进 14 类宿主
|   `-- package_claudeai.py           # 打 claude.ai / Skills API 可上传的 zip
`-- .github/workflows/verify.yml      # CI：ubuntu + windows 双矩阵
```

---

## ✦ 其他安装方式

<details>
<summary><b>② 手工克隆到 skills 目录</b></summary>

```bash
# 个人级（所有项目可用）
git clone https://github.com/EDboy-616/finance-daily-v5.git ~/.claude/skills/finance-daily-v5
# Windows PowerShell: $env:USERPROFILE\.claude\skills\finance-daily-v5

# 项目级
git clone https://github.com/EDboy-616/finance-daily-v5.git .claude/skills/finance-daily-v5
```

其他宿主把路径换成 `.agents/skills/`、`.gemini/skills/`、`.qwen/skills/` 等（见上表）。
</details>

<details>
<summary><b>③ Claude Code 插件 / claude.ai 上传</b></summary>

```bash
# Claude Code：本地市场 + 安装
claude plugin marketplace add ./
claude plugin install finance-daily-v5@finance-daily-v5
claude plugin validate .            # 可选：校验清单

# claude.ai：打上传包（根 = finance-daily-v5/ 文件夹，符合官方要求）
python scripts/package_claudeai.py  # → dist/finance-daily-v5-5.0.0.zip
```

claude.ai 侧：Settings → Capabilities → Skills → Upload a skill（需开启 Code execution）。
</details>

<details>
<summary><b>④ 装完自检</b></summary>

```bash
python scripts/build_adapters.py --check && python scripts/validate_skill.py
```

装好后重启宿主会话；Claude Code 里输入 `/` 应能看到 `finance-daily-v5`。
</details>

---

## ✦ 维护者须知

改 `SKILL.md` 后必须重新生成适配层并自检：

```bash
python scripts/build_adapters.py     # 重新生成 adapters/
python scripts/validate_skill.py     # 规范合规 + 宿主上限 + 引用路径 + 摘编覆盖率
```

- `adapters/` 是**生成物**，手改会被下一次生成覆盖。
- `adapters/system-prompt-slim.md` 有**第二个源文件** `maintainer/prompt-slim.src.md`（人工压缩）。生成器会校验：正文里的每个色值、每条铁律关键词都必须出现在摘编里，否则报错——这样「摘编」不会因为某次正文改动而悄悄漏掉新规则。
- 改完 README 用图：`python maintainer/make_docs_images.py`（需 playwright + pillow）。
- CI 在 ubuntu + windows 双矩阵跑：`validate_skill.py` → `build_adapters.py --check` → `git status --porcelain -- adapters/` 漂移即失败 → 脚本 smoke → 打 claude.ai 上传包。

---

## ✦ 已知限制

- **没有「检索网页」能力的宿主自动降级为行情版**；缺什么降什么档，但数据铁律不放宽。
- **非 Claude 宿主上触发词不会自动生效**，除非走 inject 模式（正文常驻）。这是各家 agent 的能力边界，不是本技能的缺陷。
- 东方财富 push2 与 FRED 在部分网络环境（本地代理 / 强制 HTTP/2）会被拒；脚本已降级为可选交叉源，失败即跳过。
- 美股 `curmktstatus=REG_MKT` 表示盘中价（美东 16:00 前），日报会标注时点。
- 财政部收益率曲线为 T-1 发布，当日美债数据次日才出。
- 新浪 `int_dji/int_nasdaq/int_sp500` 是陈旧序列，本技能**禁用**（美股只信 CNBC + 新闻双源）。
- 非交易日 A股/港股沿用最近交易日收盘，深交所官方接口可能返回「未找到股票行」，属正常。
- `adapters/AGENTS.md` 约 10k 字符，超出 Copilot 默认 8000 字符上限，需调大 `chat.agent.customInstructionLimit`；Codex 默认 32768 字节放得下。
- `scripts/install.py` 的宿主路径表来自官方文档与三家安装器交叉核对，**未在每台宿主上逐一实测**；OpenCode / TRAE / Kiro / Roo / Goose / CodeBuddy / Antigravity 七家沿用社区约定。

---

## ✦ 版本

| 版本 | 要点 |
|:--|:--|
| **V5.0.0**（当前） | 全面改为公开数据源（零连接器 / 零 API Key / 零积分）；脚本化硬行情 + 「检索网页/打开网页」多源交叉核对；适配层重做为 inject + 原生 skills 双机制，新增 `install.py` / `validate_skill.py` / `package_claudeai.py` 与 CI |
| V4 | ftShare + Wind 双连接器交叉核对 —— 已删除，不保留备份 |

---

## ✦ License

[MIT](LICENSE) · 仅供信息参考，不构成投资建议

<br>

<div align="center">
<sub>如果这个技能帮你省下了每天早上翻十个网站的时间，给个 ⭐ 吧</sub>
</div>
