FROM node:22-bookworm-slim AS node-runtime

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Copy Node.js 22 + npm/npx for the Helius MCP stdio server.
COPY --from=node-runtime /usr/local/ /usr/local/

WORKDIR /app/backend

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app ./app
COPY backend/tests ./tests
COPY pytest.ini /app/pytest.ini

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
