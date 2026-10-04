#!/usr/bin/env bash
# 用法：project_git.sh <git 子命令及参数>。不自动提交或推送。
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
if git -C "$project_root" rev-parse --git-dir >/dev/null 2>&1; then
    project_git=(git -C "$project_root")
else
    project_git=(git --git-dir="$project_root/.project-git" --work-tree="$project_root")
    if [[ ! -f "$project_root/.project-git/HEAD" ]]; then
        "${project_git[@]}" init
        "${project_git[@]}" symbolic-ref HEAD refs/heads/main
    fi
fi
"${project_git[@]}" config core.hooksPath "$project_root/.githooks"
if ! "${project_git[@]}" remote get-url origin >/dev/null 2>&1; then
    "${project_git[@]}" remote add origin https://gitee.com/chx6/ns_analysis.git
fi
if [[ $# -eq 0 ]]; then
    set -- status --short
fi
# 某些数据盘不支持执行权限。用临时副本执行 hooks，源文件仍随项目版本化。
project_hooks=$(mktemp -d "${TMPDIR:-/tmp}/chx-git-hooks.XXXXXXXX")
trap 'rm -f -- "$project_hooks/pre-commit" "$project_hooks/pre-push"; rmdir -- "$project_hooks"' EXIT
cp -- "$project_root/.githooks/pre-commit" "$project_root/.githooks/pre-push" "$project_hooks/"
chmod 700 "$project_hooks/pre-commit" "$project_hooks/pre-push"
"${project_git[@]}" -c core.hooksPath="$project_hooks" "$@"
