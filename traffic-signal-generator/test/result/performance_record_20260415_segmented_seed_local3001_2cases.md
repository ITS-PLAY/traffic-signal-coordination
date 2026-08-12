# Performance Record - Segmented Seed Local 3001 (2 cases)

- Date: `2026-04-15`
- Runner: `traffic-signal-generator/test/test_performance.py`
- Evaluator: `http://127.0.0.1:3001/algorithm/invoke`
- Benchmark cases:
  - `traffic-signal-generator/test/benchmark/shuzhilu_shengtangba-ali.json`
  - `traffic-signal-generator/test/benchmark/shuzhilu_shengtangba-yunxiao.json`
- Shared override: `useSegmentedSeed=true`

## Summary Files

- Baseline summary: `traffic-signal-generator/test/result/performance_summary_20260415_segmented_seed_local3001_2cases_baseline.txt`
- Baseline report: `traffic-signal-generator/test/result/performance_report_20260415_segmented_seed_local3001_2cases_baseline.json`
- Optimized summary: `traffic-signal-generator/test/result/performance_summary_20260415_segmented_seed_local3001_2cases_optimized.txt`
- Optimized report: `traffic-signal-generator/test/result/performance_report_20260415_segmented_seed_local3001_2cases_optimized.json`

## Comparison

| Case | Baseline avg_ms | Optimized avg_ms | Ratio | Delta |
|---|---:|---:|---:|---:|
| shuzhilu_shengtangba-ali | 642564.87 | 35667.30 | 0.055x | -94.45% |
| shuzhilu_shengtangba-yunxiao | 22203.80 | 16403.72 | 0.739x | -26.12% |
| suite_avg_ms | 332384.34 | 26035.51 | 0.078x | -92.17% |
| suite_max_p95_ms | 642564.87 | 35667.30 | 0.055x | -94.45% |

## Applied Optimizations

- Added minimum offset spacing constraint: `DEFAULT_MIN_OFFSET_DELTA=3`
- Switched GA population sizing to dynamic sizing based on `optional_solutions`、变量维度和并行度
- Added early stop using `min_gen=5`、`patience=4`、`min_improvement=0.05`
- Replaced default polynomial mutation with bounded perturbation mutation plus spacing repair

## Notes

- `shuzhilu_shengtangba-ali` 优化最明显，主要受益于 `population_size: 200 -> 16` 和第 `8` 代提前终止。
- `shuzhilu_shengtangba-yunxiao` 的初始搜索空间较小，收益主要来自第 `5` 代提前终止和 `population_size: 100 -> 12`。
- 当前优化后仍保持 `failures=0`。
