#!/usr/bin/env python3
"""Return cached style previews and native choice-card arguments; never open a project PDF."""
import argparse
import json
from pathlib import Path


def style_options(group=None):
    root = Path(__file__).resolve().parents[1] / "assets" / "style-picker"
    data = json.loads((root / "options.json").read_text(encoding="utf-8"))
    styles = data["styles"]
    preview = root / data["preview"]
    if group:
        selected = data["groups"][group]
        styles = [s for s in styles if s["id"] in selected["ids"]]
        preview = root / selected["preview"]
    if not preview.is_file():
        raise FileNotFoundError(f"预存简图缺失：{preview}；请修复图库，不要为新 PDF 生成多款小样替代。")
    choices = [f"{s['id']} {s['name']}｜{s['feature']}" for s in styles]
    title = "请选择一种彩平风格，选定后直接按这款制作你的 PDF。"
    if group:
        title = f"请选择 {group} 类的具体款式，选定后直接制作。"
    return {
        "workflow": data["workflow"],
        "preview_path": str(preview),
        "preview_markdown": f"![预存风格简图（非当前项目）]({preview})",
        "style_ids": [s["id"] for s in styles],
        "question": title,
        "choices": [{"id": s["id"], "name": s["name"], "feature": s["feature"], "label": label} for s, label in zip(styles, choices)],
        "display_hint": "Use the host image preview or attachment; markdown is optional.",
        "request_user_input_async_args": {"questions": [{"title": title, "options": choices}]},
        "fallback_prompt": "请回复样式号：" + " / ".join(s["id"] for s in styles),
        "next_action": "wait_for_actual_user_selection_then_produce_one_style",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=list("ABCDE"))
    args = parser.parse_args()
    print(json.dumps(style_options(args.group), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
