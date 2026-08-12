import time
from functools import wraps
import re
import threading
import json
import sys

from utils.logger import log
from config.parser import ConfigParser
from utils.np_encoder import NpEncoder


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
