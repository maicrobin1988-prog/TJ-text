# 室内彩平制作：通用 Agent 入口

本目录是独立技能 `interior-colored-plan-indesign`。先读取本目录 `SKILL.md`，不要套用仓库根目录用于演示文稿的 TJ-text 工作流或依赖。

收到未选风格的 PDF 时，只展示预存 PNG 与八个样式 ID，等待实际选择；不完整解析 PDF、不启动 InDesign、不生成项目多款 demo。用宿主图片预览/附件与单选工具；无单选工具则让用户回复 ID。

```bash
python3 scripts/show_style_options.py
```

选定后才安装制作依赖、核图并直接制作这一款。运行条件、Windows/macOS 路线和更新方法见 `README.md`；作业格式见 `references/job-format.md`。脚本中的相对资源均以本技能目录为基准；不要依赖作者机器路径、Codex 专有工具或仓库根目录的模板。
