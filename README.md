# 金融日报 V5 (finance-daily-v5)

一个 [Claude Code / Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) 格式的技能包：对话中说「金融日报」，自动采集公开市场数据并生成**报刊风（editorial）金融要闻日报长图**，双交付 **HTML + 高清 PNG**。

![style](https://img.shields.io/badge/style-报刊风暖纸金线-b08a2e) ![deps](https://img.shields.io/badge/fetch-零第三方依赖-1e7a52) ![api](https://img.shields.io/badge/API%20Key-不需要-b23b2e)

## 特性

- **纯公开数据源** — 零连接器、零 API Key、零积分。硬行情由 `scripts/fetch_public.py`（纯 Python 标准库）直连公开接口一次取齐：
  - A股/港股指数与成交额（新浪财经公开行情接口）
  - 美股三大指数（CNBC 公开报价，含盘中/收盘状态标记）
  - 美债收益率曲线（美国财政部官方 CSV）
  - 深市成交额官方复核（深交所）
  - 内盘商品期货、外盘商品、汇率与美元指数（新浪）
- **新闻走 WebSearch + WebFetch**：新华社、证券时报、上海证券报、中国证券报、财联社、第一财经、东方财富、上交所/深交所/港交所、央行、美联储 H.15、AP News 等权威源，6 主题检索 + 2~4 个核心数字定点复核。
- **多源交叉核对铁律**：每个 ticker 数字须有脚本或 ≥2 个新闻源支撑；取不到的数字**撤下或标「待核」，禁止编造、禁止取平均**。
- **报刊风版面**：暖纸底 `#f7f4ed` + 深墨蓝 + 金线 + 红涨绿跌（中国习惯），读报式多栏排版，ticker 十卡 + 头版主稿 + TOP5 侧栏 + 11 个内容板块 + 数据说明。
- **双交付**：HTML 网页（可预览）+ 3x 高清 PNG 长图（Playwright 渲染 + 自动裁边）。
- **纯市场要闻**：不含个人持仓/自选等个性化内容，页面内不出现风格/流程自述。

## 目录结构

```
finance-daily-v5/
├── SKILL.md                        # 技能定义与完整流程（触发后 Claude 按此执行）
├── README.md                       # 本文件
├── LICENSE
├── assets/
│   └── market_news_template.html   # 报刊风渲染模板（含全部 section 结构）
└── scripts/
    ├── fetch_public.py             # 公开源硬行情抓取（纯标准库，零第三方依赖）
    └── render.py                   # Playwright 3x 渲染 PNG + 自动裁边
```

## 安装

个人级（所有项目可用）：

```bash
# Windows (PowerShell / cmd)
git clone https://github.com/<你的用户名>/finance-daily-v5.git "$USERPROFILE\.claude\skills\finance-daily-v5"
```

```bash
# macOS / Linux
git clone https://github.com/<你的用户名>/finance-daily-v5.git ~/.claude/skills/finance-daily-v5
```

项目级：克隆到 `<repo>/.claude/skills/finance-daily-v5`。

安装渲染依赖（仅 PNG 需要；行情脚本零依赖）：

```bash
pip install playwright pillow
playwright install chromium
```

重启 Claude Code，新会话中输入 `/` 应能看到 `finance-daily-v5`。

## 使用

对 Claude 说以下任意触发词即可：

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

- **没有 WebSearch 工具的宿主环境只能出「纯行情版」**：硬行情靠脚本，六块新闻全靠 WebSearch + WebFetch。
- 东方财富 push2 与 FRED 在部分网络环境（本地代理 / 强制 HTTP/2）会被拒；脚本已将其降级为可选交叉源，失败即跳过。
- 美股 `curmktstatus=REG_MKT` 表示盘中价（美东 16:00 前），日报会标注时点。
- 财政部收益率曲线为 T-1 发布，当日美债数据次日才出。
- 新浪 `int_dji/int_nasdaq/int_sp500` 是陈旧序列，本技能禁用（美股只信 CNBC + 新闻双源）。
- 非交易日 A股/港股沿用最近交易日收盘，深交所官方接口可能返回「未找到股票行」，属正常。

## 版本

- **V5（当前）**：全面改为公开数据源（零连接器、零 API Key、零积分），脚本化硬行情 + WebSearch/WebFetch 多源交叉核对。版面 / 双交付 / 红涨绿跌沿用 V4。
- V4：ftShare + Wind 双连接器交叉核对 —— 已删除，不保留备份。

## License

MIT
