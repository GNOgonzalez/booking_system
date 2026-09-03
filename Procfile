release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-60} --graceful-timeout 30 --access-logfile - --error-logfile -
