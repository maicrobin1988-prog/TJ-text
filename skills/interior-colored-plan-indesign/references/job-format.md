# 作业数据与执行

依赖 Python 3、PyMuPDF（`fitz`）及本机 InDesign。默认顺序是**预存选项 → 实际用户选择 → 一次单款制作**。`prepare_job.py` 不识别空间，只把看图核实的数据与已选风格编译为 JSX。

## 1. 选样时只读缓存

```bash
python3 /absolute/skill/scripts/show_style_options.py
```

读取返回的 `preview_path`，用宿主图片预览/附件展示；支持本地 Markdown 图片时可用 `preview_markdown`。选择问题与选项见 `question` / `choices`；Codex 可把可用的 `request_user_input_async_args` 交给同名工具，其他宿主用已有单选工具或直接回复样式号。用户只选 B/D 父类时才加 `--group B` / `--group D` 查看预存子款。脚本不读项目 PDF、不创建输出目录、不调用 InDesign、不重新生成图片。

选样前不编写项目 job，也不执行下列检查/制作命令。已有明确选择时跳过此步。界面预选或未回复不构成选择。

## 2. 选定后处理真实 PDF

```bash
python3 /absolute/skill/scripts/inspect_pdf.py /project/plan.pdf --page 1 --out /project/work/plan_inspect_R01
```

输出 `inspect.json`、`preview.png`、`extracted_text.txt`、`normalized_plan.pdf`。看图核对房间；扫描或轮廓字需要视觉识读/OCR。坐标使用归一化可视页左上角为原点、x右y下、单位 pt 的 `bbox_display_pt`，不是 PNG 像素。归一化保留可见外观，交互和签名语义不保留；原件不改。

在真实选择后建立单款 job。以下只解释格式，尺寸、房间、坐标和选择证据必须替换成实际数据；不能照抄示例选择来冒充用户回复。

```json
{
  "mode": "final",
  "name": "project_floor_R01",
  "title": "项目名称 · 首层彩平",
  "subtitle": "方案版本 R01",
  "style_ids": ["A1"],
  "selection": {"confirmed": true, "style_id": "A1", "evidence": "用户实际回复：选 A1"},
  "geometry_reviewed": true,
  "coordinate_size": [1000, 700],
  "source": {"path": "plan_inspect_R01/normalized_plan.pdf", "normalized": true},
  "rooms": [
    {"id": "01", "name": "接待区", "anchor": [120, 180], "source_label": "源PDF第1页文字：接待区", "status": "verified"}
  ],
  "zones": [
    {"room_id": "01", "polygon": [[40,40],[240,40],[240,250],[40,250]], "material": "stone"}
  ]
}
```

## 字段

| 字段 | 含义 |
|---|---|
| `mode` | `final` 选后的单款项目制作；`template` 空白版式；`demo` 仅图库维护或用户明确要求的项目对比 |
| `style_ids` | 正式项目只填一个已选 ID：A1/B1/B2/B3/C1/D1/D2/E1 |
| `selection` | `confirmed:true`、相同的 `style_id`、实际回复的非空 `evidence`；无需另有一轮项目 demo 或二次批准 |
| `geometry_reviewed` | 核对源图、边界与锚点后为 true；不能在未核图时直接预置 |
| `coordinate_size` | 归一化单页 PDF 宽高 `[w,h]`，pt；MediaBox=[0,0,w,h]，CropBox相同，旋转0 |
| `source` | 归一化单页 PDF 路径；可用 `sha256` 防止底图更新后继续套旧几何 |
| `rooms` | id唯一；name真实功能名；anchor编号中心；source_label来源证据；status核实状态；可有secondary/name_en/leader |
| `zones` | 原生闭合直线polygon、room_id、wood/stone/carpet分类；可有texture_image/opacity；C1室外区域才设environment:true；真实曲线用ID钢笔 |
| `walls` / `lines` | 经核实的线段a/b与源坐标width；lines可指定color，不自动提取或新增墙 |
| `furniture` | 原位细化对象shape=rect/ellipse/plant、bounds=[x,y,w,h]、可选round；不替换布局 |
| `emphasis` | 真实区域polygon、style_ids、role和opacity，用于动线/组团表达 |

材质图片置入原生裁切画框，图片仍是位图。默认比例填充只是起点，精制须调整方向与尺度。final 需非空房间/地坪清单、房间明确 verified 和核图标记；数据完整不代表视觉检查已完成。

## 3. 编译、制作与验收

下例使用 macOS 的 `python3`；Windows 可将 Python 命令换成 `py`，不要运行 osascript。

```bash
python3 /absolute/skill/scripts/prepare_job.py /project/job.json --out /project/output/final_R01
osascript -e 'tell application "Adobe InDesign 2025" to do script (POSIX file "/project/output/final_R01/run.jsx") language javascript'
```

Windows 在 InDesign 中打开“窗口 → 实用工具 → 脚本”，将本机编译的 `run.jsx` 放入用户脚本目录并运行；编译入口已引用本机当前技能的 `render_indesign.jsx`。此路线未在 Windows 真机端到端验证。宿主不能操作桌面时可交付已准备的入口并说明尚未执行，不能声称已生成 INDD。

输出 INDD（模板为INDT）、IDML、PDF、JPEG、rooms.json、job.resolved.json、audit.json 和 Links/。拒绝覆盖已有输出目录；运行入口引用当前 skill 绝对路径，迁移后重新编译。复制交付包后检查链接和原生重开，视觉检查单独记录。

## 受限的多款例外与维护

- 图库维护：`mode:demo`、`fictional_fixture:true`、`library_maintenance:true`，且**不能有 source**。使用 [demo-job.json](../assets/demo-job.json)，仅在更新/修复图库时运行，不能把真实项目冒充虚构夹具。
- 用户明确要求当前 PDF 多款比较：`mode:demo`、真实 source、`project_demo_requested:true`，并记录非空 `demo_request_evidence` 的实际请求。没有这项明确要求就拒绝项目 demo；“测试一下”不构成该例外。
- 空白 A3 模板使用 [template-job.json](../assets/template-job.json)，不要求风格选择，也不接项目 source。

编译器和 `render_indesign.jsx` 在启动 ID 文档操作前都检查这些门槛，调用本 renderer 的旧多款 run.jsx 也会被检查。独立的旧项目脚本应先改成只制作已选款式，不直接重跑。色彩参数见 [style-presets.json](../assets/style-presets.json)。脚本不执行OCR、房间分割、复杂曲线追踪或自动家具替换；仍需源图核对和原生精修。
