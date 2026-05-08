import os
from pathlib import Path
import dj_database_url
import dotenv

# Load environment variables
dotenv.load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

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
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
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
CORS_ALLOWED_ORIGINS = [
    'https://roaring-scone-cfda07.netlify.app',
    'http://localhost:3000',
    'https://localhost:3000',
]
CORS_ALLOW_CREDENTIALS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'Authorization',
    'authorization',
    'content-type',
]

_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [u.strip() for u in _csrf_origins.split(',') if u.strip()]
# Add CORS origins to trusted CSRF origins to support cross-origin requests
# from frontend servers like localhost:3000
CSRF_TRUSTED_ORIGINS.extend([
    'https://roaring-scone-cfda07.netlify.app',
    'http://localhost:3000',
    'https://localhost:3000',
])

# ============================================
# EMAIL CONFIGURATION (COMMENTED OUT - Clerk handles email verification)
# ============================================
# Old email configuration for OTP and verification emails
# Now Clerk handles all email verification and notifications
# Keep these commented for backward compatibility during migration

# EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
# EMAIL_HOST = os.environ.get('EMAIL_HOST')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
# DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
# EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', 10))

# Fallback to console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
CLERK_PUBLISH_KEY = os.environ.get('CLERK_PUBLISH_KEY', '')
CLERK_ISSUER = os.environ.get('CLERK_ISSUER', '')
CLERK_JWKS_URL = os.environ.get('CLERK_JWKS_URL', '')

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
# OPENAI CONFIGURATION (Performance Lab)
# ============================================
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

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
