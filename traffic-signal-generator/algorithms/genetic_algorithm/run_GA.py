import json
import random
from collections import OrderedDict

import numpy as np
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.operators.crossover.expx import ExponentialCrossover

from algorithms.genetic_algorithm.GA import CustomInitialPopulation, CustomPerturbationMutation, MinimumOffsetSpacingRepair, OffsetSpacingRepairStats, ParallelGreenWaveProblem
from common.common_vars import DEFAULT_GA_EARLY_STOP_MIN_GEN, DEFAULT_GA_EARLY_STOP_MIN_IMPROVEMENT, DEFAULT_GA_EARLY_STOP_PATIENCE, DEFAULT_GA_POP_MAX, DEFAULT_GA_POP_MIN, DEFAULT_GA_POP_PER_VAR, DEFAULT_GA_RESET_MIN_OFFSET_DELTA_ON_IMPROVEMENT, DEFAULT_MIN_OFFSET_DELTA, DEFAULT_MODE, DEFAULT_SEED, FAST_MODE, OBJECTIVE, PERTURBATION_SCALE
from utils.logger import log
from utils.profiling import finalize_profile_summary, is_profiling_enabled, profile_stage
from utils.util import find_max_speed_best_iteration, find_min_ratio_best_iteration, find_min_traveltime_best_iteration, get_cycles


DYNAMIC_MIN_OFFSET_DELTA_MULTIPLIER = 2


def _resolve_ga_objective(input_data):
    """根据配置解析当前遗传算法使用的优化目标。"""
    objective_str = input_data.get('config', {}).get('objective')
    if objective_str:
        return OBJECTIVE(objective_str)
    return OBJECTIVE.WEIGHTED_SPEED


def _normalize_display_objective(objective, objective_value):
    """将内部最小化目标值转换为便于日志展示的业务指标。"""
    if objective_value is None:
        return None
    if objective == OBJECTIVE.WEIGHTED_SPEED:
        return -objective_value
    return objective_value


def _resolve_population_size(input_data, optional_solutions, var_number, num_processes):
    """根据候选解数量、变量维度和并行度动态估算 GA 种群规模。"""
    config = input_data.get('config', {})
    if config.get('onlyEvaluation', False):
        return 1

    optional_count = len(optional_solutions)
    process_floor = max(1, int(num_processes or 1))
    population_min = max(1, int(config.get('gaPopulationMin', DEFAULT_GA_POP_MIN)))
    population_max = max(population_min, int(config.get('gaPopulationMax', DEFAULT_GA_POP_MAX)))
    population_per_var = max(1, int(config.get('gaPopulationPerVar', DEFAULT_GA_POP_PER_VAR)))
    mode = config.get('mode', DEFAULT_MODE)

    if mode == FAST_MODE:
        target = max(optional_count, process_floor, max(4, population_per_var // 2) * var_number)
    else:
        target = max(optional_count * 2, process_floor, population_per_var * var_number)

    population_size = max(optional_count, min(population_max, max(population_min, target)))
    return max(1, population_size)


def _resolve_min_offset_delta(input_data, cycle):
    """读取并修正初始最小 offset 差值配置，避免超过周期长度。"""
    configured_value = int(input_data.get('config', {}).get('gaMinOffsetDelta', DEFAULT_MIN_OFFSET_DELTA))
    return max(0, min(configured_value, max(0, cycle // 2)))


def _resolve_early_stop_settings(input_data):
    """解析提前终止所需的最小代数、耐心值和最小提升阈值。"""
    config = input_data.get('config', {})
    if config.get('onlyEvaluation', False):
        return 0, 0, 0.0

    min_gen = max(0, int(config.get('gaEarlyStopMinGen', DEFAULT_GA_EARLY_STOP_MIN_GEN)))
    patience = max(0, int(config.get('gaEarlyStopPatience', DEFAULT_GA_EARLY_STOP_PATIENCE)))
    min_improvement = max(0.0, float(config.get('gaEarlyStopMinImprovement', DEFAULT_GA_EARLY_STOP_MIN_IMPROVEMENT)))
    return min_gen, patience, min_improvement


def _resolve_reset_min_offset_delta_on_improvement(input_data):
    """解析出现明显提升后是否恢复初始最小 offset 差值。"""
    value = input_data.get('config', {}).get(
        'gaResetMinOffsetDeltaOnImprovement',
        DEFAULT_GA_RESET_MIN_OFFSET_DELTA_ON_IMPROVEMENT,
    )
    if isinstance(value, bool):
        return value
    if value is None:
        return DEFAULT_GA_RESET_MIN_OFFSET_DELTA_ON_IMPROVEMENT
    return str(value).strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def _has_significant_improvement(best_raw_objective, current_raw_objective, min_improvement):
    """判断当前代是否相对历史最优产生了足够明显的提升。"""
    if current_raw_objective is None:
        return False
    if best_raw_objective is None:
        return True
    return (best_raw_objective - current_raw_objective) > min_improvement


def _resolve_dynamic_min_offset_delta(current_delta, cycle):
    """当连续代提升不足时，将最小 offset 差值放大 2 倍，并限制在半周期内。"""
    if current_delta <= 0:
        return 0
    return max(0, min(max(0, cycle // 2), current_delta * DYNAMIC_MIN_OFFSET_DELTA_MULTIPLIER))


def _apply_dynamic_min_offset_delta(spacing_repair, mutation_operator, new_delta):
    """将最新的最小 offset 差值同步到交叉修复器和变异算子。"""
    spacing_repair.update_delta(new_delta)
    mutation_operator.update_delta(new_delta)


def _build_generation_best_item(best_solution, objective):
    """提取当前代最优解，转换为回调和日志需要的统一结构。"""
    raw_solution = best_solution.X.tolist() if hasattr(best_solution, 'X') else None
    raw_objective = best_solution.F.tolist()[0] if hasattr(best_solution, 'F') else None
    display_objective = _normalize_display_objective(objective, raw_objective)

    if raw_solution is not None:
        raw_solution = [0] + raw_solution

    return {
        'solution': raw_solution,
        'objective': display_objective,
        'raw_objective': raw_objective,
    }


def run_genetic_algorithm(input_data, optional_solutions, n_max_gen=1, generation_callback=None, num_processes=None):
    """执行遗传算法搜索，并逐代产出最优候选与最终结果。"""
    enable_profiling = is_profiling_enabled(input_data)
    profiling = OrderedDict()

    random.seed(DEFAULT_SEED)
    np.random.seed(DEFAULT_SEED)

    with profile_stage(profiling, 'ga_prepare', enable_profiling):
        cycle = max(get_cycles(input_data))
        var_number = len(input_data['roadLength'])
        objective = _resolve_ga_objective(input_data)
        population_size = _resolve_population_size(input_data, optional_solutions, var_number, num_processes)
        min_offset_delta = _resolve_min_offset_delta(input_data, cycle)
        early_stop_min_gen, early_stop_patience, early_stop_min_improvement = _resolve_early_stop_settings(input_data)
        reset_min_offset_delta_on_improvement = _resolve_reset_min_offset_delta_on_improvement(input_data)

        problem = ParallelGreenWaveProblem(
            cycle=cycle,
            var_number=var_number,
            input_data=input_data,
            num_processes=num_processes,
        )
        log.info('初始迭代有效方案个数: %s', len(optional_solutions))
        log.info('每次迭代种群个数: %s', population_size)
        log.info('GA 初始最小 offset 差值约束: %s', min_offset_delta)
        log.info(
            'GA 动态最小 offset 差值策略: multiplier=%s trigger_min_improvement=%s upper_bound=%s reset_on_improvement=%s',
            DYNAMIC_MIN_OFFSET_DELTA_MULTIPLIER,
            early_stop_min_improvement,
            max(0, cycle // 2),
            reset_min_offset_delta_on_improvement,
        )

        repair_stats = OffsetSpacingRepairStats()

        spacing_repair = MinimumOffsetSpacingRepair(
            reference_population=optional_solutions,
            cycle=cycle,
            min_offset_delta=min_offset_delta,
            seed=DEFAULT_SEED,
            repair_stats=repair_stats,
        )
        mutation_operator = CustomPerturbationMutation(
            cycle,
            prob=0.8,
            perturbation_scale=PERTURBATION_SCALE,
            reference_population=optional_solutions,
            min_offset_delta=min_offset_delta,
            seed=DEFAULT_SEED,
            repair_stats=repair_stats,
        )
        algorithm = GA(
            pop_size=population_size,
            sampling=CustomInitialPopulation(
                optional_solutions,
                cycle,
                perturbation_scale=PERTURBATION_SCALE,
                min_offset_delta=min_offset_delta,
                seed=DEFAULT_SEED,
                repair_stats=repair_stats,
            ),
            crossover=ExponentialCrossover(prob=1, prob_exp=0.9, repair=spacing_repair),
            mutation=mutation_operator,
            eliminate_duplicates=True,
        )

    with profile_stage(profiling, 'ga_setup', enable_profiling):
        algorithm.setup(problem, seed=DEFAULT_SEED)

    best_raw_objective = None
    stagnation_generations = 0
    executed_generations = 0
    early_stop_generation = None
    dynamic_min_offset_delta = min_offset_delta
    dynamic_delta_change_count = 0
    dynamic_delta_reset_count = 0

    for gen in range(1, n_max_gen + 1):
        generation_profile = OrderedDict()
        with profile_stage(generation_profile, 'generation_total', enable_profiling, emit_log=False):
            algorithm.next()

        executed_generations = gen
        if algorithm.opt is not None and len(algorithm.opt) > 0:
            best_solution = algorithm.opt[0]
            best_item = _build_generation_best_item(best_solution, objective)
            current_raw_objective = best_item.get('raw_objective')

            if _has_significant_improvement(best_raw_objective, current_raw_objective, early_stop_min_improvement):
                best_raw_objective = current_raw_objective
                stagnation_generations = 0
                if (
                    reset_min_offset_delta_on_improvement
                    and dynamic_min_offset_delta != min_offset_delta
                ):
                    previous_delta = dynamic_min_offset_delta
                    dynamic_min_offset_delta = min_offset_delta
                    dynamic_delta_reset_count += 1
                    _apply_dynamic_min_offset_delta(spacing_repair, mutation_operator, dynamic_min_offset_delta)
                    log.info(
                        'dynamic min offset delta reset: generation=%s previous=%s current=%s',
                        gen,
                        previous_delta,
                        dynamic_min_offset_delta,
                    )
            elif current_raw_objective is not None:
                stagnation_generations += 1
                updated_delta = _resolve_dynamic_min_offset_delta(dynamic_min_offset_delta, cycle)
                if updated_delta != dynamic_min_offset_delta:
                    previous_delta = dynamic_min_offset_delta
                    dynamic_min_offset_delta = updated_delta
                    dynamic_delta_change_count += 1
                    _apply_dynamic_min_offset_delta(spacing_repair, mutation_operator, dynamic_min_offset_delta)
                    log.info(
                        'dynamic min offset delta enlarged: generation=%s stagnation_generations=%s previous=%s current=%s',
                        gen,
                        stagnation_generations,
                        previous_delta,
                        dynamic_min_offset_delta,
                    )

            if enable_profiling:
                generation_profile['generation'] = gen
                generation_profile['best_objective'] = best_item.get('objective')
                generation_profile['stagnation_generations'] = stagnation_generations
                generation_profile['min_offset_delta'] = dynamic_min_offset_delta
                log.info('profile summary name=ga_generation data=%s', json.dumps(generation_profile, ensure_ascii=False))

            log.info(
                'generation best solution: generation=%s solution=%s objective=%s min_offset_delta=%s',
                gen,
                best_item.get('solution'),
                best_item.get('objective'),
                dynamic_min_offset_delta,
            )

            if generation_callback:
                callback_result = generation_callback(
                    gen,
                    {
                        'solution': best_item.get('solution'),
                        'objective': best_item.get('objective'),
                    },
                )
                if callback_result is not None:
                    for event in callback_result:
                        yield event

        if 0 < early_stop_patience <= stagnation_generations and gen >= early_stop_min_gen:
            early_stop_generation = gen
            log.info(
                'early stop triggered: generation=%s stagnation_generations=%s min_improvement=%s min_offset_delta=%s',
                gen,
                stagnation_generations,
                early_stop_min_improvement,
                dynamic_min_offset_delta,
            )
            break

    with profile_stage(profiling, 'ga_result_collect', enable_profiling):
        algorithm.result()

    with profile_stage(profiling, 'ga_best_item_select', enable_profiling):
        if objective == OBJECTIVE.STOP_RATE:
            best_item = find_min_ratio_best_iteration(problem.waiting_log_info)
        elif objective == OBJECTIVE.TRAVEL_TIME:
            best_item = find_min_traveltime_best_iteration(problem.waiting_log_info)
        else:
            best_item = find_max_speed_best_iteration(problem.waiting_log_info)

    if best_item is None:
        failed_samples = problem.failed_evaluations[:5]
        raise ValueError(
            f'no valid evaluation result generated; total_failures={len(problem.failed_evaluations)}, '
            f'failed_samples={failed_samples}'
        )

    profile_summary = {
        **dict(profiling),
        'population_size': population_size,
        'n_max_gen': n_max_gen,
        'executed_generations': executed_generations,
        'early_stop_generation': early_stop_generation,
        'early_stop_patience': early_stop_patience,
        'early_stop_min_gen': early_stop_min_gen,
        'early_stop_min_improvement': early_stop_min_improvement,
        'initial_min_offset_delta': min_offset_delta,
        'min_offset_delta': dynamic_min_offset_delta,
        'dynamic_min_offset_delta_multiplier': DYNAMIC_MIN_OFFSET_DELTA_MULTIPLIER,
        'dynamic_min_offset_delta_change_count': dynamic_delta_change_count,
        'dynamic_min_offset_delta_reset_count': dynamic_delta_reset_count,
        'reset_min_offset_delta_on_improvement': reset_min_offset_delta_on_improvement,
        'optional_solution_count': len(optional_solutions),
        'failed_evaluations': len(problem.failed_evaluations),
        **repair_stats.to_profile_summary(),
        **(problem.get_profile_summary() or {}),
    }
    finalize_profile_summary(
        'genetic_algorithm',
        profiling,
        enable_profiling,
        extra_fields=profile_summary,
    )
    if enable_profiling:
        input_data.setdefault('_profile_debug', {})['genetic_algorithm'] = profile_summary

    yield {
        'event': 'algorithm_complete',
        'result': best_item,
    }
