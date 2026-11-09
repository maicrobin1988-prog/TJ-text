#!/usr/bin/env python3
"""Build portable and WorkBuddy import ZIPs from this skill; Python standard library only."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "interior-colored-plan-indesign"
EXCLUDE = {".git", "dist", "__pycache__", ".DS_Store"}


def workbuddy_skill(text, version):
    # Dedicated WorkBuddy archive includes its published display/version metadata.
    # The canonical Agent Skills source keeps the portable frontmatter schema.
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.S)
    if not match:
        raise ValueError("SKILL.md frontmatter is missing")
    description = re.search(r"^description:\s*(.+)$", match[1], re.M)
    if not description:
        raise ValueError("SKILL.md description is missing")
    raw = description[1].strip()
    desc = json.loads(raw) if raw.startswith('"') else raw
    fields = {
        "name": NAME,
        "display_name": "室内彩平制作",
        "display_name_en": "Interior Colored Plan in InDesign",
        "description": desc,
        "description_zh": "先选预存风格简图，再依据平面PDF制作单款InDesign A3彩平及编号功能表。",
        "description_en": "Choose a cached style, then create one editable InDesign A3 colored floor plan from a PDF.",
        "version": version,
        "author": "maicrobin1988-prog",
    }
    header = "\n".join(key + ": " + json.dumps(value, ensure_ascii=False) for key, value in fields.items())
    return "---\n" + header + "\n---\n\n" + match[2]


def build(output):
    output = output.resolve()
    if output == ROOT:
        raise ValueError("Output must be a separate dist directory")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    files = [p for p in sorted(ROOT.rglob('*')) if p.is_file()
             and not any(part in EXCLUDE for part in p.relative_to(ROOT).parts)
             and not p.suffix == '.pyc' and not p.is_relative_to(output)]
    output.mkdir(parents=True, exist_ok=True)
    archives = []
    for target in ("portable", "workbuddy"):
        path = output / (NAME + '-' + target + '.zip')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for file in files:
                relative = file.relative_to(ROOT)
                name = relative.as_posix() if target == "workbuddy" else (Path(NAME) / relative).as_posix()
                data = file.read_bytes()
                if target == "workbuddy" and relative.as_posix() == "SKILL.md":
                    data = workbuddy_skill(data.decode('utf-8'), version).encode('utf-8')
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError("Archive verification failed: " + str(path))
        archives.append(path)
    sums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in archives)
    (output / 'SHA256SUMS.txt').write_text(sums, encoding='ascii')
    print(json.dumps({"version": version, "files": [str(p) for p in archives]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().out)
