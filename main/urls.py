from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    EquipmentViewSet,
    NutritionArticleViewSet, WorkoutArticleViewSet, FitnessArticleViewSet,
    ExerciseViewSet, MuscleGroupViewSet,
    contact_message_api,
    nutrition_articles_list_api, nutrition_article_detail_api,
    workout_articles_list_api, workout_article_detail_api,
    fitness_articles_list_api, fitness_article_detail_api, fitness_articles_related_api,
    workout_tips_list_api, workout_tip_detail_api,
    workout_tips_categories_api, workout_tips_related_api,
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
router.register(r"fitness-articles", FitnessArticleViewSet, basename="fitness-articles")
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
    path("fitness-articles/", fitness_articles_list_api, name="fitness-articles-list"),
    path("fitness-articles/related/<str:article_id>/", fitness_articles_related_api, name="fitness-articles-related"),
    path("fitness-articles/<slug:slug>/", fitness_article_detail_api, name="fitness-article-detail"),
    path("workout-tips/", workout_tips_list_api, name="workout-tips-list"),
    path("workout-tips/categories/", workout_tips_categories_api, name="workout-tips-categories"),
    path("workout-tips/related/<str:tip_id>/", workout_tips_related_api, name="workout-tips-related"),
    path("workout-tips/<slug:slug>/", workout_tip_detail_api, name="workout-tip-detail"),

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
