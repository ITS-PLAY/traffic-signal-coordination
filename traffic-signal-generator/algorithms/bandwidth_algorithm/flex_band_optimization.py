from algorithms.bandwidth_algorithm.flex_band import flexBand
from utils.logger import log


def judgeBandWeights(opt_objective,
                     num_signals,
                     outbound,
                     inbound):
    if 'bandWeights' in opt_objective.keys():
        # 该参数存在
        band_weights = opt_objective.get('bandWeights')
        if not band_weights:
            # 空数据
            band_weights = flexBand.getBandWeights(num_signals, outbound, inbound)
        # 该参数存在且不为空
        else:
            band_weights = opt_objective['bandWeights']
            # list
    else:
        # 如果不存在
        band_weights = flexBand.getBandWeights(num_signals, outbound, inbound)
    return band_weights


def judgeClearanceTime(opt_objective, green):
    _num_signals = len(green[0])
    if 'clearanceTime' in opt_objective.keys():
        # 该参数存在且不为空
        clearance_time = opt_objective.get('clearanceTime')
        if clearance_time is None or len(clearance_time) == 0:
            # 空数据
            clearance_time = [[0] * _num_signals, [0] * _num_signals]
        else:
            clearance_time = opt_objective['clearanceTime']
    else:
        # 如果不存
        clearance_time = [[0] * _num_signals, [0] * _num_signals]

    # 填补清空时间0
    clearance_time[0] = [0] * (_num_signals - len(clearance_time[0])) + clearance_time[0]
    clearance_time[1] = clearance_time[1] + [0] * (_num_signals - len(clearance_time[1]))
    return clearance_time


def judgeMultiCycle(opt_objective, green):
    _num_signals = len(green[0])
    if 'multiCycle' in opt_objective.keys():
        # 该参数存在
        multi_cycle = opt_objective.get('multiCycle')
        if multi_cycle is None:
            # 空数据
            multi_cycle = [1] * _num_signals
        # 该参数存在且不为空
        else:
            multi_cycle = opt_objective['multiCycle']
        # list
    else:
        # 如果不存在
        multi_cycle = [1] * _num_signals

    return multi_cycle


def run_flex_band(input_info):
    cl = input_info['cl']
    # green为2*num_signals的数组
    green = input_info['green']
    # 路口数量
    num_signals = len(green[0])
    # 路段距离
    dist = input_info['dist']
    # speed为2*(num_signals-1)的数组
    speed = input_info['speed']
    optimization_objective = input_info['optimizationObjective']

    result = {}
    if optimization_objective:
        outbound = optimization_objective['outbound'] if optimization_objective.get('outbound', None) is not None else True
        inbound = optimization_objective['inbound'] if optimization_objective.get('inbound', None) is not None else False
        # 多周期标识
        multi_cycle = judgeMultiCycle(optimization_objective, green)
        band_weights = judgeBandWeights(optimization_objective, num_signals, outbound, inbound)
        # 交叉口清空时间
        queue_clearance_time = judgeClearanceTime(optimization_objective, green)
        # 正向最小带宽标志：以该带宽作为最小值，求解正向贯通绿波
        min_outbound_thru = optimization_objective[
            'minOutboundThru'] if 'minOutboundThru' in optimization_objective else 0
        # 反向最小带宽标志：以该带宽作为最小值，求解正向贯通绿波
        min_inbound_thru = optimization_objective['minInboundThru'] if 'minInboundThru' in optimization_objective else 0

        solution = flexBand.solve(
            cl=cl,
            green=green,
            dist=dist,
            speed=speed,
            band_weights=band_weights,
            min_outbound_thru=min_outbound_thru,
            min_inbound_thru=min_inbound_thru,
            multi_cycle=multi_cycle,
            queue_clearance_time=queue_clearance_time
        )


        if solution is not None:
            cl, b0, b1, offset, t = solution
            result = {
                'cl': round(cl),
                'b0': b0.astype(int).tolist(),
                'b1': b1.astype(int).tolist(),
                'offset': offset
            }
    log.info('flex band algorithm output: {}'.format(result))
    return result