#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
processor=${1:?usage: run_execution.sh PROCESSOR NEW_OUTPUT_DIRECTORY}
output=${2:?usage: run_execution.sh PROCESSOR NEW_OUTPUT_DIRECTORY}
output=$(realpath -m -- "$output")
policy=${5:-weighted}
[[ "$policy" == weighted || "$policy" == main ]] || { echo "Invalid pre-training candidate policy" >&2; exit 1; }
budget=${3:-2000000}
training_begin=${4:-0}
training_end=$((training_begin+budget))
training_core_begin=$((training_begin+10000))
training_core_end=$((training_end-10000))
source_root=/home/ys/data_401/data/chx_20260622
[[ ! -e "$output" ]] || { echo "Refusing existing output directory: $output" >&2; exit 1; }
mkdir -p "$output"
: > "$output/mission_inputs.txt"
for group in A B C; do
    case "$group" in
        A) training=6015; grid=0; comparisons='6019 6024 6028' ;;
        B) training=6035; grid=0; comparisons='6045 6050' ;;
        C) training=6054; grid=50000; comparisons='6061 6065 6075 6078' ;;
    esac
    "$processor" --scan --input "$source_root/decode_data/data_C2_${training}_${training}_wave.root" --output "$output/train_$group.root" --ge-run "$training" --csi-run "$training" --group "$group" --slice "train-$training-$training_begin-$training_end" --begin "$training_begin" --end "$training_end" --core-begin "$training_core_begin" --core-end "$training_core_end" --chunk 100000 --max-gap-ns 1000000000 --slice-entries "$grid" --candidate-policy "$policy"
    "$processor" --suggest-windows "$output/train_$group.root" "$output/windows_$group.csv"
    : > "$output/comparisons_$group.txt"
    # All windows derive exclusively from this training artifact; same source/parameters/offsets for every run.
    for run in $comparisons; do
        begin=$training_begin
        if [[ "$group" == C && "$run" == 6061 && "$begin" == 0 ]]; then begin=2000000; fi
        end=$((begin+budget)); core_begin=$((begin+10000)); core_end=$((end-10000))
        "$processor" --freeze --training "$output/train_$group.root" --windows "$output/windows_$group.csv" --template0 "$source_root/decode_data/DecodeAndSortAll/crate0.dat" --template1 "$source_root/decode_data/DecodeAndSortAll/crate1.dat" --input "$source_root/decode_data/data_C2_${run}_${run}_wave.root" --output "$output/frozen_${group}_${run}" --ge-run "$run" --csi-run "$run" --group "$group" --slice "holdout-$run-$begin-$end" --begin "$begin" --end "$end" --core-begin "$core_begin" --core-end "$core_end" --chunk 100000 --max-gap-ns 1000000000 --slice-entries "$grid" --candidate-policy "$policy"
    done
    # No holdout is read until all per-group comparisons and frozen candidates are on disk.
    for run in $comparisons; do
        "$processor" --validate "$output/frozen_${group}_${run}" "$output/validated_${group}_${run}"
        printf '%s\n' "$output/validated_${group}_${run}" >> "$output/comparisons_$group.txt"
    done
    "$processor" --combine "$output/comparisons_$group.txt" "$output/group_$group"
    printf '%s\n' "$output/group_$group" >> "$output/mission_inputs.txt"
done
"$processor" --provenance "$output/mission_inputs.txt" "$output/sources.csv"
"$processor" --summarize "$output/mission_inputs.txt" "$output/reasons.csv"
"$processor" --mission "$output/mission_inputs.txt" "$output/completion.json"
