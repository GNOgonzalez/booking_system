FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Render sets PORT (often 10000); default 8000 for local docker compose.
# SEED_DEMO=true runs bootstrap_sandbox --demo after migrate (free tier has no Shell).
# SEED_SHOWCASE=true adds --showcase (demo_student membership + upcoming lesson).
# DEMO_RESET_ON_START=true adds --reset (fresh demo data on each container start).
CMD ["sh", "-c", "python manage.py migrate --noinput && if [ \"$SEED_DEMO\" = \"true\" ]; then RESET_FLAG=\"\"; SHOWCASE_FLAG=\"\"; if [ \"$DEMO_RESET_ON_START\" = \"true\" ]; then RESET_FLAG=\"--reset\"; fi; if [ \"$SEED_SHOWCASE\" = \"true\" ]; then SHOWCASE_FLAG=\"--showcase\"; fi; python manage.py bootstrap_sandbox --demo $RESET_FLAG $SHOWCASE_FLAG; fi && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
