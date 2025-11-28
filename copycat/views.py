import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication

# if we need to add it in api token
# from api_tokens.authentication import ApiTokenAuthentication

from .models import CopycatReport
from .services import run_moss_check

# ===================================================================
def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    if data is None: data = {}
    return Response({"data": data, "message": message, "status": status_str}, status=status_code)

class CopycatView(APIView):
    """
    抄襲檢測 API
    POST: 觸發檢測 (背景執行)
    GET: 查詢檢測結果
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        請求生成報告
        Body: { "problem_id": 101, "language": "python" }
        """
        problem_id = request.data.get('problem_id')
        language = request.data.get('language', 'python')
        
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)

        
        report = CopycatReport.objects.create(
            problem_id=problem_id,
            requester=request.user,
            status='pending'
        )

        thread = threading.Thread(
            target=run_moss_check,
            args=(report.id, problem_id, language)
        )
        thread.start()

        return api_response(
            {"report_id": report.id, "status": "pending"},
            "已開始進行抄襲比對，請稍後查詢結果",
            status_code=202
        )

    def get(self, request):
        """
        查詢報告
        Query Params: ?problem_id=101
        """
        problem_id = request.query_params.get('problem_id')
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)

        report = CopycatReport.objects.filter(problem_id=problem_id).first()
        
        if not report:
            return api_response(None, "此題目尚未進行過抄襲比對", status_code=404)

        data = {
            "id": report.id,
            "status": report.status,
            "moss_url": report.moss_url, 
            "created_at": report.created_at,
            "error_message": report.error_message
        }
        
        msg = "成功取得報告" if report.status == 'success' else f"報告狀態：{report.get_status_display()}"
        return api_response(data, msg)