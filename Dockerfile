# APTRANSCO SFRA platform — backend image.
#
# Single-stage Python image. ~700 MB. The frontend lives in a separate
# image so substations that don't need the dashboard can omit it.
#
# Build:
#   docker build -t aptransco/sfra-backend:0.3 .
#
# Run (sqlite, dev):
#   docker run -p 8000:8000 -v $(pwd)/data:/app/data aptransco/sfra-backend:0.3
#
# Run (postgres, prod):
#   docker run -p 8000:8000 \
#     -e SFRA_DATABASE_URL=postgresql+psycopg://user:pwd@db:5432/sfra \
#     -e SFRA_JWT_SECRET=$(openssl rand -hex 32) \
#     -v $(pwd)/data/storage:/app/data/storage \
#     aptransco/sfra-backend:0.3

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for scipy / numpy wheels (slim image lacks them); kept lean.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libpq5 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only what the backend needs. The frontend is built separately.
COPY pyproject.toml ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY standards/ ./standards/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Install Python deps. Pinned versions match pyproject.toml.
RUN pip install --upgrade pip \
    && pip install \
        "fastapi==0.115.0" \
        "uvicorn[standard]==0.32.0" \
        "python-multipart==0.0.12" \
        "pydantic==2.9.2" \
        "sqlalchemy>=2.0.30,<2.1" \
        "alembic>=1.13,<2.0" \
        "psycopg[binary]>=3.2,<4" \
        "numpy==1.26.4" \
        "scipy==1.13.1" \
        "pandas==2.2.2" \
        "matplotlib>=3.8,<3.10" \
        "reportlab==4.2.2" \
        "openpyxl>=3.1,<4" \
        "lxml==5.3.0" \
        "pyyaml>=6.0,<7" \
        "python-jose[cryptography]>=3.3,<4" \
        "bcrypt>=4,<5" \
        "httpx==0.27.2"

RUN pip install -e .

# Storage volumes mount here; entrypoint creates the SQLite parent dir if missing.
RUN mkdir -p /app/data/storage /app/data/audit /app/assets/branding

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# Entrypoint: run Alembic migrations, seed combinations, then launch uvicorn.
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "sfra_full.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
