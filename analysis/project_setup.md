# 项目配置记录

日期：2026-10-05。

## 目录规则

按用户约定，`chx_20260622/` 是工作及处理后数据的存放目录；同级 `Ge/`、`CsI/` 是只读原始数据；同级 `software/` 属于他人，不作操作。`analysis/` 存放记录本、代码、配置、结果图等小文件；解码与其他大型中间数据保留在项目内专用数据子目录。

项目规则写入根目录 `AGENTS.md` 和 `README.md`；项目技能为 `skills/chx-data-analysis/SKILL.md`。项目约定、技能、hooks 和 `analysis/` 同步到 `https://gitee.com/chx6/ns_analysis.git`；数据与编译产物排除。

## 本地配置

- 当前环境的 `.git`、`.agents`、`.codex` 不可写，Git 元数据使用 `.project-git/`。不修改受保护目录权限。
- 使用 `bash analysis/code/project_git.sh <git 参数>` 操作本地仓库；脚本兼容 Git 2.25，并处理数据盘不能保留可执行权限的问题。
- 提交邮箱为用户提供的 `2272149417@qq.com`；作者名采用目标远端账号 `chx6`。
- `.gitignore` 使用根目录白名单；`.githooks/` 的提交与推送检查默认限制单文件为 25 MiB。

## 验证

已完成技能格式验证、脚本语法检查和本地待提交文件检查。通过独立临时仓库验证了：允许正常代码和文档提交、拒绝中间 ROOT 数据、拒绝超过 25 MiB 的文件、拒绝符号链接、允许正常历史推送到本地测试仓库，以及拒绝推送历史中已在最新版本删除的数据文件。测试不修改原始数据目录或他人的软件目录。

已验证解码 ROOT、其他数据子目录、本地 Git 元数据和 `decodeandsort` 编译产物均被忽略。

## 远端状态

首次配置时受限环境无法解析 `gitee.com`。用户要求重试后，通过获准的网络访问成功执行 `ls-remote --symref origin HEAD refs/heads/*`，确认远端当前无分支和提交，首次同步目标为 `main`。后续同步仍需先获取并核对远端历史，再正常推送。

## 项目技能与工具扩展

按用户指定读取七个仓库，完整安装 Ponytail、shuorenhua、humanizer、Nature 的全部技能单元及 Crawl4AI 全部 extras，并用 OMX 原生源码执行 project setup。技能总计 62 个入口：57 个上游技能、既有数据分析技能、4 个项目适配入口。OMX 原生角色、提示词、hooks、MCP 与四个原生组件已安装；Python、Chromium、Mermaid/Puppeteer 和 LibreOffice 保存在项目内。

固定来源、许可证、恢复脚本和运行限制见 `analysis/third_party/INSTALL.md`。13 项安装及离线运行验收通过，证据在 `analysis/third_party/verification.json`。独立 Codex CLI 尚未登录，模型调用与真实 Team 运行不属于本次已通过的检查。
