# 项目内技能与工具安装

所有持久安装文件和依赖属于 `chx_20260622`。没有运行 `npm install -g`、修改全局 Codex 配置、写入全局技能目录或安装系统软件。原始数据目录及他人的 `software/` 保持原约定。

## 安装内容

| 来源 | 内容 |
| --- | --- |
| [muIon-beam](https://gitee.com/chx6/muIon-beam) | 读取项目设计；保存 evolution、farmer 和标签/提交脚本作为适配来源 |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | 全部 6 个技能、完整源码、SessionStart 与 UserPromptSubmit hooks |
| [shuorenhua](https://github.com/MrGeDiao/shuorenhua) | 中文 full 技能，含入口和两份参考文档；保留完整上游资源 |
| [humanizer](https://github.com/blader/humanizer) | 英文完整技能与全部上游支持文件 |
| [oh-my-codex](https://github.com/Yeachan-Heo/oh-my-codex) | 固定源码 0.21.7；全部 29 个主技能目录（24 个 setup 当前技能、4 个迁移卡片及 git-master 技能），18 个原生角色、32 份提示词、7 种 native hook 事件、6 个 MCP 服务及四个原生组件 |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | 固定源码 0.9.4；`[all]` 全部 extras、CPU PyTorch、Playwright/Patchright Chromium |
| [Nature Skills](https://github.com/Yuan1z0825/nature-skills) | 全部 20 个安装单元，含 `nature-shared`；references、static、scripts、assets、manifest 完整保留，补齐声明的 Python 依赖 |

项目 Python 环境共固定 155 个包，另安装 Mermaid/Puppeteer 与官方 LibreOffice 25.8.7 解包版，用于 Nature 的本地图表和 Office 渲染。

固定提交、uv 下载版本/校验值和原生组件摘要见 [sources.lock.json](sources.lock.json)。所有上游许可证在 `licenses/`。57 个上游技能保留来源记录；用户要求的 Ponytail 报告适用范围和隐式调用配置记录在 `project_overrides`，保留原始摘要与安装后的摘要。另有既有 `chx-data-analysis` 和 5 个项目适配入口：`go-on`、`evolution`、`task-tag`、`crawl4ai`、`farmer`。

This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai).

## 存放与发现

- `.agents/skills/`：Codex 当前的项目技能发现目录及项目维护源。
- `.codex/skills/`、`.codex/agents/`、`.codex/prompts/`：OMX 原生项目安装目录。
- `.codex/config.toml`、`.codex/hooks.json`：原生项目配置与 hooks。保留宿主信任流程，不迁移临时 setup 的 trust hash；Ponytail 的状态路径显式限定在项目内。
- `.omx/setup-scope.json`、`.omx/hud-config.json`：版本化的项目安装范围和界面偏好；其他 `.omx/` 会话与运行状态留在本地。
- `analysis/vendor/`：Ponytail、OMX、Crawl4AI 的固定源码，保留其目录结构和许可证。编译输出及依赖另行恢复。
- `.runtime/`：项目独立 Python、包、浏览器、原生二进制、缓存及可选模型权重，不提交 Git。

根 `skills/` 曾用于安装时的读取兼容，现已核对没有独有内容并清理。所有维护和调用路径使用 `.agents/skills/`，修改技能时同步保留的 `.codex/skills/`；不再生成根目录副本。技能/角色通常在新会话加载，hooks 由宿主按信任设置加载。

技能与 hooks 按任务自动触发，无需提示技能名。报告和代码都自动使用 Ponytail，中文报告结合说人话、英文结合 Humanizer；科研报告再选择适用的 Nature 技能。项目自动路由规则只定义在根 `AGENTS.md`，轻量的 SessionStart/UserPromptSubmit hook 读取同一规则并注入，避免另写一套匹配表。

Ponytail 的两个 hook 经 `analysis/scripts/ponytail_project_hook.cjs` 复用上游模式管理，正文读取 `.codex/skills/ponytail/SKILL.md`，不再注入上游的三行回复限制；上游快照保留。`install_project_sync.py` 同步交付技能、项目 hook 路径和已安装摘要，重复运行保持一致。回复须独立说明主要结果、依据和限制；程序按科学复现需要留档，报告按长期留存价值生成。无需报告的小任务仍保留必要机器验证证据，不为此额外写报告。新任务产物采用 `analysis/YYYYMMDD-topic/`，旧任务原地续作。

项目新增的 `python-svg-qa` 为所有绘图执行 SVG 最终渲染审查。用户另已持续授权：文件变更完成并验证后自动 commit/push；扩展的 `task-tag` 技能调用 `analysis/scripts/project_sync.py`。并行员工通过 `analysis/scripts/session_coordinator.py` 建立独立普通克隆，提交本地 outbox，由控制端串行整合与重新验收；使用已安装 Git、Python 标准库和 bubblewrap，没有新增外部编排依赖。SessionStart 分配工作区和上下文，Stop 只跟进当前员工，均不隐藏联网或改变宿主 cwd/沙箱。控制端验收需真实可用的 namespace 权限；当前 App 外层限制需真实宿主审批，不使用无沙箱回退。安装模板为 `analysis/scripts/install_project_sync.py`，技能双入口与指纹同步，详细使用和恢复见 `analysis/session_coordination/reports/usage.md`。受限网络／认证失败需记录真实阻碍；宿主仍负责新增 hook 的加载和信任。

Nature 资源按各技能的 `manifest.yaml` 解析；某些 `core/` 路径是 `static/core/` 的简写。OMX 文档所指的根 `templates/AGENTS.md` 位于 `analysis/vendor/oh-my-codex/templates/AGENTS.md`。`nature-proposal-writer` 的调用名为 `researchwrite`，按上游保留。

## 运行

```bash
# OMX 使用本项目配置和原生组件
python3 analysis/scripts/project_runtime.py omx doctor
python3 analysis/scripts/project_runtime.py omx ultragoal status

# 使用项目 Python；与系统 Python 3.8 / PyROOT 分开
python3 analysis/scripts/project_runtime.py python analysis/<task>/<your-script>.py

# Image2PPT 的本地 runtime 检查
python3 analysis/scripts/project_runtime.py python .agents/skills/nature-image2ppt/cli/image2ppt/cli.py doctor --json

# Mermaid 使用同一项目浏览器
python3 analysis/scripts/project_runtime.py mermaid -i diagram.mmd -o diagram.svg
```

自然语言任务自动按项目 AGENTS 路由到相应技能；也可显式指定技能覆盖默认选择。OMX 的 Ralph、Pipeline、Ultrawork 和旧 Goal 入口已退役，保留的卡片会指向当前实现。

数据盘不支持符号链接和可执行权限。依赖、Python 和浏览器保留项目内完整副本；运行时将必要的可执行文件复制到私有 `/tmp/chx-runtime-<uid>-<project-id>/` 缓存并恢复执行权限。这个临时缓存可重建，不是全局安装。Python 的可选 terminfo 资源因大小写冲突被省略；使用系统终端资源，不影响 Python 或浏览器运行。

## 恢复环境

克隆本仓库后，技能和配置立即存在，运行依赖可按固定版本恢复：

```bash
python3 analysis/scripts/bootstrap_project_tools.py
# 仅恢复一类依赖
python3 analysis/scripts/bootstrap_project_tools.py --node-only
python3 analysis/scripts/bootstrap_project_tools.py --python-only
```

此恢复脚本只写项目 `.runtime/`、OMX 本地 `node_modules`/编译目录和临时目录。它不重新生成或覆盖项目约定与原生配置。Node 使用原生 `package-lock.json` 和 `nature-node/` 锁文件，Python 使用 `python.requirements.lock`，uv/LibreOffice archive 验证固定 SHA256，OMX 原生下载通过官方 manifest 验证。当前固定环境为 Linux x86_64；迁移系统时需重新选择平台构建。

## 已知运行条件

当前系统为 Ubuntu 20.04，浏览器采用 `ubuntu22.04-x64` fallback 下载目标；实际启动和抓取结果以验证回执为准。不会运行 Crawl4AI 的 `--with-deps` 安装路径，因为它会改变系统环境。

OMX doctor 能验证安装形态，但本项目的独立 Codex CLI 还没有登录凭据。模型自动执行、Ultragoal 实际任务和 tmux Team 模型工作需要用户登录；当前宿主会话身份不能被当作 CLI 已认证的证据。运行 `omx auth` 时也应保持项目范围，凭据不提交 Git。

Nature 的 OpenRouter、Scopus、图像服务等按所用工作流需要相应账户/API key。项目 LibreOffice 渲染器已安装，Image2PPT doctor 已通过；TeX 和独立 OCR 系统程序未安装，已有离线 OCR fallback 可用。外部服务和任务特定系统工具的可用性应在具体任务前检查。包安装不等于下载全部模型权重或验证了所有研究流程。

安装时 npm audit 报告 OMX 锁文件有 7 个告警（含 3 个 high），Nature Mermaid/Puppeteer 有 8 个 high 告警，并提示上游声明的 Puppeteer 23 版本已停止支持。当前保留可复现的上游依赖选择，未执行会改变兼容性的强制升级。后续对外部署这些工具前应评估并修复相关依赖。

## 验证结果

[verification.json](verification.json) 记录 17 项实际通过的检查：完整技能资源、保留的 OMX 入口及自动选择策略、脚本语法、全部 Python 依赖导入、两种 Chromium 抓取、OMX 安装形态、六个 MCP 服务握手与工具列表、Ponytail hook 输出、隔离目标计划建立与恢复、Image2PPT doctor、Mermaid SVG 渲染，独立的标签证据保护测试，以及四个原生可执行组件的启动检查。未调用模型 API、启动真实 Team 模型任务或访问外部付费服务。

## 交付标签

实际检查结果保存在 `analysis/` 下的 JSON 证据中。暂存交付内容后运行 `task_delivery.py prepare`，下一次通过项目 Git 脚本的提交由 `post-commit` 自动创建本地 annotated tag。代码 tree 或证据不匹配时不产生标签；没有准备证据的普通提交也不产生标签。推送按照用户的同步要求执行。

## configure 工作机制的核结构适配

参考公开仓库 `zhangxin8069/configure` 的固定提交，采用共享专业提示词、首条输入注入、按需技能发现和证据核对；领域改为原子核结构、能级纲图、gamma 强度及 ADO/P、集体激发。全部 28 个上游技能按现有能力映射复用，不重复安装另一套工作流。许可和指纹见 `sources.lock.json` 的 `sources.configure` 及 `licenses/configure/LICENSE`。

`analysis/scripts/agent-prompt.txt` 是 co 与 SessionStart 共用正文。已有项目 hook 保留注册与宿主信任；首次 co 注入按正文哈希去重，清空和恢复事件可重新输出正文。UserPromptSubmit 保留路由和正文位置提醒；未新增插件或信任绕过。co 复用独立员工启动与验证交付，安装只 co 的 Bash 块，不重启用户关闭的旧 codex source。

调用、采用边界和可复跑检查见 [采用说明](../20261015-configure-adaptation/reports/adaptation.md)。本次只适配研究上下文和工具机制，不开发核谱分析程序，不自动生成 plan，不修改既有模型、供应商、登录或沙箱边界。

## muIon-beam 会话监督与恢复适配（farmer）

参考 `muIon-beam` 仓库提交 `c27082aa702cb93304333afe62e4b4ee641158a3` 中的 `farmer` 技能与 ADR-008。
在保留紧急停用开关（`control.json`）、有界重试熔断（`max_attempts: 3`）、看门狗超时（`queue-stuck`）与原子锁（`recovery.lock`）的同时，适配 Linux POSIX 运行环境与本项目路径结构：
- 项目配置默认读取 `.codex/farmer.json`（回退兼容 `.agents/skills/farmer/farmer.json` 与 `00_project/`）；
- 项目根限定为 `/home/ys/data_401/data/chx_20260622`，排查范围仅限本项目会话；
- 源码与配置维护于 `.agents/skills/farmer/` 并镜像同步 `.codex/skills/farmer/`；来源固定于 `analysis/third_party/muIon-beam/`，指纹记录在 `sources.lock.json`。
