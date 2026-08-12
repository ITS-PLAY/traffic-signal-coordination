import json
import itertools
import multiprocessing
import os
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, as_completed


from algorithms.bandwidth_algorithm.flex_band_optimization import run_flex_band
from utils.profiling import is_profiling_enabled, profile_stage, finalize_profile_summary
from utils.util import get_green_ratios, timer, get_cycles, update_plan_info
from utils.logger import log
from common.common_vars import DEFAULT_TIMEOUT, DEFAULT_MODE, FAST_MODE, DEFAULT_SEGMENT_CROSS_COUNT, DEFAULT_SEGMENT_OVERLAP_CROSS_COUNT


SERIAL_EXECUTION = os.environ.get('SERIAL_EXECUTION', '0') == '1'


def _build_bandwidth_profile_summary(profiling, tasks, num_processes, optional_solutions):
    """汇总带宽候选生成阶段的 profiling 结果与任务规模信息。"""
    return {
        **dict(profiling),
        'task_count': len(tasks),
        'num_processes': num_processes,
        'optional_solution_count': len(optional_solutions),
        'serial_execution': SERIAL_EXECUTION,
    }


def _resolve_weight_candidates(input_data):
    """根据正/反向优先和运行模式选择 FlexBand 权重候选集合。"""
    outbound = input_data.get('config', {}).get('outbound', True)
    inbound = input_data.get('config', {}).get('inbound', True)
    mode = input_data.get('config', {}).get('mode', DEFAULT_MODE)
    if outbound and inbound:
        return [1] if mode == FAST_MODE else [1, 5, 0.2]
    if outbound:
        return [5] if mode == FAST_MODE else [2, 5]
    return [0.2] if mode == FAST_MODE else [0.2, 0.5]


def _build_band_context(input_data):
    """抽取绿信比、统一周期和多周期映射，构造带宽算法共享上下文。"""
    in_green, out_green = get_green_ratios(input_data)
    cycles = get_cycles(input_data)
    common_cycle = max(cycles)
    multi_cycles = [common_cycle // cycle for cycle in cycles]
    for index, cross_id in enumerate(input_data.get('crossList', [])):
        input_data['planInfo'][cross_id] = update_plan_info(input_data['planInfo'][cross_id], common_cycle, multi_cycles[index])
    return {
        'common_cycle': common_cycle,
        'green': [out_green, in_green],
        'road_length': input_data['roadLength'],
        'road_speed': input_data['roadSpeed'],
        'multi_cycles': multi_cycles,
        'road_nums': len(input_data['roadLength']),
        'cross_nums': len(input_data.get('crossList', [])),
    }


def _build_band_algorithm_input(context, cross_start=0, cross_end=None):
    """按指定路口区间裁剪共享上下文，生成一次 FlexBand 求解输入。"""
    if cross_end is None:
        cross_end = context['cross_nums'] - 1

    road_start = cross_start
    road_end = cross_end - 1
    road_count = max(0, cross_end - cross_start)
    return {
        'cl': context['common_cycle'],
        'green': [
            context['green'][0][cross_start:cross_end + 1],
            context['green'][1][cross_start:cross_end + 1],
        ],
        'dist': context['road_length'][road_start:road_end + 1],
        'speed': [
            context['road_speed'][0][road_start:road_end + 1],
            context['road_speed'][1][road_start:road_end + 1],
        ],
        'optimizationObjective': {
            'bandWeights': [[1] * road_count, [1] * road_count],
            'multiCycle': context['multi_cycles'][cross_start:cross_end + 1],
        }
    }


def _build_tasks(experts, band_algorithm_input, road_nums, weights):
    """展开专家、权重和贯通约束组合，生成待执行的求解任务列表。"""
    tasks = []
    band_weights = list(itertools.product(weights, repeat=road_nums))
    min_bounds = [0, 1]
    for iter_index, weight in enumerate(band_weights):
        weight_list = list(weight)
        for min_bound_thru in min_bounds:
            for expert in experts:
                tasks.append((
                    expert,
                    band_algorithm_input,
                    weight_list,
                    min_bound_thru,
                    iter_index * len(min_bounds) * len(experts) +
                    min_bounds.index(min_bound_thru) * len(experts) +
                    experts.index(expert)
                ))
    return tasks


def _execute_tasks(tasks, num_processes):
    """串行或并行执行候选任务，并收集每个任务的求解结果。"""
    results = []
    if SERIAL_EXECUTION:
        for task in tasks:
            try:
                results.append(run_expert_algorithm(task))
            except Exception as e:
                expert_name, weight, min_bound_thru = task[0].__name__, task[2], task[3]
                log.info('task failed: expert=%s, weight=%s, min_bound_thru=%s, error=%s', expert_name, weight, min_bound_thru, e)
    else:
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            future_to_task = {executor.submit(run_expert_algorithm, task): task for task in tasks}
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    results.append(future.result(timeout=DEFAULT_TIMEOUT))
                except Exception as e:
                    expert_name, weight, min_bound_thru = task[0].__name__, task[2], task[3]
                    log.info('task failed: expert=%s, weight=%s, min_bound_thru=%s, error=%s', expert_name, weight, min_bound_thru, e)
    return results


def _rank_candidates(results):
    """按带宽得分对候选解排序、去重。"""
    ranked = []
    seen = set()
    for result in results:
        relative_offset = result.get('relative_offset')
        if relative_offset is None:
            continue
        candidate_key = tuple(relative_offset)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        ranked.append({
            'relative_offset': [int(value) for value in relative_offset],
            'score': result.get('score', 0),
        })

    ranked.sort(key=lambda item: item['score'], reverse=True)
    return ranked


def _resolve_segment_cross_count(config, cross_nums):
    """优先使用外部 segmentCrossCount；未传入时按总路口数一半向上取整，并受默认最小值保护。"""
    if 'segmentCrossCount' in config and config.get('segmentCrossCount') is not None:
        return max(DEFAULT_SEGMENT_CROSS_COUNT, int(config.get('segmentCrossCount')))
    return max(DEFAULT_SEGMENT_CROSS_COUNT, (int(cross_nums) + 1) // 2)


def _resolve_segment_overlap_cross_count(config, segment_cross_count):
    """解析重叠路口数配置，只读取 segmentOverlapCrossCount，并至少保留 1 个边界路口。"""
    configured = int(config.get('segmentOverlapCrossCount', DEFAULT_SEGMENT_OVERLAP_CROSS_COUNT))
    normalized = max(1, configured)
    return min(max(1, segment_cross_count - 1), normalized)


def _build_segment_ranges(cross_nums, segment_cross_count, overlap_cross_count=1):
    """按分段路口数和重叠路口数切分走廊，返回每段覆盖的路口区间。"""
    ranges = []
    step = max(1, segment_cross_count - overlap_cross_count)
    start = 0
    while start < cross_nums:
        end = min(cross_nums - 1, start + segment_cross_count - 1)
        ranges.append((start, end))
        if end == cross_nums - 1:
            break
        start += step
    return ranges


def _merge_segment_candidate(beam, segment, candidate):
    """按重叠路口数覆盖上一段尾部 offset，再追加当前段剩余 offset。"""
    candidate_offsets = [int(value) for value in candidate['relative_offset']]
    if not beam['solution']:
        return {
            'solution': list(candidate_offsets),
            'score_delta': candidate['score'],
            'cross_end': segment['cross_end'],
        }

    shared_cross_count = max(0, beam['cross_end'] - segment['cross_start'] + 1)
    shared_offset_count = max(0, shared_cross_count - 1)
    if shared_offset_count > len(beam['solution']) or shared_offset_count > len(candidate_offsets):
        log.debug(
            'segment merge failed: shared_offset_count=%s beam_len=%s candidate_len=%s beam_cross_end=%s segment_start=%s segment_end=%s',
            shared_offset_count,
            len(beam['solution']),
            len(candidate_offsets),
            beam['cross_end'],
            segment['cross_start'],
            segment['cross_end'],
        )
        return None

    merged_solution = list(beam['solution'])
    if shared_offset_count > 0:
        merged_solution[-shared_offset_count:] = candidate_offsets[:shared_offset_count]
        merged_solution.extend(candidate_offsets[shared_offset_count:])
    else:
        merged_solution.extend(candidate_offsets)

    return {
        'solution': merged_solution,
        'score_delta': candidate['score'],
        'cross_end': segment['cross_end'],
    }


def _build_segment_candidate_beam(segment_candidates, selected_candidates):
    """按已选的每段候选顺序拼接出一个完整 seed。"""
    beam = {'solution': [], 'score': 0, 'cross_end': -1}
    for segment, candidate in zip(segment_candidates, selected_candidates):
        merged = _merge_segment_candidate(
            beam=beam,
            segment=segment,
            candidate=candidate,
        )
        if merged is None:
            return None
        beam = {
            'solution': merged['solution'],
            'score': beam['score'] + merged['score_delta'],
            'cross_end': merged['cross_end'],
        }
    return beam


def _combine_segment_candidates(segment_candidates):
    """线性拼接分段候选：先取各段最优，再逐段替换候选，避免指数组合。"""
    if not segment_candidates:
        return []

    base_candidates = [segment['candidates'][0] for segment in segment_candidates]
    beams = []

    base_beam = _build_segment_candidate_beam(segment_candidates, base_candidates)
    if base_beam is not None:
        beams.append(base_beam)

    for segment_index, segment in enumerate(segment_candidates):
        for candidate in segment['candidates'][1:]:
            selected_candidates = list(base_candidates)
            selected_candidates[segment_index] = candidate
            beam = _build_segment_candidate_beam(segment_candidates, selected_candidates)
            if beam is not None:
                beams.append(beam)

    deduplicated = []
    seen = set()
    for beam in sorted(beams, key=lambda item: item['score'], reverse=True):
        solution_key = tuple(beam['solution'])
        if solution_key in seen:
            continue
        seen.add(solution_key)
        deduplicated.append(beam)

    return [beam['solution'] for beam in deduplicated]


def _generate_segmented_optional_solutions(input_data, context, experts, weights, num_processes):
    """执行按路口重叠约束的分段优化，用线性拼接生成全局 seed。"""
    config = input_data.get('config', {})
    segment_cross_count = _resolve_segment_cross_count(config, context['cross_nums'])
    overlap_cross_count = _resolve_segment_overlap_cross_count(config, segment_cross_count)

    if context['cross_nums'] <= segment_cross_count:
        return [], []

    segment_ranges = _build_segment_ranges(context['cross_nums'], segment_cross_count, overlap_cross_count)
    segment_candidates = []
    all_tasks = []

    for cross_start, cross_end in segment_ranges:
        segment_input = _build_band_algorithm_input(context, cross_start, cross_end)
        segment_tasks = _build_tasks(experts, segment_input, cross_end - cross_start, weights)
        all_tasks.extend(segment_tasks)
        segment_results = _execute_tasks(segment_tasks, num_processes)
        for result in segment_results:
            relative_offset = result.get('relative_offset')
            if relative_offset is None:
                continue
            log.info('segment flexband offset: cross_start=%s cross_end=%s offset=%s', cross_start, cross_end, relative_offset)
        ranked_candidates = _rank_candidates(segment_results)
        if not ranked_candidates:
            log.info(
                'segment seed generation failed, fallback to full corridor: cross_start=%s cross_end=%s finished_segment_count=%s',
                cross_start,
                cross_end,
                len(segment_candidates),
            )
            return [], all_tasks
        segment_candidates.append({
            'cross_start': cross_start,
            'cross_end': cross_end,
            'candidates': ranked_candidates,
        })

    combined = _combine_segment_candidates(segment_candidates)
    log.info(
        'segmented optional_solutions combined: strategy=linear_anchor segment_count=%s segment_candidate_count=%s combined_count=%s',
        len(segment_candidates),
        sum(len(segment['candidates']) for segment in segment_candidates),
        len(combined),
    )
    return combined, all_tasks


@timer
def generate_optional_plan_parallel(input_data, num_processes=None):
    """生成 GA 初始候选解，优先走带重叠约束的分段 seed，失败时回退到整段 FlexBand。"""
    enable_profiling = is_profiling_enabled(input_data)
    profiling = OrderedDict()

    if num_processes is None:
        num_processes = max(1, multiprocessing.cpu_count() // 2)

    with profile_stage(profiling, 'band_prepare', enable_profiling):
        experts = [run_flex_band]
        context = _build_band_context(input_data)
        weights = _resolve_weight_candidates(input_data)
        road_nums = context['road_nums']
        band_algorithm_input = _build_band_algorithm_input(context)
        tasks = _build_tasks(experts, band_algorithm_input, road_nums, weights)

    config = input_data.get('config', {})
    # 未显式传入 useSegmentedSeed 时，默认开启分段种子候选生成
    use_segmented_seed = config.get('useSegmentedSeed')
    if use_segmented_seed is None:
        use_segmented_seed = True

    optional_solutions = []
    segmented_optional_solutions = []
    segmented_tasks = []

    with profile_stage(profiling, 'band_task_execute', enable_profiling):
        if use_segmented_seed:
            segmented_optional_solutions, segmented_tasks = _generate_segmented_optional_solutions(
                input_data,
                context,
                experts,
                weights,
                num_processes,
            )
            optional_solutions.extend(segmented_optional_solutions)

        if not optional_solutions:
            log.info('开始并行处理 %s 个任务，使用 %s 个进程...', len(tasks), num_processes)
            for result in _execute_tasks(tasks, num_processes):
                relative_offset = result.get('relative_offset')
                if relative_offset is not None and relative_offset not in optional_solutions:
                    optional_solutions.append(relative_offset)

    if segmented_optional_solutions:
        tasks = segmented_tasks

    profile_summary = _build_bandwidth_profile_summary(profiling, tasks, num_processes, optional_solutions)
    finalize_profile_summary(
        'bandwidth_optional_plan',
        profiling,
        enable_profiling,
        extra_fields=profile_summary,
    )
    if enable_profiling:
        input_data.setdefault('_profile_debug', {})['bandwidth_optional_plan'] = profile_summary
    return optional_solutions


def run_expert_algorithm(args):
    """执行单个专家任务并返回 offset 候选及其带宽得分。"""
    expert_main, band_algorithm_input, weight, min_bound_thru, iter_index = args
    try:
        # 复制输入数据以避免修改共享数据
        input_copy = json.loads(json.dumps(band_algorithm_input))

        # 设置权重
        input_copy['optimizationObjective']['bandWeights'][0] = weight
        input_copy['optimizationObjective']['minInboundThru'] = min_bound_thru
        input_copy['optimizationObjective']['minOutboundThru'] = min_bound_thru

        # 运行专家算法
        result = expert_main(input_copy)
        relative_offset = result.get('offset', None)
        score = sum(result.get('b0', [])) + sum(result.get('b1', []))
        return {
            'relative_offset': relative_offset,
            'weight': weight,
            'min_bound_thru': min_bound_thru,
            'expert': expert_main.__name__,
            'iter_index': iter_index,
            'score': score,
        }

    except Exception as e:
        log.info(f"Error running expert algorithm {expert_main.__name__} with weight {weight}: {e}")
        return {
            'relative_offset': None,
            'weight': weight,
            'min_bound_thru': min_bound_thru,
            'expert': expert_main.__name__,
            'iter_index': iter_index,
            'error': str(e)
        }
