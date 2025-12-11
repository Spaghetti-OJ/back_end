# api_tokens/authentication.py

import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import ApiToken

class ApiTokenAuthentication(BaseAuthentication):
    """
    自訂的 Token 認證機制。
    解析 Header 中的 'Authorization: Bearer <token>'
    """

    def authenticate(self, request):
        # 1. 取得 Authorization Header
        auth_header = request.headers.get('Authorization')
        
        # 如果沒有 Header，或者格式不是 'Bearer ...'，則不處理 (回傳 None)
        # 讓 DRF 繼續嘗試下一個認證方式 (例如 Session)
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        # 2. 取出 Token 字串
        try:
            # "Bearer <token_string>" -> 根據空格切割
            raw_token = auth_header.split(' ')[1]
        except IndexError:
            raise AuthenticationFailed('Token 格式錯誤')

        # 2.5. 檢查是否為 API Token 格式
        # 如果不是 noj_pat_ 開頭，可能是 JWT token，讓其他認證類別處理
        if not raw_token.startswith('noj_pat_'):
            return None

        # 3. 對 Token 進行雜湊 (因為資料庫存的是 Hash)
        # 注意：這裡必須跟當初生成 Token 時的雜湊演算法一致 (SHA-256)
        hashed_token = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        # 4. 查詢資料庫
        try:
            token = ApiToken.objects.get(token_hash=hashed_token)
        except ApiToken.DoesNotExist:
            raise AuthenticationFailed('無效的 API Token')

        # 5. 檢查是否過期 (RFC 要求)
        if token.expires_at and token.expires_at < timezone.now():
            raise AuthenticationFailed('API Token 已過期')
        if not token.is_active:
            raise AuthenticationFailed('API Token 已被撤銷')

        # 6. (RFC 要求) 更新使用統計
        # 只有在驗證成功時才更新
        token.last_used_at = timezone.now()
        # 這裡我們需要判斷 request 的 IP
        token.last_used_ip = self.get_client_ip(request)
        token.usage_count += 1
        token.save()

        # 7. 認證成功！回傳 (User, Auth) tuple
        # request.user 會變成 token.user
        # request.auth 會變成這個 token 物件
        return (token.user, token)

    def get_client_ip(self, request):
        """
        輔助函式：嘗試取得客戶端真實 IP
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip