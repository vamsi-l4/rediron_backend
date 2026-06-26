# RedIron SQLite to Neon PostgreSQL Migration

## 1. Export Current SQLite Data

Run this while `.env` still points to local SQLite:

```bash
python manage.py export_all_data
```

This writes:

```text
main/fixtures/all_data.json
```

## 2. Configure Neon

Set either `DATABASE_URL` or the separate `DB_*` variables in `.env` or Render.

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

The Django settings force SSL for `DATABASE_URL` and use `DB_SSLMODE=require` for separate variables.

## 3. Migrate PostgreSQL

```bash
python manage.py migrate
```

## 4. Import Data Into Neon

```bash
python manage.py loaddata main/fixtures/all_data.json
```

Optional product/equipment refresh commands:

```bash
python manage.py load_products_json
python manage.py loaddata rediron_shop/fixtures/equipment_products_clean.json
```

## 5. Render Deployment

Required Render environment variables:

```env
SECRET_KEY=your-production-secret
DEBUG=False
DATABASE_URL=your-neon-url
ALLOWED_HOSTS=your-render-host.onrender.com
CLERK_SECRET_KEY=your-clerk-secret
CLERK_PUBLISH_KEY=your-clerk-publishable-key
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=your-email
```

Deploy command:

```bash
bash start.sh
```

Static files are collected through `collectstatic`, `gunicorn` serves Django, and `whitenoise` serves static assets.
