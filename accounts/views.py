from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework import status
from .serializers import SignupSerializer
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import jwt

User = get_user_model()

@api_view(['POST'])
def custom_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Username and password required'}, status=400)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=401)

    if not check_password(password, user.password):
        return Response({'error': 'Invalid credentials'}, status=401)

    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': timezone.now() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS),
        'iat': timezone.now(),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return Response({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username
        }
    })
@api_view(['POST'])
def signup(request):
    serializer=SignupSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message":"user created sucessfully."},status=201)
    return Response(serializer.errors,status=400)