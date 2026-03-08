FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY static/ static/

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    pip install --no-cache-dir git+https://github.com/Bortlesboat/bitcoinlib-rpc.git && \
    pip install --no-cache-dir . && \
    rm -rf /var/lib/apt/lists/*

COPY scripts/ scripts/

RUN mkdir -p /app/data && \
    adduser --disabled-password --no-create-home apiuser && \
    chown -R apiuser:apiuser /app/data

USER apiuser

EXPOSE 9332

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9332/healthz')" || exit 1

CMD ["python", "-m", "bitcoin_api.main"]
