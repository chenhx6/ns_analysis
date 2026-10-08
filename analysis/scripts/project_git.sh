#!/usr/bin/env bash
# 用法：project_git.sh [--workspace /absolute/path] <git 子命令及参数>。
set -euo pipefail
# Never route an employee checkout through another session's index or objects.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX
control_script="$(readlink -f -- "${BASH_SOURCE[0]}")"
control_root="$(cd -- "$(dirname -- "$control_script")/../.." && pwd -P)"
project_root="$control_root"
if [[ "${1:-}" == --workspace ]]; then
    if [[ $# -lt 3 || "$2" != /* || ! -d "$2" ]]; then
        echo '--workspace requires an existing absolute repository directory and Git command' >&2
        exit 2
    fi
    project_root="$(cd -- "$2" && pwd -P)"
    shift 2
fi
if [[ -f "$project_root/.omx/employee.json" ]]; then
    for argument in "$@"; do
        if [[ "$argument" == push ]]; then
            echo 'Employee pushes are disabled; use project_sync.py sync to submit, then collect from the project.' >&2
            exit 1
        fi
    done
fi
if git -C "$project_root" rev-parse --git-dir >/dev/null 2>&1; then
    project_git=(git -C "$project_root")
else
    project_git=(git --git-dir="$project_root/.project-git" --work-tree="$project_root")
    if [[ ! -f "$project_root/.project-git/HEAD" ]]; then
        "${project_git[@]}" init
        "${project_git[@]}" symbolic-ref HEAD refs/heads/main
    fi
fi
if [[ "$("${project_git[@]}" config --get core.hooksPath || true)" != "$project_root/.githooks" ]]; then
    "${project_git[@]}" config core.hooksPath "$project_root/.githooks"
fi
if ! "${project_git[@]}" remote get-url origin >/dev/null 2>&1; then
    "${project_git[@]}" remote add origin https://gitee.com/chx6/ns_analysis.git
fi
if [[ $# -eq 0 ]]; then
    set -- status --short
fi
# Run fixed control scripts, never candidate-controlled hook contents.
project_hook_tmp="${TMPDIR:-/tmp}"
if [[ -f "$project_root/.omx/employee.json" ]]; then
    project_hook_tmp="$project_root/.omx/tmp"
    mkdir -p -- "$project_hook_tmp"
fi
project_hooks=$(mktemp -d "$project_hook_tmp/chx-git-hooks.XXXXXXXX")
trap 'rm -f -- "$project_hooks/pre-commit" "$project_hooks/pre-push" "$project_hooks/post-commit"; rmdir -- "$project_hooks"' EXIT
{
    printf '#!/usr/bin/env bash\nset -euo pipefail\nexec python3 %q\n' "$control_root/analysis/scripts/check_git_content.py"
} > "$project_hooks/pre-commit"
{
    printf '#!/usr/bin/env bash\nset -euo pipefail\n'
    printf 'if [[ -f %q ]]; then echo "Employee pushes are disabled; submit and collect instead." >&2; exit 1; fi\n' "$project_root/.omx/employee.json"
    printf 'exec python3 %q --push --remote "${1:-}"\n' "$control_root/analysis/scripts/check_git_content.py"
} > "$project_hooks/pre-push"
{
    printf '#!/usr/bin/env bash\nset -euo pipefail\nexec python3 %q --root %q finalize\n' "$control_root/analysis/scripts/task_delivery.py" "$project_root"
} > "$project_hooks/post-commit"
chmod 700 "$project_hooks/pre-commit" "$project_hooks/pre-push" "$project_hooks/post-commit"
"${project_git[@]}" -c core.hooksPath="$project_hooks" "$@"
