#!/usr/bin/env python3
"""Build an interior scheme text book as HTML, PPTX, and PDF from JSON data."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt


SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
INK = RGBColor(17, 17, 17)
GRAY = RGBColor(125, 125, 125)
LINE = RGBColor(215, 219, 226)
BLUE = RGBColor(49, 92, 255)
PALE_BLUE = RGBColor(223, 247, 251)
PALE_LAV = RGBColor(222, 214, 255)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-") or "scheme-textbook"


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def resolve_path(raw: Optional[str], base: Path) -> Optional[Path]:
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = base / p
    return p if p.exists() else None


def image_src(raw: Optional[str], base: Path) -> str:
    p = resolve_path(raw, base)
    return p.as_uri() if p else ""


def item_title(item: Any, key: str = "title_cn") -> str:
    if isinstance(item, dict):
        return str(item.get(key) or item.get("title") or item.get("title_cn") or "")
    return str(item)


def html_lines(value: Any) -> str:
    return "<br>".join(esc(x) for x in str(value or "").splitlines() if x.strip())


def content_layout(slide: Dict[str, Any], index: int) -> str:
    allowed = ["statement", "metrics", "matrix", "split", "timeline"]
    explicit = str(slide.get("layout") or "").strip().lower()
    if explicit in allowed:
        return explicit
    return allowed[(index - 1) % len(allowed)]


def hex_to_rgb(value: str, fallback: RGBColor = PALE_BLUE) -> RGBColor:
    value = str(value or "").strip().lstrip("#")
    if len(value) != 6:
        return fallback
    try:
        return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return fallback


def metric_parts(item: Any, index: int) -> tuple[str, str]:
    label = item_title(item, "title_cn")
    match = re.search(r"(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s*(?:%|㎡|m²|元|天|万|亿|F|层)?)", label)
    if match:
        return match.group(1).strip(), label
    return f"{index:02d}", label


def css() -> str:
    return """
@page { size: 420mm 297mm; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; background: #e9ecef; font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif; color: #111; }
.slide { position: relative; width: 420mm; height: 297mm; overflow: hidden; background: #fbfcfc; page-break-after: always; }
.slide::after { content: ""; position: absolute; inset: 0; pointer-events: none; }
.gradient { position: absolute; width: 210mm; height: 210mm; right: -20mm; bottom: -32mm; border-radius: 50%; background: radial-gradient(circle at 40% 45%, rgba(49,92,255,.28), rgba(142,122,230,.16) 35%, rgba(135,200,232,.12) 55%, rgba(255,255,255,0) 72%); filter: blur(18px); }
.header { position: absolute; top: 22mm; right: 24mm; width: 150mm; text-align: right; font-size: 18pt; letter-spacing: .02em; font-weight: 300; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cover .gradient { width: 240mm; height: 240mm; right: -34mm; bottom: -46mm; opacity: .92; }
.cover-title { position: absolute; top: 30mm; left: 28mm; width: 255mm; }
.cover-title .eyebrow { color: #777; font-size: 17pt; letter-spacing: .10em; margin-bottom: 10mm; }
.cover-title h1 { margin: 0; font-size: 56pt; line-height: 1; font-weight: 560; letter-spacing: 0; max-width: 248mm; }
.rule { width: 184mm; height: .3mm; background: #111; margin: 7mm 0; }
.cover .rule { width: 112mm; height: .45mm; margin: 12mm 0 9mm; }
.cover-cn { font-size: 29pt; line-height: 1.18; font-weight: 300; }
.cover-sub { max-width: 220mm; font-size: 23pt; line-height: 1.25; color: #333; }
.cover-sub small { display: block; margin-top: 3mm; color: #777; font-size: 13pt; letter-spacing: .04em; }
.cover-points { position: absolute; left: 28mm; bottom: 52mm; display: flex; gap: 9mm; max-width: 260mm; }
.cover-point { border-left: .55mm solid #315cff; padding-left: 4mm; width: 78mm; font-size: 13pt; line-height: 1.32; color: #222; }
.brand { position: absolute; left: 28mm; bottom: 18mm; font-size: 8pt; color: #555; }
.date { position: absolute; left: 28mm; bottom: 33mm; font-size: 14pt; }
.toc { position: absolute; right: 78mm; top: 118mm; display: flex; gap: 18mm; color: #555; }
.toc div { border-left: .3mm solid #d7dbe2; padding-left: 5mm; min-width: 30mm; font-size: 10pt; }
.toc b { display: block; color: #111; font-weight: 300; margin-bottom: 1mm; }
.chapter-block { position: absolute; right: 78mm; top: 118mm; display: grid; grid-template-columns: auto auto; gap: 8mm; align-items: start; }
.chapter-no { font-size: 52pt; font-weight: 700; line-height: .9; }
.chapter-name { font-size: 22pt; letter-spacing: .08em; }
.chapter-name span { display: block; font-size: 25pt; letter-spacing: 0; margin-top: 4mm; }
.chapter-items { position: absolute; right: 78mm; top: 178mm; color: #333; font-size: 12pt; line-height: 1.55; }
.placeholder, .image { background: #e8ecef; display: flex; align-items: center; justify-content: center; color: #8a8a8a; font-size: 14pt; }
.image img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rendering-hero { position: absolute; left: 0; right: 0; bottom: 16mm; height: 220mm; }
.locator { position: absolute; left: 22mm; top: 24mm; width: 50mm; height: 32mm; opacity: .8; }
.plan-wrap { position: absolute; left: 22mm; top: 34mm; width: 270mm; height: 232mm; border: .35mm solid #e2e5e8; }
.legend { position: absolute; right: 28mm; bottom: 42mm; width: 80mm; }
.legend h2 { font-size: 20pt; font-weight: 300; margin: 0 0 8mm; }
.legend-row { display: grid; grid-template-columns: 17mm 1fr; gap: 5mm; margin: 4mm 0; font-size: 12pt; align-items: start; }
.swatch { height: 5mm; margin-top: 1mm; }
.legend-row small { display: block; color: #8a8a8a; font-size: 9pt; margin-top: 1mm; }
.journey-title { position: absolute; left: 20mm; top: 50mm; }
.journey-title h1 { margin: 0; font-size: 25pt; font-weight: 300; }
.journey-title p { margin: 2mm 0 0; color: #888; font-size: 18pt; letter-spacing: .06em; }
.journey-line { position: absolute; left: 65mm; right: 28mm; top: 150mm; height: 42mm; border-top: 2.5mm solid #4a58ff; border-radius: 48% 52% 0 0; opacity: .9; }
.journey-items { position: absolute; left: 65mm; right: 28mm; top: 174mm; display: flex; justify-content: space-between; border-top: 1.5mm solid #c2c5ce; padding-top: 8mm; }
.journey-item { text-align: center; width: 34mm; font-size: 13pt; }
.journey-item small { display: block; color: #888; font-size: 8pt; margin-top: 1mm; }
.dot { width: 7mm; height: 7mm; background: #141b42; border-radius: 50%; margin: -12mm auto 7mm; }
.materials-grid { position: absolute; left: 18mm; right: 18mm; top: 58mm; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8mm; }
.mat-tile { height: 75mm; position: relative; background: #e6e6e6; overflow: hidden; }
.mat-tile img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.85); }
.pill { position: absolute; top: 8mm; left: 14mm; background: white; border-radius: 10mm; padding: 1.5mm 6mm; font-size: 11pt; box-shadow: 0 0 0 .2mm rgba(0,0,0,.08); }
.mat-summary { position: absolute; left: 18mm; bottom: 24mm; font-size: 15pt; line-height: 1.45; }
.content-title { position: absolute; left: 24mm; top: 42mm; width: 205mm; }
.content-title .en { color: #777; font-size: 14pt; letter-spacing: .08em; margin-bottom: 4mm; }
.content-title h1 { margin: 0; font-size: 38pt; line-height: 1.08; font-weight: 540; }
.content-lead { position: absolute; left: 24mm; top: 106mm; width: 188mm; color: #444; font-size: 19pt; line-height: 1.38; }
.content-grid { position: absolute; left: 230mm; right: 24mm; top: 72mm; display: grid; grid-template-columns: 1fr; gap: 8mm; }
.content-item { border-top: .35mm solid #d7dbe2; padding-top: 4mm; font-size: 17pt; line-height: 1.28; }
.content-item .idx { color: #315cff; font-size: 13pt; margin-right: 3mm; }
.content-item small { display: block; color: #888; font-size: 10pt; margin-top: 1mm; }
.content-statement .content-title { top: 48mm; width: 345mm; }
.content-statement .content-title h1 { font-size: 50pt; max-width: 330mm; }
.statement-lead { position: absolute; left: 24mm; top: 132mm; width: 210mm; font-size: 24pt; line-height: 1.32; color: #222; }
.statement-points { position: absolute; right: 25mm; bottom: 34mm; width: 125mm; display: grid; gap: 8mm; }
.statement-point { border-top: .4mm solid #111; padding-top: 4mm; font-size: 17pt; line-height: 1.24; }
.metrics-row { position: absolute; left: 24mm; right: 24mm; top: 118mm; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8mm; }
.metric { border-top: .45mm solid #315cff; min-height: 50mm; padding-top: 5mm; }
.metric b { display: block; font-size: 34pt; font-weight: 560; line-height: 1.02; }
.metric span { display: block; margin-top: 4mm; color: #444; font-size: 14pt; line-height: 1.28; }
.matrix-grid { position: absolute; left: 225mm; top: 70mm; width: 166mm; height: 178mm; display: grid; grid-template-columns: repeat(2, 1fr); gap: 7mm; }
.matrix-cell { background: rgba(223,247,251,.55); border-top: .45mm solid #315cff; padding: 7mm; font-size: 17pt; line-height: 1.24; }
.matrix-cell:nth-child(2), .matrix-cell:nth-child(3) { background: rgba(222,214,255,.42); }
.timeline { position: absolute; left: 32mm; right: 32mm; top: 166mm; display: flex; justify-content: space-between; border-top: 1.1mm solid #315cff; }
.time-node { width: 62mm; padding-top: 9mm; position: relative; font-size: 16pt; line-height: 1.25; }
.time-node::before { content: ""; position: absolute; top: -4mm; left: 0; width: 8mm; height: 8mm; border-radius: 50%; background: #141b42; }
.time-node b { display: block; color: #315cff; font-size: 16pt; margin-bottom: 2mm; }
.content-visual { position: absolute; display: flex; align-items: center; justify-content: center; border: .35mm solid #d7dbe2; color: #8a8a8a; font-size: 13pt; letter-spacing: .05em; overflow: hidden; }
.content-visual.image { background: #e8ecef; }
.content-visual img { width: 100%; height: 100%; object-fit: cover; display: block; }
.visual-statement { left: 24mm; bottom: 34mm; width: 176mm; height: 62mm; }
.visual-metrics { left: 24mm; right: 24mm; bottom: 30mm; height: 62mm; }
.visual-matrix { left: 24mm; bottom: 34mm; width: 172mm; height: 82mm; }
.visual-timeline { right: 28mm; top: 80mm; width: 132mm; height: 60mm; }
.visual-split { left: 24mm; bottom: 34mm; width: 176mm; height: 82mm; }
.thanks { position: absolute; left: 132mm; top: 112mm; display: grid; grid-template-columns: 84mm 115mm; column-gap: 18mm; align-items: center; }
.thanks-en { color: #888; font-size: 33pt; line-height: 1.1; font-weight: 300; text-align: center; }
.thanks-cn { font-size: 43pt; font-weight: 800; margin-top: 12mm; text-align: center; }
.thanks-info { font-size: 17pt; line-height: 1.35; }
.thanks-info small { display: block; color: #888; font-size: 11pt; line-height: 1.35; margin-top: 5mm; }
"""


def render_image_box(raw: Optional[str], base: Path, klass: str, label: str) -> str:
    src = image_src(raw, base)
    if src:
        return f'<div class="{klass} image"><img src="{src}" alt="{esc(label)}"></div>'
    return f'<div class="{klass} placeholder">{esc(label)} TBD</div>'


def render_slide(slide: Dict[str, Any], project: Dict[str, Any], base: Path, index: int) -> str:
    typ = slide.get("type", "rendering")
    title_cn = slide.get("title_cn", project.get("title_cn", ""))
    title_en = slide.get("title_en", project.get("title_en", ""))

    if typ == "cover":
        points = "".join(
            f'<div class="cover-point">{esc(item_title(x, "title_cn"))}</div>'
            for x in slide.get("items", [])[:3]
        )
        return f"""
<section class="slide cover" data-title="{esc(title_cn)}">
  <div class="gradient"></div>
  <div class="cover-title">
    <div class="eyebrow">{esc(title_en)}</div>
    <h1>{html_lines(title_cn)}</h1>
    <div class="rule"></div>
    <div class="cover-sub">{html_lines(slide.get("subtitle_cn", project.get("subtitle_cn", "")))}<small>{esc(slide.get("subtitle_en", project.get("subtitle_en", "")))}</small></div>
  </div>
  <div class="cover-points">{points}</div>
  <div class="date">{esc(project.get("date", ""))}</div>
  <div class="brand">{esc(project.get("company_cn", ""))}<br>{esc(project.get("company_en", ""))}</div>
</section>"""

    if typ == "toc":
        items = "".join(
            f"<div><b>{esc(item_title(x, 'title_en'))}</b>{esc(item_title(x, 'title_cn'))}</div>"
            for x in slide.get("items", [])
        )
        return f'<section class="slide toc-slide" data-title="TOC"><div class="toc">{items}</div></section>'

    if typ == "chapter":
        items = "".join(f"<div>{esc(x)}</div>" for x in slide.get("items", []))
        return f"""
<section class="slide chapter" data-title="{esc(title_cn)}">
  <div class="gradient"></div>
  <div class="chapter-block">
    <div class="chapter-no">{esc(slide.get("chapter_no", "01"))}</div>
    <div class="chapter-name">{esc(title_en)}<span>{esc(title_cn)}</span></div>
  </div>
  <div class="chapter-items">{items}</div>
</section>"""

    header = f'<div class="header">{esc(title_en)} / {esc(title_cn)}</div>'

    if typ == "plan":
        legend = "".join(
            f'<div class="legend-row"><div class="swatch" style="background:{esc(x.get("color", "#dff7fb"))}"></div><div>{esc(item_title(x, "title_cn"))}<small>{esc(item_title(x, "title_en"))}</small></div></div>'
            for x in slide.get("items", [])
            if isinstance(x, dict)
        )
        return f"""
<section class="slide plan" data-title="{esc(title_cn)}">
  {header}
  {render_image_box(slide.get("image"), base, "plan-wrap", "PLAN IMAGE")}
  <div class="legend"><h2>空间功能<br><small>SPATIAL FUNCTION</small></h2>{legend}</div>
</section>"""

    if typ == "journey":
        items = "".join(
            f'<div class="journey-item"><div class="dot"></div>{esc(item_title(x, "title_cn"))}<small>{esc(item_title(x, "title_en"))}</small></div>'
            for x in slide.get("items", [])
        )
        return f"""
<section class="slide journey" data-title="{esc(title_cn)}">
  {header}
  <div class="journey-title"><h1>{esc(title_cn)}</h1><p>{esc(title_en)}</p></div>
  <div class="journey-line"></div>
  <div class="journey-items">{items}</div>
</section>"""

    if typ == "materials":
        imgs = slide.get("images", [])
        labels = slide.get("items", [])
        tiles = []
        for i in range(6):
            raw = imgs[i].get("image") if i < len(imgs) and isinstance(imgs[i], dict) else None
            label = item_title(labels[i], "title_cn") if i < len(labels) else "材料"
            src = image_src(raw, base)
            img = f'<img src="{src}" alt="{esc(label)}">' if src else ""
            tiles.append(f'<div class="mat-tile">{img}<div class="pill">{esc(label)}</div></div>')
        summary = "<br>".join(esc(item_title(x, "title_cn")) for x in labels[:6])
        return f"""
<section class="slide materials" data-title="{esc(title_cn)}">
  {header}
  <div class="materials-grid">{''.join(tiles)}</div>
  <div class="mat-summary">{summary}</div>
</section>"""

    if typ == "content":
        items = slide.get("items", [])
        lead = esc(item_title(items[0], "title_cn")) if items else ""
        layout = content_layout(slide, index)
        title = f'<div class="content-title"><div class="en">{esc(title_en)}</div><h1>{html_lines(title_cn)}</h1></div>'
        visual = render_image_box(slide.get("image"), base, f"content-visual visual-{layout}", "PLANNING IMAGE")
        if layout == "statement":
            points = "".join(
                f'<div class="statement-point"><span class="idx">{i:02d}</span>{esc(item_title(item, "title_cn"))}</div>'
                for i, item in enumerate(items[1:5], 1)
            )
            body = f'{title}<div class="statement-lead">{lead}</div>{visual}<div class="statement-points">{points}</div>'
        elif layout == "metrics":
            metric_cards = []
            for i, item in enumerate(items[:4], 1):
                value, label = metric_parts(item, i)
                metric_cards.append(f'<div class="metric"><b>{esc(value)}</b><span>{esc(label)}</span></div>')
            metrics = "".join(metric_cards)
            body = f'{title}<div class="metrics-row">{metrics}</div>{visual}'
        elif layout == "matrix":
            cells = "".join(
                f'<div class="matrix-cell"><span class="idx">{i:02d}</span><br>{esc(item_title(item, "title_cn"))}</div>'
                for i, item in enumerate(items[1:5], 1)
            )
            body = f'{title}<div class="content-lead">{lead}</div>{visual}<div class="matrix-grid">{cells}</div>'
        elif layout == "timeline":
            nodes = "".join(
                f'<div class="time-node"><b>{i:02d}</b>{esc(item_title(item, "title_cn"))}</div>'
                for i, item in enumerate(items[1:6], 1)
            )
            body = f'{title}<div class="content-lead">{lead}</div>{visual}<div class="timeline">{nodes}</div>'
        else:
            rows = []
            for i, item in enumerate(items[1:7], 1):
                rows.append(
                    f'<div class="content-item"><span class="idx">{i:02d}</span>{esc(item_title(item, "title_cn"))}<small>{esc(item_title(item, "title_en"))}</small></div>'
                )
            body = f'{title}<div class="content-lead">{lead}</div>{visual}<div class="content-grid">{"".join(rows)}</div>'
        return f"""
<section class="slide content content-{layout}" data-title="{esc(title_cn)}">
  {header}
  <div class="gradient"></div>
  {body}
</section>"""

    if typ == "thanks":
        return f"""
<section class="slide thanks-slide" data-title="THANK YOU">
  <div class="thanks">
    <div><div class="thanks-en">THANK<br>YOU</div><div class="thanks-cn">谢谢</div></div>
    <div class="thanks-info">{esc(project.get("title_cn", ""))}<br>{esc(project.get("subtitle_cn", "方案文本"))}<div class="rule"></div><small>{esc(project.get("title_en", ""))}<br>{esc(project.get("company_cn", ""))}</small></div>
  </div>
</section>"""

    return f"""
<section class="slide rendering" data-title="{esc(title_cn)}">
  {header}
  {render_image_box(slide.get("locator"), base, "locator", "LOCATOR")}
  {render_image_box(slide.get("image"), base, "rendering-hero", "RENDERING")}
</section>"""


def build_html(data: Dict[str, Any], out_html: Path, data_base: Path) -> None:
    project = data.get("project", {})
    slides = data.get("slides", [])
    body = "\n".join(render_slide(slide, project, data_base, index) for index, slide in enumerate(slides, 1))
    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(project.get("title_cn", "Scheme Textbook"))}</title>
<style>{css()}</style>
</head>
<body>
{body}
</body>
</html>
"""
    out_html.write_text(doc, encoding="utf-8")


def add_textbox(slide, x, y, w, h, text, size=18, color=INK, bold=False):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = str(text or "")
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "Arial"
    return box


def add_rect(slide, x, y, w, h, color, transparency=0):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.fill.transparency = transparency
    shape.line.color.rgb = LINE
    shape.line.width = Pt(0.5)
    return shape


def add_placeholder(slide, x, y, w, h, label):
    add_rect(slide, x, y, w, h, RGBColor(232, 236, 239), 0)
    add_textbox(slide, x, y + h / 2 - Inches(0.2), w, Inches(0.4), label, 16, GRAY)


def add_picture_or_placeholder(slide, raw: Optional[str], base: Path, x, y, w, h, label):
    p = resolve_path(raw, base)
    if p:
        slide.shapes.add_picture(str(p), x, y, width=w, height=h)
    else:
        add_placeholder(slide, x, y, w, h, label)


def ppt_header(slide, title_en: str, title_cn: str):
    add_textbox(slide, Inches(9.55), Inches(0.38), Inches(3.45), Inches(0.35), str(title_en or title_cn)[:42], 12, INK)


def build_pptx(data: Dict[str, Any], out_pptx: Path, data_base: Path) -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]
    project = data.get("project", {})

    for index, spec in enumerate(data.get("slides", []), 1):
        slide = prs.slides.add_slide(blank)
        typ = spec.get("type", "rendering")
        title_cn = spec.get("title_cn", project.get("title_cn", ""))
        title_en = spec.get("title_en", project.get("title_en", ""))

        if typ in ("cover", "chapter"):
            add_rect(slide, Inches(7.2), Inches(1.2), Inches(5.3), Inches(5.3), PALE_BLUE, 35)
            if typ == "cover":
                add_textbox(slide, Inches(0.75), Inches(0.55), Inches(6.2), Inches(0.35), spec.get("title_en", project.get("title_en")), 13, GRAY)
                add_textbox(slide, Inches(0.75), Inches(1.0), Inches(7.9), Inches(1.75), spec.get("title_cn", project.get("title_cn")), 38, INK, True)
                add_rect(slide, Inches(0.75), Inches(2.8), Inches(3.7), Inches(0.03), INK)
                add_textbox(slide, Inches(0.75), Inches(3.05), Inches(7.45), Inches(0.82), spec.get("subtitle_cn", project.get("subtitle_cn")), 19, INK)
                x = Inches(0.75)
                for item in spec.get("items", [])[:3]:
                    add_rect(slide, x, Inches(5.75), Inches(0.02), Inches(0.55), BLUE)
                    add_textbox(slide, x + Inches(0.12), Inches(5.7), Inches(2.35), Inches(0.58), item_title(item, "title_cn"), 11, INK)
                    x += Inches(2.55)
                add_textbox(slide, Inches(0.75), Inches(6.75), Inches(2), Inches(0.3), project.get("date", ""), 11)
                add_textbox(slide, Inches(0.75), Inches(7.02), Inches(5), Inches(0.25), project.get("company_cn", ""), 6, GRAY)
            else:
                add_textbox(slide, Inches(7.25), Inches(3.0), Inches(1.5), Inches(0.8), spec.get("chapter_no", "01"), 44, INK, True)
                add_textbox(slide, Inches(8.6), Inches(3.05), Inches(3.5), Inches(0.45), title_en, 20)
                add_textbox(slide, Inches(8.6), Inches(3.55), Inches(3.5), Inches(0.45), title_cn, 22)
                add_textbox(slide, Inches(8.6), Inches(4.55), Inches(3.5), Inches(1.2), "\n".join(map(str, spec.get("items", []))), 11, GRAY)
            continue

        if typ == "toc":
            x = Inches(7.2)
            for item in spec.get("items", []):
                add_textbox(slide, x, Inches(3.25), Inches(1.5), Inches(0.35), item_title(item, "title_en"), 9, GRAY)
                add_textbox(slide, x, Inches(3.55), Inches(1.5), Inches(0.35), item_title(item, "title_cn"), 10, INK)
                x += Inches(1.35)
            continue

        if typ == "plan":
            ppt_header(slide, title_en, title_cn)
            add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(0.5), Inches(0.8), Inches(8.2), Inches(6.1), "PLAN IMAGE TBD")
            add_textbox(slide, Inches(9.1), Inches(2.0), Inches(2.6), Inches(0.5), "空间功能", 20)
            y = Inches(3.0)
            for item in spec.get("items", []):
                add_rect(slide, Inches(9.1), y, Inches(0.45), Inches(0.12), PALE_BLUE, 0)
                add_textbox(slide, Inches(9.75), y - Inches(0.08), Inches(2.4), Inches(0.25), item_title(item, "title_cn"), 11)
                add_textbox(slide, Inches(9.75), y + Inches(0.15), Inches(2.4), Inches(0.22), item_title(item, "title_en"), 7, GRAY)
                y += Inches(0.48)
            continue

        if typ == "journey":
            ppt_header(slide, title_en, title_cn)
            add_textbox(slide, Inches(0.65), Inches(1.2), Inches(3.2), Inches(0.45), title_cn, 22)
            add_rect(slide, Inches(2.2), Inches(4.2), Inches(10.2), Inches(0.04), BLUE)
            count = max(len(spec.get("items", [])), 1)
            for i, item in enumerate(spec.get("items", [])):
                x = Inches(2.2 + i * (10.0 / max(count - 1, 1)))
                circ = slide.shapes.add_shape(MSO_SHAPE.OVAL, x, Inches(4.0), Inches(0.18), Inches(0.18))
                circ.fill.solid()
                circ.fill.fore_color.rgb = RGBColor(20, 27, 66)
                circ.line.fill.background()
                add_textbox(slide, x - Inches(0.45), Inches(4.45), Inches(1.2), Inches(0.35), item_title(item, "title_cn"), 10)
                add_textbox(slide, x - Inches(0.45), Inches(4.75), Inches(1.2), Inches(0.3), item_title(item, "title_en"), 6, GRAY)
            continue

        if typ == "materials":
            ppt_header(slide, title_en, title_cn)
            labels = spec.get("items", [])
            positions = [(0.45, 1.25), (4.55, 1.25), (8.65, 1.25), (0.45, 4.15), (4.55, 4.15), (8.65, 4.15)]
            for i, (x, y) in enumerate(positions):
                add_placeholder(slide, Inches(x), Inches(y), Inches(3.65), Inches(1.85), item_title(labels[i], "title_cn") if i < len(labels) else "MATERIAL")
            continue

        if typ == "content":
            layout = content_layout(spec, index)
            ppt_header(slide, title_en, title_cn)
            add_rect(slide, Inches(8.3), Inches(1.2), Inches(3.8), Inches(3.8), PALE_BLUE, 45)
            items = spec.get("items", [])
            add_textbox(slide, Inches(0.7), Inches(0.95), Inches(5.2), Inches(0.32), title_en, 10, GRAY)
            add_textbox(slide, Inches(0.7), Inches(1.28), Inches(6.85), Inches(1.05), title_cn, 28, INK, True)
            lead = item_title(items[0], "title_cn") if items else ""
            if layout == "statement":
                add_textbox(slide, Inches(0.7), Inches(2.75), Inches(6.2), Inches(1.15), lead, 19, INK)
                add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(0.7), Inches(4.55), Inches(5.8), Inches(1.55), "PLANNING IMAGE TBD")
                y = Inches(4.65)
                for i, item in enumerate(items[1:5], 1):
                    add_rect(slide, Inches(7.2), y, Inches(4.5), Inches(0.02), INK)
                    add_textbox(slide, Inches(7.2), y + Inches(0.16), Inches(0.5), Inches(0.25), f"{i:02d}", 10, BLUE)
                    add_textbox(slide, Inches(7.75), y + Inches(0.08), Inches(4.0), Inches(0.48), item_title(item, "title_cn"), 14)
                    y += Inches(0.62)
            elif layout == "metrics":
                x = Inches(0.75)
                for i, item in enumerate(items[:4], 1):
                    add_rect(slide, x, Inches(3.02), Inches(2.6), Inches(0.03), BLUE)
                    value, label = metric_parts(item, i)
                    add_textbox(slide, x, Inches(3.22), Inches(2.5), Inches(0.65), value, 26, INK, True)
                    add_textbox(slide, x, Inches(3.92), Inches(2.55), Inches(0.75), label, 12, GRAY)
                    x += Inches(3.05)
                add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(0.75), Inches(5.25), Inches(11.4), Inches(1.35), "PLANNING IMAGE TBD")
            elif layout == "matrix":
                if lead:
                    add_textbox(slide, Inches(0.7), Inches(2.58), Inches(5.6), Inches(1.15), lead, 16, GRAY)
                add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(0.7), Inches(4.2), Inches(5.6), Inches(2.0), "PLANNING IMAGE TBD")
                positions = [(7.05, 1.75), (9.6, 1.75), (7.05, 4.0), (9.6, 4.0)]
                for i, item in enumerate(items[1:5], 1):
                    x, y = positions[i - 1]
                    add_rect(slide, Inches(x), Inches(y), Inches(2.25), Inches(1.55), PALE_LAV if i in (2, 3) else PALE_BLUE, 15)
                    add_textbox(slide, Inches(x + 0.15), Inches(y + 0.18), Inches(0.5), Inches(0.25), f"{i:02d}", 10, BLUE)
                    add_textbox(slide, Inches(x + 0.15), Inches(y + 0.52), Inches(1.9), Inches(0.78), item_title(item, "title_cn"), 12)
            elif layout == "timeline":
                if lead:
                    add_textbox(slide, Inches(0.7), Inches(2.55), Inches(5.6), Inches(0.9), lead, 15, GRAY)
                add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(7.55), Inches(1.65), Inches(4.4), Inches(1.55), "PLANNING IMAGE TBD")
                add_rect(slide, Inches(0.95), Inches(4.55), Inches(11.2), Inches(0.04), BLUE)
                timeline_items = items[1:6]
                step = 10.4 / max(len(timeline_items) - 1, 1)
                for i, item in enumerate(timeline_items, 1):
                    x = Inches(0.95 + (i - 1) * step)
                    dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, x, Inches(4.43), Inches(0.23), Inches(0.23))
                    dot.fill.solid()
                    dot.fill.fore_color.rgb = RGBColor(20, 27, 66)
                    dot.line.fill.background()
                    add_textbox(slide, x, Inches(4.85), Inches(1.8), Inches(0.25), f"{i:02d}", 10, BLUE)
                    add_textbox(slide, x, Inches(5.12), Inches(1.9), Inches(0.72), item_title(item, "title_cn"), 10, INK)
            else:
                if lead:
                    add_textbox(slide, Inches(0.7), Inches(2.55), Inches(5.7), Inches(1.18), lead, 16, GRAY)
                add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(0.7), Inches(4.35), Inches(5.7), Inches(1.85), "PLANNING IMAGE TBD")
                y = Inches(1.75)
                for i, item in enumerate(items[1:7], 1):
                    add_rect(slide, Inches(7.05), y, Inches(4.9), Inches(0.01), LINE)
                    add_textbox(slide, Inches(7.05), y + Inches(0.12), Inches(0.45), Inches(0.25), f"{i:02d}", 10, BLUE)
                    add_textbox(slide, Inches(7.55), y + Inches(0.06), Inches(4.2), Inches(0.46), item_title(item, "title_cn"), 13)
                    y += Inches(0.72)
            continue

        if typ == "thanks":
            add_textbox(slide, Inches(4.2), Inches(2.8), Inches(2.4), Inches(0.9), "THANK\nYOU", 30, GRAY)
            add_textbox(slide, Inches(4.25), Inches(4.15), Inches(2.4), Inches(0.75), "谢谢", 34, INK, True)
            add_textbox(slide, Inches(6.8), Inches(3.0), Inches(3.2), Inches(0.8), project.get("title_cn", ""), 16)
            add_rect(slide, Inches(6.8), Inches(4.0), Inches(2.2), Inches(0.02), GRAY)
            add_textbox(slide, Inches(6.8), Inches(4.25), Inches(4.0), Inches(0.6), project.get("title_en", ""), 10, GRAY)
            continue

        ppt_header(slide, title_en, title_cn)
        add_picture_or_placeholder(slide, spec.get("locator"), data_base, Inches(0.25), Inches(0.25), Inches(1.6), Inches(1.0), "LOCATOR")
        add_picture_or_placeholder(slide, spec.get("image"), data_base, Inches(0), Inches(1.25), Inches(13.333), Inches(5.85), "RENDERING TBD")

    prs.save(out_pptx)


def build_reportlab_pdf(data: Dict[str, Any], out_pdf: Path, data_base: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    try:
        pdfmetrics.registerFont(TTFont("STHeiti", "/System/Library/Fonts/STHeiti Medium.ttc"))
        cn_font = "STHeiti"
    except Exception:
        cn_font = "Helvetica"

    page_w, page_h = landscape(A3)
    c = canvas.Canvas(str(out_pdf), pagesize=(page_w, page_h))
    project = data.get("project", {})

    def mm(v: float) -> float:
        return v * 72 / 25.4

    def text(x, y, value, size=18, color=colors.black, font=None):
        c.setFillColor(color)
        c.setFont(font or cn_font, size)
        c.drawString(mm(x), page_h - mm(y), str(value or ""))

    def header(spec):
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 14)
        c.drawRightString(mm(396), page_h - mm(24), str(spec.get("title_en") or spec.get("title_cn") or "")[:42])

    def placeholder(x, y, w, h, label):
        c.setFillColor(colors.HexColor("#e8ecef"))
        c.setStrokeColor(colors.HexColor("#d7dbe2"))
        c.rect(mm(x), page_h - mm(y + h), mm(w), mm(h), fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#8a8a8a"))
        c.setFont(cn_font, 16)
        c.drawCentredString(mm(x + w / 2), page_h - mm(y + h / 2), label)

    def image_or_placeholder(raw, x, y, w, h, label):
        p = resolve_path(raw, data_base)
        if p:
            c.drawImage(str(p), mm(x), page_h - mm(y + h), width=mm(w), height=mm(h), preserveAspectRatio=True, anchor="c")
        else:
            placeholder(x, y, w, h, label)

    for index, spec in enumerate(data.get("slides", []), 1):
        typ = spec.get("type", "rendering")
        c.setFillColor(colors.HexColor("#fbfcfc"))
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        c.setFillColor(colors.Color(0.75, 0.86, 1.0, alpha=0.35))
        c.circle(mm(315), page_h - mm(182), mm(64), fill=1, stroke=0)

        if typ == "cover":
            c.setFont("Helvetica", 35)
            c.setFillColor(colors.black)
            text(28, 34, spec.get("title_en", project.get("title_en", "")), 16, colors.HexColor("#777777"), "Helvetica")
            y = 62
            for line in str(spec.get("title_cn", project.get("title_cn", ""))).splitlines()[:3]:
                text(28, y, line, 50)
                y += 24
            c.setStrokeColor(colors.black)
            c.line(mm(28), page_h - mm(y), mm(200), page_h - mm(y))
            y += 14
            text(28, y, spec.get("subtitle_cn", project.get("subtitle_cn", "")), 25)
            x = 28
            for item in spec.get("items", [])[:3]:
                c.setStrokeColor(colors.HexColor("#315cff"))
                c.setLineWidth(mm(0.45))
                c.line(mm(x), page_h - mm(238), mm(x), page_h - mm(254))
                text(x + 4, 246, item_title(item, "title_cn"), 12)
                x += 78
            text(28, 272, project.get("date", ""), 14)
            text(28, 284, project.get("company_cn", ""), 8)
            c.showPage()
            continue

        if typ == "toc":
            x = 250
            for item in spec.get("items", []):
                text(x, 140, item_title(item, "title_en"), 10, colors.HexColor("#7d7d7d"), "Helvetica")
                text(x, 148, item_title(item, "title_cn"), 11)
                x += 36
            c.showPage()
            continue

        if typ == "chapter":
            text(250, 144, spec.get("chapter_no", "01"), 50, font="Helvetica")
            text(302, 144, spec.get("title_en", ""), 22, font="Helvetica")
            text(302, 160, spec.get("title_cn", ""), 24)
            y = 190
            for item in spec.get("items", []):
                text(302, y, item, 12, colors.HexColor("#555555"))
                y += 8
            c.showPage()
            continue

        header(spec)

        if typ == "plan":
            image_or_placeholder(spec.get("image"), 20, 42, 270, 220, "PLAN IMAGE TBD")
            text(305, 96, "空间功能", 22)
            y = 124
            for item in spec.get("items", []):
                c.setFillColor(colors.HexColor(item.get("color", "#dff7fb") if isinstance(item, dict) else "#dff7fb"))
                c.rect(mm(305), page_h - mm(y), mm(18), mm(4), fill=1, stroke=0)
                text(330, y, item_title(item, "title_cn"), 12)
                y += 14
            c.showPage()
            continue

        if typ == "journey":
            text(22, 64, spec.get("title_cn", ""), 26)
            text(22, 78, spec.get("title_en", ""), 18, colors.HexColor("#888888"), "Helvetica")
            c.setStrokeColor(colors.HexColor("#315cff"))
            c.setLineWidth(mm(1.2))
            c.line(mm(70), page_h - mm(162), mm(390), page_h - mm(162))
            items = spec.get("items", [])
            step = 300 / max(len(items) - 1, 1)
            for i, item in enumerate(items):
                x = 70 + i * step
                c.setFillColor(colors.HexColor("#141b42"))
                c.circle(mm(x), page_h - mm(162), mm(3.2), fill=1, stroke=0)
                text(x - 10, 184, item_title(item, "title_cn"), 12)
                text(x - 10, 192, item_title(item, "title_en"), 7, colors.HexColor("#888888"), "Helvetica")
            c.showPage()
            continue

        if typ == "materials":
            labels = spec.get("items", [])
            positions = [(18, 58), (145, 58), (272, 58), (18, 154), (145, 154), (272, 154)]
            for i, (x, y) in enumerate(positions):
                placeholder(x, y, 118, 66, "")
                pill = item_title(labels[i], "title_cn") if i < len(labels) else "材料"
                c.setFillColor(colors.white)
                c.roundRect(mm(x + 10), page_h - mm(y + 18), mm(45), mm(8), mm(4), fill=1, stroke=0)
                text(x + 14, y + 16, pill, 9)
            c.showPage()
            continue

        if typ == "content":
            layout = content_layout(spec, index)
            text(24, 50, spec.get("title_en", ""), 13, colors.HexColor("#777777"), "Helvetica")
            title_lines = str(spec.get("title_cn", "")).splitlines() or [str(spec.get("title_cn", ""))]
            y_title = 68
            for line in title_lines[:2]:
                text(24, y_title, line, 34)
                y_title += 16
            items = spec.get("items", [])
            lead = item_title(items[0], "title_cn") if items else ""
            if layout == "statement":
                text(24, 128, lead, 23, colors.HexColor("#333333"))
                image_or_placeholder(spec.get("image"), 24, 210, 176, 54, "PLANNING IMAGE TBD")
                y = 166
                for i, item in enumerate(items[1:5], 1):
                    c.setStrokeColor(colors.black)
                    c.line(mm(250), page_h - mm(y), mm(390), page_h - mm(y))
                    text(250, y + 10, f"{i:02d}", 11, colors.HexColor("#315cff"), "Helvetica")
                    text(267, y + 10, item_title(item, "title_cn"), 15)
                    y += 26
            elif layout == "metrics":
                x = 24
                for i, item in enumerate(items[:4], 1):
                    c.setStrokeColor(colors.HexColor("#315cff"))
                    c.setLineWidth(mm(0.45))
                    c.line(mm(x), page_h - mm(118), mm(x + 80), page_h - mm(118))
                    value, label = metric_parts(item, i)
                    text(x, 140, value, 32)
                    text(x, 158, label, 13, colors.HexColor("#555555"))
                    x += 96
                image_or_placeholder(spec.get("image"), 24, 210, 372, 58, "PLANNING IMAGE TBD")
            elif layout == "matrix":
                if lead:
                    text(24, 116, lead, 17, colors.HexColor("#555555"))
                image_or_placeholder(spec.get("image"), 24, 190, 172, 76, "PLANNING IMAGE TBD")
                positions = [(225, 72), (310, 72), (225, 160), (310, 160)]
                for i, item in enumerate(items[1:5], 1):
                    x, y = positions[i - 1]
                    c.setFillColor(colors.HexColor("#dff7fb" if i in (1, 4) else "#ded6ff"))
                    c.rect(mm(x), page_h - mm(y + 62), mm(76), mm(62), fill=1, stroke=0)
                    text(x + 6, y + 16, f"{i:02d}", 11, colors.HexColor("#315cff"), "Helvetica")
                    text(x + 6, y + 34, item_title(item, "title_cn"), 15)
            elif layout == "timeline":
                if lead:
                    text(24, 112, lead, 17, colors.HexColor("#555555"))
                image_or_placeholder(spec.get("image"), 260, 82, 132, 58, "PLANNING IMAGE TBD")
                c.setStrokeColor(colors.HexColor("#315cff"))
                c.setLineWidth(mm(1))
                c.line(mm(32), page_h - mm(166), mm(388), page_h - mm(166))
                timeline_items = items[1:6]
                step = 330 / max(len(timeline_items) - 1, 1)
                for i, item in enumerate(timeline_items, 1):
                    x = 32 + (i - 1) * step
                    c.setFillColor(colors.HexColor("#141b42"))
                    c.circle(mm(x), page_h - mm(166), mm(3.4), fill=1, stroke=0)
                    text(x, 186, f"{i:02d}", 11, colors.HexColor("#315cff"), "Helvetica")
                    text(x, 198, item_title(item, "title_cn"), 13)
            else:
                if lead:
                    text(24, 112, lead, 17, colors.HexColor("#555555"))
                image_or_placeholder(spec.get("image"), 24, 190, 176, 76, "PLANNING IMAGE TBD")
                y = 88
                for i, item in enumerate(items[1:7], 1):
                    c.setStrokeColor(colors.HexColor("#d7dbe2"))
                    c.line(mm(225), page_h - mm(y), mm(390), page_h - mm(y))
                    text(225, y + 11, f"{i:02d}", 11, colors.HexColor("#315cff"), "Helvetica")
                    text(242, y + 11, item_title(item, "title_cn"), 15)
                    y += 24
            c.showPage()
            continue

        if typ == "thanks":
            text(132, 128, "THANK", 34, colors.HexColor("#888888"), "Helvetica")
            text(150, 146, "YOU", 34, colors.HexColor("#888888"), "Helvetica")
            text(132, 184, "谢谢", 48)
            text(220, 138, project.get("title_cn", ""), 18)
            text(220, 162, project.get("subtitle_cn", "方案文本"), 16)
            c.showPage()
            continue

        image_or_placeholder(spec.get("image"), 0, 58, 420, 220, "RENDERING TBD")
        c.showPage()

    c.save()


def build_pdf(data: Dict[str, Any], out_html: Path, out_pdf: Path, data_base: Path) -> None:
    try:
        from weasyprint import HTML

        HTML(filename=str(out_html), base_url=str(out_html.parent)).write_pdf(str(out_pdf))
    except Exception as exc:
        print(f"WeasyPrint unavailable, using ReportLab fallback PDF: {exc}")
        build_reportlab_pdf(data, out_pdf, data_base)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to project JSON file.")
    parser.add_argument("--out-dir", required=True, help="Output directory.")
    parser.add_argument("--formats", default="html,pptx,pdf", help="Comma-separated formats.")
    args = parser.parse_args()

    data_path = Path(args.data).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    slug = slugify(project.get("slug") or project.get("title_en") or project.get("title_cn") or "scheme-textbook")
    formats = {x.strip().lower() for x in args.formats.split(",") if x.strip()}

    out_html = out_dir / f"{slug}.html"
    out_pptx = out_dir / f"{slug}.pptx"
    out_pdf = out_dir / f"{slug}.pdf"

    if "html" in formats or "pdf" in formats:
        build_html(data, out_html, data_path.parent)
        print(out_html)
    if "pptx" in formats:
        build_pptx(data, out_pptx, data_path.parent)
        print(out_pptx)
    if "pdf" in formats:
        build_pdf(data, out_html, out_pdf, data_path.parent)
        print(out_pdf)


if __name__ == "__main__":
    main()
