from rest_framework.permissions import BasePermission
from .models import ApiToken

class TokenHasScope(BasePermission):
    """
    權限檢查：
    1. 如果是 Session 登入 (request.auth 不是 ApiToken)，預設擁有所有權限 (回傳 True)。
    2. 如果是 Token 登入，檢查 Token 的 permissions 是否包含 View 定義的 `required_scopes`。
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not isinstance(request.auth, ApiToken):
            return True

        required_scopes = getattr(view, 'required_scopes', [])
        
        if not required_scopes:
            return True

        token_perms = set(request.auth.permissions or [])
    
        required_perms = set(required_scopes)
        
        return required_perms.issubset(token_perms)