#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 README / 文档用展示图（维护脚本，不随 skill 安装）

产物：
  docs/emblem.svg          金色麦穗徽标（纯矢量，无文字，字体无关）
  docs/banner.png          顶部横幅（1400x420 @2x）
  docs/preview-top.png     产物预览·报头与头版
  docs/preview-detail.png  产物预览·板块细节
  docs/preview-full.png    产物预览·整版缩览

用法: python maintainer/make_docs_images.py
依赖: playwright + Pillow（与 render.py 相同）
"""
import math
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TEMPLATE = ROOT / "assets" / "market_news_template.html"

INK = "#1c2230"
INK2 = "#4a5366"
GOLD = "#b08a2e"
GOLD2 = "#c9a84a"
PAPER = "#f7f4ed"
PAPER2 = "#efe9dc"
CARD = "#fffdf8"
LINE = "#d9d0bd"
UP = "#b23b2e"
DOWN = "#1e7a52"


# ---------------------------------------------------------------- 麦穗徽标
def _bez(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def _stalk(p0, ctrl, p2, n=10, rx=8.6, ry=3.9, out_d=8.0, in_d=4.2):
    """一根麦穗：弯曲麦秆 + 外侧大麦粒 + 内侧小麦粒 + 顶粒与短芒。"""
    parts = [
        f'<path d="M{p0[0]} {p0[1]} Q{ctrl[0]} {ctrl[1]} {p2[0]} {p2[1]}" fill="none" '
        f'stroke="{GOLD}" stroke-width="2" stroke-linecap="round"/>'
    ]
    for i in range(n):
        t = 0.12 + i * (0.82 / (n - 1))
        x, y = _bez(p0, ctrl, p2, t)
        x2, y2 = _bez(p0, ctrl, p2, min(t + 0.02, 1.0))
        ang = math.degrees(math.atan2(y2 - y, x2 - x))
        dx, dy = x2 - x, y2 - y
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        k = 1.0 - 0.40 * max(0.0, (t - 0.66) / 0.34)
        ox, oy = x + nx * out_d, y + ny * out_d
        parts.append(f'<ellipse cx="{ox:.1f}" cy="{oy:.1f}" rx="{rx * k:.2f}" '
                     f'ry="{ry * k:.2f}" fill="{GOLD2}" '
                     f'transform="rotate({ang + 34:.1f} {ox:.1f} {oy:.1f})"/>')
        if t > 0.46:
            ix, iy = x - nx * in_d, y - ny * in_d
            parts.append(f'<ellipse cx="{ix:.1f}" cy="{iy:.1f}" rx="{rx * 0.62 * k:.2f}" '
                         f'ry="{ry * 0.64 * k:.2f}" fill="{GOLD}" fill-opacity="0.78" '
                         f'transform="rotate({ang - 26:.1f} {ix:.1f} {iy:.1f})"/>')
    tx, ty = p2[0] - 1, p2[1] - 1
    parts.append(f'<ellipse cx="{tx:.1f}" cy="{ty:.1f}" rx="{rx * 0.5:.2f}" '
                 f'ry="{ry * 1.15:.2f}" fill="{GOLD2}" '
                 f'transform="rotate(-30 {tx:.1f} {ty:.1f})"/>')
    parts.append(f'<path d="M{tx - 2:.1f} {ty - 5:.1f} l1 -9" stroke="{GOLD}" '
                 f'stroke-width="1.2" stroke-linecap="round" fill="none"/>')
    return "".join(parts)


def emblem_svg(size=200, uid=""):
    """双穗环抱 + 中心走势线的金色徽标（README 头像 / 横幅 / 页眉通用）。"""
    geo = dict(p0=(100.0, 181.0), ctrl=(36.0, 126.0), p2=(40.0, 52.0), n=10)
    left = _stalk(**geo)
    right = f'<g transform="translate(200,0) scale(-1,1)">{left}</g>'
    pts = [(82, 126), (92, 112), (100, 118), (110, 99), (118, 105), (128, 86)]
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    chart = (
        f'<g stroke="{INK}" stroke-width="2.8" fill="none" stroke-linecap="round" '
        f'stroke-linejoin="round"><path d="{d}"/></g>'
        f'<circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="3.8" fill="{GOLD}"/>'
    )
    base = (f'<circle cx="100" cy="181" r="4.2" fill="{PAPER}" stroke="{GOLD}" '
            f'stroke-width="1.8"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
        f'width="{size}" height="{size}" role="img" aria-label="finance-daily-v5" id="{uid}">'
        f'<circle cx="100" cy="100" r="95" fill="none" stroke="{LINE}" stroke-width="1.1"/>'
        f'<circle cx="100" cy="100" r="88.5" fill="none" stroke="{GOLD}" stroke-width="0.7" '
        f'stroke-opacity="0.45"/>'
        f'{left}{right}{chart}{base}</svg>'
    )


# ---------------------------------------------------------------- 横幅
def banner_html():
    emblem = emblem_svg(224)
    chips = [
        ("上证指数", "3889.44", "+0.19%", UP),
        ("深证成指", "13745.87", "-0.35%", DOWN),
        ("道指·收盘", "53516", "+0.19%", UP),
        ("WTI原油", "82.46", "-2.99%", DOWN),
        ("美元/人民币", "7.0912", "+0.08%", UP),
    ]
    chip_html = "".join(
        f'<div class="chip"><span class="cl">{n}</span>'
        f'<span class="cv" style="color:{c}">{v}<i>{ch}</i></span></div>'
        for n, v, ch, c in chips
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{width:1400px;height:420px;overflow:hidden}}
  body{{background:{PAPER};
    font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;color:{INK};}}
  .grid{{position:absolute;inset:0;
    background-image:linear-gradient(rgba(28,34,48,.032) 1px,transparent 1px);
    background-size:100% 32px;}}
  .glow{{position:absolute;inset:0;
    background:radial-gradient(900px 380px at 14% -8%,rgba(255,253,248,.95),rgba(255,253,248,0) 62%),
               radial-gradient(760px 340px at 102% 112%,rgba(239,233,220,.9),rgba(239,233,220,0) 60%);}}
  .frame{{position:absolute;inset:15px;border:1px solid {LINE};}}
  .frame::after{{content:"";position:absolute;inset:4px;border:1px solid rgba(176,138,46,.3);}}
  .wrap{{position:relative;display:flex;align-items:center;height:420px;padding:0 60px;gap:30px}}
  .emblem{{flex:0 0 auto}}
  .rule{{flex:0 0 1px;width:1px;height:224px;
    background:linear-gradient(180deg,transparent,{LINE} 16%,{LINE} 84%,transparent)}}
  .text{{flex:1 1 auto;min-width:0}}
  .kicker{{font-size:12px;letter-spacing:.44em;text-transform:uppercase;color:{GOLD};font-weight:700}}
  .title{{font-family:"Noto Serif SC","Songti SC",Georgia,serif;font-size:72px;font-weight:800;
    letter-spacing:.12em;line-height:1.1;margin:6px 0 8px}}
  .title em{{font-style:normal;color:{GOLD}}}
  .sub{{font-size:16.5px;color:{INK2};letter-spacing:.01em}}
  .sub b{{color:{INK};font-weight:700}}
  .meta{{margin-top:14px;font-size:12.5px;color:{INK2};letter-spacing:.04em}}
  .meta span{{margin-right:18px}}
  .meta i{{font-style:normal;color:{GOLD};font-weight:700;margin-right:3px}}
  .side{{flex:0 0 330px}}
  .card{{background:{CARD};border:1px solid {LINE};border-top:3px solid {GOLD};
    box-shadow:0 1px 0 rgba(28,34,48,.03);padding:13px 15px 11px}}
  .card h4{{font-size:10px;letter-spacing:.24em;color:{GOLD};font-weight:700;margin-bottom:9px}}
  .chip{{display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;
    border-bottom:1px dotted {LINE}}}
  .chip:last-child{{border-bottom:none}}
  .cl{{font-size:11.5px;color:{INK2}}}
  .cv{{font-family:"Noto Serif SC",Georgia,serif;font-weight:800;font-size:14.5px}}
  .cv i{{font-style:normal;font-size:10.5px;font-weight:600;margin-left:7px}}
</style></head>
<body>
  <div class="grid"></div><div class="glow"></div><div class="frame"></div>
  <div class="wrap">
    <div class="emblem">{emblem}</div>
    <div class="rule"></div>
    <div class="text">
      <div class="kicker">Agent Skill · Financial Daily</div>
      <div class="title">金融<em>日报</em></div>
      <div class="sub">说一句「<b>金融日报</b>」，自动采集公开行情并生成<b>报刊风要闻长图</b></div>
      <div class="meta">
        <span><i>零</i>API Key</span><span><i>零</i>积分</span>
        <span><i>15</i>个安装目标</span><span>HTML 必交 · PNG 可选</span>
      </div>
    </div>
    <div class="side">
      <div class="card">
        <h4>MARKET TAPE · 示例</h4>
        {chip_html}
      </div>
    </div>
  </div>
</body></html>
"""


def social_html():
    """GitHub 仓库 Social preview 用（1280x640，上传到 Settings → Social preview）。"""
    emblem = emblem_svg(260)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{width:1280px;height:640px;overflow:hidden}}
  body{{background:{PAPER};
    font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;color:{INK};
    display:flex;align-items:center;justify-content:center}}
  .grid{{position:absolute;inset:0;
    background-image:linear-gradient(rgba(28,34,48,.032) 1px,transparent 1px);
    background-size:100% 30px;}}
  .glow{{position:absolute;inset:0;
    background:radial-gradient(760px 420px at 50% 8%,rgba(255,253,248,.98),rgba(255,253,248,0) 66%),
               radial-gradient(700px 380px at 50% 108%,rgba(239,233,220,.92),rgba(239,233,220,0) 62%);}}
  .frame{{position:absolute;inset:22px;border:1px solid {LINE};}}
  .frame::after{{content:"";position:absolute;inset:6px;border:1px solid rgba(176,138,46,.28);}}
  .box{{position:relative;text-align:center}}
  .emblem{{margin-bottom:16px}}
  .kicker{{font-size:13px;letter-spacing:.5em;text-transform:uppercase;color:{GOLD};font-weight:700}}
  .title{{font-family:"Noto Serif SC","Songti SC",Georgia,serif;font-size:82px;font-weight:800;
    letter-spacing:.14em;line-height:1.1;margin:10px 0 12px}}
  .title em{{font-style:normal;color:{GOLD}}}
  .sub{{font-size:19px;color:{INK2}}}
  .sub b{{color:{INK}}}
  .line{{margin-top:20px;font-size:13.5px;color:{INK2};letter-spacing:.06em}}
  .line span{{margin:0 12px}}
  .line i{{font-style:normal;color:{GOLD};font-weight:700}}
</style></head>
<body>
  <div class="grid"></div><div class="glow"></div><div class="frame"></div>
  <div class="box">
    <div class="emblem">{emblem}</div>
    <div class="kicker">Agent Skill</div>
    <div class="title">金融<em>日报</em></div>
    <div class="sub">一句「<b>金融日报</b>」→ 公开行情采集 → <b>报刊风要闻长图</b></div>
    <div class="line">
      <span><i>零</i>API Key</span><span><i>零</i>积分</span>
      <span><i>15</i>个安装目标</span><span>HTML 必交 · PNG 可选</span>
    </div>
  </div>
</body></html>
"""


# ---------------------------------------------------------------- 渲染
def shoot(html_path: Path, out_png: Path, width: int, height: int, scale: int = 2,
          sections: bool = False):
    """截图；sections=True 时同时返回每个 .section-title 的文档内 y 坐标（CSS px）。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
        page = browser.new_page(device_scale_factor=scale,
                                viewport={"width": width, "height": height})
        page.goto(Path(html_path).resolve().as_uri())
        page.wait_for_timeout(600)
        page.screenshot(path=str(out_png))
        tops = []
        if sections:
            tops = page.evaluate(
                "() => Array.from(document.querySelectorAll('.section-title'))"
                ".map(el => el.getBoundingClientRect().top + window.scrollY)")
        browser.close()
    return tops


def main():
    DOCS.mkdir(exist_ok=True)

    (DOCS / "emblem.svg").write_text(emblem_svg(200), encoding="utf-8", newline="\n")
    print("[ok] docs/emblem.svg")

    src = Path(tempfile.mkdtemp()) / "banner.src.html"
    src.write_text(banner_html(), encoding="utf-8", newline="\n")
    shoot(src, DOCS / "banner.png", 1400, 420, scale=2)
    print("[ok] docs/banner.png")

    social = src.parent / "social.src.html"
    social.write_text(social_html(), encoding="utf-8", newline="\n")
    shoot(social, DOCS / "social-preview.png", 1280, 640, scale=1)
    print("[ok] docs/social-preview.png")

    raw = DOCS / "_full_raw.png"
    tops = shoot(TEMPLATE, raw, 1080, 2400, scale=2, sections=True)
    full = Image.open(raw)
    w, h = full.size
    css_w = w / 2  # scale=2
    print(f"[ok] raw {w}x{h}  sections={len(tops)}")

    def save(im, name, target_w=1080):
        im.resize((target_w, round(im.height * target_w / im.width)), Image.LANCZOS).save(
            DOCS / name, optimize=True)
        print(f"[ok] docs/{name}")

    save(full.crop((0, 0, w, min(h, 2500))), "preview-top.png")

    # 细节图从「行业扫描」板块标题起，保证切口落在板块边界上
    y_css = tops[4] if len(tops) > 4 else 1500  # 行业扫描 SECTORS
    y0 = max(0, int((y_css - 12) * 2))
    save(full.crop((0, y0, w, min(h, y0 + 2050))), "preview-detail.png")
    save(full, "preview-full.png", 820)

    raw.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
