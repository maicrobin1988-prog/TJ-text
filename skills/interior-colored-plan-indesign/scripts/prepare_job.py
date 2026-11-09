#!/usr/bin/env python3
"""Validate a measured plan job and compile a safe ExtendScript entrypoint.

This does not infer room boundaries. Coordinates must be reviewed against the PDF.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(test, message):
    if not test:
        raise ValueError(message)


def point(p, label):
    require(isinstance(p, list) and len(p) == 2, f"{label}: expected [x, y]")
    require(all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in p),
            f"{label}: coordinates must be finite numbers")


def validate(job, base):
    require(job.get("mode") in ("demo", "final", "template"), "mode must be demo/final/template")
    require(isinstance(job.get("title"), str) and job["title"].strip(), "title is required")
    require(job.get("name", "plan").replace("-", "").replace("_", "").isalnum(),
            "name may contain letters, numbers, hyphens and underscores")
    presets = json.loads((ROOT / "assets/style-presets.json").read_text())
    if isinstance(presets, dict):
        presets = presets["styles"]
    by_id = {p["id"]: p for p in presets}
    ids = job.get("style_ids", ["B3"])
    require(isinstance(ids, list) and ids and len(ids) == len(set(ids)), "style_ids must be a nonempty unique list")
    require(all(s in by_id for s in ids), f"unknown style; available: {', '.join(by_id)}")
    maintenance = (job["mode"] == "demo" and job.get("fictional_fixture") is True
                   and job.get("library_maintenance") is True and not job.get("source"))
    if job.get("fictional_fixture") is True:
        require(maintenance, "fictional fixtures are only for source-free library maintenance")
    if job["mode"] == "demo" and not maintenance:
        require(bool(job.get("source")), "project comparison requires a real PDF source")
        require(job.get("project_demo_requested") is True,
                "show cached style options first; project demos require an explicit user request")
        require(isinstance(job.get("demo_request_evidence"), str) and bool(job["demo_request_evidence"].strip()),
                "record the actual user request for project comparisons in demo_request_evidence")
    if job["mode"] == "final":
        require(bool(job.get("source")), "selected-style production requires the real project PDF")
        require(len(ids) == 1, "final requires exactly one chosen style")
        require(job.get("geometry_reviewed") is True, "final requires geometry_reviewed=true after visual alignment review")
        require(job.get("selection", {}).get("confirmed") is True,
                "final requires selection.confirmed=true from an actual user choice")
        require(job["selection"].get("style_id") == ids[0], "selected style and style_ids disagree")
        require(isinstance(job["selection"].get("evidence"), str) and bool(job["selection"]["evidence"].strip()),
                "record the user's actual selection in selection.evidence")
    job["styles"] = [by_id[s] for s in ids]
    if job["mode"] == "template":
        require(not job.get("source"), "template must not contain a project source")
        job.setdefault("coordinate_size", [1000, 700])
    else:
        point(job.get("coordinate_size"), "coordinate_size")
        require(min(job["coordinate_size"]) > 0, "coordinate_size must be positive")
        require(bool(job.get("source")) or job.get("fictional_fixture") is True,
                "a real plan requires source; only explicitly fictional fixtures may omit it")
    w, h = job["coordinate_size"]
    rooms = job.get("rooms", [])
    require(isinstance(rooms, list), "rooms must be a list")
    if job["mode"] == "final":
        require(bool(rooms) and bool(job.get("zones")), "final requires reviewed rooms and colored zones")
    codes = []
    for i, room in enumerate(rooms):
        require(isinstance(room.get("name"), str) and bool(room["name"].strip()), f"room {i}: name required")
        require(str(room.get("id", "")).strip() != "", f"room {i}: id required")
        room["id"] = str(room["id"])
        codes.append(room["id"])
        point(room.get("anchor"), f"room {room['id']} anchor")
        x, y = room["anchor"]
        require(0 <= x <= w and 0 <= y <= h, f"room {room['id']}: anchor outside coordinate_size")
        require(bool(room.get("source_label")) or job.get("fictional_fixture") is True,
                f"room {room['id']}: record source_label/page or confirmed text evidence")
        if job["mode"] == "final":
            require(room.get("status") == "verified", f"room {room['id']}: explicitly verify name/geometry")
    require(len(codes) == len(set(codes)), "room ids must be unique; repeated functions need distinct room ids")
    polygons = job.get("zones", []) + job.get("emphasis", [])
    for i, zone in enumerate(polygons):
        pts = zone.get("polygon")
        require(isinstance(pts, list) and len(pts) >= 3, f"zone {i}: closed polygon needs at least 3 vertices")
        for p in pts:
            point(p, f"zone {i}")
            require(0 <= p[0] <= w and 0 <= p[1] <= h, f"zone {i}: polygon outside coordinate_size")
        area = abs(sum(pts[j][0] * pts[(j+1) % len(pts)][1] - pts[(j+1) % len(pts)][0] * pts[j][1]
                       for j in range(len(pts)))) / 2
        require(area > 0, f"zone {i}: zero-area polygon")
        if "room_id" in zone:
            require(str(zone["room_id"]) in codes, f"zone {i}: unknown room_id")
        if "style_ids" in zone:
            require(all(s in by_id for s in zone["style_ids"]), f"zone {i}: invalid style_ids")
        if zone.get("texture_image"):
            src = (base / zone["texture_image"]).resolve()
            require(src.is_file(), f"texture missing: {src}")
            zone["_resolved_texture"] = str(src)
    for i, line in enumerate(job.get("walls", []) + job.get("lines", [])):
        point(line.get("a"), f"line {i}.a")
        point(line.get("b"), f"line {i}.b")
        require(all(0 <= p[0] <= w and 0 <= p[1] <= h for p in [line["a"], line["b"]]),
                f"line {i}: endpoint outside coordinate_size")
    for i, item in enumerate(job.get("furniture", [])):
        require(item.get("shape") in ("rect", "ellipse", "plant"), f"furniture {i}: unknown shape")
        b = item.get("bounds")
        require(isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in b),
                f"furniture {i}: bounds=[x,y,width,height]")
        require(b[2] > 0 and b[3] > 0, f"furniture {i}: width and height must be positive")
        require(b[0] >= 0 and b[1] >= 0 and b[0]+b[2] <= w and b[1]+b[3] <= h,
                f"furniture {i}: bounds outside coordinate_size")
    if job.get("source"):
        source = job["source"]
        require(source.get("normalized") is True, "run inspect_pdf.py and use its normalized_plan.pdf")
        p = (base / source["path"]).resolve()
        require(p.is_file() and p.suffix.lower() == ".pdf", "source.path must be an existing PDF")
        import fitz
        with fitz.open(p) as doc:
            require(len(doc) == 1 and doc[0].rotation == 0, "normalized source must be one page with rotation=0")
            page = doc[0]
            require(all(abs(float(a)-float(b)) < .1 for a, b in zip(page.mediabox, [0, 0, w, h])),
                    "normalized source MediaBox must be [0,0,width,height]")
            require(all(abs(float(a)-float(b)) < .1 for a, b in zip(page.cropbox, page.mediabox)),
                    "normalized source CropBox must equal MediaBox; run inspect_pdf.py")
            require(abs(page.rect.width - w) < .1 and abs(page.rect.height - h) < .1,
                    "coordinate_size does not match normalized PDF (points)")
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if source.get("sha256"):
            require(source["sha256"] == sha, "source PDF hash changed; review geometry before rebuilding")
        source["sha256"] = sha
        source["_resolved"] = str(p)
    job.setdefault("name", "plan")
    job.setdefault("subtitle", "")
    job.setdefault("rooms", [])
    job.setdefault("zones", [])
    job.setdefault("walls", [])
    job.setdefault("lines", [])
    job.setdefault("furniture", [])
    job.setdefault("emphasis", [])
    return job


def compile_job(input_path: Path, output: Path):
    require(not output.exists(), f"output directory already exists: {output}; choose a new revision directory")
    job = validate(json.loads(input_path.read_text(encoding="utf-8")), input_path.parent)
    output.mkdir(parents=True)
    (output / "Links").mkdir()
    if job.get("source"):
        src = Path(job["source"].pop("_resolved"))
        target = output / "Links" / "normalized_plan.pdf"
        shutil.copy2(src, target)
        job["source"]["path"] = str(target)
    for i, zone in enumerate(job.get("zones", [])):
        if zone.get("texture_image"):
            src = Path(zone.pop("_resolved_texture"))
            target = output / "Links" / (f"texture_{i:03d}" + src.suffix.lower())
            shutil.copy2(src, target)
            zone["texture_image"] = str(target)
    job["output_dir"] = str(output)
    (output / "job.resolved.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "rooms.json").write_text(json.dumps(job["rooms"], ensure_ascii=False, indent=2), encoding="utf-8")
    renderer = ROOT / "scripts/render_indesign.jsx"
    # JSON is encoded as an object literal, never inserted into shell commands or eval strings.
    content = "var CP_JOB = " + json.dumps(job, ensure_ascii=True, allow_nan=False) + ";\n"
    content += "$.evalFile(File(" + json.dumps(str(renderer), ensure_ascii=True) + "));\n"
    (output / "run.jsx").write_text(content, encoding="utf-8")
    print(output / "run.jsx")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("job", type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    compile_job(args.job.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()
