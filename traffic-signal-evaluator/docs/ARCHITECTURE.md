# 系统架构与技术实现

## 1. 整体架构

### 1.1 架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   输入数据       │    │   配置解析器     │    │   路网生成器     │
│ (JSON格式)      │───▶│ (ConfigParser)  │───▶│  (Converter)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   仿真结果       │◀───│   SUMO仿真器     │◀───│   SUMO路网文件   │
│ (多维度指标)     │    │ (Simulator)     │    │ (.net.xml等)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1.2 数据流
1. **输入解析**: JSON配置 → 内存数据结构
2. **路网构建**: 内存数据结构 → SUMO XML文件
3. **仿真执行**: SUMO XML文件 → 仿真结果XML
4. **结果分析**: 仿真结果XML → JSON指标

## 2. 核心数据模型

### 2.1 Cross (路口)
```python
class Cross:
    def __init__(self, id: str, points: List[Point], edges: List[Edge], 
                 dir_points: Dict[str, Point], dir_edges: Dict[str, Any], 
                 traffic_light: TrafficLightPlan):
        self.id = id                    # 路口ID
        self.points = points           # 过渡点列表  
        self.edges = edges             # 道路边列表
        self.dir_points = dir_points   # 方向-过渡点映射
        self.dir_edges = dir_edges     # 方向-边映射
        self.next_cross = None         # 下一个路口
        self.pre_cross = None          # 上一个路口  
        self.traffic_light = traffic_light  # 信控方案
```

### 2.2 TrafficLightPlan (信控方案)
```python
class TrafficLightPlan:
    def __init__(self, cross_id: str, phases: List[str], durations: Dict[str, int], 
                 functions: Dict[str, Any], offset: int, coordination_phase: str = ''):
        self.id = cross_id
        self.phases = phases                    # 相位列表 ['A', 'B', 'C']
        self.durations = durations              # 相位时长 {'A': 59, 'B': 32}
        self.functions = functions              # 相位功能 {'A': {'3': ['s'], '2': ['r']}}
        self.offset = offset                    # 相位偏移
        self.coordination_phase = coordination_phase  # 协调相位
        self.cycle = sum(durations.values())    # 周期时长
```

### 2.3 Roadnet (路网)
```python
class Roadnet:
    def __init__(self, cross_list: List[str], nodes: List[Node], edges: List[Edge], 
                 conn_list: List[Connection], tl_list: List[TLLogic], routes: Routes):
        self.cross_list = cross_list    # 路口列表
        self.nodes = nodes             # 节点列表  
        self.edges = edges             # 边列表
        self.conn_list = conn_list     # 连接列表
        self.tl_list = tl_list         # 信号灯列表
        self.routes = routes           # 路由列表
```

## 3. 关键算法实现

### 3.1 路口渠化解析
**输入**: `"1,422,2|2,441,2|3,221,2"`
**处理流程**:
1. 按`|`分割各方向信息
2. 按`,`分割方向ID、车道转向、出口道数
3. 解析十六进制车道转向编码
4. 生成Point和Edge对象

**车道转向解码**:
```python
def _parse_turn_list(self, turn_char):
    hex_value = int(turn_char, 16)
    turns = []
    if hex_value & 0b0010: turns.append("s")  # 直行
    if hex_value & 0b0100: turns.append("l")  # 左转  
    if hex_value & 0b0001: turns.append("r")  # 右转
    if hex_value & 0b1000: turns.append("t")  # 掉头
    return turns
```

### 3.2 相位状态生成
**目标**: 将相位功能转换为SUMO的state字符串 (如: "GGGrrr")

**算法流程**:
1. 初始化所有连接为红灯 ('r')
2. 遍历每个连接，检查其方向-转向组合
3. 如果该组合在相位功能中被允许，设置为绿灯 ('g')
4. 右转默认为绿灯（除非明确禁止）

```python
def _gen_phase_state(self, connections, phase_list, functions):
    size = len(connections)
    states = {ph: ['r']*size for ph in phase_list}
    
    for con in connections:
        from_dir = con.from_dir
        turn = con.dir  
        link_index = con.link_index
        
        # 检查相位功能
        if from_dir in dir_turn_phases and turn in dir_turn_phases[from_dir]:
            for ph in dir_turn_phases[from_dir][turn]:
                states[ph][link_index] = 'g'
        elif turn == 'r':  # 右转默认绿灯
            for ph in states:
                states[ph][link_index] = 'g'
                
    return states
```

### 3.3 路由生成算法
**协调路由生成**:
1. 从起点路口开始，沿协调方向生成路径
2. 处理正向和反向两个方向
3. 自动计算流量加载时间和概率

**转向路由生成**:
1. 处理非协调方向的转向流量
2. 生成reroute规则用于动态转向

### 3.4 并发仿真优化
**进程池管理**:
```python
MAX_SIM_WORKERS = max(1, os.cpu_count() // 2)
SIM_WORKER_POOL = ProcessPoolExecutor(max_workers=MAX_SIM_WORKERS)

def main(input_json):
    future = SIM_WORKER_POOL.submit(run_simulator_worker, input_data)
    return future.result()
```

**文件锁机制**:
- 避免多个进程同时执行`netconvert`
- 使用文件锁实现进程间同步
- 支持缓存已生成的路网文件

## 4. SUMO集成细节

### 4.1 文件生成
系统生成以下SUMO配置文件：
- `.node.xml`: 节点定义
- `.edg.xml`: 边定义  
- `.conn.xml`: 连接定义
- `.tll.xml`: 信号灯逻辑
- `.rou.xml`: 路由和流量
- `.sumocfg`: 仿真配置

### 4.2 仿真命令
```bash
sumo -c config.sumocfg \
     --fcd-output fcd.xml \
     --queue-output queue.xml \
     --tripinfo-output tripinfo.xml
```

### 4.3 输出解析
- **FCD输出**: 浮动车数据，用于轨迹分析
- **Queue输出**: 排队数据，用于拥堵分析  
- **Tripinfo输出**: 单车行程信息，用于详细指标计算

## 5. 性能优化策略

### 5.1 缓存机制
- **路网缓存**: 相同配置生成相同的MD5哈希，复用已存在的路网文件
- **结果缓存**: 避免重复仿真相同场景

### 5.2 并发处理
- **多进程仿真**: 利用多核CPU并行处理多个仿真任务
- **多线程分析**: 并行处理FCD和Queue数据分析

### 5.3 内存管理
- **临时文件清理**: 自动删除仿真生成的临时XML文件
- **资源释放**: 确保进程池和文件句柄正确关闭

## 6. 扩展性设计

### 6.1 模块化架构
- **配置解析**: 独立的ConfigParser模块
- **数据转换**: 独立的Converter模块  
- **仿真执行**: 独立的Simulator模块
- **结果分析**: 可扩展的分析函数

### 6.2 插件接口
**新增评估指标**:
```python
def _calculate_new_metric(self, xml_file):
    # 实现新的指标计算逻辑
    pass
```

**新增仿真引擎**:
- 替换SUMO集成模块
- 保持相同的输入/输出接口

### 6.3 配置扩展
- 支持新的路口渠化格式
- 支持更复杂的信控方案
- 支持多时段配时方案

## 7. 错误处理与调试

### 7.1 异常处理
- **配置错误**: 详细的验证和错误提示
- **仿真失败**: 捕获SUMO错误并提供调试信息
- **文件操作**: 安全的文件读写和清理

### 7.2 日志系统
- **结构化日志**: 使用logger模块记录关键事件
- **调试信息**: 详细的处理步骤日志
- **错误追踪**: 完整的异常堆栈信息

### 7.3 调试工具
- **输入验证**: 自动检查输入数据的合法性
- **中间结果**: 可选输出中间XML文件用于调试
- **性能监控**: 记录各阶段执行时间

## 8. 部署与运维

### 8.1 Docker容器化
- **基础镜像**: 包含Python和SUMO环境
- **依赖管理**: requirements.txt管理Python依赖
- **配置挂载**: 支持外部配置文件挂载

### 8.2 Kubernetes部署
- **Helm Chart**: 标准化的Kubernetes部署包
- **资源配置**: 合理的CPU/Memory请求和限制
- **健康检查**: HTTP和命令行健康检查

### 8.3 监控告警
- **资源使用**: CPU、内存、磁盘监控
- **服务状态**: 仿真任务成功率监控
- **性能指标**: 响应时间、吞吐量监控