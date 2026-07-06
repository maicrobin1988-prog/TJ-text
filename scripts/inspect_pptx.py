#!/usr/bin/env python3
"""Inspect a PPTX via OOXML and optionally seed a TJ-text project JSON."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def slide_number(path: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", path)
    return int(match.group(1)) if match else 0


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def guess_type(index: int, total: int, texts: List[str], image_count: int) -> str:
    joined = " ".join(texts).lower()
    if index == 1:
        return "cover"
    if index == total or "thank" in joined or "谢谢" in joined:
        return "thanks"
    if "目录" in joined or "contents" in joined or "content" in joined:
        return "toc"
    first = texts[0].strip() if texts else ""
    if image_count == 0 and len(texts) <= 8 and (re.match(r"^0[1-9]\b", first) or "chapter" in joined):
        return "chapter"
    if "plan" in joined or "平面" in joined:
        return "plan"
    if "material" in joined or "材料" in joined or "用材" in joined:
        return "materials"
    if "动线" in joined or "旅程" in joined or "journey" in joined:
        return "journey"
    if image_count >= 1:
        return "rendering"
    return "content"


def read_rels(zf: zipfile.ZipFile, slide_path: str) -> Dict[str, str]:
    rel_path = slide_path.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
    if rel_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rel_path))
    rels: Dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        rid = rel.attrib.get("Id", "")
        target = rel.attrib.get("Target", "")
        rels[rid] = target
    return rels


def inspect_pptx(pptx: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(pptx) as zf:
        slide_paths = sorted(
            [x for x in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", x)],
            key=slide_number,
        )
        slides = []
        for path in slide_paths:
            root = ET.fromstring(zf.read(path))
            texts = [clean_text(t.text or "") for t in root.findall(".//a:t", NS)]
            texts = [x for x in texts if x]
            rels = read_rels(zf, path)
            image_targets = [target for target in rels.values() if "../media/" in target or target.startswith("../media")]
            idx = slide_number(path)
            slides.append(
                {
                    "index": idx,
                    "type_guess": guess_type(idx, len(slide_paths), texts, len(image_targets)),
                    "text_count": len(texts),
                    "image_count": len(image_targets),
                    "texts": texts[:40],
                    "image_targets": image_targets,
                }
            )
        return {
            "source": str(pptx),
            "slide_count": len(slides),
            "slides": slides,
        }


def make_project_seed(summary: Dict[str, Any], pptx: Path) -> Dict[str, Any]:
    title = pptx.stem
    slides = []
    for slide in summary["slides"]:
        texts = slide["texts"]
        title_text = texts[0] if texts else f"第{slide['index']}页"
        slide_type = slide["type_guess"]
        slides.append(
            {
                "type": slide_type,
                "title_cn": title_text,
                "title_en": "TJ-TEXT",
                "items": [{"title_cn": x} for x in texts[1:7]],
                "notes": f"Seeded from source slide {slide['index']}; image_count={slide['image_count']}. Replace image paths manually when generating final output.",
            }
        )
    return {
        "project": {
            "slug": re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", title).strip("-") or "tj-text-project",
            "title_cn": title,
            "title_en": "TJ-TEXT PROJECT",
            "subtitle_cn": "方案文本",
            "subtitle_en": "SCHEME TEXT",
            "date": "",
            "company_cn": "上海同济建筑室内设计工程有限公司",
            "company_en": "SHANGHAI TONGJI ARCHITECTURAL INTERIOR DESIGN ENGINEERING CO., LTD.",
        },
        "slides": slides,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True, help="Input PPTX.")
    parser.add_argument("--out", required=True, help="Output outline JSON.")
    parser.add_argument("--project-json", help="Optional seeded TJ-text project JSON.")
    args = parser.parse_args()

    pptx = Path(args.pptx).expanduser().resolve()
    summary = inspect_pptx(pptx)
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)

    if args.project_json:
        project = make_project_seed(summary, pptx)
        project_out = Path(args.project_json).expanduser().resolve()
        project_out.parent.mkdir(parents=True, exist_ok=True)
        project_out.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        print(project_out)


if __name__ == "__main__":
    main()
