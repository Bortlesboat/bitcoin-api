FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

COPY scripts/ scripts/

RUN mkdir -p /app/data && \
    adduser --disabled-password --no-create-home apiuser && \
    chown -R apiuser:apiuser /app/data

USER apiuser

EXPOSE 9332

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9332/api/v1/health')" || exit 1

CMD ["uvicorn", "bitcoin_api.main:app", "--host", "0.0.0.0", "--port", "9332"]
