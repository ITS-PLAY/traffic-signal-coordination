FROM docker.m.daocloud.io/library/python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ts_generator.py ./
COPY server.py ./

ENV PORT=3001 \
    ALGO_MODULE=ts_generator \
    ALGO_NAME=ts_generator \
    GUNICORN_WORKERS=2 \
    GUNICORN_TIMEOUT=3600

EXPOSE 3001

# EVALUATOR_URL 指向 evaluator 服务地址，例如 http://ts-evaluator:3001
CMD ["sh", "-c", "exec gunicorn -w ${GUNICORN_WORKERS} -b 0.0.0.0:${PORT} --timeout ${GUNICORN_TIMEOUT} server:app"]
