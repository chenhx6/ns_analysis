# Source this independently; existing codex customizations remain untouched.
_CHX_CO_ENTRY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/codex_entry.py"
co() {
    local chx_co_binary
    chx_co_binary="$(type -P codex)" || return
    if [[ -z "$chx_co_binary" ]]; then
        printf '%s\n' 'Codex executable was not found in PATH' >&2
        return 127
    fi
    python3 "$_CHX_CO_ENTRY" --project-prompt --executable "$chx_co_binary" -- "$@"
}
