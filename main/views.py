# main/views.py
import json
import os
from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from rediron_site.email_utils import send_email_message, send_user_email, send_admin_notification, EmailServiceError
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import (
    Equipment, ContactMessage, NutritionArticle, WorkoutArticle,
    FitnessArticle, WorkoutTip, Exercise, MuscleGroup
)
from .serializers import (
    EquipmentSerializer, ContactMessageSerializer, NutritionArticleSerializer,
    WorkoutArticleSerializer, FitnessArticleSerializer, WorkoutTipSerializer, ExerciseSerializer, MuscleGroupSerializer,
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
    for index, row in enumerate(raw_tips):
        tip = row.get("fields", row)
        slug = tip.get("slug") or str(tip.get("title", f"workout-tip-{index + 1}")).lower().replace(" ", "-")
        overview = tip.get("overview", "")
        normalized = {
            **tip,
            "id": row.get("pk") or tip.get("id") or f"WT{index + 1:02d}",
            "slug": slug,
            "thumbnail": tip.get("thumbnail") or tip.get("featured_image_url") or f"/assets/workout-tips/{slug}.jpg",
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
            send_email_message(
                subject=subject,
                message=text_content,
                recipient_list=recipient_list,
                from_email=from_email,
                html_message=html_content,
                fail_silently=fail_silently,
            )
        except EmailServiceError:
            logger.exception("Async email sending failed for subject %s", subject)
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
    data = request.data.copy()
    if getattr(request.user, "is_authenticated", False):
        data["name"] = getattr(request.user, "name", "") or getattr(request.user, "email", "") or data.get("name", "")
        data["email"] = getattr(request.user, "email", "") or data.get("email", "")

    serializer = ContactMessageSerializer(data=data, context={"request": request})
    if serializer.is_valid():
        msg = serializer.save()
        try:
            subject_admin = f"📬 New Contact Message from {msg.name}"
            message_plain_admin = (
                f"Name: {msg.name}\n"
                f"Email: {msg.email}\n"
                f"Subject: {msg.subject}\n\n"
                f"Message:\n{msg.message}\n\n"
                f"Date: {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            admin_to = [getattr(settings, "ADMIN_EMAIL", None) or getattr(settings, "SITE_OWNER_EMAIL", None) or getattr(settings, "SHOP_ADMIN_EMAIL", None)]
            admin_html_message = f"""
            <html><body style="font-family: sans-serif;">
                <h2 style="color: #c0392b;">New Contact Message</h2>
                <p><strong>Name:</strong> {msg.name}</p>
                <p><strong>Email:</strong> {msg.email}</p>
                <p><strong>Subject:</strong> {msg.subject}</p>
                <p><strong>Date:</strong> {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p>{msg.message.replace(chr(10), '<br>')}</p>
            </body></html>
            """
            send_email_async(subject_admin, message_plain_admin, settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER, [recipient for recipient in admin_to if recipient], html_content=admin_html_message, fail_silently=False)

            subject_user = "✅ We received your message at RedIron Gym"
            auto_message_plain = (
                f"Hi {msg.name},\n\n"
                "Thank you for contacting RedIron. We received your message and our team will respond shortly.\n\n"
                "Regards,\nRedIron Gym Team"
            )
            user_html_message = f"""
            <html><body style="font-family: sans-serif;">
                <p>Hi {msg.name},</p>
                <p>Thank you for contacting RedIron. We received your message and our team will respond shortly.</p>
                <p><strong>Regards,</strong><br>The RedIron Gym Team</p>
            </body></html>
            """
            send_email_async(subject_user, auto_message_plain, settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER, [msg.email], html_content=user_html_message, fail_silently=False)

            return Response({"success": "Message received"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Error while handling contact message")
            return Response({"success": "Message received", "warning": f"Email notification failed: {e}"}, status=status.HTTP_201_CREATED)

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
    search_fields = ["title", "overview", "coachInsight"]
    ordering_fields = ["published_at", "title", "category"]
    ordering = ["-published_at", "title"]


# ---------------- EXERCISES ----------------
class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all().prefetch_related("primary_muscles", "secondary_muscles", "equipment").order_by("name")
    serializer_class = ExerciseSerializer # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    permission_classes = [permissions.AllowAny]
    pagination_class = ExercisePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "slug", "skill_level", "exercise_type", "muscle_group", "subcategory",
        "primary_muscles__slug", "secondary_muscles__slug", "equipment", "equipment__name",
    ]
    search_fields = [
        "name", "code", "description", "muscle_group", "subcategory",
        "primary_muscles__name", "secondary_muscles__name", "equipment__name",
    ]
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

    related_codes = [str(code) for code in (current.relatedArticles or [])]
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
