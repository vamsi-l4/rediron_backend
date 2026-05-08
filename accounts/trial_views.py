"""
Trial Subscription API Views
Handles free trial management, upgrades, and payment verification

TODO: Payment Integration Notes
- Razorpay payment verification currently disabled
- When integrating real payments:
  1. Uncomment payment verification in upgrade_trial()
  2. Implement webhook handling for async payment confirmation
  3. Add retry logic for failed payment transactions
  4. Integrate with Clerk user metadata to track trial status
  5. Add email notifications for trial expiration
"""

from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import TrialSubscription, PaymentTransaction
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trial_status(request):
    """Get current user's trial subscription status"""
    try:
        trial = TrialSubscription.objects.get(user=request.user)
        trial.mark_expired()  # Update status if expired
        
        return Response({
            'status': 'success',
            'trial': {
                'status': trial.status,
                'is_active': trial.is_active,
                'start_date': trial.start_date,
                'end_date': trial.end_date,
                'days_remaining': trial.days_remaining(),
                'is_expired': trial.is_expired(),
                'features': trial.features,
            }
        })
    except TrialSubscription.DoesNotExist:
        return Response({
            'status': 'success',
            'trial': None,
            'message': 'No trial subscription found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting trial status: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_trial(request):
    """Start a new free trial for the user"""
    try:
        # Check if trial already exists
        existing_trial = TrialSubscription.objects.filter(user=request.user).first()
        if existing_trial and existing_trial.status == 'active':
            return Response(
                {'error': 'User already has an active trial'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Default: 7-day trial
        trial_days = request.data.get('days', 7)
        features = request.data.get('features', [
            'articles',
            'workouts',
            'exercises',
            'basic_nutrition'
        ])
        
        end_date = timezone.now() + timedelta(days=trial_days)
        
        # Create or update trial
        trial, created = TrialSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'status': 'active',
                'is_active': True,
                'end_date': end_date,
                'features': features,
            }
        )
        
        action = "created" if created else "updated"
        logger.info(f"Trial subscription {action} for user {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': f'Trial subscription {action}',
            'trial': {
                'days': trial_days,
                'start_date': trial.start_date,
                'end_date': trial.end_date,
                'features': trial.features,
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error starting trial: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_trial(request):
    """Upgrade from trial to premium after successful payment"""
    try:
        payment_id = request.data.get('payment_id')
        plan = request.data.get('plan', 'premium')
        amount = request.data.get('amount')
        
        if not payment_id:
            return Response(
                {'error': 'payment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create trial
        trial, _ = TrialSubscription.objects.get_or_create(user=request.user)
        
        # Update trial status
        trial.status = 'upgraded'
        trial.is_active = False
        trial.save()
        
        # Create payment transaction record
        PaymentTransaction.objects.create(
            user=request.user,
            payment_id=payment_id,
            amount=amount or 499,
            currency='INR',
            status='completed',
            method='razorpay',
            plan=plan,
            description=f'Upgrade from trial to {plan}'
        )
        
        logger.info(f"User {request.user.email} upgraded from trial to {plan}")
        
        return Response({
            'status': 'success',
            'message': f'Successfully upgraded to {plan} plan',
            'plan': plan,
        })
    
    except Exception as e:
        logger.error(f"Error upgrading trial: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_transaction(request):
    """Create a payment transaction record"""
    try:
        payment_id = request.data.get('payment_id')
        amount = request.data.get('amount')
        method = request.data.get('method', 'razorpay')
        plan = request.data.get('plan', 'premium')
        
        if not payment_id or not amount:
            return Response(
                {'error': 'payment_id and amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            payment_id=payment_id,
            amount=amount,
            currency='INR',
            status='completed',
            method=method,
            plan=plan,
        )
        
        logger.info(f"Payment transaction created: {payment_id}")
        
        return Response({
            'status': 'success',
            'transaction_id': transaction.id,
            'payment_id': transaction.payment_id,
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Error creating payment transaction: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """Get user's payment history"""
    try:
        transactions = PaymentTransaction.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        data = [{
            'id': t.id,
            'payment_id': t.payment_id,
            'amount': str(t.amount),
            'currency': t.currency,
            'status': t.status,
            'method': t.method,
            'plan': t.plan,
            'created_at': t.created_at,
        } for t in transactions]
        
        return Response({
            'status': 'success',
            'transactions': data,
            'total': len(data),
        })
    
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
