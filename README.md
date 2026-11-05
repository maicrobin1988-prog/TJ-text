# TJ-text

TJ-text is a reusable multi-agent skill for generating Chinese/English interior design and commercial planning text decks. It was distilled from a company A3 landscape scheme text-book style and supports:

- inspecting an existing PPTX and turning it into structured project JSON
- generating HTML, PPTX, and PDF outputs from one JSON source
- rotating multiple text-heavy planning layouts instead of repeating one slide style
- using large, clear cover typography and bilingual labels for proposal decks
- reserving editable planning-image placeholders on strategy/content pages

The machine-readable skill name is `tj-text`. The display name is `TJ-text`.

TJ-text can be used by Codex and by repository-based agents such as Open Cloud, Harness, Work Buddy, Claude-style agents, or any tool that can read a repo instruction file and run local Python scripts. Exact import UI varies by platform; the portable entry points are:

- `SKILL.md`: primary skill instructions
- `AGENTS.md`: generic agent instructions and commands
- `CLAUDE.md`: Claude-compatible entry point
- `agent-manifest.json`: machine-readable capability and command manifest
- `agents/openai.yaml`: OpenAI/Codex UI metadata

## 飞书案例解剖与归档

独立 Skill [`lark-case-library`](skills/lark-case-library/SKILL.md) 用于拆解设计案例 PDF，制作可搜索的飞书画板，并将画板和原始 PDF 归档到同一条多维表格记录。

在 Codex 中，可先克隆本仓库，再到需要使用该 Skill 的项目目录运行：

```bash
mkdir -p .agents/skills/lark-case-library
cp -R /path/to/TJ-text/skills/lark-case-library/. .agents/skills/lark-case-library/
```

把 `/path/to/TJ-text` 替换为实际克隆位置。在对话中使用 `$lark-case-library`，提供案例 PDF 及目标飞书案例库或单条记录链接。其他支持 `SKILL.md` 的 Agent 可导入整个 `skills/lark-case-library` 目录。同步新版时，更新仓库后重新复制该目录。

飞书案例资料和权限由各团队管理。执行云端归档需要调用者有对应画板、多维表格和附件的访问与写入能力。

## What It Produces

From a single project JSON file, TJ-text can generate:

- editable browser deck: `.html`
- WPS/PowerPoint-editable deck: `.pptx`
- printable A3 landscape file: `.pdf`

The PDF exporter tries WeasyPrint first. If the local system is missing WeasyPrint native libraries, it falls back to ReportLab.

## Install Dependencies

Required Python packages:

```bash
python3 -m pip install -r requirements.txt
```

Optional closer HTML-to-PDF rendering:

```bash
python3 -m pip install -r requirements-optional.txt
```

If WeasyPrint native libraries are unavailable, TJ-text still generates PDF through the ReportLab fallback.

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

## Install For Other Agents

For agents that support repository skills or custom instruction repositories, connect this GitHub repo:

```text
https://github.com/maicrobin1988-prog/TJ-text
```

Use these settings when the platform asks for them:

- Skill name: `tj-text`
- Display name: `TJ-text`
- Primary instruction file: `SKILL.md`
- Generic instruction file: `AGENTS.md`
- Manifest file: `agent-manifest.json`
- Working directory: repository root
- Required setup command: `python3 -m pip install -r requirements.txt`
- Main build command: `python3 scripts/build_textbook.py --data output/project.json --out-dir output/generated`

For platforms without a formal skill installer:

1. Clone the repository into the agent workspace.
2. Tell the agent to read `AGENTS.md` first, then `SKILL.md`.
3. Allow the agent to run Python scripts from the repo root.
4. Provide a project JSON or PPTX source file.

Example prompt:

```text
Use the TJ-text skill in this repository. Read AGENTS.md and SKILL.md, inspect my PPTX, create a project JSON, then generate HTML, PPTX, and PDF outputs.
```

## Platform Notes

- Open Cloud or OpenAI-style agents: use `SKILL.md` and `agents/openai.yaml` when a skill import flow is available.
- Claude-style agents: use `CLAUDE.md` or `AGENTS.md` as the repo instruction file.
- Harness / Work Buddy / generic work agents: use `agent-manifest.json` for capability discovery and `AGENTS.md` for executable instructions.
- If a platform only supports pasted instructions, paste the content of `AGENTS.md` and include the repository URL.

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
├── AGENTS.md
├── CLAUDE.md
├── agent-manifest.json
├── agents/openai.yaml
├── assets/sample-project.json
├── requirements.txt
├── requirements-optional.txt
├── references/content-architecture.md
├── references/design-system.md
└── scripts/
    ├── build_textbook.py
    └── inspect_pptx.py
```

## License

MIT. See `LICENSE`.
