# 执行计划：analysis 按任务整理与 Python SVG 绘图审查技能

- 创建日期：2026-10-07
- 状态：已完成；目录、入口、源码跟踪与 SVG 技能验证完成
- 用户确认记录：2026-10-07 用户明确指令“开始执行两份计划”，授权本计划及 run.log 计划；不包含提交或推送
- 范围：整理现有项目路径、维护运行入口和源码跟踪；创建自动触发的绘图审查技能。run.log 统计按独立的 `2026-10-07-ge-run-log-timeline.md` 执行。

## 目标结构

```text
analysis/
  plans/                       集中计划，压缩后从这里恢复
  scripts/                     通用项目工具，不混入具体分析任务
  run_log/                     当前任务：程序和 CSV 直接放这里
    run_log.py
    test_run_log.py
    runs.csv
    figures/                   仅 SVG
    reports/                   说明和检查证据
  experiment_log/              既有实验记录与来源图片
    record_analysis.md
    figures/                   保留原始照片／截图，不改为伪 SVG
  project_maintenance/
    reports/                   项目配置、既往清理和本次迁移报告
  vendor/                      保留固定上游源码
  third_party/                 保留安装清单、来源和恢复说明
decode_data/
  DecodeAndSortAll/             官方解码源码，用户已完成移动
  *.root                       本地解码结果，禁止提交
```

任务代码默认平铺；只有文件确实需要组织时才加子目录。不建立空的任务骨架，不保留 `code/` 别名或重复工具副本。`vendor/`、`third_party/` 和 `plans/` 作为共用基础设施保留。

## 当前事实与引用

- 用户已移动解码源码：`decode_data/DecodeAndSortAll/` 存在，`analysis/code/DecodeAndSortAll/` 不存在；原位置的 14 个源码／配置文件在 Git 状态中显示删除。不得撤销用户移动。
- `analysis/code/` 剩余 7 个通用工具：`project_git.sh`、`project_runtime.py`、`check_git_content.py`、`task_delivery.py`、`bootstrap_project_tools.py`、`verify_project_tools.py`、`skill-routing-hook.mjs`。
- `.githooks/pre-commit:4`、`pre-push:4`、`post-commit:4` 和 `.codex/hooks.json` 引用旧工具路径。`README.md`、`AGENTS.md`、安装说明及 4 个项目技能也有旧路径。
- `.gitignore:2` 的根白名单未允许 `decode_data/`；`analysis/code/check_git_content.py:24` 起的允许规则也未允许新源码路径。必须同时修复这两处，不能放开整个数据目录。
- `analysis/record_analysis.md` 含用户修改；迁移只调整图片链接和文件位置，不核实、改写或覆盖实验内容。其图片位于 `analysis/analysis_figure/record_analysis/`。
- 现有 `.agents/skills/nature-figure/references/qa-contract.md` 已规定源码检查、逐图视觉检查和缺工具时不能声称通过；`scripts/audit_figure_collisions.py:245` 读取 PDF，`validate_figure.py:427` 起要求同时导出 SVG/PDF，不能直接作为本项目 SVG 专用审查的通过依据。
- 项目安装清单记录 Nature Skills 上游为 `https://github.com/Yuan1z0825/nature-skills`，固定提交为 `50851efc109c981be6cdc1ed5171a2eaa739d20a`。本轮采用已安装规范作依据，不另引入 GitHub 图形库。
- 已看到本地 Playwright 包与 Chromium 目录；这只是文件存在证据，浏览器能否实际渲染须在执行阶段验证。

## 预计迁移与修改的文件

| 当前路径 | 目标／修改 | 处理要求 |
| --- | --- | --- |
| `analysis/code/` 下 7 个通用工具 | `analysis/scripts/` 下同名文件 | 逐个迁移；根目录解析仍需验证；修复程序中的旧路径 |
| `analysis/project_setup.md` | `analysis/project_maintenance/reports/project_setup.md` | 迁移并更新当前调用说明 |
| `analysis/records/` 下两个 Markdown 和两个 JSON | `analysis/project_maintenance/reports/` 下同名文件 | 保留既往证据内容和当时命令，不把旧结果改写为本次验证 |
| `analysis/record_analysis.md` | `analysis/experiment_log/record_analysis.md` | 保留用户现有正文，只修正随迁移变化的图片相对路径 |
| `analysis/analysis_figure/record_analysis/` 内来源图片 | `analysis/experiment_log/figures/` 内同名文件 | 原样移动，不转换、不删除 |
| `.githooks/` 下三个 hook、`.codex/hooks.json` | 更新工具入口 | 同步 `analysis/scripts/`，不修改 hook 信任数据库 |
| `AGENTS.md`、`README.md`、`analysis/third_party/INSTALL.md` | 更新当前目录和调用说明 | 与实际迁移后的文件位置一致 |
| `.gitignore`、`analysis/scripts/check_git_content.py` | 精确允许官方解码源码 | 仅允许 `decode_data/DecodeAndSortAll/` 的既有源码／配置；仍拒绝 `.root`、`.bin`、编译产物和可执行文件 `decodeandsort` |
| `.agents/skills/{chx-data-analysis,crawl4ai,go-on,task-tag}/SKILL.md` 及 `.codex/skills/` 对应文件 | 同步实际程序／记录入口 | 两个技能目录保持一致；不修改固定的上游 vendor 副本 |
| `analysis/third_party/sources.lock.json` | 更新本地覆盖指纹，登记新技能 | 保留上游来源与提交，不伪造来源 |
| `analysis/plans/` 中模板和当前计划 | 按实际状态更新 | 保留未执行事项与授权记录 |

源码白名单须同时限制目录和文件种类，不能让源码旁的数据因路径获准；解码调试文件 `crate.dat`、`test.cc`、底本 `run.sh` 均保留。

## 新技能文件与范围

| 预计文件 | 用途 |
| --- | --- |
| `.agents/skills/python-svg-qa/SKILL.md` | 自动处理本项目绘图、改图与导出：Python、仅 SVG、可追溯数据、导出后实际视觉审查 |
| `.agents/skills/python-svg-qa/scripts/audit_svg.py` | 一个小型 Python 辅助程序：检查最终 SVG 的文字几何、输出 JSON，并提供不落地的内存渲染供查看；含可运行 `--self-test` |
| `.codex/skills/python-svg-qa/` 对应文件 | OMX 项目技能入口，内容与维护源一致 |
| `analysis/scripts/check_layout.py` | 可查看的迁移与路径边界验证程序，记录迁移前后检查证据 |
| `analysis/project_maintenance/reports/layout_svg_qa.md` | 路径迁移、采用依据、检查范围及使用方法 |
| `analysis/project_maintenance/reports/layout_svg_qa_verification.json` | 本次实际验证证据，与历史安装验证区分 |
| `analysis/project_maintenance/reports/layout_baseline.json` | 实际新增：迁移前文件指纹、用户配置和实验正文基线 |
| `analysis/project_maintenance/reports/svg_qa_self_test.json` | 实际新增：真实 Chromium 四类 SVG 自检证据 |

新增技能只补本项目的约束和 SVG 审查，不复制 Nature 全部文档，不写新的绘图库或通用场景框架。描述覆盖普通图表、科研图和示意图；默认允许自动选择，无需用户输入技能名。安装后在 `AGENTS.md` 的自动技能表中加入所有绘图 → `python-svg-qa`，科研图再按需使用 `nature-figure`。现有路由 hook 读取该表，原则上不需要新建关键词引擎。

## SVG 审查办法

1. **生成前**：读取计划及真实来源数据，明确坐标、单位、映射和筛选。Python 保存绘图程序；Matplotlib SVG 保留文字，不为减少碰撞提示把文字转成不可审查路径。
2. **导出后自动检查**：针对最终 SVG，用现有浏览器经 Python 读取实际渲染的文字边界，检查非预期文字重叠、越界／裁切和输出格式。仅对导出前 Matplotlib 坐标做检查不能替代最终 SVG 检查；浏览器未运行或文字不可审查时明确返回未审查。
3. **实际查看**：通过 Python 调用现有浏览器将最终 SVG 在内存中渲染，并由助手查看整体和密集区域。只保留 SVG、程序、源数据和 JSON／Markdown 证据，不落地 PNG、PDF 等副本。检查字体缺字、标签、图例、坐标轴、图形遮挡、数据关系；必要时对照数值表。
4. **修正与停止条件**：发现错误就修改 Python 程序，重新导出并重新检查；自动检查与视觉结论分开记录，未经实际查看不能填视觉通过。工具缺失时保留阻碍，不伪造完成，也不临时改用 AI 图片。

意图明确的图内文字、路径文字、科学上必要的重叠分别记录，不能把所有图元交叉都当错误，也不能关掉全局检查以掩盖碰撞。自动检查只证明所覆盖的几何条件，不能证明数据正确。若需要从上游复制具体代码，执行前核对对应许可证；优先使用已安装工具与少量本地逻辑。

## 统计方法与预计结果

本任务是目录维护与技能建设，不涉及数据统计检验；不计算实验结果。预计得到按任务集中存放的文件、可工作的通用工具入口、继续跟踪的官方解码源码，以及每次绘图自动使用的 SVG 审查技能。

不生成真实实验图；验证图只用于证明可识别重叠／裁切和能实际查看 SVG，与正式 run.log 结果隔离。

## 执行步骤与验证

1. 用户确认后，记录文件清单、Git 差异和待迁移文件指纹，保留用户未提交改动。先建立最小行为检查：旧入口的只读 Git 状态、路由 hook 对有效事件／项目外事件的响应、路径边界检查和源码跟踪规则；不运行安装恢复或提交／推送。
2. 保存迁移和验证所需的显式程序为 `analysis/scripts/check_layout.py`，随后按清单迁移通用工具、维护记录、实验记录及图片。逐项修复入口和链接，不做无关代码重构；目标已存在且内容不同时停止覆盖并报告。
3. 修复 Git 两层白名单，并验证新解码源能被识别、ROOT／bin／编译产物仍被拒绝。迁移前后的源码及来源图片指纹应一致；实验正文除链接外与用户当前版本一致。
4. 编写技能与一个辅助程序，同步两个入口，登记来源和文件指纹。运行 skill-creator 的 frontmatter 验证及辅助程序自检；用正常图、文字重叠、边界裁切实例验证实际结果，再实际查看渲染结果。测试图仅保存隔离的 SVG，不能混入实验结果。
5. 更新自动技能表，验证路由 hook 注入新规则；用一次简单绘图任务验证技能可被选用、只输出 SVG 并留下视觉检查。新会话技能发现仍由宿主加载，不能把文件存在说成已验证新会话自动加载。
6. 验证 Python 语法、shell／Node 语法、关键入口、链接和 Git 跟踪范围；记录结果。已迁空的旧目录只在确认属于本次迁移且无其他内容时清理。更新计划，交付文件与验证证据后停止。

拟用命令（未运行）：

```bash
python3 analysis/scripts/check_layout.py verify
bash analysis/scripts/project_git.sh status --short
python3 analysis/scripts/project_runtime.py python .agents/skills/python-svg-qa/scripts/audit_svg.py --self-test
```

`check_layout.py` 在迁移前也须能以显式当前入口进行有限验证，避免只测迁移后结果；新程序的具体接口在执行时先保存再使用。现有 `verify_project_tools.py` 会生成安装报告并运行大量无关检查，本次只取相关检查，不重跑全部安装链。

## 完成标准与风险

- `analysis/code/` 已迁空、所有当前入口指向实际存在的 `analysis/scripts/`；历史证据中的旧命令保留并注明当时路径，不按字符串全局替换。
- 任务文件集中归档，实验记录及原始图片无内容损失；不把来源图片因新 SVG 规则转换或删除。
- 用户已移动的官方解码源码保留原位，可被 Git 内容规则识别；任何数据／编译产物仍不在允许范围内，不触及原始数据目录。
- 新技能两个目录内容一致；正常图能完成检查，故意重叠／裁切图能报问题。最终审查针对 SVG，不伪称 PDF 工具已验证 SVG。
- 不新增依赖、不改全局环境、不提交或推送。若现有浏览器不能使用，则暂停依赖它的视觉验证，保留具体阻碍，其他可安全验证的工作继续。
- 清理计划由主代理编写，用户审阅后执行；迁移前后行为检查作为独立验证步骤，不把计划描述当验证结果。

## 进度与恢复记录

- 已完成：迁移前检查和基线；全部指定文件迁移与引用修复；解码源码白名单；新 SVG 技能两入口及指纹登记；真实浏览器自检、自动路由输出验证和 run.log 九张实际图的视觉应用；清理与安装文件一致的临时技能目录。
- 保留证据：用户配置、14 个官方解码源码、8 个来源图片和历史报告指纹一致，实验正文除图片链接外保持用户现有内容；旧 code/、records/、analysis_figure/ 已迁空。
- 实际命令：`python3 analysis/scripts/check_layout.py capture`、`migrate`、`install-skill`、`verify`、`cleanup-stage`；首次 `capture` 在迁移前使用旧工具入口。受保护技能／hooks 写入和 Chromium 启动通过宿主权限执行，无权限绕过。
- 审查修正：更新 verifier 拼接旧路径；补全 README 的源码暂存示例；为 SVG JSON 输出加入项目路径、输入分离及拒绝覆盖保护。新技能语法／格式及真实自检通过。
- 未执行：无本计划必需工作剩余；未恢复全环境、提交、推送或伪造新会话技能加载。新会话的发现和 hook 信任仍由宿主负责。
- 下一步：交付后停止；报告见 `analysis/project_maintenance/reports/layout_svg_qa.md` 与本次 JSON 证据。
