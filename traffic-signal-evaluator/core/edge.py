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
