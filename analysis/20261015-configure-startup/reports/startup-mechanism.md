# configure 的 Codex 启动与自动化机制

核查日期：2026-10-15。来源：<https://gitee.com/zhangxin8069/configure>，读取提交 `43c216e8a2e755975633c163b38ad79bac7042d7`。

主要结论：仓库使用 `co/cos` 启动器，在启动 Codex 时传入固定提示词、技能路径和运行契约。技能选择依赖模型执行提示词；仓库的 hooks 是待接入的显式脚本适配器，plugins 是推荐索引和显式安装器。源码没有证明这些 hooks 和插件会随每次启动自动注册或运行。

## 启动入口与提示词

1. `env.sh` 由个人 `.bashrc/.zshrc` source，将仓库 `bin/` 放进 PATH。`bin/co`、`bin/cos` 是指向 `agent.sh` 的符号链接；启动器按调用名分派到 `run_codex()`。因此，这条附加提示词链对应 `co/cos` 入口；直接运行原始 `codex` 不会因此自动经过该函数。
2. `agent.sh:_load_prompt()` 读取 `bin/agent-prompt.txt` 正文，替换 `${CONFIGURE_ROOT}`、`${HOME}` 等占位符。它也加入项目说明文件的路径清单；没有把这些项目文件的正文全部拼入 prompt。
3. 启动器追加全局 `{skills,tools,hooks,plugins}` 目录、全局及工作区 `SKILL.md` 路径清单，以及角色、模型、停止条件等运行契约。路径已列出只证明模型知道位置，不证明已经读取或执行。
4. 普通模式最终调用真实二进制：

```bash
"${_CODEX_BIN}" "${CODEX_INITIAL_ARGS[@]}" -- "${PROMPT}"
```

这段文本通过 CLI 的初始输入参数传入。源码没有将它写成系统提示词，也没有使用原生 `SessionStart.additionalContext` 注入它。

证据：[env.sh](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/env.sh#L42)、[入口分派](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L43)、[读取模板](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L159)、[组合 prompt](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L2313)、[真实启动命令](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L2509)。

## 自动选择技能

`_append_skill_list()` 用 `find ... -name SKILL.md` 搜索并去重，只列路径。来源包括配置根的 `skills/`、当前工作目录的 `skills/` 和 `.codex/skills/`；若处于 Git 子目录，再加入仓库根的这两类目录。

模板第 21 行要求模型：收到任务后按需选择技能、完整读取选中的 `SKILL.md`，识别 `{~skill-name}` 约定；未指定技能时默认使用 `auto+all`，简单单步任务可直接完成。因而“自动触发”在这里主要是模型遵循提示规则，不是 Shell 将所有技能逐个执行，也不是保证每项任务都实际调用了技能。

`auto` 包装无人值守执行，`all` 编排其他技能；二者正文是后续工作流的来源。读取它们作为调查证据不构成本项目调用或接受其授权规则。

启动器还把四个全局目录以 `--add-dir` 传给 Codex。这是目录范围参数；源码没有用它执行技能安装、hook 注册或插件加载。

证据：[路径枚举](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L694)、[工作区目录](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L2084)、[技能规则](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent-prompt.txt#L21)、[目录参数](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L2394)。

## hooks 与 plugins 的实际边界

| 部分 | 已核实的实现 | 尚需的接入 |
| --- | --- | --- |
| `hooks/codex-hook.sh` | 按调用方传入的事件名分派到预检、路径检查、验证或通知脚本 | 需要外部 runner 或原生 hooks 配置实际调用；主启动器没有这条调用链 |
| `.codex/hooks.json` | runtime 发现工作区已有文件时，把路径列入上下文 | 这段发现逻辑不生成或注册 hooks；宿主可独立加载已有受信配置 |
| `hooks/pre-commit`、`pre-push` | 独立 Git 质量检查入口 | 文件存在不代表 Git 已启用；主实现未自动配置 `core.hooksPath` |
| `plugins/` | 推荐插件文档与 `install-recommended.sh` | 显式执行安装器后才调用 Codex marketplace/plugin add；启用和 hook 信任另核对 |

`codex-hook.sh` 的映射包括 `session-start → codex-preflight.sh`、`before-edit → codex-guard.sh`、`after-edit/stop → codex-verify.sh`。这些是适配器的命令行事件名，不能据此断言已经注册了 Codex 的 `SessionStart`、`PreToolUse` 或 `Stop` 原生事件。

`lib/_codex/install.sh` 安装真实 CLI 并配置 PATH；`config.sh --apply` 可改模型、审批、沙箱、主题和供应商。核查范围内未发现它们安装全局 AGENTS、建立技能链接或注册上述 hooks/plugins。

证据：[hooks 的显式协议](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/hooks/codex-hook.sh#L4)、[事件分派](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/hooks/codex-hook.sh#L60)、[hooks 启用说明](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/hooks/README.md#L46)、[plugins 显式安装](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/plugins/README.md#L3)、[安装器真实调用](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/plugins/install-recommended.sh#L547)、[仅列已有 runtime 配置](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent-runtime.sh#L531)。

## “持续执行”与“重复注入”

无人值守模式首轮调用 `codex exec ... --json -- "$PROMPT"`，提取 thread ID，后续调用同一线程的 `codex exec resume ... -- "继续"`。后续回合没有每次重新传入完整模板，主要依靠同一会话的上下文。脚本另外检查停止条件及连续失败；不能将此机制说成每一轮都会重新执行全部 skills/hooks/plugins。

证据：[首轮输入](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L2535)、[继续循环](https://gitee.com/zhangxin8069/configure/blob/43c216e8a2e755975633c163b38ad79bac7042d7/bin/agent.sh#L2579)。

## Codex 原生机制的对照

本轮实际读取的 OpenAI Docs 页面分别确认：

- [AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)：Codex 在每次 run 开始构建指令链，读取全局及项目层级指令。启动器只列路径，不会取消 Codex 自己的原生加载。
- [Skills](https://developers.openai.com/codex/skills/)：先提供技能名称和描述，任务匹配时再读取全文；隐式调用受配置控制。configure 自己列出的任意 `skills/` 目录，不等同于原生技能目录已经安装。
- [Hooks](https://developers.openai.com/codex/hooks/)：原生 `SessionStart`、`UserPromptSubmit` 可返回 `hookSpecificOutput.additionalContext`，作为额外 developer context。项目配置与非托管 hook 的信任要求仍适用；启用插件不自动信任其 hooks。
- [Plugins](https://developers.openai.com/codex/plugins/)：安装并启用的插件提供技能、MCP 等组件；安装后通常需新会话加载，MCP 还可能需要认证。

仓库 hooks README 的“当时无法核实统一 API”表述不能代替当前官方说明；当前官方支持原生 hooks，也不代表 configure 已把自己的适配脚本接入。

## 核查方式与限制

实际下载命令：

```bash
git -c core.hooksPath=/dev/null clone --depth 1 https://gitee.com/zhangxin8069/configure.git /tmp/chx-configure-read-20261015
```

使用 `rg`、`nl -ba`、`git ls-files -s` 和 `readlink` 做只读源码追踪，并由独立角色核对 hooks/plugins 调用者和官方文档。未执行仓库启动器、hook、安装器或第三方插件，未更改本项目配置。本次仅留存调查说明及最小验证证据，不制作 plan。

结论对上述提交的主实现有高置信度；不推定作者机器的个人配置、已安装插件、额外 wrapper 或 `refer/` 参考项目实际生效。官方页面反映本轮读取内容，不保证任意旧版 Codex 具有相同行为。验证记录见同目录 `verification.json`。
