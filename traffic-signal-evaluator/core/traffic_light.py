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
