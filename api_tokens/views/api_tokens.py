# api_tokens/views/api_tokens.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from api_tokens.models import ApiToken
from ..serializers.api_token import ApiTokenCreateSerializer, ApiTokenListSerializer
from ..services import generate_api_token
from ..authentication import ApiTokenAuthentication

# ===================================================================
def api_response(data=None, message="OK", status_code=200):
    """
    統一的 API 回應格式 (這個函式現在是這個檔案專屬的)
    """
    status_str = "ok" if 200 <= status_code < 400 else "error"
    
    if data is None:
        data = {}
        
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)


class ApiTokenListView(APIView):
    """
    處理對 API Tokens 的請求。
    - GET: 列出當前登入使用者的所有 API Tokens。
    - POST: 為當前使用者建立一個新的 API Token。
    """

    authentication_classes = [SessionAuthentication, ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        tokens = ApiToken.objects.filter(user=request.user)
        serializer = ApiTokenListSerializer(tokens, many=True)
        return api_response(serializer.data, "成功取得 Token 列表")

    def post(self, request):
        serializer = ApiTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        full_token, token_hash = generate_api_token()
        ApiToken.objects.create(
            user=request.user,
            name=serializer.validated_data['name'],
            token_hash=token_hash,
            prefix=full_token[:8],
            permissions=serializer.validated_data.get('permissions', []),
            expires_at=serializer.validated_data.get('expires_at')
        )
        response_data = {
            "full_token": full_token
        }
        return api_response(
            response_data, 
            "API Token 已建立，請妥善保存", 
            status_code=status.HTTP_201_CREATED
        )

class ApiTokenDetailView(APIView):
    """
    處理對 API Tokens 的請求。
    - GET: 列出當前登入使用者的所有 API Tokens。
    - POST: 為當前使用者建立一個新的 API Token。
    """
    
    authentication_classes = [SessionAuthentication, ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, request, tokenId):
        try:
            return ApiToken.objects.get(id=tokenId, user=request.user)
        except ApiToken.DoesNotExist:
            return None

    def get(self, request, tokenId):
        # ❗ 此處為未實作的 GET /<id> 端點
        return api_response(
            None, 
            "Token 詳情端點尚未實作",
            status_code=status.HTTP_501_NOT_IMPLEMENTED
        )

    def delete(self, request, tokenId):
        token = self.get_object(request, tokenId)
        if token is None:
            # ⬇️ 替換 Delete 的失敗回傳 (404 Not Found) ⬇️
            return api_response(
                None, 
                "Token 不存在或權限不足", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        token.delete()

        return api_response(None, "Token 已成功刪除")