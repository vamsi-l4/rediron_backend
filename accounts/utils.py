from django.utils import timezone
from datetime import timedelta, datetime
from django.conf import settings
import jwt
import secrets

from .models import RefreshToken

def generate_access_token(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS),
        'iat': datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    # PyJWT >=2 returns str; keep as str
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

def generate_refresh_token_for_user(user):
    token = secrets.token_urlsafe(64)
    expiry = timezone.now() + timedelta(days=getattr(settings, 'REFRESH_TOKEN_EXP_DAYS', 7))
    RefreshToken.objects.create(user=user, token=token, expiry=expiry)
    return token

def refresh_access_token_using_refresh_token(refresh_token_str):
    try:
        rt = RefreshToken.objects.get(token=refresh_token_str)
    except RefreshToken.DoesNotExist:
        return None, 'Refresh token not found'

    if rt.expiry < timezone.now():
        return None, 'Refresh token expired'

    user = rt.user
    new_access = generate_access_token(user)
    return new_access, None

def generate_otp():
    # cryptographically secure 6-digit code
    return f"{secrets.randbelow(900000) + 100000}"
