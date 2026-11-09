# InDesign 制作与验收

**仅在用户选定款式后执行本参考。** 选样前复用预存简图，不打开 InDesign、不完整读取/OCR PDF、不做描图或房间清单。

## 实际制作路线

1. 对照 PDF 原始页和预览读取功能文字，记录所用页、版本和证据。`inspect_pdf.py` 的归一化页只作为制作底图：保留原可见 CropBox、旋转外观和矢量，坐标起点改为左上角；原文件另存不改。
2. 在源显示坐标中描出区域轮廓，再统一等比映射到页面。不要各个房间分别“适应画框”或重置比例，已知尺寸才校准比例。只制作已选风格；复用旧项目脚本时先检查并移除写死的多页/多款循环，不能直接重跑上轮四款比较脚本。用户另明确要求项目多款对比时，各稿共享同一变换。
3. 在 ID 里以原生闭合 Polygon/钢笔路径制作地坪和材质画框。曲线用锚点及控制柄。素材置入该路径内部并按真实材质方向、尺度调整；不能用跨过墙体或门洞的大矩形遮盖边界。不要将微缩参考图里的贴图直接拉到大幅精稿。
4. PDF 置入锁定层。材质可在底图下、强化/编号在底图上。先检查 PDF 的白色填充：透明背景选项不负责删除内容中实际的白色对象。Multiply 可用于中性线稿叠合，但会影响原有颜色/灰面，需要渲染检查；效果不成立时重绘必要线稿或采用经过核对的线稿版本。不要盲目降低整张 PDF 的透明度让关键墙线消失。
5. 依据确认的原几何处理墙体切面、家具、地面拼缝、阴影和植物。保持门扇、柱、洁具、楼梯等逻辑。未获材料表时纹理是风格表达，不赋予已选定品牌/SKU的含义。阴影统一方向和强弱；D1/D2 用二维投影，不报告为真实三维渲染。
6. 编号和图例从同一清单生成。先确定房间身份，再编号，后挪动标记；搬动标记不能改变其功能归属。长名称换行后再排后续行，过多条目用新增页面解决。

推荐层从底至顶：页面底色 → 地坪与材质 → 投影/墙体强化 → PDF线稿 → 家具与绿植 → 空间编号 → 版式与功能表。实际项目可按遮挡关系调整；墙体强化若被源图灰面遮盖需检查层序。脚本保留每类独立层和对象 label，PDF 层锁定。

## 辅助脚本

先读 [作业格式](job-format.md)。已有 macOS / InDesign 2025 的原生基线测试。Windows 需使用本机 InDesign 脚本面板，未做 Windows 端到端实测。macOS 原生脚本执行示例（路径必须替换成实际输出，不把用户原文拼成 shell 代码）：

```bash
osascript -e 'tell application "Adobe InDesign 2025" to do script (POSIX file "/absolute/path/build/run.jsx") language javascript'
```

Windows 使用 InDesign 的“窗口 → 实用工具 → 脚本”面板运行本机编译的 run.jsx；自动操作能力由宿主提供。macOS 自动化/沙箱需要授权时，按当前环境的执行权限处理。脚本只创建自己的文档和输出，不保存已打开的用户文档；导出后关闭自己的文档、重新打开交付文件检查再关闭。其运行状态和 PDF/JPEG 导出设置会恢复。ExtendScript 是旧版 JavaScript，不能假定全局 `JSON` 或 `Array.indexOf` 存在；内置脚本已避免这些依赖。`render_indesign.jsx` 以 UTF-8 BOM 保存，防止 `$.evalFile` 将固定中文误按本地编码读取；编译入口中的作业文字使用 Unicode 转义。

图例固定宽度，用 `AutoSizingTypeEnum.HEIGHT_ONLY` 自动增高，逐行重排；不对长名称使用 `FitOptions.FRAME_TO_CONTENT`，因为它可能把画框横向撑到页面外，即使 `overflows=false` 也会错误。

初次使用新机器/新版 ID 时，在选定款式的文档内检查字体、色彩、保存和重开；出现环境故障需要隔离排查时才用维护夹具，不把重建整套样式库作为每个任务的前置工作。不要把旧机器的一次验证当作永久跨版本保证。

## 固定选样图库维护

`assets/style-picker/` 的 PNG 是预存简图，普通 PDF 任务只读使用。只有用户要求更新参考/图库或修复明确缺失的缓存时，才运行 `scripts/build_style_picker.py`；它使用已有干净示意平面，不接收新项目 PDF。需要重做干净示意平面时，使用 `assets/demo-job.json` 的虚构维护夹具，保留 `library_maintenance:true`，不得混入真实项目 source。原生样式库和 A3 模板继续作为维护/版式资源，不再充当新项目必做 demo。

## A3 基线

内置脚本：420 × 297 mm，非对页；18 mm 左右边距；图面约为 x=18–292、y=58–263 mm；右图例 x=310–402 mm；页眉 y=14–43 mm；页脚线 y=276 mm。所有坐标为版式起点，可按图形长宽和品牌模板调整。长条平面优先调整主图比例/分图范围；不压扁建筑。

空白模板 [A3彩平版式模板.indt](../assets/templates/A3彩平版式模板.indt) 只提供版式，功能表必须按本项目生成。样式库含虚构平面、7个空间和参数化材质图案，不能充当精细材质成品。

## 验收记录

- **几何：** 逐页与源图叠合核对外轮廓、柱墙、门洞、关键家具、场地关系；已知尺寸与缩放保持一致。图纸含多个不同比例视图时先分离，不套一个变换。保持朝向，参考图斜置不构成旋转新底图的授权。
- **功能：** 图内 `room-number` 和右侧 `legend-name` 来自同清单，编号集合一致；检查锚点在正确空间、长引线端点准确、未知房名已处理，原 PDF 旧编号不与新编号混淆。
- **视觉：** 在实际 A3 输出尺度查看整页和细部；无溢出、遮字、跨区纹理、错缝、过黑阴影、低分辨率放大、被材质覆盖的细线。不能只看缩略图。
- **原生：** 缺失/过期/不可访问链接为零；字体状态正常或明确替代；检查 `TextFrame.overflows`；保存 INDD、导出 IDML、PDF 与 JPEG。复制 PDF/材质到交付 `Links/` 并更新链接，重新打开交付副本验证。允许打包的字体才随包带走。
- **报告：** `audit.json` 记录 ID 版本、页面尺寸、源文件链接、房号/图例、字体和自动检查；脚本将 `visual_review` 留为 `required`，人工/模型实际看过最终渲染后才更新为通过。有失败项保留并修正，不删错误记录冒充通过。

审阅 PDF 与印刷交付不同：需要印刷时再按印厂要求校准颜色、ICC、出血和 PDF/X 预设，不默认套用会改变颜色的预设。

## Adobe 官方接口依据

按本机现有版本验证后使用；下列为参考而非制作时逐项必读：

- [PDFPlacePreference](https://developer.adobe.com/indesign/uxp/omv/p/PDFPlacePreference/) / [PDFCrop](https://developer.adobe.com/indesign/uxp/omv/p/PDFCrop/)：页码、裁剪框和透明背景。
- [Path](https://developer.adobe.com/indesign/uxp/omv/p/Path/)：`entirePath` 的锚点与控制点。
- [BlendingSetting](https://developer.adobe.com/indesign/uxp/dom/api/b/blending-setting/)：对象透明度/混合；填充透明度与整个对象透明度有区别。
- [Document](https://developer.adobe.com/indesign/uxp/dom/api/d/document/) / [TextFrame](https://developer.adobe.com/indesign/uxp/omv/t/TextFrame/) / [LinkStatus](https://developer.adobe.com/indesign/uxp/dom/api/l/link-status/)：保存、导出、溢出、链接检查。
- [Adobe 打包说明](https://helpx.adobe.com/uk/indesign/desktop/print/preflight/package-files-for-output.html)：链接和字体可携带性。
