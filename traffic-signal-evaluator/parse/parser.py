#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置解析器模块
用于解析路口信息、车速、流量等配置信息
"""

import json
import re
from typing import Dict, List, Any, Tuple
import math
import collections

from core.point import Point
from core.edge import Edge, Lane
from core.cross import Cross
from core.traffic_light import TrafficLightPlan
from core.route import Route, Flow, Routes, ReRoute, ReRouters
from constants.constants import TRANSITION_EDGE_LENGTH, TRANSITION_EDGE_SPEED, DEFAULT_FLOW_BEGIN_TIME, DEFAULT_DIRECTIONS, DEFAULT_LANE_FLOW, FLOW_TIME_INTERVAL, DEFAULT_FLOW_WINDOWS, TURN_MAP_NUM, DEFAULT_VEH_TYPE, DEFAULT_MIN_SPEED_KMH, COOR_DEFAULT_FLOW_BEGIN_TIME, TRANSITION_DISTANCE
from utils.util import get_target_direction


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
        self.green_speed = config_data.get('roadSpeed', [[], []])
        self.flow = config_data.get('crossFlow', '')
        self.planInfo = config_data.get('planInfo', '')
        self.road_length = config_data.get('roadLength', [])
        
        # 解析后的数据存储
        self.crosses = {}  # 路口信息
        self.transition_edges = {}  # 过渡边信息
        self.coor_routes: Routes = None # 协调方向的路由
        self.routes: Routes = None # 路由流量信息
        self.reroutes = None      # 重新路由信息
        self.cross_turn_ratio = {} # 交叉口进口道转向比

        # 交叉口间各路段的映射ID
        self.road_map_id = {"forward": {}, "backward": {}}
        # 交叉口间各路段的长度
        self.road_length_dict = {}
        # 交叉口间路段包含的出口、连接段、渠化段信息
        self.road_section_info = collections.defaultdict(list)
        # 交叉口的方案信息
        self.cross_plan_infos = self._parse_plan_infos()
        self.max_sim_time = 0
        # 协调道路信息
        self.coor_road_id = self._get_coor_road()
        
    def parse(self) -> Dict[str, Any]:
        """
        解析所有配置信息
        
        Returns:
            解析后的配置信息字典
        """
        # 解析路口信息
        self._parse_cross_info()
        self._calculate_sim_time()
        self._parse_turn_routes()
        self._parse_coor_routes()
        
        return {
            'cross_list': self.cross_list,
            'crosses': self.crosses,
            'transition_edges': self.transition_edges,
            'routes': self.routes,
            'reroutes': self.reroutes,
            'road_length': self.road_length,
            'max_sim_time': self.max_sim_time,
            'road_section_info': self.road_section_info
        }

    def _get_coor_road(self):
        """获取正向和反向 从起点到终点的道路编号"""
        coor_road_id = ['{}{}'.format(self.cross_list[0], self.cross_list[-1]),
                        '{}{}'.format(self.cross_list[-1], self.cross_list[0])]
        return coor_road_id

    def _calculate_sim_time(self):
        cycles = []
        for cross_id in self.cross_list:
            cross_info = self.crosses.get(cross_id)
            cycles.append(cross_info.traffic_light.cycle)
        max_sim_time = math.ceil(sum(self.road_length)/(DEFAULT_MIN_SPEED_KMH/3.6) + (len(cycles) + 1) * max(cycles))
        self.max_sim_time = DEFAULT_FLOW_WINDOWS + max_sim_time

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

    def _get_coordinate_direction_info(self, cross_id):
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
        relative_abs_offset = 0
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
            relative_abs_offset += tls_plan.offset
            tls_plan.relative_abs_offset = relative_abs_offset
            tls_plan.calculate_abs_offset()
            # 生成当前路口对象
            cur_cross = Cross(cross_id, points, edges, dir_points, dir_edges, tls_plan)
            # 存储路口信息
            self.crosses[cross_id] = cur_cross
        
        # 解析路口的连接关系
        # 路口间过渡路段列表
        transition_edges = []
        # 路口间过渡路段字典，键为路口ID，值为该路口的不同方向的过渡路段
        dir_transition_edges = {}
        idx = 0
        # 路段列表的元素为：from_node-to_node，如：C1_3-C2_1
        for index in range(len(self.cross_list)-1):
            from_cross = self.cross_list[index]
            coordinate_direction = self._get_coordinate_direction_info(from_cross)
            from_dir = coordinate_direction['backward']['direction']
            to_cross = self.cross_list[index + 1]
            coordinate_direction = self._get_coordinate_direction_info(to_cross)
            to_dir = coordinate_direction['forward']['direction']
            
            # 根据输入参数中的路段速度，计算过渡路段的速度
            from_edge_speed = self.green_speed[0][idx]/3.6 if len(self.green_speed) > 0 and idx < len(self.green_speed[0]) else TRANSITION_EDGE_SPEED/3.6
            to_edge_speed = self.green_speed[1][idx]/3.6 if len(self.green_speed) > 1 and idx < len(self.green_speed[1]) else from_edge_speed
            # 根据输入参数中的路段长度，计算过渡路段的长度
            from_edge_length = self.road_length[idx]
            to_edge_length = from_edge_length
            
            # 更新cross的邻居节点
            # 更新协调方向的下一个路口
            next_cross = {
                'next': self.crosses[to_cross],
                'from_dir': from_dir,
                'to_dir': to_dir,
                'length': from_edge_length,
                'speed': from_edge_speed
            }
            # 更新协调方向反向的下一个路口
            pre_cross = {
                'pre': self.crosses[from_cross],
                'from_dir': to_dir,
                'to_dir': from_dir,
                'length': from_edge_length,
                'speed': to_edge_speed
            }
            self.crosses[from_cross].set_next_cross(next_cross)
            # 更新协调道路上的边的车速
            self.crosses[from_cross].dir_edges[from_dir]['out'].set_speed(from_edge_speed)
            self.crosses[to_cross].dir_edges[to_dir]['in'].set_speed(from_edge_speed)
        
            self.crosses[to_cross].set_pre_cross(pre_cross)
            # 更新协调道路上的边的车速
            self.crosses[from_cross].dir_edges[from_dir]['in'].set_speed(to_edge_speed)
            self.crosses[to_cross].dir_edges[to_dir]['out'].set_speed(to_edge_speed)

            # 创建两个路口间的过渡边
            # 获取过渡边的起始点和终止点
            from_transition_point = self.crosses[from_cross].dir_points[from_dir]
            to_transition_point = self.crosses[to_cross].dir_points[to_dir]
            # 过渡边的长度需要用原始路段长度减去路口内过渡路段的长度
            from_transition_edge_length = from_edge_length - 2 * TRANSITION_EDGE_LENGTH
            to_transition_edge_length = to_edge_length - 2 * TRANSITION_EDGE_LENGTH
            # 生成Edge对象
            from_transition_edge = Edge(from_transition_point.id, to_transition_point.id, from_transition_edge_length, from_edge_speed, 1)
            # 根据车道数生成过渡边的车道
            from_lane_num = self.crosses[from_cross].dir_edges[from_dir]['out'].lane_num
            from_lanes = self._gen_lanes_by_cnt(from_transition_edge.get_id(), from_transition_edge_length, from_edge_speed, from_lane_num)
            from_transition_edge.set_lanes(from_lanes)
            # 定义正向交叉口间的路段
            road_between_crosses = '{}{}'.format(from_cross, to_cross)
            self.road_map_id['forward'][self.crosses[from_cross].dir_edges[from_dir]['out'].id] = road_between_crosses
            self.road_map_id['forward'][self.crosses[to_cross].dir_edges[to_dir]['in'].id] = road_between_crosses
            self.road_map_id['forward'][from_transition_edge.id] = road_between_crosses
            self.road_length_dict[road_between_crosses] = self.road_length[index]

            # 正向交叉口间路段包含的出口段、连接段、渠化段
            self.road_section_info[road_between_crosses].append(self.crosses[from_cross].dir_edges[from_dir]['out'].id)
            self.road_section_info[road_between_crosses].append(from_transition_edge.id)
            self.road_section_info[road_between_crosses].append(self.crosses[to_cross].dir_edges[to_dir]['in'].id)

            # 生成Edge对象
            to_transition_edge = Edge(to_transition_point.id, from_transition_point.id, to_transition_edge_length, to_edge_speed, 1)
            # 根据车道数生成过渡边的车道
            to_lane_num = self.crosses[to_cross].dir_edges[to_dir]['out'].lane_num
            to_lanes = self._gen_lanes_by_cnt(to_transition_edge.get_id(), to_transition_edge_length, to_edge_speed, to_lane_num)
            to_transition_edge.set_lanes(to_lanes)
            # 定义反向交叉口间的路段
            road_between_crosses = '{}{}'.format(to_cross, from_cross)
            self.road_map_id['backward'][self.crosses[to_cross].dir_edges[to_dir]['out'].id] = road_between_crosses
            self.road_map_id['backward'][self.crosses[from_cross].dir_edges[from_dir]['in'].id] = road_between_crosses
            self.road_map_id['backward'][to_transition_edge.id] = road_between_crosses
            self.road_length_dict[road_between_crosses] = self.road_length[index]

            # 反向交叉口间路段包含的出口段、连接段、渠化段
            self.road_section_info[road_between_crosses].append(self.crosses[to_cross].dir_edges[to_dir]['out'].id)
            self.road_section_info[road_between_crosses].append(to_transition_edge.id)
            self.road_section_info[road_between_crosses].append(self.crosses[from_cross].dir_edges[from_dir]['in'].id)

            # 添加过渡边
            transition_edges.append(from_transition_edge)
            transition_edges.append(to_transition_edge)
            
            # 更新dir_transition_edges
            if from_cross not in dir_transition_edges:
                dir_transition_edges[from_cross] = {}
            dir_transition_edges[from_cross][from_dir] = from_transition_edge
            if to_cross not in dir_transition_edges:
                dir_transition_edges[to_cross] = {}
            dir_transition_edges[to_cross][to_dir] = to_transition_edge
            idx += 1
        self.transition_edges = {
            'edges': transition_edges,
            'dir_edges': dir_transition_edges,
        }


    def _gen_lanes_by_cnt(self, eid, length, speed, cnt):
        # 过渡路段的车道默认都是直行，直接根据车道数生成
        lanes = [Lane(eid, i, length, speed, ['s']) for i in range(cnt)]
        
        return lanes


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
                if turn_str == '' or '0' in turn_str:
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
                    in_edge = Edge(from_point_id, to_point_id, TRANSITION_EDGE_LENGTH, TRANSITION_EDGE_SPEED, 0)
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
                    out_edge = Edge(from_point_id, to_point_id, TRANSITION_EDGE_LENGTH, TRANSITION_EDGE_SPEED, 0)
                    out_edge_id = out_edge.get_id()
                    # 根据出口道数生成出口道的车道
                    out_lanes = []
                    for i in range(int(out_count) if out_count else 0):
                        cur_lane = Lane(out_edge_id, i, TRANSITION_EDGE_LENGTH, TRANSITION_EDGE_SPEED, ['s'])
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
                    cur_lane = Lane(eid, i, TRANSITION_EDGE_LENGTH, TRANSITION_EDGE_SPEED, lane_turns)
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

    def search_available_flow(self, step=1):
        """获取协调方向的可用流量"""
        if step == 1:
            start, end = 1, len(self.cross_list)
            coor_dir = 'forward'
        else:
            start, end= len(self.cross_list)-2, -1
            coor_dir = 'backward'

        coordinate_direction = self._get_coordinate_direction_info(self.cross_list[start])
        lane_nums = self.get_turn_lane_nums(self.cross_list[start], coordinate_direction[coor_dir]['direction'],
                                            coordinate_direction[coor_dir]['turn'])
        lane_nums = max(lane_nums, 1)
        flow = 0
        for index in range(start, end, step):
            cross_id = self.cross_list[index]
            coordinate_direction = self._get_coordinate_direction_info(cross_id)
            direction = coordinate_direction[coor_dir]['direction']
            turn = TURN_MAP_NUM[coordinate_direction[coor_dir]['turn']]
            vehs = self.flow.get(self.cross_list[index], {}).get(direction+turn, None)
            if vehs is None:
                continue
            else:
                flow = vehs
                break
        return flow if flow > DEFAULT_LANE_FLOW * lane_nums else DEFAULT_LANE_FLOW * lane_nums

    def get_turn_lane_nums(self, cross_id, direction, turn):
        """获取路口某一进口道的转向车道数（包含混合车道）"""
        lane_nums = 0
        dir_edges = self.crosses[cross_id].dir_edges.get(direction, {}).get('in', None)
        if dir_edges is None:
            return lane_nums
        for lane in dir_edges.lanes:
            if turn in lane.turn:
                lane_nums += 1
        return lane_nums

    def _parse_coor_routes(self):
        turn_map = {'l': 1, 's': 2, 'r': -1, 't': 0}

        routes = []
        flows = []

        # 生成正向的路径
        forward_vehs = self.search_available_flow(step=1)
        forward_cross = self.cross_list[0]

        coordination_turn = self._get_coordinate_direction_info(forward_cross)
        backward_direction = coordination_turn['backward']['direction']
        backward_turn = coordination_turn['backward']['turn']
        back_direction_index = DEFAULT_DIRECTIONS.index(backward_direction)
        forward_start_direction = DEFAULT_DIRECTIONS[(back_direction_index + turn_map[backward_turn]) % 4]
        if forward_start_direction not in self.crosses[forward_cross].dir_edges:
            forward_start_direction = coordination_turn['forward']['direction']

        # 根据起始路口和方向获取路由边列表，路由默认由输入中设置的起始路口沿协调方向或者反方向到终点
        is_forward = True
        route_edges = self._get_route_edges(self.crosses[forward_cross], forward_start_direction, is_forward)
        # 生成路由对象
        route = Route(route_edges)
        routes.append(route)
        # 生成流量对象
        flow_prob = forward_vehs / FLOW_TIME_INTERVAL
        # 正向的头车流量加载开始时间
        begin_time = (self.crosses[forward_cross].traffic_light.relative_abs_offset - COOR_DEFAULT_FLOW_BEGIN_TIME) % self.crosses[forward_cross].traffic_light.cycle
        flow = Flow(route, DEFAULT_VEH_TYPE, begin_time, flow_prob, int(flow_prob * DEFAULT_FLOW_WINDOWS))
        flows.append(flow)

        # 生成反向的路径
        backward_vehs = self.search_available_flow(step=-1)
        backward_cross = self.cross_list[-1]

        coordination_turn = self._get_coordinate_direction_info(backward_cross)
        forward_direction = coordination_turn['forward']['direction']
        forward_turn = coordination_turn['forward']['turn']
        for_direction_index = DEFAULT_DIRECTIONS.index(forward_direction)
        backward_start_direction = DEFAULT_DIRECTIONS[(for_direction_index + turn_map[forward_turn]) % 4]
        if backward_start_direction not in self.crosses[backward_cross].dir_edges:
            backward_start_direction = coordination_turn['backward']['direction']

        # 根据起始路口和方向获取路由边列表，路由默认由输入中设置的起始路口沿协调方向或者反方向到终点
        is_forward = False
        route_edges = self._get_route_edges(self.crosses[backward_cross], backward_start_direction, is_forward)
        # 生成路由对象
        route = Route(route_edges)
        routes.append(route)
        # 生成流量对象
        flow_prob = backward_vehs / FLOW_TIME_INTERVAL
        # 反向的头车流量加载开始时间
        begin_time = (self.crosses[backward_cross].traffic_light.relative_abs_offset - COOR_DEFAULT_FLOW_BEGIN_TIME) % self.crosses[backward_cross].traffic_light.cycle
        flow = Flow(route, DEFAULT_VEH_TYPE, begin_time, flow_prob, int(flow_prob * DEFAULT_FLOW_WINDOWS))
        flows.append(flow)

        # 更新反向的终点路段和正向的终点路段
        routes[1].route_edges[-1] = self.crosses[forward_cross].dir_edges[forward_start_direction]['out'].id
        routes[0].route_edges[-1] = self.crosses[backward_cross].dir_edges[backward_start_direction]['out'].id

        # flow必须按照begin升序排列
        flows.sort(key=lambda x: x.begin)
        self.coor_routes = Routes(routes, flows)
        if not self.routes.routes:
            self.routes = self.coor_routes

    def _parse_routes(self):
        """解析交通流量信息"""

        routes = []
        flows = []

        for cross_id, flow_info in self.flow.items():
            # 解析流量信息
            for lane_turn, flow_value in flow_info.items():
                # 解析路口方向和转向字符
                dir, turn = lane_turn[0], lane_turn[1]

                # 获取路由流量起始路口信息
                start_cross = self.crosses[cross_id]
                # 判断是正向还是反向
                is_forward = True if cross_id == self.cross_list[0] else False
                # 根据起始路口和方向获取路由边列表，路由默认由输入中设置的起始路口沿协调方向或者反方向到终点
                route_edges = self._get_route_edges(start_cross, dir, is_forward)
                # 生成路由对象
                route = Route(route_edges)
                routes.append(route)
                # 生成流量对象
                flow_prob = flow_value / FLOW_TIME_INTERVAL
                flow = Flow(route, DEFAULT_VEH_TYPE, DEFAULT_FLOW_BEGIN_TIME, flow_prob, int(flow_prob * DEFAULT_FLOW_WINDOWS))
                flows.append(flow)

        self.routes = Routes(routes, flows)

    def _parse_turn_routes(self):
        """解析起终点，以及中间路口非协调方向上，每个转向的路径和流量"""
        self._get_turn_flow_ratio()

        routes = []
        flows = []
        reroutes = []

        for cross_id, flow_info in self.flow.items():
            # 解析流量信息
            for lane_turn, flow_value in flow_info.items():
                # 解析路口方向和转向字符
                dir, turn = lane_turn[0], lane_turn[1]

                turn_num_to_str = {value: key for key, value in TURN_MAP_NUM.items()}
                turn_lane_num = self.get_turn_lane_nums(cross_id, dir, turn_num_to_str.get(turn))
                if turn_lane_num == 0 or turn == '8':
                    continue

                # 获取路由流量起始路口信息
                start_cross = self.crosses[cross_id]
                coordination_turn = self._get_coordinate_direction_info(cross_id)
                # 正向起始路口，不加载反向进口道的流量
                if cross_id == self.cross_list[0] and dir != coordination_turn['backward']['direction']:
                    # 根据起始路口和方向获取路由边列表，路由默认由输入中设置的起始路口沿协调方向或者反方向到终点
                    route_edges = self._get_turn_edges(start_cross, dir, turn)
                    if not route_edges:
                        continue
                    # 生成路由对象
                    route = Route(route_edges)
                    routes.append(route)
                    # 生成流量对象
                    flow_prob = flow_value / FLOW_TIME_INTERVAL
                    flow = Flow(route, DEFAULT_VEH_TYPE, DEFAULT_FLOW_BEGIN_TIME, flow_prob, int(flow_prob * DEFAULT_FLOW_WINDOWS))
                    flows.append(flow)
                # 正向终点路口，不加载正向进口道的流量
                elif cross_id == self.cross_list[-1] and dir != coordination_turn['forward']['direction']:
                    route_edges = self._get_turn_edges(start_cross, dir, turn)
                    if not route_edges:
                        continue
                    # 生成路由对象
                    route = Route(route_edges)
                    routes.append(route)
                    # 生成流量对象
                    flow_prob = flow_value / FLOW_TIME_INTERVAL
                    flow = Flow(route, DEFAULT_VEH_TYPE, DEFAULT_FLOW_BEGIN_TIME, flow_prob, int(flow_prob * DEFAULT_FLOW_WINDOWS))
                    flows.append(flow)
                # 途径路口，不加载协调方向的流量
                elif dir != coordination_turn['forward']['direction'] and dir != coordination_turn['backward']['direction']:
                    route_edges = self._get_turn_edges(start_cross, dir, turn)
                    if not route_edges:
                        continue
                    # 生成路由对象
                    route = Route(route_edges)
                    routes.append(route)
                    # 生成流量对象
                    flow_prob = flow_value / FLOW_TIME_INTERVAL
                    flow = Flow(route, DEFAULT_VEH_TYPE, DEFAULT_FLOW_BEGIN_TIME, flow_prob, int(flow_prob * DEFAULT_FLOW_WINDOWS))
                    flows.append(flow)
                else:
                    route_edges = self._get_turn_edges(start_cross, dir, turn)
                    if not route_edges:
                        continue
                    dir_flow = sum(self.cross_turn_ratio[cross_id].get(dir, {}).values())
                    turn_ratio = flow_value / max(1, dir_flow)
                    reroute = ReRoute(route_edges[0], route_edges[1], turn_ratio)
                    reroutes.append(reroute)
                    for index in range(1, len(route_edges) - 1):
                        reroute = ReRoute(route_edges[index], route_edges[index + 1], 1.0)
                        reroutes.append(reroute)
        # flow必须按照begin升序排列
        flows.sort(key=lambda x: x.begin)
        self.routes = Routes(routes, flows)
        self.reroutes = ReRouters(reroutes, self.max_sim_time)


    def _get_turn_edges(self, cur_cross, start_dir, start_turn):
        edges = []
        # 获取起始边
        in_edge = cur_cross.dir_edges[start_dir]['in']
        out_dir = get_target_direction(start_dir, start_turn)
        if out_dir not in cur_cross.dir_edges:
            return edges

        edges.append(in_edge.get_id())
        # 顺着路由方向寻找出边
        out_edge = cur_cross.dir_edges[out_dir]['out']
        edges.append(out_edge.get_id())

        # 再寻找过渡节点的到下一个路口过渡节点的边
        if cur_cross.id in self.transition_edges['dir_edges'] and out_dir in self.transition_edges['dir_edges'][cur_cross.id]:
            transition_edge = self.transition_edges['dir_edges'][cur_cross.id][out_dir]
            edges.append(transition_edge.get_id())
            next_edge = transition_edge.get_id().split('-')[1]
            next_cross = next_edge.split('P')[0]
            edges.append('-'.join([next_edge, next_cross]))

        return edges


    def _get_route_edges(self, start_cross: Cross, start_dir: str, is_forward: bool=True) -> List[str]:
        """获取从start_cross到end_cross的所有边"""
        edges = []
        route_edge_length = 0
        # 起始路口
        cur_cross = start_cross
        # 起始路口方向
        cur_dir = start_dir
        while cur_cross is not None:
            # 获取起始边
            in_edge = cur_cross.dir_edges[cur_dir]['in']
            edges.append(in_edge.get_id())
            # 累加路由长度
            route_edge_length += in_edge.length
            # 根据路由方向，决定下一条边
            if (is_forward and cur_cross.next_cross is None) or (not is_forward and cur_cross.pre_cross is None):
                # 如果当前路口是路由方向的最后一个路口
                # 顺着路由方向寻找出边
                coordination_turn = self._get_coordinate_direction_info(cur_cross.id)
                if is_forward:
                    coor_dir = 'backward'
                else:
                    coor_dir = 'forward'
                out_dir = coordination_turn[coor_dir]['direction']
                # 获取协调方向的出边
                out_edge = cur_cross.dir_edges[out_dir]['out']
                # 累加路由长度
                route_edge_length += out_edge.length
                # 添加新边到路由列表
                edges.append(out_edge.get_id())
                cur_cross = None
            else:
                # 当前路口不是路由方向的最后一个路口
                # 顺着路由方向寻找出边
                cur_next_cross = cur_cross.next_cross if is_forward else cur_cross.pre_cross
                # 先寻找路口的到过渡节点的边
                out_dir = cur_next_cross['from_dir']
                next_in_dir = cur_next_cross['to_dir']
                out_edge = cur_cross.dir_edges[out_dir]['out']
                edges.append(out_edge.get_id())
                route_edge_length += out_edge.length
                # 再寻找过渡节点的到下一个路口过渡节点的边
                transition_edge = self.transition_edges['dir_edges'][cur_cross.id][out_dir]
                edges.append(transition_edge.get_id())
                route_edge_length += transition_edge.length
                # 当前节点沿路由方向后移
                cur_cross = cur_next_cross['next'] if is_forward else cur_next_cross['pre']
                cur_dir = next_in_dir
        return edges


    def _get_turn_flow_ratio(self):
        """获取每个交叉口每个进口道的转向流量"""
        for cross_id, flow_info in self.flow.items():
            self.cross_turn_ratio[cross_id] = {}
            # 处理协调方向流量缺失值
            coordination_turn = self._get_coordinate_direction_info(cross_id)
            for _, direction_info in coordination_turn.items():
                coor_dir = direction_info['direction']
                coor_turn = TURN_MAP_NUM.get(direction_info['turn'], '2')
                flow_turn = coor_dir + coor_turn
                if flow_turn not in flow_info:
                    flow_info[flow_turn] = 1

            # 解析流量信息
            for lane_turn, flow_value in flow_info.items():
                # 解析路口方向和转向字符
                dir, turn = lane_turn[0], lane_turn[1]
                turn_num_to_str = {value: key for key, value in TURN_MAP_NUM.items()}
                turn_lane_num = self.get_turn_lane_nums(cross_id, dir, turn_num_to_str.get(turn))
                if turn_lane_num == 0 or turn == '8':
                    continue
                if dir not in self.cross_turn_ratio[cross_id]:
                    self.cross_turn_ratio[cross_id][dir] = {}
                self.cross_turn_ratio[cross_id][dir][turn] = flow_value


    def to_json(self ) -> Dict[str, Any]:
        """将配置转换为JSON格式"""
        intersection_json = {}
        for cross_id, cross in self.crosses.items():
            intersection_json[cross_id] = cross.to_json()

        transition_edges_json = {
            'edges': [edge.to_json() for edge in self.transition_edges['edges']],
            'dir_edges': {}
        }
        
        for cross_id in self.transition_edges['dir_edges']:
            transition_edges_json['dir_edges'][cross_id] = {}
            for dir, edge in self.transition_edges['dir_edges'][cross_id].items():
                transition_edges_json['dir_edges'][cross_id][dir] = edge.to_json()
        
        return {
            'cross_list': self.cross_list,
            'crosses': intersection_json,
            'transition_edges': transition_edges_json,
            'routes': self.routes.to_json()
        }

