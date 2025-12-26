from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    """
    讀取(GET/HEAD/OPTIONS)任何人可用；
    寫入(POST/PUT/PATCH/DELETE)必須是該資源的擁有者。
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "creator_id", None)
        return owner == request.user


class IsTeacherOrAdmin(BasePermission):
    """
    允許 admin/teacher；需已登入。
    - 自訂使用者模型 user.identity in (teacher, admin)
    - 或 is_staff/superuser
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        identity = getattr(user, "identity", None)
        return bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or identity in ("teacher", "admin")
        )
