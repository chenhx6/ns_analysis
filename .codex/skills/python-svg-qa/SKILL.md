---
name: python-svg-qa
description: 本项目每次绘图、改图或导出图表时自动使用；以 Python 生成 SVG，检查最终渲染的文字重叠、裁切、缺字和数据关系，并保存审查证据。适用于普通图表、科研图和示意图。
---

# Python SVG 绘图与审查

先保存任务计划，在已授权范围内连续执行非危害步骤：保存可查看的 Python 程序，读取真实来源数据，注明轴、单位、筛选及颜色含义。缺失数据不补造；示意图注明其性质。仅导出 SVG，不调用 AI 图像生成或编辑工具。保留程序及绘图数据表。

Matplotlib 使用 `plt.rcParams['svg.fonttype'] = 'none'` 保留可审查文字；选择实际存在且覆盖所需字符的字体。不要通过文字转路径消除检查提示。每次改图后重新导出并检查最终文件。

## 最终 SVG 检查

通过项目 Python 运行本技能的 `scripts/audit_svg.py`（可一次传入多个 SVG）：

```bash
python3 analysis/scripts/project_runtime.py python .agents/skills/python-svg-qa/scripts/audit_svg.py analysis/<任务>/figures/<图>.svg --json-out analysis/<任务>/reports/svg_audit.json
```

检查使用已安装 Playwright Chromium 的真实文字边界。退出码 0 仅表示覆盖的自动几何检查通过；1 表示须修正越界或审阅重叠／裁剪提示；2 表示不能审查（包括没有可审查文字、浏览器不可用等）。所有结果的 `visual_review` 保持 `pending`，不能自动写成视觉通过。无文字的合理示意图也需记录文字检查不适用并实际查看。

加入 `--preview-base64` 可在标准输出 JSON 的 `preview_png_base64` 中获取最终 SVG 的内存预览。由工具将此内容作为图片显示供检查，不保存 PNG/PDF 文件；`--json-out` 不包含预览。审查每幅整体和密集区域，核对文字／图例重叠、裁切、缺字、刻度、单位、颜色映射和数据关系。自动几何提示可能来自旋转标签的矩形包围盒或科学上必要的叠加，逐项核实并在任务报告中注明理由，不关闭全局检查。图内遮挡、字体缺字、字形描边及语义正确性仍需视觉和源数据核查。

报告保存文件 SHA-256、实际命令、自动结果、查看的图及区域、每条提示的处理和视觉结论。修正后重新生成证据；看不到实际渲染时记录未完成。交付停止条件为自动问题处理完毕且最终 SVG 已实际查看。

`--json-out` 仅允许写项目内独立的新 JSON 文件，拒绝覆盖已有报告或 SVG 输入。复查时使用新的报告名，不能以覆盖原始日志或图表保存证据。

## 依据及范围

沿用已安装 `nature-figure/references/qa-contract.md` 的最终渲染审查与逐图核对原则；科研图按需同时使用该技能。项目约定覆盖其 R、AI 生成及 PDF/位图导出要求。本检查不等价于 Nature 的 PDF 碰撞／面板对齐检查，也不证明数据正确；多面板对齐仍需核对最终图。

运行 `scripts/audit_svg.py --self-test` 验证正常、文字重叠、边界裁切和无可审查文字案例。仅使用临时 SVG，无实验数据。
