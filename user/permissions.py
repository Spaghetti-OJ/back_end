from rest_framework.permissions import BasePermission

class IsEmailVerified(BasePermission):
    message = "Email not verified."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(view, "skip_email_verification", False):
            return True

        return getattr(user, "is_email_verified", False)
