# api_tokens/views/api_tokens.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from api_tokens.models import ApiToken
# 注意 import 路徑的變化，從 ..serializers 子模組中導入
from ..serializers.api_token import ApiTokenCreateSerializer, ApiTokenListSerializer
from ..services import generate_api_token

class ApiTokenListView(APIView):
    """
    處理對 API Tokens 的請求。
    - GET: 列出當前登入使用者的所有 API Tokens。
    - POST: 為當前使用者建立一個新的 API Token。
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        tokens = ApiToken.objects.filter(user=request.user)
        serializer = ApiTokenListSerializer(tokens, many=True)
        return Response(serializer.data)

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
        return Response(
            {"message": "API Token created...", "full_token": full_token},
            status=status.HTTP_201_CREATED
        )

class ApiTokenDetailView(APIView):
    """
    處理對 API Tokens 的請求。
    - GET: 列出當前登入使用者的所有 API Tokens。
    - POST: 為當前使用者建立一個新的 API Token。
    """
    
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, request, tokenId):
        try:
            return ApiToken.objects.get(id=tokenId, user=request.user)
        except ApiToken.DoesNotExist:
            return None

    def get(self, request, tokenId):
        token = self.get_object(request, tokenId)
        if token is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ApiTokenListSerializer(token)
        return Response(serializer.data)

    def delete(self, request, tokenId):
        token = self.get_object(request, tokenId)
        if token is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)