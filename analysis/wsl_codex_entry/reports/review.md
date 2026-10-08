# WSL 命令入口审查

独立 code-reviewer 与 architect 均限定检查本次普通 codex 入口、Bash source、已有 launcher 适配和真实回归，不重新设计已验收的员工协调机制。

发现并修复的具体问题：`--` 后的字面提示被误判帮助；未知或嵌套 resume/fork 未绑定员工；原生 value option 漏判；CLI 自己写输出文件的路径越界；可改变写权限的 profile/config/remote/trust 绕过；云端/守护命令被误当成本地员工；私人 Bash 备份/临时文件权限。回归保留实际 Bash/子进程 cwd/argv、参数拒绝和配置原文保护的断言。

最终代码审查 APPROVE，架构 CLEAR；批准范围为项目 Bash 入口启动的本地员工。源文件语法与验证记录指纹核对通过，shell 函数与员工登记都不提供额外权限。原 CLI 保留，父进程使用原有 outbox 收集/串行整合流程。

主代理已通过真实宿主审批追加个人 Bash source 段。实际新交互 Bash 的 `type -t codex` 返回 function，`codex --version` 返回 codex-cli 0.161.0，退出 0。安装核对发现数据盘不保留 chmod 权限，改为在个人 Bash 所在文件系统保存原文并实际核对0700目录/0600文件；逐字核对新备份后仅移除精确的本任务旧副本，最终隐私修正获代码审查 APPROVE。安装原文保留、标记唯一；既有已打开终端不会回溯加载，既有 Codex 会话也不会自动迁移。

完整实际验收：`python3 analysis/wsl_codex_entry/verify.py`。它运行八组入口真实进程回归、变化后的十八组 Git/进程/bubblewrap 回归和现有同步/配置/指纹检查，全部退出 0。假 CLI 检查真实参数和目录选择，不证明付费模型调用或登录；这些未执行，也不宣称通过。
