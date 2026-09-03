#!/usr/bin/env sh
# Container entrypoint: migrate, optionally seed, purge stale homework, then serve.
# Used by the Dockerfile CMD. Every step logs to stdout so Render captures it.
set -e

echo "==> migrate"
python manage.py migrate --noinput

# SEED_DEMO=true recreates the sandbox accounts. Render Free has no shell, so
# seeding has to happen here or not at all.
if [ "$SEED_DEMO" = "true" ]; then
  echo "==> bootstrap_sandbox"
  set -- --demo
  if [ "$DEMO_RESET_ON_START" = "true" ]; then
    set -- "$@" --reset
  fi
  if [ "$SEED_SHOWCASE" = "true" ]; then
    set -- "$@" --showcase
  fi
  python manage.py bootstrap_sandbox "$@"
fi

# Homework uploads live on the container's ephemeral disk, so this is the only
# place a purge can delete the actual files — a scheduled job running elsewhere
# would drop the database rows and leave the files orphaned. Non-fatal: a failed
# purge must not stop the app from booting.
echo "==> purge_expired_homework"
python manage.py purge_expired_homework || echo "purge_expired_homework failed; continuing"

echo "==> gunicorn on ${PORT:-8000} (${WEB_CONCURRENCY:-2} workers)"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  --log-level "${GUNICORN_LOG_LEVEL:-info}"
