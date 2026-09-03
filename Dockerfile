FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

# Run as a non-root user. media/ must exist and be writable before we drop
# privileges, otherwise homework uploads fail at runtime.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/media \
    && chown -R appuser:appuser /app \
    && chmod +x /app/scripts/start.sh
USER appuser

EXPOSE 8000

# Liveness only — /healthz deliberately does not touch the database, so a paused
# Supabase project does not turn into a restart loop. slim has no curl/wget.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/healthz\", timeout=4).status == 200 else 1)"

# Render sets PORT (often 10000); default 8000 for local docker compose.
# Env knobs: SEED_DEMO, SEED_SHOWCASE, DEMO_RESET_ON_START, WEB_CONCURRENCY.
CMD ["sh", "/app/scripts/start.sh"]
