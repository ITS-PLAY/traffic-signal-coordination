FROM docker.m.daocloud.io/library/python:3.11-slim-bookworm

WORKDIR /app
COPY index.html serve.py sketch.js ./

# SAE 上通过 K8s 服务名访问 generator；本地 docker 可用 http://host.docker.internal:3002
ENV PORT=8080 \
    GENERATOR_URL=http://ts-generator:3001 \
    UPSTREAM_TIMEOUT=3600

EXPOSE 8080

CMD ["python", "serve.py"]
