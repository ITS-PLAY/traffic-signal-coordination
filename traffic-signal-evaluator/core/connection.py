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
