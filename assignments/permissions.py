from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsTeacherOrAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # 可自行改為：群組/role 檢查
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser or
            getattr(request.user, "is_teacher", False) or
            request.user.groups.filter(name__in=["teacher", "instructor"]).exists()
        )