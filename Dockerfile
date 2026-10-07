# Multi-stage build for Hitech AVL CRM (Frontend + Backend in a single production container)

# ---------------------------------------------------------------------------
# Stage 1: Build React Frontend
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python Backend + Production Runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8001

# Install build dependencies for python packages
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Install backend Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./

# Copy built frontend static files into backend/static
COPY --from=frontend-builder /app/frontend/build /app/static

# Expose production port 8001
EXPOSE 8001

# Container health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8001/health || exit 1

# Production start command using $PORT
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001} --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
