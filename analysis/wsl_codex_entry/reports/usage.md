# WSL/Bash 继续使用普通 codex

接入脚本为 `analysis/scripts/codex_shell.sh`，由个人 `.bashrc` 中带标记的一段 source 加载。它定义项目分派函数，系统 Codex 可执行文件、登录和信任记录保持原样。安装后新交互 Bash 终端在本项目中仍使用：

```bash
cd ~/data_401/data/chx_20260622
codex
```

每次新启动先安排一名独立员工，输出员工 ID 和 workspace，再调用真实 Codex CLI，显式使用该目录与 workspace-write。启动器父进程收集员工本地 outbox 并串行整合；并行任务仍按已实施的范围、验证和冲突恢复规则执行。

提示词、`--model`、允许的模型配置等原始参数保持 argv 形式转发，不使用 eval 或 shell 拼接。项目外的 `codex`、帮助/版本及明确登录等管理操作转交原始 CLI，不创建员工；守护服务/debug 等不能描述成员工隔离启动，在管理环境中显式使用原始可执行文件。直接 `command codex` 也会绕过 Bash 函数，因此不属于自动员工入口。

协作可给几个员工安排同一任务、不同文件范围。计划也要在范围中：

```bash
codex --chx-task spectrum --chx-employee fit --chx-scope analysis/spectrum/fit/ --chx-scope analysis/plans/2026-10-08-spectrum-fit.md
codex --chx-task spectrum --chx-employee plot --chx-scope analysis/spectrum/plot/ --chx-scope analysis/plans/2026-10-08-spectrum-plot.md
```

普通 `codex resume`、`codex resume --last`、`codex fork` 和嵌套 `exec resume` 不再被包装器阻止：未给员工选择器时，原样调用真实 CLI，保留原 cwd 与参数，恢复的是原生历史，不将旧会话伪装成已隔离员工。恢复明确的员工时指定 ID：

```bash
codex --chx-employee fit resume --last
```

显式员工模式的恢复要求已有登记；旧主目录会话不会被自动迁移。新建/显式员工模式的 CLI `-o/--output-last-message` 只能使用员工目录内的相对输出路径，拒绝 `..`、主目录绝对路径和链接逃逸。会绕过本地员工边界的 cwd/sandbox、额外写目录、远端执行、任意 profile/权限配置或信任绕过参数会明确拒绝；原生历史恢复按真实CLI原有语义，不声明员工隔离。

已在员工目录中调用 `codex` 会复用该员工；其受管理启动器已运行时第二次明确报忙，不能同时开启两个写入者。未指定员工的项目主目录普通新启动则创建另一目录，没有固定员工数量上限。

安装只追加/更新本项目标记，不改其他 Bash 配置；既有 codex 自定义冲突会拒绝自动覆盖。备份放在个人 Bash 文件同一文件系统的私有目录，目录0700、文件0600，并实际核对权限；其位置记在本地忽略的 `.omx/coordination/shell-backup.json`，私人内容不放 Git 或不支持 Unix 权限的数据盘。新终端自动加载，已经打开的旧 Bash 进程不会回溯加载新增函数；它需重新读取 `.bashrc` 才能使用新入口。

验证使用假 CLI 的真实子进程检查 argv/cwd，以及重新执行原18组真实Git/进程/bubblewrap测试；不以假 CLI 证明模型登录或实际付费会话。候选验收仍需要真实可用的 bubblewrap namespace 权限，普通终端与工具外层沙箱按实际能力判断；无能力时保留成果等待恢复。
