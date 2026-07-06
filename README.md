# TJ-text

TJ-text is a reusable Codex skill for generating Chinese/English interior design and commercial planning text decks. It was distilled from a company A3 landscape scheme text-book style and supports:

- inspecting an existing PPTX and turning it into structured project JSON
- generating HTML, PPTX, and PDF outputs from one JSON source
- rotating multiple text-heavy planning layouts instead of repeating one slide style
- using large, clear cover typography and bilingual labels for proposal decks
- reserving editable planning-image placeholders on strategy/content pages

The machine-readable skill name is `tj-text`. The display name is `TJ-text`.

## What It Produces

From a single project JSON file, TJ-text can generate:

- editable browser deck: `.html`
- WPS/PowerPoint-editable deck: `.pptx`
- printable A3 landscape file: `.pdf`

The PDF exporter tries WeasyPrint first. If the local system is missing WeasyPrint native libraries, it falls back to ReportLab.

## Install For Codex

Clone this repository and copy it into your Codex skills directory:

```bash
git clone https://github.com/maicrobin1988-prog/TJ-text.git /tmp/TJ-text
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/tj-text
cp -R /tmp/TJ-text ~/.codex/skills/tj-text
```

Restart Codex after installing, then invoke it as:

```text
Use $tj-text to inspect this PPTX and generate a scheme text deck in HTML, PPTX, and PDF.
```

## Install In A Workspace

If your workspace uses a local `.agents/skills` folder, install it there:

```bash
git clone https://github.com/maicrobin1988-prog/TJ-text.git /tmp/TJ-text
mkdir -p .agents/skills
rm -rf .agents/skills/tj-text
cp -R /tmp/TJ-text .agents/skills/tj-text
```

## Requirements

Required:

- Python 3
- `python-pptx`
- `reportlab`

Recommended:

- `weasyprint` plus its native system libraries for closer HTML-to-PDF fidelity

Install Python packages:

```bash
python3 -m pip install python-pptx reportlab weasyprint
```

If WeasyPrint native libraries are unavailable, TJ-text still generates PDF through the ReportLab fallback.

## Inspect A PPTX

Use `inspect_pptx.py` to extract slide text, infer page types, and generate a seed project JSON:

```bash
python scripts/inspect_pptx.py \
  --pptx path/to/input.pptx \
  --out output/outline.json \
  --project-json output/project.json
```

The generated JSON assigns content-heavy pages to rotating layouts:

- `statement`
- `metrics`
- `matrix`
- `split`
- `timeline`

You can edit the generated JSON before building final outputs.

## Build Outputs

Generate HTML, PPTX, and PDF:

```bash
python scripts/build_textbook.py \
  --data output/project.json \
  --out-dir output/generated
```

Generate selected formats:

```bash
python scripts/build_textbook.py \
  --data output/project.json \
  --out-dir output/generated \
  --formats html,pptx
```

## Project JSON

Start from:

```text
assets/sample-project.json
```

Each slide supports fields such as:

- `type`: `cover`, `toc`, `chapter`, `content`, `plan`, `journey`, `rendering`, `materials`, `thanks`
- `layout`: for `content` pages, one of `statement`, `metrics`, `matrix`, `split`, `timeline`
- `title_cn`: main Chinese title
- `title_en`: compact English category label
- `items`: short content points, metrics, legends, or proof points
- `image`: optional dominant image path. On `content` pages, this replaces the reserved planning image/diagram placeholder.
- `images`: optional image array for grids or material callouts

Example content slide with a replaceable planning image slot:

```json
{
  "type": "content",
  "layout": "matrix",
  "title_cn": "商业功能重组策略",
  "title_en": "COMMERCIAL PLANNING",
  "image": "images/planning-diagram.png",
  "items": [
    {"title_cn": "以首层到达界面作为商业更新的第一触点"},
    {"title_cn": "沿街展示强化"},
    {"title_cn": "垂直交通识别"},
    {"title_cn": "业态组合优化"},
    {"title_cn": "运营导视联动"}
  ]
}
```

## Design Direction

TJ-text favors:

- A3 landscape composition
- large Chinese theme title on the first page
- stronger title/body hierarchy on content pages
- sparse white space
- bilingual technical labels
- cool blue/cyan/violet accents
- large renderings or diagrams when available
- reserved planning image positions that can be replaced by adding `image` paths
- multiple composition types for strategy-heavy pages

It avoids:

- tiny loose cover typography
- one repeated two-column layout for every text page
- dense consulting-slide card grids
- decorative gradients that overpower content

## Repository Structure

```text
.
├── SKILL.md
├── agents/openai.yaml
├── assets/sample-project.json
├── references/content-architecture.md
├── references/design-system.md
└── scripts/
    ├── build_textbook.py
    └── inspect_pptx.py
```

## License

No open-source license has been added yet. Contact the repository owner before redistributing or modifying beyond personal/internal installation.
