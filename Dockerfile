# Build stage for frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci
COPY ui ./

ARG VITE_BROWSER_URL=http://localhost:7474
ENV VITE_BROWSER_URL=$VITE_BROWSER_URL
RUN npm run build

# Build stage for Python dependencies
FROM python:3.12-slim AS backend-builder

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=backend-builder /app/.venv ./.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY src ./src
COPY data ./data

# Copy built frontend
COPY --from=frontend-builder /app/ui/dist ./ui/dist

# Set production mode
ENV NODE_ENV=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
