FROM docker.m.daocloud.io/library/python:3.11.4-bookworm

ENV SUMO_HOME=/usr/share/sumo
WORKDIR /app

# 安装 SUMO（sumo / netconvert 命令行工具）
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends sumo sumo-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ts_evaluator.py ./
COPY server.py ./

ENV PORT=3001 \
    ALGO_MODULE=ts_evaluator \
    ALGO_NAME=ts_evaluator \
    GUNICORN_WORKERS=2 \
    GUNICORN_TIMEOUT=600

EXPOSE 3001

CMD ["sh", "-c", "exec gunicorn -w ${GUNICORN_WORKERS} -b 0.0.0.0:${PORT} --timeout ${GUNICORN_TIMEOUT} server:app"]
