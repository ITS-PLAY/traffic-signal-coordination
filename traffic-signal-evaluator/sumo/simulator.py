from typing import Any, Dict
from core.roadnet import Roadnet
from parse.parser import ConfigParser
from .converter import Converter
import json
import hashlib
import subprocess
from contextlib import contextmanager
from utils.logger import logger
import sys
import os
import time
import xml.etree.ElementTree as ET
import collections
from constants.constants import *
import errno
from concurrent.futures import ThreadPoolExecutor

from core.veh_type import VehType
from constants.constants import DEFAULT_VEH_TYPE, DECIMAL_NUMBER, WAITING_SPEED
from utils.util import extract_edge_lengths, convert_trajectory_format


def run_simulator_worker(cfg: dict) -> dict:
    """这个函数在子进程中执行：新建 Simulator(cfg) 并调用 run()"""
    cross_list = cfg.get('crossList', []) if isinstance(cfg, dict) else []
    logger.info('worker start: cross_count=%s, cross_list=%s', len(cross_list), cross_list)
    sim = Simulator(cfg)
    logger.info('worker initialized simulator successfully')
    return sim.run()


class Simulator:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.runtime_config = cfg.get('config', {}) if isinstance(cfg, dict) else {}
        self.enable_profiling = self.runtime_config.get('enableProfiling', os.environ.get('ENABLE_SIM_PROFILING', '0') == '1')
        self.enable_queue_output = self.runtime_config.get('enableQueueOutput', True)
        self.enable_tripinfo_output = self.runtime_config.get('enableTripinfoOutput', self.runtime_config.get('supportDiagram', False))
        self.enable_sumo_perf_options = self.runtime_config.get('enableSumoPerfOptions', True)
        self.fcd_period = max(1, int(self.runtime_config.get('fcdPeriod', os.environ.get('FCD_PERIOD', '1'))))
        self._profiling = collections.OrderedDict()
        # 初始化config parser解析输入数据
        self.cfg_parser: ConfigParser = ConfigParser(self.cfg)
        # 由原始配置数据解析通用的路网配置数据
        self.roadnet_cfg_data: Dict[str, Any] = self.cfg_parser.parse()
        # 初始化数据转换器
        self.converter: Converter = Converter()
        # 初始化roadnet对象为空
        self.roadnet: Roadnet = None
        # 初始化路网相关文件名为None
        self.net_file: str = None
        self.rou_file: str = None
        self.reroute_file: str = None
        self.vehtype_file: str = None
        self.sumo_cfg_file: str = None
        self.node_file: str = None
        self.edg_file: str = None
        self.conn_file: str = None
        self.tll_file: str = None
        self.output_dir: str = '/app/result'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        # 初始化文件前缀为空，后续根据解析的路网
        self.file_prefix: str = None
        # 记录本次仿真实际创建（写入）的文件完整路径
        self._created_files = set()

    @contextmanager
    def _profile_stage(self, stage_name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
            self._profiling[stage_name] = elapsed_ms
            if self.enable_profiling:
                logger.info('profile stage=%s elapsed_ms=%s', stage_name, elapsed_ms)

    def _record_file_size(self, label: str, path: str):
        if not self.enable_profiling:
            return
        if path and os.path.exists(path):
            size_bytes = os.path.getsize(path)
            self._profiling[f'{label}_bytes'] = size_bytes
            logger.info('profile artifact=%s size_bytes=%s path=%s', label, size_bytes, path)

    def _finalize_profiling(self):
        if self.enable_profiling and self._profiling:
            logger.info('profile summary=%s', json.dumps(self._profiling, ensure_ascii=False))

    
    def _get_output_dir(self):
        """获取输出目录，确保目录存在"""
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        return self.output_dir
    
    def _get_file_prefix(self):
        """根据配置数据生成文件前缀，同样的配置数据，生成的文件前缀也相同，后续可以根据文件前缀来判断是否需要重新生成路网文件"""
        if self.file_prefix is None:
            self.file_prefix = hashlib.md5(json.dumps(self.cfg_parser.to_json(), sort_keys=True).encode('utf-8')).hexdigest()

        return self.file_prefix

    def _get_node_file(self):
        """获取节点文件路径，若未指定则根据文件前缀生成"""
        if self.node_file is None:
            self.node_file = f'{self._get_file_prefix()}.node.xml'
    
        return self.node_file
    
    def _get_edg_file(self):
        """获取边文件路径，若未指定则根据文件前缀生成"""
        if self.edg_file is None:
            self.edg_file = f'{self._get_file_prefix()}.edg.xml'
    
        return self.edg_file
    
    def _get_conn_file(self):
        """获取连接文件路径，若未指定则根据文件前缀生成"""
        if self.conn_file is None:
            self.conn_file = f'{self._get_file_prefix()}.conn.xml'
    
        return self.conn_file
    
    def _get_tll_file(self):
        """获取交通灯文件路径，若未指定则根据文件前缀生成"""
        if self.tll_file is None:
            self.tll_file = f'{self._get_file_prefix()}.tll.xml'
    
        return self.tll_file
    
    def _get_rou_file(self):
        """获取路由文件路径，若未指定则根据文件前缀生成"""
        if self.rou_file is None:
            self.rou_file = f'{self._get_file_prefix()}.rou.xml'
    
        return self.rou_file

    def _get_reroute_file(self):
        """获取路由文件路径，若未指定则根据文件前缀生成"""
        if self.reroute_file is None:
            self.reroute_file = f'{self._get_file_prefix()}reroute.add.xml'

        return self.reroute_file

    def _get_vehtype_file(self):
        """获取路由文件路径，若未指定则根据文件前缀生成"""
        if self.vehtype_file is None:
            self.vehtype_file = f'{self._get_file_prefix()}veh.add.xml'

        return self.vehtype_file
    
    def _get_sumo_cfg_file(self):
        """获取SUMO配置文件路径，若未指定则根据文件前缀生成"""
        if self.sumo_cfg_file is None:
            self.sumo_cfg_file = f'{self._get_file_prefix()}.sumocfg'
    
        return self.sumo_cfg_file
    
    def _get_net_file(self):
        """获取路网文件路径，若未指定则根据文件前缀生成"""
        if self.net_file is None:
            self.net_file = f'{self._get_file_prefix()}.net.xml'
    
        return self.net_file
    
    def _gen_roadnet(self):
        """根据配置数据生成路网对象"""
        self.roadnet = self.converter.convert(self.roadnet_cfg_data)
        
        return self.roadnet
    
    def _gen_node_file(self):
        node_file = self._get_node_file()
        node_xml = self.roadnet.gen_node_xml()
        path = f'{self.output_dir}/{node_file}'
        with open(path, 'w') as f:
            f.write(node_xml)
        # 记录为本次仿真创建的文件
        self._created_files.add(path)
        return node_file

    def _gen_edg_file(self):
        edg_file = self._get_edg_file()
        edg_xml = self.roadnet.gen_edge_xml()
        path = f'{self.output_dir}/{edg_file}'
        with open(path, 'w') as f:
            f.write(edg_xml)
        self._created_files.add(path)
        return edg_file

    def _gen_conn_file(self):
        conn_file = self._get_conn_file()
        conn_xml = self.roadnet.gen_conn_xml()
        path = f'{self.output_dir}/{conn_file}'
        with open(path, 'w') as f:
            f.write(conn_xml)
        self._created_files.add(path)
        return conn_file

    def _gen_tll_file(self):
        tll_file = self._get_tll_file()
        tll_xml = self.roadnet.gen_tl_xml()
        path = f'{self.output_dir}/{tll_file}'
        with open(path, 'w') as f:
            f.write(tll_xml)
        self._created_files.add(path)
        return tll_file

    def _acquire_file_lock(self, lock_path: str, wait_interval: float = 0.05, timeout: float = 30.0):
        """
        生成/使用 net 的原子锁工具函数（避免多个进程同时 netconvert）
        通过创建一个独占 lock 文件实现进程间锁，若已存在则轮询等待直到超时。
        原理：os.open with O_CREAT|O_EXCL 是原子的。
        """
        start = time.time()
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                # 我们可以写入创建者 PID 便于调试
                os.write(fd, str(os.getpid()).encode('utf-8'))
                os.close(fd)
                return True
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                # 已存在 lock 文件 => 说明其他进程在构建 net，等待
                if (time.time() - start) > timeout:
                    raise TimeoutError(f"等待锁超时: {lock_path}")
                time.sleep(wait_interval)

    def _release_file_lock(self, lock_path: str):
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass

    def _gen_roadnet_file(self):
        """根据路网对象生成路网文件（带缓存/锁以避免重复 netconvert）"""
        self._gen_roadnet()
        node_file = self._gen_node_file()
        edg_file = self._gen_edg_file()
        conn_file = self._gen_conn_file()
        tll_file = self._gen_tll_file()

        net_file = self._get_net_file()
        output_net_path = f'{self.output_dir}/{net_file}'

        # 如果 net 文件存在，则直接返回
        if os.path.exists(output_net_path):
            # logger.info(f"找到已存在的路网文件，跳过 netconvert: {output_net_path}")
            return net_file

        # 否则创建一个基于 file_prefix 的 lock 来避免并发 netconvert
        lock_path = f'{self.output_dir}/{self._get_file_prefix()}.net.lock'

        try:
            self._acquire_file_lock(lock_path, wait_interval=0.05, timeout=60.0)
            # 再次检查（避免在等待锁时其他进程已生成）
            if os.path.exists(output_net_path):
                logger.info(f"其他进程已生成路网文件，跳过 netconvert: {output_net_path}")
                return net_file

            cmd = [
                'netconvert',
                '--node-files', f'{self.output_dir}/{node_file}',
                '--edge-files', f'{self.output_dir}/{edg_file}',
                '--connection-files', f'{self.output_dir}/{conn_file}',
                '--tllogic-files', f'{self.output_dir}/{tll_file}',
                '--output-file', f'{self.output_dir}/{net_file}'
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"netconvert执行失败，退出码: {e.returncode}")
                logger.error(f"错误输出: {e.stderr}")
                raise
            except FileNotFoundError:
                logger.error("未找到netconvert命令，请确保SUMO已正确安装并添加到PATH环境变量中")
                raise
            self._created_files.add(output_net_path)
        finally:
            # 释放锁
            self._release_file_lock(lock_path)
        return net_file
    
    def _gen_rou_file(self):
        rou_file = self._get_rou_file()
        rou_xml = self.roadnet.gen_route_xml()
        path = f'{self.output_dir}/{rou_file}'
        with open(path, 'w') as f:
            f.write(rou_xml)
        self._created_files.add(path)
        return rou_file

    def _gen_reroute_file(self):
        reroute_file = self._get_reroute_file()
        reroute_xml = self.roadnet.gen_reroute_xml()
        path = f'{self.output_dir}/{reroute_file}'
        with open(path, 'w') as f:
            f.write(reroute_xml)
        self._created_files.add(path)
        return reroute_file

    def _gen_vehtype_file(self):
        vehtype_file = self._get_vehtype_file()
        vehtype_xml = VehType(DEFAULT_VEH_TYPE).to_xml()
        path = f'{self.output_dir}/{vehtype_file}'
        with open(path, 'w') as f:
            f.write(vehtype_xml)
        self._created_files.add(path)
        return vehtype_file

    def _gen_sumo_cfg(self) -> str:
        """根据路网对象生成SUMO配置文件"""
        # 计算仿真持续时间，确保能够 cover 所有车辆
        
        net_file = self._gen_roadnet_file() 
        rou_file = self._gen_rou_file()
        reroute_file = self._gen_reroute_file()
        vehtype_file = self._gen_vehtype_file()
        sumo_cfg_file = self._get_sumo_cfg_file()
        max_sim_time = self.roadnet_cfg_data['max_sim_time']
        xml = ''
        xml += f'<configuration>\n'
        xml += f'    <input>\n'
        xml += f'        <net-file value="{net_file}" />\n'
        xml += f'        <route-files value="{rou_file}" />\n'
        xml += f'        <additional-files value="{reroute_file},{vehtype_file}" />\n'
        xml += f'    </input>\n'
        xml += f'    <random_number>\n'
        xml += f'        <seed>42</seed>\n'
        xml += f'    </random_number>\n'
        xml += f'    <time>\n'
        xml += f'        <begin value="0" />\n'
        xml += f'        <end value="{max_sim_time}" />\n'
        xml += f'    </time>\n'
        xml += f'</configuration>\n'

        path = f'{self._get_output_dir()}/{sumo_cfg_file}'
        with open(path, 'w') as f:
            f.write(xml)
        self._created_files.add(path)
        return sumo_cfg_file
    
    def _get_sim_output_file_prefix(self):
        """获取仿真生成的输出文件前缀，若未指定则根据文件前缀生成"""
        # 不同请求可能会使用同样路网进行仿真，生成的输出文件需要进行区分，使用ns时间戳作为前缀
        return time.time_ns()

    def _get_tripinfo_file(self):
        """获取仿真生成的行程信息文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-tripinfo.xml'
    
    def _get_emission_file(self):
        """获取仿真生成的排放信息文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-emission.xml'

    def _get_fcd_output_file(self):
        """获取仿真生成的FCD(Floating Car Data)输出文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-fcd_output.xml'
    
    def _get_queue_output_file(self):
        """获取仿真生成的Queue（排队数据）输出文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-queues.xml'

    def _get_tripinfo_output_file(self):
        """获取仿真生成的tripinfo（行程信息）输出文件路径，若未指定则根据文件前缀生成"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-tripinfo.xml'

    def _get_tripinfo_json_file(self):
        """获取单车指标的json输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-tripinfo.json'

    def _get_diagram_json_file(self):
        """获取单车指标的json输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-diagram.json'

    def _get_forward_trajectroy_json_file(self):
        """获取正向协调FCD(Floating Car Data)自定义json的输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-forward_traj.json'

    def _get_backward_trajectroy_json_file(self):
        """获取反向协调FCD(Floating Car Data)自定义json的输出文件路径"""
        return f'{self._get_file_prefix()}_{self._get_sim_output_file_prefix()}-backward_traj.json'

    def _calculate_parking_metrics(self, xml_file, filter_road=None, road_map_id={}):
        """统计每个路段的停车率、总停车次数和车均停车次数，同一路段停车间隔需超过WAITING_TIME_INTERVAL秒才累计次数
        同时计算指定路段的车均平均行程速度"""
        # 存储数据结构
        road_vehicles = collections.defaultdict(set)  # 路段上出现的车辆
        road_parking_vehicles = collections.defaultdict(set)  # 路段上停过车的车辆
        road_total_parking = collections.defaultdict(int)  # 路段总停车次数
        vehicle_road_status = collections.defaultdict(dict)  # {vehicle_id: {road: has_parked}}
        vehicle_road_parking_status = collections.defaultdict(dict)  # {vehicle_id: {road: is_parking}}
        # 新增：记录车辆在路段上次停车结束的时间步 {vehicle_id: {road: last_end_time}}
        vehicle_road_last_parking_end = collections.defaultdict(dict)

        # 新增：用于计算速度的数据结构
        vehicle_road_speeds = collections.defaultdict(
            lambda: collections.defaultdict(list))  # {vehicle_id: {road: [speeds]}}

        # 等待时间
        vehicles_waiting_time = 0

        for event, elem in ET.iterparse(xml_file, events=('end',)):
            if elem.tag != 'timestep':
                continue

            current_time = float(elem.get('time', 0))
            for vehicle in elem.findall('vehicle'):
                vehicle_id = vehicle.get('id')
                lane_info = vehicle.get('lane', '').split('_')
                if len(lane_info) > 2:
                    continue
                road = lane_info[0]
                if filter_road and road not in filter_road:
                    continue
                speed = float(vehicle.get('speed', 0))

                road = road_map_id.get(road, road)
                road_vehicles[road].add(vehicle_id)
                vehicle_road_speeds[vehicle_id][road].append(speed)

                # 检查是否停车（速度小于5km/h）
                if speed < WAITING_SPEED:
                    # 统计停车等待时间
                    vehicles_waiting_time += 1
                    # 检查该车辆在该路段是否已经统计过停车（用于停车率计算）
                    if not vehicle_road_status.get(vehicle_id, {}).get(road, False):
                        road_parking_vehicles[road].add(vehicle_id)
                        # 标记该车辆在该路段已经统计过停车
                        vehicle_road_status[vehicle_id][road] = True

                    # 统计停车次数（考虑多次停车及时间间隔）
                    current_parking_status = vehicle_road_parking_status.get(vehicle_id, {}).get(road, False)
                    if not current_parking_status:
                        # 检查上次停车结束时间，确保间隔超过WAITING_TIME_INTERVAL秒
                        last_end_time = vehicle_road_last_parking_end.get(vehicle_id, {}).get(road, -float('inf'))
                        time_interval = current_time - last_end_time
                        # 首次停车或间隔超过WAITING_TIME_INTERVAL秒才累计次数
                        if time_interval > WAITING_TIME_INTERVAL or last_end_time == -float('inf'):
                            road_total_parking[road] += 1
                        # 更新停车状态为正在停车
                        vehicle_road_parking_status[vehicle_id][road] = True
                else:
                    # 车辆在移动，更新停车状态和上次结束时间
                    if vehicle_id in vehicle_road_parking_status:
                        # 如果之前是停车状态，记录当前时间为停车结束时间
                        if vehicle_road_parking_status[vehicle_id].get(road, False):
                            vehicle_road_last_parking_end[vehicle_id][road] = current_time
                        # 重置当前停车状态
                        vehicle_road_parking_status[vehicle_id][road] = False

            elem.clear()
        # 计算每个路段的统计指标
        parking_metrics = {}
        for road in road_vehicles:
            total_vehicles = len(road_vehicles[road])
            parking_vehicles = len(road_parking_vehicles.get(road, set()))
            total_parking = road_total_parking.get(road, 0)

            # 计算停车率
            parking_ratio = parking_vehicles / total_vehicles if total_vehicles > 0 else 0.0
            # 计算路段车均停车次数
            avg_parking_per_vehicle = total_parking / total_vehicles if total_vehicles > 0 else 0.0

            # 新增：计算该路段的车均平均行程速度
            road_speeds = []
            road_non_stop_speeds = []
            for vehicle_id in road_vehicles[road]:
                if vehicle_id in vehicle_road_speeds and road in vehicle_road_speeds[vehicle_id]:
                    speeds = vehicle_road_speeds[vehicle_id][road]
                    if speeds:  # 确保有速度数据
                        avg_vehicle_speed = sum(speeds) / len(speeds)  # 车辆在该路段的平均速度(m/s)
                        road_speeds.append(avg_vehicle_speed)
                        # 计算非停车速度
                        non_stop_speeds = [speed for speed in speeds if speed >= WAITING_SPEED]
                        if non_stop_speeds:
                            road_non_stop_speeds.append(sum(non_stop_speeds) / len(non_stop_speeds))

            # 计算路段车均平均速度
            avg_road_speed = sum(road_speeds) / len(road_speeds) if road_speeds else 0.0
            avg_road_non_stop_speed = sum(road_non_stop_speeds) / len(road_non_stop_speeds) if road_non_stop_speeds else 0.0

            parking_metrics[road] = {
                'total_vehicles': total_vehicles,
                'parking_vehicles': parking_vehicles,
                'total_parking': total_parking,
                'parking_ratio': round(parking_ratio, DECIMAL_NUMBER),
                'avg_parking_per_vehicle': round(avg_parking_per_vehicle, DECIMAL_NUMBER),  # 路段车均停车次数
                'avg_travel_speed_kmh': round(avg_road_speed * 3.6, DECIMAL_NUMBER),  # 车均平均行程速度(km/h)
                'avg_non_stop_speed_kmh': round(avg_road_non_stop_speed * 3.6, DECIMAL_NUMBER) # 车均非停车速度(km/h)
            }

        # 获取正向和反向的协调路段编号
        coor_roads = []
        for coor_route_obj in self.cfg_parser.coor_routes.routes:
            route_edges = set(road_map_id.get(edge, edge) for edge in coor_route_obj.route_edges)
            coor_roads.append(route_edges)

        # 计算从起点到终点的车辆的指标
        coor_roads_index = collections.defaultdict(list)
        for vehicle_id, travel_road in vehicle_road_speeds.items():
            travel_road_set = set(travel_road.keys())
            if travel_road_set in coor_roads:
                road_speeds = []
                for road in travel_road:
                    speeds = vehicle_road_speeds[vehicle_id][road]
                    avg_vehicle_speed = sum(speeds) / len(speeds)
                    road_speeds.append(avg_vehicle_speed)
                avg_road_speed = sum(road_speeds) / len(road_speeds) if road_speeds else 0.0
                coor_index = coor_roads.index(travel_road_set)
                coor_road_id = self.cfg_parser.coor_road_id[coor_index]
                coor_roads_index[coor_road_id].append(avg_road_speed)
        for road_id, travel_speeds in coor_roads_index.items():
            parking_metrics[road_id] = {'avg_travel_speed_kmh': 3.6 * sum(travel_speeds) / len(travel_speeds),
                                        'total_vehicles': len(travel_speeds)}
        return parking_metrics, vehicles_waiting_time


    def _calculate_statistics(self, parking_metrics, filter_road=None, road_length_dict={}):
        """计算统计结果，包含每个路段的车均停车次数"""

        # 计算总体统计
        if filter_road is None:
            filter_road = list(parking_metrics.keys())
        total_vehicles = sum(stats.get('total_vehicles', 0) for road_id, stats in parking_metrics.items() if road_id in filter_road)
        total_parking_vehicles = sum(stats.get('parking_vehicles', 0) for road_id, stats in parking_metrics.items() if road_id in filter_road)
        avg_parking_ratio = total_parking_vehicles / total_vehicles if total_vehicles > 0 else 0
        total_distance = max(1, sum(info.get('total_vehicles', 0) * road_length_dict.get(road_id, 100)
                                    for road_id, info in parking_metrics.items() if road_id in filter_road))
        overall_avg_speed_kmh = sum(info.get('avg_travel_speed_kmh', 0) * info.get('total_vehicles', 0) * road_length_dict.get(road_id, 100)
                                    for road_id, info in parking_metrics.items() if road_id in filter_road) / total_distance
        overall_avg_non_stop_speed_kmh = sum(info.get('avg_non_stop_speed_kmh', 0) * info.get('total_vehicles', 0) * road_length_dict.get(road_id, 100)
                                    for road_id, info in parking_metrics.items() if road_id in filter_road) / total_distance
        return round(avg_parking_ratio, DECIMAL_NUMBER), round(overall_avg_speed_kmh, DECIMAL_NUMBER), round(overall_avg_non_stop_speed_kmh, DECIMAL_NUMBER)

    def _gen_fcd_output_json(self, fcd_output_file, road_section_length_dict, road_map_id={}):
        """处理sumo原始轨迹xml（重点更新车道编号lane和车道距离pos），适配时距图绘制；输出json"""
        # 正反向的协调路段
        coor_roads, coor_dist = self._get_coor_roads_info(road_section_length_dict)

        forward_fcd_trajectory = collections.defaultdict(list)
        backward_fcd_trajectory = collections.defaultdict(list)
        for event, timestep in ET.iterparse(fcd_output_file, events=('end',)):
            if timestep.tag != 'timestep':
                continue
            sim_time = int(float(timestep.get('time', 0)))
            for vehicle in timestep.findall('vehicle'):
                vehicle_id = vehicle.get('id')
                lane_info = vehicle.get('lane', '').split('_')
                if len(lane_info) > 2:
                    continue
                road = lane_info[0]
                if road not in road_map_id:
                    continue

                # 获取车辆在道路的绝对位置
                road_pos = float(vehicle.get('pos', 0))
                coor_index, coor_pos = self._get_vehicle_abs_pos(road, road_pos, road_section_length_dict, road_map_id)

                # 车辆位于正向协调道路上
                if coor_index == 0:
                    forward_fcd_trajectory[vehicle_id].append({'timestamp': sim_time, 'dis': coor_pos})
                # 车辆位于反向协调道路上
                elif coor_index == 1:
                    backward_fcd_trajectory[vehicle_id].append({'timestamp': sim_time, 'dis': coor_pos})
            timestep.clear()
        # 转换每辆车的轨迹格式，每辆车包含一个连续轨迹的列表
        forward_traj = convert_trajectory_format(forward_fcd_trajectory)
        backward_traj = convert_trajectory_format(backward_fcd_trajectory)

        # 获取正向和反向的交叉口信息
        cross_list = ['START'] + self.cfg_parser.cross_list + ['END']
        forward_cross_loc = [{'cross_id': cross_id, 'cross_name': cross_id, 'dis': 0 if i == 0 else sum(coor_dist[:i])}
                             for i, cross_id in enumerate(cross_list)]
        backward_cross_loc = [{'cross_id': cross_id, 'cross_name': cross_id, 'dis': 0 if i == 0 else sum(coor_dist[::-1][:i])}
                             for i, cross_id in enumerate(cross_list[::-1])]

        forward_fcd_output = {"cross_loc": forward_cross_loc, "forward_traj": forward_traj}
        backward_fcd_output = {"cross_loc": backward_cross_loc, "forward_traj": backward_traj}

        # 生成正向轨迹的json
        forward_fcd_json_file = f'{self.output_dir}/{self._get_forward_trajectroy_json_file()}'
        with open(forward_fcd_json_file, "w", encoding="utf-8") as f:
            json.dump({"data": forward_fcd_output}, f, indent=4)

        # 生成反向轨迹的json
        backward_fcd_json_file = f'{self.output_dir}/{self._get_backward_trajectroy_json_file()}'
        with open(backward_fcd_json_file, "w", encoding="utf-8") as f:
            json.dump({"data": backward_fcd_output}, f, indent=4)
        self._created_files.add(forward_fcd_json_file)
        self._created_files.add(backward_fcd_json_file)

    def _get_vehicle_abs_pos(self, road_id, road_pos, road_section_length_dict, road_map_id):
        """获取车辆在道路的绝对位置"""

        new_road = road_map_id.get(road_id, road_id)
        # 获取pos的值
        road_section_list = self.cfg_parser.road_section_info.get(new_road, [])
        coor_roads, coor_dist = self._get_coor_roads_info(road_section_length_dict)

        if road_section_list:
            index = road_section_list.index(road_id)
            road_pos += sum([road_section_length_dict[section] for section in road_section_list[:index]])

        coor_pos = road_pos
        if new_road in coor_roads[0]:
            coor_index = 0
        elif new_road in coor_roads[1]:
            coor_index = 1
        else:
            coor_index = -1

        # 车辆位于正向协调道路上
        if coor_index == 0:
            road_index = coor_roads[coor_index].index(new_road)
            coor_pos += sum([length for length in coor_dist[:road_index]])
        # 车辆位于反向协调道路上
        elif coor_index == 1:
            road_index = coor_roads[coor_index].index(new_road)
            coor_pos += sum([length for length in coor_dist[road_index + 1:]])
        return coor_index, coor_pos

    def _get_coor_roads_info(self, road_section_length_dict):
        """获取以交叉口间路段表示的协调道路信息"""
        coor_roads = []
        road_map_id = self.cfg_parser.road_map_id['forward'] | self.cfg_parser.road_map_id['backward']
        for edges in self.cfg_parser.coor_routes.routes:
            direction_roads = []
            for edge_id in edges.route_edges:
                road_id = road_map_id.get(edge_id, edge_id)
                if road_id not in direction_roads:
                    direction_roads.append(road_id)
            coor_roads.append(direction_roads)
        coor_roads[-1] = coor_roads[-1][::-1]

        coor_dist = []
        for road_id in coor_roads[0]:
            road_section_list = self.cfg_parser.road_section_info.get(road_id, [])
            if road_section_list:
                road_length = sum(road_section_length_dict.get(section, 0) for section in road_section_list)
            else:
                road_length = road_section_length_dict.get(road_id, 0)
            coor_dist.append(road_length)
        return coor_roads, coor_dist

    def _analyze_vehicle_trip(self, tripinfo_file):
        """分析单车的指标"""
        vehicles_index = collections.defaultdict(dict)
        for event, trip in ET.iterparse(tripinfo_file, events=('end',)):
            if trip.tag != 'tripinfo':
                continue
            id = trip.get('id')
            # 单车进入和离开位置
            depart_lane = trip.get('departLane')
            depart_pos = float(trip.get('departPos'))
            arrival_lane = trip.get('arrivalLane')
            arrival_pos = float(trip.get('arrivalPos'))
            # 单车行程时间和行程距离
            travel_time = int(float(trip.get('duration')))
            travel_length = float(trip.get('routeLength'))
            # 单车停车速度和不停车速度
            stop_speed = round(3.6 * travel_length / travel_time, DECIMAL_NUMBER)
            non_stop_speed = round(3.6 * travel_length / (travel_time - float(trip.get('waitingTime'))), DECIMAL_NUMBER)
            # 拼接单车的指标
            vehicles_index[id] = {'depart_lane': depart_lane, 'depart_pos': depart_pos, 'arrival_lane': arrival_lane,
                                  'arrival_pos': arrival_pos, 'travel_time': travel_time, 'travel_length': travel_length,
                                  'stop_speed': stop_speed, 'non_stop_speed': non_stop_speed}
            trip.clear()

        tripinfo_out_file = f'{self.output_dir}/{self._get_tripinfo_json_file()}'
        with open(tripinfo_out_file, "w", encoding="utf-8") as f:
            json.dump(vehicles_index, f, indent=4)
        self._created_files.add(tripinfo_out_file)

    def _analyze_queue_output(self, queue_file, filter_road=None, road_map_id={}):
        """分析排队输出文件"""
        total_timesteps = set()
        lane_ids = set()
        max_queue_length = 0.0
        max_experimental_queue_length = 0.0
        max_queueing_time = 0.0
        total_queue_length = 0.0
        total_queueing_time = 0.0
        total_samples = 0
        lane_max = {}
        timestep_sum = collections.defaultdict(float)
        road_timestep_agg = collections.defaultdict(lambda: {'queueing_time': 0.0, 'queueing_length': 0.0, 'queueing_length_experimental': 0.0})

        for event, data_elem in ET.iterparse(queue_file, events=('end',)):
            if data_elem.tag != 'data':
                continue
            timestep = float(data_elem.get('timestep', 0))
            lanes_elem = data_elem.find('lanes')
            if lanes_elem is not None:
                for lane_elem in lanes_elem.findall('lane'):
                    lane_id = lane_elem.get('id', '')
                    lane_info = lane_id.split('_')
                    if len(lane_info) > 2:
                        continue
                    road = lane_info[0]
                    if filter_road and road not in filter_road:
                        continue

                    long_road = road_map_id.get(road, road)
                    queueing_time = float(lane_elem.get('queueing_time', 0))
                    queueing_length = float(lane_elem.get('queueing_length', 0))
                    queueing_length_experimental = float(lane_elem.get('queueing_length_experimental', 0))

                    total_timesteps.add(timestep)
                    lane_ids.add(lane_id)
                    total_samples += 1
                    total_queue_length += queueing_length
                    total_queueing_time += queueing_time
                    max_queue_length = max(max_queue_length, queueing_length)
                    max_experimental_queue_length = max(max_experimental_queue_length, queueing_length_experimental)
                    max_queueing_time = max(max_queueing_time, queueing_time)
                    lane_max[lane_id] = max(lane_max.get(lane_id, 0.0), queueing_length)
                    timestep_sum[timestep] += queueing_length

                    agg = road_timestep_agg[(long_road, timestep)]
                    agg['queueing_time'] = max(agg['queueing_time'], queueing_time)
                    agg['queueing_length'] += queueing_length
                    agg['queueing_length_experimental'] += queueing_length_experimental

            data_elem.clear()

        if total_samples == 0:
            return {}

        road_grouped = collections.defaultdict(list)
        for (long_road, timestep), agg in road_timestep_agg.items():
            road_grouped[long_road].append(agg)

        road_detailed_stats = {}
        for road, entries in road_grouped.items():
            queue_lengths = [item['queueing_length'] for item in entries]
            road_detailed_stats[road] = {
                'avg_queue_length': sum(queue_lengths) / len(queue_lengths),
                'max_queue_length': max(queue_lengths)
            }

        return {
            'total_timesteps': len(total_timesteps),
            'total_lanes_with_queues': len(lane_ids),
            'max_queue_length': max_queue_length,
            'max_experimental_queue_length': max_experimental_queue_length,
            'avg_queue_length': total_queue_length / total_samples,
            'max_queueing_time': max_queueing_time,
            'avg_queueing_time': total_queueing_time / total_samples,
            'most_congested_lane': max(lane_max, key=lane_max.get) if lane_max else None,
            'most_congested_timestep': max(timestep_sum, key=timestep_sum.get) if timestep_sum else None,
            'road_detailed_stats': road_detailed_stats,
        }

    def _simulate(self):
        """运行SUMO仿真"""
        # 从 $SUMO_HOME/tools 导入python模块
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")

        sumo_cfg_file = f'{self.output_dir}/{self._get_sumo_cfg_file()}'
        fcd_out_file = f'{self.output_dir}/{self._get_fcd_output_file()}'
        queue_out_file = f'{self.output_dir}/{self._get_queue_output_file()}'
        tripinfo_out_file = f'{self.output_dir}/{self._get_tripinfo_output_file()}'
        network_out_file = f'{self.output_dir}/{self._get_net_file()}'
        self._created_files.add(fcd_out_file)
        if self.enable_queue_output:
            self._created_files.add(queue_out_file)
        if self.enable_tripinfo_output:
            self._created_files.add(tripinfo_out_file)

        cmd = [
            'sumo',
            '-c', sumo_cfg_file,
        ]
        cmd.extend(['--fcd-output', fcd_out_file])
        if self.fcd_period > 1:
            cmd.extend(['--device.fcd.period', str(self.fcd_period)])
        if self.enable_queue_output:
            cmd.extend(['--queue-output', queue_out_file])
        if self.enable_tripinfo_output:
            cmd.extend(['--tripinfo-output', tripinfo_out_file])
        if self.enable_sumo_perf_options:
            cmd.extend(['--no-step-log', 'true', '--duration-log.disable', 'true'])
        
        try:
            # 执行命令
            with self._profile_stage('sumo_run'):
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"sumo执行失败，退出码: {e.returncode}")
            logger.error(f"错误输出: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.error("未找到sumo命令，请确保SUMO已正确安装并添加到PATH环境变量中")
            raise

        self._record_file_size('fcd_output', fcd_out_file)
        if self.enable_queue_output:
            self._record_file_size('queue_output', queue_out_file)
        if self.enable_tripinfo_output:
            self._record_file_size('tripinfo_output', tripinfo_out_file)

        forward_roads = self.cfg_parser.coor_routes.routes[0].route_edges
        backward_roads = self.cfg_parser.coor_routes.routes[1].route_edges
        selected_road = forward_roads + backward_roads
        road_map_id = self.cfg_parser.road_map_id['forward'] | self.cfg_parser.road_map_id['backward']
        # 添加起点入口段和终点出口段
        road_map_id.update({forward_roads[0]: forward_roads[0], forward_roads[-1]: forward_roads[-1],
                            backward_roads[0]: backward_roads[0], backward_roads[-1]: backward_roads[-1]})
        road_length_dict = self.cfg_parser.road_length_dict

        # 并行计算：把 fcd 解析（停车指标）和 queue 解析并行化
        with ThreadPoolExecutor(max_workers=2 if self.enable_queue_output else 1) as tpe:
            fut_parking = tpe.submit(self._profiled_parking_metrics, fcd_out_file, selected_road, road_map_id)
            fut_queue = tpe.submit(self._profiled_queue_output, queue_out_file, selected_road, road_map_id) if self.enable_queue_output else None

            parking_metrics, waiting_time = fut_parking.result()
            queue_stat = fut_queue.result() if fut_queue else {}

        # 正向道路
        forward_roads = list(self.cfg_parser.road_map_id['forward'].values())
        # 反向道路
        backward_roads = list(self.cfg_parser.road_map_id['backward'].values())

        # 双向道路
        filter_road = forward_roads + backward_roads
        avg_waiting_ratio, avg_speed, avg_non_stop_speed = self._calculate_statistics(parking_metrics, filter_road, road_length_dict)

        # 正向指标
        forward_avg_waiting_ratio, forward_avg_speed, _ = self._calculate_statistics(parking_metrics, forward_roads, road_length_dict)

        # 反向指标
        backward_avg_waiting_ratio, backward_avg_speed, _ = self._calculate_statistics(parking_metrics, backward_roads, road_length_dict)

        # 起点到终点的行程指标
        filter_road = self.cfg_parser.coor_road_id
        _, travel_speed, _ = self._calculate_statistics(parking_metrics, filter_road, road_length_dict)

        avg_queue_length = queue_stat.get('avg_queue_length') if isinstance(queue_stat, dict) else None

        if self.cfg.get('config', {}).get('supportDiagram', False):
            with self._profile_stage('support_diagram_postprocess'):
                road_section_length_dict = extract_edge_lengths(network_out_file)
                with ThreadPoolExecutor(max_workers=2 if self.enable_tripinfo_output else 1) as tpe:
                    futures = [tpe.submit(self._gen_fcd_output_json, fcd_out_file, road_section_length_dict, road_map_id)]
                    if self.enable_tripinfo_output:
                        futures.append(tpe.submit(self._profiled_tripinfo_analysis, tripinfo_out_file))
                    for future in futures:
                        future.result()
        # 返回道路层的群体指标，用于相位差方案评估
        return {
            'parking_metrics': parking_metrics,
            'waiting_time': waiting_time,
            'avg_waiting_ratio': avg_waiting_ratio,
            'avg_speed': avg_speed,
            'avg_non_stop_speed': avg_non_stop_speed,
            'avg_queue_length': avg_queue_length,
            'outbound': {'avg_speed': forward_avg_speed, 'avg_waiting_ratio': forward_avg_waiting_ratio},
            'inbound': {'avg_speed': backward_avg_speed, 'avg_waiting_ratio': backward_avg_waiting_ratio},
            'avg_travel_time': round(3.6 * sum(self.cfg_parser.road_length) / travel_speed, DECIMAL_NUMBER) if travel_speed > 0 else 0
        }

    def _profiled_parking_metrics(self, xml_file, filter_road=None, road_map_id={}):
        with self._profile_stage('fcd_parse'):
            return self._calculate_parking_metrics(xml_file, filter_road, road_map_id)

    def _profiled_queue_output(self, queue_file, filter_road=None, road_map_id={}):
        with self._profile_stage('queue_parse'):
            return self._analyze_queue_output(queue_file, filter_road, road_map_id)

    def _profiled_tripinfo_analysis(self, tripinfo_file):
        with self._profile_stage('tripinfo_parse'):
            return self._analyze_vehicle_trip(tripinfo_file)
    
    def _cleanup_xml_files(self):
        """清理文件"""
        for p in list(self._created_files):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception as e:
                logger.warning(f"删除文件失败 {p}: {e}")


    def run(self):
        """运行仿真流程，包括路网生成、路由生成、配置文件生成和仿真运行"""
        try:
            with self._profile_stage('roadnet_generate'):
                self._gen_roadnet_file()
            with self._profile_stage('route_generate'):
                self._gen_rou_file()
            with self._profile_stage('sumocfg_generate'):
                self._gen_sumo_cfg()
            output = self._simulate()
            return output
        finally:
            try:
                with self._profile_stage('cleanup'):
                    self._cleanup_xml_files()
            except Exception as e:
                logger.error(f"清理文件时发生错误: {e}")
            finally:
                self._finalize_profiling()

