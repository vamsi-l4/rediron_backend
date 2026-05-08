"""
RedIron Performance Lab - API Views

Production-grade API endpoints for fitness performance tracking.
- Clerk JWT authentication
- Optimized queryset queries
- Comprehensive error handling
- Structured JSON responses
"""

import os
from datetime import timedelta
from django.utils import timezone
from django.db.models import Prefetch, Sum, F
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.http import require_http_methods

from .models import (
    WorkoutSession, ExerciseLog, BodyMetrics,
    NutritionLog, UserGoal
)
from .serializers import (
    WorkoutSessionSerializer, ExerciseLogSerializer,
    BodyMetricsSerializer, NutritionLogSerializer,
    UserGoalSerializer, PerformanceDashboardSerializer,
    RecommendationSerializer
)
from .analytics import PerformanceAnalytics


# ============================================
# AUTHENTICATION & MIDDLEWARE
# ============================================

def get_clerk_user_id(request):
    """
    Extract Clerk user ID from JWT claims in request.
    Uses Clerk's subject (sub) claim which is the user ID.
    """
    # Clerk stores user ID in request.user.clerk_user_id (set by middleware)
    if hasattr(request, 'user') and hasattr(request.user, 'clerk_user_id'):
        return request.user.clerk_user_id

    # Fallback: Extract from request headers (if custom middleware not present)
    from rest_framework_simplejwt.authentication import JWTAuthentication
    jwt_auth = JWTAuthentication()
    try:
        validated_token = jwt_auth.get_validated_token(
            request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
        )
        return validated_token.get('sub')  # Clerk user ID is in 'sub' claim
    except:
        return None


# ============================================
# 1. LOG WORKOUT / CREATE SESSION
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_http_methods(["POST"])
def log_workout(request):
    """
    POST /performance/log-workout/
    
    Creates a new workout session with exercise logs.
    
    Request body:
    {
        "date": "2024-02-22",
        "duration": 60,
        "exercises": [
            {
                "exercise_name": "Bench Press",
                "sets": 4,
                "reps": 8,
                "weight": 100.0
            }
        ]
    }
    
    Response: 201 Created
    {
        "id": 1,
        "date": "2024-02-22",
        "duration": 60,
        "total_volume": 3200.0,
        "exercises": [...]
    }
    """
    try:
        clerk_user_id = get_clerk_user_id(request)
        if not clerk_user_id:
            return Response(
                {'error': 'Clerk user ID not found'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        exercises_data = data.get('exercises', [])

        # Create workout session
        session = WorkoutSession.objects.create(
            clerk_user_id=clerk_user_id,
            date=data.get('date', timezone.now().date()),
            duration=data.get('duration', 0)
        )

        # Create exercise logs and calculate volume
        total_volume = 0
        created_exercises = []

        for ex_data in exercises_data:
            # Calculate 1RM
            one_rm = PerformanceAnalytics.calculate_1rm(
                weight=float(ex_data.get('weight', 0)),
                reps=int(ex_data.get('reps', 1))
            )

            # Calculate volume for this exercise
            volume = (
                float(ex_data.get('weight', 0)) *
                int(ex_data.get('reps', 0)) *
                int(ex_data.get('sets', 0))
            )
            total_volume += volume

            exercise_log = ExerciseLog.objects.create(
                session=session,
                exercise_name=ex_data.get('exercise_name', 'Unknown'),
                sets=int(ex_data.get('sets', 0)),
                reps=int(ex_data.get('reps', 0)),
                weight=float(ex_data.get('weight', 0)),
                calculated_1rm=one_rm
            )
            created_exercises.append(exercise_log)

        # Update session with total volume
        session.total_volume = total_volume
        session.save()

        # Serialize response
        serializer = WorkoutSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except (ValueError, KeyError) as e:
        return Response(
            {'error': f'Invalid data: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 2. LOG NUTRITION / CREATE LOG
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_http_methods(["POST"])
def log_nutrition(request):
    """
    POST /performance/log-nutrition/
    
    Logs daily nutrition intake.
    
    Request body:
    {
        "date": "2024-02-22",
        "calories": 2000,
        "protein": 165,
        "carbs": 200,
        "fat": 67,
        "water": 3.5
    }
    
    Response: 201 Created
    """
    try:
        clerk_user_id = get_clerk_user_id(request)
        if not clerk_user_id:
            return Response(
                {'error': 'Clerk user ID not found'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data

        # Check if already logged for today
        nutrition_log = NutritionLog.objects.filter(
            clerk_user_id=clerk_user_id,
            date=data.get('date', timezone.now().date())
        ).first()

        if nutrition_log:
            # Update existing log
            nutrition_log.calories = data.get('calories', 0)
            nutrition_log.protein = data.get('protein', 0)
            nutrition_log.carbs = data.get('carbs', 0)
            nutrition_log.fat = data.get('fat', 0)
            nutrition_log.water = data.get('water', 0)
            nutrition_log.save()
        else:
            # Create new log
            nutrition_log = NutritionLog.objects.create(
                clerk_user_id=clerk_user_id,
                date=data.get('date', timezone.now().date()),
                calories=data.get('calories', 0),
                protein=data.get('protein', 0),
                carbs=data.get('carbs', 0),
                fat=data.get('fat', 0),
                water=data.get('water', 0)
            )

        serializer = NutritionLogSerializer(nutrition_log)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except (ValueError, KeyError) as e:
        return Response(
            {'error': f'Invalid data: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 3. GET DASHBOARD / ANALYTICS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_http_methods(["GET"])
def get_dashboard(request):
    """
    GET /performance/dashboard/
    
    Returns comprehensive performance dashboard with all analytics.
    Optimized with select_related and prefetch_related.
    
    Response:
    {
        "strength_score": {...},
        "weekly_volume": {...},
        "body_metrics_trend": {...},
        "calorie_balance": {...},
        "training_streak": {...},
        "recommendations": [...],
        "current_goal": {...},
        "last_updated": "2024-02-22T10:30:00Z"
    }
    """
    try:
        clerk_user_id = get_clerk_user_id(request)
        if not clerk_user_id:
            return Response(
                {'error': 'Clerk user ID not found'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get data from past 30 days
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        # Optimized queries with prefetch
        recent_sessions = WorkoutSession.objects.filter(
            clerk_user_id=clerk_user_id,
            date__gte=thirty_days_ago
        ).prefetch_related('exercises').order_by('-date')

        recent_metrics = BodyMetrics.objects.filter(
            clerk_user_id=clerk_user_id
        ).order_by('-recorded_at')[:100]  # Last 100 records

        today = timezone.now().date()
        today_nutrition = NutritionLog.objects.filter(
            clerk_user_id=clerk_user_id,
            date=today
        ).first()

        user_goal = UserGoal.objects.filter(
            clerk_user_id=clerk_user_id
        ).first()

        # ============================================
        # CALCULATE ANALYTICS
        # ============================================

        # 1. Strength Score
        exercise_logs = []
        for session in recent_sessions:
            for log in session.exercises.all():
                exercise_logs.append({
                    'calculated_1rm': log.calculated_1rm
                })

        # Get average body weight
        latest_metric = recent_metrics.first() if recent_metrics else None
        body_weight = latest_metric.weight if latest_metric else 80.0

        strength_score = PerformanceAnalytics.calculate_strength_score(
            exercise_logs=exercise_logs,
            body_weight=body_weight
        )

        # 2. Weekly Volume
        weekly_sessions = recent_sessions.filter(
            date__gte=timezone.now().date() - timedelta(days=7)
        )
        weekly_volume_data = [
            {'total_volume': s.total_volume} for s in weekly_sessions
        ]
        weekly_volume = PerformanceAnalytics.calculate_weekly_volume(
            sessions=weekly_volume_data,
            days_back=7
        )

        # 3. Body Metrics Trend
        metrics_history = [
            {
                'weight': m.weight,
                'recorded_at': m.recorded_at
            }
            for m in recent_metrics
        ]
        body_metrics_trend = PerformanceAnalytics.analyze_body_metrics(
            metrics_history=metrics_history
        )

        # 4. Calorie Balance
        calories = today_nutrition.calories if today_nutrition else 0
        calorie_balance = PerformanceAnalytics.calculate_calorie_balance(
            daily_intake=calories,
            tdee=2000,  # TODO: Calculate from user profile
            goal_type=user_goal.goal_type if user_goal else 'muscle_gain'
        )

        # 5. Training Streak
        session_dates = [s.date for s in recent_sessions]
        training_streak = PerformanceAnalytics.calculate_streak(
            session_dates=session_dates
        )

        # 6. Generate Recommendations
        recommendations = PerformanceAnalytics.generate_recommendations(
            strength_score=strength_score,
            weekly_volume=weekly_volume,
            calorie_balance=calorie_balance,
            body_metrics=body_metrics_trend
        )

        # ============================================
        # BUILD RESPONSE
        # ============================================

        response_data = {
            'strength_score': strength_score,
            'weekly_volume': weekly_volume,
            'body_metrics_trend': body_metrics_trend,
            'calorie_balance': calorie_balance,
            'training_streak': training_streak,
            'recommendations': recommendations,
            'current_goal': UserGoalSerializer(user_goal).data if user_goal else None,
            'last_updated': timezone.now().isoformat()
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 4. GET RECOMMENDATIONS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_http_methods(["GET"])
def get_recommendations(request):
    """
    GET /performance/recommendations/
    
    Returns rule-based recommendations (no AI).
    Uses analytics to generate actionable advice.
    
    Query parameters:
    - ?type=strength (optional: filter by type)
    """
    try:
        clerk_user_id = get_clerk_user_id(request)
        if not clerk_user_id:
            return Response(
                {'error': 'Clerk user ID not found'},
                status=status.HTTP_403_FORBIDDEN
            )

        # This would fetch dashboard and extract recommendations
        # For now, return a list of recommendations
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        recent_sessions = WorkoutSession.objects.filter(
            clerk_user_id=clerk_user_id,
            date__gte=thirty_days_ago
        ).prefetch_related('exercises')

        exercise_logs = []
        for session in recent_sessions:
            for log in session.exercises.all():
                exercise_logs.append({
                    'calculated_1rm': log.calculated_1rm
                })

        recent_metrics = BodyMetrics.objects.filter(
            clerk_user_id=clerk_user_id
        ).order_by('-recorded_at')[:100]

        body_weight = recent_metrics.first().weight if recent_metrics else 80.0

        strength_score = PerformanceAnalytics.calculate_strength_score(
            exercise_logs=exercise_logs,
            body_weight=body_weight
        )

        weekly_sessions = recent_sessions.filter(
            date__gte=timezone.now().date() - timedelta(days=7)
        )
        weekly_volume = PerformanceAnalytics.calculate_weekly_volume(
            sessions=[{'total_volume': s.total_volume} for s in weekly_sessions],
            days_back=7
        )

        today = timezone.now().date()
        today_nutrition = NutritionLog.objects.filter(
            clerk_user_id=clerk_user_id,
            date=today
        ).first()
        calorie_balance = PerformanceAnalytics.calculate_calorie_balance(
            daily_intake=today_nutrition.calories if today_nutrition else 0,
            tdee=2000
        )

        recommendations = PerformanceAnalytics.generate_recommendations(
            strength_score=strength_score,
            weekly_volume=weekly_volume,
            calorie_balance=calorie_balance
        )

        # Filter by type if requested
        rec_type = request.query_params.get('type')
        if rec_type:
            recommendations = [r for r in recommendations if r.get('type') == rec_type]

        return Response(
            {'recommendations': recommendations},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 5. OPTIONAL: AI-POWERED WORKOUT OPTIMIZATION
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_http_methods(["POST"])
def optimize_workout(request):
    """
    POST /performance/optimize-workout/
    
    OPTIONAL: Uses OpenAI API to generate optimized workout splits.
    Modular and isolated from core analytics.
    
    Request body:
    {
        "current_strength_level": "intermediate",
        "goal_type": "muscle_gain",
        "available_days": 4,
        "equipment": ["barbell", "dumbbells", "cables"]
    }
    
    Response:
    {
        "workout_split": {
            "day_1": {...},
            "day_2": {...},
            ...
        },
        "generated_at": "2024-02-22T10:30:00Z"
    }
    """
    try:
        import openai
        
        clerk_user_id = get_clerk_user_id(request)
        if not clerk_user_id:
            return Response(
                {'error': 'Clerk user ID not found'},
                status=status.HTTP_403_FORBIDDEN
            )

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return Response(
                {'error': 'AI optimization not available'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        data = request.data

        # Build structured prompt
        prompt = f"""
        Create a personalized workout split for a {data.get('current_strength_level', 'intermediate')} 
        fitness enthusiast with a goal of {data.get('goal_type', 'muscle_gain')}.
        
        Available training days per week: {data.get('available_days', 4)}
        Available equipment: {', '.join(data.get('equipment', []))}
        
        Please provide:
        1. A complete workout split with exercise selection
        2. Sets, reps, and rest periods
        3. Progressive overload strategy
        4. Nutrition recommendations aligned with the goal
        
        Format the response as structured JSON with clear sections.
        """

        # Call OpenAI API
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional fitness coach providing personalized workout plans."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=30
        )

        workout_content = response.choices[0].message.content

        # Parse and return
        import json
        try:
            # Try to extract JSON from response
            json_start = workout_content.find('{')
            json_end = workout_content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                workout_data = json.loads(workout_content[json_start:json_end])
            else:
                workout_data = {'raw_recommendation': workout_content}
        except:
            workout_data = {'raw_recommendation': workout_content}

        return Response(
            {
                'workout_split': workout_data,
                'generated_at': timezone.now().isoformat()
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'AI optimization failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 6. USER GOAL ENDPOINTS
# ============================================

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def user_goal(request):
    """
    POST /performance/user-goal/
    GET /performance/user-goal/
    """
    clerk_user_id = get_clerk_user_id(request)
    if not clerk_user_id:
        return Response(
            {'error': 'Clerk user ID not found'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'GET':
        goal = UserGoal.objects.filter(
            clerk_user_id=clerk_user_id
        ).first()
        if not goal:
            return Response(
                {'error': 'No goal set'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = UserGoalSerializer(goal)
        return Response(serializer.data)

    elif request.method == 'POST':
        data = request.data
        goal, created = UserGoal.objects.get_or_create(
            clerk_user_id=clerk_user_id,
            defaults={
                'goal_type': data.get('goal_type', 'muscle_gain'),
                'target_value': data.get('target_value')
            }
        )
        if not created:
            goal.goal_type = data.get('goal_type', goal.goal_type)
            goal.target_value = data.get('target_value', goal.target_value)
            goal.save()

        serializer = UserGoalSerializer(goal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
