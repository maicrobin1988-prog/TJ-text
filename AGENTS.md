# AGENTS.md

Use this repository as the `TJ-text` skill for generating Chinese/English interior design and commercial planning text books.

## Entry Point

1. Read `SKILL.md` first.
2. Read `references/design-system.md` before making visual or layout decisions.
3. Read `references/content-architecture.md` before creating or revising the deck outline.
4. Use `assets/sample-project.json` as the starting data model.

## Commands

Install required Python packages:

```bash
python3 -m pip install -r requirements.txt
```

Inspect an existing PPTX:

```bash
python3 scripts/inspect_pptx.py \
  --pptx path/to/input.pptx \
  --out output/outline.json \
  --project-json output/project.json
```

Build outputs:

```bash
python3 scripts/build_textbook.py \
  --data output/project.json \
  --out-dir output/generated
```

## Rules

- Keep Chinese as the main content language and English as a compact label layer.
- Do not invent project facts; mark missing information as `TBD`.
- Preserve the A3 landscape text-book language: sparse composition, cool accents, large hierarchy, and restrained diagrams.
- Keep content-page planning image placeholders visible unless the `image` field provides a replacement image.
- Verify generated PPTX, HTML, and PDF outputs before delivery.
