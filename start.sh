#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting RedIron Backend Deployment..."

# Ensure required env vars exist for critical steps (non-blocking check)
: "${DJANGO_SETTINGS_MODULE:=rediron_site.settings}"

# Run migrations
echo "📊 Applying database migrations..."
python manage.py migrate --noinput

# Load initial fixture data and refresh nutrition articles
echo "📚 Loading fixture data and refreshing nutrition articles..."
python manage.py load_initial_data

# This automatically:
# ✓ Loads master_db.json (equipment, base articles, etc.)
# ✓ Deletes all old nutrition articles
# ✓ Loads new premium nutrition articles from rediron_articles_complete_guide.json
# ✓ Frontend automatically fetches fresh data from the API

# Create test user
echo "👤 Setting up test user..."
python manage.py create_test_user --email krishnavamsim04@gmail.com --password Krish@009 --name "Krishna Vamsi"

echo "✅ Deployment complete! New nutrition data is live."
echo "📱 Frontend will automatically display new articles when it refreshes."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn rediron_site.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-3} --log-level ${GUNICORN_LOGLEVEL:-info}
