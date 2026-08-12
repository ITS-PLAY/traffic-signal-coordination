#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
from gekko import GEKKO


class flexBand(object):
    EPS = 0.001
    CL_MAX = 180
    SPEED_ADJUST_RANGE = 2
    TWO_WAY_VOL_RATIO = 5
    DRAW_CL = 3

    @classmethod
    def run_flex_band_gekko_mcyl(cls, num_signals, band_weights, red_time, queue_clearance_time,
                                 two_way_vol_ratio, cycle_range, speed_range,
                                 speed_change_range, distance, left_turn_time,
                                 min_outbound_thru=0, min_inbound_thru=0, multi_cycle=None):

        assert red_time.shape == (2, num_signals)
        assert queue_clearance_time.shape == (2, num_signals)
        assert left_turn_time.shape == (2, num_signals)
        assert speed_range.shape == (2, num_signals - 1, 2)
        assert speed_change_range.shape == (2, num_signals - 2, 2)
        assert distance.shape == (2, num_signals - 1)

        # create model
        model = GEKKO(remote=False)

        # create varibles
        b_ = model.Array(model.Var, 2 * (num_signals - 1), lb=0, ub=1)
        w_ = model.Array(model.Var, 2 * num_signals * 2, lb=0, ub=1)
        m_ = model.Array(model.Var, 2 * (num_signals - 1), integer=True, lb=0)
        two_way_m_ = model.Array(model.Var, num_signals - 1, integer=1)
        z_ = model.Array(model.Var, 1, lb=cycle_range[1], ub=cycle_range[0])
        t_ = model.Array(model.Var, 2 * (num_signals - 1), lb=0)
        L_sig_ = model.Array(model.Var, 2 * num_signals, lb=0, ub=1, integer=1)
        fi_ = model.Array(model.Var, num_signals - 1, lb=0, ub=2)
        fi_r_ = model.Array(model.Var, num_signals - 1, lb=0, ub=2)
        b_sig_ = model.Array(model.Var, 2 * (num_signals - 1), value=1, lb=0, ub=1, integer=1)

        b = np.array(b_).reshape((2, num_signals - 1))
        w = np.array(w_).reshape((2, num_signals, 2))
        m = np.array(m_).reshape((2, num_signals - 1))
        two_way_m = np.array(two_way_m_)
        z = np.array(z_)
        t = np.array(t_).reshape((2, num_signals - 1))
        L_sig = np.array(L_sig_).reshape((2, num_signals))
        fi = np.array(fi_)
        fi_r = np.array(fi_r_)
        b_sig = np.array(b_sig_).reshape((2, num_signals - 1))

        r = red_time
        tao = queue_clearance_time
        L = left_turn_time
        d = distance
        e, f = speed_range[:, :, 0], speed_range[:, :, 1]
        g, h = speed_change_range[:, :, 0], speed_change_range[:, :, 1]

        m2 = {}
        # add constraints
        # No.1: Directional Interference

        # 绿波起点w的约束。
        # w为三维数组，第一维表示正向或反向，第二维表示路口，
        # 第三维表示绿波起点位置（0表示当前路口为终点时，上游绿波的起点；1表示当前路口为起点时，下游绿波的起点）
        for i in range(num_signals - 1):
            model.Equation(w[0, i, 0] - tao[0, i] >= 0)
            model.Equation(w[0, i, 1] <= (1 - r[0, i]) / multi_cycle[i] - b[0, i])
            model.Equation(w[0, i, 1] >= 0)

            # 正向清空时间的强制约束，相邻路口的绿波起点w需要满足清空时间
            if tao[0, i + 1] / cycle_range[1] >= 1:
                model.Equation(w[0, i + 1, 0] - w[0, i, 1] >= tao[0, i + 1])

            # 反向清空时间的强制约束，相邻路口的绿波起点w需要满足清空时间
            if tao[1, i] / cycle_range[1] >= 1:
                model.Equation(w[1, i, 0] - w[1, i + 1, 1] >= tao[1, i])

            model.Equation(w[0, i + 1, 0] - tao[0, i + 1] >= 0)
            model.Equation(w[0, i + 1, 0] <= (1 - r[0, i + 1]) / multi_cycle[i + 1] - b[0, i])

            if multi_cycle[i] == 1 or min_outbound_thru == 0:
                model.Equation(w[1, i, 0] - tao[1, i] >= 0)
                model.Equation(w[1, i, 1] >= 0)
                model.Equation(w[1, i, 0] <= (1 - r[1, i]) / multi_cycle[i] - b[1, i])
            else:
                if i not in m2:
                    m2[i] = model.Var(lb=0, ub=multi_cycle[i] - 1, integer=1)
                model.Equation(w[1, i, 1] >= m2[i] / multi_cycle[i])
                model.Equation(w[1, i, 0] - tao[1, i] >= m2[i] / multi_cycle[i])
                model.Equation(w[1, i, 0] <= (1 + m2[i] - r[1, i]) / multi_cycle[i] - b[1, i])

            if multi_cycle[i + 1] == 1 or min_inbound_thru == 0:
                model.Equation(w[1, i + 1, 0] - tao[1, i + 1] >= 0)
                model.Equation(w[1, i + 1, 1] >= 0)
                model.Equation(w[1, i + 1, 1] <= (1 - r[1, i + 1]) / multi_cycle[i + 1] - b[1, i])
            else:
                if (i + 1) not in m2:
                    m2[i + 1] = model.Var(lb=0, ub=multi_cycle[i + 1] - 1, integer=1)
                model.Equation(w[1, i + 1, 1] >= m2[i + 1] / multi_cycle[i + 1])
                model.Equation(w[1, i + 1, 0] - tao[1, i + 1] >= m2[i + 1])
                model.Equation(w[1, i + 1, 1] <= (1 + m2[i + 1] - r[1, i + 1]) / multi_cycle[i + 1] - b[1, i])

        # No.2: Loop Integer
        for i in range(num_signals - 1):
            # outbound, 反向优先时，取消正向的相位差约束
            if band_weights[1, i] / band_weights[0, i] < cls.TWO_WAY_VOL_RATIO:
                model.Equation(L_sig[0, i] * L[0, i] + w[0, i, 1] + t[0, i] + r[0, i] / (2 * multi_cycle[i]) == fi[i] + L_sig[0, i + 1] * L[0, i + 1] + w[0, i + 1, 0] + r[0, i + 1] / (2 * multi_cycle[i + 1]))
            # inbound, 正向优先时，取消反向的相位差约束
            if band_weights[0, i] / band_weights[1, i] < cls.TWO_WAY_VOL_RATIO:
                model.Equation(L_sig[1, i] * L[1, i] + w[1, i, 0] + r[1, i] / (2 * multi_cycle[i]) + fi_r[i] == L_sig[1, i + 1] * L[1, i + 1] + w[1, i + 1, 1] + t[1, i] + r[1, i + 1] / (2 * multi_cycle[i + 1]))
            model.Equation(fi[i] + fi_r[i] == two_way_m[i] / (1 if min_outbound_thru > 0 else np.lcm(multi_cycle[i], multi_cycle[i + 1])))

        # No.3: Weighted inbound and outbound bandwidth
        # 约束每个路段的正向和反向的带宽权重
        for i in range(num_signals - 1):
            k = band_weights[0, i] / band_weights[1, i]
            model.Equation((k - 1) * k * b[1, i] <= (k - 1) * b[0, i])

        # No.4: Speed Range
        for j in range(2):
            for i in range(num_signals - 1):
                model.Equation(t[j, i] >= (d[j, i] / f[j, i]) * z[0])
                model.Equation(t[j, i] <= (d[j, i] / e[j, i]) * z[0])

        # Additionally, bind outbound or inbound bandwidth
        for i in range(num_signals - 2):
            if min_outbound_thru > 0:
                model.Equation(b[0, i] == b[0, i + 1])
            if min_inbound_thru > 0:
                model.Equation(b[1, i] == b[1, i + 1])
        for i in range(num_signals - 1):
            if min_outbound_thru > 0:
                model.Equation(b_sig[0, i] == 1)
            if min_inbound_thru > 0:
                model.Equation(b_sig[1, i] == 1)
        for i in range(num_signals):
            if min_outbound_thru > 0:
                model.Equation(w[0, i, 0] == w[0, i, 1])
            if min_inbound_thru > 0:
                model.Equation(w[1, i, 0] == w[1, i, 1])

        # enforce bandwidth
        if min_outbound_thru > 0:
            model.Equation(b[0, 0] >= min_outbound_thru * z[0])
        if min_inbound_thru:
            model.Equation(b[1, 0] >= min_inbound_thru * z[0])

        # build objective
        # 目标函数调整为考虑权重因素下，双向总带宽的最大
        model.Maximize(np.sum(band_weights * b) / (num_signals - 1) - np.sum(w) * 0.0001)
        model.solve(debug=False, disp=False)
        if model.options.APPINFO != 0 or model.options.APPSTATUS != 1:
            return None

        solution_b = [v.value[0] for v in b_]
        solution_w = [v.value[0] for v in w_]
        solution_m = [v.value[0] for v in m_]
        solution_z = [v.value[0] for v in z_]
        solution_t = [v.value[0] for v in t_]
        solution_L_sig = [v.value[0] for v in L_sig_]
        solution_fi = [v.value[0] for v in fi_]
        solution_b_sig = [v.value[0] for v in b_sig_]

        return solution_b, solution_w, solution_m, solution_z, solution_t, solution_L_sig, solution_fi, solution_b_sig

    @classmethod
    def solve(cls, cl, green, dist, speed,
              band_weights,
              two_way_vol_ratio=1,
              min_outbound_thru=0, min_inbound_thru=0,
              multi_cycle=None,
              queue_clearance_time=None):
        """
        :param cl: 路线周期
        :param green: 绿信比
        :param dist: 路段距离
        :param speed: 建议速度
        :param two_way_vol_ratio: 流量比
        :param band_weights: 带宽权重 -- 路段带宽
        :param min_outbound_thru:
        :param min_inbound_thru:
        :param multi_cycle: 周期数量
        :param queue_clearance_time: 清空时间
        :return:
        """
        # 正反向优化参数
        # 隐含了是否贯穿参数
        # 含义：贯穿带宽最小值，如 带宽为小为m的贯穿绿波
        #  outbound, inbound <->min_outbound_thru, min_inbound_thru  含义相同
        # min_outbound_thru = 0 正向优化不要求贯穿
        # min_inbound_thru = 0 反向优化不要求贯穿
        # min_outbound_thru > n 意思正向带宽最小为n的贯穿绿波
        # min_inbound_thru > m 意思反向带宽最小为m的贯穿绿波
        # min_outbound_thru = n and min_inbound_thru=m 意思双向正向带宽最小为n、反向带宽最小为m的贯穿绿波

        num_signals = len(green[0])
        green = np.array(green)
        distance = np.array([dist] * 2)
        red_time = 1 - green

        # band_weights = np.ones((2, num_signals - 1))
        # band_weights[1,] = 1 / TWO_WAY_VOL_RATIO
        band_weights = cls.setBandWeights(band_weights)
        # 清空时间
        # queue_clearance_time = np.zeros((2, num_signals))
        queue_clearance_time = cls.setclearanceTime(queue_clearance_time, num_signals)
        # 默认1
        two_way_vol_ratio = 1 / two_way_vol_ratio
        # two_way_vol_ratio = cls.setTwoWayVolRatio()
        # 周期范围
        # cycle_range = [1 / (cl - CL_ADJUST_RANGE), 1 / min(cl + CL_ADJUST_RANGE, CL_MAX)]
        cycle_range = cls.setCycleRange(cl)
        # 路口周期数量
        multi_cycle = cls.setMultiCycle(num_signals, multi_cycle)
        # 速度范围
        # speed_range = (speed - SPEED_ADJUST_RANGE) / 3.6 * np.ones((2, num_signals - 1, 2))
        # speed_range[:, :, 1] = (speed + SPEED_ADJUST_RANGE) / 3.6
        speed_range = cls.setSpeedRange(speed, num_signals)
        # 速度变化范围：默认值10000。期望它不起作用
        speed_change_range = cls.setSpeedChangeRange(num_signals)
        # 左转时间：默认0
        left_turn_time = np.zeros((2, num_signals))

        solution = cls.run_flex_band_gekko_mcyl(num_signals, band_weights, red_time, queue_clearance_time,
                                                two_way_vol_ratio, cycle_range, speed_range, speed_change_range,
                                                distance, left_turn_time, min_outbound_thru, min_inbound_thru,
                                                multi_cycle)
        if solution == None:
            return None
        b, w, m, z, t, L_sig, fi, b_sig = solution
        cycle = 1 / z[0]
        t = np.array(t).reshape((2, num_signals - 1))
        b = np.array(b).reshape((2, num_signals - 1))

        # 根据正向相位差，计算正向协调相位的绿初相位差
        optimized_phase_offset=[]
        for i in range(num_signals - 1):
            cross_offset_value = fi[i] + (red_time[0, i + 1] / multi_cycle[i + 1] - red_time[0, i] / multi_cycle[i]) / 2
            optimized_phase_offset.append(cross_offset_value)
        offset = [round(cycle * value % cycle) for value in optimized_phase_offset]
        return cycle, cycle * b[0], cycle * b[1], offset, t

    @classmethod
    def estimate(cls, cl, green, offset, travel_time, flow, bottom=True):
        cl = cl[0]
        soft, hard, delay = 0.0, 0.0, 0.0
        last = [(0, flow)] if bottom else [(green[0] - flow, flow)]
        for i in range(len(green) - 1):
            r, g = [], []
            for start, width in last:

                start = (start + travel_time[i] - offset[i] / cl) % 1
                if start < green[i + 1]:
                    if start + width <= green[i + 1]:
                        g.append((start, width))
                    else:
                        g.append((start, green[i + 1] - start))
                        if start + width <= 1:
                            r.append((green[i + 1], start + width - green[i + 1]))
                        else:
                            r.append((green[i + 1], 1 - green[i + 1]))
                            g.append((0, start + width - 1))
                elif start + width <= 1:
                    r.append((start, width))
                else:
                    r.append((start, 1 - start))
                    g.append((0, start + width - 1))
            r.sort()
            g.sort()
            last = []
            current = 0
            for start, width in r:
                last.append((current, width))
                soft += width / flow
                hard += width / flow
                delay += (1 - start + current) * width / flow
                current += width
            for start, width in g:
                if start < current + cls.EPS:
                    last.append((current, width))
                    if start < current - cls.EPS:
                        hard += width / flow
                        delay += (current - start) * width / flow
                    current += width
                else:
                    last.append((start, width))
                    current = start + width
        return soft, hard, cl * delay

    @classmethod
    def getBandWeights(cls, num_signals, outbound, inbound):
        # 获取带宽权重. 正向优先时，正向/反向=5;反向优先时，正向/反向=0.2;双向时，设置正向/反向=1
        band_weights = np.ones((2, num_signals - 1))
        if outbound == True and inbound == True:
            band_weights[0,:] = 1
        elif outbound == True and inbound == False:
            band_weights[0,:] = cls.TWO_WAY_VOL_RATIO
        elif inbound == True and outbound == False:
            band_weights[0,:] = 1 / cls.TWO_WAY_VOL_RATIO
        return band_weights

    @classmethod
    def setTwoWayVolRatio(cls, outbound, inbound):
        # 废弃修改为bandWight参数
        if outbound == True and inbound == True:
            return 1
        elif outbound == True and inbound == False:

            return cls.TWO_WAY_VOL_RATIO

        elif inbound == True and outbound == False:

            return 1 / cls.TWO_WAY_VOL_RATIO
        else:

            return 1

    @classmethod
    def setBandWeights(cls, band_weights):
        if isinstance(band_weights, np.ndarray):
            band_weights = band_weights
        else:
            band_weights = np.array(band_weights)
        return band_weights

    @classmethod
    def setMultiCycle(cls, num_signals, multi_cycle):
        # multi_cycle = None 代表对应i路口是单周期（路线路口不存在多周期的情况）
        # multi_cycle = 1  代表对应i路口是单周期
        # multi_cycle = 2  代表对应i路口是双周期
        # multi_cycle = 3  代表对应i路口是多=3周期

        if multi_cycle is None:
            # 单周期
            multi_cycle = [1] * num_signals
        elif isinstance(multi_cycle, list) and len(multi_cycle) == 0:
            # 默认单周期
            multi_cycle = [1] * num_signals
            # multi_cycle = [1,1,2,3,1] 说明路线的第2个路口为双周期控制，第3个路口为多（3）周期控制
        else:
            assert isinstance(multi_cycle, list) and len(multi_cycle) == num_signals, '多周期参数输入正确'
            multi_cycle = multi_cycle

        return multi_cycle

    @classmethod
    def setCycleRange(cls, cl):
        # 判断 cl 是否为空
        if cl is None:
            raise ValueError("参数 cl 不可以为空")

        if isinstance(cl, int) or isinstance(cl, float) and cl > 0:
            if cl <= 0:
                raise ValueError("参数 cl 作为整数时必须为正整数")
            return [1 / cl, 1 / cl]

        elif isinstance(cl, list):
            if len(cl) == 0:
                # 空list
                raise ValueError("参数 cl 不可以为空list")
            elif len(cl) == 1:
                if cl[0] >= 0:
                    return [1 / cl[0], 1 / cl[0]]
                else:
                    raise ValueError("参数 cl 必须大于0")
            elif len(cl) == 2:
                return [1 / cl[0], 1 / min(cl[1], cls.CL_MAX)]
            else:
                raise ValueError("参数 cl 输入异常")

        else:
            raise ValueError("参数 cl 输入异常")

    @classmethod
    def setclearanceTime(cls, queue_clearance_time, num_signals):
        # queue_clearance_time 如果存在
        assert len(queue_clearance_time[0]) == num_signals, '清空时间必须与路口数量一致'
        queue_clearance_time = np.array(queue_clearance_time)
        return queue_clearance_time

    @classmethod
    def setSpeedRange(cls, speed, num_signals):
        # speed 必填项：(1)数值全部一样 (2)数值不同
        assert type(speed) == list and len(speed) == 2
        speed_range = np.ones((2, num_signals - 1, 2))
        # 填充数据
        for i in range(len(speed)):
            for j in range(len(speed[i])):
                speed_range[i, j, 0] = (speed[i][j]  - cls.SPEED_ADJUST_RANGE) / 3.6
                speed_range[i, j, 1] = (speed[i][j]  + cls.SPEED_ADJUST_RANGE) / 3.6
        return speed_range

    @classmethod
    def setSpeedChangeRange(cls, num_signals):
        speed_change_range = -11000 * np.ones((2, num_signals - 2, 2))
        speed_change_range[:, :, 1] = 11000
        return speed_change_range


class OneWayOptimization(flexBand):

    @classmethod
    def solve(cls, cl, green, dist, speed,
             band_weights,
             two_way_vol_ratio=1,
             min_outbound_thru=0, min_inbound_thru=0,
             multi_cycle=None,
             queue_clearance_time=None):

        num_signals = len(green[0])
        queue_clearance_time = cls.setclearanceTime(queue_clearance_time, num_signals)
        multi_cycle = cls.setMultiCycle(num_signals, multi_cycle)

        # 将绿信比改为绿灯时长
        for dir_index, dir_greens in enumerate(green):
            for cross_index, value in enumerate(dir_greens):
                green[dir_index][cross_index] *=  cl / multi_cycle[cross_index]

        # 判断正向或反向
        if min_outbound_thru > 0:
            index = 0
        else:
            index = 1

        queue_clearance_time = queue_clearance_time[index, :]
        speed = speed[index]

        # 相邻路口的相对相位差
        offset = []
        # 正向和反向的带宽长度，仅供参考
        outbound_band, inbound_band = [], []
        for i in range(1, num_signals):
            travel_time = 3.6 * dist[i-1] / speed[i-1]

            if index == 0:
                # 计算正向相位差和带宽值
                travel_time = travel_time - (queue_clearance_time[i] + queue_clearance_time[i-1])
                bandwidth = min(green[0][i - 1], green[0][i])
                outbound_band.append(bandwidth)
                inbound_band.append(0)
            else:
                # 当计算反向相位差时，采用减的方式计算 与下一个路口的相对相位差
                travel_time = -1 * travel_time + queue_clearance_time[i-1] - queue_clearance_time[i]
                # 计算反向的带宽值
                bandwidth = min(green[1][i - 1], green[1][i])
                inbound_band.append(bandwidth)
                outbound_band.append(0)

            cross_offset_value = travel_time % (cl/multi_cycle[i])
            offset.append(round(cross_offset_value))
        return cl, np.array(outbound_band), np.array(inbound_band), offset, np.array([])
