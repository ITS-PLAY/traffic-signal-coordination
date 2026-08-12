# 输出指标详细说明

## 1. 宏观性能指标

### 1.1 平均行程速度 (avg_speed)
- **定义**: 所有车辆在整个路网中的平均行驶速度
- **计算公式**: 总行驶距离 / 总行驶时间
- **单位**: km/h
- **用途**: 评估整体交通流畅度

### 1.2 平均停车率 (avg_waiting_ratio)
- **定义**: 停车车辆数 / 总车辆数
- **计算逻辑**: 
  - 停车判定: 速度 < 5 km/h (1.39 m/s)
  - 同一车辆在同一路段多次停车需间隔 > 5秒才计为多次
- **单位**: 比例 (0-1)
- **用途**: 评估交通中断程度

### 1.3 平均排队长度 (avg_queue_length)
- **定义**: 各进口道排队长度的时间平均值
- **数据来源**: SUMO queue-output
- **单位**: 米
- **用途**: 评估路口拥堵程度

### 1.4 平均行程时间 (avg_travel_time)
- **定义**: 车辆从起点到终点的平均行程时间
- **计算公式**: 3.6 × 总路段长度 / 平均行程速度
- **单位**: 秒
- **用途**: 评估干线协调效果

## 2. 方向性指标

### 2.1 正向指标 (outbound)
```json
"outbound": {
  "avg_speed": 45.2,
  "avg_waiting_ratio": 0.15
}
```

### 2.2 反向指标 (inbound)
```json
"inbound": {
  "avg_speed": 42.8,
  "avg_waiting_ratio": 0.18
}
```

**说明**: 
- 正向/反向基于`crossList`中路口的排列顺序
- 用于评估双向协调的平衡性

## 3. 路段级详细指标 (parking_metrics)

每个路段提供详细的性能指标：

```json
"parking_metrics": {
  "C0C1": {
    "total_vehicles": 125,
    "parking_vehicles": 18,
    "total_parking": 22,
    "parking_ratio": 0.144,
    "avg_parking_per_vehicle": 0.176,
    "avg_travel_speed_kmh": 48.5,
    "avg_non_stop_speed_kmh": 52.3
  }
}
```

### 3.1 字段说明

| 字段 | 类型 | 描述 |
|------|------|------|
| `total_vehicles` | Integer | 通过该路段的总车辆数 |
| `parking_vehicles` | Integer | 在该路段停车的车辆数 |
| `total_parking` | Integer | 该路段总停车次数 |
| `parking_ratio` | Float | 停车率 = parking_vehicles / total_vehicles |
| `avg_parking_per_vehicle` | Float | 车均停车次数 = total_parking / total_vehicles |
| `avg_travel_speed_kmh` | Float | 车均平均行程速度 (包含停车时间) |
| `avg_non_stop_speed_kmh` | Float | 车均非停车速度 (排除停车时间) |

### 3.2 特殊路段标识

- **协调路段**: `C0C1`, `C1C2` 等表示路口间的协调路段
- **起点-终点**: `C0C2` 表示从第一个路口到最后一个路口的整体行程

## 4. 微观轨迹数据

当启用`supportDiagram: true`时，系统生成详细的轨迹数据：

### 4.1 单车指标 (tripinfo.json)
```json
{
  "vehicle_1": {
    "depart_lane": "C0P1_0",
    "depart_pos": 0.0,
    "arrival_lane": "C2P3_0", 
    "arrival_pos": 100.0,
    "travel_time": 120,
    "travel_length": 1100.0,
    "stop_speed": 33.0,
    "non_stop_speed": 38.5
  }
}
```

### 4.2 时空轨迹 (forward_traj.json, backward_traj.json)
```json
{
  "data": {
    "cross_loc": [
      {"cross_id": "START", "cross_name": "START", "dis": 0},
      {"cross_id": "C0", "cross_name": "C0", "dis": 0},
      {"cross_id": "C1", "cross_name": "C1", "dis": 500},
      {"cross_id": "C2", "cross_name": "C2", "dis": 1100},
      {"cross_id": "END", "cross_name": "END", "dis": 1100}
    ],
    "forward_traj": [
      [
        {"traj_id": "vehicle_1", "timestamp": 0, "dis": 0},
        {"traj_id": "vehicle_1", "timestamp": 10, "dis": 50},
        // ... more trajectory points
      ]
    ]
  }
}
```

**用途**: 
- 生成时距图 (Space-Time Diagram)
- 分析绿波带效果
- 可视化车辆运行轨迹

## 5. 排队动态数据 (queue_output analysis)

详细的排队统计信息：

```json
{
  "total_timesteps": 300,
  "total_lanes_with_queues": 12,
  "max_queue_length": 45.2,
  "max_experimental_queue_length": 48.7,
  "avg_queue_length": 22.3,
  "max_queueing_time": 120.5,
  "avg_queueing_time": 45.8,
  "most_congested_lane": "C1P2_0",
  "most_congested_timestep": 180,
  "road_detailed_stats": {
    "C0C1": {
      "avg_queue_length": 18.5,
      "max_queue_length": 35.2
    }
  }
}
```

## 6. 指标计算逻辑

### 6.1 停车判定逻辑
- **速度阈值**: < 5 km/h (1.39 m/s)
- **时间间隔**: 同一车辆同一路段停车需间隔 > 5秒
- **统计方式**: 
  - 停车车辆数: 至少停车一次的车辆
  - 停车次数: 满足时间间隔条件的停车事件

### 6.2 速度计算逻辑
- **行程速度**: 总距离 / (行驶时间 + 停车时间)
- **非停车速度**: 总距离 / 行驶时间
- **路段速度**: 各车辆在该路段的平均速度的平均值

### 6.3 协调效果评估
- **正向协调**: 基于`crossList`顺序的主方向
- **反向协调**: 相反方向
- **整体效果**: 起点到终点的端到端性能

## 7. 使用建议

### 7.1 指标选择
- **方案比选**: 使用宏观指标 (avg_speed, avg_waiting_ratio)
- **问题诊断**: 使用路段级详细指标和排队数据  
- **可视化展示**: 使用微观轨迹数据
- **协调优化**: 对比正向/反向指标差异

### 7.2 结果解读
- **高停车率 + 低速度**: 严重拥堵，需要优化配时
- **正向/反向差异大**: 协调不平衡，调整相位差
- **排队长度长**: 饱和度高，考虑增加绿信比或渠化改造
- **行程时间长**: 干线协调效果差，优化绿波带

### 7.3 敏感性分析
建议进行以下对比分析：
- 不同信控方案对比
- 不同流量水平对比  
- 不同相位差设置对比
- 单点 vs 协调控制对比