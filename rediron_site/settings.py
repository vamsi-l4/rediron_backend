import os
import base64
from pathlib import Path
from urllib.parse import urlsplit
import dj_database_url
import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the backend .env file, regardless of the current working directory
dotenv.load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-secret-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,rediron-backend-1.onrender.com').split(',') if h.strip()]

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'main',
    'accounts',
    'rediron_shop',
    'coach',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ============================================
    # PRODUCTION-GRADE: DATA ISOLATION MIDDLEWARE
    # ============================================
    'accounts.middleware.DataIsolationMiddleware',  # Ensure user data isolation
    'accounts.middleware.ClerkUserValidationMiddleware',  # Validate Clerk setup
]

ROOT_URLCONF = 'rediron_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rediron_site.wsgi.application'
ASGI_APPLICATION = 'rediron_site.asgi.application'

# Database
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL:
    is_postgres_url = DATABASE_URL.startswith(('postgres://', 'postgresql://'))
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=is_postgres_url,
        )
    }
else:
    db_name = os.environ.get('DB_NAME', '')
    db_user = os.environ.get('DB_USER', '')
    db_password = os.environ.get('DB_PASSWORD', '')
    db_host = os.environ.get('DB_HOST', '')
    db_port = os.environ.get('DB_PORT', '5432')

    if all([db_name, db_user, db_password, db_host]):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': db_name,
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': db_host,
                'PORT': db_port,
                'OPTIONS': {
                    'sslmode': os.environ.get('DB_SSLMODE', 'require'),
                },
                'CONN_MAX_AGE': 600,
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

# Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = os.environ.get('STATICFILES_STORAGE', 'whitenoise.storage.CompressedManifestStaticFilesStorage')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS
CORS_ALLOW_ALL_ORIGINS = False

def _clean_origin(origin):
    value = (origin or '').strip().rstrip('/')
    while value.startswith('https://https://'):
        value = 'https://' + value[len('https://https://'):]
    while value.startswith('http://http://'):
        value = 'http://' + value[len('http://http://'):]
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return ''
    return f'{parsed.scheme}://{parsed.netloc}'

def _clean_origin_list(raw_value):
    cleaned = [_clean_origin(item) for item in (raw_value or '').split(',')]
    return [item for item in cleaned if item]

_cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = _clean_origin_list(_cors_origins)
CORS_ALLOWED_ORIGINS.extend([
    'https://roaring-scone-cfda07.netlify.app',
    'http://localhost:3000',
    'https://localhost:3000',
])
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(CORS_ALLOWED_ORIGINS))
CORS_ALLOW_CREDENTIALS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'Authorization',
    'authorization',
    'content-type',
    'x-clerk-email',
    'x-clerk-name',
]

_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = _clean_origin_list(_csrf_origins)
# Add CORS origins to trusted CSRF origins to support cross-origin requests
# from frontend servers like localhost:3000
CSRF_TRUSTED_ORIGINS.extend([
    'https://roaring-scone-cfda07.netlify.app',
    'http://localhost:3000',
    'https://localhost:3000',
])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# ============================================
# BREVO SMTP CONFIGURATION
# ============================================
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
)
def _env_bool(name, default=False):
    return str(os.environ.get(name, str(default))).strip().lower() in {'1', 'true', 'yes', 'on'}

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com')
EMAIL_PORT = int(str(os.environ.get('EMAIL_PORT', '587')).strip())
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = _env_bool('EMAIL_USE_SSL', False)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_FROM_ADDRESS = os.environ.get('EMAIL_FROM_ADDRESS', EMAIL_HOST_USER)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_FROM_ADDRESS or EMAIL_HOST_USER)
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL or EMAIL_HOST_USER)
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', os.environ.get('SITE_OWNER_EMAIL', 'support@rediron.com'))
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', ADMIN_EMAIL)
SITE_OWNER_EMAIL = ADMIN_EMAIL
SHOP_ADMIN_EMAIL = os.environ.get('SHOP_ADMIN_EMAIL', ADMIN_EMAIL)
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))

# JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXP_DELTA_SECONDS = int(os.environ.get('JWT_EXP_DELTA_SECONDS', 3600))

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authentication.ClerkAuthentication',  # NEW: Clerk authentication
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        # 'accounts.authentication.JWTAuthentication',  # COMMENTED OUT: Old JWT authentication
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.environ.get('PAGE_SIZE', 10)),
}

AUTH_USER_MODEL = 'accounts.CustomUser'

# ============================================
# CLERK AUTHENTICATION (PRODUCTION-GRADE)
# ============================================
CLERK_SECRET_KEY = os.environ.get('CLERK_SECRET_KEY', '')
CLERK_PUBLISH_KEY = os.environ.get('CLERK_PUBLISH_KEY') or os.environ.get('CLERK_PUBLISHABLE_KEY', '')

def _clerk_frontend_api_from_publishable_key(publishable_key):
    """Clerk publishable keys encode the frontend API domain after the prefix."""
    try:
        encoded = (publishable_key or '').split('_', 2)[-1]
        padded = encoded + '=' * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode('utf-8').strip()
        return decoded.rstrip('$').strip()
    except Exception:
        return ''

_clerk_frontend_api = _clerk_frontend_api_from_publishable_key(CLERK_PUBLISH_KEY)
_clerk_issuer = f'https://{_clerk_frontend_api}' if _clerk_frontend_api else ''
CLERK_ISSUER = (os.environ.get('CLERK_ISSUER') or _clerk_issuer).rstrip('/')
CLERK_JWKS_URL = (
    os.environ.get('CLERK_JWKS_URL')
    or (f'{CLERK_ISSUER}/.well-known/jwks.json' if CLERK_ISSUER else 'https://api.clerk.dev/v1/jwks')
)

# In production, both keys are required
if not DEBUG:
    if not CLERK_SECRET_KEY or not CLERK_PUBLISH_KEY:
        raise ValueError('CLERK_SECRET_KEY and CLERK_PUBLISH_KEY are required in production')

# Log Clerk configuration status
if CLERK_SECRET_KEY:
    logger = __import__('logging').getLogger(__name__)
    logger.info('✅ Clerk authentication configured')
else:
    logger = __import__('logging').getLogger(__name__)
    logger.warning('⚠️ Clerk keys not configured - using development mode')

AUTHENTICATION_BACKENDS = [
    'accounts.authentication.AllowInactiveUserBackend',
    'django.contrib.auth.backends.ModelBackend',
]

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# ============================================
# REDIRON COACH AI CONFIGURATION
# ============================================
COACH_AI_PROVIDER = os.environ.get('COACH_AI_PROVIDER', 'gemini')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# Security (production)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO')},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REFRESH_TOKEN_EXP_DAYS = 7

# Force HTTPS for images in production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

