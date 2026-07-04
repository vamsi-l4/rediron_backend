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
from rediron_site.email_utils import send_user_email, EmailServiceError

logger = logging.getLogger(__name__)


def _trial_payload(trial):
    trial.mark_expired()
    return {
        'trial_used': trial.trial_used,
        'status': trial.status,
        'subscription_status': trial.subscription_status,
        'is_active': trial.is_active,
        'trial_start_date': trial.start_date,
        'trial_end_date': trial.end_date,
        'start_date': trial.start_date,
        'end_date': trial.end_date,
        'days_remaining': trial.days_remaining(),
        'is_expired': trial.is_expired(),
        'renewal_preference': trial.renewal_preference,
        'features': trial.features,
    }


def _send_trial_email(user, trial):
    subject = "Your RedIron 15-Day Trial Has Started"
    preference = "auto-renew after trial" if trial.renewal_preference == "auto" else "manual renewal only"
    message = (
        f"Hi {user.name or 'RedIron member'},\n\n"
        f"Your 15-day RedIron trial is active until {trial.end_date.date()}.\n"
        f"Billing preference after trial: {preference}.\n\n"
        "You can view days remaining and renewal options from your profile.\n\n"
        "The RedIron Team"
    )
    html_message = (
        f"<p>Hi {user.name or 'RedIron member'},</p>"
        f"<p>Your <strong>15-day RedIron trial</strong> is active until <strong>{trial.end_date.date()}</strong>.</p>"
        f"<p>Billing preference after trial: <strong>{preference}</strong>.</p>"
        "<p>You can view days remaining and renewal options from your profile.</p>"
    )
    try:
        send_user_email(user, subject, message, html_message=html_message)
    except EmailServiceError:
        logger.exception("Trial start email failed for %s", user.email)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trial_status(request):
    """Get current user's trial subscription status"""
    try:
        trial = TrialSubscription.objects.get(user=request.user)
        
        return Response({
            'status': 'success',
            'trial': _trial_payload(trial),
        })
    except TrialSubscription.DoesNotExist:
        return Response({
            'status': 'success',
            'trial': None,
            'message': 'No trial subscription found'
        }, status=status.HTTP_200_OK)
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
        existing_trial = TrialSubscription.objects.filter(user=request.user).first()
        if existing_trial:
            return Response(
                {
                    'error': 'You have already used your free trial.',
                    'message': 'Free trial already used. Please purchase a membership plan.',
                    'trial': _trial_payload(existing_trial),
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        trial_days = 15
        renewal_preference = request.data.get('renewal_preference')
        if not renewal_preference:
            auto_payment = request.data.get('auto_payment_enabled')
            renewal_preference = 'auto' if auto_payment is True or str(auto_payment).lower() == 'true' else 'manual'

        if renewal_preference not in {'auto', 'manual'}:
            return Response(
                {'error': 'renewal_preference must be auto or manual'},
                status=status.HTTP_400_BAD_REQUEST
            )

        features = request.data.get('features', [
            'articles',
            'workouts',
            'exercises',
            'basic_nutrition',
            'coach_ai'
        ])
        
        start_date = timezone.now()
        end_date = timezone.now() + timedelta(days=trial_days)
        
        trial = TrialSubscription.objects.create(
            user=request.user,
            status='active',
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            trial_used=True,
            renewal_preference=renewal_preference,
            subscription_status='trial_active',
            features=features,
        )

        _send_trial_email(request.user, trial)
        
        logger.info(f"Trial subscription created for user {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': '15-day trial started successfully.',
            'trial': _trial_payload(trial),
        }, status=status.HTTP_201_CREATED)
    
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
