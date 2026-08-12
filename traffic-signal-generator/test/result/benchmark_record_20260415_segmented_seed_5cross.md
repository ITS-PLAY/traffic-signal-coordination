# Benchmark Record - Segmented Seed / Overlap vs Baseline

- Date: `2026-04-15`
- Scenario: `traffic-signal-generator/test/benchmark/dengcaijie_suzhen-hehong.json`
- Scope: `generate_optional_plan_parallel()` stage only
- Reason: full `main -> GA -> evaluator` chain showed unstable `ts-evaluator` DNS resolution in this environment, so this comparison focuses on the optional plan generation stage where the `P1/P2` optimization lands directly.

## Case Summary

- Cross count: `5`
- Road count: `4`
- Mode: `best`
- Processes: `11`
- Profiling: enabled

## Comparison

| Variant | useSegmentedSeed | segmentOverlapRoads | task_count | optional_solution_count | band_task_execute_ms | elapsed_ms | elapsed_ratio_vs_baseline |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_no_segment | false | - | 162 | 75 | 8623.579 | 8624.919 | 1.000x |
| segmented_no_overlap | true | 0 | 60 | 12 | 4441.340 | 4443.171 | 0.515x |
| segmented_with_overlap | true | 1 | 162 | 75 | 13469.008 | 13470.630 | 1.562x |

## Delta

- `baseline_no_segment -> segmented_no_overlap`
  - `optional_solution_count`: `75 -> 12`，减少 `84.0%`
  - `task_count`: `162 -> 60`，减少 `63.0%`
  - `band_task_execute_ms`: `8623.579 -> 4441.340`，减少约 `48.5%`
  - `elapsed_ms`: `8624.919 -> 4443.171`，减少约 `48.5%`
- `segmented_no_overlap -> segmented_with_overlap`
  - `optional_solution_count`: `12 -> 75`，增加 `525.0%`
  - `task_count`: `60 -> 162`，增加 `170.0%`
  - `band_task_execute_ms`: `4441.340 -> 13469.008`，增加约 `203.3%`
  - `elapsed_ms`: `4443.171 -> 13470.630`，增加约 `203.2%`
- `baseline_no_segment -> segmented_with_overlap`
  - `optional_solution_count`: `75 -> 75`，无变化
  - `task_count`: `162 -> 162`，无变化
  - `band_task_execute_ms`: `8623.579 -> 13469.008`，增加约 `56.2%`
  - `elapsed_ms`: `8624.919 -> 13470.630`，增加约 `56.2%`

## Interpretation

- `P1` 的分段种子策略在该 5 路口场景下，明显减少了候选组合数量，并带来接近 `48.5%` 的候选生成耗时下降。
- 当前 `P2` 的重叠分段配置（`segmentOverlapRoads=1`）在该场景下把候选数和任务数拉回到接近基线，且总耗时达到 baseline 的 `1.562x`。
- 这说明当前 overlap 拼接约束虽然提升了段间一致性，但在这个 5 路口案例里，额外搜索成本明显偏高，暂时更适合作为受控开关而不是默认配置。
- 后续若继续优化 overlap 路径，建议优先关注重叠段去重、候选裁剪和拼接前的提前剪枝，而不是继续单纯放宽搜索空间。

## Notes

- `baseline_no_segment` 实测输出来自 `useSegmentedSeed=false`。
- `segmented_no_overlap` 使用 `segmentSize=3`、`segmentTopK=4`、`segmentBeamWidth=12`、`segmentOverlapRoads=0`。
- `segmented_with_overlap` 使用 `segmentSize=3`、`segmentTopK=4`、`segmentBeamWidth=12`、`segmentOverlapRoads=1`。
- 当前默认配置已切换为 `segmentOverlapRoads=0`，即默认不重叠。
- 本记录未对 GA 整体收敛质量做结论，仅记录前置候选生成阶段的性能对比。
