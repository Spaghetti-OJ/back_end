import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication
from api_tokens.authentication import ApiTokenAuthentication
# if we need to add it in api token
# from api_tokens.authentication import ApiTokenAuthentication

from .models import CopycatReport
from submissions.models import Submission
from problems.models import Problems
from .services import run_moss_check, LANG_DB_MAP

try:
    from problems.models import Problems
except ImportError:
    Problems = None

# ===================================================================
def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    if data is None: data = {}
    return Response({"data": data, "message": message, "status": status_str}, status=status_code)

class CopycatView(APIView):
    authentication_classes = [SessionAuthentication, ApiTokenAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        problem_id = request.data.get('problem_id')
        language = request.data.get('language', 'python')
        
        # 1. 基礎驗證
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)
        
        # 1.5 驗證 problem_id 是否為整數 (Copilot 建議)
        try:
            problem_id = int(problem_id)
        except (ValueError, TypeError):
            return api_response(None, "problem_id 必須是整數", status_code=400)

        # 2. 驗證題目是否存在 (Copilot 建議)
        if Problems:
            if not Problems.objects.filter(id=problem_id).exists():
                return api_response(None, f"題目 ID {problem_id} 不存在", status_code=404)

        # 3. 驗證語言
        if language.lower() not in LANG_DB_MAP:
             return api_response(None, f"不支援的語言: {language}", status_code=400)

        # 4. 防止重複任務 (使用 get_or_create 防止 Race Condition)
        # 只有當沒有 pending 任務時，才建立新的
        report, created = CopycatReport.objects.get_or_create(
            problem_id=problem_id,
            status='pending',
            defaults={'requester': request.user}
        )

        if not created:
            # 如果已經有 pending 的，直接回傳該任務資訊，不重複執行
            return api_response(
                {"report_id": report.id, "status": "pending"},
                "該題目已有正在進行中的抄襲比對任務，請稍後再試",
                status_code=429 # Too Many Requests
            )

        # 5. 啟動背景執行緒
        thread = threading.Thread(
            target=run_moss_check,
            args=(report.id, problem_id, language)
        )
        thread.daemon = True # (Copilot 建議：設為守護執行緒)
        thread.start()

        return api_response(
            {"report_id": report.id, "status": "pending"},
            "已開始進行抄襲比對",
            status_code=202
        )

    def get(self, request):
        """
        查詢「最新」一份報告 (Copilot 建議：與文件保持一致)
        """
        problem_id = request.query_params.get('problem_id')
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)

        # 只抓最新一筆
        report = CopycatReport.objects.filter(problem_id=problem_id).order_by('-created_at').first()
        
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