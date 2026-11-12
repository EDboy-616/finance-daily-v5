# HANDOFF · 交接说明

> 写给接手本仓库的 AI agent（或人类协作者）。读完这一份即可零上下文接手，无需追问历史。
> 最近一次更新：2026-11-12（跨宿主适配层重做 + 校验/安装/打包脚本 + CI）。

## 1. 这是什么项目

**finance-daily-v5（金融日报 V5）**：一个 [Agent Skills 开放规范](https://agentskills.io/specification) 格式的技能包。用户对 agent 说「金融日报」等触发词，agent 采集公开市场数据，生成报刊风（暖纸底+金线+红涨绿跌）的金融市场要闻日报，双交付 HTML + 3x PNG 长图。

- 来源：从 WorkBuddy 平台的「金融日报V5」skill 移植（2026-11-12 导出），正文逻辑未改，仅标准化。
- 仓库：`C:\AIdocument\GitHub-cc-ds\skill-2\test\finance-daily-v5`（git 已初始化，分支 `main`，**无远端**）。
- 用户目标：准备上传到 GitHub 公开，但**明确要求暂不推送**（"你先别推，等我把本地活干完再说"）。所以：不要自行 `git remote add` 或 push。

## 2. 当前状态（2026-11-12 第二轮改造后）

- git 历史：`aefe8d2` 标准化重构 → `fa39855` 跨宿主适配层 → `55a9f8c` HANDOFF（本轮改动尚未提交）。
- 本轮新增：`scripts/validate_skill.py`、`scripts/install.py`、`scripts/package_claudeai.py`、`maintainer/prompt-slim.src.md`、`adapters/system-prompt-slim.md`、`.claude-plugin/marketplace.json`、`.github/workflows/verify.yml`、`.gitattributes`。
- `test/_extracted/`（仓库外，位于 `skill-2/test/`）是原始 zip 的解压残留，仅作对照，**不要**纳入仓库。
- 调研笔记（仓库外，别删）：`C:\AIdocument\GitHub-cc-ds\skill-2\test\_notes\agent-skills-conventions.md` —— 规范原文约束、46 个原生支持宿主的目录约定、各家上下文文件字符上限、可抄的 marketplace.json 实例，都在那里，别再重复调研。

## 3. 架构铁律（改代码前必读）

1. **SKILL.md 是唯一事实源**。`adapters/` 下 7 个文件全部由 `scripts/build_adapters.py` 从 SKILL.md 生成，文件头有 DO NOT EDIT 标记。**改正文永远改 SKILL.md，然后重新生成**，绝不手改 adapters/。
   - 唯一例外：`adapters/system-prompt-slim.md` 的源是 `maintainer/prompt-slim.src.md`（人工摘编，给放不下全文的对话宿主）。它由**覆盖率校验**保护：SKILL.md 里每个 `#rrggbb` 色值 + 每条铁律关键词都必须出现在摘编里，否则生成器报错。加新铁律时两处都要改。
2. **frontmatter 白名单**：只允许 `name / description / license / compatibility / metadata / allowed-tools` 六个字段（Agent Skills 规范；claude.ai 上传、Skills API、`package_skill.py` 会**硬错**，而 Claude Code 只是静默忽略——这个不对称是校验器必须把非规范键判 ERROR 的原因）。当前用 `name, description, license, compatibility, metadata`。`version` 不是规范字段，版本写在 `metadata.version` 且**必须加引号**。
3. **正文能力声明式**：正文不引用任何宿主专有工具名，只用「执行命令 / 检索网页 / 打开网页 / 读写文件」四类能力动词。`validate_skill.py` 有黑名单扫描（WebSearch/WebFetch/google_web_search/read_url/mcp__/`/skill:`/`$finance-daily` 等）。
   - 同理，**正文里不能用 Claude Code 专有的替换量**（`${CLAUDE_SKILL_DIR}`、`` !`cmd` ``、`@file`、`$ARGUMENTS`）—— 它们在其他宿主就是字面垃圾。需要绝对路径就写 `<SKILL_DIR>` 占位符 + §0 的探测规则。
4. **数据铁律不容放宽**（SKILL.md §2/§7/§9 反复强调）：取不到的数字一律撤下或标「待核」，禁止编造、禁止取平均、禁止用旧值回退。任何重构、降级、适配都不能弱化这条。
5. **路径约定**：脚本在 `scripts/`，HTML 模板在 `assets/`。正文里引用一律 `<SKILL_DIR>/scripts/...` 形式（宿主 CWD 通常是用户项目目录，不是 skill 目录）；`validate_skill.py` 会抓裸 `python scripts/...`。
6. **换行符**：所有生成物写 `newline="\n"`；`.gitattributes` 强制 LF，否则 Windows runner 上 `--check` 会误报漂移。

## 4. 跨宿主适配：两种机制（本项目核心特性）

关键结论（2026-11-12 查官方文档得出，别再推翻）：**AGENTS.md 规范里没有 skill 机制，且 Codex / Gemini / Qwen / Cursor 都不按触发词路由**（Codex 要 `$finance-daily-v5`，Gemini 要 `/skill:…`）。所以：

| 机制 | 实现 | 触发词自动生效？ | 代价 |
|------|------|----------------|------|
| **inject（注入式）** | 把 `adapters/<宿主>.md` 整篇写进该宿主常驻上下文文件（AGENTS.md / GEMINI.md / QWEN.md / CLAUDE.md / `.cursor/rules/*.mdc`） | ✅ 是 | 每会话固定 ~10k 字符 |
| **skill（原生 skills）** | 整个 skill 目录复制进宿主 skills 根 | ❌ 多数宿主需显式调用（Claude 除外） | 省上下文，可被宿主管理 |

两条都保留、都可装（`scripts/install.py`），因为「能自动跑」和「省上下文」是真实取舍，不是重复劳动。此前调研建议"只做复制、不做全文注入"，已按官方文档事实否决。

| 宿主 | inject 文件 | 原生 skills 目录 | 已知限制 |
|------|------------|-----------------|---------|
| Claude Code / claude.ai | `adapters/CLAUDE.md` | `.claude/skills/`、`~/.claude/skills/` | 唯一按 description 自动路由 |
| OpenAI Codex CLI | `adapters/AGENTS.md` | `.agents/skills/`、`~/.agents/skills/` | 无 `.codex/skills/`；`project_doc_max_bytes=32768`；全局与仓库 AGENTS.md 只取第一个命中 |
| GitHub Copilot / VS Code | `adapters/AGENTS.md` | `.github/skills/`、`~/.copilot/skills/` | 默认 8000 字符上限，本文件超了 |
| Gemini CLI | `adapters/GEMINI.md` | `.gemini/skills/`、`~/.gemini/skills/` | 上下文文件不自动执行动作 |
| Qwen Code | `adapters/QWEN.md` | `.qwen/skills/`、`~/.qwen/skills/` | QWEN.md 优先于 AGENTS.md |
| Cursor | `adapters/cursor-rules.mdc` | `.cursor/skills/` | 只加载 `.mdc`；`alwaysApply:false` 靠 description 命中 |
| 纯对话型（GPTs/Kimi/DeepSeek/豆包/GLM） | `adapters/system-prompt-slim.md`（2.3k）/ `system-prompt.md`（9.7k） | — | 只能手工粘贴 |

- 降级档位定义在 SKILL.md §9：完整版 → 标准版（无打开网页）→ 行情版（无检索）→ 只读版（无命令）。**缺能力不等于可以编数**。
- 新增宿主：`build_adapters.py` 的 `ADAPTERS` 加条目（生成适配文件）+ `install.py` 的 `HOSTS` 加条目（落点路径）。两处都要改，`validate_skill.py` 会检查 HOSTS 引用的文件是否存在。

## 5. 常用命令

```bash
cd C:\AIdocument\GitHub-cc-ds\skill-2\test\finance-daily-v5

# 改 SKILL.md 后：重新生成 + 自检（提交前必跑）
python scripts/build_adapters.py
python scripts/validate_skill.py          # --strict 把 WARN 也当失败

# 只校验是否漂移（CI 用）
python scripts/build_adapters.py --check

# 装进宿主
python scripts/install.py --list
python scripts/install.py --target all --dry-run
python scripts/install.py --target agents --mode inject --project <你的项目目录>
python scripts/install.py --target claude --mode skill --global

# 打 claude.ai 上传包（根 = finance-daily-v5/ 文件夹）
python scripts/package_claudeai.py --dry-run
python scripts/package_claudeai.py

# 行情脚本自检（纯标准库，零第三方依赖；已实测可用）
python scripts/fetch_public.py --date YYYY-MM-DD --out-dir ./raw

# 渲染 PNG（需 playwright + pillow，本机已装 chromium）
python scripts/render.py <input.html> <output.png> [scale=3]
```

## 6. 已验证事项（截至本交接）

- ✅ `fetch_public.py` 实测跑通（2026-11-12）：A股/港股/美股(CNBC)/美债(财政部)/商品/汇率全部取到真实数据；深交所官方源当日失败被正确标记 `fail`（设计如此，agent 会改用新闻源补）；FRED 失败属可选交叉源，可跳过。
- ✅ `build_adapters.py` / `build_adapters.py --check` / `validate_skill.py` 全部通过（7 个适配文件、12 项 ✓、2 个 WARN 均为 Copilot 8000 字符上限的已知提示）。
- ✅ `install.py` 实测（2026-11-12，在 `test/_install_probe*/` 隔离目录）：inject 新建 / 追加 / 替换受管块均幂等，块外用户文本保留；skill 模式只复制 `SKILL.md + scripts/(仅 fetch_public.py、render.py) + assets/ + LICENSE`（维护脚本不进安装副本），重复跑无 `--force` 正确拒绝（exit 1）；`--project` 指定项目根生效；`--target all` 对共用落点去重。
- ✅ `render.py` 端到端验证过：拿 `assets/market_news_template.html` 改日期渲染出 3240×8631 的 3x PNG，裁边正常、13 个板块与 ticker 十卡都在。playwright + Pillow 已在本机装好（chromium-1248 在 `%LOCALAPPDATA%\ms-playwright`）；`file:///" +` 拼接的旧 bug 已修为 `Path.resolve().as_uri()`，validator 有回归守卫。
- ⚠️ **未做真实日报端到端**：模板渲染链路已验证，但 Step 0~7 的完整流程（含检索新闻、填内容）尚未串起来出过一张真图。
- ⚠️ `install.py` 的宿主路径表来自官方文档 + skills.sh / skillfish / ruler 三家交叉核对，但未逐台实测；OpenCode / TRAE / Kiro / Roo / Goose / CodeBuddy / Antigravity 七家沿用社区约定。
- ⚠️ `claude plugin validate .` 未跑过（本机 `gh` 未登录、未装 claude CLI）；`.claude-plugin/marketplace.json` 结构按官方实例写，`validate_skill.py` 只做了结构自检。
- ⚠️ 乱码说明：`skill-2/test/_extracted/` 下两个文件名乱码的 md 是原 zip GBK 文件名导致（内容是「README_安装说明.md」和「打包说明_金融日报V5.md」），内容已无损失，不影响仓库。

## 7. 待办（接手后可做）

1. **端到端实跑一次**（最高价值）：跑完 Step 0~7 出真实日报，验证渲染裁边与双交付。裁边逻辑依赖模板纸底色 `#f7f4ed`，改模板配色会破坏裁边。
2. **推 GitHub**（用户明确暂缓，等他说可以再做）：`git remote add origin <URL> && git push -u origin main`。README 里的克隆地址已按 `EDboy-628/finance-daily-v5` 写好，仓库建好后无需再改；若要换名，`git remote` 与 README 两处同步。
3. 可选：`claude plugin validate .` 实跑一次（需装 claude CLI）；`npx skills add EDboy-628/finance-daily-v5` 验证 skills.sh 能发现本仓库根 SKILL.md。
4. 可选：CI 里的 `fetch_public.py` 数据源巡检（现在是 smoke 只跑 `--help`，没联网，避免网络抖动误报）。

## 8. 联系上下文

- 用户中文交流，偏好直接执行、不过度确认；此前已授权在本 test 目录内创建文件与 git 操作。**但推送 GitHub 必须等他明确同意。**
- 原始 zip：`C:\WPS\Downloads\skills-export-20261112\finance-daily-v5.zip`（另有同名导出包含 WorkBuddy 原版，与本仓库无关）。
- 本轮调研笔记：`C:\AIdocument\GitHub-cc-ds\skill-2\test\_notes\agent-skills-conventions.md`。
