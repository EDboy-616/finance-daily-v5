#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融日报 V5 — 公开数据源硬行情抓取脚本（零连接器 / 零第三方依赖 / 零积分）

用法:
  python scripts/fetch_public.py [--date YYYY-MM-DD] [--out-dir DIR] [--quiet]
默认 --date = 系统当日，--out-dir = ./raw

输出:
  <out-dir>/market_YYYYMMDD.json   结构化行情（每个字段带 src / status）
  控制台人类可读摘要

设计原则（必须遵守）:
  1. 只用公开官方/权威接口，不依赖任何 MCP 连接器、不需要 API Key、不扣积分。
  2. 每个数据源独立 try/except；失败只标 status="fail"，**绝不编造、绝不回退旧值**。
  3. 同一指标至少两路交叉（如两市成交：新浪接口 vs 深交所官方），输出 cross 字段供模型核对。
  4. 新闻类内容不在本脚本内 —— 由模型「检索网页 / 打开网页」采集（见 SKILL.md §2）。

数据源清单（2026-09-29 实测可用）:
  A股指数+成交额 / 港股  : 新浪财经 hq.sinajs.cn（urllib 直连可用）
  美股三大指数           : CNBC quote-html-webservice（实时，含 curmktstatus）
  美股复核（官方 T-1）   : FRED fredgraph.csv?id=SP500（圣路易斯联储）
  深市成交额（官方）      : 深交所 szse.cn ShowReport 接口
  美债收益率曲线（官方）  : 美国财政部 daily-treasury-rates.csv
  内盘商品期货（主力连续）: 新浪 nf_XX0
  外盘商品               : 新浪 hf_XX（纽约金/银、WTI、布伦特、现货金、COMEX铜）
  外汇 / 美元指数        : 新浪 fx_s* 与 DINIW
  可选交叉（常失败）     : 东方财富 push2（WAF 常拒 urllib/curl.exe，失败即跳过，不影响主流程）
"""
import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 25


# ---------- 基础 HTTP（urllib 优先，失败回退本机 curl） ----------
def _curl(url, headers=None, retries=1):
    cmd = ["curl", "-sSL", "--compressed", "-m", str(TIMEOUT), "-A", UA, url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    last = None
    for _ in range(retries + 1):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 10)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode("utf-8", errors="replace")
            last = f"rc={r.returncode} {r.stderr.decode('utf-8', 'replace')[:120]}"
        except Exception as e:                       # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
    raise RuntimeError(f"curl failed: {last}")


def get(url, headers=None, encoding="utf-8", retries=1):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode(encoding, errors="replace")
        except Exception as e:                       # noqa: BLE001
            last = e
    return _curl(url, h)


def fnum(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:                                # noqa: BLE001
        return None


def fpct(x):
    """解析形如 '+1.31%' / '-0.85%' / '1.31' 的涨跌幅字符串 → float 百分数。

    不能直接用 fnum：CNBC 的 change_pct 带百分号，float() 会抛异常返回 None，
    于是回退到 pct(last, prev_close)；而 CNBC 的 previous_day_closing 有时恰好等于
    last（数据源自身异常），回退会算出 0.00% —— 一个"看起来正常"的错值。
    """
    if x is None:
        return None
    s = str(x).replace(",", "").replace("%", "").strip().lstrip("+")
    try:
        return round(float(s), 2)
    except Exception:                                # noqa: BLE001
        return None


def pct(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return round((cur - prev) / prev * 100, 2)


# ---------- 新浪 ----------
SINA = "https://hq.sinajs.cn/list="
SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}

CN_IDX = {
    "sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指",
    "sh000688": "科创50", "sh000300": "沪深300", "sh000016": "上证50",
    "sh000905": "中证500", "bj899050": "北证50",
}
HK_IDX = {"rt_hkHSI": "恒生指数", "rt_hkHSCEI": "国企指数", "rt_hkHSTECH": "恒生科技"}
FX_CODES = {
    "fx_susdcny": "美元/在岸人民币", "fx_susdcnh": "美元/离岸人民币",
    "fx_susdjpy": "美元/日元", "fx_seurusd": "欧元/美元", "DINIW": "美元指数",
}
DOM_CODE = {
    "AU0": "沪金", "AG0": "沪银", "CU0": "沪铜", "AL0": "沪铝", "ZN0": "沪锌",
    "PB0": "沪铅", "NI0": "沪镍", "SN0": "沪锡", "RB0": "螺纹钢", "HC0": "热卷",
    "I0": "铁矿石", "J0": "焦炭", "JM0": "焦煤", "SC0": "上海原油", "FU0": "燃油",
    "RU0": "橡胶", "TA0": "PTA", "EG0": "乙二醇", "V0": "PVC", "MA0": "甲醇",
    "PP0": "聚丙烯", "L0": "塑料", "EB0": "苯乙烯", "PG0": "LPG", "SS0": "不锈钢",
    "M0": "豆粕", "Y0": "豆油", "P0": "棕榈油", "C0": "玉米", "SA0": "纯碱",
    "FG0": "玻璃", "UR0": "尿素", "LC0": "碳酸锂", "SI0": "工业硅", "AO0": "氧化铝",
    "JD0": "鸡蛋", "AP0": "苹果", "CJ0": "红枣", "SR0": "白糖", "CF0": "棉花",
}
OVS_CODE = {
    "GC": "COMEX黄金", "SI": "COMEX白银", "CL": "NYMEX原油(WTI)", "OIL": "布伦特原油",
    "XAU": "现货黄金", "XAG": "现货白银", "CAD": "COMEX铜", "S": "美豆", "W": "美麦",
}


def sina_parse(codes):
    raw = get(SINA + ",".join(codes), SINA_HEADERS, encoding="gbk")
    out = {}
    for line in raw.strip().split("\n"):
        m = re.match(r'var hq_str_(.+?)="(.*)";', line.strip())
        if m:
            out[m.group(1)] = m.group(2).split(",")
    return out


def sina_cn_index():
    """A股指数：现价、涨跌幅、成交额（元）。字段: 0名,1开,2昨收,3现价,4高,5低,...,8量,9额"""
    data = sina_parse(list(CN_IDX))
    out = {}
    for c, nm in CN_IDX.items():
        f = data.get(c) or []
        if len(f) < 10:
            continue
        close, prev = fnum(f[3]), fnum(f[2])
        amt = fnum(f[9])
        out[c] = {"name": nm, "open": fnum(f[1]), "prev_close": prev, "close": close,
                  "high": fnum(f[4]), "low": fnum(f[5]), "pct": pct(close, prev),
                  "amount_yuan": amt,
                  "amount_yi": round(amt / 1e8, 2) if amt else None,
                  "date": f[30] if len(f) > 30 else None,
                  "time": f[31] if len(f) > 31 else None,
                  "src": "sina-hq"}
    if not out:
        raise RuntimeError("sina A股指数返回空")
    return out


def sina_hk_index():
    """港股 rt_hk*：2开,3昨收,4高,5低,6现价,7涨跌,8涨跌幅%,13成交额"""
    data = sina_parse(list(HK_IDX))
    out = {}
    for c, nm in HK_IDX.items():
        f = data.get(c) or []
        if len(f) < 9:
            continue
        out[c.replace("rt_hk", "")] = {
            "name": nm, "open": fnum(f[2]), "prev_close": fnum(f[3]), "high": fnum(f[4]),
            "low": fnum(f[5]), "close": fnum(f[6]), "chg": fnum(f[7]), "pct": fnum(f[8]),
            "turnover": fnum(f[13]) if len(f) > 13 else None,
            "date": f[17] if len(f) > 17 else None, "time": f[18] if len(f) > 18 else None,
            "src": "sina-rt_hk"}
    if not out:
        raise RuntimeError("sina 港股指数返回空")
    return out


def sina_futures():
    data = sina_parse(["nf_" + k for k in DOM_CODE])
    items = []
    for k, nm in DOM_CODE.items():
        f = data.get("nf_" + k) or []
        if len(f) < 15:
            continue
        last, presettle = fnum(f[8]), fnum(f[10])
        items.append({"code": k, "name": nm, "last": last, "presettle": presettle,
                      "pct": pct(last, presettle), "high": fnum(f[3]), "low": fnum(f[4]),
                      "oi": fnum(f[13]), "vol": fnum(f[14]),
                      "date": f[17] if len(f) > 17 else None, "src": "sina-nf"})
    if not items:
        raise RuntimeError("sina 内盘期货返回空")
    return {"items": items, "src": "sina-nf"}


def sina_oversea(codes=("GC", "SI", "CL", "OIL", "XAU", "CAD")):
    data = sina_parse(["hf_" + c for c in codes])
    items = []
    for c in codes:
        f = data.get("hf_" + c) or []
        if len(f) < 9:
            continue
        last, prev = fnum(f[0]), fnum(f[7])
        items.append({"code": c, "name": OVS_CODE.get(c, f[13] if len(f) > 13 else c),
                      "last": last, "prev_close": prev, "pct": pct(last, prev),
                      "high": fnum(f[4]), "low": fnum(f[5]),
                      "time": f[6], "date": f[12] if len(f) > 12 else None,
                      "src": "sina-hf"})
    if not items:
        raise RuntimeError("sina 外盘商品返回空")
    return {"items": items, "src": "sina-hf"}


def sina_fx():
    data = sina_parse(list(FX_CODES))
    out = {}
    for c, nm in FX_CODES.items():
        f = data.get(c) or []
        if not f:
            continue
        if c.startswith("fx_"):
            out[c] = {"name": nm, "bid": fnum(f[1]), "ask": fnum(f[2]),
                      "prev_close": fnum(f[7]) if len(f) > 7 else None,
                      "pct": fnum(f[10]) if len(f) > 10 else None,
                      "date": f[-1], "src": "sina-fx"}
        else:  # DINIW 美元指数：0时间,1最新,5高,6低,7昨收
            out[c] = {"name": nm, "last": fnum(f[1]), "high": fnum(f[5]),
                      "low": fnum(f[6]), "prev_close": fnum(f[7]),
                      "pct": pct(fnum(f[1]), fnum(f[7])),
                      "time": f[0], "date": f[-1], "src": "sina-fx"}
    if not out:
        raise RuntimeError("sina 外汇返回空")
    return out


# ---------- 美股：CNBC（实时）+ FRED（官方复核） ----------
def cnbc_quote(symbols=(".DJI", ".SPX", ".IXIC")):
    out = {}
    for s in symbols:
        url = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
               f"?symbols={s}&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1"
               "&output=json&events=1")
        j = json.loads(get(url, {"Referer": "https://www.cnbc.com/"}))
        q = (((j.get("FormattedQuoteResult") or {}).get("FormattedQuote") or [{}])[0])
        if not q or q.get("code") not in (0, "0"):
            continue
        last, chg = fnum(q.get("last")), fnum(q.get("change"))
        prev = fnum(q.get("previous_day_closing"))
        chg_pct = fpct(q.get("change_pct"))
        # 数据源自检：previous_day_closing == last 但有涨跌额 → 前收不可信，用 last-chg 反推。
        # 否则 pct() 会算出 0.00%（一个看起来正常的错值），比 None 更危险。
        if prev is not None and last is not None and chg not in (None, 0) and abs(prev - last) < 1e-9:
            prev = round(last - chg, 4)
        if chg_pct is None:
            chg_pct = pct(last, prev)
        out[s.lstrip(".")] = {
            "name": q.get("name"), "last": last,
            "chg": chg,
            "pct": chg_pct,
            "open": fnum(q.get("open")), "high": fnum(q.get("high")),
            "low": fnum(q.get("low")), "prev_close": prev,
            "curmktstatus": q.get("curmktstatus"), "last_time": q.get("last_time"),
            "src": "cnbc-quote",
        }
    if not out:
        raise RuntimeError("CNBC 美股行情返回空")
    return out


def fred_series(series_id="SP500", n=3):
    """圣路易斯联储 FRED 官方 CSV（T-1 收盘，用作美股官方复核）。"""
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
    rows = [r for r in csv.reader(io.StringIO(raw)) if len(r) >= 2 and r[1]]
    out = [{"date": r[0], "value": fnum(r[1])} for r in rows[-n:]]
    if not out:
        raise RuntimeError("FRED 返回空")
    return {"series": series_id, "rows": out, "src": "fred-stlouisfed",
            "note": "官方序列，通常滞后 1 个交易日，用于复核前收盘"}


# ---------- 官方：深交所成交额 / 美债收益率 ----------
def szse_turnover(date):
    url = ("https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON"
           "&CATALOGID=1803_sczm&TABKEY=tab1&txtQueryDate=" + date)
    raw = get(url, {"Referer": "https://www.szse.cn/"})
    j = json.loads(raw[raw.index("["):] if not raw.strip().startswith("[") else raw)
    for r in (j[0].get("data") or []):
        if str(r.get("lbmc", "")).strip() == "股票":
            return {"stock_turnover_yi": fnum(r.get("cjje")), "src": "szse-official", "raw": r}
    raise RuntimeError("深交所返回中未找到『股票』行（可能非交易日）")


def ust_curve(year=None):
    year = year or datetime.now().year
    url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
           f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
           f"&field_tdr_date_value={year}&page&_format=csv")
    raw = get(url)
    rd = list(csv.DictReader(io.StringIO(raw)))
    rows = [{"date": r.get("Date"), "1M": fnum(r.get("1 Mo")), "3M": fnum(r.get("3 Mo")),
             "6M": fnum(r.get("6 Mo")), "1Y": fnum(r.get("1 Yr")), "2Y": fnum(r.get("2 Yr")),
             "5Y": fnum(r.get("5 Yr")), "10Y": fnum(r.get("10 Yr")), "30Y": fnum(r.get("30 Yr"))}
            for r in rd[:3]]
    if not rows:
        raise RuntimeError("财政部收益率曲线返回空")
    return {"rows": rows, "src": "treasury.gov-daily-yield-curve"}


# ---------- 可选交叉：东方财富 push2（常被 WAF 拒，失败不影响主流程） ----------
def eastmoney_cross():
    q = urllib.parse.urlencode({"fltt": "2", "invt": "2",
                                "ut": "fa5fd1943f7b386f172d6893dbfba10b",
                                "fields": "f2,f3,f6,f12,f14",
                                "secids": "1.000001,0.399001,0.399006,100.HSI,100.DJIA,100.SPX,100.NDX,100.UDI"})
    j = json.loads(get("https://push2.eastmoney.com/api/qt/ulist.np/get?" + q))
    out = {}
    for d in (j.get("data") or {}).get("diff") or []:
        out[d.get("f12")] = {"name": d.get("f14"), "close": fnum(d.get("f2")),
                             "pct": fnum(d.get("f3")),
                             "amount_yi": round(fnum(d.get("f6")) / 1e8, 2) if fnum(d.get("f6")) else None,
                             "src": "eastmoney-push2"}
    if not out:
        raise RuntimeError("东财返回空")
    return out


# ---------- 汇总 ----------
def _derive_actual_data_date(out):
    """从已抓取字段推导本期实际数据日期；取不到返回 None。

    绝不回退到「请求日期」—— 非交易日请求日 != 数据日，用请求日会写错时点。
    优先级：A股 cn_indices.*.date → 美股 us_indices.*.last_time → 美债 ust_curve.rows[0].date。
    """
    def iso(s):
        if not isinstance(s, str):
            return None
        m = re.search(r"\d{4}-\d{2}-\d{2}", s)                 # CNBC last_time 可能带时分秒，只取日期段
        if m:
            return m.group(0)
        m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", s)     # 财政部 CSV 的 Date 常为 M/D/YYYY
        if m:
            return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
        return None

    def first(values):
        for v in values:
            d = iso(v)
            if d:
                return d
        return None

    cn = out.get("cn_indices") or {}
    d = first((v or {}).get("date") for v in cn.values() if isinstance(v, dict))
    if d:
        return d
    us = out.get("us_indices") or {}
    d = first((v or {}).get("last_time") for v in us.values() if isinstance(v, dict))
    if d:
        return d
    rows = (out.get("ust_curve") or {}).get("rows") or []
    if rows and isinstance(rows[0], dict):
        return first([rows[0].get("date")])
    return None


def collect(date=None):
    date = date or datetime.now().strftime("%Y-%m-%d")
    out = {"meta": {"date": date,
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "ok": [], "fail": [], "optional_fail": []}}

    def run(tag, fn, optional=False):
        try:
            out[tag] = fn()
            out["meta"]["ok"].append(tag)
        except Exception as e:                        # noqa: BLE001
            out[tag] = {"status": "fail", "err": f"{type(e).__name__}: {e}"}
            (out["meta"]["optional_fail"] if optional else out["meta"]["fail"]).append(tag)
        return out[tag]

    run("cn_indices", sina_cn_index)
    run("hk_indices", sina_hk_index)
    run("us_indices", cnbc_quote)
    run("szse_official", lambda: szse_turnover(date))
    run("ust_curve", lambda: ust_curve(datetime.now().year))
    run("commodities_cn", sina_futures)
    run("commodities_oversea", sina_oversea)
    run("fx", sina_fx)
    # 以下两路为可选交叉源：部分网络环境（代理/HTTP2 限制）会拒绝，失败不影响主流程
    run("us_official_fred", lambda: fred_series("SP500"), optional=True)
    run("eastmoney_cross", eastmoney_cross, optional=True)

    # 两市成交交叉
    cn = out.get("cn_indices") or {}
    sh = (cn.get("sh000001") or {}).get("amount_yi")
    sz = (cn.get("sz399001") or {}).get("amount_yi")
    sina_total = round(sh + sz, 2) if (sh and sz) else None
    szse_v = (out.get("szse_official") or {}).get("stock_turnover_yi")
    out["turnover_cross"] = {
        "sina_total_yi": sina_total,
        "szse_official_sz_yi": szse_v,
        "sina_sz_yi": sz,
        "diff_pct": (round(abs(sz - szse_v) / szse_v * 100, 3) if (sz and szse_v) else None),
        "note": "新浪深市成交额 vs 深交所官方『股票』成交额；差异 >0.5% 需在数据说明中标注并复核",
    }
    # 美股 vs FRED 交叉
    spx = (out.get("us_indices") or {}).get("SPX") or {}
    fred_rows = ((out.get("us_official_fred") or {}).get("rows") or [])
    out["us_cross"] = {
        "cnbc_spx": spx.get("last"), "cnbc_status": spx.get("curmktstatus"),
        "fred_prev_close": fred_rows[-1]["value"] if fred_rows else None,
        "fred_prev_date": fred_rows[-1]["date"] if fred_rows else None,
        "note": "CNBC 为实时/收盘价，FRED SP500 为官方 T-1 收盘，用于确认量级一致",
    }
    out["meta"]["actual_data_date"] = _derive_actual_data_date(out)
    return out


def summary(d):
    L = [f"日期 {d['meta']['date']}   成功源: {', '.join(d['meta']['ok'])}"]
    if d["meta"].get("fail"):
        L.append("⚠️ 失败源(必须补): " + ", ".join(d["meta"]["fail"]) +
                 " —— 禁止编造，须改用新闻源或「打开网页」复核")
    if d["meta"].get("optional_fail"):
        L.append("· 可选交叉源未取到(可跳过): " + ", ".join(d["meta"]["optional_fail"]))
    cn = d.get("cn_indices") or {}
    for k in ("sh000001", "sz399001", "sz399006", "sh000688"):
        v = cn.get(k)
        if v:
            L.append(f"  {v['name']} {v['close']}  {v['pct']:+.2f}%  成交 {v['amount_yi']}亿")
    tc = d.get("turnover_cross") or {}
    L.append(f"  两市成交 {tc.get('sina_total_yi')}亿 | 深交所官方深市 {tc.get('szse_official_sz_yi')}亿"
             f" | 偏差 {tc.get('diff_pct')}%")
    hk = d.get("hk_indices") or {}
    for k, v in hk.items():
        L.append(f"  {v['name']} {v['close']}  {v['pct']:+.2f}%")
    us = d.get("us_indices") or {}
    for k, v in us.items():
        p = v.get("pct")
        L.append(f"  {v['name']} {v['last']}  " + (f"{p:+.2f}%" if p is not None else "pct=?") +
                 f"  [{v.get('curmktstatus')}] {v.get('last_time')}")
    uc = (d.get("ust_curve") or {}).get("rows") or []
    for r in uc[:2]:
        L.append(f"  美债 {r['date']}: 2Y {r['2Y']} / 10Y {r['10Y']} / 30Y {r['30Y']}")
    items = (d.get("commodities_cn") or {}).get("items") or []
    if items:
        L.append("  内盘: " + "  ".join(f"{i['name']} {i['last']}({i['pct']:+.2f}%)"
                                        for i in items[:12] if i["pct"] is not None))
    ovs = (d.get("commodities_oversea") or {}).get("items") or []
    if ovs:
        L.append("  外盘: " + "  ".join(f"{i['name']} {i['last']}({i['pct']:+.2f}%)"
                                        for i in ovs if i["pct"] is not None))
    for k, v in (d.get("fx") or {}).items():
        L.append(f"  {v['name']} {v.get('bid') or v.get('last')}  {v.get('pct')}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="YYYY-MM-DD，默认今日")
    ap.add_argument("--out-dir", default="raw")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    d = collect(a.date)
    os.makedirs(a.out_dir, exist_ok=True)
    ymd = d["meta"]["date"].replace("-", "")
    path = os.path.join(a.out_dir, f"market_{ymd}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    if not a.quiet:
        print(summary(d))
    print("saved:", os.path.abspath(path))


if __name__ == "__main__":
    main()
