import os
from enum import Enum

# 默认超时秒数
DEFAULT_TIMEOUT = 60

# 遗传算法的变异幅度
PERTURBATION_SCALE = 10

# 遗传算法新解与已有方案之间允许的初始最小 offset 环形差值；
# 连续多代提升不足时会在 GA 内按代动态放大
DEFAULT_MIN_OFFSET_DELTA = 3

# 遗传算法动态种群规模的最小值
DEFAULT_GA_POP_MIN = 12

# 遗传算法动态种群规模的最大值
DEFAULT_GA_POP_MAX = 64

# 遗传算法动态种群规模的每变量倍数
DEFAULT_GA_POP_PER_VAR = 8

# 遗传算法提前终止时至少执行的代数
DEFAULT_GA_EARLY_STOP_MIN_GEN = 5

# 遗传算法提前终止时允许连续无提升的代数
DEFAULT_GA_EARLY_STOP_PATIENCE = 4

# 遗传算法提前终止与动态放大 offset 差值时认定为有效提升的最小目标变化
DEFAULT_GA_EARLY_STOP_MIN_IMPROVEMENT = 0.05

# 当动态放大的最小 offset 差值遇到明显提升后，是否恢复为初始值
DEFAULT_GA_RESET_MIN_OFFSET_DELTA_ON_IMPROVEMENT = True

# 遗传算法迭代次数
GA_ITERATIONS = 20

# 仿真器的服务名
EVALUATOR_FUNC_NAME = 'ts_evaluator'
# 仿真的 url
EVALUATOR_URL = os.environ.get('EVALUATOR_URL', 'http://ts-evaluator')
# 仿真的路由
EVALUATOR_URL_PATH = '/algorithm/invoke'

# 默认的进口道顺序
DEFAULT_DIRECTIONS = ['1', '2', '3', '4']  # 北、东、南、西
# 遗传算法的随机种子
DEFAULT_SEED = 42
# 遗传算法的单交叉口初始种群数量（保留为兼容常量）
DEFAULT_POP_SIZE = 100
# 遗传算法的运行效率标志
FAST_MODE = 'fast'
BEST_MODE = 'best'
DEFAULT_MODE = FAST_MODE

# 分段候选生成时每个子问题覆盖的默认路口数
DEFAULT_SEGMENT_CROSS_COUNT = 3
# 分段优化时相邻子问题默认共享的重叠路口数量，默认重叠 2 个路口
DEFAULT_SEGMENT_OVERLAP_CROSS_COUNT = 2


# 算法目标
class OBJECTIVE(Enum):
    TRAVEL_TIME = "travel_time"
    WEIGHTED_SPEED = "weighted_speed"
    STOP_RATE = "stop_rate"
