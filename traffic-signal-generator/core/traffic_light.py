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
        self.coordination_phase = coordination_phase
        self.cycle = sum(self.durations.values())
    
    # 转换为完整JSON格式
    def to_json(self) -> dict:
        return {
            'id': self.id,
            'cross_id': self.cross_id,
            'phases': self.phases,
            'durations': self.durations,
            'functions': self.functions,
            'offset': self.offset
        }
    
    # 转换为字符串格式，TODO：需要补充更多信息
    def to_string(self) -> str:
        return f'{self.id} {self.cross_id}'
