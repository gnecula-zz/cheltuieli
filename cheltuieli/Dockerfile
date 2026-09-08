# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV BUILD_INGRESS=1
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend /src/dist /app/frontend/dist

ENV AUTH_MODE=homeassistant \
    DATABASE_URL=sqlite:////data/cheltuieli.db \
    UPLOAD_DIR=/data/uploads \
    FRONTEND_DIR=/app/frontend/dist \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data/uploads

EXPOSE 8099

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]
