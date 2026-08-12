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
