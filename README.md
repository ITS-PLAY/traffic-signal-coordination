# 交通信号协调控制系统（Traffic Signal Coordination）

> ## 🌐 在线体验
>
> # 👉 http://121.41.65.106:8080/
>
> **公网演示地址，浏览器直接打开即可使用（绿波配置 + 时距图可视化工具）**

---

## 项目简介

面向城市干道**绿波协调控制**的一体化系统：输入沿线各路口的渠化、相位配时、流量与路段参数，自动求解最优**相位差方案**，并通过 **SUMO 交通仿真**对方案进行评价，最终由 Web 前端以**绿波时距图**和**路口示意图**直观呈现结果。

系统由三个松耦合的服务组成：

| 模块 | 职责 |
| --- | --- |
| **traffic-signal-generator** | 相位差优化核心：带宽算法（flex-band）+ 遗传算法（GA），输出各路口协调相位差方案 |
| **traffic-signal-evaluator** | 方案评价：调用 SUMO / netconvert 做微观交通仿真，返回车均延误、排队等指标 |
| **deploy/frontend** | 可视化前端：单页应用，渠化/相位/流量示意图 + 绿波时距图，反向代理 API 避免跨域 |

GA 每一代个体都会通过 HTTP 调用 evaluator 做仿真评价，形成"优化—评价"闭环。

## 技术框架

**算法层**
- 带宽优化（flex-band）：[gekko](https://gekko.readthedocs.io/) 数学规划求解
- 遗传算法（多目标优化）：[pymoo](https://pymoo.org/)
- 数值计算：numpy

**仿真评价**
- [SUMO](https://www.eclipse.dev/sumo/)（Simulation of Urban MObility）微观交通仿真
- `sumo` / `netconvert` 命令行工具构建路网并运行仿真

**服务层**
- Python 3.11 + Flask 3 + Gunicorn
- 统一 API 契约：`POST /algorithm/invoke`，请求 `{"func": "<名字>", "in": {...}}`，响应 `{"out": {...}}`
- 健康检查：`GET /health` → `{"status":"ok"}`

**前端**
- 原生 HTML / CSS / JavaScript 单页应用（无前端框架，零构建）
- Canvas 绘制绿波时距图，SVG 绘制路口渠化/相位/流量示意图
- Python 标准库 `http.server` 提供静态服务并反向代理 `/api/*`

**部署**
- Docker 容器化（基础镜像经 `docker.m.daocloud.io` 加速）
- 阿里云 **SAE**（Serverless 应用引擎）+ **ACR**（容器镜像服务）

## 系统架构

```
浏览器 ──► ts-frontend (公网入口 :8080)
              │  静态页面 index.html + sketch.js
              │  /api/* 反向代理 ↓
              ▼
           ts-generator (VPC 内网 :3001)
              │  带宽算法 + 遗传算法(GA)
              │  GA 每代 HTTP 调用 ↓ 做仿真评价
              ▼
           ts-evaluator (VPC 内网 :3001)
              调用 sumo / netconvert 做交通仿真
```

## 目录结构

```
.
├── traffic-signal-generator/   # 相位差优化服务（带宽算法 + GA）
│   ├── algorithms/             #   bandwidth_algorithm/  genetic_algorithm/
│   ├── config/  core/  common/ #   配置 / 核心逻辑 / HTTP 客户端
│   └── test/                   #   benchmark 用例与结果
├── traffic-signal-evaluator/   # SUMO 仿真评价服务
│   ├── sumo/                   #   路网构建与仿真封装
│   ├── core/  parse/  config/  #   评价逻辑 / 数据解析
│   └── test/
└── deploy/                     # 容器化与部署
    ├── frontend/               #   Web 前端（index.html / sketch.js / serve.py / Dockerfile）
    ├── generator/              #   generator 镜像（Dockerfile / server.py）
    ├── evaluator/              #   evaluator 镜像（Dockerfile / server.py）
    ├── docker-compose.yml      #   本地一键联调
    └── README-SAE.md           #   阿里云 SAE 详细部署文档
```

## 本地运行

**前置**：安装 Docker（或 Python 3.11 + SUMO）。

### 方式一：Docker Compose（推荐，一键联调）

```bash
cd deploy
# 构建镜像
docker build -t ts-evaluator:1.0.0 -f evaluator/Dockerfile evaluator
docker build -t ts-generator:1.0.0 -f generator/Dockerfile generator
docker build -t ts-frontend:1.0.3 -f frontend/Dockerfile frontend

# 启动 evaluator + generator
docker compose up -d

# 启动前端（反代到本地 generator 的 3002 端口）
cd frontend && python serve.py   # 默认 :8080，GENERATOR_URL=http://localhost:3002
```

浏览器打开 http://localhost:8080/ 即可。

### 方式二：前端单独预览

前端为纯静态页面，也可直接用任意静态服务器托管 `deploy/frontend/`，
但调用算法 API 需保证 `serve.py` 的反代指向可用的 ts-generator。

## 部署流程（阿里云 SAE）

详细步骤见 **[deploy/README-SAE.md](deploy/README-SAE.md)**，概要如下：

1. **构建并推送镜像到 ACR**
   ```bash
   docker save ts-evaluator:1.0.0 -o dist/ts-evaluator-1.0.0.tar   # 或直接 docker push
   # docker login / tag / push 到 registry.cn-hangzhou.aliyuncs.com/<命名空间>/...
   ```
2. **按依赖顺序创建 SAE 应用**（同一 VPC + 同一命名空间）：
   ```
   ts-evaluator → ts-generator → ts-frontend
   ```
   - `ts-evaluator`：端口 3001，仅内网，2C4G 起步
   - `ts-generator`：端口 3001，仅内网，环境变量 `EVALUATOR_URL=http://<evaluator 内网地址>:3001`
   - `ts-frontend`：端口 8080，公网入口，环境变量 `GENERATOR_URL=http://ts-generator:3001`
3. **公网访问**：前端绑定公网 SLB/NLB，**使用非 80 端口或公网 IP** 访问
   （80/443 + 未备案域名会被阿里云 ICP 拦截返回 403）。

## API 调用示例

```bash
curl -X POST http://121.41.65.106:8080/api/algorithm/invoke \
  -H "Content-Type: application/json" \
  -d '{"func": "ts_generator", "in": { ...benchmark 输入... }}'
```

输入样例见 `traffic-signal-generator/test/benchmark/`，
响应 `{"out": {...}}` 含各路口相位差方案与仿真评价指标。
