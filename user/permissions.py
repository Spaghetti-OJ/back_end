from rest_framework.permissions import BasePermission
from user.models import UserProfile

class IsEmailVerified(BasePermission):
    message = "Email not verified."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(view, "skip_email_verification", False):
            return True

        return UserProfile.objects.filter(user=user, email_verified=True).exists()