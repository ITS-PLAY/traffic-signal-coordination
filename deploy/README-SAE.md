# 阿里云 SAE 部署说明 — ts-frontend / ts-generator / ts-evaluator

## 一、架构说明

```
浏览器 ──► ts-frontend (SAE 应用, 公网入口)
              │  静态文件 index.html + sketch.js
              │  /api/* 反向代理到 ts-generator
              ▼
           ts-generator (SAE 应用, 仅 VPC 内网)
              POST /algorithm/invoke {"func":"ts_generator","in":{...}}
              内部运行 带宽算法 + 遗传算法(GA)
              GA 每代通过 HTTP 调用 evaluator 做 SUMO 仿真评价
              ▼
           ts-evaluator (SAE 应用, 仅 VPC 内网)
              POST /algorithm/invoke {"func":"ts_evaluator","in":{...}}
              内部调用 sumo / netconvert 二进制做交通仿真
```

- 三个服务均为独立镜像、独立 SAE 应用，部署在同一 VPC 同一命名空间下。
- ts-frontend 是用户直接访问的 Web 前端（单页应用 + Python stdlib 反代），
  对外提供页面并反向代理 `/api/*` 到 ts-generator，避免浏览器跨域。
- API 契约与原 algorithm-api-base (Go) 完全一致：`POST /algorithm/invoke`，
  请求 `{"func": "<名字>", "in": {...}}`，响应 `{"out": {...}}`。
- 健康检查：ts-generator/ts-evaluator `GET /health` 返回 `{"status":"ok"}`。
- 端口：ts-frontend 容器内监听 **8080**，ts-generator/ts-evaluator 监听 **3001**。

## 二、镜像制品

| 镜像                 | 本地 tar 包                    | 说明                          |
| ------------------ | --------------------------- | --------------------------- |
| ts-frontend:1.0.0  | dist/ts-frontend-1.0.0.tar  | Web 前端（Python stdlib 静态服务 + 反代，约 50MB） |
| ts-evaluator:1.0.0 | dist/ts-evaluator-1.0.0.tar | SUMO 仿真评价服务（约 1.2GB，含 SUMO） |
| ts-generator:1.0.0 | dist/ts-generator-1.0.0.tar | 相位差生成服务（约 400MB）            |

## 三、上传镜像到阿里云 ACR（容器镜像服务）

1. 在 ACR 控制台创建命名空间（如 `zhjt`），记录仓库地址与访问凭证。
2. 本机导入并推送（以 ACR 个人版实例为例）：

```bash
docker load -i dist/ts-frontend-1.0.0.tar
docker load -i dist/ts-evaluator-1.0.0.tar
docker load -i dist/ts-generator-1.0.0.tar

# 登录 ACR（地址按实际实例替换，如 registry.cn-hangzhou.aliyuncs.com）
docker login --username=<阿里云账号> registry.cn-hangzhou.aliyuncs.com

docker tag ts-frontend:1.0.0  registry.cn-hangzhou.aliyuncs.com/<命名空间>/ts-frontend:1.0.0
docker tag ts-evaluator:1.0.0 registry.cn-hangzhou.aliyuncs.com/<命名空间>/ts-evaluator:1.0.0
docker tag ts-generator:1.0.0 registry.cn-hangzhou.aliyuncs.com/<命名空间>/ts-generator:1.0.0

docker push registry.cn-hangzhou.aliyuncs.com/<命名空间>/ts-frontend:1.0.0
docker push registry.cn-hangzhou.aliyuncs.com/<命名空间>/ts-evaluator:1.0.0
docker push registry.cn-hangzhou.aliyuncs.com/<命名空间>/ts-generator:1.0.0
```

> 提示：如果上传机器在国内访问 Docker Hub 受限，本镜像构建已通过  
> `docker.m.daocloud.io` 镜像加速源拉取基础镜像，推 ACR 不受影响。

## 四、创建 SAE 应用

### 4.1 ts-evaluator（先部署）

- 部署方式：**镜像部署**，选择上面推送的 `ts-evaluator:1.0.0`
- CPU/内存建议：2C4G 起步（SUMO 仿真为 CPU 密集）
- 端口：SAE 应用监听端口填 **3001**
- 健康检查：HTTP GET `/health`，端口 3001
- 环境变量（均可选）：
  - `GUNICORN_WORKERS`（默认 2，按 CPU 核数调整）
  - `GUNICORN_TIMEOUT`（默认 600 秒）
- 该服务**不需要公网入口**，只需 VPC 内可访问。
- 记录其内网访问地址，SAE 同 VPC 内服务名一般为  
  `http://<应用名>.<命名空间>.svc.cluster.local` 或直接使用 SAE 提供的私网 SLB 地址。

### 4.2 ts-generator（后部署）

- 镜像：`ts-generator:1.0.0`，端口 **3001**
- 环境变量（**必须配置**）：
  - `EVALUATOR_URL=http://<evaluator 内网地址>:3001`  
    （不带路径，代码内部会拼接 `/algorithm/invoke`）
- 可选环境变量：
  - `NUM_PROCESS`：算法内部并行进程数（默认自动）
  - `GUNICORN_WORKERS`（默认 2）、`GUNICORN_TIMEOUT`（默认 3600 秒，  
    GA 全量运行可能数分钟，请勿将超时调低）
- 该服务**不需要公网入口**，仅 VPC 内网可访问即可。
- 记录其内网服务名（如 `http://ts-generator.<命名空间>.svc.cluster.local:3001`），
  前端容器将通过此地址代理 API 请求。

### 4.3 ts-frontend（最后部署）

- 镜像：`ts-frontend:1.0.0`，端口 **8080**
- 环境变量（**必须配置**）：
  - `GENERATOR_URL=http://ts-generator:3001`
    （使用 SAE K8s 服务发现名；若 SAE 版本不支持服务名解析，
    则填 ts-generator 的私网 SLB 地址 `http://<generator 内网 SLB IP>:3001`）
- 可选环境变量：
  - `PORT`（默认 8080，与容器端口一致，通常无需改）
  - `UPSTREAM_TIMEOUT`（默认 3600 秒，GA 全量计算可能数分钟，
    前端反代的超时必须 >= ts-generator 的 GUNICORN_TIMEOUT）
- 对外访问：SAE 应用配置公网 SLB / CLB 入口。
- **重要**：公网监听端口请使用 **非 80 端口**（如 8080、9000 等），
  避免阿里云 ICP 备案拦截（80/443 端口 + 域名访问未备案域名会返回 403）。
  如果使用公网 IP 直接访问则无此限制。

## 五、调用示例

### 5.1 浏览器访问前端

直接在浏览器打开 `http://<frontend 公网地址>:<端口>/` 即可使用绿波配置工具。
前端页面会自动将 API 请求代理到 ts-generator，无需额外配置。

### 5.2 直接调用 API

```bash
curl -X POST http://<frontend 公网地址>:<端口>/api/algorithm/invoke \
  -H "Content-Type: application/json" \
  -d @req_generator.json
```

或直接调用 ts-generator 内网地址（仅 VPC 内可用）：

```bash
curl -X POST http://<generator 内网地址>:3001/algorithm/invoke \
  -H "Content-Type: application/json" \
  -d @req_generator.json
```

其中 `req_generator.json` 形如：

```json
{"func": "ts_generator", "in": { ...benchmark 输入... }}
```

`in` 的样例见 `traffic-signal-generator/test/benchmark/shuzhilu_shengtangba-ali.json`。  
响应 `{"out": {...}}` 中包含各路口的相位差方案与评价指标。

## 六、与原方案（algorithm-api-base）的差异

- 原方案使用私有 GitLab 依赖 `gl.ge.cn/labs/glite`（Go）打包，当前环境无法访问  
  该仓库，故按预案改用 Flask + Gunicorn 直接包装算法 `main()`。
- HTTP API 请求/响应格式与原 Go 服务完全一致，调用方无需改造。
- 原 Go 服务的 SSE 流式接口（`/algorithm/sse`）未包含在本次镜像中；  
  同步接口 `/algorithm/invoke` 功能完整。

## 七、SAE 网络与部署注意事项

### 7.1 部署顺序

```
ts-evaluator → ts-generator → ts-frontend
```

三个应用必须部署在**同一 VPC、同一命名空间**下，内网服务发现才能互通。

### 7.2 VPC 与交换机

- SAE 应用必须关联 VPC。三个应用共用同一个 VPC 和命名空间。
- 创建 NLB（网络型负载均衡）时需要选择 **2 个可用区的交换机**，
  如果某个可用区交换机不足，需先在 VPC 控制台创建。
- 建议在 SAE 同地域的 VPC 中预先创建至少 2 个可用区交换机。

### 7.3 公网访问与 ICP 备案

- ts-frontend 需要公网入口供浏览器访问，通过 SAE 绑定公网 SLB/CLB 实现。
- **80/443 端口 + 域名** 访问会被阿里云 ICP 备案拦截（返回 403 跳转到
  `betit.aliyun.com/alreject.html`），解决方案二选一：
  1. **使用非 80 端口**（如 8080、9000），通过 `http://<域名>:8080` 访问
  2. **使用公网 IP** 直接访问，不绑定域名，如 `http://<公网 IP>:8080`
- ts-evaluator 和 ts-generator **不需要**公网入口，仅 VPC 内网通信即可。

### 7.4 服务发现

- SAE 支持 K8s 风格的服务名解析：同一命名空间下，
  `http://<应用名>:<端口>` 可直接访问。
- ts-frontend 的 `GENERATOR_URL` 默认为 `http://ts-generator:3001`，
  依赖此服务名解析。若 SAE 版本不支持，需改用私网 SLB IP。

### 7.5 资源规格建议

| 应用           | CPU/内存  | 备注                          |
| -------------- | --------- | ----------------------------- |
| ts-frontend    | 0.5C 1G   | 纯静态文件 + 反代，资源消耗极低 |
| ts-generator   | 1C 2G     | GA 算法 CPU 密集，可按需扩容    |
| ts-evaluator   | 2C 4G     | SUMO 仿真 CPU 密集，可按需扩容  |

### 7.6 镜像导出与传输

如果本地无法直接 `docker push` 到 ACR，可先导出 tar 包再上传：

```bash
# 导出
docker save ts-frontend:1.0.0 -o dist/ts-frontend-1.0.0.tar

# 在目标机器导入
docker load -i dist/ts-frontend-1.0.0.tar
```
