#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/time-offset-build.XXXXXX")
# Keep failed fixture/log evidence; caller can remove its explicitly returned directory.
printf 'Evidence directory: %s\n' "$build_dir"
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic $(root-config --cflags) time_offset/time_offset.cc $(root-config --libs) -o "$build_dir/time_offset" 2>&1 | tee "$build_dir/build.log"
"$build_dir/time_offset" --self-test "$build_dir/self-test" | tee "$build_dir/self-test.log"
python3 -m json.tool "$build_dir/self-test/calibration/json-failure/completion.json" > /dev/null
"$build_dir/time_offset" --verify-artifacts "$build_dir/self-test/diagnostic.root"
"$build_dir/time_offset" --verify-artifacts "$build_dir/self-test/invalid.root"
if [[ "${1:-}" == --mission ]]; then
    "$build_dir/time_offset" --mission time_offset/final-candidates/mission_inputs.txt analysis/20261008-time-offset-design/completion.json
    exit $?
fi
for artifact in "$@"; do
    "$build_dir/time_offset" --verify-artifacts "$artifact"
done
