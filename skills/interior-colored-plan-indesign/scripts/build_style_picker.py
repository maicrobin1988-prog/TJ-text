#!/usr/bin/env python3
"""仅在维护固定风格图库时运行；接收项目 PDF 时禁止调用。

本脚本不接收项目 PDF，也不生成项目彩平。首次维护可用 --source-dir
读取从八款虚构同底图 INDD 临时隐藏“06 空间编号”和“07 版式与功能表”
后导出的 144 dpi A3 JPEG（A1.jpg ... E1.jpg）；只裁出同一平面范围。
后续图库维护可直接复用 assets/style-picker/plans/ 下的固定 PNG。
普通调用技能时直接展示生成好的速选 PNG，不能重新运行本脚本。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


SKILL = Path(__file__).resolve().parents[1]
IDS = ["A1", "B1", "B2", "B3", "C1", "D1", "D2", "E1"]
GROUPS = {"A": "A 材质", "B": "B 线稿色块", "C": "C 氛围", "D": "D 模型投影", "E": "E 索引"}
LINES = {
    "A1": "米灰材质 · 细节与软阴影",
    "B1": "橙色主带 · 突出动线",
    "B2": "亮黄岛群 · 突出活动组团",
    "B3": "淡粉色阶 · 区分功能",
    "C1": "粉灰室内 · 灰青环境",
    "D1": "灰阶底面 · 黑墙强投影",
    "D2": "轻白底面 · 暖边柔投影",
    "E1": "黑白灰底 · 红色重点",
}
INK = "#28353A"
MUTED = "#75828A"
BACKGROUND = "#F1F3F2"
FONT_PATHS = [
    str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc"),
    str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simhei.ttf"),
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_PATHS:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    raise RuntimeError("请在 FONT_PATHS 中配置可显示中文的字体。")


def clean_plans(source: Path, target: Path) -> None:
    """裁切固定示意 INDD 的左图，不做当前项目处理。"""
    target.mkdir(parents=True, exist_ok=True)
    # A3 横向 420 × 297 mm；此范围包含同底图及有限外缘，不含右侧功能表。
    crop_mm = (14.0, 60.6, 296.0, 260.4)
    for sid in IDS:
        with Image.open(source / f"{sid}.jpg") as page:
            page = page.convert("RGB")
            w, h = page.size
            if abs(w / h - 420 / 297) > 0.01:
                raise ValueError(f"{sid}: 输入必须是完整 A3 横向页面导出图。")
            crop = page.crop((round(crop_mm[0] * w / 420), round(crop_mm[1] * h / 297),
                              round(crop_mm[2] * w / 420), round(crop_mm[3] * h / 297)))
            crop = ImageOps.contain(crop, (1000, 1000), Image.Resampling.LANCZOS)
            crop.save(target / f"{sid}.png", optimize=True)


def card(preset: dict, plan: Path) -> Image.Image:
    """两倍像素单卡，缩入主图后文字仍清楚。"""
    canvas = Image.new("RGB", (704, 688), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    sid = preset["id"]
    accent = preset["accent"]
    if sid == "B2":
        accent = "#A28C12"  # 黄色作为小字时提高对比度。
    draw.text((32, 23), GROUPS[sid[0]], font=font(24), fill=MUTED)
    draw.text((32, 64), f"{sid}  {preset['name']}", font=font(42), fill=INK)
    draw.rounded_rectangle((32, 126, 672, 600), radius=12, fill="#F7F8F6")
    with Image.open(plan) as image:
        image = ImageOps.contain(image.convert("RGB"), (640, 474), Image.Resampling.LANCZOS)
        canvas.paste(image, (32 + (640 - image.width) // 2, 126 + (474 - image.height) // 2))
    draw.line((32, 623, 76, 623), fill=accent, width=5)
    draw.text((92, 606), LINES[sid], font=font(28), fill=INK)
    return canvas


def sheet(cards: dict[str, Image.Image], ids: list[str], title: str, columns: int, out: Path,
          subtitle: str = "固定风格示意 · 同一简化平面 · 非当前项目") -> None:
    width = 1536 if columns == 4 else (1280 if columns == 3 else 960)
    margin, gap = 32, 18
    card_width = (width - 2 * margin - gap * (columns - 1)) // columns
    card_height = round(card_width * 688 / 704)
    rows = (len(ids) + columns - 1) // columns
    top = 122
    height = top + rows * card_height + (rows - 1) * gap + 62
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 22), title, font=font(34), fill=INK)
    draw.text((margin, 75), subtitle, font=font(20), fill=MUTED)
    for i, sid in enumerate(ids):
        x = margin + (i % columns) * (card_width + gap)
        y = top + (i // columns) * (card_height + gap)
        resized = cards[sid].resize((card_width, card_height), Image.Resampling.LANCZOS)
        canvas.paste(resized, (x, y))
    example = "D2" if "D2" in ids else ids[0]
    draw.text((margin, height - 40), f"直接回复样式编号即可选择，例如「{example}」。", font=font(20), fill=MUTED)
    canvas.save(out, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, help="仅图库维护：可显示中文的本机字体文件")
    parser.add_argument("--source-dir", type=Path, help="仅图库维护：已隐藏编号和图例层的固定 A3 JPEG 所在目录")
    parser.add_argument("--output", type=Path, default=SKILL / "assets" / "style-picker")
    args = parser.parse_args()
    if args.font:
        if not args.font.is_file():
            raise FileNotFoundError(args.font)
        FONT_PATHS.insert(0, str(args.font))
    args.output.mkdir(parents=True, exist_ok=True)
    plans = args.output / "plans"
    if args.source_dir:
        clean_plans(args.source_dir, plans)
    presets = json.loads((SKILL / "assets" / "style-presets.json").read_text(encoding="utf-8"))
    presets = {item["id"]: item for item in presets}
    cards = {sid: card(presets[sid], plans / f"{sid}.png") for sid in IDS}
    card_dir = args.output / "cards"
    card_dir.mkdir(exist_ok=True)
    for sid, image in cards.items():
        image.save(card_dir / f"{sid}.png", optimize=True)
    sheet(cards, IDS, "室内彩平 · 五类八款风格速选", 4, args.output / "八款风格速选.png")
    sheet(cards, ["B1", "B2", "B3"], "B 线稿色块 · 选择表达重点", 3,
          args.output / "B_线稿色块.png")
    sheet(cards, ["D1", "D2"], "D 模型投影 · 选择明暗层次", 2,
          args.output / "D_模型投影.png")
    print(args.output / "八款风格速选.png")


if __name__ == "__main__":
    main()
