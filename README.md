# RedIron Backend

RedIron Backend is the Django REST API for the RedIron fitness and ecommerce platform. It powers gym content, exercise videos, nutrition articles, workout tips, user profiles, role-aware account features, shop catalog data, cart and wishlist workflows, checkout, orders, notifications, and AI-assisted coaching features.

## Project Overview

The backend is a modular Django project organized around independent apps for accounts, gym content, shop commerce, and coaching. It exposes REST endpoints consumed by the React frontend and is configured for local development, PostgreSQL production deployment, static file collection, media handling, and email notifications.

## Purpose

- Provide a stable API layer for the RedIron web application.
- Store and serve structured fitness, article, equipment, product, user, order, and coaching data.
- Manage authenticated user profiles and role-aware permissions.
- Support ecommerce operations such as catalog browsing, cart management, checkout, order history, and cancellation.
- Send transactional email notifications through Django email settings.
- Run safely on a managed production platform with PostgreSQL.

## Architecture

The project follows a standard Django architecture:

- `rediron_site/` contains global settings, URL routing, ASGI, WSGI, and email utility configuration.
- `accounts/` manages users, profiles, addresses, subscriptions, preferences, authentication integration, and account APIs.
- `main/` manages gym content, articles, exercises, muscle groups, equipment, and import/export commands.
- `rediron_shop/` manages ecommerce catalog, cart, wishlist, orders, brands, reviews, policy content, coupons, and related shop APIs.
- `coach/` manages AI-assisted plans, conversations, progress, reports, challenges, notifications, and provider adapters.

The API is built with Django REST Framework. The frontend calls the backend through `/api/` routes.

## REST API

API endpoints are grouped by app:

- `/api/accounts/` - User profiles, profile initialization, addresses, trial/preferences, activity, and account data.
- `/api/` - Gym content such as nutrition articles, fitness articles, workout tips, muscle groups, equipment, and exercises.
- `/api/shop-*` - Shop categories, products, cart, checkout, orders, wishlist, reviews, offers, policies, and supporting ecommerce data.
- `/api/coach/` - Coaching dashboard, generated plans, conversations, progress tracking, challenges, reports, calendar items, and notifications.
- `/admin/` - Django admin interface.

## Folder Structure

```text
gitpull_backend/
  accounts/
    admin.py
    authentication.py
    middleware.py
    models.py
    serializers.py
    urls.py
    views.py
    migrations/
  coach/
    models.py
    permissions.py
    serializers.py
    services/
    urls.py
    views.py
    migrations/
  main/
    fixtures/
    management/commands/
    models.py
    serializers.py
    urls.py
    views.py
    migrations/
  rediron_shop/
    management/commands/
    models.py
    serializers.py
    urls.py
    views.py
    migrations/
  rediron_site/
    settings.py
    urls.py
    email_utils.py
    asgi.py
    wsgi.py
  manage.py
  requirements.txt
  render.yaml
  start.sh
```

## Apps

### Accounts

Handles the custom user model, profile records, profile images, address data, user preferences, account initialization, user activity data, and role-aware account access.

### Main

Handles public and protected fitness content, including exercises, equipment, muscle groups, workout tips, nutrition articles, fitness articles, and JSON import/export workflows.

### RedIron Shop

Handles ecommerce catalog data, categories, subcategories, brands, products, product details, reviews, cart items, wishlist items, orders, coupons, offers, policies, FAQs, dealer data, and shop pages consumed by the frontend.

### Coach

Handles RedIron Coach AI data models, generated plan storage, chat conversations, progress records, weekly reports, challenges, notifications, prompt/context services, response validation, and provider adapters.

## Authentication Overview

Authentication is handled by the configured external identity service and represented locally by the Django `CustomUser` model. Protected API requests resolve the authenticated user, initialize profile-related records when needed, and enforce permissions through Django REST Framework permission classes and app-level access checks.

The backend stores only the user data required by the application, such as identity linkage, email, display name, profile data, preferences, addresses, orders, progress, and related records.

## Role Based Permissions

The backend uses Django and DRF permission patterns to separate public content from authenticated account, profile, checkout, order, wishlist, and coaching operations. Admin access is handled through Django admin permissions and staff/superuser flags.

## Database

Production is configured for PostgreSQL. Local development can use PostgreSQL through `DATABASE_URL` or the individual database environment variables. If no PostgreSQL configuration is provided, the project falls back to local SQLite for development.

## PostgreSQL

The production database target is Neon PostgreSQL. Database connection details must be provided through environment variables and must not be committed to the repository.

## Models

Model groups include:

- `accounts.CustomUser`, profile, address, subscription, preference, and activity models.
- `main` content models for exercises, equipment, articles, tips, and muscle groups.
- `rediron_shop` ecommerce models for catalog, cart, wishlist, orders, reviews, coupons, and policy content.
- `coach` models for plans, conversations, progress, challenges, reports, calendar entries, and notifications.

## Serializers

Serializers convert Django models to API-safe JSON and validate inbound request payloads. Each app keeps serializers close to its models and views to preserve feature boundaries.

## Views

Views and viewsets implement the REST API behavior for content listing, detail retrieval, profile initialization, cart updates, checkout, orders, coach workflows, and supporting data.

## URLs

URL routing is split by app and mounted in `rediron_site/urls.py`. This keeps route ownership clear and avoids a single large root URL file.

## Services

Service modules hold non-view business operations such as AI prompt building, response parsing, provider adapters, context loading, JSON validation, and shared utility behavior. This keeps views focused on HTTP request/response handling.

## Utilities

Utility modules provide reusable account helpers, email helpers, payment integration wrappers, middleware support, and content import helpers.

## Admin

Django admin is enabled for internal management of users, content, shop data, orders, and coaching records. Admin access should be restricted to trusted staff accounts.

## Email System

Email notifications are sent through Django's email backend configuration. The project supports transactional notifications such as order confirmations, cancellation notices, and administrative alerts. Provider credentials must be configured through environment variables only.

## User Management

User management is centered on the custom user model and related profile records. The API initializes user-adjacent records after authentication so the frontend can rely on profile, cart, wishlist, and preferences being available.

## Migrations

All Django migrations are committed and must remain in order. Do not delete or rewrite migrations after they have been applied to production. Use standard Django migration commands for schema changes.

## Static Files

Static files are collected into `staticfiles/` for production serving through WhiteNoise. The generated `staticfiles/` directory is ignored and should not be committed.

## Media

Uploaded and imported media files are stored under `media/` in local development. Production media storage strategy should be configured according to the deployment environment. The local `media/` directory is ignored.

## Environment Variables

Use environment variable names only in documentation. Never commit real values.

```text
SECRET_KEY
DEBUG
ALLOWED_HOSTS
DATABASE_URL
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
DB_SSLMODE
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
EMAIL_BACKEND
EMAIL_HOST
EMAIL_PORT
EMAIL_USE_TLS
EMAIL_USE_SSL
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_FROM_ADDRESS
DEFAULT_FROM_EMAIL
SERVER_EMAIL
ADMIN_EMAIL
SUPPORT_EMAIL
SITE_OWNER_EMAIL
SHOP_ADMIN_EMAIL
EMAIL_TIMEOUT
JWT_SECRET_KEY
JWT_ALGORITHM
JWT_EXP_DELTA_SECONDS
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
COACH_AI_PROVIDER
GEMINI_API_KEY
GEMINI_MODEL
GEMINI_FALLBACK_MODELS
OPENAI_API_KEY
OPENAI_MODEL
SECURE_SSL_REDIRECT
SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE
STATICFILES_STORAGE
TIME_ZONE
PAGE_SIZE
DJANGO_LOG_LEVEL
LOAD_ALL_DATA
```

Authentication service keys are also required for protected API access and should be configured privately in the deployment environment.

## Installation

### Requirements

- Python
- pip
- PostgreSQL for production-like development
- Virtual environment tool

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file using `.env.example` as a reference, then configure only local development values.

### Runserver

```bash
python manage.py runserver
```

The API runs locally at:

```text
http://127.0.0.1:8000
```

### Makemigrations

```bash
python manage.py makemigrations
```

### Migrate

```bash
python manage.py migrate
```

### Collectstatic

```bash
python manage.py collectstatic --noinput
```

## Data Loading

The deployment start script can optionally load the active production fixture when `LOAD_ALL_DATA` is enabled. Keep production data files intentional and avoid committing duplicate backups.

Useful commands:

```bash
python manage.py import_all_data
python manage.py load_initial_data
python manage.py load_products_json
python manage.py refresh_nutrition_articles
python manage.py refresh_workout_tips
```

## Deployment Overview

The backend is prepared for Render deployment.

- Build command: `pip install -r requirements.txt`
- Start command: `bash start.sh`
- Runtime: configured in `runtime.txt`
- Deployment blueprint: `render.yaml`
- Static files: collected during startup
- Database: configured through managed PostgreSQL environment variables

## Database Overview

Production uses Neon PostgreSQL through `DATABASE_URL` or separate PostgreSQL connection variables. SSL mode should remain enabled for hosted PostgreSQL connections.

## API Documentation

Current API documentation is maintained in repository markdown and app-level URL/serializer definitions. A future production improvement is to expose an OpenAPI schema and interactive API reference generated from Django REST Framework metadata.

## Future Improvements

- Add generated OpenAPI documentation for all public and protected endpoints.
- Add request/response examples for core shop and account workflows.
- Expand automated API tests for checkout, orders, profile initialization, and coach endpoints.
- Add CI checks for migrations, formatting, tests, and deployment configuration.
- Move large fixture lifecycle management into a documented data pipeline.

## Contributing

1. Create a focused feature branch.
2. Keep migrations intact and review them before commit.
3. Run `python manage.py check` before opening a pull request.
4. Run migration checks before deployment.
5. Do not commit `.env`, local databases, media uploads, static build output, logs, caches, or temporary files.
6. Document new environment variable names without values.

## License

License information is not yet specified. Add the final project license before public distribution.
