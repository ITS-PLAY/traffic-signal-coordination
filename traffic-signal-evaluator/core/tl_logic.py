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
