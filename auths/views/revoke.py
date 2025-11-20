from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)

class SessionRevokeView(APIView):
    """
    POST /auth/session/revoke/
    將一顆 refresh token 加入黑名單，使其不能再換發 access。
    預設需帶 Authorization: Bearer <access>（IsAuthenticated）
    refresh 可從 JSON body 或（若採 Cookie 流程）從 Cookie 取得。
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 1) 優先從 JSON body 讀 refresh
        refresh = request.data.get("refresh")

        # 2) 若沒傳，且你採 httpOnly Cookie 存 refresh，可改從 Cookie 讀
        if not refresh:
            refresh = request.COOKIES.get("refresh")

        if not refresh:
            return api_response(message="refresh field required", status_code=status.HTTP_400_BAD_REQUEST)
            #return Response({"detail": "refresh field required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh)  # 解析與驗證 refresh
            token.blacklist()              # 放入黑名單
        except TokenError:
            return api_response(message="Invalid or expired refresh token", status_code=status.HTTP_400_BAD_REQUEST)
            #return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        # 可選：若採 Cookie 流程，順便清除 cookie
        #resp = Response(status=status.HTTP_205_RESET_CONTENT)
        resp = api_response(message="Session revoked", status_code=status.HTTP_205_RESET_CONTENT)
        # resp.delete_cookie("refresh")
        # resp.delete_cookie("access")
        return resp
