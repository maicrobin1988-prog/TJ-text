# Content Architecture Reference

Use this when turning a project brief into a reusable scheme text book.

## Default Document Arc

1. Cover
2. Contents or chapter index
3. Project image / future workplace mood
4. Design concept or visual reference collage
5. Chapter 01: Lobby / arrival / first impression
6. Functional positioning and floor logic
7. Plans and spatial function analysis
8. User journey or emotional experience
9. Chapter 02: Standard office / work floor
10. Standard floor plans and option comparison
11. Rendering sequence by space
12. Meeting, collaboration, tea, service, restroom, and support spaces
13. Material and key finish callouts
14. Communication optimization or issue response pages
15. Closing

## Page Selection Guide

- Use `cover` once at the beginning.
- Use `toc` only when the deck has three or more chapters.
- Use `chapter` whenever shifting from one major spatial group to another.
- Use `plan` for each floor or option that must be reviewed for decision making.
- Use `journey` when the concept depends on user sequence, emotion, service, arrival, or brand experience.
- Use `rendering` for the main design proof. One page should contain one dominant viewpoint.
- Use `content` for commercial planning, strategy, market, financial model, risk, executive summary, or other text-heavy pages without drawings/renderings.
- Use `rendering-index` when several renderings correspond to one plan.
- Use `materials` when the project requires construction or finish decisions.
- Use `optimization` for before/after, client comments, value engineering, or design revision notes.
- Use `thanks` once at the end.

## Writing Style

- Keep headings concrete: `1F PLAN / 首层平面方案`, `RENDERING / 接待大厅效果图`.
- Write Chinese page titles as nouns, not slogans.
- English is a compact functional tag: `SPATIAL FUNCTION`, `USER JOURNEY`, `MATERIAL`, `COMMUNICATION OPTIMIZATION`.
- Use short bilingual item labels for diagrams. Example:
  - `机器人交互区 / MACHINE INTERACTION ZONE`
  - `会议谈话区 / MEETING CONVERSATION AREA`
- For renderings, use captions only when they clarify viewpoint or design intent.
- For material pages, list by surface: ceiling, wall, floor, cabinet, door, signage, lighting.

## Required Inputs

- Project name in Chinese and English.
- Scope: building, floors, area, phase, and date.
- Chapter list and floor/space list.
- CAD/PDF plan exports or plan images.
- Renderings with desired order and viewpoint names.
- Material list and finish image references.
- Client comments or optimization notes if a comparison chapter is needed.

## Data Model

Use `assets/sample-project.json` as the canonical input. Each slide has:

- `type`: page family.
- `title_cn`, `title_en`: page title.
- `chapter_no`: optional large chapter number.
- `image`: optional dominant image path. On `content` pages, this fills the reserved planning image/diagram slot; when omitted, the generator keeps a `PLANNING IMAGE TBD` placeholder for later editing.
- `images`: optional array for grids or callouts.
- `items`: short bullets, legend entries, or chapter topics.
- `notes`: internal generation guidance; do not show unless explicitly needed.
- `layout`: optional content page variant for `content` pages. Use `statement`, `metrics`, `matrix`, `split`, or `timeline`; omit it to let `inspect_pptx.py` rotate variants automatically.

## Content Page Layouts

- `statement`: use for executive summary, decision recommendation, central judgment, positioning, and one-strong-thesis pages. Make the Chinese judgment the main visual event.
- `metrics`: use for market, rent, financial model, area, floor, percentage, and other quantitative pages. Only enlarge real numbers; otherwise use 01/02/03 markers.
- `matrix`: use for current status, risk checklist, customer groups, product systems, and four-part comparison.
- `split`: use for mixed explanation plus several supporting points.
- `timeline`: use for implementation path, roadmap, decision sequence, phased upgrade, or journey-like strategic logic.
- Every `content` layout reserves a modifiable image area. Use it for planning diagrams, site photos, cropped plans, precedent references, tenant mix charts, or leave it as a visible placeholder until the image is ready.
- Keep content hierarchy direct: large Chinese title, readable lead statement, then proof points. Do not shrink the whole page to fit extra copy; split pages instead.

## Output Fidelity Notes

- HTML/PDF should be visually closest to the source text-book system.
- PPTX should prioritize editability of text and labels. Image masks and soft gradients may be simplified.
- If the project has no renderings yet, generate a wireframe deck with image placeholders and clear missing-asset notes.
