<!-- DO NOT EDIT · 由 scripts/build_adapters.py 从 SKILL.md v5.0.0 自动生成。改内容请改源文件后重跑该脚本；--check 会抓出漂移。 -->

# finance-daily-v5 · CLAUDE.md 适配（Claude Code / Agent SDK 项目级兜底）

> 由 SKILL.md v5.0.0 生成 · 整篇 10011 字符

## 安装

1. **注入式（触发词自动生效的唯一途径）**：把本文件整篇放到 `CLAUDE.md（项目根）或 ~/.claude/CLAUDE.md`。
2. **原生 skills（按需加载，省上下文）**：把整个仓库复制为 `.claude/skills/finance-daily-v5/`，由宿主按 description 自动加载或按各家语法显式调用。
3. **通用安装器**：`npx skills add EDboy-616/finance-daily-v5`，GitHub CLI 也可 `gh skill install EDboy-616/finance-daily-v5`（v2.90+，装前可 `gh skill preview` 审阅）；或 `python scripts/install.py --list` 看全部目标。

## 触发

触发：对话里说「金融日报」「市场要闻」等触发词。

## 本宿主须知

- **Claude Code 的首选不是本文件**：把仓库复制成 `.claude/skills/finance-daily-v5/`，Claude 会按 SKILL.md 的 description 自动判定何时读全文，正文不常驻上下文。本文件只给不想建 skills 目录的场景兜底。
- Agent SDK 建议 CLAUDE.md 保持在 10k tokens 内（本文件约 5k tokens，安全）。

## 能力自查

开始前先确认宿主具备哪些能力（执行命令 / 检索网页 / 打开网页 / 渲染 PNG），按正文 §9 的降级档位执行；缺能力不等于可以编数。

---

-- 正文开始（SKILL.md 正文逐字复制，仅去掉其文件级维护注释）--

# 金融日报 V5

## 用途

生成每日「金融市场要闻日报」信息图，采用**报刊风（editorial / 年报风）**版面：暖纸底 `#f7f4ed` + 深墨蓝 `#1c2230` + 金线 `#b08a2e` + 红涨绿跌，读报式多栏排版。

面向市场公开信息，**绝不加入用户个人持仓、自选品种标注等个性化内容**。页面内**禁止出现任何风格/流程自述**（如"本日报延续某页""套用 V5 模板""见并表页"等），只放信息本身。

**V5 相对 V4 的根本变化（2026-09-29 改造，用户拍板）**：
- **砍掉全部 MCP 连接器依赖**（ftShare / 万得 Wind / 通达信问小达 全部不再使用），改为**公开权威源**取数。理由：连接器频繁掉线、授权麻烦、问小达按次扣积分；公开源更快捷、可复核、零成本。
- **硬行情走脚本**（`scripts/fetch_public.py`，纯标准库，无第三方依赖）：一次跑出 A股/港股/美股/美债/商品/汇率全部点位。
- **新闻与交叉核对走「检索网页 + 打开网页」**：新华社、证券时报、上海证券报、中国证券报、东方财富、新浪财经、财联社、第一财经、央广网、中新经纬、上交所/深交所/港交所官网、央行、美联储 H.15、AP News 等。
- 版面样式、双交付（HTML + PNG）、红涨绿跌、自审清单**沿用 V4**，不变。

## 触发词

金融市场要闻 / 市场要闻 / 要闻更新 / 金融要闻日报 / 今天的市场要闻 / 金融日报

---

## §0 路径基准（跨宿主第一步，别跳过）

- 本文件所在目录记为 `<SKILL_DIR>`（即包含本 SKILL.md 的文件夹）。**宿主「执行命令」时的工作目录通常是用户的项目目录，不是 `<SKILL_DIR>`**，所以下文所有脚本与模板都必须写成 `<SKILL_DIR>/...` 的完整路径，不要假设相对路径能命中。
- 定位 `<SKILL_DIR>`：优先用宿主报出的 skill 路径；否则按安装位置逐个探测（`.claude/skills/finance-daily-v5`、`~/.claude/skills/finance-daily-v5`、`.agents/skills/finance-daily-v5`、`~/.agents/skills/finance-daily-v5`），仍找不到就按文件名 `market_news_template.html` 检索。
- **产物一律写到当前工作目录**：行情 JSON → `./raw/`，成稿 HTML/PNG → `./outputs/`。不要往 `<SKILL_DIR>` 里写（安装目录可能只读，也不该被一次运行污染）。
- `scripts/render.py` 的 HTML 入参相对/绝对都可（内部会解析成绝对 `file://` URI）；输出 PNG 路径按当前工作目录解析，父目录不存在会自动创建。

---

## §1 数据源清单（白名单，按需取用）

### A. 脚本直连的公开行情接口（硬数据主力，`scripts/fetch_public.py`）

| 指标 | 接口 | 实测状态（2026-09-29） |
|------|------|----------------------|
| A股指数 + 成交额 | 新浪 `hq.sinajs.cn/list=sh000001,sz399001,...` | ✅ 可用 |
| 港股指数 | 新浪 `hq.sinajs.cn/list=rt_hkHSI,rt_hkHSCEI,rt_hkHSTECH` | ✅ 可用 |
| 美股三大指数 | CNBC `quote.cnbc.com/quote-html-webservice/restQuote/...symbols=.DJI/.SPX/.IXIC` | ✅ 可用（逐个请求） |
| 美债收益率曲线 | 美国财政部 `home.treasury.gov/.../daily-treasury-rates.csv/{年}/all` | ✅ 官方 |
| 深市成交额（官方复核） | 深交所 `szse.cn/api/report/ShowReport/data?CATALOGID=1803_sczm&txtQueryDate=YYYY-MM-DD` | ✅ 官方 |
| 内盘商品期货（主力连续） | 新浪 `hq.sinajs.cn/list=nf_AU0,nf_CU0,...` | ✅ 可用 |
| 外盘商品 | 新浪 `hq.sinajs.cn/list=hf_GC,hf_SI,hf_CL,hf_OIL,hf_XAU,hf_CAD` | ✅ 可用 |
| 汇率 / 美元指数 | 新浪 `fx_susdcny,fx_susdcnh,fx_susdjpy,fx_seurusd,DINIW` | ✅ 可用 |
| 美股复核（官方 T-1） | 圣路易斯联储 FRED `fredgraph.csv?id=SP500` | ⚠️ 可选，部分网络被拒 |
| 交叉复核 | 东方财富 `push2.eastmoney.com/api/qt/ulist.np/get` | ⚠️ 可选，WAF 常拒脚本 |

运行：
```bash
python "<SKILL_DIR>/scripts/fetch_public.py" --date YYYY-MM-DD --out-dir ./raw
```
输出 `raw/market_YYYYMMDD.json` + 控制台摘要。每个字段带 `src`/`status`；**失败的源只标 `fail`，绝不编造、绝不回退旧值**。

### B. 新闻与政策（检索网页 / 打开网页）

| 类别 | 权威源 |
|------|--------|
| 通讯社/党媒 | 新华社 news.cn、央广网 cnr.cn、人民日报 people.com.cn |
| 证券专业媒体 | 证券时报 stcn.com、上海证券报 cnstock.com、中国证券报 cs.com.cn、证券日报 zqrb.cn、财联社 cls.cn、第一财经 yicai.com、中新经纬 jwview.com |
| 门户财经 | 东方财富 eastmoney.com、新浪财经 finance.sina.com.cn、同花顺 10jqka.com.cn |
| 交易所/监管（官方） | 上交所 sse.com.cn、深交所 szse.cn、港交所 hkex.com.hk、证监会 csrc.gov.cn、央行 pbc.gov.cn、外汇局 safe.gov.cn、统计局 stats.gov.cn、财政部 mof.gov.cn |
| 海外 | AP News apnews.com、Reuters、CNBC、Bloomberg、FT、Nikkei、美联储 federalreserve.gov（H.15 每日收益率）、ECB、BIS |
| 期货 | 上期所 shfe.com.cn、大商所 dce.cn、郑商所 czce.com.cn、中金所 cffex.com.cn、广期所 gfex.com.cn |

---

## §2 取数流程（按顺序执行）

### Step 0 · 定日期与口径
- 用系统当日日期作为「日报日期」。A股/港股/商品用当日收盘；美股用**最近一个已收盘交易日**（美东 16:00 后才是当日收盘，之前是盘中）。
- 非交易日（周末/节假日）：A股/港股沿用最近交易日收盘，并在 dateline 注明"数据截至 X 月 X 日收盘"。

### Step 1 · 跑脚本取硬行情（必做，1 次；需宿主具备「执行命令」能力）
```bash
python "<SKILL_DIR>/scripts/fetch_public.py" --date <YYYY-MM-DD> --out-dir ./raw
```
- 看控制台：若有 `失败源(必须补)`，该指标必须改用新闻源或「打开网页」定点补，禁止猜数。
- `可选交叉源未取到(可跳过)` 可忽略（FRED / 东财）。

### Step 2 · 网页检索新闻（6 个主题，各 1 次，必带 `freshness=d1`；需宿主具备「检索网页」能力，没有时见 §9 降级策略）

| # | 搜索意图 | 覆盖板块 |
|---|---------|---------|
| 1 | `{日期} A股收盘 三大指数 两市成交额 涨停家数 领涨领跌板块` | 头版 + 行业扫描 + 资金 |
| 2 | `{日期} 央行 公开市场操作 逆回购 净投放 流动性 Shibor 国债收益率` | 国内宏观 + 债市 |
| 3 | `stock market close Dow S&P Nasdaq {英文日期} Federal Reserve` | 国际·美股与央行 |
| 4 | `{日期} 国内商品期货收盘 黄金 原油 有色金属 涨跌` | 商品与期货 |
| 5 | `{日期} 政策 监管 上市公司 中报 业绩 IPO` | 公司与中报 + 政策 |
| 6 | `{日期} 人民币汇率 美元指数 美债收益率 美联储` | 汇率与外汇 + 央行 |

> 跨日/索引滞后时改用 `freshness=d2`，但**必须逐条核对稿件日期是否为目标日**，不是则丢弃。

### Step 3 · 打开权威站点复核（2~4 次，**核心数字必做**；需宿主具备「打开网页/抓取正文」能力）
对 Step 1/Step 2 拿到的**头版关键数字**挑 2~4 个做定点复核，优先顺序：
1. 交易所/监管官网（上交所、深交所、央行、美联储 H.15）→ 最权威
2. 新华社 / 证券时报 / 上海证券报 → 国内权威
3. AP News / CNBC → 海外

**必复核项**：三大指数收盘点位、两市成交额、美股三大指数、10Y 美债、人民币中间价或离岸价、现货黄金/WTI。

### Step 4 · 交叉核对矩阵（写入数据说明前先自检）

| 项目 | 主源 | 复核源 | 一致性要求 |
|------|------|--------|-----------|
| 沪指/深成/创业板 | 脚本(新浪) | 新闻通稿 | 点位一致、涨跌幅 ≤0.02pct 差 |
| 两市成交额 | 脚本(新浪 沪+深) | 深交所官方 + 新闻 | 脚本深市 vs 官方偏差 >0.5% 须在数据说明标注（两源口径本就略异） |
| 恒生指数 | 脚本(新浪 rt_hk) | 新闻 / 港交所 | 一致 |
| 美股三大 | 脚本(CNBC) | 新闻通稿 | 一致；注意 `curmktstatus`（REG_MKT=盘中，须标注"截至 X 时盘中"） |
| 10Y/2Y 美债 | 财政部官方 CSV | Fed H.15 / 新闻 | 一致；CSV 为 T-1 发布，标注日期 |
| 人民币 | 脚本(新浪) | 央行中间价 / 中国货币网 / 新闻 | 一致 |
| 商品 | 脚本(新浪 内盘+外盘) | 交易所官网 / 新闻 | 一致 |

**冲突处理铁律**：两源不一致 → **不编造、不取平均**，写"X 源报 A，Y 源报 B（待核）"或只写区间；若均不可得 → 该指标从 ticker 撤下，改在正文定性表述，并在数据说明注明"该指标当日未获可复核数据"。

### Step 5 · 填模板 → Step 6 · 渲染 → Step 7 · 双交付（见 §4~§6）

---

## §3 内容组织（层级分明，沿用 V4）

1. **价格速览条（ticker）**：头版上方，10 个等宽卡（上证/深成/创业板/两市成交/黄金/WTI/道指/标普/美元指数或比特币/10Y美债），红涨绿跌。核心点位必须已交叉复核。
2. **头版 FRONT PAGE**：左=主稿（大标题+导语+2 段含关键数字）；右=「今日要点 TOP5」侧栏（优先放已复核的精确数字）。
3. **国内·宏观与政策**：流动性与货币（央行净投放、DR007、Shibor）/ 政策与产业。
4. **国际·市场与央行**：美股与资产 / 央行与债市（FED、美债、日银、ECB）。
5. **汇率与外汇 FX**：人民币 / 美元与主要货币。**此板块不得遗漏**。
6. **行业扫描 SECTORS**：领涨/领跌/题材三栏，附涨跌幅。
7. **商品与期货 COMMODITIES**：内盘收盘表 / 外盘与持仓。
8. **资金流向 FLOWS**：融资余额、主力净流入、南向（北向自 2024 起停止披露净额，注明）。
9. **公司与中报 CORPORATES**：业绩亮点 / 新股与 IPO。
10. **机构观点 STREET VIEWS**：券商/外资观点（须带机构名）。
11. **今日关注 / 日历 WATCH**：事件 / 风险提示。
12. **数据说明（note-box，必填）**：披露当日本期实际数据源与复核情况 + 不构成投资建议。
13. **页脚 foot**：生成时间。

**数据说明（note-box）措辞模板**（按实际用到的源改，不要照抄）：
> 本期硬行情由公开接口采集：A股与港股指数、内外盘商品及汇率取自新浪财经公开行情接口，美股三大指数取自 CNBC 公开报价，美债收益率取自美国财政部每日收益率曲线（官方），深市成交额经深圳证券交易所官方数据复核；新闻与政策要闻经新华社/证券时报/上海证券报/东方财富/AP News 等多源交叉核对。美股为美东时间 X 时盘中价（未收盘）。仅供信息参考，不构成投资建议。

---

## §4 渲染模板

模板：`<SKILL_DIR>/assets/market_news_template.html`（V5 沿用 V4 报刊风，含响应式 @media + ticker + 全部 section 结构，顶部注释已更新为 V5）。
**用法**：复制模板 → 改头部日期/数据时间 → 替换 ticker 十卡 → 替换头版主稿+TOP5 → 替换各 section 的 `.news-col` / `.sector` / `.tbl` → 更新 note-box 数据源措辞与 foot 时间。

**样式铁律（勿改）**：
- 色板：纸 `#f7f4ed` / 墨 `#1c2230` / 线 `#d9d0bd` / 金 `#b08a2e` / 涨红 `#b23b2e` / 跌绿 `#1e7a52` / 卡 `#fffdf8`。
- 报头：4px double 墨线顶 + 居中大标题（衬线 46px）+ 金色 kicker 英文刊头。
- 标题金色细线 + 英文小标（sec-en）；卡片浅纸白底 + 金左边线。
- 红涨绿跌（中国习惯）：+ 用红 `#b23b2e`，− 用绿 `#1e7a52`。
- 字号：头版主稿 23 / 正文 12.5-13.5 / 行高 1.55；数字用衬线加粗。

---

## §5 渲染出 PNG（Playwright，默认 3x）

```bash
python "<SKILL_DIR>/scripts/render.py" <input_html> <output_png>      # 默认 3x
python "<SKILL_DIR>/scripts/render.py" <input_html> <output_png> 4    # 更高清
python "<SKILL_DIR>/scripts/render.py" <input_html> <output_png> 2    # 降体积
```

逻辑：`device_scale_factor=3`、viewport 1080×2400 → full_page 截图 → Pillow 按内容 bbox 裁上下空白 + 40px 安全边距（背景比对色 `#f7f4ed` 与模板纸底对齐）。

⚠️ 无 Playwright 时：`pip install playwright pillow` → `playwright install chromium`。Edge headless 已弃用（静默失败）。

输出命名：`outputs/market_news_YYYYMMDD.png`（与同名 HTML 并列）。

---

## §6 交付规范（双交付）

**同时交付 HTML 与 PNG**（HTML 在前）：给出两个绝对路径并打开 HTML 预览：
- HTML：本地绝对路径（自动网页预览）。
- PNG：本地绝对路径（3x 高清长图）。
- 回复附一句话快照时间 + 头版要点速览（≤5 行），不输出长表格。

---

## §7 禁区与自审清单

**禁区**：
- 不得使用任何 MCP 连接器取数（ftShare / Wind / 问小达 / TDX 均已退出本 skill）。
- 不得编造任何未取到的数字；不得用"约""大概"糊弄 ticker 点位。
- 不得在页面出现风格/流程自述、不得出现个人持仓/自选标注。

**自审（每次生成后逐条过）**：
1. ticker 十个卡的每个数字，是否都有脚本或 ≥2 个新闻源支撑？
2. 美股是否注明盘中/收盘与时点？
3. 汇率 FX 板块是否缺失？
4. 数据说明是否如实披露本期实际源（含失败的源）？
5. 红涨绿跌是否符合中国习惯？
6. 信息密度是否够（国内外 + 多行业 + 期货 + 资金 + 机构 + 日历）？

## §8 已知坑（实测，别踩）

- **东财 push2 与 FRED 在部分网络环境（本地代理/强制 HTTP2）会被拒**：Python urllib 报 `RemoteDisconnected`、Windows curl.exe 报 `schannel: server closed abruptly`。脚本已把它们降级为可选交叉源，失败不影响主流程；**不要反复重试**，改用新闻源或「打开网页」。
- **美股 `curmktstatus=REG_MKT` = 盘中**：美东 16:00 前取到的都是盘中价，写稿必须标注"截至 X 时盘中"，不得写成收盘。
- **新浪深市成交额 ≠ 深交所官方口径**：实测偏差约 0.1%~0.2%（成分 vs 全市场），属正常；>0.5% 才需在数据说明标注。
- **财政部收益率曲线为 T-1 发布**：当日美债收益率要次一工作日才出，写稿标注其日期（如"9/28 官方值"）。
- **新浪 `int_dji/int_nasdaq/int_sp500` 是陈旧序列，禁止用于美股**（实测点位与真实值差 20%+）。美股只信 CNBC + 新闻双源。
- **非交易日**：脚本对 A股/港股会返回上一交易日数据或空；`szse_official` 可能抛"未找到股票行"——属正常，按最近交易日写稿即可。
- **问小达/积分类接口一律不用**：本 skill 已完全零积分。

---

## §9 宿主能力要求与降级策略（跨宿主通用）

本 skill 设计为**能力声明式**：正文只依赖「执行命令 / 检索网页 / 打开网页 / 读写文件」四类通用能力，不绑定任何宿主专有工具名。各宿主按自己拥有的能力执行，缺什么按下面降级，**缺能力不等于可以编数**。

| 宿主能力 | 满足时 | 缺失时降级策略 |
|---------|--------|---------------|
| 执行命令（跑 fetch_public.py） | 硬行情一次取齐 | 改用「检索网页 + 打开网页」逐项取数；再没有 → 全部板块按下方「无检索」处理 |
| 检索网页（搜索类工具） | 6 主题新闻采集 | 用「打开网页」直接访问 §1-B 权威源首页/栏目页找当日要闻 |
| 打开网页（抓取/浏览器类） | 权威站点定点复核 | 跳过定点复核，新闻数字须 ≥2 个独立检索结果一致才可上 ticker |
| 渲染依赖（playwright+pillow） | 双交付 HTML+PNG | 只交 HTML，注明"未渲染 PNG（缺 playwright）"；**不要**改用其他截图工具硬渲 |

**降级档位**（按能力从高到低）：
1. **完整版**（命令+检索+打开+渲染）：全流程，双交付。
2. **标准版**（命令+检索，无打开网页）：新闻数字 ≥2 源一致才可用；数据说明注明"未经官网定点复核"。
3. **行情版**（仅命令，无检索）：只出 ticker + 商品表 + 汇率 + 美债等脚本数据板块，新闻类板块标注"本环境无检索能力，未采集新闻"，并在 dateline 写明「纯行情版」。
4. **只读版**（无命令，纯对话宿主如 GPTs/Kimi/豆包）：告知用户先在 skill 安装目录（或本仓库根目录）跑 `python scripts/fetch_public.py`，把 `raw/market_YYYYMMDD.json` 内容（或控制台摘要）粘贴回来，模型基于粘贴数据填模板产出 HTML 文本；新闻部分仅当宿主自带联网检索时才写，否则同档位 3 处理。

**铁律不随降级放宽**：任何档位下，取不到的数字一律撤下或标「待核」，禁止编造、禁止取平均；数据说明必须如实披露当期实际用到的源与缺失的能力/源。
