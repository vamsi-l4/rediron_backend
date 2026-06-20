from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
import json
import jwt
from jwt import PyJWTError
from django.conf import settings
import logging
import requests
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:

    logger.warning("Cryptography not available - JWT signature verification disabled (dev mode only)") 
import base64

logger = logging.getLogger(__name__)
User = get_user_model()

# ============================================
# CLERK TOKEN VERIFICATION
# ============================================
# Prefer settings values (deployed) but fall back to Clerk public JWKS
CLERK_JWKS_URL = getattr(settings, 'CLERK_JWKS_URL', 'https://api.clerk.dev/v1/jwks')
_clerk_public_keys = {}  # Cache Clerk's public keys by kid


def get_clerk_public_key(kid):
    """Fetch Clerk's public keys for JWT verification and cache them.

    Returns a public key object usable by PyJWT or None on failure.
    """
    global _clerk_public_keys

    if kid in _clerk_public_keys:
        return _clerk_public_keys[kid]

    try:
        jwks_url = CLERK_JWKS_URL
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        jwks = response.json()

        for key_data in jwks.get('keys', []):
            key_id = key_data.get('kid')
            if key_id:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
                _clerk_public_keys[key_id] = public_key

        if kid not in _clerk_public_keys:
            logger.warning(f"[Clerk] Key {kid} not found in JWKS at {jwks_url}")
            return None

        return _clerk_public_keys[kid]
    except Exception:
        logger.exception("[Clerk] Failed to fetch/parse JWKS")
        return None


class ClerkAuthentication(BaseAuthentication):
    """
    Production-grade Clerk JWT authentication.
    Expects Authorization: Bearer <clerk_token>

    Validates token structure, signature, and extracts clerk_user_id.
    In development: skips signature verification for easier testing.
    In production: verifies signatures with Clerk's public key.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        logger.info(f"[ClerkAuth] Authenticating {request.method} {request.path}")
        logger.info(f"[ClerkAuth] Authorization header present: {bool(auth_header)}")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.info(f"[ClerkAuth] ⚠️ No Authorization header or invalid format")
            return None

        token = auth_header.split(' ', 1)[1]
        try:
            # ============================================
            # STEP 1: DECODE TOKEN WITH PROPER VERIFICATION
            # ============================================
            # Decode / verify token
            if settings.DEBUG:
                # Development: allow easier local testing by skipping signature
                payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
                logger.info("[ClerkAuth] DEV MODE: Skipping signature and audience verification")
            else:
                # Production: verify signature with Clerk key and validate issuer (not audience)
                try:
                    header = jwt.get_unverified_header(token)
                    kid = header.get('kid')
                    if not kid:
                        logger.error('[ClerkAuth] Token missing "kid" in header')
                        raise AuthenticationFailed('Token missing key ID')

                    public_key = get_clerk_public_key(kid)
                    if not public_key:
                        logger.error(f'[ClerkAuth] No public key available for kid={kid}')
                        raise AuthenticationFailed('Invalid token key')

                    # Validate issuer if configured (strip trailing slash to be safe)
                    issuer = getattr(settings, 'CLERK_ISSUER', None)
                    if issuer:
                        issuer = issuer.rstrip('/')

                    # IMPORTANT: Do not validate audience here unless you control the audience
                    # Some Clerk tokens do not include an `aud` claim that matches your publishable key.
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=['RS256'],
                        options={"verify_aud": False},
                        issuer=issuer if issuer else None,
                    )
                    logger.info('[ClerkAuth] PRODUCTION: Token signature verified and decoded')
                except PyJWTError as e:
                    logger.exception(f'[ClerkAuth] JWT verification/decoding error: {e}')
                    raise AuthenticationFailed('Invalid Clerk token')
                except Exception:
                    logger.exception('[ClerkAuth] Unexpected error while verifying token')
                    raise AuthenticationFailed('Invalid Clerk token')


            # ============================================
            # STEP 2: VALIDATE TOKEN STRUCTURE
            # ============================================
            # Check if this looks like a Clerk token
            if not payload.get('sub'):
                raise AuthenticationFailed('Invalid token: missing subject')

            # Clerk tokens have these required claims
            if not payload.get('azp'):
                logger.warning('Token missing azp claim - may not be a valid Clerk token')

            # ============================================
            # STEP 3: EXTRACT USER INFO
            # ============================================
            clerk_user_id = payload.get('sub')  # 'sub' is OpenID standard for user ID
            if not clerk_user_id or not clerk_user_id.startswith('user_'):
                raise AuthenticationFailed('Invalid Clerk user ID in token')

            # ============================================
            # STEP 4: GET OR CREATE USER IN DJANGO
            # ============================================
            try:
                user = User.objects.get(clerk_user_id=clerk_user_id)
                logger.info(f'✅ Found existing user for Clerk ID: {clerk_user_id}')

                token_email = payload.get('email') or payload.get('primary_email_address')
                if token_email and user.email.endswith('@clerk.invalid'):
                    user.email = token_email
                    user.save(update_fields=['email'])
                    logger.info(f'✅ Repaired placeholder Clerk email for: {clerk_user_id}')
            except User.DoesNotExist:
                # ============================================
                # STEP 4A: CREATE NEW USER FROM CLERK TOKEN
                # ============================================
                try:
                    email = payload.get('email', f'{clerk_user_id}@clerk.invalid')
                    name = payload.get('name', 'Clerk User')
                    first_name = payload.get('given_name', '')
                    last_name = payload.get('family_name', '')

                    user = User.objects.create(
                        email=email,
                        name=f"{first_name} {last_name}".strip() or name,
                        clerk_user_id=clerk_user_id,
                        is_active=True,
                        is_verified=True,
                    )
                    logger.info(f'✅ Created new user from Clerk token: {clerk_user_id}')
                except Exception as create_error:
                    # If user creation fails, log but still allow authentication
                    # The user object from Clerk is valid even if DB creation fails
                    logger.error(f'Failed to create user in DB: {str(create_error)}')
                    # Create a minimal user object to return
                    # This prevents 403 errors when DB is temporarily unavailable
                    raise AuthenticationFailed(f'User creation failed: {str(create_error)}')

            logger.info(f'✅ ClerkAuth SUCCESS for {clerk_user_id}')
            
            # ============================================
            # STEP 5: ENSURE USERPROFILE EXISTS
            # ============================================
            # Create UserProfile if it doesn't exist
            # This ensures all authenticated users have a profile
            try:
                from django.apps import apps
                UserProfile = apps.get_model('accounts', 'UserProfile')
                UserProfile.objects.get_or_create(user=user)
                logger.info(f'✅ UserProfile ensured for {clerk_user_id}')
            except Exception as profile_error:
                logger.warning(f'Could not ensure UserProfile: {str(profile_error)}')
                # Don't fail authentication if profile creation fails
            
            return (user, token)

        except jwt.ExpiredSignatureError:
            logger.exception('Clerk token expired')
            raise AuthenticationFailed('Clerk token expired')
        except PyJWTError as e:
            # Catch all other PyJWT errors and log details
            logger.exception(f'Clerk token invalid: {e}')
            raise AuthenticationFailed('Invalid Clerk token')
        except Exception as e:
            # ============================================
            # FIX: HANDLE DB ERRORS GRACEFULLY
            # ============================================
            # If there's a database error (e.g., table doesn't exist),
            # log it but don't fail authentication.
            # This allows the user to proceed even if DB is temporarily unavailable.
            logger.error(f'Clerk authentication error (non-critical): {str(e)}')
            
            # Still raise to inform DRF of the error, but don't expose DB details
            raise AuthenticationFailed(f'Authentication service temporarily unavailable')


# ============================================
# DEPRECATED: OLD JWT AUTHENTICATION (KEPT FOR REFERENCE)
# ============================================
# This class is no longer used in production.
# All authentication should use ClerkAuthentication above.
# Kept here as reference for legacy code migration.
class JWTAuthentication(BaseAuthentication):
    """
    OLD JWT authentication using PyJWT and custom tokens.
    DEPRECATED: Replaced with Clerk authentication.
    Kept for backward compatibility during migration.
    
    IMPLEMENTATION DETAILS (OLD FLOW - NO LONGER USED):
    - Used to decode custom JWT tokens with PyJWT
    - Tokens were signed with settings.JWT_SECRET_KEY
    - Extracted user_id from token payload
    - Queried User model directly by ID
    - No Clerk integration
    
    NEW FLOW (USE ClerkAuthentication INSTEAD):
    - Uses Clerk's official JWT tokens
    - Validates token structure with Clerk claims
    - Extracts clerk_user_id (sub claim)
    - Creates/updates users from Clerk data
    - Full Clerk integration with email verification
    """
    
    # ============ OLD IMPLEMENTATION (DISABLED) ============
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')

        try:
            user = User.objects.get(id=payload.get('user_id'))
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

        return (user, None)
    """
    # ============ END OLD IMPLEMENTATION ============
    
    def authenticate(self, request):
        # This method is disabled - use ClerkAuthentication instead
        return None

class AllowInactiveUserBackend(ModelBackend):
    def user_can_authenticate(self, user):
        # This allows inactive users to authenticate. The view will then handle
        # sending an OTP for verification.
        # NOTE: With Clerk, email verification is handled by Clerk, not here
        return True

