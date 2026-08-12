# Benchmark Record - Overlap Comparison (2 cases, full combo)

- Date: `2026-04-16`
- Evaluator: `http://127.0.0.1:3001/algorithm/invoke`
- Common settings: `useSegmentedSeed=true`、`DEFAULT_SEGMENT_TOP_K=0`、`DEFAULT_SEGMENT_BEAM_WIDTH=0`
- Compared variants: `segmentOverlapRoads=0/1/2`

## Suite Summary

| Variant | suite_avg_ms | suite_max_p95_ms |
|---|---:|---:|
| segmentOverlapRoads=0, full combo | 267939.18 | 415536.42 |
| segmentOverlapRoads=1, full combo | 143939.97 | 172163.81 |
| segmentOverlapRoads=2, full combo | 229114.44 | 283662.47 |

## Case Comparison

| Case | overlap=0 avg_ms | overlap=1 avg_ms | overlap=2 avg_ms | best latency |
|---|---:|---:|---:|---|
| dengcaijie_suzhen-hehong | 120341.94 | 115716.13 | 174566.41 | overlap=1 |
| fuchunlu_sanxin-jiangjin | 415536.42 | 172163.81 | 283662.47 | overlap=1 |

## Final Quality Snapshot

| Case | Variant | outbound_avgSpeed | inbound_avgSpeed | outbound_avgParkingRatio | inbound_avgParkingRatio |
|---|---|---:|---:|---:|---:|
| dengcaijie_suzhen-hehong | overlap=0 | 37.054203 | 40.996315 | 0.428571 | 0.344729 |
| dengcaijie_suzhen-hehong | overlap=1 | 37.884881 | 40.050051 | 0.401734 | 0.342262 |
| dengcaijie_suzhen-hehong | overlap=2 | 36.260532 | 41.984714 | 0.505882 | 0.290698 |
| fuchunlu_sanxin-jiangjin | overlap=0 | 32.861408 | 36.341766 | 0.310458 | 0.320611 |
| fuchunlu_sanxin-jiangjin | overlap=1 | 33.736602 | 35.523115 | 0.257862 | 0.374502 |
| fuchunlu_sanxin-jiangjin | overlap=2 | 32.237184 | 36.858082 | 0.275542 | 0.306569 |

## Interpretation

- 从这 2 个 5 路口场景实测看，`segmentOverlapRoads=1` 的整体耗时最低。
- `segmentOverlapRoads=2` 明显拉高了候选生成和整体耗时。
- `segmentOverlapRoads=0` 在 `dengcaijie_suzhen-hehong` 上更快，但在 `fuchunlu_sanxin-jiangjin` 上明显慢于 `overlap=1`。
- 就这两例而言，`overlap=1` 是当前三组里更均衡的默认值。