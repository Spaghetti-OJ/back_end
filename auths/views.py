# auths/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# 引入 Session 認證和權限檢查工具
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

# 引入我們的 Model, Serializers 和 Services
from .models import ApiToken
from .serializers import ApiTokenCreateSerializer, ApiTokenListSerializer
from .services import generate_api_token

class ApiTokenListView(APIView):
    """
    處理對 API Tokens 的請求。
    - GET: 列出當前登入使用者的所有 API Tokens。
    - POST: 為當前使用者建立一個新的 API Token。
    """
    
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        處理 GET 請求，回傳使用者擁有的 Tokens 列表。
        """
        tokens = ApiToken.objects.filter(user=request.user)
        serializer = ApiTokenListSerializer(tokens, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        處理 POST 請求，建立一個新的 API Token。
        """
        # 1. 【驗證輸入】
        #    使用 ApiTokenCreateSerializer 來驗證前端傳來的資料。
        serializer = ApiTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True) # 若驗證失敗，會自動回傳 400 錯誤

        # 2. 【執行核心邏輯】
        #    呼叫我們的 service 來生成 Token 和雜湊值
        full_token, token_hash = generate_api_token()
        
        # 3. 【儲存到資料庫】
        #    從驗證過的資料中，安全地獲取 name 等資訊來建立物件
        ApiToken.objects.create(
            user=request.user,
            name=serializer.validated_data['name'],
            token_hash=token_hash,
            # 我們只儲存 Token 的前 8 個字元作為 prefix，方便使用者辨識
            prefix=full_token[:8],
            permissions=serializer.validated_data.get('permissions', []),
            expires_at=serializer.validated_data.get('expires_at')
        )

        # 4. 【回傳重要資訊】
        #    這一步非常關鍵！我們只在這裡回傳一次完整的 Token。
        return Response(
            {
                "message": "API Token created successfully. Please save it securely, as it will not be shown again.",
                "full_token": full_token
            },
            status=status.HTTP_201_CREATED
        )