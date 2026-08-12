# 保留小数点位数
DECIMAL_NUMBER = 6
# 排队有效等待时间的时间阈值，单位秒
WAITING_TIME_INTERVAL = 5
# 默认最小平均车速，用于计算仿真持续时间
DEFAULT_MIN_SPEED_KMH = 20
# 路口内过渡边长度，单位米
TRANSITION_EDGE_LENGTH = 100
# 路网外围进口道长度，单位米
TRANSITION_DISTANCE = 80
# 路口内过渡边速度，单位米/秒
TRANSITION_EDGE_SPEED = 50/3.6
# 默认流量开始时间，单位秒
DEFAULT_FLOW_BEGIN_TIME = 0
# 协调方向流量开始时间，单位秒
COOR_DEFAULT_FLOW_BEGIN_TIME = int(4 * TRANSITION_DISTANCE / TRANSITION_EDGE_SPEED)
# 默认流量出现概率，单位秒，即每秒会生成一辆车的概率
DEFAULT_FLOW_PROBABILITY = 0.15
# 默认的进口道顺序
DEFAULT_DIRECTIONS = ['1', '2', '3', '4']  # 北、东、南、西
# 路径单车道流量的最小值，单位：辆/小时
DEFAULT_LANE_FLOW = 120
# 流量采集的时间间隔，单位：秒
FLOW_TIME_INTERVAL = 3600
# 加载流量的时间窗口，单位：秒
DEFAULT_FLOW_WINDOWS = 900
#起点和终点路口协调转向的反方向
DEFAULT_REVERSE_TURN = {'2': '2', '4': '1', '1': '4'}
# 直行车道连接下游，按照下游出口车道数，从中间开始匹配
STRAIGHT_CONNECTION_DELTA = [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
# 路段中间连接线的最小长度
DEFAULT_EDGE_MIN_LENGTH = 10
# 转向的编号
TURN_MAP_NUM = {'t': '8', 'l': '4', 's': '2', 'r': '1'}
# 车辆类型编号
DEFAULT_VEH_TYPE = 'car'
# 判断是否停车的速度阈值，米/秒
WAITING_SPEED = 3.6/3.6

#默认最多允许多少个仿真任务同时运行
DEFAULT_MAX_SIM_WORKERS = '3'
#默认一个worker连续处理多少次后重建
DEFAULT_MAX_TASKS_PER_CHILD = '50'
#默认允许额外等待的任务数量
DEFAULT_MAX_SIM_QUEUE_SIZE = '5'
