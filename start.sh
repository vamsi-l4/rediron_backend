#!/usr/bin/env bash
set -euo pipefail

echo "Starting startup script..."

# Ensure required env vars exist for critical steps (non-blocking check)
: "${DJANGO_SETTINGS_MODULE:=rediron_site.settings}"

# Run migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Load initial fixture data only when Equipment is empty
echo "Loading initial fixture data if needed..."
python manage.py load_initial_data

# Create test user
echo "Creating test user..."
python manage.py create_test_user --email krishnavamsim04@gmail.com --password Krish@009 --name "Krishna Vamsi"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn rediron_site.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-3} --log-level ${GUNICORN_LOGLEVEL:-info}
