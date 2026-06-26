#!/usr/bin/env bash
set -euo pipefail

echo "Starting RedIron Backend Deployment..."

# Ensure required env vars exist for critical steps (non-blocking check)
: "${DJANGO_SETTINGS_MODULE:=rediron_site.settings}"

# Run migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

if [[ "${LOAD_ALL_DATA:-false}" == "true" && -f "main/fixtures/all_data.json" ]]; then
  echo "Loading exported RedIron data fixture..."
  python manage.py loaddata main/fixtures/all_data.json
fi

if [[ "${LOAD_INITIAL_DATA:-false}" == "true" ]]; then
  echo "Loading initial seed fixtures..."
  python manage.py load_initial_data
fi

echo "Database setup complete."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn rediron_site.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-3} --log-level ${GUNICORN_LOGLEVEL:-info}
