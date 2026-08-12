import json
import re
import sys
import os
import traceback
from collections import OrderedDict

from algorithms.bandwidth_algorithm.run_band_algorithm import generate_optional_plan_parallel
from algorithms.genetic_algorithm.run_GA import run_genetic_algorithm
from utils.logger import log
from utils.np_encoder import *
from utils.profiling import is_profiling_enabled, profile_stage, finalize_profile_summary
from config.protocol_output import generate_output
from common.common_vars import GA_ITERATIONS
from utils.util import HeartbeatManager


def _parse_num_process(env_value):
    if env_value is None:
        return None

    normalized_value = str(env_value).strip()
    if not normalized_value:
        return None

    try:
        parsed_value = int(normalized_value)
    except ValueError:
        log.warning('invalid NUM_PROCESS=%s, fallback to auto process selection', env_value)
        return None

    return parsed_value if parsed_value > 0 else None


DEFAULT_NUM_PROCESS = _parse_num_process(os.environ.get("NUM_PROCESS"))


def _extract_offset_from_plan_info(plan_info):
    """从 planInfo 字符串中提取单个路口 offset。"""
    if not isinstance(plan_info, str):
        raise ValueError('planInfo item must be a string')

    parts = [part.strip() for part in plan_info.split(',')]
    if len(parts) < 2:
        raise ValueError(f'invalid planInfo format: {plan_info}')

    matched = re.search(r'-?\d+', parts[1])
    if matched is None:
        raise ValueError(f'offset not found in planInfo: {plan_info}')
    return int(matched.group())



def _current_plan_as_optional_solutions(input_data):
    """从当前方案中提取 relative_offset，作为评估模式下的唯一候选解。"""
    try:
        cross_list = input_data.get('crossList') or []
        if len(cross_list) <= 1:
            return [[]]

        plan_info = input_data.get('planInfo') or {}
        relative_offset = []
        for cross_id in cross_list[1:]:
            relative_offset.append(_extract_offset_from_plan_info(plan_info[cross_id]))
        return [relative_offset]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        log.warning('failed to extract current plan as optional_solutions: %s', exc)
        return []


def _resolve_iteration_num(input_data, is_evaluation):
    """统一解析遗传算法迭代代数配置。"""
    if is_evaluation:
        return 1

    config = input_data.get('config', {}) if isinstance(input_data, dict) else {}
    configured_value = config.get('iterationNum', GA_ITERATIONS)
    try:
        return max(1, int(configured_value))
    except (TypeError, ValueError):
        log.warning('invalid iterationNum=%s, fallback to default=%s', configured_value, GA_ITERATIONS)
        return GA_ITERATIONS


def _build_main_profile_summary(profiling, is_evaluation, optional_solutions, n_max_gen):
    return {
        **dict(profiling),
        'only_evaluation': is_evaluation,
        'optional_solution_count': len(optional_solutions),
        'n_max_gen': n_max_gen,
    }


def _attach_profile_debug(output, input_data, main_profile_summary, enable_profiling):
    if not enable_profiling:
        return output
    debug_profile = OrderedDict()
    nested_profile = input_data.get('_profile_debug', {}) if isinstance(input_data, dict) else {}
    for key, value in nested_profile.items():
        debug_profile[key] = value
    debug_profile['generator_main'] = main_profile_summary
    output['debug'] = {'profile': debug_profile}
    return output

def main_sse(input_data):
    """调用算法，输出方案（相位差）和评价指标。"""
    try:
        input_data = json.loads(input_data)
        enable_profiling = is_profiling_enabled(input_data)
        profiling = OrderedDict()
        log.info('input of algorithm: {}'.format(input_data))
        is_evaluation = input_data.get('config', {}).get('onlyEvaluation', False)
        if is_evaluation:
            with profile_stage(profiling, 'current_plan_extract', enable_profiling):
                optional_solutions = _current_plan_as_optional_solutions(input_data)
            if not optional_solutions:
                raise ValueError('failed to extract current plan for evaluation')
        else:
            with profile_stage(profiling, 'optional_plan_generate', enable_profiling):
                optional_solutions = generate_optional_plan_parallel(input_data, num_processes=DEFAULT_NUM_PROCESS)
        n_max_gen = _resolve_iteration_num(input_data, is_evaluation)

        def generation_callback(generation, best_item):
            result = {
                'event': 'iteration_complete',
                'result': {
                    'generation': generation,
                    'best_item': best_item,
                },
            }
            print(json.dumps(result, cls=NpEncoder, ensure_ascii=False))
            sys.stdout.flush()

        with HeartbeatManager() as heartbeat_manager:
            final_result = None
            with profile_stage(profiling, 'ga_run', enable_profiling):
                for event in run_genetic_algorithm(input_data, optional_solutions, n_max_gen, generation_callback, DEFAULT_NUM_PROCESS):
                    if event.get('event') == 'algorithm_complete':
                        final_result = event.get('result')

            if final_result is not None:
                with profile_stage(profiling, 'output_generate', enable_profiling):
                    output = generate_output(input_data, final_result)
                log.info('output of algorithm: {}'.format(output))
                main_profile_summary = _build_main_profile_summary(profiling, is_evaluation, optional_solutions, n_max_gen)
                finalize_profile_summary(
                    'generator_main_sse',
                    profiling,
                    enable_profiling,
                    extra_fields=main_profile_summary,
                )
                output = _attach_profile_debug(output, input_data, main_profile_summary, enable_profiling)
                result = {
                    'event': 'algorithm_complete',
                    'result': output,
                }
                print(json.dumps(result, cls=NpEncoder, ensure_ascii=False))
                sys.stdout.flush()
    except Exception as exc:
        trace = traceback.format_exc()
        log.error('generator main_sse failed: %s\n%s', exc, trace)
        result = {
            'event': 'error',
            'result': {
                'error': 'algorithm execution failed',
            },
        }
        print(json.dumps(result, cls=NpEncoder, ensure_ascii=False))
        sys.stdout.flush()


def main(input_data):
    """调用算法，输出方案（相位差）和评价指标"""
    try:
        input_data = json.loads(input_data)
        enable_profiling = is_profiling_enabled(input_data)
        profiling = OrderedDict()
        log.info('input of algorithm: {}'.format(input_data))
        is_evaluation = input_data.get('config', {}).get('onlyEvaluation', False)
        if is_evaluation:
            with profile_stage(profiling, 'current_plan_extract', enable_profiling):
                optional_solutions = _current_plan_as_optional_solutions(input_data)
            if not optional_solutions:
                raise ValueError('failed to extract current plan for evaluation')
        else:
            with profile_stage(profiling, 'optional_plan_generate', enable_profiling):
                optional_solutions = generate_optional_plan_parallel(input_data, num_processes=DEFAULT_NUM_PROCESS)
        n_max_gen = _resolve_iteration_num(input_data, is_evaluation)

        best_item = {}
        with profile_stage(profiling, 'ga_run', enable_profiling):
            for event in run_genetic_algorithm(input_data, optional_solutions, n_max_gen, None, DEFAULT_NUM_PROCESS):
                if event.get('event') == 'algorithm_complete':
                    best_item = event.get('result')

        with profile_stage(profiling, 'output_generate', enable_profiling):
            output = generate_output(input_data, best_item)
        log.info('output of algorithm: {}'.format(output))
        main_profile_summary = _build_main_profile_summary(profiling, is_evaluation, optional_solutions, n_max_gen)
        finalize_profile_summary(
            'generator_main',
            profiling,
            enable_profiling,
            extra_fields=main_profile_summary,
        )
        output = _attach_profile_debug(output, input_data, main_profile_summary, enable_profiling)
        return json.dumps(output, cls=NpEncoder, ensure_ascii=False)
    except Exception as exc:
        trace = traceback.format_exc()
        log.error('generator main failed: %s\n%s', exc, trace)
        return json.dumps({'error': 'algorithm execution failed'}, cls=NpEncoder, ensure_ascii=False)
