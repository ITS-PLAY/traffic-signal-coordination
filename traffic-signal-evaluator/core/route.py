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
