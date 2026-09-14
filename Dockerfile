FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -v -r /app/requirements.txt

COPY backend /app/backend

WORKDIR /app/backend

RUN groupadd --gid 1001 finpilot \
    && useradd --uid 1001 --gid 1001 --no-create-home finpilot \
    && mkdir -p /app/backend/staticfiles \
    && chown -R finpilot:finpilot /app

USER finpilot

EXPOSE 8000

ENTRYPOINT ["/app/backend/docker/entrypoint.sh"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1