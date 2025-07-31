from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from .models import OTP
from .serializers import SignupSerializer
from .utils import generate_token, refresh_user_token, generate_otp

User = get_user_model()

@api_view(['POST'])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User created successfully."}, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
def custom_login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=401)

    if not user.check_password(password):
        return Response({'error': 'Invalid credentials'}, status=401)

    # ✅ Generate and send OTP
    otp_code = generate_otp()
    OTP.objects.create(user=user, code=otp_code)
    send_mail(
        'Your RedIron Gym Login OTP',
        f'Your OTP code is: {otp_code}',
        'rediron@example.com',
        [email],
        fail_silently=False,
    )

    token = generate_token(user)

    return Response({
        'token': token,
        'email': email,
        'message': 'OTP sent to your email'
    })


@api_view(['POST'])
def verify_otp(request):
    email = request.data.get("email")
    otp_code = request.data.get("otp")

    try:
        user = User.objects.get(email=email)
        otp = OTP.objects.filter(user=user, code=otp_code, is_verified=False).last()

        if not otp:
            return Response({"error": "Invalid OTP"}, status=400)
        
        

        if timezone.now() - otp.created_at > timedelta(minutes=5):
            return Response({'error': 'OTP expired'}, status=400)

        otp.is_verified = True
        otp.save()

        send_mail(
            'Login Verified - RedIron Gym',
            'You successfully logged in at RedIron Gym!',
            'rediron@example.com',
            [email],
            fail_silently=False,
        )

        return Response({'success': 'OTP verified'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['POST'])
def refresh_token(request):
    token = request.data.get('refresh')
    if not token:
        return Response({'error': 'Token not provided'}, status=400)

    new_token, error = refresh_user_token(token)

    if error:
        return Response({'error': error}, status=400)

    return Response({'token': new_token})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'name': user.name,
    })
