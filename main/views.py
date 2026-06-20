# main/views.py
from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Equipment, ContactMessage, NutritionArticle, WorkoutArticle,
    Workout, Exercise, MuscleGroup
)
from .serializers import (
    EquipmentSerializer, ContactMessageSerializer, NutritionArticleSerializer,
    WorkoutArticleSerializer, WorkoutSerializer, ExerciseSerializer, MuscleGroupSerializer,
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
