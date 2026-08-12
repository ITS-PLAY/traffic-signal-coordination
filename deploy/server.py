# -*- coding: utf-8 -*-
"""
算法服务 HTTP 包装层（Flask）

保持与 algorithm-api-base (Go/glite) 完全一致的 API 契约：
  POST /algorithm/invoke
    请求: {"func": "<algo_name>", "in": <任意JSON>}
    响应: {"out": <算法 main() 返回的JSON>}

通过环境变量配置：
  ALGO_MODULE  - 算法模块名（如 ts_evaluator / ts_generator）
  ALGO_NAME    - 对外暴露的 func 名称（与 ALGO_MODULE 一致）
  PORT         - 监听端口，默认 3001
"""
import importlib
import json
import os
import traceback

from flask import Flask, Response, jsonify, request

ALGO_MODULE = os.environ.get("ALGO_MODULE", "ts_evaluator")
ALGO_NAME = os.environ.get("ALGO_NAME", ALGO_MODULE)

algo = importlib.import_module(ALGO_MODULE)

app = Flask(__name__)


@app.after_request
def add_cors_headers(resp):
    """允许浏览器跨域直连（前端页面部署在别处时必需）"""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/algorithm/invoke", methods=["OPTIONS"])
def invoke_preflight():
    """处理 CORS 预检请求"""
    return ("", 204)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": ALGO_NAME})


@app.route("/algorithm/invoke", methods=["POST"])
def invoke():
    req = request.get_json(force=True, silent=True)
    if not isinstance(req, dict):
        return jsonify({"error": "invalid json body"}), 400

    func = req.get("func")
    if func != ALGO_NAME:
        return jsonify({"error": "Algorithm not found: {}".format(func)}), 404

    if "in" not in req:
        return jsonify({"error": "missing field: in"}), 400

    try:
        # Go 版本中 main() 接收 in 字段的原始 JSON 字节，这里等价构造
        in_bytes = json.dumps(req["in"], ensure_ascii=False).encode("utf-8")
        out_str = algo.main(in_bytes)
        if not isinstance(out_str, (str, bytes)):
            out_str = json.dumps(out_str, ensure_ascii=False)
        if isinstance(out_str, bytes):
            out_str = out_str.decode("utf-8")
        # Go 版本将算法 stdout 原样嵌入 out 字段（json.RawMessage），保持同样行为
        return Response(
            '{"out":' + out_str + '}',
            content_type="application/json; charset=utf-8",
        )
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": "internal_error", "exception": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3001"))
    app.run(host="0.0.0.0", port=port, threaded=True)
