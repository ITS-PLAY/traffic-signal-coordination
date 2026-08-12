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
