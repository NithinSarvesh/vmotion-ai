# Multi-stage Dockerfile for VMotion AI Cloud Control Plane
# Stage 1: Build React/TypeScript Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.11 Production Control Plane Server
FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    PORT=8000 \
    SERVE_FRONTEND=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application source
COPY backend/ /app/backend/

# Copy AI model checkpoints and frozen contracts
COPY models/ /app/models/

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Expose HTTP/WSS Port
EXPOSE 8000

# Run FastAPI Cloud Control Plane with dynamic PORT support
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
