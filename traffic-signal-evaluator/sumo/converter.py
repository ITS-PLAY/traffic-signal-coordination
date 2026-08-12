#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据转换器，将解析后的配置转换为SUMO仿真路网需要的JSON信息
"""

import json
import math
from typing import Dict, List, Any, Tuple
from core.node import Node
from core.edge import Edge, Lane
from core.connection import Connection
from core.route import Route
from core.tl_logic import Phase, TLLogic
from core.roadnet import Roadnet
from core.cross import Cross
from constants.constants import STRAIGHT_CONNECTION_DELTA, DEFAULT_EDGE_MIN_LENGTH, TRANSITION_DISTANCE


class Converter:
    """
    数据转换器类，负责将解析后的配置转换为SUMO仿真路网需要的JSON信息
    """
    
    def __init__(self):
        """初始化数据转换器"""
            
    def convert(self, parsed_config: dict) -> dict:
        """
        将解析后的配置转换为SUMO仿真路网需要的JSON信息
        
        Args:
            parsed_config: 解析后的配置信息
            
        Returns:
            转换后的SUMO仿真路网数据
        """
        sumo_data = {
            'nodes': [],        # 节点列表（包括实际路口和过渡路口）
            'edges': [],        # 边列表
            'connections': [],  # 连接线列表
            'traffic_lights': [],  # 信号灯列表
            'routes': [],         # 路由列表
            'reroutes': [], # 重新路由列表
        }
        
        roadnet_data = parsed_config
        cross_list = roadnet_data['cross_list']
        transition_edges = roadnet_data['transition_edges']
        crosses = roadnet_data['crosses']
        
        if len(cross_list) == 0:
            return sumo_data

        # 生成当前节点
        x_pos = 0
        y_pos = 0
        cur_node = Node(cross_list[0], x_pos, y_pos, 'traffic_light')
        # 遍历路口列表，生成当前路口和当前路网的子网（包括路口内的中心点、周边过渡节点、路口内节点间边、连接线、信号灯）
        for i in range(len(cross_list)):
            # 获取当前路口信息
            node_id = cross_list[i]
            cross_info = roadnet_data['crosses'][node_id]
            # 生成当前路口子网
            nodes, edges, connections, traffic_lights, cur_node = self._gen_subnet_by_node(cur_node, cross_info)

            # 累加当前路口子网的节点、边、连接线、信号灯
            sumo_data['nodes'] += nodes
            sumo_data['edges'] += edges
            sumo_data['connections'] += connections
            sumo_data['traffic_lights'].append(traffic_lights)
        
        # 生成过渡边和连接线
        trans_edges = self._gen_trans_edges(transition_edges)
        trans_connections = self._gen_trans_connections(transition_edges, crosses)
        
        # 累加过渡边和连接线
        sumo_data['edges'] += trans_edges
        sumo_data['connections'] += trans_connections
        
        sumo_data['routes'] = roadnet_data['routes']
        sumo_data['reroutes'] = roadnet_data['reroutes']
        roadnet = Roadnet(roadnet_data['cross_list'], sumo_data['nodes'], sumo_data['edges'], sumo_data['connections'], sumo_data['traffic_lights'], sumo_data['routes'], sumo_data['reroutes'])
        
        return roadnet
    
    def _gen_subnet_by_node(self, cur_node, cross_info):
        nodes = []
        edges = []
        connections = []
        traffic_lights = None
        next_node = None

        # 生成当前路口子网的节点
        nodes, next_node = self._gen_sub_nodes(cur_node, cross_info)
        # 生成当前路口子网的边
        edges = self._gen_sub_edges(cross_info)
        # 生成当前路口子网的连接线
        connections = self._gen_sub_connections(cur_node, cross_info)

        # 生成当前路口子网的信号灯
        traffic_lights = self._gen_sub_traffic_lights(cur_node, cross_info, connections)


        return nodes, edges, connections, traffic_lights, next_node

    def split_road_length(self, length):
        """当路段较短时，按照路段长度划分出口道和下游进口道"""
        start_edge_length = math.floor(0.5 * (length - DEFAULT_EDGE_MIN_LENGTH))
        return start_edge_length

    def _gen_sub_nodes(self, cur_node: Node, cross: Cross):
        nodes = [cur_node]
        next_node = None
        points = cross.points
        next_cross = cross.next_cross
        pre_cross = cross.pre_cross

        # 生成to方向的过渡节点
        for point in points:
            if point.dir == '0':
                continue
            dir = point.dir
            # 当上游或下游路段长度小于默认的过渡路段长度时，调整过渡路段的长度
            if next_cross and dir == next_cross['from_dir'] and next_cross['length'] < 2 * TRANSITION_DISTANCE + 20:
                length = self.split_road_length(next_cross['length'])
            elif pre_cross and dir == pre_cross['from_dir'] and pre_cross['length'] < 2 * TRANSITION_DISTANCE + 20:
                length = self.split_road_length(pre_cross['length'])
            else:
                length = TRANSITION_DISTANCE
            # 计算过渡节点坐标
            x_pos, y_pos = self._cal_node_pos(cur_node, dir, length)
            node = Node(point.id, x_pos, y_pos, 'transition')
            nodes.append(node)
        
        # 计算下一节点坐标
        if next_cross is not None:
            next_cross_dir = next_cross['from_dir']
            next_cross_id = next_cross['next'].id
            length = next_cross['length']
            # 计算下一节点坐标
            x_pos, y_pos = self._cal_node_pos(cur_node, next_cross_dir, length)
            node = Node(next_cross_id, x_pos, y_pos, 'traffic_light')
            
            next_node = node

        return nodes, next_node
    
    def _gen_sub_edges(self, cross_info: Cross):
        # 增加路口内的边
        return cross_info.edges
    
    def _gen_trans_edges(self, transition_edges: Dict[str, Any]):

        return transition_edges['edges']
    
    # 生成实际路口内的连接线
    def _gen_sub_connections(self, cur_node: Node, cross_info: Dict[str, Any]):
        connections = []
        # 生成实际路口内的转向对
        turn_pairs = self._gen_cross_turn_pairs(cross_info)

        # 遍历实际路口内的转向对，生成连接线
        for turn_pair in turn_pairs:
            cur_connection = self._gen_turn_connection(turn_pair, cur_node.id)
            connections += cur_connection
        
        # 对连接线进行排序，统一设置linkIndex
        custom_turn_order = ['r', 's', 'l', 't']
        custom_order_dict = {item: index for index, item in enumerate(custom_turn_order)}
        connections.sort(key=lambda x: (x.from_edge, x.from_lane, custom_order_dict.get(x.dir), x.to_edge, x.to_lane))
        for i, conn in enumerate(connections):
            conn.link_index = i

        return connections

    # 生成过渡路段的连接线
    def _gen_trans_connections(self, transition_edges: Dict[str, Any], crosses: Dict[str, Cross]):
        connections = []
        # 生成过渡路段的转向对
        turn_pairs = self._gen_trans_turn_pairs(transition_edges, crosses)
        
        # 遍历过渡路段的转向对，生成连接线
        for turn_pair in turn_pairs:
            cur_connection = self._gen_turn_connection(turn_pair, None)
            connections += cur_connection

        return connections
    
    def _gen_turn_connection(self, turn_pair, tl_id):
        # 生成连接线
        connection = []
        type = turn_pair['type']
        from_edge = turn_pair['from_edge']
        to_edge = turn_pair['to_edge']
        from_edge_id = from_edge.id
        to_edge_id = to_edge.id
        from_lanes = from_edge.lanes
        to_lanes = to_edge.lanes
        # 出边车道数为0，直接返回空列表
        if len(to_lanes) == 0:
            return connection
        # 转向对的转向方向
        turn = turn_pair['turn']
        # 过滤入边所有车道运行允许当前转向对定义的转向的车道
        from_turn_lanes = [lane for lane in from_lanes if turn in lane.turn]

        # 遍历入边所有车道运行允许当前转向对定义的转向的车道，生成连接线
        target_middle_index = len(to_lanes) // 2
        effective_from_lanes, effective_to_lanes = [], []
        for to_lane_idx, lane in enumerate(from_turn_lanes):
            from_lane_idx = lane.index
            # 左转时，从最左侧开始连接
            if turn == 'l' or turn == 't':
                to_lane_idx = len(to_lanes) - len(from_turn_lanes) + to_lane_idx
            # 出边车道数小于入边车道数，取出边车道数-1作为目标车道索引
            if to_lane_idx >= len(to_lanes) or to_lane_idx < 0:
                continue

            # 直行从中间车道往两边拓展连接
            if turn == 's':
                from_lane_idx = from_turn_lanes[len(from_turn_lanes) - 1 - to_lane_idx].index
                lane_index = to_lane_idx
                to_lane_idx = target_middle_index + STRAIGHT_CONNECTION_DELTA[lane_index]
                if to_lane_idx >= len(to_lanes) or to_lane_idx < 0:
                    to_lane_idx = target_middle_index + STRAIGHT_CONNECTION_DELTA[lane_index + 1]
            effective_from_lanes.append(from_lane_idx)
            effective_to_lanes.append(to_lane_idx)
            # else:
                # 出边车道数大于等于入边车道数，目标车道索引与入边车道索引相同
                # TODO: 出边车道会存在没有连接线的情况，需要进一步处理
                # to_lane_idx = from_lane_idx

        # 升序排列
        effective_from_lanes.sort()
        effective_to_lanes.sort()
        for from_lane_idx, to_lane_idx in zip(effective_from_lanes, effective_to_lanes):
            cur_connection = Connection(from_edge_id, to_edge_id, from_lane_idx, to_lane_idx, turn)
            
            # 信控路口内的connection增加信号灯相关信息
            if type == 'internal':
                from_dir = turn_pair['dir']
                cur_connection.tl = tl_id
                cur_connection.from_dir = from_dir
            connection.append(cur_connection)

        return connection

    def _gen_trans_turn_pairs(self, transition_edges: Dict[str, Any], crosses: Dict[str, Cross]):
        # 生成过渡路段的转向对
        turn_pairs = []
        dir_trans_edges = transition_edges['dir_edges']
        for cross_id in dir_trans_edges:
            cross = crosses[cross_id]
            for dir in dir_trans_edges[cross_id]:
                # 计算从cross到dir方向的过渡边的转向对，默认只有直行
                to_edge = dir_trans_edges[cross_id][dir]
                from_edge = cross.dir_edges[dir]['out']
                turn_pairs.append({
                    'from_edge': from_edge,
                    'to_edge': to_edge,
                    'turn': 's',
                    'type': 'transition',
                })

                # 计算从过渡边到下一个节点的边的转向对
                next_cross = cross.get_next_cross_by_dir(dir)
                # 跳过没有下一个节点（终点或起点）的过渡边
                if next_cross is None:
                    continue
                next_in_dir = next_cross['to_dir']
                # 计算从过渡边到下一个节点的边的转向对，默认只有直行
                next_to_edge = next_cross['next'].dir_edges[next_in_dir]['in'] if 'next' in next_cross else next_cross['pre'].dir_edges[next_in_dir]['in']
                next_from_edge = to_edge

                turn_pairs.append({
                    'from_edge': next_from_edge,
                    'to_edge': next_to_edge,
                    'turn': 's',
                    'type': 'transition',
                })

        return turn_pairs

    def _gen_cross_turn_pairs(self, cross_info):
        # 预定义所有可能的转向对，包括左转、直行、右转、掉头
        dir_pairs = [('1', '1', 't'), ('1', '2', 'l'), ('1', '3', 's'), ('1', '4', 'r'),
        ('2', '1', 'r'), ('2', '2', 't'), ('2', '3', 'l'), ('2', '4', 's'),
        ('3', '1', 's'), ('3', '2', 'r'), ('3', '3', 't'), ('3', '4', 'l'),
        ('4', '1', 'l'), ('4', '2', 's'), ('4', '3', 'r'), ('4', '4', 't')]


        dir_edges = cross_info.dir_edges
        turn_pairs = []
        # 路口过渡节点之间的转向对
        for dir_pair in dir_pairs:
            from_dir, to_dir, turn = dir_pair
            # 当前转向不存在入边或者出边j，跳过
            if from_dir not in dir_edges or to_dir not in dir_edges:
                continue
            # 获取当前转向对的入边和出边
            from_edge = dir_edges[from_dir]['in']
            to_edge = dir_edges[to_dir]['out']
            # 生成当前转向的转向对，包括当前转向的入边、出边、转向方向和类型（内部转向，即路口内的转向）
            turn_pairs.append({
                'from_edge': from_edge,
                'to_edge': to_edge,
                'turn': turn,
                'type': 'internal',
                'dir': from_dir
            })

        return turn_pairs

    def _gen_sub_traffic_lights(self, cur_node, cross_info, connections):
        # 生成当前节点的子交通灯，包括交通灯ID、类型（静态）、偏移时间和相位列表
        # 获取当前路口的信控方案信息
        plan = cross_info.traffic_light
        # 信控方案中定义的相位功能（即每个相位允许的转向方向）
        functions = plan.functions
        # 信控方案中定义的相位列表
        phase_list = plan.phases
        # 生成sumo格式的交通灯
        traffic_lights = TLLogic(cur_node.id, 'static', plan.abs_offset, [])

        # 结合连接线信息生成相位的state（即每个相位允许的通行的连接线，格式为rR(红灯),gG(绿灯),yY(黄灯)组成的字符串）
        phase_states = self._gen_phase_state(connections, phase_list, functions)

        phases = []
        # 生成每个相位的持续时间和state
        for phase_no in plan.durations:
            phases.append(Phase(plan.durations[phase_no], ''.join(phase_states[phase_no])))
        
        traffic_lights.set_phases(phases)
        
        return traffic_lights
    
    def _get_dir_turn_phases(self, functions):
        # 转换相位功能为方向-转向-相位列表的格式
        # functions格式为{相位: {方向: [转向列表]}}
        cross_dir_phases = {}
        for ph in functions:
            for dir in functions[ph]:
                if dir not in cross_dir_phases:
                    cross_dir_phases[dir] = {}
                for turn in functions[ph][dir]:
                    if turn not in cross_dir_phases[dir]:
                        cross_dir_phases[dir][turn] = []
                    cross_dir_phases[dir][turn].append(ph)
            
        return cross_dir_phases
    
    def _gen_phase_state(self, connections, phase_list, functions):
        # 生成每个相位的状态（即每个相位允许的通行的连接线）
        # connections为所有连接线的列表，每个元素为一个字典，包含连接的信息（包括交通灯ID、方向、连接的边、车道索引等）
        # phase_list为信控方案中定义的相位列表
        # functions为信控方案中定义的相位功能（即每个相位允许的转向方向）
        # 返回一个字典，键为相位，值为该相位允许的通行的连接线的状态列表（格式为rR(红灯),gG(绿灯),yY(黄灯)组成的字符串）
        size = len([con for con in connections if con.tl is not None])
        # 转换相位功能为方向-转向-相位列表的格式
        dir_turn_phases = self._get_dir_turn_phases(functions)
        # 初始化状态为红灯
        states = {ph: ['r']*size for ph in phase_list}

        for con in connections:
            # 跳过没有交通灯的连接线，即非信控路口内的连接线
            if con.tl is None:
                continue
            from_dir = con.from_dir
            turn = con.dir
            link_index = con.link_index
            # 如果当前方向-转向组合在相位功能中定义，且当前相位在该组合的相位列表中，将该连接线的状态设置为绿灯
            if from_dir in dir_turn_phases and turn in dir_turn_phases[from_dir]:
                for ph in dir_turn_phases[from_dir][turn]:
                    states[ph][link_index] = 'g'
            else:
                # 如果当前方向-转向组合不在相位功能中定义，但是是右转，将该连接线的状态设置为绿灯
                if turn == 'r':
                    for ph in states:
                        states[ph][link_index] = 'g'
                continue

        return states

    def _cal_node_pos(self, base_node: Node, dir: str, distance: float) -> Tuple[float, float]:
        """计算节点坐标
        
        Args:
            base_node: 基准节点信息（包含x, y坐标）
            dir: 方向（1-北，2-东，3-南，4-西）
            distance: 距离（米）
            
        Returns:
            节点坐标（x, y）
        """
        dir_offset = {
            '1': (0, 1),    # 北
            '2': (1, 0),    # 东
            '3': (0, -1),   # 南
            '4': (-1, 0)    # 西
        }
        x_dir, y_dir = dir_offset[dir]
        x_pos = base_node.x + x_dir * distance
        y_pos = base_node.y + y_dir * distance
        
        return x_pos, y_pos

def convert_parsed_config_to_sumo(parsed_config: dict) -> dict:
    """
    将解析后的配置转换为SUMO仿真路网需要的JSON信息
    
    Args:
        parsed_config: 解析后的配置信息
        
    Returns:
        转换后的SUMO仿真路网数据
    """
    converter = DataConverter()
    return converter.convert(parsed_config)
