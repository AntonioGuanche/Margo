# =============================================================
# Stage 1 — Build frontend (Node 20)
# =============================================================
FROM node:20-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# =============================================================
# Stage 2 — Python backend + frontend dist
# =============================================================
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (pyproject.toml only, no source yet)
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

# Copy backend source for runtime
COPY backend/app/ app/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini .
COPY backend/scripts/ scripts/

# Copy built frontend into /app/static
COPY --from=frontend-build /frontend/dist /app/static

EXPOSE 8080

CMD ["bash", "scripts/start.sh"]
