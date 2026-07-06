---
name: tj-text
description: TJ-text generates reusable interior design and commercial planning text books modeled on the company's Zhiyuan B Zone A3 landscape PDF style. Use when creating, rewriting, testing, or templating Chinese/English proposal decks, scheme text volumes, presentation books, HTML decks, PPTX files, PDF exports, or when inspecting an uploaded PPTX to seed a new deck.
---

# TJ-text

## Core Workflow

1. Confirm the project scope: building, floors, spaces, output formats, available drawings, renderings, material images, and whether the result is for client review or internal iteration.
2. Read `references/design-system.md` before designing slides or visual language.
3. Read `references/content-architecture.md` before writing the document outline or selecting page types.
4. If the user provides an existing PPTX, run `scripts/inspect_pptx.py` first to extract a slide outline and seed project JSON.
5. Prepare one structured project data file from `assets/sample-project.json`, replacing placeholder text and image paths.
6. Run `scripts/build_textbook.py` to generate HTML, PPTX, and PDF from the same data source.
7. Inspect the generated HTML and exported pages visually. Fix clipped text, overloaded legends, weak image crops, or pages that drift from the visual system.

## Output Rules

- Keep the base format as A3 landscape: 420mm x 297mm for HTML/PDF and 16:9 widescreen for PPTX.
- Preserve the company text-book feeling: sparse white space, thin typography, bilingual section labels, cool blue/violet light gradients, large renderings, and restrained analysis diagrams.
- Make the first page decisive: large Chinese project/theme title, concise subtitle, and short strategic points. Avoid tiny or overly loose cover typography.
- For text-heavy planning decks, rotate content layouts (`statement`, `metrics`, `matrix`, `split`, `timeline`) instead of repeating one page composition.
- Use Chinese as the main content language. Use English as a secondary label layer, not as a second full paragraph.
- Prefer one clear point per page. If a page needs more than six content items, split it.
- Never invent project facts. Mark missing data with `TBD` placeholders and ask for drawings/renderings/material lists when needed.

## Data And Scripts

- Start from `assets/sample-project.json`.
- Inspect an uploaded PPTX:

```bash
python /Users/hhb_t/Claude/.agents/skills/tj-text/scripts/inspect_pptx.py \
  --pptx path/to/input.pptx \
  --out path/to/outline.json \
  --project-json path/to/seed-project.json
```

- Run:

```bash
python /Users/hhb_t/Claude/.agents/skills/tj-text/scripts/build_textbook.py \
  --data path/to/project.json \
  --out-dir path/to/output
```

The script writes:

- `<slug>.html`: editable browser deck.
- `<slug>.pptx`: WPS/PowerPoint-editable deck.
- `<slug>.pdf`: printable PDF export. It tries WeasyPrint first for closer HTML fidelity, then falls back to a ReportLab A3 PDF if system libraries such as `libgobject` are missing.

## Quality Gate

Before delivery, verify:

- Cover, TOC, chapter dividers, plan pages, rendering pages, material pages, and closing page all share the same margins, header style, and bilingual hierarchy.
- Renderings occupy most of the slide on effect pages; text does not compete with image inspection.
- Plans use pale translucent zones and a right-side legend, not dense explanatory paragraphs.
- Material callouts use small white rounded labels with thin leader lines.
- PPTX remains editable enough for titles, labels, and captions.
