#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融日报 V5 渲染脚本（高分辨率版）
用法: python scripts/render.py <input_html> <output_png> [scale]
依赖: playwright + Pillow
  pip install playwright pillow
  playwright install chromium

说明:
  - device_scale_factor 默认 3（高清；V2 为 2x）。命令行第三参数可覆盖，如 4（更高清）或 2（降体积）。
  - 截图后自动用 ImageChops 按内容 bbox 裁掉上下空白（保留左右 body padding），
    再叠加 40px 安全边距，避免页脚下方大段留白。
"""
import sys
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

DEFAULT_SCALE = 3
VIEWPORT_WIDTH = 1080
VIEWPORT_HEIGHT = 2400


def render(html_path: str, out_png: str, scale: int = DEFAULT_SCALE):
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
        page = browser.new_page(
            device_scale_factor=scale,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        )
        page.goto("file:///" + html_path)
        page.wait_for_timeout(700)
        page.screenshot(path=out_png, full_page=True)
        browser.close()

    # 裁上下空白，左右不裁
    im = Image.open(out_png)
    bg = Image.new(im.mode, im.size, (247, 244, 237))  # 与 --paper:#f7f4ed 对齐
    b = ImageChops.difference(im, bg).getbbox()
    if b is None:
        # 全图纯色（极少出现），直接保存
        im.save(out_png)
    else:
        im.crop((0, max(0, b[1] - 40), im.size[0], min(im.size[1], b[3] + 40))).save(out_png)
    print("done", out_png, im.size)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python scripts/render.py <input_html> <output_png> [scale=3]")
        sys.exit(1)
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_SCALE
    render(sys.argv[1], sys.argv[2], scale)
