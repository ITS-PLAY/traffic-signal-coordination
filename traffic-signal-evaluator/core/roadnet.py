#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from core.node import Node
from core.edge import Edge
from core.connection import Connection
from core.tl_logic import TLLogic
from core.route import Routes
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

