from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import jwt
import random


def generate_token(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': (timezone.now() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS)).timestamp(),
        'iat': timezone.now().timestamp(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def refresh_user_token(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None, 'Token has expired'
    except jwt.InvalidTokenError:
        return None, 'Invalid token'

    new_payload = {
        'user_id': payload['user_id'],
        'email': payload['email'],
        'exp': (timezone.now() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS)).timestamp(),
        'iat': timezone.now().timestamp(),
    }

    new_token = jwt.encode(new_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return new_token, None


def generate_otp():
    return str(random.randint(100000, 999999))
