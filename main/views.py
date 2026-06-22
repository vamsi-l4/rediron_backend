# main/views.py
import json
import os
from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import (
    Equipment, ContactMessage, NutritionArticle, WorkoutArticle,
    FitnessArticle, WorkoutTip, Workout, Exercise, MuscleGroup
)
from .serializers import (
    EquipmentSerializer, ContactMessageSerializer, NutritionArticleSerializer,
    WorkoutArticleSerializer, FitnessArticleSerializer, WorkoutTipSerializer, WorkoutSerializer, ExerciseSerializer, MuscleGroupSerializer,
)
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Prefetch
import logging
from threading import Thread

logger = logging.getLogger(__name__)

# ---------------- PAGINATION ----------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ExercisePagination(PageNumberPagination):
    page_size = 16
    page_size_query_param = "page_size"
    max_page_size = 200


WORKOUT_TIP_CATEGORIES = ["Beginner", "Form", "Recovery", "Strength", "Advanced"]


def _workout_tips_fixture_path():
    return os.path.join(settings.BASE_DIR, "main", "fixtures", "Workout_Tips.json")


def _load_workout_tips():
    try:
        with open(_workout_tips_fixture_path(), "r", encoding="utf-8") as fixture:
            raw_tips = json.load(fixture)
    except Exception:
        logger.exception("Failed to load Workout_Tips.json")
        return []

    tips = []
    for index, tip in enumerate(raw_tips):
        slug = tip.get("slug") or str(tip.get("title", f"workout-tip-{index + 1}")).lower().replace(" ", "-")
        overview = tip.get("overview", "")
        normalized = {
            **tip,
            "id": tip.get("id") or f"WT{index + 1:02d}",
            "slug": slug,
            "thumbnail": tip.get("thumbnail") or f"/assets/workout-tips/{slug}.jpg",
            "youtubeUrl": tip.get("youtubeUrl") or "",
            "excerpt": tip.get("excerpt") or (overview[:156] + "..." if len(overview) > 156 else overview),
            "author": tip.get("author") or "RedIron Team",
            "published_at": tip.get("published_at") or tip.get("date") or "2026-01-01T00:00:00Z",
        }
        legacy_youtube_key = "youtube" + "SearchKeyword"
        normalized.pop(legacy_youtube_key, None)
        tips.append(normalized)
    return tips


def _filter_workout_tips(request):
    tips = WorkoutTip.objects.filter(is_published=True).order_by("category", "title")
    category = request.GET.get("category")
    search = request.GET.get("search")

    if category and category.lower() != "all":
        tips = tips.filter(category__iexact=category)

    if search:
        tips = tips.filter(
            models.Q(title__icontains=search) |
            models.Q(overview__icontains=search) |
            models.Q(category__icontains=search)
        )
    return tips


# ---------------- UTIL: async send email ----------------
def send_email_async(subject, text_content, from_email, recipient_list, html_content=None, fail_silently=False):
    def _send():
        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=fail_silently
            )
        except Exception:
            logger.exception("Async email sending failed.")
    Thread(target=_send, daemon=True).start()


# ---------------- EQUIPMENT ----------------
class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Equipment.objects.all().order_by("name")
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # Disable pagination - return all equipment
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


# ---------------- CONTACT ----------------
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AnonRateThrottle])
def contact_message_api(request):
    """
    Saves contact message, sends admin email and auto-reply asynchronously,
    and returns success. Throttled for anonymous clients (configure rates in settings).
    """
    serializer = ContactMessageSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        msg = serializer.save()
        try:
            subject_admin = f"📬 New Contact Message from {msg.name}"
            message_plain_admin = (
                f"Name: {msg.name}\n"
                f"Email: {msg.email}\n"
                f"Subject: {msg.subject}\n\n"
                f"Message:\n{msg.message}"
            )
            admin_to = [settings.EMAIL_HOST_USER] if settings.EMAIL_HOST_USER else [settings.DEFAULT_FROM_EMAIL]
            message_html = msg.message.replace('\n', '<br>')
            admin_html_message = f"""
            <html><body style="font-family: sans-serif;">
                <h2 style="color: #c0392b;">New Contact Message</h2>
                <p><strong>Name:</strong> {msg.name}</p>
                <p><strong>Email:</strong> {msg.email}</p>
                <p><strong>Subject:</strong> {msg.subject}</p>
                <hr>
                <p>{message_html}</p>
            </body></html>
            """
            send_email_async(subject_admin, message_plain_admin, settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER, admin_to, html_content=admin_html_message, fail_silently=True)

            # Auto reply to user (async)
            subject_user = "✅ We received your message at RedIron Gym!"
            auto_message_plain = (
                f"Hi {msg.name},\n\n"
                "Thanks for contacting us! We will get back to you shortly.\n\n"
                "- RedIron Gym Team"
            )
            user_html_message = f"""
            <html><body style="font-family: sans-serif;">
                <p>Hi {msg.name},</p>
                <p>Thanks for contacting us! We have received your message and will get back to you shortly.</p>
                <p><strong>- The RedIron Gym Team</strong></p>
            </body></html>
            """
            send_email_async(subject_user, auto_message_plain, settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER, [msg.email], html_content=user_html_message, fail_silently=True)

            return Response({"success": "Message received"}, status=status.HTTP_201_CREATED)
        except BadHeaderError:
            return Response({"error": "Invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error while handling contact message")
            return Response({"error": f"Error processing message: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------- NUTRITION ARTICLES ----------------
class NutritionArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NutritionArticle.objects.filter(is_published=True).order_by("-featured", "-published_at")
    serializer_class = NutritionArticleSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "featured"]
    search_fields = ["title", "excerpt", "tags"]
    ordering_fields = ["published_at", "title", "featured"]
    ordering = ["-featured", "-published_at"]


# ---------------- WORKOUT ARTICLES ----------------
class WorkoutArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkoutArticle.objects.filter(is_published=True).order_by("-featured", "-published_at")
    serializer_class = WorkoutArticleSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "featured"]
    search_fields = ["title", "excerpt", "tags"]
    ordering_fields = ["published_at", "title", "featured"]
    ordering = ["-featured", "-published_at"]


# ---------------- FITNESS ARTICLES ----------------
class FitnessArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FitnessArticle.objects.filter(is_published=True).order_by("-published_at", "title")
    serializer_class = FitnessArticleSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category"]
    search_fields = ["title", "overview", "coach_insight"]
    ordering_fields = ["published_at", "title", "category"]
    ordering = ["-published_at", "title"]


# ---------------- WORKOUT PROGRAMS ----------------
class WorkoutViewSet(viewsets.ModelViewSet):
    queryset = Workout.objects.all().prefetch_related("workout_exercises__exercise", "muscle_groups", "equipment").order_by("-created_at")
    serializer_class = WorkoutSerializer # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["difficulty", "muscle_groups__slug", "equipment__name", "published"]
    search_fields = ["title", "description", "workout_exercises__exercise__name"]
    ordering_fields = ["created_at", "duration_minutes"]
    lookup_field = "slug"


# ---------------- EXERCISES ----------------
class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all().prefetch_related("primary_muscles", "secondary_muscles", "equipment").order_by("name")
    serializer_class = ExerciseSerializer # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    permission_classes = [permissions.AllowAny]
    pagination_class = ExercisePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["slug", "skill_level", "exercise_type", "primary_muscles__slug", "equipment__name"]
    search_fields = ["name", "description"]
    ordering_fields = ["name"]
    lookup_field = "slug"


# ---------------- MUSCLE GROUPS ----------------
class MuscleGroupViewSet(viewsets.ModelViewSet):
    queryset = MuscleGroup.objects.all().order_by("name")
    serializer_class = MuscleGroupSerializer # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    permission_classes = [permissions.AllowAny]


# ---------------- NON-PAGINATED CONVENIENCE ENDPOINTS ----------------

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def nutrition_articles_list_api(request):
    """
    Returns a list of published nutrition articles without pagination.
    Supports optional category filtering via `?category=`.
    """
    articles = NutritionArticle.objects.filter(is_published=True).order_by("-featured", "-published_at")
    category = request.GET.get("category")
    if category:
        articles = articles.filter(category__iexact=category)
    serializer = NutritionArticleSerializer(articles, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def nutrition_article_detail_api(request, slug):
    """
    Returns the details of a specific nutrition article by slug.
    """
    try:
        article = NutritionArticle.objects.get(slug=slug, is_published=True)
        serializer = NutritionArticleSerializer(article, context={"request": request})
        return Response(serializer.data)
    except NutritionArticle.DoesNotExist:
        return Response({"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def workout_articles_list_api(request):
    """
    Returns a list of all published workout articles without pagination.
    """
    articles = WorkoutArticle.objects.filter(is_published=True).order_by("-featured", "-published_at")
    serializer = WorkoutArticleSerializer(articles, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def workout_article_detail_api(request, slug):
    """
    Returns the details of a specific workout article by slug.
    """
    try:
        article = WorkoutArticle.objects.get(slug=slug, is_published=True)
        serializer = WorkoutArticleSerializer(article, context={"request": request})
        return Response(serializer.data)
    except WorkoutArticle.DoesNotExist:
        return Response({"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def fitness_articles_list_api(request):
    articles = FitnessArticle.objects.filter(is_published=True).order_by("-published_at", "title")
    category = request.GET.get("category")
    search = request.GET.get("search")
    if category and category.lower() != "all":
        articles = articles.filter(category__iexact=category)
    if search:
        articles = articles.filter(
            models.Q(title__icontains=search) |
            models.Q(overview__icontains=search) |
            models.Q(category__icontains=search)
        )
    serializer = FitnessArticleSerializer(articles, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def fitness_article_detail_api(request, slug):
    try:
        article = FitnessArticle.objects.get(slug=slug, is_published=True)
    except FitnessArticle.DoesNotExist:
        return Response({"error": "Fitness article not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = FitnessArticleSerializer(article, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def fitness_articles_related_api(request, article_id):
    current = FitnessArticle.objects.filter(code__iexact=article_id, is_published=True).first()
    if not current and str(article_id).isdigit():
        current = FitnessArticle.objects.filter(pk=article_id, is_published=True).first()
    if not current:
        return Response([], status=status.HTTP_200_OK)

    related_codes = [str(code) for code in (current.related_articles or [])]
    related = list(FitnessArticle.objects.filter(code__in=related_codes, is_published=True))
    related.sort(key=lambda item: related_codes.index(item.code) if item.code in related_codes else 999)

    if len(related) < 4:
        related_ids = {item.id for item in related}
        related.extend(list(
            FitnessArticle.objects.filter(category=current.category, is_published=True)
            .exclude(id=current.id)
            .exclude(id__in=related_ids)
            .order_by("-published_at")[:4 - len(related)]
        ))

    if len(related) < 4:
        related_ids = {item.id for item in related}
        related.extend(list(
            FitnessArticle.objects.filter(is_published=True)
            .exclude(id=current.id)
            .exclude(id__in=related_ids)
            .order_by("-published_at")[:4 - len(related)]
        ))

    serializer = FitnessArticleSerializer(related[:4], many=True, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def workout_tips_list_api(request):
    """
    Fixture-backed Workout Tips API.
    Supports pagination, category filtering and search.
    """
    tips = _filter_workout_tips(request)
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(tips, request)
    serializer_context = {"request": request}
    if page is not None:
        serializer = WorkoutTipSerializer(page, many=True, context=serializer_context)
        return paginator.get_paginated_response(serializer.data)
    serializer = WorkoutTipSerializer(tips, many=True, context=serializer_context)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def workout_tips_categories_api(request):
    discovered = list(
        WorkoutTip.objects.filter(is_published=True)
        .exclude(category="")
        .order_by()
        .values_list("category", flat=True)
        .distinct()
    )
    ordered = [cat for cat in WORKOUT_TIP_CATEGORIES if cat in discovered]
    ordered.extend(cat for cat in discovered if cat not in ordered)
    return Response(["All", *ordered])


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def workout_tip_detail_api(request, slug):
    try:
        tip = WorkoutTip.objects.get(slug=slug, is_published=True)
    except WorkoutTip.DoesNotExist:
        return Response({"error": "Workout tip not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = WorkoutTipSerializer(tip, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def workout_tips_related_api(request, tip_id):
    current = WorkoutTip.objects.filter(code__iexact=tip_id, is_published=True).first()
    if not current and str(tip_id).isdigit():
        current = WorkoutTip.objects.filter(pk=tip_id, is_published=True).first()
    if not current:
        return Response([], status=status.HTTP_200_OK)

    related_codes = [str(code) for code in (current.related_articles or [])]
    related = list(WorkoutTip.objects.filter(code__in=related_codes, is_published=True))
    related.sort(key=lambda item: related_codes.index(item.code) if item.code in related_codes else 999)

    if len(related) < 4:
        related_ids = {item.id for item in related}
        related.extend(list(
            WorkoutTip.objects.filter(category=current.category, is_published=True)
            .exclude(id=current.id)
            .exclude(id__in=related_ids)
            .order_by("title")[:4 - len(related)]
        ))

    serializer = WorkoutTipSerializer(
        related[:4],
        many=True,
        context={"request": request}
        )
    return Response(serializer.data)
