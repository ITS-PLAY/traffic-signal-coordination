#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绿波配置前端 - 本地/SAE 通用服务（仅标准库）

功能：
  1. 提供 index.html 等静态文件
  2. 将 /api/* 反向代理到 ts-generator 服务（避免浏览器跨域）

环境变量：
  PORT             监听端口，默认 8080
  GENERATOR_URL    ts-generator 服务地址
                   本地默认 http://localhost:3002（docker 容器映射端口）
                   SAE 上设为 http://ts-generator:3001（K8s 服务发现）
  UPSTREAM_TIMEOUT 上游超时秒数，默认 3600（GA 全量计算可能数分钟）
"""
import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', '8080'))
GENERATOR_URL = os.environ.get('GENERATOR_URL', 'http://localhost:3002').rstrip('/')
UPSTREAM_TIMEOUT = float(os.environ.get('UPSTREAM_TIMEOUT', '3600'))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, fmt, *args):
        pass  # 静默访问日志

    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy()
        else:
            self.send_error(404, 'Not Found')

    def _proxy(self):
        suffix = self.path[len('/api'):]  # /api/algorithm/invoke -> /algorithm/invoke
        target = GENERATOR_URL + suffix
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length > 0 else b''
        req = urllib.request.Request(
            target, data=body, method='POST',
            headers={'Content-Type': self.headers.get('Content-Type', 'application/json')})
        try:
            with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as resp:
                self._relay(resp.status, resp.headers.get('Content-Type', 'application/json'), resp.read())
        except urllib.error.HTTPError as e:
            self._relay(e.code, e.headers.get('Content-Type', 'application/json') if e.headers else 'application/json', e.read())
        except Exception as e:
            payload = json.dumps({'error': 'proxy_error', 'exception': str(e), 'upstream': target},
                                 ensure_ascii=False).encode('utf-8')
            self._relay(502, 'application/json; charset=utf-8', payload)

    def _relay(self, status, content_type, data):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print('前端地址: http://localhost:%d' % PORT)
    print('API 代理: /api/* -> %s/*' % GENERATOR_URL)
    server.serve_forever()
