import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication

# if we need to add it in api token
# from api_tokens.authentication import ApiTokenAuthentication

from .models import CopycatReport
from submissions.models import Submission
from problems.models import Problems
from .services import run_moss_check, LANG_DB_MAP

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
        problem_id = request.data.get('problem_id')
        language = request.data.get('language', 'python') # 預設小寫
        
        # 1. 驗證參數存在
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)
            
        # 2. 驗證語言是否支援 (Copilot 建議)
        if language.lower() not in LANG_DB_MAP:
             return api_response(None, f"不支援的語言: {language}", status_code=400)

        # 3. 檢查是否有正在進行中的任務 (Copilot 建議 - 防止重複)
        if CopycatReport.objects.filter(problem_id=problem_id, status='pending').exists():
             return api_response(None, "該題目已有正在進行中的抄襲比對任務，請稍後再試", status_code=429) # Too Many Requests

        # 4. (選用) 驗證題目是否存在 (這裡先略過，假設前端傳的是對的，或者在 service 層會報錯)

        # 建立報告 & 啟動 Thread (Thread 部分暫時保留，因為 Celery 架設成本較高)
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
            "已開始進行抄襲比對",
            status_code=202
        )

    def get(self, request):
        """
        查詢報告列表 (Copilot 建議：回傳列表而不是單筆)
        """
        problem_id = request.query_params.get('problem_id')
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)

        # 改成回傳列表
        reports = CopycatReport.objects.filter(problem_id=problem_id).order_by('-created_at')
        
        if not reports.exists():
            return api_response([], "此題目尚未進行過抄襲比對", status_code=404)

        data = []
        for report in reports:
            data.append({
                "id": report.id,
                "status": report.status,
                "moss_url": report.moss_url,
                "created_at": report.created_at,
                "error_message": report.error_message
            })
            
        return api_response(data, "成功取得報告列表")