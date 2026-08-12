# -*- coding: utf-8 -*-
"""
合并后的项目代码
源项目: D:\本地脚本\SUMO\traffic-signal-generator
入口文件: main.py
自动生成 - 请勿直接编辑
"""



# ----------------------------------------------------------------------------
# 原文件: common\common_vars.py
# ----------------------------------------------------------------------------

import os
from enum import Enum

# 默认超时秒数
DEFAULT_TIMEOUT = 60

# 遗传算法的变异幅度
PERTURBATION_SCALE = 10

# 遗传算法新解与已有方案之间允许的初始最小 offset 环形差值；
# 连续多代提升不足时会在 GA 内按代动态放大
DEFAULT_MIN_OFFSET_DELTA = 3

# 遗传算法动态种群规模的最小值
DEFAULT_GA_POP_MIN = 12

# 遗传算法动态种群规模的最大值
DEFAULT_GA_POP_MAX = 64

# 遗传算法动态种群规模的每变量倍数
DEFAULT_GA_POP_PER_VAR = 8

# 遗传算法提前终止时至少执行的代数
DEFAULT_GA_EARLY_STOP_MIN_GEN = 5

# 遗传算法提前终止时允许连续无提升的代数
DEFAULT_GA_EARLY_STOP_PATIENCE = 4

# 遗传算法提前终止与动态放大 offset 差值时认定为有效提升的最小目标变化
DEFAULT_GA_EARLY_STOP_MIN_IMPROVEMENT = 0.05

# 当动态放大的最小 offset 差值遇到明显提升后，是否恢复为初始值
DEFAULT_GA_RESET_MIN_OFFSET_DELTA_ON_IMPROVEMENT = True

# 遗传算法迭代次数
GA_ITERATIONS = 20

# 仿真器的服务名
EVALUATOR_FUNC_NAME = 'ts_evaluator'
# 仿真的 url
EVALUATOR_URL = os.environ.get('EVALUATOR_URL', 'http://ts-evaluator')
# 仿真的路由
EVALUATOR_URL_PATH = '/algorithm/invoke'

# 默认的进口道顺序
DEFAULT_DIRECTIONS = ['1', '2', '3', '4']  # 北、东、南、西
# 遗传算法的随机种子
DEFAULT_SEED = 42
# 遗传算法的单交叉口初始种群数量（保留为兼容常量）
DEFAULT_POP_SIZE = 100
# 遗传算法的运行效率标志
FAST_MODE = 'fast'
BEST_MODE = 'best'
DEFAULT_MODE = FAST_MODE

# 分段候选生成时每个子问题覆盖的默认路口数
DEFAULT_SEGMENT_CROSS_COUNT = 3
# 分段优化时相邻子问题默认共享的重叠路口数量，默认重叠 2 个路口
DEFAULT_SEGMENT_OVERLAP_CROSS_COUNT = 2


# 算法目标
class OBJECTIVE(Enum):
    TRAVEL_TIME = "travel_time"
    WEIGHTED_SPEED = "weighted_speed"
    STOP_RATE = "stop_rate"


# ----------------------------------------------------------------------------
# 原文件: core\traffic_light.py
# ----------------------------------------------------------------------------

from typing import Any, List, Dict

# 信控方案类，由输入解析得来
class TrafficLightPlan:
    def __init__(self, cross_id: str, phases: List[str], durations: Dict[str, int], functions: Dict[str, Any], offset: int, coordination_phase: str = ''):
        self.id = cross_id
        self.cross_id = cross_id
        self.phases = phases
        self.durations = durations
        self.functions = functions
        self.offset = offset
        self.coordination_phase = coordination_phase
        self.cycle = sum(self.durations.values())
    
    # 转换为完整JSON格式
    def to_json(self) -> dict:
        return {
            'id': self.id,
            'cross_id': self.cross_id,
            'phases': self.phases,
            'durations': self.durations,
            'functions': self.functions,
            'offset': self.offset
        }
    
    # 转换为字符串格式，TODO：需要补充更多信息
    def to_string(self) -> str:
        return f'{self.id} {self.cross_id}'


# ----------------------------------------------------------------------------
# 原文件: utils\np_encoder.py
# ----------------------------------------------------------------------------

import numpy as np
import json

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


# ----------------------------------------------------------------------------
# 原文件: core\edge.py
# ----------------------------------------------------------------------------

from typing import List

class Lane:
    """车道类"""
    def __init__(self, eid: str, index: int, length: float, speed: float, turn: List[str] = []):
        self.id = f'{eid}_{index}'
        self.eid = eid
        self.index = index
        self.length = length
        self.speed = speed
        self.turn = turn
    
    def get_id(self) -> str:
        return self.id
    
    # 转换为json格式
    def to_json(self) -> dict:
        return {
            'id': self.get_id(),
            'eid': self.eid,
            'index': self.index,
            'turn': self.turn,
            'length': self.length,
            'speed': self.speed
        }
    # 转换为字符串格式, TODO: 增加更多的信息
    def to_string(self) -> str:
        return f'{self.get_id()} ({self.index})'

class Edge:
    """边类"""
    def __init__(self, from_node: str, to_node: str, length: float, speed: float, lane_num: int, lanes: List[Lane] = [], type: str = 'normal'):
        self.id = f'{from_node}-{to_node}'
        self.from_node = from_node
        self.to_node = to_node
        self.length = length
        self.speed = speed
        self.lane_num = lane_num
        self.lanes = lanes
        self.type = type
    
    # 获取边id
    def get_id(self) -> str:
        if self.id is None:
            self.id = f'{self.from_node}-{self.to_node}'
        return self.id

    # 设置车道列表
    def set_lanes(self, lanes: List[Lane]):
        self.lanes = lanes
        # 设置车道数量，生成路网需要为边设置车道数，不然会报和车道数量不匹配错误
        self.lane_num = len(lanes)
    
    # 设置速度
    def set_speed(self, speed: float):
        self.speed = speed
        for lane in self.lanes:
            lane.speed = speed

    # 转换为json格式
    def to_json(self) -> dict:
        return {
            'id': self.get_id(),
            'from_node': self.from_node,
            'to_node': self.to_node,
            'length': self.length,
            'speed': self.speed,
            'lane_num': self.lane_num,
            'lanes': [lane.to_json() for lane in self.lanes],
            'type': self.type
        }
    
    # 转换为字符串格式, TODO: 增加更多的信息
    def to_string(self) -> str:
        return f'{self.get_id()} ({self.from_node.get_id()} -> {self.to_node.get_id()})'


# ----------------------------------------------------------------------------
# 原文件: utils\logger.py
# ----------------------------------------------------------------------------

import logging
import sys

log = logging.getLogger()
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt='[%(levelname)s] %(asctime)s | %(filename)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
log.addHandler(handler)


# ----------------------------------------------------------------------------
# 原文件: core\point.py
# ----------------------------------------------------------------------------

from typing import Dict, Any

# 点类，表示路口周围虚拟的节点（用于处理入口道前车道数量变化的情况）
class Point:
    def __init__(self, cross_id: str, dir: str):
        self.cross_id = cross_id
        self.id = None
        self.dir = dir

    # 获取点id
    def get_id(self) -> str:
        if self.id is None:
            if self.dir == '0':
                self.id = self.cross_id
            else:
                self.id = f'{self.cross_id}P{self.dir}'
        return self.id

    # 转换为json格式
    def to_json(self) -> Dict[str, Any]:
        return {
            "cross_id": self.cross_id,
            "id": self.id,
            "dir": self.dir
        }


# ----------------------------------------------------------------------------
# 原文件: algorithms\bandwidth_algorithm\flex_band.py
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# 原文件: utils\profiling.py
# ----------------------------------------------------------------------------

import collections
import json
import os
import sys
import time
from contextlib import contextmanager



def is_profiling_enabled(input_data=None):
    config = input_data.get('config', {}) if isinstance(input_data, dict) else {}
    config_value = config.get('enableProfiling') if isinstance(config, dict) else None
    if config_value is not None:
        return bool(config_value)
    return os.environ.get('ENABLE_GEN_PROFILING', '0') == '1'


def new_profile_store():
    return collections.OrderedDict()


def _emit_profile_line(message):
    log.info(message)
    try:
        sys.stderr.write(f'{message}\n')
        sys.stderr.flush()
    except Exception:
        pass


@contextmanager
def profile_stage(profile_store, stage_name, enabled=False, emit_log=True):
    start = time.perf_counter()
    try:
        yield
    finally:
        if not enabled:
            return
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        profile_store[stage_name] = elapsed_ms
        if emit_log:
            _emit_profile_line(f'profile stage={stage_name} elapsed_ms={elapsed_ms}')


def finalize_profile_summary(summary_name, profile_store, enabled=False, extra_fields=None):
    if not enabled:
        return
    summary = collections.OrderedDict(profile_store)
    if extra_fields:
        for key, value in extra_fields.items():
            summary[key] = value
    _emit_profile_line(f'profile summary name={summary_name} data={json.dumps(summary, ensure_ascii=False)}')


# ----------------------------------------------------------------------------
# 原文件: common\http_client.py
# ----------------------------------------------------------------------------

import requests
import random
import time



# evaluator 单次 HTTP 请求超时时间，单位秒。
EVALUATOR_HTTP_TIMEOUT_SECONDS = 30.0

# evaluator 繁忙或网络抖动时的最大重试次数。
EVALUATOR_RETRY_TIMES = 12

# 首次重试前的基础等待时间，单位秒；后续会按指数退避放大。
EVALUATOR_RETRY_DELAY_SECONDS = 1.0

# 单次重试等待时间上限，单位秒，避免退避时间无限增长。
EVALUATOR_RETRY_MAX_DELAY_SECONDS = 8.0

# 单个 generator 实例同时发往 evaluator 的最大并发请求数。
EVALUATOR_MAX_INFLIGHT = 4

# GA 外层等待单个评估任务完成的超时预算，
# 需要覆盖「HTTP 超时 * 重试次数 + 退避等待 + 额外缓冲」。
GA_EVALUATION_TIMEOUT_SECONDS = max(
    DEFAULT_TIMEOUT,
    int(
        EVALUATOR_HTTP_TIMEOUT_SECONDS * EVALUATOR_RETRY_TIMES
        + EVALUATOR_RETRY_MAX_DELAY_SECONDS * max(EVALUATOR_RETRY_TIMES - 1, 0)
        + 10
    ),
)

# 这些状态码通常表示服务暂时繁忙或网关瞬时异常，适合等待后重试。
DEFAULT_RETRY_STATUS_CODES = (429, 502, 503, 504)


class HttpServiceClient:
    """HTTP 服务调用客户端"""

    def __init__(
        self,
        base_url,
        timeout=EVALUATOR_HTTP_TIMEOUT_SECONDS,
        retry_times=EVALUATOR_RETRY_TIMES,
        retry_delay_seconds=EVALUATOR_RETRY_DELAY_SECONDS,
        max_retry_delay_seconds=EVALUATOR_RETRY_MAX_DELAY_SECONDS,
        retry_status_codes=None,
    ):
        # 统一在客户端内部使用 evaluator 的固定默认超时和重试参数，
        # 这样调用方只需传 base_url，避免在业务代码里散落同一套配置。
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_times = retry_times
        self.retry_delay_seconds = retry_delay_seconds
        self.max_retry_delay_seconds = max_retry_delay_seconds
        self.retry_status_codes = set(retry_status_codes or DEFAULT_RETRY_STATUS_CODES)
        self.session = None

    def _get_retry_delay(self, attempt, response=None):
        # 如果服务端显式返回 Retry-After，则优先尊重服务端的等待时间。
        if response is not None:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except (TypeError, ValueError):
                    pass

        # 否则使用指数退避，并附加少量随机抖动，
        # 避免多个并发请求在同一时刻再次冲击下游服务。
        base_delay = min(
            self.max_retry_delay_seconds,
            self.retry_delay_seconds * (2 ** attempt),
        )
        jitter = min(1.0, base_delay * 0.2)
        return base_delay + random.uniform(0, jitter)

    def __enter__(self):
        """建立连接"""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HttpServiceClient/1.0'
        })
        return self

    def post(self, endpoint, data=None):
        """POST 请求"""
        url = f"{self.base_url}{endpoint}"

        # 在有限次数内重试，尽量把 evaluator 的瞬时繁忙转化为等待而不是直接失败。
        for attempt in range(self.retry_times):
            try:
                response = self.session.post(
                    url=url,
                    json=data,
                    timeout=self.timeout
                )

                # 对明确可重试的繁忙/网关类状态码走退避重试。
                if response.status_code in self.retry_status_codes and attempt < self.retry_times - 1:
                    delay = self._get_retry_delay(attempt, response=response)
                    response_text = (response.text or '')[:4000]
                    log.warning(
                        f"请求繁忙，准备重试 (尝试 {attempt + 1}/{self.retry_times}): "
                        f"status={response.status_code}, url={url}, delay={delay:.2f}s, body={response_text}"
                    )
                    time.sleep(delay)
                    continue

                # 非重试状态码或最后一次尝试时，按正常 HTTP 结果处理。
                response.raise_for_status()
                result = response.json()
                return result

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 'unknown'
                response_text = ''
                if e.response is not None:
                    response_text = (e.response.text or '')[:4000]
                log.info(
                    f"请求失败 (尝试 {attempt + 1}/{self.retry_times}): status={status_code}, url={url}, body={response_text}"
                )
                if attempt == self.retry_times - 1:
                    return {
                        'error': 'http_error',
                        'status_code': status_code,
                        'url': url,
                        'response_text': response_text,
                    }
                # 对 HTTP 层错误继续退避，给下游一点恢复时间。
                delay = self._get_retry_delay(attempt, response=e.response)
                time.sleep(delay)
            except requests.exceptions.RequestException as e:
                log.info(f"请求失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt == self.retry_times - 1:
                    return {
                        'error': 'request_exception',
                        'exception': str(e),
                        'url': url,
                    }
                # 网络抖动、连接超时等异常也做同样的退避重试。
                delay = self._get_retry_delay(attempt)
                time.sleep(delay)
        return {
            'error': 'request_failed',
            'url': url,
        }

    def __exit__(self, exc_type, exc_val, exc_tb):
        """关闭会话"""
        self.session.close()


# ----------------------------------------------------------------------------
# 原文件: core\cross.py
# ----------------------------------------------------------------------------

from typing import List, Dict, Any, Tuple

# 路口类，用于表示路口定义，包含实际的路口中心点、抽象的周边道路上的过渡点、周边道路边、信控方案、下一个路口、上一个路口
class Cross:
    def __init__(self, id: str, points: List[Point], edges: List[Edge], dir_points: Dict[str, Point], dir_edges: Dict[str, Any], traffic_light: TrafficLightPlan):
        """
        初始化路口对象
        
        Args:
            id (str): 路口ID
            points (List[Point]): 路口周边的过渡点列表
            edges (List[Edge]): 路口与周边过渡点之间的道路边列表
            dir_points (Dict[str, Point]): 每个方向上的过渡点字典，键为方向（1-4），值为过渡点对象
            dir_edges (Dict[str, Dict[str, Edge]]): 每个方向上与过渡点之间的边字典，键为方向（1-4），值为{"in": 入边对象, "out": 出边对象}
            traffic_light (TrafficLightPlan): 路口的信控方案对象
            next_cross (Dict[str, Any]): 下一个路口字典，格式为{"next": "<路口ID>","from_dir": "<当前路口方向>","to_dir": "<下一个路口方向>","length": <道路长度>,"speed": <道路速度>}
            pre_cross (Dict[str, Any]): 上一个路口字典，格式与next_cross相同
        """
        self.id:str = id
        self.points:List[Point] = points
        self.edges:List[Edge] = edges
        self.dir_edges:Dict[str, Dict[str, Edge]] = dir_edges
        self.dir_points:Dict[str, Point] = dir_points
        self.next_cross:Dict[str, Any] = None
        self.pre_cross:Dict[str, Any] = None
        self.traffic_light:TrafficLightPlan = traffic_light

    def get_dir_edges(self, dir: str) -> Dict[str, Edge]:
        """
        获取指定方向上的入边和出边
        
        Args:
            dir (str): 方向（1-4）
        
        Returns:
            Dict[str, Edge]: 包含"in"和"out"键的字典，值为对应方向上的入边和出边对象
        """
        return self.dir_edges[dir]
    

    def set_next_cross(self, next_cross: Dict[str, Any]):
        """
        设置下一个路口
        
        Args:
            next_cross (Dict[str, Any]): 下一个路口字典，格式为{"next": "<路口ID>","from_dir": "<当前路口方向>","to_dir": "<下一个路口方向>","length": <道路长度>,"speed": <道路速度>}
        """
        self.next_cross = next_cross
    
    def set_pre_cross(self, pre_cross: Dict[str, Any]):
        """
        设置上一个路口
        
        Args:
            pre_cross (Dict[str, Any]): 上一个路口字典，格式与next_cross相同
        """
        self.pre_cross = pre_cross
    
    def get_point_by_id(self, id: str) -> Point:
        """
        根据ID获取路口周边的过渡点
        
        Args:
            id (str): 过渡点ID
        
        Returns:
            Point: 对应的过渡点对象，如果不存在则返回None
        """
        for point in self.points:
            if point.id == id:
                return point
        return None
    
    def get_next_cross_by_dir(self, dir: str) -> Dict[str, Any]:
        """
        根据当前方向获取下一个路口
        
        Args:
            dir (str): 当前方向（1-4）
        
        Returns:
            Dict[str, Any]: 下一个路口字典，格式与next_cross相同，如果不存在则返回None
        """
        if self.next_cross is not None:
            if self.next_cross['from_dir'] == dir:
                return self.next_cross
        if self.pre_cross is not None:
            if self.pre_cross['from_dir'] == dir:
                return self.pre_cross
        
        return None

    def get_coordinate_dir(self)->Tuple[str, str]:
        """
        获取当前路口的坐标方向
        
        Returns:
            Tuple[str, str]: 包含入方向和出方向的元组，每个方向为1-4
        """
        coordinate_dir = {
            '1': '3',
            '2': '4',
            '3': '1',
            '4': '2',
        }
        in_dir = None
        out_dir = None
        if self.next_cross is not None:
            out_dir = self.next_cross['to_dir']
        
        if self.pre_cross is not None:
            in_dir = self.pre_cross['from_dir']

        if self.next_cross is None and in_dir is not None:
            out_dir = coordinate_dir[in_dir]
        
        if self.pre_cross is None and out_dir is not None:
            in_dir = coordinate_dir[out_dir]

        return in_dir, out_dir
        
        

    def to_json(self) -> Dict[str, Any]:
        """
        转换为JSON格式的路口定义
        
        Returns:
            Dict[str, Any]: JSON格式的路口字典，包含路口ID、周边过渡点、道路边、方向上的过渡点和边、下一个路口、上一个路口和信控方案
        """
        next_cross_json = {} if self.next_cross is None else {
            'next': self.next_cross['next'].id,
            'from_dir': self.next_cross['from_dir'],
            'to_dir': self.next_cross['to_dir'],
            'length': self.next_cross['length'],
            'speed': self.next_cross['speed']
        }
        pre_cross_json = {} if self.pre_cross is None else {
            'pre': self.pre_cross['pre'].id,
            'from_dir': self.pre_cross['from_dir'],
            'to_dir': self.pre_cross['to_dir'],
            'length': self.pre_cross['length'],
            'speed': self.pre_cross['speed']
        }

        return {
            "id": self.id,
            "points": [p.to_json() for p in self.points],
            "edges": [e.to_json() for e in self.edges],
            "dir_points": {k: v.to_json() for k, v in self.dir_points.items()},
            "dir_edges": {k: {k1: v1.to_json() for k1, v1 in v.items()} for k, v in self.dir_edges.items()},
            "next_cross": next_cross_json,
            "pre_cross": pre_cross_json,
            "traffic_light": self.traffic_light.to_json()
        }


# ----------------------------------------------------------------------------
# 原文件: algorithms\bandwidth_algorithm\flex_band_optimization.py
# ----------------------------------------------------------------------------



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

# ----------------------------------------------------------------------------
# 原文件: config\parser.py
# ----------------------------------------------------------------------------

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置解析器模块
用于解析路口信息、车速、流量等配置信息
"""

import re
from typing import Dict, Any


class ConfigParser:
    """配置解析器类"""
    
    def __init__(self, config_data: Dict[str, Any]):
        """
        初始化配置解析器
        
        Args:
            config_data: 包含crossList, crossInfo, greenSpeed, flow等字段的配置数据
        """
        self.cross_list = config_data.get('crossList', [])
        self.cross_info = config_data.get('crossInfo', '')
        self.planInfo = config_data.get('planInfo', '')
        
        # 解析后的数据存储
        self.crosses = {}  # 路口信息

        # 交叉口的方案信息
        self.cross_plan_infos = self._parse_plan_infos()
        
    def parse(self) -> Dict[str, Any]:
        """
        解析所有配置信息
        
        Returns:
            解析后的配置信息字典
        """
        # 解析路口信息
        self._parse_cross_info()
        
        return {
            'cross_list': self.cross_list,
            'crosses': self.crosses
        }

    def _parse_plan_infos(self):
        """解析计划信息"""
        cross_plan_infos = {}
        # 按照$分割各个计划的信息
        for cross_id, plan_info in self.planInfo.items():
            phases = []
            durations = {}
            offset = 0
            coordination_phase = ''
            
            # 按照;分割计划信息
            parts = plan_info.split(',')
            if len(parts) < 2:
                continue

            # 按照,分割定时信息和协调相位信息
            parts = plan_info.split(',')
            timing_info = parts[0]  # 定时信息
            coordination_info = parts[1] if len(parts) > 1 else ''  # 协调相位信息
            
            # 解析定时信息 (格式如: A44B26C34D26)
            if timing_info:
                # 使用正则表达式匹配相位名和时长
                # 匹配相位名(字母)和时长(数字)的组合
                pattern = r'([A-Z])(\d+)'
                matches = re.findall(pattern, timing_info)
                
                for phase_name, duration in matches:
                    phases.append(phase_name)
                    durations[phase_name] = int(duration)
            
            # 解析协调相位信息 (格式如: A3)
            if coordination_info:
                # 第一个字符是协调相位
                if len(coordination_info) >= 1:
                    coordination_phase = coordination_info[0]
                
                # 剩余字符是绝对相位差
                if len(coordination_info) > 1:
                    try:
                        offset = int(coordination_info[1:])
                    except ValueError:
                        # 如果无法转换为整数，保持默认值0
                        pass
            if cross_id not in cross_plan_infos:
                cross_plan_infos[cross_id] = {}
            cross_plan_infos[cross_id]['phases'] = phases
            cross_plan_infos[cross_id]['durations'] = durations
            cross_plan_infos[cross_id]['offset'] = offset
            cross_plan_infos[cross_id]['coordination_phase'] = coordination_phase
        return cross_plan_infos

    def _get_coordinate_direction(self, cross_id):
        """获取每个路口协调的进口道方向"""

        cross_coordination_phase = self.cross_plan_infos[cross_id]['coordination_phase']
        parts = self.cross_info[cross_id].split(';')
        phase_info = parts[1]  # 相位信息
        phase_direction_turn = self._parse_phase_functions(phase_info)

        # 获取正向/反向协调相位对应的方向
        coordinate_directions = list(phase_direction_turn[cross_coordination_phase].keys())

        # 南北方向，以及东西方向
        north_south, west_east = [DEFAULT_DIRECTIONS[0], DEFAULT_DIRECTIONS[2]], [DEFAULT_DIRECTIONS[3], DEFAULT_DIRECTIONS[1]]
        # 去重并排序
        reverse = True if set(west_east) & set(coordinate_directions) else False
        coordinate_directions = west_east if reverse else north_south
        forward_directions = sorted(list(set(coordinate_directions)), reverse=reverse)
        backward_directions = sorted(list(set(coordinate_directions)), reverse=not reverse)

        forward_direction, backward_direction = forward_directions[0], backward_directions[0]

        # 判断进口道是否存在
        if forward_direction not in self.crosses[cross_id].dir_edges:
            forward_direction = None
        if backward_direction not in self.crosses[cross_id].dir_edges:
            backward_direction = None
        return forward_direction, backward_direction

    def _get_coordinate_stages(self, cross_id, coordinate_direction):
        """获取每个路口的正方向/反方向的协调相位列表"""
        forward_stages, backward_stages = [], []
        stage_dir_turn = self.crosses[cross_id].traffic_light.functions

        # 根据协调方向和转向，匹配出协调的相位名列表
        forward_direction, backward_direction = coordinate_direction['forward']['direction'], coordinate_direction['backward']['direction']
        forward_turn, backward_turn = coordinate_direction['forward']['turn'], coordinate_direction['backward']['turn']
        for stage_name, dir_turn_info in stage_dir_turn.items():
            for dir, turns in dir_turn_info.items():
                if forward_direction == dir and forward_turn in turns:
                    forward_stages.append(stage_name)
                if backward_direction == dir and backward_turn in turns:
                    backward_stages.append(stage_name)

        # 如果协调转向为不受控右转时，添加整个协调相位名称
        if not forward_stages and forward_turn == 'r':
            forward_stages.extend(stage_dir_turn.keys())
        if not backward_stages and backward_turn == 'r':
            backward_stages.extend(stage_dir_turn.keys())
        coordinate_direction['forward']['stages'] = forward_stages
        coordinate_direction['backward']['stages'] = backward_stages
        return coordinate_direction

    def _get_coordinate_turn(self, cross_id, direction):
        """获取协调方向的转向"""

        parts = self.cross_info[cross_id].split(';')
        phase_info = parts[1]  # 相位信息
        phase_direction_turn = self._parse_phase_functions(phase_info)

        cross_coordination_phase = self.cross_plan_infos[cross_id]['coordination_phase']
        turn = 's'
        if direction in phase_direction_turn[cross_coordination_phase]:
            turn = phase_direction_turn[cross_coordination_phase][direction][0]
        else:
            for dir_turn in phase_direction_turn.values():
                if direction in dir_turn and dir_turn[direction]:
                    turn = dir_turn[direction][0]
                    break
        return turn

    def get_coordinate_direction_info(self, cross_id):
        """修正每个路口正向协调相位和反向协调相位对应的进口道方向和转向"""

        forward_direction, backward_direction = self._get_coordinate_direction(cross_id)

        # 获取单独的正向或反向，以及关联的灯组转向
        if forward_direction:
            # 获取正向协调的转向
            forward_turn = self._get_coordinate_turn(cross_id, forward_direction)

            if backward_direction:
                # 获取反向协调的灯组转向
                backward_turn = self._get_coordinate_turn(cross_id, backward_direction)
            else:
                # 缺失反向进口道时，改为正向左转出去的路段，通过右转进入反向路段
                forward_index = DEFAULT_DIRECTIONS.index(forward_direction)
                # 正向左转到达的上游路段
                backward_direction = DEFAULT_DIRECTIONS[(forward_index + 1) % 4]
                backward_turn = 'r'
        else:
            backward_turn = self._get_coordinate_turn(cross_id, backward_direction)
            # 缺失正向进口道时，改为反向左转出去的路段，通过右转进入正向路段
            backward_index = DEFAULT_DIRECTIONS.index(backward_direction)
            forward_direction = DEFAULT_DIRECTIONS[(backward_index + 1) % 4]
            forward_turn = 'r'

        coordinate_direction_info = {'forward': {'direction': forward_direction, 'turn': forward_turn},
                                'backward': {'direction': backward_direction, 'turn': backward_turn}}
        # 更新协调相位的信息
        coordinate_direction_info = self._get_coordinate_stages(cross_id, coordinate_direction_info)
        return coordinate_direction_info

    def _parse_cross_info(self):
        """解析路口信息"""
        for cross_id in self.cross_list:
            # 按照;分割路口渠化信息、相位信息
            parts = self.cross_info[cross_id].split(';')
            # 确保至少有渠道化信息和相位信息
            if len(parts) < 2:
                continue
            channelization_info = parts[0]  # 渠化信息
            phase_info = parts[1]           # 相位信息
        
            # 解析路口静态信息
            points, dir_points, edges, dir_edges = self._parse_cross(cross_id, channelization_info)
            
            # 解析信号灯信息
            # 获取当前路口的信号灯方案信息
            cross_signal_info = self.cross_plan_infos.get(cross_id, {})
            # 生成信控方案对象
            tls_plan = self._parse_tsl_plan(cross_id, cross_signal_info, phase_info)
            # 生成当前路口对象
            cur_cross = Cross(cross_id, points, edges, dir_points, dir_edges, tls_plan)
            # 存储路口信息
            self.crosses[cross_id] = cur_cross

    def _parse_cross(self, cross_id, channelization_info):
        """解析渠化信息"""
        # 解析渠化信息
        edges = []
        dir_edges = {}
        points = []
        dir_points = {}

        # 当前路口本身
        cross_point = Point(cross_id, '0')
        points.append(cross_point)
        dir_points['0'] = cross_point

        if channelization_info:
            # 按照|分割各个方向的信息
            directions = channelization_info.split('|')
            for direction in directions:
                # 每个方向的信息用逗号分割，分别是方向ID、车道转向字符串和出口道数
                if ',' not in direction:
                    continue
                # 解析方向ID、车道转向字符串和出口道数
                dir_id, turn_str, out_count = direction.split(',')
                # 跳过没有入口道的方向
                if turn_str == '' or turn_str == '0':
                    continue
                # 为避免进口道单车道转向的不完整，将单车道默认置为左直右
                if len(turn_str) == 1:
                    turn_str = '7'
                out_count = '1' if out_count == '' or out_count == '0' else out_count
                # 设置是否有入口道和出口道
                in_allow = turn_str != ''
                out_allow = out_count != '' and out_count != '0'

                # 设置该方向的虚拟过渡点
                dir_point = Point(cross_id, dir_id)
                # 添加该方向的虚拟过渡点和方向ID到字典中
                points.append(dir_point)
                dir_points[dir_id] = dir_point

                # 解析入口道
                if in_allow:
                    # 获取入口道的起始点和终止点
                    from_point_id = dir_point.get_id()
                    to_point_id = cross_point.get_id()
                    # 生成入口道的Edge对象
                    in_edge = Edge(from_point_id, to_point_id, 0, 0, 0)
                    # 根据车道转向获取车道信息
                    in_lanes = self._parse_lane_info(turn_str, in_edge.get_id())
                    in_edge.set_lanes(in_lanes)
                    edges.append(in_edge)
                    # 设置dir_edges的入口道
                    if dir_id not in dir_edges:
                        dir_edges[dir_id] = {}
                    dir_edges[dir_id]['in'] = in_edge
                # 解析出口道
                if out_allow:
                    from_point_id = cross_point.get_id()
                    to_point_id = dir_point.get_id()
                    # 生成出口道的Edge对象
                    out_edge = Edge(from_point_id, to_point_id, 0, 0, 0)
                    out_edge_id = out_edge.get_id()
                    # 根据出口道数生成出口道的车道
                    out_lanes = []
                    for i in range(int(out_count) if out_count else 0):
                        cur_lane = Lane(out_edge_id, i, 0, 0, ['s'])
                        out_lanes.append(cur_lane)
                    out_edge.set_lanes(out_lanes)
                    edges.append(out_edge)
                    # 设置dir_edges的出口道
                    if dir_id not in dir_edges:
                        dir_edges[dir_id] = {}
                    dir_edges[dir_id]['out'] = out_edge

        return points, dir_points, edges, dir_edges

    def _parse_lane_info(self, turn_str, eid):
        """解析转向字符串"""
        # 解析转向字符串
        lanes = []
        if turn_str:
            # 十六进制字符格式：每个字符代表一个车道，每个字符的4位二进制从高位到低位分别代表掉头、左转、直行、右转
            for i, char in enumerate(turn_str[::-1]):
                try:
                    # 通过位运算判断车道的转向功能
                    lane_turns = self._parse_turn_list(char)       
                    cur_lane = Lane(eid, i, 0, 0, lane_turns)
                    lanes.append(cur_lane)
                except ValueError:
                    # 如果不是有效的十六进制字符，跳过
                    continue
        return lanes
        
    def _parse_turn_list(self, turn_char):
        """解析转向列表"""
        # 解析转向列表
        turns = []
        if turn_char:
            # 将十六进制字符转换为整数
            hex_value = int(turn_char, 16)
            
            # 定义转向的二进制模式
            uturn_mask = 0b1000    # 8
            left_mask = 0b0100     # 4
            straight_mask = 0b0010  # 2
            right_mask = 0b0001    # 1
            
            # 通过位运算判断车道的转向功能
            turns = []
            if hex_value & straight_mask:
                turns.append("s")
            if hex_value & left_mask:
                turns.append("l")
            if hex_value & right_mask:
                turns.append("r")
            if hex_value & uturn_mask:
                turns.append("t")
        return turns

    def _parse_phase_functions(self, phase_info):
        """解析相位信息"""
        functions = {}
        if phase_info:
            for phase in phase_info.split('|'):
                # 解析格式如"A1431"的相位字符串
                # A为phaseNo，14表示道路标号为1转向字符为4，31表示道路标号为3转向字符为1
                phase_no = None
                if len(phase) >= 3:  # 至少要有phaseNo和一对道路转向信息
                    # 第一个字符是phaseNo
                    phase_no = phase[0]
                if phase_no is None:
                    continue

                # 剩余部分按两位一组解析
                remaining = phase[1:]
                
                # 每两个字符为一组，分别表示道路标号和转向字符
                for i in range(0, len(remaining), 2):
                    if i + 1 < len(remaining):
                        road_code = remaining[i]
                        turn_char = remaining[i + 1]
                        turns = self._parse_turn_list(turn_char)
                        if phase_no not in functions:
                            functions[phase_no] = {}
                        functions[phase_no][road_code] = turns

        return functions
    
    def _parse_tsl_plan(self, cross_id, signal_info, phase_info):
        """解析信号灯信息"""
        # 解析相位运行的转向信息
        functions = self._parse_phase_functions(phase_info)
        # 直接获取信号灯的相位、持续时间、偏移量、协调相位
        phases = signal_info['phases']
        durations = signal_info['durations']
        offset = signal_info['offset']
        coordination_phase = signal_info['coordination_phase']
        # 生成TrafficLightPlan对象
        tl_plan = TrafficLightPlan(cross_id, phases, durations, functions, offset, coordination_phase)
        
        return tl_plan


# ----------------------------------------------------------------------------
# 原文件: utils\util.py
# ----------------------------------------------------------------------------

import time
from functools import wraps
import re
import threading
import json
import sys



def timer(func):
    """简单的计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        log.info(f"🕒 {func.__name__} 耗时: {end - start:.2f} 秒")
        return result
    return wrapper


def find_min_ratio_best_iteration(data):
    """找出最小停车率下等待时间最小的迭代"""
    if not data:
        return None

    # 找出最小停车率
    min_ratio = min(item['avg_waiting_ratio'] for item in data)

    # 找出所有具有最小停车率的迭代
    min_ratio_items = [item for item in data if item['avg_waiting_ratio'] == min_ratio]

    # 在这些迭代中找出等待时间最小的
    best_item = min(min_ratio_items, key=lambda x: x['waiting_time'])

    return best_item


def find_max_speed_best_iteration(data):
    """找出最大速度下停车率最小的迭代"""
    if not data:
        return None

    # 找出最大速度
    max_speed = max(item['avg_speed'] for item in data)

    # 找出所有具有最大速度的迭代
    max_speed_items = [item for item in data if item['avg_speed'] == max_speed]

    # 在这些迭代中找出停车率最小的
    best_item = min(max_speed_items, key=lambda x: x['avg_waiting_ratio'])

    return best_item


def find_min_traveltime_best_iteration(data):
    """找出最小行程时间下停车率最小的迭代"""
    if not data:
        return None

    # 找出最小行程时间
    min_traveltime = min(item['avg_travel_time'] for item in data)

    # 找出所有具有最小行程时间的迭代
    min_traveltime_items = [item for item in data if item['avg_travel_time'] == min_traveltime]

    # 在这些迭代中找出停车率最小的
    best_item = min(min_traveltime_items, key=lambda x: x['avg_waiting_ratio'])

    return best_item


def get_cycles(input_data):
    """获取各路口的周期时长"""
    cross_list = input_data['crossList']
    crosses_plan = input_data['planInfo']
    cycles = []
    for index, cross_id in enumerate(cross_list):
        cross_plan_str = crosses_plan[cross_id]
        cross_stages_length = get_plan_info(cross_plan_str)
        cycle = sum([stage['length'] for stage in cross_stages_length])
        cycles.append(cycle)
    return cycles


def get_green_ratios(input_data):
    """提取绿信比信息"""
    cfg_parser = ConfigParser(input_data)
    cfg_parser.parse()

    # 反向绿信比
    backward_greens = []
    # 正向绿信比
    forward_greens = []

    crosses_plan = cfg_parser.planInfo
    for index, cross_id in enumerate(cfg_parser.cross_list):
        backward_green = []
        forward_green = []

        coordinate_direction = cfg_parser.get_coordinate_direction_info(cross_id)
        backward_stages = coordinate_direction['backward']['stages']
        forward_stages = coordinate_direction['forward']['stages']

        cross_plan_str = crosses_plan[cross_id]
        cross_stages_length = get_plan_info(cross_plan_str)
        cycle = sum([stage['length'] for stage in cross_stages_length])

        for stage in cross_stages_length:
            _stage = stage.get('stage')
            for coor_stage in backward_stages:
                if _stage == coor_stage:
                    backward_green.append(stage.get('length') / cycle)
            for coor_stage in forward_stages:
                if _stage == coor_stage:
                    forward_green.append(stage.get('length') / cycle)

        backward_coor_green = sum(backward_green)
        forward_coor_green = sum(forward_green)

        backward_greens.append(backward_coor_green)
        forward_greens.append(forward_coor_green)
    return backward_greens, forward_greens


def get_plan_info(plan_str):
    """解析方案"""
    pattern = r'([A-Za-z])(\d+)'
    matches = re.findall(pattern, plan_str.split(',')[0])

    # 将每个匹配项转换为一个字典，并存入方案信息表中
    plan_info = [{'stage':k, 'length': int(v)} for k, v in matches]
    return plan_info


def update_plan_info(plan_str, common_cycle, cycle_multiple=1):
    """根据周期时长，同步放大相位时长"""
    current_plan = get_plan_info(plan_str)
    current_cycle = sum([stage['length'] for stage in current_plan])
    if common_cycle / cycle_multiple != current_cycle:
        expected_cycle = common_cycle / cycle_multiple
        ratio = expected_cycle / current_cycle
        stages_length = []
        for stage in current_plan:
            stages_length.append(stage['length'] * ratio)
        adjusted_stages_length = adjust_green_duration(stages_length, expected_cycle)

        # 重新拼接相位时长
        adjusted_plan_str = ''
        for index, stage in enumerate(current_plan):
            adjusted_plan_str += '{}{}'.format(stage['stage'], round(adjusted_stages_length[index]))

        plans = plan_str.split(',')
        plans[0] = adjusted_plan_str
        return ','.join(plans)
    else:
        return plan_str


def adjust_green_duration(stage_duration_list, cycle):
    """调整绿灯时长或者绿信比，保证绿灯时长之和等于周期时长，绿信比之和等于100。暂时累加到第一个相位上"""
    stage_duration_list = [round(stage_duration) for stage_duration in stage_duration_list]
    delta = cycle - sum(stage_duration_list)
    i = 0
    while i < len(stage_duration_list):
        if stage_duration_list[i] + delta > 0:
            stage_duration_list[i] += delta
            break
        i += 1
    return stage_duration_list


def replace_offset_value(plan_str, new_offset):
    """替换路口的协调相位差"""
    parts = plan_str.split(',')
    if len(parts) == 2:
        # 替换相位差
        offset_str = parts[1][0] + str(new_offset)
        parts[1] = offset_str
        new_plan_str = ','.join(parts)
    else:
        new_plan_str = plan_str
    return new_plan_str


class HeartbeatManager:
    """
    心跳管理器，用于在长时间运行的任务中发送心跳消息以保持连接活跃
    """
    
    def __init__(self, interval=1):
        """
        初始化心跳管理器
        :param interval: 心跳间隔（秒）
        """
        self.interval = interval
        self.heartbeat_thread = None
        self.stop_event = threading.Event()
    
    def _send_heartbeat(self):
        """
        发送心跳消息的内部方法
        """
        while not self.stop_event.is_set():
            # 发送心跳消息
            heartbeat_msg = {
                'event': 'heartbeat',
                'result': 'alive'
            }
            print(json.dumps(heartbeat_msg, cls=NpEncoder, ensure_ascii=False))
            sys.stdout.flush()
            # 等待指定间隔或直到停止信号
            self.stop_event.wait(self.interval)
    
    def start(self):
        """
        启动心跳线程
        """
        if self.heartbeat_thread is not None and self.heartbeat_thread.is_alive():
            # 如果已有心跳线程在运行，则先停止它
            self.stop()
        
        self.stop_event.clear()
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
    
    def stop(self):
        """
        停止心跳线程
        """
        self.stop_event.set()
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.stop()


# ----------------------------------------------------------------------------
# 原文件: config\protocol_output.py
# ----------------------------------------------------------------------------



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


# ----------------------------------------------------------------------------
# 原文件: algorithms\bandwidth_algorithm\run_band_algorithm.py
# ----------------------------------------------------------------------------

import json
import itertools
import multiprocessing
import os
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, as_completed




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


# ----------------------------------------------------------------------------
# 原文件: algorithms\genetic_algorithm\GA.py
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# 原文件: algorithms\genetic_algorithm\run_GA.py
# ----------------------------------------------------------------------------

import json
import random
from collections import OrderedDict

import numpy as np
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.operators.crossover.expx import ExponentialCrossover



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


# ----------------------------------------------------------------------------
# 原文件: main.py
# ----------------------------------------------------------------------------

import json
import re
import sys
import os
import traceback
from collections import OrderedDict



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
