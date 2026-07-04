from rest_framework.permissions import IsAuthenticated


class IsCoachOwner(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and getattr(obj, "user_id", None) == request.user.id)

