# -*- coding: utf-8 -*-
"""
合并后的项目代码
源项目: D:\本地脚本\SUMO\traffic-signal-evaluator
入口文件: main.py
自动生成 - 请勿直接编辑
"""



# ----------------------------------------------------------------------------
# 原文件: core\node.py
# ----------------------------------------------------------------------------

# 节点类
class Node:
    def __init__(self, id: str, x: float, y: float, type: str = 'normal'):
        self.id = id
        self.x = x
        self.y = y
        self.type = type

    # 获取节点id
    def get_id(self) -> str:
        return self.id

    # 转换为sumo xml格式
    def to_xml(self) -> str:
        return f'    <node id="{self.get_id()}" x="{self.x}" y="{self.y}" type="{self.type}" />'

    # 转换为json格式
    def to_json(self) -> dict:
        return {
            'id': self.get_id(),
            'x': self.x,
            'y': self.y,
            'type': self.type
        }
    
    # 转换为字符串格式, TODO: 增加更多的信息
    def to_string(self) -> str:
        return f'{self.get_id()} ({self.x}, {self.y})'


# ----------------------------------------------------------------------------
# 原文件: core\tl_logic.py
# ----------------------------------------------------------------------------

from typing import List

# 交通灯相位类，用于表示SUMO中的交通灯相位定义
class Phase:
    def __init__(self, duration: int, state: str):
        self.duration = duration
        self.state = state
    
    def to_xml(self) -> str:
        """
        转换为SUMO XML格式的交通灯相位定义
        
        Returns:
            SUMO XML格式的交通灯相位字符串
        """
        return f'        <phase duration="{self.duration}" state="{self.state}"/>'
    
    def to_json(self) -> dict:
        """
        转换为JSON格式的交通灯相位定义
        
        Returns:
            JSON格式的交通灯相位字典
        """
        return {
            'duration': self.duration,
            'state': self.state
        }

class TLLogic:
    """
    交通灯逻辑类，负责处理交通灯的状态转换和时间分配
    """
    def __init__(self, id: str, type: str, offset: int, phases: List[Phase]=None) -> None:
        self.id = id
        self.type = type
        self.offset = offset
        self.phases = phases
    
    def set_phases(self, phases: List[Phase]):
        self.phases = phases

    def to_xml(self) -> str:
        """
        转换为SUMO XML格式的交通灯逻辑定义
        
        Returns:
            SUMO XML格式的交通灯逻辑字符串
        """
        xml_lines = [f'    <tlLogic id="{self.id}" type="{self.type}" programID="0" offset="{self.offset}">']
        xml_lines.extend([phase.to_xml() for phase in self.phases])
        xml_lines.append('    </tlLogic>')
        
        return '\n'.join(xml_lines)
    
    def to_json(self) -> dict:
        """
        转换为JSON格式的交通灯逻辑定义
        
        Returns:
            JSON格式的交通灯逻辑字典
        """
        return {
            'id': self.id,
            'type': self.type,
            'offset': self.offset,
            'phases': [phase.to_json() for phase in self.phases]
        }


# ----------------------------------------------------------------------------
# 原文件: core\connection.py
# ----------------------------------------------------------------------------

# 连接类，用于表示边和边之间的连接定义
class Connection:
    def __init__(self, from_edge: str, to_edge: str, from_lane: int, to_lane: int, dir: str, tl: str=None, link_index: int=None):
        self.id = None
        self.from_edge = from_edge
        self.to_edge = to_edge
        self.from_lane = from_lane
        self.to_lane = to_lane
        self.dir = dir
        self.tl = tl
        self.link_index = link_index
        self.from_dir = None

    # 转换为SUMO XML格式的连接定义
    def to_xml(self) -> str:
        if self.tl is None:
            return f'    <connection from="{self.from_edge}" to="{self.to_edge}" fromLane="{self.from_lane}" toLane="{self.to_lane}" dir="{self.dir}" />'
        return f'    <connection from="{self.from_edge}" to="{self.to_edge}" fromLane="{self.from_lane}" toLane="{self.to_lane}" dir="{self.dir}" tl="{self.tl}" linkIndex="{self.link_index}" />'


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
        self.relative_abs_offset = 0
        self.abs_offset = 0
        self.coordination_phase = coordination_phase
        self.cycle = sum(self.durations.values())

    def calculate_abs_offset(self):
        """计算每个路口的绝对相位差"""
        self.abs_offset = self.relative_abs_offset

        temp_offset = 0
        for stage_name in self.phases:
            stage_length = self.durations[stage_name]
            if stage_name == self.coordination_phase:
                self.abs_offset = self.relative_abs_offset - temp_offset
                break
            else:
                temp_offset += stage_length
        self.abs_offset = self.abs_offset % self.cycle
        self.relative_abs_offset = self.relative_abs_offset % self.cycle

    # 转换为XML格式，目前未被使用，TODO：需要补充更多信息
    def to_xml(self) -> str:
        xml = ''
        for phase in self.phases:
            xml += f'<phase duration="{self.durations[phase]}" state="{phase}" />'
        return xml
    
    # 转换为完整JSON格式
    def to_json(self) -> dict:
        return {
            'id': self.id,
            'cross_id': self.cross_id,
            'phases': self.phases,
            'durations': self.durations,
            'functions': self.functions,
            'offset': self.abs_offset
        }
    
    # 转换为字符串格式，TODO：需要补充更多信息
    def to_string(self) -> str:
        return f'{self.id} {self.cross_id}'


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

    # 转换为sumo xml格式
    def to_xml(self) -> str:
        # 不添加length属性，因为sumo会根据node位置以及路口内部路径计算edge的length
        return f'        <lane index="{self.index}" speed="{self.speed}" />'
    
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

    # 转换为sumo xml格式
    def to_xml(self) -> str:
        # 不添加length属性，因为sumo会根据node位置以及路口内部路径计算edge的length
        xml_lines = [f'    <edge id="{self.get_id()}" from="{self.from_node}" to="{self.to_node}" priority="1" numLanes="{self.lane_num}">']
        for lane in self.lanes:
            xml_lines.append(lane.to_xml())
        xml_lines.append('    </edge>')
        return '\n'.join(xml_lines)

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
# 原文件: core\veh_type.py
# ----------------------------------------------------------------------------


# 车辆类型类，定义车辆的换道行为
class VehType:
    laneChangeDuration = "2.0"
    overtakeRight = "true"
    lcStrategic = "2.0"
    lcCooperative = "0.7" # 减少相互等待
    lcAssertive = "1.8" # 果断换道
    lcSpeedGain = "1.0"
    lcKeepRight = "0.5" #左转车辆优先左侧
    def __init__(self, id='car'):
        self.id = id

    def to_xml(self):
        xml_lines = ['<additional>']
        veh_type = (f'<vType id="{self.id}" laneChangeDuration="{self.laneChangeDuration}"'
                    f' overtakeRight="{self.overtakeRight}" lcStrategic="{self.lcStrategic}"'
                    f' lcCooperative="{self.lcCooperative}" lcAssertive="{self.lcAssertive}"'
                    f' lcSpeedGain="{self.lcSpeedGain}" lcKeepRight="{self.lcKeepRight}"/>')
        xml_lines.append(veh_type)
        xml_lines.append('</additional>')
        return '\n'.join(xml_lines)


# ----------------------------------------------------------------------------
# 原文件: utils\logger.py
# ----------------------------------------------------------------------------

import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# ----------------------------------------------------------------------------
# 原文件: core\route.py
# ----------------------------------------------------------------------------

from typing import List

# 路由类，用于表示SUMO中的路由定义
class Route:
    def __init__(self, route_edges: List[str], route_id: str = None):
        # 路由边列表，每个元素为SUMO中的边ID
        self.route_edges = route_edges
        # 路由ID，默认格式为'r_<起始边ID>_<终止边ID>'
        self.id = f'r_{self.route_edges[0]}_{self.route_edges[-1]}' if route_id is None else route_id
    
    def get_route_id(self) -> str:
        """
        获取路由ID
        
        Returns:
            路由ID字符串
        """
        if self.id is None:
            self.id = f'r_{self.route_edges[0]}_{self.route_edges[-1]}'

        return self.id

    def to_xml(self) -> str:
        """
        转换为SUMO XML格式的路由定义
        
        Returns:
            SUMO XML格式的路由字符串
        """
        return f'    <route id="{self.get_route_id()}" edges="{" ".join(self.route_edges)}"/>'

    def to_json(self) -> dict:
        """
        转换为JSON格式的路由定义
        
        Returns:
            JSON格式的路由字典
        """
        return {
            'id': self.get_route_id(),
            'edges': self.route_edges
        }
    
    def to_string(self) -> str:
        """
        转换为字符串格式的路由定义
        
        Returns:
            字符串格式的路由定义
        """
        return f'{self.get_route_id()} [{", ".join(self.route_edges)}]'

# 流量类，用于表示SUMO中的流量定义
class Flow:
    def __init__(self, route: Route, type, begin_time: float, probability: float, number: int, flow_id: str = None):
        self.route = route.get_route_id()
        self.type = type
        self.begin = begin_time
        self.probability = probability
        self.number = number
        self.id = flow_id if flow_id is not None else f'f_{self.route}'
    
    def get_flow_id(self) -> str:
        if self.id is None:
            self.id = f'f_{self.route.get_route_id()}'

        return self.id
    
    def to_xml(self) -> str:
        """
        转换为SUMO XML格式的流量定义
        
        Returns:
            SUMO XML格式的流量字符串
        """
        return f'    <flow id="{self.get_flow_id()}" type= "{self.type}" route="{self.route}" begin="{self.begin}" departSpeed="3" probability="{self.probability}" number="{self.number}"/>'
    
    def to_json(self) -> dict:
        """
        转换为JSON格式的流量定义
        
        Returns:
            JSON格式的流量字典
        """
        return {
            'id': self.get_flow_id(),
            'type': self.type,
            'route': self.route,
            'begin': self.begin,
            'probability': self.probability,
            'number': self.number
        }
    
    def to_string(self) -> str:
        """
        转换为字符串格式的流量定义
        
        Returns:
            字符串格式的流量定义
        """
        return f'{self.get_flow_id()} {self.route} {self.begin} {self.probability} {self.number}'

# 路由集合类，用于表示SUMO中的路由集合定义
class Routes:
    def __init__(self, routes: List[Route], flows: List[Flow]):
        self.routes = routes
        self.flows = flows
    
    def to_xml(self) -> str:
        """
        转换为SUMO XML格式的路由定义
        
        Returns:
            SUMO XML格式的路由字符串
        """
        xml_lines = ['<routes>']
        xml_lines.extend([route.to_xml() for route in self.routes])
        xml_lines.extend([flow.to_xml() for flow in self.flows])
        xml_lines.append('</routes>')

        return '\n'.join(xml_lines)
    
    def to_json(self) -> dict:
        """
        转换为JSON格式的路由定义
        
        Returns:
            JSON格式的路由字典
        """
        return {
            'routes': [route.to_json() for route in self.routes],
            'flows': [flow.to_json() for flow in self.flows]
        }
    
    def to_string(self) -> str:
        """
        转换为字符串格式的路由定义
        
        Returns:
            字符串格式的路由定义
        """
        return '\n'.join([route.to_string() for route in self.routes]) + '\n' + '\n'.join([flow.to_string() for flow in self.flows])


class ReRoute:
    def __init__(self, edge_from, edge_to, probability):
        self.edge_from = edge_from
        self.edge_to = edge_to
        self.probability = probability

    def to_xml(self):
        """
        转换为SUMO XML格式的转向比定义

        Returns:
            SUMO XML格式的转向比字符串
        """
        return f'    <destProbReroute id="{self.edge_to}" probability="{self.probability}"/>'


class ReRouters:
    def __init__(self, reroutes, simulation_time):
        self.reroutes = reroutes
        self.simulation_time = simulation_time
        self.edges_turn_info = {}
        self._calculate_turn_ratio()

    def _calculate_turn_ratio(self):
        for reroute in self.reroutes:
            if reroute.edge_from not in self.edges_turn_info:
                self.edges_turn_info[reroute.edge_from] = []
            self.edges_turn_info[reroute.edge_from].append(reroute)

    def to_xml(self):
        xml_lines = ['<additional>']
        for edge_from, reroute_info in self.edges_turn_info.items():
            xml_lines.append(f'  <rerouter id="{edge_from}" edges="{edge_from}" pos="0">')
            xml_lines.append(f'       <interval begin="0" end="{self.simulation_time}">')
            xml_lines.extend([reroute.to_xml() for reroute in reroute_info])
            xml_lines.append('        </interval>')
            xml_lines.append('   </rerouter>')
        xml_lines.append('</additional>')
        return '\n'.join(xml_lines)


# ----------------------------------------------------------------------------
# 原文件: constants\constants.py
# ----------------------------------------------------------------------------

# 保留小数点位数
DECIMAL_NUMBER = 6
# 排队有效等待时间的时间阈值，单位秒
WAITING_TIME_INTERVAL = 5
# 默认最小平均车速，用于计算仿真持续时间
DEFAULT_MIN_SPEED_KMH = 20
# 路口内过渡边长度，单位米
TRANSITION_EDGE_LENGTH = 100
# 路网外围进口道长度，单位米
TRANSITION_DISTANCE = 80
# 路口内过渡边速度，单位米/秒
TRANSITION_EDGE_SPEED = 50/3.6
# 默认流量开始时间，单位秒
DEFAULT_FLOW_BEGIN_TIME = 0
# 协调方向流量开始时间，单位秒
COOR_DEFAULT_FLOW_BEGIN_TIME = int(4 * TRANSITION_DISTANCE / TRANSITION_EDGE_SPEED)
# 默认流量出现概率，单位秒，即每秒会生成一辆车的概率
DEFAULT_FLOW_PROBABILITY = 0.15
# 默认的进口道顺序
DEFAULT_DIRECTIONS = ['1', '2', '3', '4']  # 北、东、南、西
# 路径单车道流量的最小值，单位：辆/小时
DEFAULT_LANE_FLOW = 120
# 流量采集的时间间隔，单位：秒
FLOW_TIME_INTERVAL = 3600
# 加载流量的时间窗口，单位：秒
DEFAULT_FLOW_WINDOWS = 900
#起点和终点路口协调转向的反方向
DEFAULT_REVERSE_TURN = {'2': '2', '4': '1', '1': '4'}
# 直行车道连接下游，按照下游出口车道数，从中间开始匹配
STRAIGHT_CONNECTION_DELTA = [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
# 路段中间连接线的最小长度
DEFAULT_EDGE_MIN_LENGTH = 10
# 转向的编号
TURN_MAP_NUM = {'t': '8', 'l': '4', 's': '2', 'r': '1'}
# 车辆类型编号
DEFAULT_VEH_TYPE = 'car'
# 判断是否停车的速度阈值，米/秒
WAITING_SPEED = 3.6/3.6

#默认最多允许多少个仿真任务同时运行
DEFAULT_MAX_SIM_WORKERS = '3'
#默认一个worker连续处理多少次后重建
DEFAULT_MAX_TASKS_PER_CHILD = '50'
#默认允许额外等待的任务数量
DEFAULT_MAX_SIM_QUEUE_SIZE = '5'


# ----------------------------------------------------------------------------
# 原文件: core\cross.py
# ----------------------------------------------------------------------------

from re import S
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
# 原文件: core\roadnet.py
# ----------------------------------------------------------------------------

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List

# 路网类，定义路网的结构和属性
class Roadnet:
    def __init__(self, cross_list: List[str], nodes: List[Node], edges: List[Edge], conn_list: List[Connection], tl_list: List[TLLogic], routes: Routes, reroutes):
        self.cross_list = cross_list
        self.nodes = nodes
        self.edges = edges
        self.conn_list = conn_list
        self.tl_list = tl_list
        self.routes = routes
        self.reroutes = reroutes
    
    # 生成节点xml格式
    def gen_node_xml(self) -> str:
        xml_lines = ['<nodes>']
        
        # 添加location标签（计算边界）
        min_x = min(node.x for node in self.nodes) if self.nodes else 0
        max_x = max(node.x for node in self.nodes) if self.nodes else 0
        min_y = min(node.y for node in self.nodes) if self.nodes else 0
        max_y = max(node.y for node in self.nodes) if self.nodes else 0
        
        xml_lines.append(
            f'    <location netOffset="0.00,0.00" convBoundary="{min_x:.2f},{min_y:.2f},{max_x:.2f},{max_y:.2f}" '
            f'origBoundary="{min_x:.2f},{min_y:.2f},{max_x:.2f},{max_y:.2f}" projParameter="!"/>'
        )
        
        # 添加节点
        for node in self.nodes:
            xml_lines.append(
                node.to_xml()
            )
        
        xml_lines.append('</nodes>')
        return '\n'.join(xml_lines)
    
    # 生成边xml格式
    def gen_edge_xml(self) -> str:
        xml_lines = ['<edges>']
        for edge in self.edges:
            xml_lines.append(
                edge.to_xml()
            )
        xml_lines.append('</edges>')
        return '\n'.join(xml_lines)
    
    # 生成连接xml格式
    def gen_conn_xml(self) -> str:
        xml_lines = ['<connections>']
        for conn in self.conn_list:
            xml_lines.append(
                conn.to_xml()
            )
        xml_lines.append('</connections>')
        return '\n'.join(xml_lines)
    
    # 生成信号灯xml格式
    def gen_tl_xml(self) -> str:
        """
        生成信号灯XML内容
        
        Returns:
            信号灯XML字符串
        """
        if not self.tl_list:
            return '<tlLogics/>'  # 如果没有信号灯，返回空的tlLogics标签
        
        xml_lines = ['<tlLogics>']
        
        # 添加信号灯
        for tl in self.tl_list:
            xml_lines.append(
                tl.to_xml()
            )
        
        xml_lines.append('</tlLogics>')
        return '\n'.join(xml_lines)
    
    # 生成路由xml格式
    def gen_route_xml(self) -> str:
        """
        生成路由XML内容
        
        Returns:
            路由XML字符串
        """
        
        return self.routes.to_xml()

    # 生成重新路由xml格式
    def gen_reroute_xml(self):
        return self.reroutes.to_xml()
    
    # 生成路网xml格式，仅合并节点、边、连接、信号灯、路由的xml，sumo命令生成路网时，会根据这些xml生成完整的路网
    def gen_net_xml(self) -> str:
        xml = ''
        xml += self.gen_node_xml()
        xml += self.gen_edge_xml()
        xml += self.gen_conn_xml()
        xml += self.gen_tl_xml()
        xml += self.gen_route_xml()

        return xml



# ----------------------------------------------------------------------------
# 原文件: utils\util.py
# ----------------------------------------------------------------------------

import xml.etree.ElementTree as ET



def get_target_direction(from_direction, lane_turn):
    """根据起始方向和转向类型确定目标方向"""
    from_index = DEFAULT_DIRECTIONS.index(from_direction)

    if lane_turn == '2':  # 直行
        target_direction = DEFAULT_DIRECTIONS[(from_index + 2) % 4]
    elif lane_turn == '4':  # 左转
        target_direction = DEFAULT_DIRECTIONS[(from_index + 1) % 4]
    elif lane_turn == '1':  # 右转
        target_direction = DEFAULT_DIRECTIONS[(from_index - 1) % 4]
    elif lane_turn == '8':  # 掉头
        target_direction = from_direction
    else:  # 默认为直行
        target_direction = DEFAULT_DIRECTIONS[(from_index + 2) % 4]
    return target_direction


def extract_edge_lengths(net_file):
    """获取每个edge的真实长度"""
    tree = ET.parse(net_file)
    root = tree.getroot()

    edge_lengths = {}
    for edge in root.findall('edge'):
        edge_id = edge.get('id')
        # 跳过没有 lane 的 edge
        lanes = edge.findall('lane')
        if not lanes:
            continue

        # 取第一个 lane 的 length（SUMO 中同一 edge 的 lane 长度一致）
        length_str = lanes[0].get('length')
        if length_str is not None:
            edge_lengths[edge_id] = float(length_str)
        else:
            edge_lengths[edge_id] = None
    return edge_lengths


def convert_trajectory_format(vehicle_trajectory):
    """将每辆车的轨迹字典，转换为列表格式"""
    vehicles_trajectory_list = []
    for vehicle_id, trajectory_info in vehicle_trajectory.items():
        vehicle_traj = []
        for traj in trajectory_info:
            traj.update({'traj_id': vehicle_id})
            vehicle_traj.append(traj)
        vehicles_trajectory_list.append(vehicle_traj)
    return vehicles_trajectory_list


# ----------------------------------------------------------------------------
# 原文件: sumo\converter.py
# ----------------------------------------------------------------------------

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据转换器，将解析后的配置转换为SUMO仿真路网需要的JSON信息
"""

import json
import math
from typing import Dict, List, Any, Tuple


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


# ----------------------------------------------------------------------------
# 原文件: parse\parser.py
# ----------------------------------------------------------------------------

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



# ----------------------------------------------------------------------------
# 原文件: sumo\simulator.py
# ----------------------------------------------------------------------------

from typing import Any, Dict
import json
import hashlib
import subprocess
from contextlib import contextmanager
import sys
import os
import time
import xml.etree.ElementTree as ET
import collections
import errno
from concurrent.futures import ThreadPoolExecutor



def run_simulator_worker(cfg: dict) -> dict:
    """这个函数在子进程中执行：新建 Simulator(cfg) 并调用 run()"""
    cross_list = cfg.get('crossList', []) if isinstance(cfg, dict) else []
    logger.info('worker start: cross_count=%s, cross_list=%s', len(cross_list), cross_list)
    sim = Simulator(cfg)
    logger.info('worker initialized simulator successfully')
    return sim.run()


class Simulator:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.runtime_config = cfg.get('config', {}) if isinstance(cfg, dict) else {}
        self.enable_profiling = self.runtime_config.get('enableProfiling', os.environ.get('ENABLE_SIM_PROFILING', '0') == '1')
        self.enable_queue_output = self.runtime_config.get('enableQueueOutput', True)
        self.enable_tripinfo_output = self.runtime_config.get('enableTripinfoOutput', self.runtime_config.get('supportDiagram', False))
        self.enable_sumo_perf_options = self.runtime_config.get('enableSumoPerfOptions', True)
        self.fcd_period = max(1, int(self.runtime_config.get('fcdPeriod', os.environ.get('FCD_PERIOD', '1'))))
        self._profiling = collections.OrderedDict()
        # 初始化config parser解析输入数据
        self.cfg_parser: ConfigParser = ConfigParser(self.cfg)
        # 由原始配置数据解析通用的路网配置数据
        self.roadnet_cfg_data: Dict[str, Any] = self.cfg_parser.parse()
        # 初始化数据转换器
        self.converter: Converter = Converter()
        # 初始化roadnet对象为空
        self.roadnet: Roadnet = None
        # 初始化路网相关文件名为None
        self.net_file: str = None
        self.rou_file: str = None
        self.reroute_file: str = None
        self.vehtype_file: str = None
        self.sumo_cfg_file: str = None
        self.node_file: str = None
        self.edg_file: str = None
        self.conn_file: str = None
        self.tll_file: str = None
        self.output_dir: str = '/app/result'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        # 初始化文件前缀为空，后续根据解析的路网
        self.file_prefix: str = None
        # 记录本次仿真实际创建（写入）的文件完整路径
        self._created_files = set()

    @contextmanager
    def _profile_stage(self, stage_name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
            self._profiling[stage_name] = elapsed_ms
            if self.enable_profiling:
                logger.info('profile stage=%s elapsed_ms=%s', stage_name, elapsed_ms)

    def _record_file_size(self, label: str, path: str):
        if not self.enable_profiling:
            return
        if path and os.path.exists(path):
            size_bytes = os.path.getsize(path)
            self._profiling[f'{label}_bytes'] = size_bytes
            logger.info('profile artifact=%s size_bytes=%s path=%s', label, size_bytes, path)

    def _finalize_profiling(self):
        if self.enable_profiling and self._profiling:
            logger.info('profile summary=%s', json.dumps(self._profiling, ensure_ascii=False))

    
    def _get_output_dir(self):
        """获取输出目录，确保目录存在"""
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        return self.output_dir
    
    def _get_file_prefix(self):
        """根据配置数据生成文件前缀，同样的配置数据，生成的文件前缀也相同，后续可以根据文件前缀来判断是否需要重新生成路网文件"""
        if self.file_prefix is None:
            self.file_prefix = hashlib.md5(json.dumps(self.cfg_parser.to_json(), sort_keys=True).encode('utf-8')).hexdigest()

        return self.file_prefix

    def _get_node_file(self):
        """获取节点文件路径，若未指定则根据文件前缀生成"""
        if self.node_file is None:
            self.node_file = f'{self._get_file_prefix()}.node.xml'
    
        return self.node_file
    
    def _get_edg_file(self):
        """获取边文件路径，若未指定则根据文件前缀生成"""
        if self.edg_file is None:
            self.edg_file = f'{self._get_file_prefix()}.edg.xml'
    
        return self.edg_file
    
    def _get_conn_file(self):
        """获取连接文件路径，若未指定则根据文件前缀生成"""
        if self.conn_file is None:
            self.conn_file = f'{self._get_file_prefix()}.conn.xml'
    
        return self.conn_file
    
    def _get_tll_file(self):
        """获取交通灯文件路径，若未指定则根据文件前缀生成"""
        if self.tll_file is None:
            self.tll_file = f'{self._get_file_prefix()}.tll.xml'
    
        return self.tll_file
    
    def _get_rou_file(self):
        """获取路由文件路径，若未指定则根据文件前缀生成"""
        if self.rou_file is None:
            self.rou_file = f'{self._get_file_prefix()}.rou.xml'
    
        return self.rou_file

    def _get_reroute_file(self):
        """获取路由文件路径，若未指定则根据文件前缀生成"""
        if self.reroute_file is None:
            self.reroute_file = f'{self._get_file_prefix()}reroute.add.xml'

        return self.reroute_file

    def _get_vehtype_file(self):
        """获取路由文件路径，若未指定则根据文件前缀生成"""
        if self.vehtype_file is None:
            self.vehtype_file = f'{self._get_file_prefix()}veh.add.xml'

        return self.vehtype_file
    
    def _get_sumo_cfg_file(self):
        """获取SUMO配置文件路径，若未指定则根据文件前缀生成"""
        if self.sumo_cfg_file is None:
            self.sumo_cfg_file = f'{self._get_file_prefix()}.sumocfg'
    
        return self.sumo_cfg_file
    
    def _get_net_file(self):
        """获取路网文件路径，若未指定则根据文件前缀生成"""
        if self.net_file is None:
            self.net_file = f'{self._get_file_prefix()}.net.xml'
    
        return self.net_file
    
    def _gen_roadnet(self):
        """根据配置数据生成路网对象"""
        self.roadnet = self.converter.convert(self.roadnet_cfg_data)
        
        return self.roadnet
    
    def _gen_node_file(self):
        node_file = self._get_node_file()
        node_xml = self.roadnet.gen_node_xml()
        path = f'{self.output_dir}/{node_file}'
        with open(path, 'w') as f:
            f.write(node_xml)
        # 记录为本次仿真创建的文件
        self._created_files.add(path)
        return node_file

    def _gen_edg_file(self):
        edg_file = self._get_edg_file()
        edg_xml = self.roadnet.gen_edge_xml()
        path = f'{self.output_dir}/{edg_file}'
        with open(path, 'w') as f:
            f.write(edg_xml)
        self._created_files.add(path)
        return edg_file

    def _gen_conn_file(self):
        conn_file = self._get_conn_file()
        conn_xml = self.roadnet.gen_conn_xml()
        path = f'{self.output_dir}/{conn_file}'
        with open(path, 'w') as f:
            f.write(conn_xml)
        self._created_files.add(path)
        return conn_file

    def _gen_tll_file(self):
        tll_file = self._get_tll_file()
        tll_xml = self.roadnet.gen_tl_xml()
        path = f'{self.output_dir}/{tll_file}'
        with open(path, 'w') as f:
            f.write(tll_xml)
        self._created_files.add(path)
        return tll_file

    def _acquire_file_lock(self, lock_path: str, wait_interval: float = 0.05, timeout: float = 30.0):
        """
        生成/使用 net 的原子锁工具函数（避免多个进程同时 netconvert）
        通过创建一个独占 lock 文件实现进程间锁，若已存在则轮询等待直到超时。
        原理：os.open with O_CREAT|O_EXCL 是原子的。
        """
        start = time.time()
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                # 我们可以写入创建者 PID 便于调试
                os.write(fd, str(os.getpid()).encode('utf-8'))
                os.close(fd)
                return True
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                # 已存在 lock 文件 => 说明其他进程在构建 net，等待
                if (time.time() - start) > timeout:
                    raise TimeoutError(f"等待锁超时: {lock_path}")
                time.sleep(wait_interval)

    def _release_file_lock(self, lock_path: str):
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass

    def _gen_roadnet_file(self):
        """根据路网对象生成路网文件（带缓存/锁以避免重复 netconvert）"""
        self._gen_roadnet()
        node_file = self._gen_node_file()
        edg_file = self._gen_edg_file()
        conn_file = self._gen_conn_file()
        tll_file = self._gen_tll_file()

        net_file = self._get_net_file()
        output_net_path = f'{self.output_dir}/{net_file}'

        # 如果 net 文件存在，则直接返回
        if os.path.exists(output_net_path):
            # logger.info(f"找到已存在的路网文件，跳过 netconvert: {output_net_path}")
            return net_file

        # 否则创建一个基于 file_prefix 的 lock 来避免并发 netconvert
        lock_path = f'{self.output_dir}/{self._get_file_prefix()}.net.lock'

        try:
            self._acquire_file_lock(lock_path, wait_interval=0.05, timeout=60.0)
            # 再次检查（避免在等待锁时其他进程已生成）
            if os.path.exists(output_net_path):
                logger.info(f"其他进程已生成路网文件，跳过 netconvert: {output_net_path}")
                return net_file

            cmd = [
                'netconvert',
                '--node-files', f'{self.output_dir}/{node_file}',
                '--edge-files', f'{self.output_dir}/{edg_file}',
                '--connection-files', f'{self.output_dir}/{conn_file}',
                '--tllogic-files', f'{self.output_dir}/{tll_file}',
                '--output-file', f'{self.output_dir}/{net_file}'
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"netconvert执行失败，退出码: {e.returncode}")
                logger.error(f"错误输出: {e.stderr}")
                raise
            except FileNotFoundError:
                logger.error("未找到netconvert命令，请确保SUMO已正确安装并添加到PATH环境变量中")
                raise
            self._created_files.add(output_net_path)
        finally:
            # 释放锁
            self._release_file_lock(lock_path)
        return net_file
    
    def _gen_rou_file(self):
        rou_file = self._get_rou_file()
        rou_xml = self.roadnet.gen_route_xml()
        path = f'{self.output_dir}/{rou_file}'
        with open(path, 'w') as f:
            f.write(rou_xml)
        self._created_files.add(path)
        return rou_file

    def _gen_reroute_file(self):
        reroute_file = self._get_reroute_file()
        reroute_xml = self.roadnet.gen_reroute_xml()
        path = f'{self.output_dir}/{reroute_file}'
        with open(path, 'w') as f:
            f.write(reroute_xml)
        self._created_files.add(path)
        return reroute_file

    def _gen_vehtype_file(self):
        vehtype_file = self._get_vehtype_file()
        vehtype_xml = VehType(DEFAULT_VEH_TYPE).to_xml()
        path = f'{self.output_dir}/{vehtype_file}'
        with open(path, 'w') as f:
            f.write(vehtype_xml)
        self._created_files.add(path)
        return vehtype_file

    def _gen_sumo_cfg(self) -> str:
        """根据路网对象生成SUMO配置文件"""
        # 计算仿真持续时间，确保能够 cover 所有车辆
        
        net_file = self._gen_roadnet_file() 
        rou_file = self._gen_rou_file()
        reroute_file = self._gen_reroute_file()
        vehtype_file = self._gen_vehtype_file()
        sumo_cfg_file = self._get_sumo_cfg_file()
        max_sim_time = self.roadnet_cfg_data['max_sim_time']
        xml = ''
        xml += f'<configuration>\n'
        xml += f'    <input>\n'
        xml += f'        <net-file value="{net_file}" />\n'
        xml += f'        <route-files value="{rou_file}" />\n'
        xml += f'        <additional-files value="{reroute_file},{vehtype_file}" />\n'
        xml += f'    </input>\n'
        xml += f'    <random_number>\n'
        xml += f'        <seed>42</seed>\n'
        xml += f'    </random_number>\n'
        xml += f'    <time>\n'
        xml += f'        <begin value="0" />\n'
        xml += f'        <end value="{max_sim_time}" />\n'
        xml += f'    </time>\n'
        xml += f'</configuration>\n'

        path = f'{self._get_output_dir()}/{sumo_cfg_file}'
        with open(path, 'w') as f:
            f.write(xml)
        self._created_files.add(path)
        return sumo_cfg_file
    
    def _get_sim_output_file_prefix(self):
        """获取仿真生成的输出文件前缀，若未指定则根据文件前缀生成"""
        # 不同请求可能会使用同样路网进行仿真，生成的输出文件需要进行区分，使用ns时间戳作为前缀
        return time.time_ns()

    def _get_tripinfo_file(self):
        """获取仿真生成的行程信息文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-tripinfo.xml'
    
    def _get_emission_file(self):
        """获取仿真生成的排放信息文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-emission.xml'

    def _get_fcd_output_file(self):
        """获取仿真生成的FCD(Floating Car Data)输出文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-fcd_output.xml'
    
    def _get_queue_output_file(self):
        """获取仿真生成的Queue（排队数据）输出文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-queues.xml'

    def _get_tripinfo_output_file(self):
        """获取仿真生成的tripinfo（行程信息）输出文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-tripinfo.xml'

    def _get_tripinfo_json_file(self):
        """获取单车指标的json输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-tripinfo.json'

    def _get_diagram_json_file(self):
        """获取单车指标的json输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-diagram.json'

    def _get_forward_trajectroy_json_file(self):
        """获取正向协调FCD(Floating Car Data)自定义json的输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-forward_traj.json'

    def _get_backward_trajectroy_json_file(self):
        """获取反向协调FCD(Floating Car Data)自定义json的输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-backward_traj.json'

    def _calculate_parking_metrics(self, xml_file, filter_road=None, road_map_id={}):
        """统计每个路段的停车率、总停车次数和车均停车次数，同一路段停车间隔需超过WAITING_TIME_INTERVAL秒才累计次数
        同时计算指定路段的车均平均行程速度"""
        # 存储数据结构
        road_vehicles = collections.defaultdict(set)  # 路段上出现的车辆
        road_parking_vehicles = collections.defaultdict(set)  # 路段上停过车的车辆
        road_total_parking = collections.defaultdict(int)  # 路段总停车次数
        vehicle_road_status = collections.defaultdict(dict)  # {vehicle_id: {road: has_parked}}
        vehicle_road_parking_status = collections.defaultdict(dict)  # {vehicle_id: {road: is_parking}}
        # 新增：记录车辆在路段上次停车结束的时间步 {vehicle_id: {road: last_end_time}}
        vehicle_road_last_parking_end = collections.defaultdict(dict)

        # 新增：用于计算速度的数据结构
        vehicle_road_speeds = collections.defaultdict(
            lambda: collections.defaultdict(list))  # {vehicle_id: {road: [speeds]}}

        # 等待时间
        vehicles_waiting_time = 0

        for event, elem in ET.iterparse(xml_file, events=('end',)):
            if elem.tag != 'timestep':
                continue

            current_time = float(elem.get('time', 0))
            for vehicle in elem.findall('vehicle'):
                vehicle_id = vehicle.get('id')
                lane_info = vehicle.get('lane', '').split('_')
                if len(lane_info) > 2:
                    continue
                road = lane_info[0]
                if filter_road and road not in filter_road:
                    continue
                speed = float(vehicle.get('speed', 0))

                road = road_map_id.get(road, road)
                road_vehicles[road].add(vehicle_id)
                vehicle_road_speeds[vehicle_id][road].append(speed)

                # 检查是否停车（速度小于5km/h）
                if speed < WAITING_SPEED:
                    # 统计停车等待时间
                    vehicles_waiting_time += 1
                    # 检查该车辆在该路段是否已经统计过停车（用于停车率计算）
                    if not vehicle_road_status.get(vehicle_id, {}).get(road, False):
                        road_parking_vehicles[road].add(vehicle_id)
                        # 标记该车辆在该路段已经统计过停车
                        vehicle_road_status[vehicle_id][road] = True

                    # 统计停车次数（考虑多次停车及时间间隔）
                    current_parking_status = vehicle_road_parking_status.get(vehicle_id, {}).get(road, False)
                    if not current_parking_status:
                        # 检查上次停车结束时间，确保间隔超过WAITING_TIME_INTERVAL秒
                        last_end_time = vehicle_road_last_parking_end.get(vehicle_id, {}).get(road, -float('inf'))
                        time_interval = current_time - last_end_time
                        # 首次停车或间隔超过WAITING_TIME_INTERVAL秒才累计次数
                        if time_interval > WAITING_TIME_INTERVAL or last_end_time == -float('inf'):
                            road_total_parking[road] += 1
                        # 更新停车状态为正在停车
                        vehicle_road_parking_status[vehicle_id][road] = True
                else:
                    # 车辆在移动，更新停车状态和上次结束时间
                    if vehicle_id in vehicle_road_parking_status:
                        # 如果之前是停车状态，记录当前时间为停车结束时间
                        if vehicle_road_parking_status[vehicle_id].get(road, False):
                            vehicle_road_last_parking_end[vehicle_id][road] = current_time
                        # 重置当前停车状态
                        vehicle_road_parking_status[vehicle_id][road] = False

            elem.clear()
        # 计算每个路段的统计指标
        parking_metrics = {}
        for road in road_vehicles:
            total_vehicles = len(road_vehicles[road])
            parking_vehicles = len(road_parking_vehicles.get(road, set()))
            total_parking = road_total_parking.get(road, 0)

            # 计算停车率
            parking_ratio = parking_vehicles / total_vehicles if total_vehicles > 0 else 0.0
            # 计算路段车均停车次数
            avg_parking_per_vehicle = total_parking / total_vehicles if total_vehicles > 0 else 0.0

            # 新增：计算该路段的车均平均行程速度
            road_speeds = []
            road_non_stop_speeds = []
            for vehicle_id in road_vehicles[road]:
                if vehicle_id in vehicle_road_speeds and road in vehicle_road_speeds[vehicle_id]:
                    speeds = vehicle_road_speeds[vehicle_id][road]
                    if speeds:  # 确保有速度数据
                        avg_vehicle_speed = sum(speeds) / len(speeds)  # 车辆在该路段的平均速度(m/s)
                        road_speeds.append(avg_vehicle_speed)
                        # 计算非停车速度
                        non_stop_speeds = [speed for speed in speeds if speed >= WAITING_SPEED]
                        if non_stop_speeds:
                            road_non_stop_speeds.append(sum(non_stop_speeds) / len(non_stop_speeds))

            # 计算路段车均平均速度
            avg_road_speed = sum(road_speeds) / len(road_speeds) if road_speeds else 0.0
            avg_road_non_stop_speed = sum(road_non_stop_speeds) / len(road_non_stop_speeds) if road_non_stop_speeds else 0.0

            parking_metrics[road] = {
                'total_vehicles': total_vehicles,
                'parking_vehicles': parking_vehicles,
                'total_parking': total_parking,
                'parking_ratio': round(parking_ratio, DECIMAL_NUMBER),
                'avg_parking_per_vehicle': round(avg_parking_per_vehicle, DECIMAL_NUMBER),  # 路段车均停车次数
                'avg_travel_speed_kmh': round(avg_road_speed * 3.6, DECIMAL_NUMBER),  # 车均平均行程速度(km/h)
                'avg_non_stop_speed_kmh': round(avg_road_non_stop_speed * 3.6, DECIMAL_NUMBER) # 车均非停车速度(km/h)
            }

        # 获取正向和反向的协调路段编号
        coor_roads = []
        for coor_route_obj in self.cfg_parser.coor_routes.routes:
            route_edges = set(road_map_id.get(edge, edge) for edge in coor_route_obj.route_edges)
            coor_roads.append(route_edges)

        # 计算从起点到终点的车辆的指标
        coor_roads_index = collections.defaultdict(list)
        for vehicle_id, travel_road in vehicle_road_speeds.items():
            travel_road_set = set(travel_road.keys())
            if travel_road_set in coor_roads:
                road_speeds = []
                for road in travel_road:
                    speeds = vehicle_road_speeds[vehicle_id][road]
                    avg_vehicle_speed = sum(speeds) / len(speeds)
                    road_speeds.append(avg_vehicle_speed)
                avg_road_speed = sum(road_speeds) / len(road_speeds) if road_speeds else 0.0
                coor_index = coor_roads.index(travel_road_set)
                coor_road_id = self.cfg_parser.coor_road_id[coor_index]
                coor_roads_index[coor_road_id].append(avg_road_speed)
        for road_id, travel_speeds in coor_roads_index.items():
            parking_metrics[road_id] = {'avg_travel_speed_kmh': 3.6 * sum(travel_speeds) / len(travel_speeds),
                                        'total_vehicles': len(travel_speeds)}
        return parking_metrics, vehicles_waiting_time


    def _calculate_statistics(self, parking_metrics, filter_road=None, road_length_dict={}):
        """计算统计结果，包含每个路段的车均停车次数"""

        # 计算总体统计
        if filter_road is None:
            filter_road = list(parking_metrics.keys())
        total_vehicles = sum(stats.get('total_vehicles', 0) for road_id, stats in parking_metrics.items() if road_id in filter_road)
        total_parking_vehicles = sum(stats.get('parking_vehicles', 0) for road_id, stats in parking_metrics.items() if road_id in filter_road)
        avg_parking_ratio = total_parking_vehicles / total_vehicles if total_vehicles > 0 else 0
        total_distance = max(1, sum(info.get('total_vehicles', 0) * road_length_dict.get(road_id, 100)
                                    for road_id, info in parking_metrics.items() if road_id in filter_road))
        overall_avg_speed_kmh = sum(info.get('avg_travel_speed_kmh', 0) * info.get('total_vehicles', 0) * road_length_dict.get(road_id, 100)
                                    for road_id, info in parking_metrics.items() if road_id in filter_road) / total_distance
        overall_avg_non_stop_speed_kmh = sum(info.get('avg_non_stop_speed_kmh', 0) * info.get('total_vehicles', 0) * road_length_dict.get(road_id, 100)
                                    for road_id, info in parking_metrics.items() if road_id in filter_road) / total_distance
        return round(avg_parking_ratio, DECIMAL_NUMBER), round(overall_avg_speed_kmh, DECIMAL_NUMBER), round(overall_avg_non_stop_speed_kmh, DECIMAL_NUMBER)

    def _gen_fcd_output_json(self, fcd_output_file, road_section_length_dict, road_map_id={}):
        """处理sumo原始轨迹xml（重点更新车道编号lane和车道距离pos），适配时距图绘制；输出json"""
        # 正反向的协调路段
        coor_roads, coor_dist = self._get_coor_roads_info(road_section_length_dict)

        forward_fcd_trajectory = collections.defaultdict(list)
        backward_fcd_trajectory = collections.defaultdict(list)
        for event, timestep in ET.iterparse(fcd_output_file, events=('end',)):
            if timestep.tag != 'timestep':
                continue
            sim_time = int(float(timestep.get('time', 0)))
            for vehicle in timestep.findall('vehicle'):
                vehicle_id = vehicle.get('id')
                lane_info = vehicle.get('lane', '').split('_')
                if len(lane_info) > 2:
                    continue
                road = lane_info[0]
                if road not in road_map_id:
                    continue

                # 获取车辆在道路的绝对位置
                road_pos = float(vehicle.get('pos', 0))
                coor_index, coor_pos = self._get_vehicle_abs_pos(road, road_pos, road_section_length_dict, road_map_id)

                # 车辆位于正向协调道路上
                if coor_index == 0:
                    forward_fcd_trajectory[vehicle_id].append({'timestamp': sim_time, 'dis': coor_pos})
                # 车辆位于反向协调道路上
                elif coor_index == 1:
                    backward_fcd_trajectory[vehicle_id].append({'timestamp': sim_time, 'dis': coor_pos})
            timestep.clear()
        # 转换每辆车的轨迹格式，每辆车包含一个连续轨迹的列表
        forward_traj = convert_trajectory_format(forward_fcd_trajectory)
        backward_traj = convert_trajectory_format(backward_fcd_trajectory)

        # 获取正向和反向的交叉口信息
        cross_list = ['START'] + self.cfg_parser.cross_list + ['END']
        forward_cross_loc = [{'cross_id': cross_id, 'cross_name': cross_id, 'dis': 0 if i == 0 else sum(coor_dist[:i])}
                             for i, cross_id in enumerate(cross_list)]
        backward_cross_loc = [{'cross_id': cross_id, 'cross_name': cross_id, 'dis': 0 if i == 0 else sum(coor_dist[::-1][:i])}
                             for i, cross_id in enumerate(cross_list[::-1])]

        forward_fcd_output = {"cross_loc": forward_cross_loc, "forward_traj": forward_traj}
        backward_fcd_output = {"cross_loc": backward_cross_loc, "forward_traj": backward_traj}

        # 生成正向轨迹的json
        forward_fcd_json_file = f'{self.output_dir}/{self._get_forward_trajectroy_json_file()}'
        with open(forward_fcd_json_file, "w", encoding="utf-8") as f:
            json.dump({"data": forward_fcd_output}, f, indent=4)

        # 生成反向轨迹的json
        backward_fcd_json_file = f'{self.output_dir}/{self._get_backward_trajectroy_json_file()}'
        with open(backward_fcd_json_file, "w", encoding="utf-8") as f:
            json.dump({"data": backward_fcd_output}, f, indent=4)
        self._created_files.add(forward_fcd_json_file)
        self._created_files.add(backward_fcd_json_file)

    def _get_vehicle_abs_pos(self, road_id, road_pos, road_section_length_dict, road_map_id):
        """获取车辆在道路的绝对位置"""

        new_road = road_map_id.get(road_id, road_id)
        # 获取pos的值
        road_section_list = self.cfg_parser.road_section_info.get(new_road, [])
        coor_roads, coor_dist = self._get_coor_roads_info(road_section_length_dict)

        if road_section_list:
            index = road_section_list.index(road_id)
            road_pos += sum([road_section_length_dict[section] for section in road_section_list[:index]])

        coor_pos = road_pos
        if new_road in coor_roads[0]:
            coor_index = 0
        elif new_road in coor_roads[1]:
            coor_index = 1
        else:
            coor_index = -1

        # 车辆位于正向协调道路上
        if coor_index == 0:
            road_index = coor_roads[coor_index].index(new_road)
            coor_pos += sum([length for length in coor_dist[:road_index]])
        # 车辆位于反向协调道路上
        elif coor_index == 1:
            road_index = coor_roads[coor_index].index(new_road)
            coor_pos += sum([length for length in coor_dist[road_index + 1:]])
        return coor_index, coor_pos

    def _get_coor_roads_info(self, road_section_length_dict):
        """获取以交叉口间路段表示的协调道路信息"""
        coor_roads = []
        road_map_id = self.cfg_parser.road_map_id['forward'] | self.cfg_parser.road_map_id['backward']
        for edges in self.cfg_parser.coor_routes.routes:
            direction_roads = []
            for edge_id in edges.route_edges:
                road_id = road_map_id.get(edge_id, edge_id)
                if road_id not in direction_roads:
                    direction_roads.append(road_id)
            coor_roads.append(direction_roads)
        coor_roads[-1] = coor_roads[-1][::-1]

        coor_dist = []
        for road_id in coor_roads[0]:
            road_section_list = self.cfg_parser.road_section_info.get(road_id, [])
            if road_section_list:
                road_length = sum(road_section_length_dict.get(section, 0) for section in road_section_list)
            else:
                road_length = road_section_length_dict.get(road_id, 0)
            coor_dist.append(road_length)
        return coor_roads, coor_dist

    def _analyze_vehicle_trip(self, tripinfo_file):
        """分析单车的指标"""
        vehicles_index = collections.defaultdict(dict)
        for event, trip in ET.iterparse(tripinfo_file, events=('end',)):
            if trip.tag != 'tripinfo':
                continue
            id = trip.get('id')
            # 单车进入和离开位置
            depart_lane = trip.get('departLane')
            depart_pos = float(trip.get('departPos'))
            arrival_lane = trip.get('arrivalLane')
            arrival_pos = float(trip.get('arrivalPos'))
            # 单车行程时间和行程距离
            travel_time = int(float(trip.get('duration')))
            travel_length = float(trip.get('routeLength'))
            # 单车停车速度和不停车速度
            stop_speed = round(3.6 * travel_length / travel_time, DECIMAL_NUMBER)
            non_stop_speed = round(3.6 * travel_length / (travel_time - float(trip.get('waitingTime'))), DECIMAL_NUMBER)
            # 拼接单车的指标
            vehicles_index[id] = {'depart_lane': depart_lane, 'depart_pos': depart_pos, 'arrival_lane': arrival_lane,
                                  'arrival_pos': arrival_pos, 'travel_time': travel_time, 'travel_length': travel_length,
                                  'stop_speed': stop_speed, 'non_stop_speed': non_stop_speed}
            trip.clear()

        tripinfo_out_file = f'{self.output_dir}/{self._get_tripinfo_json_file()}'
        with open(tripinfo_out_file, "w", encoding="utf-8") as f:
            json.dump(vehicles_index, f, indent=4)
        self._created_files.add(tripinfo_out_file)

    def _analyze_queue_output(self, queue_file, filter_road=None, road_map_id={}):
        """分析排队输出文件"""
        total_timesteps = set()
        lane_ids = set()
        max_queue_length = 0.0
        max_experimental_queue_length = 0.0
        max_queueing_time = 0.0
        total_queue_length = 0.0
        total_queueing_time = 0.0
        total_samples = 0
        lane_max = {}
        timestep_sum = collections.defaultdict(float)
        road_timestep_agg = collections.defaultdict(lambda: {'queueing_time': 0.0, 'queueing_length': 0.0, 'queueing_length_experimental': 0.0})

        for event, data_elem in ET.iterparse(queue_file, events=('end',)):
            if data_elem.tag != 'data':
                continue
            timestep = float(data_elem.get('timestep', 0))
            lanes_elem = data_elem.find('lanes')
            if lanes_elem is not None:
                for lane_elem in lanes_elem.findall('lane'):
                    lane_id = lane_elem.get('id', '')
                    lane_info = lane_id.split('_')
                    if len(lane_info) > 2:
                        continue
                    road = lane_info[0]
                    if filter_road and road not in filter_road:
                        continue

                    long_road = road_map_id.get(road, road)
                    queueing_time = float(lane_elem.get('queueing_time', 0))
                    queueing_length = float(lane_elem.get('queueing_length', 0))
                    queueing_length_experimental = float(lane_elem.get('queueing_length_experimental', 0))

                    total_timesteps.add(timestep)
                    lane_ids.add(lane_id)
                    total_samples += 1
                    total_queue_length += queueing_length
                    total_queueing_time += queueing_time
                    max_queue_length = max(max_queue_length, queueing_length)
                    max_experimental_queue_length = max(max_experimental_queue_length, queueing_length_experimental)
                    max_queueing_time = max(max_queueing_time, queueing_time)
                    lane_max[lane_id] = max(lane_max.get(lane_id, 0.0), queueing_length)
                    timestep_sum[timestep] += queueing_length

                    agg = road_timestep_agg[(long_road, timestep)]
                    agg['queueing_time'] = max(agg['queueing_time'], queueing_time)
                    agg['queueing_length'] += queueing_length
                    agg['queueing_length_experimental'] += queueing_length_experimental

            data_elem.clear()

        if total_samples == 0:
            return {}

        road_grouped = collections.defaultdict(list)
        for (long_road, timestep), agg in road_timestep_agg.items():
            road_grouped[long_road].append(agg)

        road_detailed_stats = {}
        for road, entries in road_grouped.items():
            queue_lengths = [item['queueing_length'] for item in entries]
            road_detailed_stats[road] = {
                'avg_queue_length': sum(queue_lengths) / len(queue_lengths),
                'max_queue_length': max(queue_lengths)
            }

        return {
            'total_timesteps': len(total_timesteps),
            'total_lanes_with_queues': len(lane_ids),
            'max_queue_length': max_queue_length,
            'max_experimental_queue_length': max_experimental_queue_length,
            'avg_queue_length': total_queue_length / total_samples,
            'max_queueing_time': max_queueing_time,
            'avg_queueing_time': total_queueing_time / total_samples,
            'most_congested_lane': max(lane_max, key=lane_max.get) if lane_max else None,
            'most_congested_timestep': max(timestep_sum, key=timestep_sum.get) if timestep_sum else None,
            'road_detailed_stats': road_detailed_stats,
        }

    def _simulate(self):
        """运行SUMO仿真"""
        # 从 $SUMO_HOME/tools 导入python模块
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")

        sumo_cfg_file = f'{self.output_dir}/{self._get_sumo_cfg_file()}'
        fcd_out_file = f'{self.output_dir}/{self._get_fcd_output_file()}'
        queue_out_file = f'{self.output_dir}/{self._get_queue_output_file()}'
        tripinfo_out_file = f'{self.output_dir}/{self._get_tripinfo_output_file()}'
        network_out_file = f'{self.output_dir}/{self._get_net_file()}'
        self._created_files.add(fcd_out_file)
        if self.enable_queue_output:
            self._created_files.add(queue_out_file)
        if self.enable_tripinfo_output:
            self._created_files.add(tripinfo_out_file)

        cmd = [
            'sumo',
            '-c', sumo_cfg_file,
        ]
        cmd.extend(['--fcd-output', fcd_out_file])
        if self.fcd_period > 1:
            cmd.extend(['--device.fcd.period', str(self.fcd_period)])
        if self.enable_queue_output:
            cmd.extend(['--queue-output', queue_out_file])
        if self.enable_tripinfo_output:
            cmd.extend(['--tripinfo-output', tripinfo_out_file])
        if self.enable_sumo_perf_options:
            cmd.extend(['--no-step-log', 'true', '--duration-log.disable', 'true'])
        
        try:
            # 执行命令
            with self._profile_stage('sumo_run'):
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"sumo执行失败，退出码: {e.returncode}")
            logger.error(f"错误输出: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.error("未找到sumo命令，请确保SUMO已正确安装并添加到PATH环境变量中")
            raise

        self._record_file_size('fcd_output', fcd_out_file)
        if self.enable_queue_output:
            self._record_file_size('queue_output', queue_out_file)
        if self.enable_tripinfo_output:
            self._record_file_size('tripinfo_output', tripinfo_out_file)

        forward_roads = self.cfg_parser.coor_routes.routes[0].route_edges
        backward_roads = self.cfg_parser.coor_routes.routes[1].route_edges
        selected_road = forward_roads + backward_roads
        road_map_id = self.cfg_parser.road_map_id['forward'] | self.cfg_parser.road_map_id['backward']
        # 添加起点入口段和终点出口段
        road_map_id.update({forward_roads[0]: forward_roads[0], forward_roads[-1]: forward_roads[-1],
                            backward_roads[0]: backward_roads[0], backward_roads[-1]: backward_roads[-1]})
        road_length_dict = self.cfg_parser.road_length_dict

        # 并行计算：把 fcd 解析（停车指标）和 queue 解析并行化
        with ThreadPoolExecutor(max_workers=2 if self.enable_queue_output else 1) as tpe:
            fut_parking = tpe.submit(self._profiled_parking_metrics, fcd_out_file, selected_road, road_map_id)
            fut_queue = tpe.submit(self._profiled_queue_output, queue_out_file, selected_road, road_map_id) if self.enable_queue_output else None

            parking_metrics, waiting_time = fut_parking.result()
            queue_stat = fut_queue.result() if fut_queue else {}

        # 正向道路
        forward_roads = list(self.cfg_parser.road_map_id['forward'].values())
        # 反向道路
        backward_roads = list(self.cfg_parser.road_map_id['backward'].values())

        # 双向道路
        filter_road = forward_roads + backward_roads
        avg_waiting_ratio, avg_speed, avg_non_stop_speed = self._calculate_statistics(parking_metrics, filter_road, road_length_dict)

        # 正向指标
        forward_avg_waiting_ratio, forward_avg_speed, _ = self._calculate_statistics(parking_metrics, forward_roads, road_length_dict)

        # 反向指标
        backward_avg_waiting_ratio, backward_avg_speed, _ = self._calculate_statistics(parking_metrics, backward_roads, road_length_dict)

        # 起点到终点的行程指标
        filter_road = self.cfg_parser.coor_road_id
        _, travel_speed, _ = self._calculate_statistics(parking_metrics, filter_road, road_length_dict)

        avg_queue_length = queue_stat.get('avg_queue_length') if isinstance(queue_stat, dict) else None

        if self.cfg.get('config', {}).get('supportDiagram', False):
            with self._profile_stage('support_diagram_postprocess'):
                road_section_length_dict = extract_edge_lengths(network_out_file)
                with ThreadPoolExecutor(max_workers=2 if self.enable_tripinfo_output else 1) as tpe:
                    futures = [tpe.submit(self._gen_fcd_output_json, fcd_out_file, road_section_length_dict, road_map_id)]
                    if self.enable_tripinfo_output:
                        futures.append(tpe.submit(self._profiled_tripinfo_analysis, tripinfo_out_file))
                    for future in futures:
                        future.result()
        # 返回道路层的群体指标，用于相位差方案评估
        return {
            'parking_metrics': parking_metrics,
            'waiting_time': waiting_time,
            'avg_waiting_ratio': avg_waiting_ratio,
            'avg_speed': avg_speed,
            'avg_non_stop_speed': avg_non_stop_speed,
            'avg_queue_length': avg_queue_length,
            'outbound': {'avg_speed': forward_avg_speed, 'avg_waiting_ratio': forward_avg_waiting_ratio},
            'inbound': {'avg_speed': backward_avg_speed, 'avg_waiting_ratio': backward_avg_waiting_ratio},
            'avg_travel_time': round(3.6 * sum(self.cfg_parser.road_length) / travel_speed, DECIMAL_NUMBER) if travel_speed > 0 else 0
        }

    def _profiled_parking_metrics(self, xml_file, filter_road=None, road_map_id={}):
        with self._profile_stage('fcd_parse'):
            return self._calculate_parking_metrics(xml_file, filter_road, road_map_id)

    def _profiled_queue_output(self, queue_file, filter_road=None, road_map_id={}):
        with self._profile_stage('queue_parse'):
            return self._analyze_queue_output(queue_file, filter_road, road_map_id)

    def _profiled_tripinfo_analysis(self, tripinfo_file):
        with self._profile_stage('tripinfo_parse'):
            return self._analyze_vehicle_trip(tripinfo_file)
    
    def _cleanup_xml_files(self):
        """清理文件"""
        for p in list(self._created_files):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception as e:
                logger.warning(f"删除文件失败 {p}: {e}")


    def run(self):
        """运行仿真流程，包括路网生成、路由生成、配置文件生成和仿真运行"""
        try:
            with self._profile_stage('roadnet_generate'):
                self._gen_roadnet_file()
            with self._profile_stage('route_generate'):
                self._gen_rou_file()
            with self._profile_stage('sumocfg_generate'):
                self._gen_sumo_cfg()
            output = self._simulate()
            return output
        finally:
            try:
                with self._profile_stage('cleanup'):
                    self._cleanup_xml_files()
            except Exception as e:
                logger.error(f"清理文件时发生错误: {e}")
            finally:
                self._finalize_profiling()



# ----------------------------------------------------------------------------
# 原文件: main.py
# ----------------------------------------------------------------------------

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SUMO路网仿真评估主程序
"""
import json
import os
import sys
import traceback

import numpy as np



class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def main(input_json):
    try:
        input_data = json.loads(input_json)
        output = run_simulator_worker(input_data)
        return json.dumps(output, cls=NpEncoder, ensure_ascii=False)
    except Exception:
        trace = traceback.format_exc()
        logger.error('main failed\n%s', trace)
        return json.dumps({'error': 'internal_error', 'traceback': trace}, ensure_ascii=False)
