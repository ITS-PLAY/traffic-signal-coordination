import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

try:
    import psutil
except ImportError:
    psutil = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BENCHMARK_DIR = Path(__file__).resolve().parent / 'benchmark'
RESULT_DIR = Path(__file__).resolve().parent / 'result'
DEFAULT_REPEAT = int(os.environ.get('PERF_REPEAT', '1'))
DEFAULT_TIMEOUT_MS = int(os.environ.get('PERF_MAX_AVG_MS', '3600000'))
DEFAULT_P95_MS = int(os.environ.get('PERF_MAX_P95_MS', '3600000'))
PERF_USE_SEGMENTED_SEED = os.environ.get('PERF_USE_SEGMENTED_SEED', '').strip().lower()
PERF_SEGMENT_CROSS_COUNT = os.environ.get('PERF_SEGMENT_CROSS_COUNT', '').strip()
PERF_SEGMENT_OVERLAP_CROSS_COUNT = os.environ.get('PERF_SEGMENT_OVERLAP_CROSS_COUNT', '').strip()
PERF_RESULT_TAG = os.environ.get('PERF_RESULT_TAG', '').strip()


def _env_flag(value: str) -> bool:
    return value in {'1', 'true', 'yes', 'on'}


def _load_case(case_file: Path) -> Dict[str, Any]:
    with case_file.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def _apply_case_overrides(case_data: Dict[str, Any]) -> Dict[str, Any]:
    overridden = json.loads(json.dumps(case_data))
    config = overridden.setdefault('config', {})

    if PERF_USE_SEGMENTED_SEED:
        config['useSegmentedSeed'] = _env_flag(PERF_USE_SEGMENTED_SEED)
    if PERF_SEGMENT_CROSS_COUNT:
        config['segmentCrossCount'] = int(PERF_SEGMENT_CROSS_COUNT)
    if PERF_SEGMENT_OVERLAP_CROSS_COUNT:
        config['segmentOverlapCrossCount'] = int(PERF_SEGMENT_OVERLAP_CROSS_COUNT)

    return overridden


def _run_generator(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from main import main as local_generator_main

    result = local_generator_main(json.dumps(input_data, ensure_ascii=False))
    if isinstance(result, str):
        return json.loads(result)
    return result


def _get_case_metadata(case_name: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
    cross_list = case_data.get('crossList', []) or []
    road_length = case_data.get('roadLength', []) or []
    cross_flow = case_data.get('crossFlow') or {}

    cross_flow_totals = []
    for cross_id in cross_list:
        flow = cross_flow.get(cross_id, {}) if isinstance(cross_flow, dict) else {}
        if isinstance(flow, dict):
            cross_flow_totals.append(sum(value for value in flow.values() if isinstance(value, (int, float))))
        else:
            cross_flow_totals.append(0)

    avg_cross_flow = round(sum(cross_flow_totals) / len(cross_flow_totals)) if cross_flow_totals else 0

    return {
        'case': case_name,
        'file_name': case_name[:-5] if case_name.endswith('.json') else case_name,
        'cross_count': len(cross_list),
        'road_length_sum': round(sum(value for value in road_length if isinstance(value, (int, float))), 2),
        'avg_cross_flow': avg_cross_flow,
    }


def _get_environment_metadata() -> Dict[str, Any]:
    available_memory_gb = _get_available_memory_gb()

    return {
        'os': _get_os_description(),
        'cpu_count': os.cpu_count() or 0,
        'available_memory_gb': available_memory_gb,
    }


def _get_os_description() -> str:
    if platform.system() == 'Linux':
        os_release = Path('/etc/os-release')
        try:
            if os_release.exists():
                fields: Dict[str, str] = {}
                for line in os_release.read_text(encoding='utf-8').splitlines():
                    if '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    fields[key] = value.strip().strip('"')
                pretty_name = fields.get('PRETTY_NAME')
                if pretty_name:
                    return pretty_name
                name = fields.get('NAME', 'Linux')
                version = fields.get('VERSION') or fields.get('VERSION_ID', '')
                return f'{name} {version}'.strip()
        except OSError:
            pass

    system_name = platform.system()
    release = platform.release()
    version = platform.version()
    return ' '.join(part for part in [system_name, release, version] if part).strip()


def _get_available_memory_gb() -> float:
    if psutil is not None:
        return round(psutil.virtual_memory().available / (1024 ** 3), 2)

    if platform.system() == 'Linux':
        try:
            with open('/proc/meminfo', 'r', encoding='utf-8') as handle:
                for line in handle:
                    if line.startswith('MemAvailable:'):
                        free_kb = int(line.split()[1])
                        return round(free_kb / (1024 ** 2), 2)
        except (OSError, ValueError):
            return 0.0

    return 0.0


def _format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f'{value:.2f}'
    if isinstance(value, int):
        return str(value)
    return str(value)


def _pad_cell(value: str, width: int) -> str:
    return value.ljust(width)


def _format_table(headers: List[str], rows: List[List[Any]]) -> str:
    string_rows = [[_format_cell(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]

    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def build_row(row: List[str]) -> str:
        padded = [_pad_cell(cell, widths[index]) for index, cell in enumerate(row)]
        return '|' + '|'.join(f' {cell} ' for cell in padded) + '|'

    separator = '|' + '|'.join('-' * (width + 2) for width in widths) + '|'
    lines = [build_row(headers), separator]
    lines.extend(build_row(row) for row in string_rows)
    return '\n'.join(lines)


def _evaluate_once(iter_index: int, case_data: Dict[str, Any]) -> Dict[str, Any]:
    generator_result = _run_generator(case_data)

    if not isinstance(generator_result, dict):
        return {
            'iter_index': iter_index,
            'error': f'invalid generator response type: {type(generator_result).__name__}',
        }
    if generator_result.get('error') or generator_result.get('traceback'):
        return {
            'iter_index': iter_index,
            'error': (
                f"generator request failed: error={generator_result.get('error')}, "
                f"traceback={str(generator_result.get('traceback', ''))[:4000]}"
            ),
        }

    evaluation = generator_result.get('evaluation', {}) if isinstance(generator_result, dict) else {}
    avg_waiting_ratio = evaluation.get('avgParkingRatio') if isinstance(evaluation, dict) else None
    avg_speed = evaluation.get('avgSpeed') if isinstance(evaluation, dict) else None

    return {
        'iter_index': iter_index,
        'waiting_ratio': round(float(avg_waiting_ratio), 2) if avg_waiting_ratio is not None else None,
        'speed': round(float(avg_speed), 2) if avg_speed is not None else None,
    }


def _run_case(case_name: str, case_data: Dict[str, Any], repeat: int) -> Dict[str, Any]:
    durations_ms: List[float] = []
    success = 0
    errors: List[str] = []
    run_results: List[Dict[str, Any]] = []

    for run_index in range(repeat):
        started_at = time.perf_counter()
        result = _evaluate_once(run_index, case_data)
        run_results.append(result)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        durations_ms.append(round(elapsed_ms, 2))

        if result.get('error'):
            errors.append(result['error'])
        else:
            success += 1

    avg_ms = round(sum(durations_ms) / len(durations_ms), 2)
    min_ms = round(min(durations_ms), 2)
    max_ms = round(max(durations_ms), 2)
    p95_ms = round(_percentile(durations_ms, 95), 2)

    successful_results = [item for item in run_results if not item.get('error')]
    last_success_result = successful_results[-1] if successful_results else {}

    result = {
        'case': case_name,
        'repeat': repeat,
        'success': success,
        'failures': repeat - success,
        'durations_ms': durations_ms,
        'avg_ms': avg_ms,
        'min_ms': min_ms,
        'max_ms': max_ms,
        'p95_ms': p95_ms,
        'errors': errors,
        'waiting_ratio': last_success_result.get('waiting_ratio'),
        'speed': last_success_result.get('speed'),
    }
    result.update(_get_case_metadata(case_name, case_data))
    return result


def _percentile(values: List[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_benchmarks(repeat: int = DEFAULT_REPEAT) -> Dict[str, Any]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    environment = _get_environment_metadata()
    overrides = {
        'use_segmented_seed': _env_flag(PERF_USE_SEGMENTED_SEED) if PERF_USE_SEGMENTED_SEED else None,
        'segment_cross_count': int(PERF_SEGMENT_CROSS_COUNT) if PERF_SEGMENT_CROSS_COUNT else None,
        'segment_overlap_cross_count': int(PERF_SEGMENT_OVERLAP_CROSS_COUNT) if PERF_SEGMENT_OVERLAP_CROSS_COUNT else None,
        'result_tag': PERF_RESULT_TAG or None,
        'evaluator_url': os.environ.get('EVALUATOR_URL', '').strip() or None,
    }

    for case_file in sorted(BENCHMARK_DIR.glob('*.json')):
        case_data = _apply_case_overrides(_load_case(case_file))
        results.append(_run_case(case_file.name, case_data, repeat))

    suite_avg_ms = round(statistics.mean(item['avg_ms'] for item in results), 2) if results else 0.0
    suite_p95_ms = round(max(item['p95_ms'] for item in results), 2) if results else 0.0
    suite_failures = sum(item['failures'] for item in results)

    report = {
        'repeat': repeat,
        'case_count': len(results),
        'suite_avg_ms': suite_avg_ms,
        'suite_max_p95_ms': suite_p95_ms,
        'suite_failures': suite_failures,
        'environment': environment,
        'overrides': overrides,
        'cases': results,
    }

    report_text = format_summary(report)
    report_path = RESULT_DIR / 'performance_report.json'
    with report_path.open('w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    summary_path = RESULT_DIR / 'performance_summary.txt'
    with summary_path.open('w', encoding='utf-8') as handle:
        handle.write(report_text)

    if PERF_RESULT_TAG:
        tagged_report_path = RESULT_DIR / f'performance_report_{PERF_RESULT_TAG}.json'
        with tagged_report_path.open('w', encoding='utf-8') as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)

        tagged_summary_path = RESULT_DIR / f'performance_summary_{PERF_RESULT_TAG}.txt'
        with tagged_summary_path.open('w', encoding='utf-8') as handle:
            handle.write(report_text)

    return report


def format_summary(report: Dict[str, Any]) -> str:
    environment = report.get('environment', {})
    overrides = report.get('overrides', {})
    lines = [
        '=== traffic-signal-generator benchmark summary ===',
        f"cases={report['case_count']} repeat={report['repeat']}",
        f"suite_avg_ms={report['suite_avg_ms']} suite_max_p95_ms={report['suite_max_p95_ms']} failures={report['suite_failures']}",
        (
            f"environment: os={environment.get('os', '')} "
            f"cpu_count={environment.get('cpu_count', '')} "
            f"available_memory_gb={environment.get('available_memory_gb', '')}"
        ),
        (
            f"overrides: useSegmentedSeed={overrides.get('use_segmented_seed')} "
            f"segmentCrossCount={overrides.get('segment_cross_count')} "
            f"segmentOverlapCrossCount={overrides.get('segment_overlap_cross_count')} "
            f"evaluator_url={overrides.get('evaluator_url')} "
            f"result_tag={overrides.get('result_tag')}"
        ),
        '',
    ]

    headers = ['case', 'avg_ms', 'p95_ms', 'fail', 'cross_num', 'road_length_m', 'avg_cross_flow', 'waiting_ratio', 'speed']
    rows: List[List[Any]] = []
    sorted_cases = sorted(report['cases'], key=lambda item: (item.get('cross_count', 0), item.get('file_name', '')))
    for item in sorted_cases:
        rows.append([
            item['file_name'],
            item['avg_ms'],
            item['p95_ms'],
            item['failures'],
            item['cross_count'],
            item['road_length_sum'],
            item['avg_cross_flow'],
            item.get('waiting_ratio'),
            item.get('speed'),
        ])
    lines.append(_format_table(headers, rows))
    return '\n'.join(lines)


def assert_thresholds(report: Dict[str, Any], max_avg_ms: int, max_p95_ms: int) -> None:
    if report['suite_failures'] > 0:
        raise AssertionError(f"benchmark failed, failures={report['suite_failures']}")
    if max_avg_ms > 0 and report['suite_avg_ms'] > max_avg_ms:
        raise AssertionError(f"suite_avg_ms {report['suite_avg_ms']} exceeded threshold {max_avg_ms}")
    if max_p95_ms > 0 and report['suite_max_p95_ms'] > max_p95_ms:
        raise AssertionError(f"suite_max_p95_ms {report['suite_max_p95_ms']} exceeded threshold {max_p95_ms}")


def test_benchmark_suite() -> None:
    report = run_benchmarks()
    assert report['case_count'] > 0
    assert_thresholds(report, DEFAULT_TIMEOUT_MS, DEFAULT_P95_MS)


if __name__ == '__main__':
    benchmark_report = run_benchmarks()
    print(format_summary(benchmark_report))
    assert_thresholds(benchmark_report, DEFAULT_TIMEOUT_MS, DEFAULT_P95_MS)
