#!/usr/bin/env bash

# 用户配置；相对数据目录从脚本所在目录计算，{run}替换为run编号。
data_dir="../../decode_data"
program="time_offset"
input_pattern='data_C2_{run}_{run}_wave.root'
runs=()                 # 例如：(6015 6018 6020)；非空时优先使用此列表。
start_run=""            # runs为空时，填写起止编号，包含两端。
end_run=""
exclude_runs=()         # 例如：(6018 6023)。

cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1
[[ -d "$data_dir" && -x "./$program" ]] || { echo "请检查数据目录和程序名。" >&2; exit 1; }

# 列表与范围二选一；调度前完成全部筛选，重复run只保留一次。
if ((${#runs[@]} == 0)); then
    [[ $start_run =~ ^[1-9][0-9]*$ && $end_run =~ ^[1-9][0-9]*$ && $start_run -le $end_run ]] || {
        echo "请填写runs列表，或有效的start_run/end_run。" >&2; exit 1;
    }
    for ((run=start_run; run<=end_run; run++)); do runs+=("$run"); done
fi
for run in "${runs[@]}" "${exclude_runs[@]}"; do
    [[ $run =~ ^[1-9][0-9]*$ ]] || { echo "无效run编号：$run" >&2; exit 1; }
done

declare -A seen=()
selected=() excluded=() missing=()
for run in "${runs[@]}"; do
    [[ ${seen[$run]+yes} ]] && continue
    seen[$run]=1
    file=${input_pattern//\{run\}/$run}
    if [[ " ${exclude_runs[*]} " == *" $run "* ]]; then
        excluded+=("$run")
    elif [[ -f "$data_dir/$file" ]]; then
        selected+=("$run")
    else
        missing+=("$run")
    fi
done
printf '运行：%s\n排除：%s\n缺失：%s\n' "${selected[*]}" "${excluded[*]}" "${missing[*]}"

# 最多5个后台进程；任意进程结束后补位，子程序输出全部丢弃。
for run in "${selected[@]}"; do
    while (( $(jobs -pr | wc -l) >= 5 )); do wait -n; done
    "./$program" "$run" >/dev/null 2>&1 &
done
wait
