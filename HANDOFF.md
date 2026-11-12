# HANDOFF · 交接说明

> 写给接手本仓库的 AI agent（或人类协作者）。读完这一份即可零上下文接手，无需追问历史。
> 最近一次更新：2026-11-12（跨宿主适配层重做 + 校验/安装/打包脚本 + CI）。

## 1. 这是什么项目

**finance-daily-v5（金融日报 V5）**：一个 [Agent Skills 开放规范](https://agentskills.io/specification) 格式的技能包。用户对 agent 说「金融日报」等触发词，agent 采集公开市场数据，生成报刊风（暖纸底+金线+红涨绿跌）的金融市场要闻日报，双交付 HTML + 3x PNG 长图。

- 来源：从 WorkBuddy 平台的「金融日报V5」skill 移植（2026-11-12 导出），正文逻辑未改，仅标准化。
- 本地：`C:\AIdocument\GitHub-cc-ds\skill-2\test\finance-daily-v5`（分支 `main`）。
- 远端：`https://github.com/EDboy-616/finance-daily-v5`（public，`origin` 已配置）。用户已授权推送（"推吧 直接用我的浏览器"），**后续改动默认本地提交 + 推送**；若用户说"先别推"则以他为准。

## 2. 当前状态（2026-11-12 第三轮：README 重做）

- git 历史：`aefe8d2` 标准化重构 → `fa39855` 跨宿主适配层 → `55a9f8c` HANDOFF → `6ed3a21` 长度回填 → `b529efc` CI 两坑 → `e175000` 文档 → `46ca522` 作者归属修正 → `6850941` README 重做 + `docs/` + `make_docs_images.py` → `bb9a135` 宿主表 br 换行（远端 `main` 同点，CI 双平台绿）。
- 本轮新增：`docs/`（`emblem.svg`、`banner.png`、`social-preview.png`、`preview-top/detail/full.png`）+ `maintainer/make_docs_images.py`（生成 README 用图的维护脚本，不随 skill 安装）+ README 全面重写。
- 更早一轮新增：`scripts/validate_skill.py`、`scripts/install.py`、`scripts/package_claudeai.py`、`maintainer/prompt-slim.src.md`、`maintainer/repo.txt`、`adapters/system-prompt-slim.md`、`.claude-plugin/marketplace.json`、`.github/workflows/verify.yml`、`.gitattributes`。
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

# 重新生成 README 用图（徽标 / 横幅 / 三张预览图；需 playwright + pillow）
python maintainer/make_docs_images.py
```

### README 用图的约束（改 README 前必读）

- `docs/` 下 6 个文件全部由 `maintainer/make_docs_images.py` 生成，**不要手改 PNG/SVG**；改版面就改脚本里的 HTML 模板。
- 预览图的渲染源是 `assets/market_news_template.html` + 样例数据，所以它永远反映真实版面；换模板配色后必须重跑一次，否则 README 里的图和实际产出对不上。
- 徽标几何（`_stalk()` 的麦粒旋转、`emblem_svg()` 的 viewBox）是反复调到 320/96/44/28px 都清晰才定稿的，**改之前先在四档尺寸下看一遍**。
- 中间 HTML 一律写 `tempfile.mkdtemp()`，别写进仓库 —— `.gitignore` 有 `*.html` 规则（只放行模板），落地文件会被静默忽略，容易以为生成成功。

## 6. 已验证事项（截至本交接）

- ✅ `fetch_public.py` 实测跑通（2026-11-12）：A股/港股/美股(CNBC)/美债(财政部)/商品/汇率全部取到真实数据；深交所官方源当日失败被正确标记 `fail`（设计如此，agent 会改用新闻源补）；FRED 失败属可选交叉源，可跳过。
- ✅ `build_adapters.py` / `build_adapters.py --check` / `validate_skill.py` 全部通过（7 个适配文件、12 项 ✓、2 个 WARN 均为 Copilot 8000 字符上限的已知提示）。
- ✅ `install.py` 实测（2026-11-12，在 `test/_install_probe*/` 隔离目录）：inject 新建 / 追加 / 替换受管块均幂等，块外用户文本保留；skill 模式只复制 `SKILL.md + scripts/(仅 fetch_public.py、render.py) + assets/ + LICENSE`（维护脚本不进安装副本），重复跑无 `--force` 正确拒绝（exit 1）；`--project` 指定项目根生效；`--target all` 对共用落点去重。
- ✅ `render.py` 端到端验证过：拿 `assets/market_news_template.html` 改日期渲染出 3240×8631 的 3x PNG，裁边正常、13 个板块与 ticker 十卡都在。playwright + Pillow 已在本机装好（chromium-1248 在 `%LOCALAPPDATA%\ms-playwright`）；`file:///" +` 拼接的旧 bug 已修为 `Path.resolve().as_uri()`，validator 有回归守卫。
- ⚠️ **未做真实日报端到端**：模板渲染链路已验证，但 Step 0~7 的完整流程（含检索新闻、填内容）尚未串起来出过一张真图。
- ✅ **已推送到 https://github.com/EDboy-616/finance-daily-v5（public，默认分支 main）**，CI `verify` 在 ubuntu-latest 与 windows-latest 双平台全绿；`dist/*.zip` 作为 artifact 留档（约 27 KB）。
- ✅ README 用图已生成并逐张目视确认（`docs/` 6 个文件，`make_docs_images.py` exit 0）；README 已用 GitHub 官方 markdown API 渲染后截图核对，修掉四处真实版面缺陷：① 宿主表 4 列导致「该宿主的坑」列被挤出容器 → 缩成 3 列 + 表下 6 条 bullet；② CJK 制表符按双宽渲染导致目录树 `#` 注释错位 → 改用纯 ASCII 连接符 `|--` / `` `-- `` + `ljust`；③ 左右双栏把细节图压到 430px → 改整宽上下排列 + 13 板块表变 4 列紧凑双栏；④ 宿主表「原生 skills」列用 ` · ` 分隔被挤成三行 → 改 `<br>`。
- ⚠️ `install.py` 的宿主路径表来自官方文档 + skills.sh / skillfish / ruler 三家交叉核对，但未逐台实测；OpenCode / TRAE / Kiro / Roo / Goose / CodeBuddy / Antigravity 七家沿用社区约定。
- ⚠️ `claude plugin validate .` 未跑过（本机 `gh` 未登录、未装 claude CLI）；`.claude-plugin/marketplace.json` 结构按官方实例写，`validate_skill.py` 只做了结构自检。
- ⚠️ 乱码说明：`skill-2/test/_extracted/` 下两个文件名乱码的 md 是原 zip GBK 文件名导致（内容是「README_安装说明.md」和「打包说明_金融日报V5.md」），内容已无损失，不影响仓库。

## 6b. CI 踩过的两个坑（已修，别改回去）

两个坑根因相同：**生成结果依赖运行环境，等于不可复现**。

1. **适配层漂移误报**：`detect_repo_slug()` 原本读 `git remote get-url origin`。本地没加 remote 时生成一版，CI checkout 后带 remote 生成另一版，`--check` 在 CI 必然报「7 个文件全部漂移」。现在唯一来源是签入仓库的 `maintainer/repo.txt`（一行 `EDboy-616/finance-daily-v5`），`FINANCE_DAILY_REPO` 环境变量仅作临时覆盖。**换仓库地址要同时改 repo.txt 和 README 克隆地址。**
2. **Windows stdout 编码**：`validate_skill.py` 打印 `✓` 时 runner 的 cp1252 抛 `UnicodeEncodeError`。`build_adapters.py` / `validate_skill.py` / `render.py` 现在开头都 `reconfigure(encoding="utf-8", errors="replace")`。新脚本必须照做，否则 windows-latest 会挂。
3. **提交作者邮箱里的数字 ID 必须是该账号自己的**：本机曾有 EDboy-628 与 EDboy-616 两个 GitHub 账号，noreply 邮箱前缀的 `137130507` 是 628 的 ID。配成 `137130507+EDboy-616@users.noreply.github.com` 时 GitHub 按前缀 ID 匹配，把提交记到 **EDboy-628** 名下（网页贡献者列表串号）。616 的真实 ID 是 **354708082**，正确写法 `354708082+EDboy-616@users.noreply.github.com`。查真实 ID：`GET /users/<login>` 的 `id` 字段，或 `GET /user` 看 token 属于谁。

另外两个**不是代码问题**的假失败，别改 workflow：

- **Windows runner 排队超时被取消**：job 在队列里超过 15 分钟没被 runner 领走，GitHub 自动 `cancelled`，整个 run 记 failure，但 job 内 8 个 step 全是 success。2026-11-12 遇到两次（一次排 295 秒才起，一次直接超时取消）。处理：`POST /repos/{o}/{r}/actions/runs/{id}/rerun-failed-jobs` 重跑即可。
- **`git push` 偶发 502**：`fatal: unable to access ... error: 502`，等几秒重试即可，不要动配置。

## 7. 待办（接手后可做）

1. **端到端实跑一次**（最高价值）：跑完 Step 0~7 出真实日报，验证渲染裁边与双交付。裁边逻辑依赖模板纸底色 `#f7f4ed`，改模板配色会破坏裁边。
2. 可选：`claude plugin validate .` 实跑一次（需装 claude CLI）；`npx skills add EDboy-616/finance-daily-v5` 验证 skills.sh 能发现本仓库根 SKILL.md。
3. 可选：CI 里的 `fetch_public.py` 数据源巡检（现在是 smoke 只跑 `--help`，没联网，避免网络抖动误报）。
4. 可选：给仓库加 topics（`agent-skills`、`claude-skills`、`finance`）提升可发现性。

## 8. 联系上下文

- 用户中文交流，偏好直接执行、不过度确认；此前已授权在本 test 目录内创建文件与 git 操作，并于 2026-11-12 明确同意推送 GitHub（已完成）。**后续改动默认本地提交 + 推送；若用户说"先别推"则以他为准。**
- 仓库：`https://github.com/EDboy-616/finance-daily-v5`（public）。注意本机 `git config` **全局**身份仍是 EDboy-628，**本仓库 local 身份已改为 EDboy-616 / `354708082+EDboy-616@users.noreply.github.com`**；GitHub 凭据管理器里两个账号的 token 都在，推送用的是 EDboy-616 的（scope: gist/repo/workflow）。历史前 6 个提交作者仍是 EDboy-628（上一轮会话的真实身份，未改写）。
- 原始 zip：`C:\WPS\Downloads\skills-export-20261112\finance-daily-v5.zip`（另有同名导出包含 WorkBuddy 原版，与本仓库无关）。
- 本轮调研笔记：`C:\AIdocument\GitHub-cc-ds\skill-2\test\_notes\agent-skills-conventions.md`。
