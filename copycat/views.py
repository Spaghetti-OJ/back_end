import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsEmailVerified
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from api_tokens.authentication import ApiTokenAuthentication

from .models import CopycatReport
from submissions.models import Submission
from problems.models import Problems
from courses.models import Course_members
from .services import run_moss_check, LANG_DB_MAP


# ===================================================================
def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response(
        {"data": data, "message": message, "status": status_str},
        status=status_code
    )


class CopycatView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication, ApiTokenAuthentication]
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def _has_problem_edit_permission(self, user, problem_id):
        """
        檢查使用者是否有該題目的編輯權限
        - Admin (is_staff/is_superuser/identity='admin') 可以操作所有題目
        - 其他使用者必須是該題所屬課程的老師或助教
        """
        # 1. Admin 權限檢查：可以操作所有題目
        if (
            getattr(user, 'is_superuser', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'identity', None) == 'admin'
        ):
            # 仍需確認題目存在
            if not Problems.objects.filter(pk=problem_id).exists():
                return False, "題目不存在"
            return True, None
        
        # 2. 非 Admin：檢查課程權限
        try:
            problem = Problems.objects.select_related('course_id').get(pk=problem_id)
        except Problems.DoesNotExist:
            return False, "題目不存在"
        
        if not problem.course_id:
            return False, "此題目未關聯到任何課程"
        
        course = problem.course_id
        
        # 檢查是否為課程主要老師
        if course.teacher_id == user:
            return True, None
        
        # 檢查是否為課程成員中的老師或 TA 角色
        is_course_staff = Course_members.objects.filter(
            course_id=course,
            user_id=user,
            role__in=[Course_members.Role.TEACHER, Course_members.Role.TA]
        ).exists()
        
        if is_course_staff:
            return True, None
        
        return False, "您必須是該題所屬課程的老師或助教才能執行此操作"

    def post(self, request):
        problem_id = request.data.get('problem_id')
        language = request.data.get('language', 'python')
        
        # 1. 基礎驗證
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)
        
        # 1.5 驗證 problem_id 是否為整數
        try:
            problem_id = int(problem_id)
        except (ValueError, TypeError):
            return api_response(None, "problem_id 必須是整數", status_code=400)

        # 2. 權限檢查：Admin 可操作所有題目，其他使用者須為課程老師或助教
        has_permission, error_msg = self._has_problem_edit_permission(request.user, problem_id)
        if not has_permission:
            # 根據錯誤訊息決定回傳的 status code
            if "不存在" in error_msg:
                return api_response(None, error_msg, status_code=404)
            return api_response(None, error_msg, status_code=403)

        # 3. 驗證語言
        if language.lower() not in LANG_DB_MAP:
            return api_response(None, f"不支援的語言: {language}", status_code=400)

        # 4. 防止重複任務 (使用 get_or_create 防止 Race Condition)
        report, created = CopycatReport.objects.get_or_create(
            problem_id=problem_id,
            status='pending',
            defaults={'requester': request.user}
        )

        if not created:
            return api_response(
                {"report_id": report.id, "status": "pending"},
                "該題目已有正在進行中的抄襲比對任務，請稍後再試",
                status_code=429
            )

        # 5. 啟動背景執行緒
        thread = threading.Thread(
            target=run_moss_check,
            args=(report.id, problem_id, language)
        )
        thread.daemon = True
        thread.start()

        return api_response(
            {"report_id": report.id, "status": "pending"},
            "已開始進行抄襲比對",
            status_code=202
        )

    def get(self, request):
        """
        查詢「最新」一份報告
        """
        problem_id = request.query_params.get('problem_id')
        if not problem_id:
            return api_response(None, "缺少 problem_id 參數", status_code=400)

        # 驗證 problem_id 是否為整數
        try:
            problem_id = int(problem_id)
        except (ValueError, TypeError):
            return api_response(None, "problem_id 必須是整數", status_code=400)

        # 權限檢查：Admin 可操作所有題目，其他使用者須為課程老師或助教
        has_permission, error_msg = self._has_problem_edit_permission(request.user, problem_id)
        if not has_permission:
            if "不存在" in error_msg:
                return api_response(None, error_msg, status_code=404)
            return api_response(None, error_msg, status_code=403)

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