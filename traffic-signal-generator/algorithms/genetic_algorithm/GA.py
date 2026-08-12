import json
import multiprocessing
import os
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from time import perf_counter
import numpy as np

from pymoo.core.problem import Problem
from pymoo.core.mutation import Mutation
from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling

from utils.logger import log
from utils.profiling import is_profiling_enabled, profile_stage, new_profile_store, finalize_profile_summary
from utils.util import replace_offset_value, timer
from common.common_vars import DEFAULT_MIN_OFFSET_DELTA, DEFAULT_TIMEOUT, PERTURBATION_SCALE, EVALUATOR_URL, EVALUATOR_URL_PATH, EVALUATOR_FUNC_NAME, OBJECTIVE
from common.http_client import HttpServiceClient, EVALUATOR_MAX_INFLIGHT, GA_EVALUATION_TIMEOUT_SECONDS


SERIAL_EXECUTION = os.environ.get('SERIAL_EXECUTION', '0') == '1'


class OffsetSpacingRepairStats:
    """Collect repair attempt and failure counts for offset spacing constraints."""

    def __init__(self):
        self.total_attempts = 0
        self.total_failures = 0
        self.stage_attempts = {}
        self.stage_failures = {}

    def record_attempt(self, stage):
        stage_name = stage or 'unknown'
        self.total_attempts += 1
        self.stage_attempts[stage_name] = self.stage_attempts.get(stage_name, 0) + 1

    def record_failure(self, stage):
        stage_name = stage or 'unknown'
        self.total_failures += 1
        self.stage_failures[stage_name] = self.stage_failures.get(stage_name, 0) + 1

    def to_profile_summary(self):
        summary = OrderedDict()
        summary['offset_spacing_repair_attempts'] = self.total_attempts
        summary['offset_spacing_repair_failures'] = self.total_failures
        summary['offset_spacing_repair_failure_rate'] = round(self.total_failures / self.total_attempts, 4) if self.total_attempts else 0.0

        stage_names = sorted(set(self.stage_attempts) | set(self.stage_failures))
        for stage_name in stage_names:
            summary[f'offset_spacing_repair_attempts_{stage_name}'] = self.stage_attempts.get(stage_name, 0)
            summary[f'offset_spacing_repair_failures_{stage_name}'] = self.stage_failures.get(stage_name, 0)
        return summary


def _normalize_reference_population(reference_population):
    """将参考方案集合统一转换为二维整数数组。"""
    if reference_population is None:
        return np.empty((0, 0), dtype=int)

    population = np.asarray(reference_population, dtype=int)
    if population.size == 0:
        return np.empty((0, 0), dtype=int)
    if population.ndim == 1:
        population = population.reshape(1, -1)
    return population


def _circular_offset_distance(left, right, cycle):
    """计算两个 offset 在周期空间中的最短环形距离。"""
    diff = abs(int(left) - int(right)) % cycle
    return min(diff, cycle - diff)


def _is_offset_spacing_valid(candidate, reference_population, cycle, min_offset_delta):
    """判断候选解是否与已有方案在每个路口都保持最小 offset 差值。"""
    if min_offset_delta <= 0 or reference_population.size == 0:
        return True

    for reference in reference_population:
        for index, value in enumerate(candidate):
            if _circular_offset_distance(value, reference[index], cycle) < min_offset_delta:
                return False
    return True


def _repair_candidate_offset_spacing(candidate, reference_population, cycle, min_offset_delta, rng, max_attempts=None, repair_stats=None, repair_stage=None):
    """通过有限次局部扰动和重采样修复候选解的最小 offset 差值约束。"""
    repaired = np.rint(np.asarray(candidate)).astype(int) % cycle
    if min_offset_delta <= 0 or reference_population.size == 0:
        return repaired
    if _is_offset_spacing_valid(repaired, reference_population, cycle, min_offset_delta):
        return repaired

    if repair_stats is not None:
        repair_stats.record_attempt(repair_stage)

    max_attempts = max_attempts or max(8, cycle)
    for attempt in range(max_attempts):
        step_scale = min(max(1, cycle - 1), min_offset_delta + attempt)
        jitter = rng.integers(-step_scale, step_scale + 1, size=len(repaired))
        jitter = np.where(
            np.abs(jitter) < min_offset_delta,
            np.where(jitter < 0, -min_offset_delta, min_offset_delta),
            jitter,
        )
        trial = (repaired + jitter) % cycle
        if _is_offset_spacing_valid(trial, reference_population, cycle, min_offset_delta):
            return trial.astype(int)

    for _ in range(max_attempts):
        trial = rng.integers(0, cycle, size=len(repaired))
        if _is_offset_spacing_valid(trial, reference_population, cycle, min_offset_delta):
            return trial.astype(int)

    if repair_stats is not None:
        repair_stats.record_failure(repair_stage)

    log.debug(
        'offset spacing repair failed: stage=%s cycle=%s min_offset_delta=%s max_attempts=%s candidate=%s reference_count=%s',
        repair_stage or 'unknown',
        cycle,
        min_offset_delta,
        max_attempts,
        repaired.tolist(),
        len(reference_population),
    )
    return repaired


def evaluate_single_solution(args):
    """评估单个解"""
    iter_index, relative_offset, base_input_data, cycle = args
    enable_profiling = is_profiling_enabled(base_input_data)
    profiling = new_profile_store()
    try:
        # 复制基础配置以避免修改共享数据
        with profile_stage(profiling, 'solution_prepare', enable_profiling, emit_log=False):
            input_data = json.loads(json.dumps(base_input_data))
            relative_offset = np.insert(relative_offset, 0, 0)

        # log.info('evaluate_single_solution: iter_index=%s relative_offset=%s', iter_index, relative_offset)

        # 设置相位差
        with profile_stage(profiling, 'solution_apply_offset', enable_profiling, emit_log=False):
            for index, cross_id in enumerate(input_data['crossList']):
                input_data['planInfo'][cross_id] = replace_offset_value(input_data['planInfo'][cross_id], relative_offset[index])

        # 在每个进程中调用TrafficSignalEvaluator提供的API,发送input_data,返回每次的评估结果
        with profile_stage(profiling, 'evaluator_request', enable_profiling, emit_log=False):
            with HttpServiceClient(EVALUATOR_URL) as client:
                request_data = {"in": input_data, "func": EVALUATOR_FUNC_NAME}
                simulation_result = client.post(EVALUATOR_URL_PATH, data=request_data)

        if not isinstance(simulation_result, dict):
            raise ValueError(f'invalid evaluator response type: {type(simulation_result).__name__}')
        if simulation_result.get('error'):
            raise ValueError(
                f"evaluator request failed: error={simulation_result.get('error')}, "
                f"status_code={simulation_result.get('status_code')}, "
                f"exception={simulation_result.get('exception')}, "
                f"response_text={simulation_result.get('response_text', '')}"
            )
        if 'out' not in simulation_result:
            raise ValueError(f'evaluator response missing out: {simulation_result}')

        simulation_metrics = simulation_result['out']

        # 调用sumo生成停车率指标
        with profile_stage(profiling, 'solution_extract_metrics', enable_profiling, emit_log=False):
            if simulation_metrics:
                avg_waiting_ratio = simulation_metrics['avg_waiting_ratio']
                waiting_time = simulation_metrics['waiting_time']
                avg_speed = simulation_metrics['avg_speed']
                avg_queue_length = simulation_metrics['avg_queue_length']
                avg_travel_time = simulation_metrics['avg_travel_time']
            else:
                avg_waiting_ratio, waiting_time, avg_speed, avg_queue_length, avg_travel_time = 0, 0, 0, 0, 0
                simulation_metrics = {}

            objective_str = input_data.get("config", {}).get('objective', None)
            if objective_str:
                objective = OBJECTIVE(objective_str)
            else:
                objective = OBJECTIVE.WEIGHTED_SPEED

            if objective == OBJECTIVE.STOP_RATE:
                fitness = avg_waiting_ratio
            elif objective == OBJECTIVE.TRAVEL_TIME:
                fitness = avg_travel_time
            else:
                fitness = -avg_speed
        # 返回结果
        result = {
            'fitness': fitness,
            'metrics': {'avg_speed': avg_speed, 'waiting_time': waiting_time, 'avg_queue_length': avg_queue_length,
                        'avg_waiting_ratio': avg_waiting_ratio, 'avg_travel_time': avg_travel_time,
                        'plan': relative_offset.tolist()},
            'direction_metrics':{"outbound": simulation_metrics.get('outbound', {'avg_speed': avg_speed, 'avg_waiting_ratio': avg_waiting_ratio}),
                                 "inbound": simulation_metrics.get('inbound', {'avg_speed': avg_speed, 'avg_waiting_ratio': avg_waiting_ratio})},
            'iter_index': iter_index
        }
        if enable_profiling:
            result['profiling'] = profiling
        return result

    except Exception as e:
        log.error(f"Error evaluating solution {iter_index}: {e}", exc_info=True)
        # 返回一个较差的结果
        result = {'fitness': float('inf'), 'metrics': {}, 'direction_metrics': {"outbound":None, "inbound": None},
                  'iter_index': iter_index, 'error': str(e)}
        if enable_profiling:
            result['profiling'] = profiling
        return result


class ParallelGreenWaveProblem(Problem):
    def __init__(self, cycle, var_number, input_data, num_processes=None):
        super().__init__(n_var=var_number, n_obj=1, n_ieq_constr=0, xl=0, xu=cycle - 1, vtype=int)
        self.cycle = cycle
        self.iter = 0
        self.waiting_log_info = []
        self.failed_evaluations = []
        self.enable_profiling = is_profiling_enabled(input_data)
        self.profile_summary = {
            'batch_count': 0,
            'solution_count': 0,
            'success_count': 0,
            'failed_count': 0,
            'batch_eval_total_ms': 0.0,
            'batch_eval_total_max_ms': 0.0,
            'evaluator_request_ms': 0.0,
            'evaluator_request_max_ms': 0.0,
            'solution_prepare_ms': 0.0,
            'solution_prepare_max_ms': 0.0,
            'solution_apply_offset_ms': 0.0,
            'solution_apply_offset_max_ms': 0.0,
            'solution_extract_metrics_ms': 0.0,
            'solution_extract_metrics_max_ms': 0.0,
        }

        # 并行处理设置
        self.num_processes = num_processes or max(1, multiprocessing.cpu_count() // 2)
        if EVALUATOR_MAX_INFLIGHT > 0:
            self.num_processes = min(self.num_processes, EVALUATOR_MAX_INFLIGHT)
        self.base_input_data = input_data

    def _evaluate(self, x, out, *args, **kwargs):
        batch_profile = OrderedDict()
        batch_start = perf_counter()
        out["F"] = np.zeros(len(x))

        # 参数列表，x中存储了pop_size个相位差组合，需要遍历每个相位差组合
        evaluation_args = [
            (i, relative_offset, self.base_input_data, self.cycle)
            for i, relative_offset in enumerate(x)
        ]

        results = []
        if SERIAL_EXECUTION:
            for index, arg in enumerate(evaluation_args):
                try:
                    result = evaluate_single_solution(arg)
                    results.append(result)
                except Exception as e:
                    log.info(f"Evaluation failed: {e}")
                    results.append({
                        'fitness': float('inf'),
                        'iter_index': index,
                        'error': f'serial_evaluation_failed: {e}'
                    })
        else:
            with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
                future_to_iter_index = {
                    executor.submit(evaluate_single_solution, arg): arg[0]
                    for arg in evaluation_args
                }

                for future, iter_index in future_to_iter_index.items():
                    try:
                        result = future.result(timeout=GA_EVALUATION_TIMEOUT_SECONDS)
                        results.append(result)
                    except Exception as e:
                        log.info(f"Evaluation failed: {e}")
                        results.append({
                            'fitness': float('inf'),
                            'iter_index': iter_index,
                            'error': f'future_result_failed: {e}'
                        })

        # 按原始顺序排序结果
        results.sort(key=lambda x: x['iter_index'])

        batch_elapsed_ms = round((perf_counter() - batch_start) * 1000, 3)

        # 填充输出数组和日志
        fitness_values = []
        evaluator_request_values = []
        solution_prepare_values = []
        solution_apply_offset_values = []
        solution_extract_metrics_values = []
        for result in results:
            fitness_values.append(result['fitness'])
            result_profile = result.get('profiling', {})
            if result_profile:
                if 'evaluator_request' in result_profile:
                    evaluator_request_values.append(result_profile['evaluator_request'])
                if 'solution_prepare' in result_profile:
                    solution_prepare_values.append(result_profile['solution_prepare'])
                if 'solution_apply_offset' in result_profile:
                    solution_apply_offset_values.append(result_profile['solution_apply_offset'])
                if 'solution_extract_metrics' in result_profile:
                    solution_extract_metrics_values.append(result_profile['solution_extract_metrics'])

            # 记录日志信息
            if 'metrics' in result and 'error' not in result:
                self.waiting_log_info.append({
                    'iter': self.iter,
                    'avg_waiting_ratio': result['metrics'].get('avg_waiting_ratio', 0),
                    'avg_speed': result['metrics'].get('avg_speed', 0),
                    'waiting_time': result['metrics'].get('waiting_time', 0),
                    'avg_queue_length': result['metrics'].get('avg_queue_length', 0),
                    'avg_travel_time': result['metrics'].get('avg_travel_time', 0),
                    'direction_metrics': result.get('direction_metrics', {"outbound":None, "inbound": None}),
                    'plan': result['metrics'].get('plan', '')
                })
                self.iter += 1
            elif result.get('error'):
                self.failed_evaluations.append({
                    'iter_index': result.get('iter_index'),
                    'error': result.get('error'),
                })

        out["F"] = np.array(fitness_values)

        if self.enable_profiling:
            solution_count = len(results)
            success_count = sum(1 for result in results if 'error' not in result)
            failed_count = solution_count - success_count
            self.profile_summary['batch_count'] += 1
            self.profile_summary['solution_count'] += solution_count
            self.profile_summary['success_count'] += success_count
            self.profile_summary['failed_count'] += failed_count
            self.profile_summary['batch_eval_total_ms'] += batch_elapsed_ms
            self.profile_summary['batch_eval_total_max_ms'] = max(self.profile_summary['batch_eval_total_max_ms'], batch_elapsed_ms)

            stage_values_map = {
                'evaluator_request': evaluator_request_values,
                'solution_prepare': solution_prepare_values,
                'solution_apply_offset': solution_apply_offset_values,
                'solution_extract_metrics': solution_extract_metrics_values,
            }
            for stage_name, values in stage_values_map.items():
                if not values:
                    continue
                total_key = f'{stage_name}_ms'
                max_key = f'{stage_name}_max_ms'
                self.profile_summary[total_key] += sum(values)
                self.profile_summary[max_key] = max(self.profile_summary[max_key], max(values))
                batch_profile[f'{stage_name}_avg_ms'] = round(sum(values) / len(values), 3)
                batch_profile[f'{stage_name}_max_ms'] = round(max(values), 3)

            batch_profile['batch_eval_total_ms'] = batch_elapsed_ms
            batch_profile['population_size'] = solution_count
            batch_profile['success_count'] = success_count
            batch_profile['failed_count'] = failed_count
            log.info('profile summary name=ga_evaluate_batch data=%s', json.dumps(batch_profile, ensure_ascii=False))

    def get_profile_summary(self):
        if not self.enable_profiling:
            return None

        solution_count = max(1, self.profile_summary['solution_count'])
        batch_count = max(1, self.profile_summary['batch_count'])
        return {
            'ga_eval_batch_count': self.profile_summary['batch_count'],
            'ga_eval_solution_count': self.profile_summary['solution_count'],
            'ga_eval_success_count': self.profile_summary['success_count'],
            'ga_eval_failed_count': self.profile_summary['failed_count'],
            'ga_eval_batch_total_avg_ms': round(self.profile_summary['batch_eval_total_ms'] / batch_count, 3),
            'ga_eval_batch_total_max_ms': round(self.profile_summary['batch_eval_total_max_ms'], 3),
            'ga_eval_evaluator_request_avg_ms': round(self.profile_summary['evaluator_request_ms'] / solution_count, 3),
            'ga_eval_evaluator_request_max_ms': round(self.profile_summary['evaluator_request_max_ms'], 3),
            'ga_eval_solution_prepare_avg_ms': round(self.profile_summary['solution_prepare_ms'] / solution_count, 3),
            'ga_eval_solution_apply_offset_avg_ms': round(self.profile_summary['solution_apply_offset_ms'] / solution_count, 3),
            'ga_eval_solution_extract_metrics_avg_ms': round(self.profile_summary['solution_extract_metrics_ms'] / solution_count, 3),
        }


class CustomInitialPopulation(Sampling):
    """使用候选解作为种子，并为补充样本生成满足最小 offset 间隔的新个体。"""

    def __init__(self, base_population, cycle, perturbation_scale=PERTURBATION_SCALE, min_offset_delta=DEFAULT_MIN_OFFSET_DELTA, seed=None, repair_stats=None):
        super().__init__()
        self.reference_population = _normalize_reference_population(base_population)
        self.base_population = self.reference_population.copy()
        self.cycle = cycle
        self.perturbation_scale = perturbation_scale
        self.min_offset_delta = max(0, int(min_offset_delta))
        self.rng = np.random.default_rng(seed)
        self.repair_stats = repair_stats

    def _do(self, problem, n_samples, **kwargs):
        n_base = len(self.base_population)
        n_var = problem.n_var

        if n_base == 0:
            population = self.rng.integers(0, self.cycle, size=(n_samples, n_var))
            return self._repair_population(population, enforce_spacing=False)

        population = self.base_population.copy()
        if n_samples > n_base:
            additional_needed = n_samples - n_base
            indices = self.rng.choice(n_base, additional_needed, replace=True)
            additional_individuals = []

            for idx in indices:
                base_individual = self.base_population[idx]
                perturbation = self.rng.integers(
                    -self.perturbation_scale,
                    self.perturbation_scale + 1,
                    size=len(base_individual),
                )
                new_individual = base_individual + perturbation
                new_individual = _repair_candidate_offset_spacing(
                    new_individual,
                    self.reference_population,
                    self.cycle,
                    self.min_offset_delta,
                    self.rng,
                    repair_stats=self.repair_stats,
                    repair_stage='sampling',
                )
                additional_individuals.append(new_individual)

            population = np.vstack([population, additional_individuals])

        population = population[:n_samples]
        population = self._repair_population(population, enforce_spacing=False)
        return population

    def _repair_population(self, population, enforce_spacing):
        """修复边界、取整，并按需补齐最小 offset 差值约束。"""
        repaired_population = np.rint(np.asarray(population)).astype(int) % self.cycle
        if not enforce_spacing:
            return repaired_population

        for index in range(len(repaired_population)):
            repaired_population[index] = _repair_candidate_offset_spacing(
                repaired_population[index],
                self.reference_population,
                self.cycle,
                self.min_offset_delta,
                self.rng,
            )
        return repaired_population


class MinimumOffsetSpacingRepair(Repair):
    """在交叉后的候选上补齐最小 offset 差值约束。"""

    def __init__(self, reference_population, cycle, min_offset_delta=DEFAULT_MIN_OFFSET_DELTA, seed=None, repair_stats=None):
        super().__init__()
        self.reference_population = _normalize_reference_population(reference_population)
        self.cycle = cycle
        self.min_offset_delta = max(0, int(min_offset_delta))
        self.rng = np.random.default_rng(seed)
        self.repair_stats = repair_stats

    def update_delta(self, new_delta):
        """Update the minimum offset spacing constraint used by this repair operator."""
        self.min_offset_delta = max(0, int(new_delta))

    def _do(self, problem, X, **kwargs):
        repaired = np.rint(np.asarray(X)).astype(int) % self.cycle
        if self.min_offset_delta <= 0 or self.reference_population.size == 0:
            return repaired

        for index in range(len(repaired)):
            repaired[index] = _repair_candidate_offset_spacing(
                repaired[index],
                self.reference_population,
                self.cycle,
                self.min_offset_delta,
                self.rng,
                repair_stats=self.repair_stats,
                repair_stage='crossover',
            )
        return repaired


class CustomPerturbationMutation(Mutation):
    """将变异范围限制在一定波动范围内，并补齐最小 offset 差值约束。"""

    def __init__(self, cycle, prob=1.0, perturbation_scale=PERTURBATION_SCALE, reference_population=None, min_offset_delta=DEFAULT_MIN_OFFSET_DELTA, seed=None, repair_stats=None):
        super().__init__()
        self.cycle = cycle
        self.prob = prob
        self.perturbation_scale = perturbation_scale
        self.reference_population = _normalize_reference_population(reference_population)
        self.min_offset_delta = max(0, int(min_offset_delta))
        self.rng = np.random.default_rng(seed)
        self.repair_stats = repair_stats

    def update_delta(self, new_delta):
        """Update the minimum offset spacing constraint used by this mutation operator."""
        self.min_offset_delta = max(0, int(new_delta))

    def _do(self, problem, X, **kwargs):
        Y = np.rint(np.asarray(X)).astype(int) % self.cycle

        for i in range(len(Y)):
            if self.prob == 1.0 or self.rng.random() < self.prob:
                changed = False
                for j in range(problem.n_var):
                    if self.rng.random() < 0.3:
                        step = self.rng.integers(-self.perturbation_scale, self.perturbation_scale + 1)
                        Y[i, j] = (Y[i, j] + step) % self.cycle
                        changed = True
                if changed:
                    Y[i] = _repair_candidate_offset_spacing(
                        Y[i],
                        self.reference_population,
                        self.cycle,
                        self.min_offset_delta,
                        self.rng,
                        repair_stats=self.repair_stats,
                        repair_stage='mutation',
                    )
        return Y
