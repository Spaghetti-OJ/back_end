from rest_framework.response import Response


def api_response(data=None, message: str = "OK", status_code: int = 200) -> Response:
    # status 欄位直接回傳 HTTP 狀態碼字串（如 "200"、"404"）
    return Response({
        "data": data,
        "message": message,
        "status": str(status_code),
    }, status=status_code)
