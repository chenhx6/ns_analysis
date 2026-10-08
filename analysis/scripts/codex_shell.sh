# Source from interactive Bash; keep the original executable and argv intact.
_CHX_CODEX_ENTRY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/codex_entry.py"
codex() {
    local chx_codex_binary
    chx_codex_binary="$(type -P codex)" || return
    if [[ -z "$chx_codex_binary" ]]; then
        printf '%s\n' 'Codex executable was not found in PATH' >&2
        return 127
    fi
    python3 "$_CHX_CODEX_ENTRY" --executable "$chx_codex_binary" -- "$@"
}
