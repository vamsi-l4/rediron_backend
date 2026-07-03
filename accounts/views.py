import hmac
import hashlib
import base64
import json
import logging
from pathlib import Path
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth import get_user_model
from rediron_site.email_utils import send_email_message, send_user_email, send_admin_notification, EmailServiceError
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
import random

from .razorpay_client import client as razorpay_client
from .models import (
    OTP, RefreshToken, UserActivityData, UserProfile, Address,
    FitnessProgress, SavedItem, GymSubscription, PaymentTransaction, TrialSubscription
)
from .serializers import SignupSerializer, UserProfileSerializer, UserActivityDataSerializer
from .utils import generate_otp, generate_access_token, generate_refresh_token_for_user, refresh_access_token_using_refresh_token

User = get_user_model()
logger = logging.getLogger(__name__)

ALLOWED_PROFILE_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_PROFILE_IMAGE_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def _profile_image_url(request, user, profile=None):
    if profile and profile.profile_image_data:
        return profile.profile_image_data
    if user.profile_image:
        return request.build_absolute_uri(user.profile_image.url)
    if profile and profile.profile_image:
        return request.build_absolute_uri(profile.profile_image.url)
    return None


def _profile_image_data_url(uploaded_file):
    uploaded_file.seek(0)
    encoded = base64.b64encode(uploaded_file.read()).decode('ascii')
    uploaded_file.seek(0)
    mime = getattr(uploaded_file, 'content_type', '') or 'image/jpeg'
    return f"data:{mime};base64,{encoded}", mime


def _validate_profile_image(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    content_type = getattr(uploaded_file, 'content_type', '')
    if suffix not in ALLOWED_PROFILE_IMAGE_EXTENSIONS or content_type not in ALLOWED_PROFILE_IMAGE_CONTENT_TYPES:
        return 'Only jpg, jpeg, png, and webp profile images are allowed.'
    return None

def send_otp_email(user_email, otp):
    """Send a password/verification OTP when the legacy flow is used."""
    if not user_email:
        logger.warning("OTP email skipped because user_email is empty")
        return False

    subject = "Your RedIron verification code"
    message = f"Your RedIron verification code is: {otp}. It will expire in 10 minutes."
    html_message = f"<p>Your RedIron verification code is: <strong>{otp}</strong>.</p><p>It will expire in 10 minutes.</p>"
    try:
        return send_email_message(subject, message, [user_email], html_message=html_message)
    except EmailServiceError:
        logger.exception("Failed to send OTP email to %s", user_email)
        return False

def send_trial_confirmation_email(user):
    """Send a confirmation email when a user starts a free trial."""
    if not user.email:
        logger.warning("Trial confirmation email skipped because user_email is empty for user %s", user.id)
        return False

    subject = "Your RedIron 15-Day Free Trial Has Started!"
    message = (
        f"Hi {user.name},\n\n"
        f"Welcome to RedIron! Your 15-day free trial has been successfully activated.\n\n"
        "You now have access to our premium features, including:\n"
        "- Exclusive workout programs\n"
        "- Advanced performance tracking\n"
        "- Personalized nutrition guides\n\n"
        "Start exploring now and unlock your full potential.\n\n"
        "Happy training,\n"
        "The RedIron Team"
    )
    html_message = (
        f"<p>Hi {user.name},</p>"
        f"<p>Welcome to RedIron! Your <strong>15-day free trial</strong> has been successfully activated.</p>"
        f"<p>You now have access to our premium features. Start exploring now and unlock your full potential.</p>"
        f"<p>Happy training,<br/>The RedIron Team</p>"
    )
    try:
        # FIX: Use send_user_email which correctly handles user objects
        # The previous implementation was using a generic email sender. This is now corrected.
        return send_user_email(user, subject, message, html_message=html_message)
    except EmailServiceError:
        logger.exception("Failed to send trial confirmation email to %s", user.email)
        return False


@csrf_exempt
@api_view(['POST'])
def razorpay_webhook(request):
    # Keep webhook minimal; real webhook validation depends on Razorpay docs
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        data = {}
    return JsonResponse({'status': 'ok'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_razorpay_payment(request):
    order_id = request.data.get('order_id') or request.data.get('razorpay_order_id')
    payment_id = request.data.get('payment_id') or request.data.get('razorpay_payment_id')
    signature = request.data.get('signature') or request.data.get('razorpay_signature')

    if not (order_id and payment_id and signature):
        return Response({'error': 'order_id, payment_id, and signature are required'}, status=400)

    try:
        generated_signature = hmac.new(
            key=bytes(settings.RAZORPAY_KEY_SECRET or '', 'utf-8'),
            msg=bytes(f"{order_id}|{payment_id}", 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        if generated_signature != signature:
            return Response({'error': 'Invalid payment signature'}, status=400)

        PaymentTransaction.objects.create(
            user=request.user,
            payment_id=payment_id,
            amount=float(request.data.get('amount', 0)),
            currency=request.data.get('currency', 'INR'),
            status='completed',
            method='razorpay',
            description=f'Razorpay payment verified for order {order_id}',
            metadata={
                'razorpay_order_id': order_id,
                'razorpay_signature': signature,
            }
        )

        return Response({'success': True, 'message': 'Payment verified successfully'})
    except Exception as e:
        logger.exception('Razorpay verification failed')
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    user = request.user
    amount = request.data.get('amount')
    currency = request.data.get('currency', 'INR')
    receipt = request.data.get('receipt', f'order_rcptid_{user.id}')

    if not amount:
        return Response({'error': 'Amount is required'}, status=400)

    try:
        order_data = {
            'amount': int(float(amount) * 100),
            'currency': currency,
            'receipt': receipt,
            'payment_capture': 1
        }
        order = razorpay_client.order.create(data=order_data)
        return Response({'order_id': order['id'], 'amount': order['amount'], 'currency': order['currency']})
    except Exception as e:
        logger.exception("Razorpay create order error")
        return Response({'error': str(e)}, status=500)

"""
============================================
AUTHENTICATION VIEWS (COMMENTED OUT - Clerk handles auth)
============================================
The following views are deprecated and replaced by Clerk's authentication system.
They are kept as comments for interview discussion and backward compatibility during migration.

OLD FLOW:
- signup() / SignupView: Generate OTP and send to email
- custom_login(): Verify password and send OTP
- VerifyOTPView: Verify OTP code for 2FA
- refresh_token(): Refresh JWT tokens

NEW FLOW (CLERK):
- Frontend: Login/Signup forms trigger Clerk authentication
- Clerk handles: Password validation, email verification, OTP sending
- Backend: ClerkAuthentication middleware verifies Clerk JWT tokens
- Backend API endpoints: Protected by @permission_classes([IsAuthenticated])
- Clerk tokens provide clerk_user_id for user identification
"""

# ============================================
# OLD SIGNUP VIEW (COMMENTED OUT)
# ============================================
"""
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        UserActivityData.objects.create(user=user)
        return Response({'message': 'User registered successfully'}, status=201)
    return Response(serializer.errors, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class SignupView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        logger.info(f"Signup request data: {request.data}")
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                name=serializer.validated_data['name'],
                is_active=False,
                is_verified=False
            )
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_expiry = timezone.now() + timedelta(minutes=10)
            user.save()
            try:
                send_otp_email(user.email, otp)
            except Exception as e:
                logger.error(f"Failed to send OTP email: {e}")
            try:
                UserActivityData.objects.create(user=user)
            except Exception as e:
                logger.error(f"Failed to create UserActivityData: {e}")
            return Response({'message': 'OTP sent to email'}, status=status.HTTP_201_CREATED)
        logger.warning(f"Signup validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
"""

# NEW: Signup is handled by Clerk frontend + ClerkAuthentication middleware

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """
    DEPRECATED: Signup is now handled by Clerk.
    This endpoint is kept for reference only.
    Frontend should use Clerk's useSignUp hook instead.
    """
    logger.warning("Old signup endpoint called - use Clerk instead")
    return Response({
        'error': 'Signup is now handled by Clerk. Use Clerk authentication instead.',
        'message': 'This endpoint is deprecated.'
    }, status=410)  # 410 Gone


@method_decorator(csrf_exempt, name='dispatch')
class SignupView(APIView):
    """
    DEPRECATED: Signup view - replaced with Clerk authentication.
    """
    parser_classes = [JSONParser]

    def post(self, request):
        logger.warning("Old SignupView endpoint called - use Clerk instead")
        return Response({
            'error': 'Signup is now handled by Clerk. Use Clerk authentication instead.',
            'message': 'This endpoint is deprecated.'
        }, status=410)  # 410 Gone


# ============================================
# OLD LOGIN VIEW (COMMENTED OUT)
# ============================================
"""
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login(request):
    email = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    if not email or not password:
        return Response({'error': 'Email/username and password required'}, status=400)

    from django.contrib.auth import authenticate
    user = authenticate(username=email, password=password)

    if user is not None:
        if user.is_active:
            access_token = generate_access_token(user)
            refresh_token = generate_refresh_token_for_user(user)
            return Response({
                'access': access_token,
                'refresh': refresh_token,
                'user': {'id': user.id, 'email': user.email, 'name': user.name}
            }, status=200)
        else:
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_expiry = timezone.now() + timedelta(minutes=10)
            user.save()
            try:
                send_otp_email(user.email, otp)
                return Response({'message': 'Account not verified. OTP sent to your email for verification.'}, status=200)
            except Exception as e:
                logger.error(f"Failed to send OTP email: {e}")
                return Response({'error': 'Failed to send OTP. Please try again.'}, status=500)
    else:
        try:
            existing_user = User.objects.get(email__iexact=email)
            logger.warning(f"User exists but auth failed for email: {email}, is_active: {existing_user.is_active}")
        except User.DoesNotExist:
            logger.warning(f"User does not exist for email: {email}")
        return Response({'error': 'Invalid credentials'}, status=401)
"""

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login(request):
    """
    DEPRECATED: Login is now handled by Clerk.
    This endpoint is kept for reference only.
    Frontend should use Clerk's useSignIn hook instead.
    """
    logger.warning("Old custom_login endpoint called - use Clerk instead")
    return Response({
        'error': 'Login is now handled by Clerk. Use Clerk authentication instead.',
        'message': 'This endpoint is deprecated.'
    }, status=410)  # 410 Gone


@method_decorator(csrf_exempt, name='dispatch')
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    DEPRECATED: Token obtain view - replaced with Clerk authentication.
    """
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        logger.warning("Old CustomTokenObtainPairView endpoint called - use Clerk instead")
        return Response({
            'error': 'Authentication is now handled by Clerk.',
            'message': 'This endpoint is deprecated.'
        }, status=410)  # 410 Gone



@csrf_exempt
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def test_view(request):
    return Response(
        {
            "message": "API working",
            "method": request.method,
            "data": request.data,
        },
        status=status.HTTP_200_OK
    )


# ============================================
# OLD OTP VERIFICATION VIEW (COMMENTED OUT)
# ============================================
"""
@method_decorator(csrf_exempt, name='dispatch')
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp')

        if not email or not otp_code:
            return Response({'error': 'Email and OTP required'}, status=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        otp = OTP.objects.filter(user=user, code=otp_code, is_verified=False).last()
        if not otp:
            return Response({'error': 'Invalid OTP'}, status=400)

        if timezone.now() - otp.created_at > timedelta(minutes=5):
            return Response({'error': 'OTP expired'}, status=400)

        otp.is_verified = True
        otp.save()

        # Activate the user after OTP verification
        user.is_active = True
        user.save()

        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token_for_user(user)

        try:
            send_mail(
                'Login Successful - RedIron Gym',
                f'Hi {user.name},\\nYou successfully logged in!',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )
        except Exception:
            logger.exception("Auto-login email failed (ignored)")

        return Response({
            'access': access_token,
            'refresh': refresh_token,
            'user': {'id': user.id, 'email': user.email, 'name': user.name}
        }, status=200)
"""

@method_decorator(csrf_exempt, name='dispatch')
class VerifyOTPView(APIView):
    """
    DEPRECATED: OTP verification is now handled by Clerk.
    This endpoint is kept for reference only.
    Clerk handles email verification automatically.
    """
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        logger.warning("Old VerifyOTPView endpoint called - Clerk handles verification")
        return Response({
            'error': 'Email verification is now handled by Clerk.',
            'message': 'This endpoint is deprecated.'
        }, status=410)  # 410 Gone




# ============================================
# OLD TOKEN REFRESH & LOGOUT (COMMENTED OUT)
# ============================================
"""
@api_view(['POST'])
def refresh_token(request):
    # DEPRECATED: Clerk manages sessions automatically
    refresh_from_cookie = request.COOKIES.get('refresh')
    refresh_from_body = request.data.get('refresh')
    refresh_token_str = refresh_from_cookie or refresh_from_body
    if not refresh_token_str:
        return Response({'error': 'Refresh token not provided'}, status=400)

    new_access, error = refresh_access_token_using_refresh_token(refresh_token_str)
    if error:
        return Response({'error': error}, status=400)

    return Response({'access': new_access})

@api_view(['POST'])
def logout(request):
    # DEPRECATED: Clerk manages sessions automatically
    refresh = request.COOKIES.get('refresh')
    if refresh:
        RefreshToken.objects.filter(token=refresh).delete()
    resp = Response({'message': 'Logged out'}, status=200)
    resp.delete_cookie('refresh')
    return resp
"""

@api_view(['POST'])
def refresh_token(request):
    """
    DEPRECATED: Token refresh is now handled by Clerk.
    Clerk manages session tokens automatically.
    """
    logger.warning("Old refresh_token endpoint called - Clerk handles sessions")
    return Response({
        'error': 'Session management is now handled by Clerk.',
        'message': 'This endpoint is deprecated.'
    }, status=410)  # 410 Gone


@api_view(['POST'])
def logout(request):
    """
    DEPRECATED: Logout is now handled by Clerk.
    Frontend should call Clerk's signOut() hook instead.
    """
    logger.warning("Old logout endpoint called - use Clerk's signOut hook")
    return Response({
        'message': 'Logout is handled by Clerk on the frontend.',
        'note': 'Use Clerk\'s signOut() hook instead.'
    }, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    FIX: Always return 200 for authenticated users.
    This endpoint now works regardless of profile existence.
    """
    user = request.user
    
    try:
        # ============================================
        # ENSURE USER ACTIVITY DATA EXISTS
        # ============================================
        # Auto-create activity data if missing (should happen here, not in profile creation)
        UserActivityData.objects.get_or_create(user=user)
        
        return Response({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'clerk_user_id': user.clerk_user_id,
            'username': getattr(user, 'username', user.name),
            'profile_image': request.build_absolute_uri(user.profile_image.url) if user.profile_image else None,
            'is_verified': user.is_verified,
            'is_active': user.is_active,
        }, status=200)
    except Exception as e:
        logger.error(f'Error fetching profile for {user.email}: {str(e)}')
        # Even if there's an error, return minimal profile data (200, not 403)
        return Response({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'clerk_user_id': user.clerk_user_id,
            'message': 'Profile loaded with minimal data due to temporary error'
        }, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_profile(request):
    """
    FIX: Create user profile/activity data if missing.
    Always returns 201 for authenticated users (never 403).
    Idempotent: Calling multiple times is safe.
    """
    user = request.user
    
    try:
        # ============================================
        # ENSURE USER ACTIVITY DATA EXISTS
        # ============================================
        # Create activity data if it doesn't exist (safe to call multiple times)
        activity_data, created = UserActivityData.objects.get_or_create(user=user)
        
        # Return 201 if newly created, 200 if already existed
        status_code = 201 if created else 200
        
        return Response({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'clerk_user_id': user.clerk_user_id,
            'username': getattr(user, 'username', user.name),
            'profile_image': request.build_absolute_uri(user.profile_image.url) if user.profile_image else None,
            'is_verified': user.is_verified,
            'is_active': user.is_active,
            'activity_data': activity_data.data if activity_data else {},
            'created': created,
        }, status=status_code)
    except Exception as e:
        logger.error(f'Error creating profile for {user.email}: {str(e)}')
        # Still return 201 even on error (user is authenticated)
        return Response({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'clerk_user_id': user.clerk_user_id,
            'error': 'Profile created with errors',
            'details': str(e),
        }, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_user_after_signup(request):
    """
    FIX FOR CROSS-BROWSER LOGIN:
    
    Called by frontend AFTER signup email verification and setActive().
    Ensures user is synced to backend database immediately after signup,
    not waiting for first login.
    
    This prevents login failures on different browsers because:
    1. User data is already in database
    2. Next login just validates the Clerk token
    3. No circular dependency on profile endpoint
    
    Request should include Clerk token in Authorization header.
    ClerkAuthentication will extract user info and create user if needed.
    """
    user = request.user
    
    try:
        # Get or create the main user profile and activity data
        UserProfile.objects.get_or_create(user=user)
        activity_data, created = UserActivityData.objects.get_or_create(user=user)

        # Ensure shop-related models are also created
        try:
            from rediron_shop.models import Cart, Wishlist as ShopWishlist
            Cart.objects.get_or_create(user=user)
            ShopWishlist.objects.get_or_create(user=user)
        except Exception as shop_error:
            # This might fail if the shop app is not installed. We can log a warning
            # but we shouldn't fail the entire request.
            logger.warning(
                f'Could not ensure shop models for {user.clerk_user_id}: {str(shop_error)}'
            )


        logger.info(f'✅ User synced and profile initialized after signup: {user.clerk_user_id} ({user.email})')
        
        return Response({
            'success': True,
            'message': 'User synced successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'clerk_user_id': user.clerk_user_id,
                'is_verified': user.is_verified,
                'is_active': user.is_active,
            }
        }, status=200)
    except Exception as e:
        logger.error(f'Error syncing user after signup: {str(e)}')
        return Response({
            'success': False,
            'error': 'Failed to sync user',
            'details': str(e)
        }, status=500)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    user = request.user
    serializer = UserProfileSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        data = serializer.data
        if user.profile_image:
            data['profile_image'] = request.build_absolute_uri(user.profile_image.url)
        return Response(data)
    return Response(serializer.errors, status=400)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_activity_data(request):
    user = request.user
    activity_data, created = UserActivityData.objects.get_or_create(user=user)
    if request.method == 'GET':
        serializer = UserActivityDataSerializer(activity_data)
        return Response(serializer.data)
    else:
        serializer = UserActivityDataSerializer(activity_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_payment_option(request):
    user = request.user
    auto_payment = request.data.get('auto_payment')
    if auto_payment is None:
        return Response({'error': 'auto_payment is required'}, status=status.HTTP_400_BAD_REQUEST)
    # Convert to boolean if passed as string
    if isinstance(auto_payment, str):
        auto_payment = auto_payment.lower() in ('true', '1', 'yes')
    user.auto_payment = bool(auto_payment)
    user.save()
    return Response({'message': 'Payment option updated', 'auto_payment': user.auto_payment})

@api_view(['GET'])
@permission_classes([AllowAny])
def welcome(request):
    logger.info(f"Request received: {request.method} {request.path}")
    return Response({'message': 'Welcome to the RedIron Gym API!'})

# ============================================
# PRODUCTION-GRADE PROFILE ENDPOINTS (NEW)
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_extended_profile(request):
    """
    Get comprehensive user profile with all related data.
    Returns user info, profile, addresses, subscription, fitness progress, etc.
    """
    user = request.user
    
    try:
        # Ensure user profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Update last login
        from .models import UserProfile as UP
        UP.objects.filter(user=user).update(last_login=timezone.now())
        
        from .serializers import ExtendedUserSerializer
        serializer = ExtendedUserSerializer(user)
        return Response(serializer.data, status=200)
    except Exception as e:
        logger.error(f'Error fetching extended profile for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to load profile',
            'details': str(e)
        }, status=500)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def manage_profile(request):
    """
    Get or update user profile information.
    """
    user = request.user
    
    try:
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if request.method == 'GET':
            from .serializers import UserProfileSerializer
            serializer = UserProfileSerializer(profile)
            data = serializer.data
            data['name'] = user.name
            data['email'] = user.email
            data['phone'] = profile.phone_number
            data['profile_image'] = _profile_image_url(request, user, profile)
            return Response(data, status=200)
        
        elif request.method == 'PATCH':
            from .serializers import UserProfileSerializer
            profile_data = request.data.copy()
            remove_profile_image = str(profile_data.get('remove_profile_image', '')).lower() in {'1', 'true', 'yes'}
            if 'phone' in profile_data and 'phone_number' not in profile_data:
                profile_data['phone_number'] = profile_data.get('phone', '')
            profile_data.pop('name', None)
            profile_data.pop('email', None)
            profile_data.pop('remove_profile_image', None)
            if 'profile_image' in request.FILES:
                profile_data.pop('profile_image', None)
            if remove_profile_image:
                profile_data.pop('profile_image', None)
            serializer = UserProfileSerializer(profile, data=profile_data, partial=True)
            if serializer.is_valid():
                profile = serializer.save()
                
                user_updated = False
                if 'name' in request.data:
                    user.name = request.data.get('name', '').strip() or user.name
                    user_updated = True
                    
                if 'profile_image' in request.FILES:
                    uploaded_image = request.FILES['profile_image']
                    validation_error = _validate_profile_image(uploaded_image)
                    if validation_error:
                        return Response({'profile_image': [validation_error]}, status=400)

                    if user.profile_image and user.profile_image.name:
                        try:
                            user.profile_image.delete(save=False)
                        except Exception:
                            logger.exception("Failed to delete previous user profile image")
                    if profile.profile_image and profile.profile_image.name:
                        try:
                            profile.profile_image.delete(save=False)
                        except Exception:
                            logger.exception("Failed to delete previous profile image")

                    image_data, image_mime = _profile_image_data_url(uploaded_image)
                    profile.profile_image = uploaded_image
                    profile.profile_image_data = image_data
                    profile.profile_image_mime = image_mime
                    user_updated = True
                elif remove_profile_image:
                    if user.profile_image and user.profile_image.name:
                        user.profile_image.delete(save=False)
                    if profile.profile_image and profile.profile_image.name:
                        profile.profile_image.delete(save=False)
                    user.profile_image = None
                    profile.profile_image = None
                    profile.profile_image_data = ''
                    profile.profile_image_mime = ''
                    user_updated = True
                    
                profile.save()

                if user_updated:
                    if profile.profile_image and profile.profile_image.name:
                        user.profile_image = profile.profile_image.name
                    user.save()
                    
                data = serializer.data
                data['name'] = user.name
                data['email'] = user.email
                data['phone'] = profile.phone_number
                data['profile_image'] = _profile_image_url(request, user, profile)
                return Response(data, status=200)
            return Response(serializer.errors, status=400)
    
    except Exception as e:
        logger.error(f'Error managing profile for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to process profile',
            'details': str(e)
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_addresses(request):
    """
    List all addresses or create a new address.
    """
    user = request.user
    
    try:
        if request.method == 'GET':
            addresses = Address.objects.filter(user=user)
            from .serializers import AddressSerializer
            serializer = AddressSerializer(addresses, many=True)
            return Response(serializer.data, status=200)
        
        elif request.method == 'POST':
            from .serializers import AddressSerializer
            serializer = AddressSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(user=user)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
    
    except Exception as e:
        logger.error(f'Error managing addresses for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to process address',
            'details': str(e)
        }, status=500)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_address_detail(request, address_id):
    """
    Get, update, or delete a specific address.
    """
    user = request.user
    
    try:
        address = Address.objects.get(id=address_id, user=user)
    except Address.DoesNotExist:
        return Response({'error': 'Address not found'}, status=404)
    
    try:
        if request.method == 'GET':
            from .serializers import AddressSerializer
            serializer = AddressSerializer(address)
            return Response(serializer.data, status=200)
        
        elif request.method == 'PATCH':
            from .serializers import AddressSerializer
            serializer = AddressSerializer(address, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=200)
            return Response(serializer.errors, status=400)
        
        elif request.method == 'DELETE':
            address.delete()
            return Response({'message': 'Address deleted successfully'}, status=200)
    
    except Exception as e:
        logger.error(f'Error managing address {address_id} for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to process address',
            'details': str(e)
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_trial(request):
    """
    Starts a 15-day free trial for the authenticated user.
    """
    user = request.user
    
    # Check if the user already has an active subscription or trial
    if GymSubscription.objects.filter(user=user, is_active=True).exists():
        return Response({'error': 'You already have an active subscription or trial.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Create a 15-day trial subscription
        start_date = timezone.now()
        end_date = start_date + timedelta(days=15)
        
        subscription = GymSubscription.objects.create(
            user=user,
            plan='trial',
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            auto_renew=request.data.get('auto_payment_enabled', False)
        )
        
        # Send confirmation email
        send_trial_confirmation_email(user)
        
        return Response({'success': True, 'message': '15-day trial started successfully.'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error starting trial for user {user.email}: {str(e)}")
        return Response({'error': 'Failed to start trial. Please try again later.'}, status=status.HTTP_500_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fitness_progress(request):
    """
    Get user's fitness progress history.
    """
    user = request.user
    
    try:
        progress = FitnessProgress.objects.filter(user=user)
        from .serializers import FitnessProgressSerializer
        serializer = FitnessProgressSerializer(progress, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        logger.error(f'Error fetching fitness progress for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to load fitness progress',
            'details': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_fitness_progress(request):
    """
    Add a new fitness progress entry.
    """
    user = request.user
    
    try:
        from .serializers import FitnessProgressSerializer
        serializer = FitnessProgressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    except Exception as e:
        logger.error(f'Error adding fitness progress for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to add fitness progress',
            'details': str(e)
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_saved_items(request):
    """
    Get all saved items or save a new item.
    """
    user = request.user
    
    try:
        if request.method == 'GET':
            item_type = request.query_params.get('type')
            items = SavedItem.objects.filter(user=user)
            if item_type:
                items = items.filter(item_type=item_type)
            items = items.order_by('-id')
            from .serializers import SavedItemSerializer
            serializer = SavedItemSerializer(items, many=True)
            return Response(serializer.data, status=200)
        
        elif request.method == 'POST':
            from .serializers import SavedItemSerializer
            serializer = SavedItemSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=user)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
    
    except Exception as e:
        logger.error(f'Error managing saved items for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to process saved item',
            'details': str(e)
        }, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_saved_item(request, item_id):
    """
    Remove a saved item.
    """
    user = request.user
    
    try:
        saved_item = SavedItem.objects.get(id=item_id, user=user)
        saved_item.delete()
        return Response({'message': 'Item removed from saved'}, status=200)
    except SavedItem.DoesNotExist:
        return Response({'error': 'Saved item not found'}, status=404)
    except Exception as e:
        logger.error(f'Error removing saved item for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to remove saved item',
            'details': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """
    Get user's payment transaction history.
    """
    user = request.user
    
    try:
        transactions = PaymentTransaction.objects.filter(user=user).order_by('-created_at')
        from .serializers import PaymentTransactionSerializer
        serializer = PaymentTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        logger.error(f'Error fetching payment history for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to load payment history',
            'details': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_gym_subscription(request):
    """
    Get current gym subscription status.
    """
    user = request.user
    
    try:
        trial = TrialSubscription.objects.filter(user=user).first()
        if trial:
            trial.mark_expired()
            return Response({
                'id': trial.id,
                'plan': 'trial',
                'status': 'Trial Active' if trial.status == 'active' else 'Trial Expired',
                'subscription_status': trial.subscription_status,
                'price': '0.00',
                'start_date': trial.start_date,
                'end_date': trial.end_date,
                'trial_start_date': trial.start_date,
                'trial_end_date': trial.end_date,
                'trial_used': trial.trial_used,
                'renewal_preference': trial.renewal_preference,
                'auto_renewal': trial.renewal_preference == 'auto',
                'payment_method': 'trial',
                'is_active': trial.status == 'active' and not trial.is_expired(),
                'days_remaining': trial.days_remaining(),
            }, status=200)

        subscription = GymSubscription.objects.filter(user=user).first()
        if not subscription:
            return Response({
                'message': 'No active subscription',
                'subscription': None
            }, status=200)
        
        from .serializers import GymSubscriptionSerializer
        serializer = GymSubscriptionSerializer(subscription)
        return Response(serializer.data, status=200)
    except Exception as e:
        logger.error(f'Error fetching gym subscription for {user.email}: {str(e)}')
        return Response({
            'error': 'Failed to load subscription',
            'details': str(e)
        }, status=500)


# ============================================
# PRODUCTION-GRADE: PROFILE INITIALIZATION
# ============================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_user_profile(request):
    """
    Initialize or ensure UserProfile exists for authenticated Clerk user.
    Called by frontend after successful Clerk authentication.
    
    Returns: UserProfile data with completion status and recommended next steps.
    
    REQUIRED: 
    - User must be authenticated (Clerk JWT in Authorization header)
    
    OPTIONAL REQUEST DATA:
    - None for this endpoint - profile is auto-created or retrieved
    
    RESPONSE:
    {
        "success": true,
        "profile": {
            "id": 1,
            "clerk_user_id": "user_xxx",
            "email": "user@example.com",
            "is_complete": false,
            "completion_percentage": 25,
            "created_at": "2024-02-13T10:00:00Z"
        },
        "message": "Profile initialized successfully"
    }
    """
    user = request.user
    
    try:
        # ============================================
        # STEP 1: GET OR CREATE PROFILE
        # ============================================
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'is_email_verified': True,  # Clerk already verified email
                'receive_notifications': True,
                'receive_emails': True,
            }
        )
        
        if created:
            logger.info(f'✅ Created new profile for {user.clerk_user_id}')
            status_code = 201
            message = "Profile created successfully"
        else:
            logger.info(f'✅ Retrieved existing profile for {user.clerk_user_id}')
            status_code = 200
            message = "Profile already exists"
        
        # ============================================
        # STEP 2: UPDATE LAST LOGIN
        # ============================================
        profile.last_login = timezone.now()
        profile.save(update_fields=['last_login'])
        
        # ============================================
        # STEP 3: ENSURE RELATED DATA MODELS EXIST
        # ============================================
        # Create Cart if doesn't exist (for shop functionality)
        try:
            from rediron_shop.models import Cart, Wishlist as ShopWishlist
            Cart.objects.get_or_create(user=user)
            ShopWishlist.objects.get_or_create(user=user)
            logger.info(f'✅ Shop models ensured for {user.clerk_user_id}')
        except Exception as shop_error:
            logger.warning(f'Could not ensure shop models: {str(shop_error)}')
            # Don't fail if shop models can't be created
        
        # ============================================
        # STEP 4: RETURN RESPONSE
        # ============================================
        from .serializers import UserProfileSerializer
        serializer = UserProfileSerializer(profile)
        
        response_data = {
            'success': True,
            'profile': serializer.data,
            'profile_complete': profile.is_complete,
            'completion_percentage': profile.complete_percentage(),
            'message': message,
        }
        
        return Response(response_data, status=status_code)
        
    except Exception as e:
        logger.error(f'Failed to initialize profile for {user.email}: {str(e)}')
        return Response({
            'success': False,
            'error': 'Failed to initialize profile',
            'details': str(e) if settings.DEBUG else 'An error occurred'
        }, status=500)
