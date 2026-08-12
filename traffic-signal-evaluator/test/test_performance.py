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

import requests

try:
    import psutil
except ImportError:
    psutil = None

EVALUATOR_FUNC_NAME = 'ts_evaluator'
EVALUATOR_URL = os.environ.get('EVALUATOR_URL', 'http://ts-evaluator')
EVALUATOR_URL_PATH = '/algorithm/invoke'

BENCHMARK_DIR = Path(__file__).resolve().parent / 'benchmark'
RESULT_DIR = Path(__file__).resolve().parent / 'result'
DEFAULT_REPEAT = int(os.environ.get('PERF_REPEAT', '3'))
DEFAULT_TIMEOUT_MS = int(os.environ.get('PERF_MAX_AVG_MS', '5000'))
DEFAULT_P95_MS = int(os.environ.get('PERF_MAX_P95_MS', '5000'))


def _load_case(case_file: Path) -> Dict[str, Any]:
    with case_file.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def _invoke(case_data: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        f'{EVALUATOR_URL}{EVALUATOR_URL_PATH}',
        json={'in': case_data, 'func': EVALUATOR_FUNC_NAME},
        timeout=120,
    )
    if not response.ok:
        body = response.text.strip()
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = None

        if isinstance(error_payload, dict):
            trace = error_payload.get('traceback')
            error = error_payload.get('error')
            if trace:
                raise AssertionError(
                    f"evaluator request failed: status={response.status_code}, error={error}, traceback={trace[:4000]}"
                )

        raise AssertionError(f'evaluator request failed: status={response.status_code}, body={body[:1000]}')
    payload = response.json()
    if 'out' not in payload:
        raise AssertionError(f'empty simulation result from {EVALUATOR_URL}{EVALUATOR_URL_PATH}')
    result = payload['out'] or {}
    if not isinstance(result, dict):
        raise AssertionError(f'invalid evaluator result type from {EVALUATOR_URL}{EVALUATOR_URL_PATH}: {type(result).__name__}')
    if result.get('error') or result.get('traceback'):
        raise AssertionError(
            f"evaluator business failed: error={result.get('error')}, traceback={str(result.get('traceback', ''))[:4000]}"
        )
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


def _preflight_check(case_name: str, case_data: Dict[str, Any]) -> None:
    started_at = time.perf_counter()
    try:
        metrics = _invoke(case_data)
    except Exception as exc:
        raise AssertionError(f'preflight failed for {case_name}: {exc}') from exc
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    print(
        f"[preflight] evaluator reachable: url={EVALUATOR_URL}{EVALUATOR_URL_PATH}, "
        f"case={case_name}, elapsed_ms={elapsed_ms}"
    )
    sys.stdout.flush()


def _run_case(case_name: str, case_data: Dict[str, Any], repeat: int) -> Dict[str, Any]:
    durations_ms: List[float] = []
    success = 0
    errors: List[str] = []
    latest_metrics: Dict[str, Any] = {}

    for _ in range(repeat):
        started_at = time.perf_counter()
        try:
            latest_metrics = _invoke(case_data)
            success += 1
        except Exception as exc:
            errors.append(str(exc))
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        durations_ms.append(round(elapsed_ms, 2))

    avg_ms = round(sum(durations_ms) / len(durations_ms), 2)
    min_ms = round(min(durations_ms), 2)
    max_ms = round(max(durations_ms), 2)
    p95_ms = round(_percentile(durations_ms, 95), 2)

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
    case_files = sorted(BENCHMARK_DIR.glob('*.json'))
    if not case_files:
        raise AssertionError(f'no benchmark cases found in {BENCHMARK_DIR}')
    environment = _get_environment_metadata()

    first_case = _load_case(case_files[0])
    _preflight_check(case_files[0].name, first_case)

    results: List[Dict[str, Any]] = []
    for case_file in case_files:
        case_data = _load_case(case_file)
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
        'evaluator_url': EVALUATOR_URL,
        'func_name': EVALUATOR_FUNC_NAME,
        'path': EVALUATOR_URL_PATH,
        'environment': environment,
        'cases': results,
    }

    report_path = RESULT_DIR / 'performance_report.json'
    with report_path.open('w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    summary_path = RESULT_DIR / 'performance_summary.txt'
    with summary_path.open('w', encoding='utf-8') as handle:
        handle.write(format_summary(report))

    return report


def format_summary(report: Dict[str, Any]) -> str:
    environment = report.get('environment', {})
    lines = [
        '=== traffic-signal-evaluator benchmark summary ===',
        f"url={report['evaluator_url']}{report['path']} func={report['func_name']}",
        f"cases={report['case_count']} repeat={report['repeat']}",
        f"suite_avg_ms={report['suite_avg_ms']} suite_max_p95_ms={report['suite_max_p95_ms']} failures={report['suite_failures']}",
        (
            f"environment: os={environment.get('os', '')} "
            f"cpu_count={environment.get('cpu_count', '')} "
            f"available_memory_gb={environment.get('available_memory_gb', '')}"
        ),
        '',
    ]

    headers = ['case', 'avg_ms', 'p95_ms', 'fail', 'cross_num', 'road_length_m', 'avg_cross_flow']
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
