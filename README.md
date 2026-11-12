# 金融日报 V5 (finance-daily-v5)

> **接手的 agent 请先读 [HANDOFF.md](HANDOFF.md)** —— 项目状态、架构约定、验证方法与待办事项都在那里。本 README 面向最终用户。

一个 [Agent Skills 开放规范](https://agentskills.io/specification)（原 Claude Agent Skills）格式的技能包：对话中说「金融日报」，自动采集公开市场数据并生成**报刊风（editorial）金融要闻日报长图**，双交付 **HTML + 高清 PNG**。

![style](https://img.shields.io/badge/style-报刊风暖纸金线-b08a2e) ![deps](https://img.shields.io/badge/fetch-零第三方依赖-1e7a52) ![api](https://img.shields.io/badge/API%20Key-不需要-b23b2e)

## 特性

- **纯公开数据源** — 零连接器、零 API Key、零积分。硬行情由 `scripts/fetch_public.py`（纯 Python 标准库）直连公开接口一次取齐：
  - A股/港股指数与成交额（新浪财经公开行情接口）
  - 美股三大指数（CNBC 公开报价，含盘中/收盘状态标记）
  - 美债收益率曲线（美国财政部官方 CSV）
  - 深市成交额官方复核（深交所）
  - 内盘商品期货、外盘商品、汇率与美元指数（新浪）
- **新闻与复核走「检索网页 + 打开网页」**（不绑定任何宿主的专有工具名）：新华社、证券时报、上海证券报、中国证券报、财联社、第一财经、东方财富、上交所/深交所/港交所、央行、美联储 H.15、AP News 等权威源，6 主题检索 + 2~4 个核心数字定点复核。
- **多源交叉核对铁律**：每个 ticker 数字须有脚本或 ≥2 个新闻源支撑；取不到的数字**撤下或标「待核」，禁止编造、禁止取平均**。
- **报刊风版面**：暖纸底 `#f7f4ed` + 深墨蓝 + 金线 + 红涨绿跌（中国习惯），读报式多栏排版，ticker 十卡 + 头版主稿 + TOP5 侧栏 + 11 个内容板块 + 数据说明。
- **双交付**：HTML 网页（可预览）+ 3x 高清 PNG 长图（Playwright 渲染 + 自动裁边）。
- **纯市场要闻**：不含个人持仓/自选等个性化内容，页面内不出现风格/流程自述。

## 跨宿主兼容：两种安装机制，各有取舍

`SKILL.md` 是唯一事实源（[Agent Skills 开放规范](https://agentskills.io/specification)）。装到别的宿主有**两条路**，本仓库两条都支持（`scripts/install.py` 一键走）：

| 机制 | 怎么生效 | 优点 | 代价 |
|------|---------|------|------|
| **注入式 inject** | 把 `adapters/<宿主>.md` 整篇写进该宿主常驻注入的上下文文件（`AGENTS.md` / `GEMINI.md` / `QWEN.md` / `CLAUDE.md` / `.cursor/rules/*.mdc`） | **说「金融日报」就自动跑完整流程**——非 Claude 宿主没有关键词路由，正文不常驻就不会执行 | 每次会话固定吃 ~10k 字符上下文 |
| **原生 skills** | 把整个 skill 目录复制进宿主的 skills 根（`~/.claude/skills/`、`~/.agents/skills/`、`~/.qwen/skills/` …） | 正文按需加载、省上下文，可用宿主的 skill 管理/更新 | 多数宿主对原生 skill **只认显式调用**（Codex `$finance-daily-v5`、Gemini `/skill:finance-daily-v5`），触发词不会自动执行 |

> 想两者兼得：注入一份到项目 `AGENTS.md`（自动触发）+ 复制一份到宿主 skills 目录（显式调用与升级）。

### 各宿主一览

| 宿主 | inject 目标 | 原生 skills 目录（项目级 / 全局） | 该宿主的坑 |
|------|------------|----------------------------------|-----------|
| **Claude Code / claude.ai** | `CLAUDE.md` | `.claude/skills/` / `~/.claude/skills/` | 唯一按 `description` 自动判定的宿主；正文里不能用 `${CLAUDE_SKILL_DIR}` 之类的宿主特性（会污染其他宿主） |
| **OpenAI Codex CLI** | `AGENTS.md` | `.agents/skills/` / `~/.agents/skills/` | **没有 `.codex/skills/` 这个路径**；`project_doc_max_bytes=32768`；全局与仓库 `AGENTS.md` **只取第一个命中**，别两处都放 |
| **GitHub Copilot / VS Code** | `AGENTS.md` | `.github/skills/` / `~/.copilot/skills/` | 默认只吃 **8000 字符**（`chat.agent.customInstructionLimit`），本文件 ~10k，需在设置里调大 |
| **Gemini CLI** | `GEMINI.md` | `.gemini/skills/` / `~/.gemini/skills/` | 上下文文件不会自动执行动作；原生 skill 要 `/skill:` 显式调用；联网工具是 `google_web_search` |
| **Qwen Code** | `QWEN.md` | `.qwen/skills/` / `~/.qwen/skills/` | `QWEN.md` 与 `AGENTS.md` 同时在 → **优先 QWEN.md**；改完 `/memory` 重载 |
| **Cursor** | `.cursor/rules/finance-daily-v5.mdc` | `.cursor/skills/` / — | 只加载 `.mdc`；`alwaysApply:false` 时靠 `description` 命中规则；规则文件上限 1MB |
| **OpenCode / TRAE / Kiro / Roo / Goose / CodeBuddy / Antigravity** | `AGENTS.md` | 各自 `.opencode/skills/`、`.trae/skills/`、`.kiro/skills/`、`.roo/skills/`、`.goose/skills/`、`.codebuddy/skills/`、`.agent/skills/` | 均支持 Agent Skills 目录约定；未逐宿主实测 |
| **GPTs / Kimi / DeepSeek / 豆包 / GLM（纯对话）** | 手工粘贴 | — | **装不了，只能贴系统提示词**：用 `adapters/system-prompt-slim.md`（2.3k 字符，最紧一档豆包 4000 token 也放得下）；能放长文的宿主（GLM / Claude Projects）用 `adapters/system-prompt.md`（9.7k 全文） |

正文按宿主实际能力自动降级，**任何档位都不放宽数据铁律**（取不到的数字撤下或标「待核」，禁止编造）：

| 档位 | 所需能力 | 产出 |
|------|---------|------|
| 完整版 | 命令 + 检索 + 打开网页 + Playwright | HTML + PNG 双交付 |
| 标准版 | 命令 + 检索 | HTML（新闻数字须 ≥2 源一致） |
| 行情版 | 仅命令 | 纯行情 HTML（新闻板块标注未采集） |
| 只读版 | 无（纯对话） | 用户本地跑 `fetch_public.py` 贴回 JSON，产出 HTML 文本 |

### 维护约定

- 改 `SKILL.md` 后必须 `python scripts/build_adapters.py` 重新生成，再 `python scripts/validate_skill.py` 自检（规范合规 + 宿主上限 + 正文引用路径 + 摘编覆盖率）。
- `adapters/system-prompt-slim.md` 有**第二个源文件** `maintainer/prompt-slim.src.md`（人工压缩的提示词，塞不进 10k 字符的宿主用）。生成器会校验：正文里的每个色值、每条铁律关键词都必须出现在摘编里，否则报错——这样"摘编"不会因为某次正文改动而悄悄漏掉新规则。
- CI（`.github/workflows/verify.yml`）在 ubuntu + windows 双矩阵跑：`validate_skill.py` → `build_adapters.py --check` → `git status --porcelain -- adapters/` 漂移即失败 → 脚本 smoke → 打 claude.ai 上传包。
- 提交前也可以本地自查：`python scripts/build_adapters.py --check && python scripts/validate_skill.py`。


## 目录结构

```
finance-daily-v5/
├── SKILL.md                        # 技能定义与完整流程（唯一事实源，Agent Skills 开放规范）
├── README.md                       # 本文件
├── HANDOFF.md                      # 维护者交接：架构约定、验证方法、待办
├── LICENSE
├── .claude-plugin/
│   └── marketplace.json            # Claude Code 插件市场清单（/plugin marketplace add 用）
├── adapters/                       # 各宿主注入文件（由 build_adapters.py 生成，勿手改）
│   ├── AGENTS.md                   #   Codex CLI / Copilot / 一切读 AGENTS.md 的 agent
│   ├── GEMINI.md                   #   Gemini CLI
│   ├── QWEN.md                     #   Qwen Code
│   ├── CLAUDE.md                   #   Claude Code 项目引用版
│   ├── cursor-rules.mdc            #   Cursor Project Rules
│   ├── system-prompt.md            #   纯对话型宿主全文版（GLM / Claude Projects）
│   └── system-prompt-slim.md       #   纯对话型宿主精简版（GPTs/Kimi/DeepSeek/豆包，2.3k）
├── maintainer/
│   └── prompt-slim.src.md          # system-prompt-slim.md 的源文件（人工摘编，带覆盖率校验）
├── assets/
│   └── market_news_template.html   # 报刊风渲染模板（含全部 section 结构）
├── scripts/
│   ├── fetch_public.py             # 公开源硬行情抓取（纯标准库，零第三方依赖）
│   ├── render.py                   # Playwright 3x 渲染 PNG + 自动裁边
│   ├── build_adapters.py           # 从 SKILL.md 生成 adapters/（--check 校验漂移）
│   ├── validate_skill.py           # 规范 + 宿主上限 + 路径引用自检（零依赖）
│   ├── install.py                  # 一键装进 14 类宿主（inject / skill 两种模式）
│   └── package_claudeai.py         # 打 claude.ai / Skills API 可上传的 zip
└── .github/workflows/verify.yml    # CI：ubuntu+windows 双矩阵，规范 / 漂移 / smoke / 打包
```

## 安装

三种方式，按省事程度排序。

### ① 一行装（推荐，两种模式都能选）

```bash
git clone https://github.com/EDboy-628/finance-daily-v5.git
cd finance-daily-v5

python scripts/install.py --list                    # 先看 14 类宿主的落点
python scripts/install.py --target claude           # 在【当前目录】装成 .claude/skills/ 原生 skill
python scripts/install.py --target agents --mode inject   # 把 AGENTS.md 受管块写进当前项目
python scripts/install.py --target all --global     # 全局装（~/.claude/skills、~/.agents/skills …）
```

- 项目级目标相对**你运行命令时所在的项目目录**解析；`--project <dir>` 可显式指定。
- `inject` 只动自己 `<!-- BEGIN finance-daily-v5 -->` 与 `<!-- END finance-daily-v5 -->` 之间的内容，块外你写的东西不会被碰；重复跑是幂等的。
- `skill` 模式默认不覆盖已存在目录，加 `--force` 才覆盖，且只覆盖 SKILL.md 里带 `name: finance-daily-v5` 的目录。

### ② 手工克隆到 skills 目录（Claude Code / 任意支持 Agent Skills 的宿主）

```bash
# 个人级（所有项目可用）
git clone https://github.com/EDboy-628/finance-daily-v5.git ~/.claude/skills/finance-daily-v5
# Windows PowerShell: $env:USERPROFILE\.claude\skills\finance-daily-v5

# 项目级
git clone https://github.com/EDboy-628/finance-daily-v5.git .claude/skills/finance-daily-v5
```

其他宿主把路径换成 `.agents/skills/`、`.gemini/skills/`、`.qwen/skills/` 等（见上表）。

### ③ Claude Code 插件 / claude.ai 上传

```bash
# Claude Code：本地市场 + 安装
claude plugin marketplace add ./
claude plugin install finance-daily-v5@finance-daily-v5
claude plugin validate .            # 可选：校验清单

# claude.ai：打上传包（根 = finance-daily-v5/ 文件夹，符合官方要求）
python scripts/package_claudeai.py  # → dist/finance-daily-v5-5.0.0.zip
```

claude.ai 侧：Settings → Capabilities → Skills → Upload a skill（需开启 Code execution）。

### 渲染依赖（仅 PNG 需要；行情脚本零依赖）

```bash
pip install playwright pillow
playwright install chromium
```

装好后重启宿主会话；Claude Code 里输入 `/` 应能看到 `finance-daily-v5`（或 `/finance-daily-v5:finance-daily-v5`，走插件时）。

## 使用

对宿主说以下任意触发词即可（Claude Code / claude.ai 靠 `description` 自动判定；其他宿主需先 inject 或显式调用）：

> 金融日报 / 金融市场要闻 / 市场要闻 / 要闻更新 / 金融要闻日报 / 今天的市场要闻

产出（在工作目录下）：

- `outputs/market_news_YYYYMMDD.html` — 网页版
- `outputs/market_news_YYYYMMDD.png` — 3x 高清长图
- `raw/market_YYYYMMDD.json` — 结构化行情中间产物（每个字段带 `src`/`status`，供复核）

也可以单独运行行情脚本自检数据源可用性：

```bash
python scripts/fetch_public.py --date 2026-11-12 --out-dir ./raw
```

控制台会列出「成功源 / 失败源(必须补) / 可选交叉源未取到(可跳过)」。

## 数据源与复核矩阵

| 指标 | 主源 | 复核源 |
|------|------|--------|
| A股三大指数 | 新浪 `hq.sinajs.cn` | 新闻通稿 |
| 两市成交额 | 新浪（沪+深） | 深交所官方 + 新闻 |
| 恒生指数 | 新浪 `rt_hk*` | 新闻 / 港交所 |
| 美股三大指数 | CNBC | 新闻通稿 + FRED（T-1） |
| 10Y/2Y 美债 | 美国财政部官方 CSV | Fed H.15 / 新闻 |
| 人民币汇率 | 新浪 | 央行中间价 / 中国货币网 |
| 商品期货 | 新浪 内盘+外盘 | 交易所官网 / 新闻 |

冲突处理：两源不一致 → 不编造、不取平均，写「X 源报 A，Y 源报 B（待核）」或撤下该指标。

## 已知限制

- **没有「检索网页」能力的宿主环境自动降级为「行情版」**（见跨宿主兼容的档位表）：硬行情靠脚本，新闻靠检索能力，缺什么降什么档，但数据铁律不放宽。
- **非 Claude 宿主上触发词不会自动生效**，除非走 inject 模式（正文常驻）。这是各家 agent 的能力边界，不是本 skill 的缺陷。
- 东方财富 push2 与 FRED 在部分网络环境（本地代理 / 强制 HTTP/2）会被拒；脚本已将其降级为可选交叉源，失败即跳过。
- 美股 `curmktstatus=REG_MKT` 表示盘中价（美东 16:00 前），日报会标注时点。
- 财政部收益率曲线为 T-1 发布，当日美债数据次日才出。
- 新浪 `int_dji/int_nasdaq/int_sp500` 是陈旧序列，本技能禁用（美股只信 CNBC + 新闻双源）。
- 非交易日 A股/港股沿用最近交易日收盘，深交所官方接口可能返回「未找到股票行」，属正常。
- `adapters/AGENTS.md` 约 10k 字符，超出 GitHub Copilot 默认 8000 字符上限，需要在 VS Code 设置里调大 `chat.agent.customInstructionLimit`；Codex 默认 32768 字节则放得下。
- `scripts/install.py` 的宿主路径表来自官方文档与三家安装器（skills.sh / skillfish / ruler）交叉核对，但**未在每台宿主上逐一实测**；OpenCode / TRAE / Kiro / Roo / Goose / CodeBuddy / Antigravity 七家的 skills 目录沿用社区约定。

## 版本

- **V5.0.0（当前）**：全面改为公开数据源（零连接器、零 API Key、零积分），脚本化硬行情 + 「检索网页/打开网页」多源交叉核对；适配层重做为 inject + 原生 skills 双机制，新增 `install.py` / `validate_skill.py` / `package_claudeai.py` 与 CI。版面 / 双交付 / 红涨绿跌沿用 V4。
- V4：ftShare + Wind 双连接器交叉核对 —— 已删除，不保留备份。

## License

MIT
