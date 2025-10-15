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
