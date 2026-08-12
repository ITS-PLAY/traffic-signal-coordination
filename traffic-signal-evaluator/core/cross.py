from re import S
from core.edge import Edge
from core.point import Point
from typing import List, Dict, Any, Tuple
from core.traffic_light import TrafficLightPlan

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
