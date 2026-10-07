# 目录整理与 Python SVG 审查交付记录

日期：2026-10-07。用户授权：“开始执行两份计划”；随后补充非危害操作可连续执行，无需额外确认。保留先写计划、原始数据只读和宿主权限边界。本次未提交、推送或调用模型／图像生成 API。

## 当前入口

- 通用工具：[analysis/scripts](../../scripts/)，旧 `analysis/code/` 已迁空。
- 实验记录：[record_analysis.md](../../experiment_log/record_analysis.md)，照片和截图原样保存在同任务 `figures/`，正文只改变因迁移所需的图片链接。
- 官方解码源码保留用户指定的 `decode_data/DecodeAndSortAll/`；Git 白名单和内容检查仅允许其 14 个既有源码／配置文件，ROOT、bin、可执行文件和额外文件仍被排除。
- 当前分析任务：[run_log.py](../../run_log/run_log.py)、[CSV](../../run_log/runs.csv)、该任务 `figures/` 和 `reports/` 集中存放。
- 既往维护报告移到本目录，文件内容与历史命令保留。旧 JSON 是当时验证证据，不伪装成本次检查。

用户原有 `.codex/config.toml` 修改、解码源码和来源图片的指纹与迁移前一致。迁移基线见 [layout_baseline.json](layout_baseline.json)，本次检查见 [layout_svg_qa_verification.json](layout_svg_qa_verification.json)。

## 绘图审查技能

项目新增 `python-svg-qa`，维护源和 OMX 入口的技能文件及辅助程序保持一致。`AGENTS.md` 自动规则已加入所有绘图、改图和导出调用该技能；科研图仍按需使用 Nature 技能。已验证路由 hook 的本地输入／输出，新会话的技能发现和 hook 加载由宿主负责，本次不修改信任数据库。

采用依据为已安装 Nature Skills 的最终渲染及逐图审查原则，其固定上游版本仍见安装清单。Nature 的 PDF 检查不用于证明 SVG 已通过，也不为沿用其默认要求保存 PDF／PNG。辅助程序为本项目编写，使用已安装 Playwright／Chromium，无新依赖。

```bash
python3 analysis/scripts/check_layout.py verify
python3 analysis/scripts/project_runtime.py python .agents/skills/python-svg-qa/scripts/audit_svg.py --self-test
python3 analysis/scripts/project_runtime.py python .agents/skills/python-svg-qa/scripts/audit_svg.py analysis/run_log/figures/gantt_2025-06-07.svg --preview-base64
```

自检实际启动浏览器，正常图返回通过、文字重叠返回待审阅、边界裁切返回需修复、不可审查文字返回未审查；实际记录见 [svg_qa_self_test.json](svg_qa_self_test.json)。新增 JSON 输出仅允许项目内独立的新文件，拒绝覆盖；外部 SVG 资源和文档脚本被禁止。

原受限沙箱无法启动 Chromium，曾正确返回 `not_auditable`；宿主批准本地浏览器权限后实际验证通过。没有通过更改目录权限、信任记录或浏览器安全参数绕过限制。

最终九张实验 SVG 已在内存中渲染并逐图查看，只保存 SVG 和 JSON／Markdown 证据；每张图的指纹、自动结果及实际视觉结论保存在 [figure_qa.json](../../run_log/reports/figure_qa.json)。自动几何检查覆盖文字重叠候选和越界，不单独证明数据正确。

## 验证与修正

迁移前后检查覆盖 Git 入口、hook 事件和项目范围、数据排除、源码允许范围、脚本语法、图片／历史证据／实验内容／用户配置保留、技能镜像及清单指纹。独立审查发现并修复了 verifier 中拼接的旧路径、README 暂存示例漏列解码源码，以及审查工具的报告输出边界。

未运行完整环境恢复、全量安装验证、解码或符合分析。技能目录的新增文件和更新通过宿主权限执行，两个入口同步；临时技能目录在核对安装副本一致后清理。
