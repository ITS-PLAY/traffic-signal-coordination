from utils.util import replace_offset_value, get_plan_info, get_cycles


def _get_direction_metric(direction_metrics, direction, metric_name):
    """Safely read a metric from direction_metrics."""
    direction_values = direction_metrics.get(direction) or {}
    return direction_values.get(metric_name)


def generate_output(input_data, algorithm_output):
    """拼接输出"""
    algorithm_output = algorithm_output or {}
    direction_metrics = algorithm_output.get('direction_metrics') or {}
    plan = algorithm_output.get('plan') or []
    cross_list = input_data.get('crossList', [])

    if len(plan) != len(cross_list):
        raise ValueError(f'invalid plan length: expected={len(cross_list)}, actual={len(plan)}')

    # 公共周期
    output = {'planInfo': input_data['planInfo'], "evaluation": {}}
    for index, cross_id in enumerate(cross_list):
        cross_offset = plan[index]
        cross_plan_info = output['planInfo'][cross_id]
        # 更新相位差
        output['planInfo'][cross_id] = replace_offset_value(cross_plan_info, cross_offset)

    output['evaluation'] = {
        "avgParkingRatio": algorithm_output.get('avg_waiting_ratio'),
        "avgSpeed": algorithm_output.get('avg_speed'),
        "outbound": {
            "avgParkingRatio": _get_direction_metric(direction_metrics, 'outbound', 'avg_waiting_ratio'),
            "avgSpeed": _get_direction_metric(direction_metrics, 'outbound', 'avg_speed'),
        },
        "inbound": {
            "avgParkingRatio": _get_direction_metric(direction_metrics, 'inbound', 'avg_waiting_ratio'),
            "avgSpeed": _get_direction_metric(direction_metrics, 'inbound', 'avg_speed'),
        },
    }
    return output
