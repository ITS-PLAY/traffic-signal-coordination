import xml.etree.ElementTree as ET

from constants.constants import DEFAULT_DIRECTIONS


def get_target_direction(from_direction, lane_turn):
    """根据起始方向和转向类型确定目标方向"""
    from_index = DEFAULT_DIRECTIONS.index(from_direction)

    if lane_turn == '2':  # 直行
        target_direction = DEFAULT_DIRECTIONS[(from_index + 2) % 4]
    elif lane_turn == '4':  # 左转
        target_direction = DEFAULT_DIRECTIONS[(from_index + 1) % 4]
    elif lane_turn == '1':  # 右转
        target_direction = DEFAULT_DIRECTIONS[(from_index - 1) % 4]
    elif lane_turn == '8':  # 掉头
        target_direction = from_direction
    else:  # 默认为直行
        target_direction = DEFAULT_DIRECTIONS[(from_index + 2) % 4]
    return target_direction


def extract_edge_lengths(net_file):
    """获取每个edge的真实长度"""
    tree = ET.parse(net_file)
    root = tree.getroot()

    edge_lengths = {}
    for edge in root.findall('edge'):
        edge_id = edge.get('id')
        # 跳过没有 lane 的 edge
        lanes = edge.findall('lane')
        if not lanes:
            continue

        # 取第一个 lane 的 length（SUMO 中同一 edge 的 lane 长度一致）
        length_str = lanes[0].get('length')
        if length_str is not None:
            edge_lengths[edge_id] = float(length_str)
        else:
            edge_lengths[edge_id] = None
    return edge_lengths


def convert_trajectory_format(vehicle_trajectory):
    """将每辆车的轨迹字典，转换为列表格式"""
    vehicles_trajectory_list = []
    for vehicle_id, trajectory_info in vehicle_trajectory.items():
        vehicle_traj = []
        for traj in trajectory_info:
            traj.update({'traj_id': vehicle_id})
            vehicle_traj.append(traj)
        vehicles_trajectory_list.append(vehicle_traj)
    return vehicles_trajectory_list
