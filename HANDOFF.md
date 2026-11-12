# HANDOFF · 交接说明

> 本文档写给接手本仓库的 AI agent（或人类协作者）。读完这一份即可零上下文接手，无需追问历史。

## 1. 这是什么项目

**finance-daily-v5（金融日报 V5）**：一个 Claude Agent Skills 格式的技能包。用户对 agent 说「金融日报」等触发词，agent 采集公开市场数据，生成报刊风（暖纸底+金线+红涨绿跌）的金融市场要闻日报，双交付 HTML + 3x PNG 长图。

- 来源：从 WorkBuddy 平台的「金融日报V5」skill 移植（2026-11-12 导出），正文逻辑未改，仅标准化。
- 仓库：`C:\AIdocument\GitHub-cc-ds\skill-2\test\finance-daily-v5`（git 已初始化，分支 `main`，**无远端**）。
- 用户目标：**准备上传到 GitHub 公开**。README 中所有 `<你的用户名>` 占位符待替换为真实 GitHub 用户名/仓库地址。

## 2. 当前状态（2026-11-12）

- 2 个 commit：`aefe8d2` 标准化重构 → `fa39855` 跨宿主适配层。
- 工作区干净，无未提交改动，无远端，未推送。
- 14 个受 git 管理的文件，目录结构见 README「目录结构」一节。
- `test/_extracted/`（仓库外，位于 `skill-2/test/`）是原始 zip 的解压残留，仅作对照，**不要**纳入仓库。

## 3. 架构铁律（改代码前必读）

1. **SKILL.md 是唯一事实源**。`adapters/` 下 6 个文件全部由 `scripts/build_adapters.py` 从 SKILL.md 生成，文件头有 DO NOT EDIT 标记。**改正文永远改 SKILL.md，然后重新生成**，绝不手改 adapters/。
2. **frontmatter 白名单**：SKILL.md 的 YAML 头只允许 `name / description / license / compatibility / metadata / allowed-tools` 六个字段（claude.ai Skills 上传 API 硬校验，出现 `agent_created` 等私有字段会报错——历史上踩过这个坑）。当前用的是 `name, description, license, metadata`。
3. **正文能力声明式**：SKILL.md 正文不引用任何宿主专有工具名，只用「执行命令 / 检索网页 / 打开网页 / 读写文件」四类能力动词。加新流程步骤时同样不要写死工具名（如 WebSearch、present_files）。
4. **数据铁律不容放宽**（SKILL.md §2/§7/§9 反复强调）：取不到的数字一律撤下或标「待核」，禁止编造、禁止取平均、禁止用旧值回退。任何重构、降级、适配都不能弱化这条。
5. **路径约定**：Python 脚本在 `scripts/`，HTML 模板在 `assets/`。SKILL.md 和脚本 docstring 里的路径引用要同步（历史版本曾把脚本都放在 assets/，已全部迁到 scripts/）。

## 4. 跨宿主兼容设计（本项目核心特性）

| 宿主 | 适配文件 | 能力档位 |
|------|---------|---------|
| Claude Code / claude.ai | `SKILL.md` 原样（~/.claude/skills/ 或项目 .claude/skills/） | 完整版 |
| OpenAI Codex CLI | `adapters/AGENTS.md` | 完整版 |
| Gemini CLI | `adapters/GEMINI.md` | 完整版 |
| Qwen Code | `adapters/QWEN.md` | 完整版 |
| Cursor | `adapters/cursor-rules.mdc`（.cursor/rules/，带 frontmatter） | 完整版 |
| GPTs / Kimi / DeepSeek / GLM / 豆包 等纯对话型 | `adapters/system-prompt.md`（贴进系统提示词） | 只读版 |

- 降级档位定义在 SKILL.md §9：完整版 → 标准版（无打开网页）→ 行情版（无检索）→ 只读版（无命令）。**缺能力不等于可以编数**。
- 新增宿主适配：在 `scripts/build_adapters.py` 的 `ADAPTERS` 字典加条目，跑脚本即可。Cursor 的 `.mdc` 需 YAML frontmatter 在文件最前（脚本里已特殊处理）。

## 5. 常用命令

```bash
cd C:\AIdocument\GitHub-cc-ds\skill-2\test\finance-daily-v5

# 改 SKILL.md 后重新生成适配文件
python scripts/build_adapters.py

# 校验 adapters/ 与 SKILL.md 是否同步（接 CI / 提交前）
python scripts/build_adapters.py --check

# 行情脚本自检（纯标准库，零第三方依赖；已实测可用）
python scripts/fetch_public.py --date YYYY-MM-DD --out-dir ./raw

# 渲染 PNG（需 playwright + pillow）
pip install playwright pillow && playwright install chromium
python scripts/render.py <input.html> <output.png> [scale=3]
```

## 6. 已验证事项（截至本交接）

- ✅ `fetch_public.py` 实测跑通（2026-11-12）：A股/港股/美股(CNBC)/美债(财政部)/商品/汇率全部取到真实数据；深交所官方源当日失败被正确标记 `fail`（设计如此，agent 会改用新闻源补）；FRED 失败属可选交叉源，可跳过。
- ✅ 六个 adapters/ 文件正文与 SKILL.md §1 起逐字一致（程序化校验通过）。
- ✅ SKILL.md frontmatter 字段全部在白名单内，无宿主专有工具名残留。
- ⚠️ `render.py` 未实测渲染（依赖 playwright 未装）；其裁边逻辑依赖模板纸底色 `#f7f4ed`，改模板配色会破坏裁边。
- ⚠️ 乱码说明：`skill-2/test/_extracted/` 下两个文件名乱码的 md 是原 zip GBK 文件名导致（内容是「README_安装说明.md」和「打包说明_金融日报V5.md」），内容已无损失，不影响仓库。

## 7. 待办（接手后可做）

1. **推 GitHub**：`git remote add origin <URL> && git push -u origin main`；替换 README 与 `scripts/build_adapters.py` 里的 `<你的用户名>` 占位符。
2. （可选）GitHub Actions：跑 `build_adapters.py --check` 防 adapters 漂移；跑 `fetch_public.py` 做数据源可用性巡检。
3. （可选）`.mdc`/`AGENTS.md` 等适配文件如宿主有新约定（如 Cursor 新版规则格式），更新 `build_adapters.py` 后重新生成。
4. （可选）实测一次端到端：在装好 playwright 的环境跑完 Step 0~7，产出真实日报，验证 §5 渲染与 §6 双交付。

## 8. 联系上下文

- 用户中文交流，偏好直接执行、不过度确认；此前已授权在本 test 目录内创建文件与 git 操作。
- 原始 zip：`C:\WPS\Downloads\skills-export-20261112\finance-daily-v5.zip`（另有同名导出包含 WorkBuddy 原版，与本仓库无关）。
