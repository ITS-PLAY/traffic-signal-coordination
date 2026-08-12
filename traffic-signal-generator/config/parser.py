#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置解析器模块
用于解析路口信息、车速、流量等配置信息
"""

import re
from typing import Dict, Any

from core.point import Point
from core.edge import Edge, Lane
from core.cross import Cross
from core.traffic_light import TrafficLightPlan
from common.common_vars import DEFAULT_DIRECTIONS

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
