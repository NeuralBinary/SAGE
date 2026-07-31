FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    SAGE_AUTO_CREATE_SCHEMA=false
WORKDIR /app
RUN addgroup --system sage && adduser --system --ingroup sage sage
COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY src ./src
COPY alembic ./alembic
RUN python -m pip install --no-cache-dir ".[postgres,mcp]"
USER sage
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=2)" || exit 1
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn sage_plugin.main:app --host 0.0.0.0 --port 8080 --workers 1 --proxy-headers"]
