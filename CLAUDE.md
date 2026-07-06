# CLAUDE.md

This repository contains the `TJ-text` reusable agent skill.

Claude-style agents should treat `SKILL.md` as the primary instruction file and use `AGENTS.md` for command shortcuts. The core workflow is:

1. Read `SKILL.md`.
2. Load `references/design-system.md` and `references/content-architecture.md` when generating or revising a deck.
3. Create or edit a project JSON based on `assets/sample-project.json`.
4. Run `scripts/inspect_pptx.py` when a PPTX source is provided.
5. Run `scripts/build_textbook.py` to generate HTML, PPTX, and PDF.

Use relative paths from the repository root. Do not rely on machine-specific absolute paths.
