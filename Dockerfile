FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

COPY scripts/ scripts/
COPY .env.example .env

EXPOSE 8333

CMD ["uvicorn", "bitcoin_api.main:app", "--host", "0.0.0.0", "--port", "8333"]
