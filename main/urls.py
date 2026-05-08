from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    EquipmentViewSet,
    NutritionArticleViewSet, WorkoutArticleViewSet,
    WorkoutViewSet, ExerciseViewSet, MuscleGroupViewSet,
    contact_message_api,
    nutrition_articles_list_api, nutrition_article_detail_api,
    workout_articles_list_api, workout_article_detail_api,
)
from .performance_views import (
    log_workout,
    log_nutrition,
    get_dashboard,
    get_recommendations,
    optimize_workout,
    user_goal,
)

router = DefaultRouter()
router.register(r"equipment", EquipmentViewSet, basename="equipment")
router.register(r"nutrition-articles", NutritionArticleViewSet, basename="nutrition-articles")
router.register(r"workout-articles", WorkoutArticleViewSet, basename="workout-articles")
router.register(r"workouts", WorkoutViewSet, basename="workouts")
router.register(r"exercises", ExerciseViewSet, basename="exercises")
router.register(r"muscle-groups", MuscleGroupViewSet, basename="muscle-groups")

urlpatterns = [
    # Contact form endpoint
    path("contact/", contact_message_api, name="contact"),

    # Non-paginated convenience endpoints
    path("nutrition-list/", nutrition_articles_list_api, name="nutrition-list"),
    path("nutrition/<slug:slug>/", nutrition_article_detail_api, name="nutrition-detail"),
    path("workout-list/", workout_articles_list_api, name="workout-list"),
    path("workout/<slug:slug>/", workout_article_detail_api, name="workout-detail"),

    # ============================================
    # REDIRON PERFORMANCE LAB - API ENDPOINTS
    # ============================================
    path("performance/log-workout/", log_workout, name="log-workout"),
    path("performance/log-nutrition/", log_nutrition, name="log-nutrition"),
    path("performance/dashboard/", get_dashboard, name="dashboard"),
    path("performance/recommendations/", get_recommendations, name="recommendations"),
    path("performance/optimize-workout/", optimize_workout, name="optimize-workout"),
    path("performance/user-goal/", user_goal, name="user-goal"),
]

urlpatterns += router.urls
