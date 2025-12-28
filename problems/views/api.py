from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status, permissions
# from .serializers import ProblemCreateSerializer

# class ProblemManageView(APIView):
#     permission_classes = [permissions.IsAdminUser]  # 建議：只有管理員可建題

#     def post(self, request):
#         ser = ProblemCreateSerializer(data=request.data, context={"request": request})
#         if not ser.is_valid():
#             return Response({"success": False, "errors": ser.errors}, status=422)
#         problem = ser.save()
#         return Response({"success": True, "problem_id": problem.id}, status=201)

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from ..responses import api_response
from django.shortcuts import get_object_or_404

from ..models import Problems, Problem_subtasks, Test_cases, Tags, Problem_tags
from courses.models import Courses, Course_members
from ..serializers import (
    ProblemSerializer, ProblemDetailSerializer, ProblemStudentSerializer,
    SubtaskSerializer, TestCaseSerializer, TagSerializer
)
from ..permissions import IsOwnerOrReadOnly, IsTeacherOrAdmin
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Max
from submissions.models import Submission
from ..models import ProblemLike
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import models as dj_models
from django.http import FileResponse, Http404
from django.core.cache import cache
import os
import uuid
import mimetypes
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser
import re

class ProblemsViewSet(viewsets.ModelViewSet):
    queryset = Problems.objects.all().order_by("-created_at")
    serializer_class = ProblemSerializer

    def get_permissions(self):
        from rest_framework.permissions import AllowAny
        if self.request.method == 'GET':
            return [AllowAny()]
        # POST/PUT/PATCH/DELETE 使用全域預設：登入 + email verified
        return []

    def get_queryset(self):
        # 舊前端可能使用 router 路徑：/problem/router/problems
        # 這裡強化過濾邏輯，與 ProblemListView 保持一致，避免未加入課程者看到 course-only 題目
        from django.db.models import Q
        qs = Problems.objects.all().select_related('creator_id', 'course_id').prefetch_related('tags', 'subtasks')

        # 篩選：difficulty
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        # 篩選：is_public（僅接受既定值）
        visibility = self.request.query_params.get('is_public')
        if visibility in ('public', 'course', 'hidden'):
            qs = qs.filter(is_public=visibility)

        # 篩選：course_id（帶入時需課程成員或管理員/教師）
        course_id = self.request.query_params.get('course_id')
        user = getattr(self.request, 'user', None)
        if course_id:
            try:
                cid = int(course_id)
            except (TypeError, ValueError):
                # 無效的 course_id 直接回傳空 QuerySet，避免異常或洩漏資訊
                return Problems.objects.none()
            qs = qs.filter(course_id=cid)
            if not getattr(user, 'is_authenticated', False):
                # 直接擋下，避免洩漏課程題目清單
                return Problems.objects.none()
            is_staff_like = bool(
                getattr(user, 'is_staff', False)
                or getattr(user, 'is_superuser', False)
                or getattr(user, 'identity', None) in ['admin', 'teacher']
            )
            if not is_staff_like:
                from courses.models import Course_members
                is_member = Course_members.objects.filter(course_id_id=cid, user_id=user).exists()
                if not is_member:
                    # 非成員時不回任何資料
                    return Problems.objects.none()

        # 一般權限過濾
        if not getattr(user, 'is_authenticated', False):
            qs = qs.filter(is_public__in=['public', True, 1])
        elif not (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False) or getattr(user, 'identity', None) in ['admin', 'teacher']):
            from courses.models import Course_members
            user_courses = Course_members.objects.filter(user_id=user).values_list('course_id', flat=True)
            qs = qs.filter(
                Q(is_public__in=['public', True, 1]) | Q(creator_id=user) | Q(is_public='course', course_id__in=user_courses)
            )

        ordering = self.request.query_params.get('ordering', '-created_at')
        return qs.order_by(ordering)

    def perform_create(self, serializer):
        serializer.save(creator_id=self.request.user)

    def perform_update(self, serializer):
        #serializer.save(creator_id=self.get_object().creator_id)
        serializer.save(creator_id=serializer.instance.creator_id)

class SubtasksViewSet(viewsets.ModelViewSet):
    queryset = Problem_subtasks.objects.all().order_by("problem_id", "subtask_no")
    serializer_class = SubtaskSerializer

    def get_permissions(self):
        from rest_framework.permissions import AllowAny
        if self.request.method == 'GET':
            return [AllowAny()]
        # POST/PUT/PATCH/DELETE 使用全域預設：登入 + email verified
        return []

    def perform_create(self, serializer):
        problem = serializer.validated_data["problem_id"]
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can modify its subtasks.")
        serializer.save()

    def perform_update(self, serializer):
        problem = serializer.instance.problem_id
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can modify its subtasks.")
        serializer.save()
        
    def perform_destroy(self, instance):
        problem = instance.problem_id
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can delete its subtasks.")
        instance.delete()


class ProblemSubtaskListCreateView(APIView):
    """GET /problem/<problemId>/subtasks — 取得子題列表
    POST /problem/<problemId>/subtasks — 新增子題
    權限：GET 可匿名（視題目可見性過濾）；POST 需為題目擁有者或課程 TA/教師/管理員。
    """
    permission_classes = []

    def get(self, request, pk: int):
        try:
            problem = Problems.objects.get(pk=pk)
        except Problems.DoesNotExist:
            return api_response(None, "Problem not found.", status_code=404)

        # 可見性過濾：非公開需檢查身份
        user = request.user
        visibility = getattr(problem, 'is_public', 'hidden')
        legacy_public = visibility in (True, 1)
        visibility_normalized = 'public' if legacy_public else visibility
        if visibility_normalized not in ('public'):
            if not user.is_authenticated:
                return api_response(None, "Authentication required.", status_code=401)
            if not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher'] or problem.creator_id == user):
                if visibility_normalized == 'course' and problem.course_id:
                    from courses.models import Course_members
                    is_course_member = Course_members.objects.filter(course_id=problem.course_id, user_id=user).exists()
                    if not is_course_member:
                        return api_response(None, "You do not have permission to view this problem.", status_code=403)
                else:
                    return api_response(None, "You do not have permission to view this problem.", status_code=403)

        subtasks = Problem_subtasks.objects.filter(problem_id=problem).order_by('subtask_no')
        return api_response(SubtaskSerializer(subtasks, many=True).data, "OK", status_code=200)

    def post(self, request, pk: int):
        if not request.user.is_authenticated:
            return api_response(None, "Authentication required.", status_code=401)
        problem = get_object_or_404(Problems, pk=pk)
        user = request.user

        # 權限：owner/課程 TA/教師/管理員
        if not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher'] or problem.creator_id == user):
            from courses.models import Course_members
            is_staff = Course_members.objects.filter(course_id=problem.course_id, user_id=user, role__in=['ta', 'teacher']).exists()
            if not is_staff:
                return api_response(None, "Not enough permission", status_code=403)

        data = request.data.copy()
        data['problem_id'] = problem.id
        serializer = SubtaskSerializer(data=data)
        if not serializer.is_valid():
            return api_response({"errors": serializer.errors}, "Validation error", status_code=422)
        subtask = serializer.save()
        return api_response(SubtaskSerializer(subtask).data, "Subtask created", status_code=201)


class ProblemSubtaskDetailView(APIView):
    """PUT /problem/<problemId>/subtasks/<subtaskId> — 修改子題
    DELETE /problem/<problemId>/subtasks/<subtaskId> — 刪除子題
    權限：題目擁有者或課程 TA/教師/管理員。
    """

    def _get_subtask_with_permission(self, problem_id: int, subtask_id: int, user):
        subtask = get_object_or_404(Problem_subtasks, pk=subtask_id)
        if subtask.problem_id_id != problem_id:
            from rest_framework.exceptions import NotFound
            raise NotFound("Subtask does not belong to this problem")
        problem = subtask.problem_id
        if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher'] or problem.creator_id == user:
            return subtask
        from courses.models import Course_members
        is_staff = Course_members.objects.filter(course_id=problem.course_id, user_id=user, role__in=['ta', 'teacher']).exists()
        if not is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Not enough permission")
        return subtask

    def put(self, request, pk: int, subtask_id: int):
        subtask = self._get_subtask_with_permission(pk, subtask_id, request.user)
        serializer = SubtaskSerializer(subtask, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response({"errors": serializer.errors}, "Validation error", status_code=422)
        serializer.save()
        return api_response(SubtaskSerializer(subtask).data, "Subtask updated", status_code=200)

    def delete(self, request, pk: int, subtask_id: int):
        subtask = self._get_subtask_with_permission(pk, subtask_id, request.user)
        subtask.delete()
        return api_response(None, "Subtask deleted", status_code=204)

class TestCasesViewSet(viewsets.ModelViewSet):
    queryset = Test_cases.objects.all().order_by("subtask_id", "idx")
    serializer_class = TestCaseSerializer

    def get_permissions(self):
        from rest_framework.permissions import AllowAny
        if self.request.method == 'GET':
            return [AllowAny()]
        # POST/PUT/PATCH/DELETE 使用全域預設：登入 + email verified
        return []

    def _ensure_owner(self, subtask):
        problem = subtask.problem_id
        if problem.creator_id != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the problem owner can modify its test cases.")

    def perform_create(self, serializer):
        subtask = serializer.validated_data["subtask_id"]
        self._ensure_owner(subtask)
        serializer.save()

    def perform_update(self, serializer):
        subtask = serializer.instance.subtask_id
        self._ensure_owner(subtask)
        serializer.save()
        
    def perform_destroy(self, instance):
        subtask = instance.subtask_id
        self._ensure_owner(subtask)
        instance.delete()


class ProblemTestCaseListCreateView(APIView):
    """
    GET /problem/<problemId>/test-cases — 取得測資列表（屬於此題目的所有子題的測資）
    POST /problem/<problemId>/test-cases — 新增測資（需指定 subtask_id，且該子題必須隸屬此題目）
    權限：owner / 課程 TA / 教師 / 管理員（POST）；GET 允許匿名但僅在題目可見時回傳（與詳情同規則）。
    """
    permission_classes = []

    def _can_view_problem(self, problem, user):
        visibility = getattr(problem, 'is_public', 'hidden')
        legacy_public = visibility in (True, 1)
        visibility_normalized = 'public' if legacy_public else visibility
        if visibility_normalized == 'public':
            return True
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher'] or problem.creator_id == user:
            return True
        if visibility_normalized == 'course' and problem.course_id:
            from courses.models import Course_members
            return Course_members.objects.filter(course_id=problem.course_id, user_id=user).exists()
        return False

    def get(self, request, pk: int):
        problem = get_object_or_404(Problems, pk=pk)
        if not self._can_view_problem(problem, request.user):
            return api_response(None, "Not enough permission", status_code=403)
        subtasks = Problem_subtasks.objects.filter(problem_id=problem).values_list('id', flat=True)
        tcs = Test_cases.objects.filter(subtask_id_id__in=list(subtasks)).order_by('subtask_id_id', 'idx')
        return api_response(TestCaseSerializer(tcs, many=True).data, "OK", status_code=200)

    def post(self, request, pk: int):
        if not request.user.is_authenticated:
            return api_response(None, "Authentication required.", status_code=401)
        problem = get_object_or_404(Problems, pk=pk)
        if not _has_problem_manage_permission(problem, request.user):
            return api_response(None, "Not enough permission", status_code=403)
        # 需指定 subtask_id，且該子題必須屬於此題目
        subtask_id = request.data.get('subtask_id') or request.data.get('subtaskId')
        if not subtask_id:
            return api_response({"errors": {"subtask_id": "required"}}, "Validation error", status_code=422)
        try:
            subtask_id_int = int(subtask_id)
        except (ValueError, TypeError):
            return api_response({"errors": {"subtask_id": "must be integer"}}, "Validation error", status_code=422)
        subtask = Problem_subtasks.objects.filter(pk=subtask_id_int, problem_id=problem).first()
        if not subtask:
            return api_response(None, "Subtask not found or not belonging to this problem", status_code=404)
        data = request.data.copy()
        data['subtask_id'] = subtask.id
        ser = TestCaseSerializer(data=data)
        if not ser.is_valid():
            return api_response({"errors": ser.errors}, "Validation error", status_code=422)
        obj = ser.save()
        return api_response(TestCaseSerializer(obj).data, "Test case created", status_code=201)


class ProblemTestCaseDetailView(APIView):
    """
    PUT /problem/<problemId>/test-cases/<caseId> — 修改測資
    DELETE /problem/<problemId>/test-cases/<caseId> — 刪除測資
    權限：owner / 課程 TA / 教師 / 管理員。
    """

    def _get_case_with_permission(self, problem_id: int, case_id: int, user):
        case = get_object_or_404(Test_cases, pk=case_id)
        subtask = case.subtask_id
        if subtask.problem_id_id != problem_id:
            from rest_framework.exceptions import NotFound
            raise NotFound("Test case does not belong to this problem")
        problem = subtask.problem_id
        if _has_problem_manage_permission(problem, user):
            return case
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Not enough permission")

    def put(self, request, pk: int, case_id: int):
        case = self._get_case_with_permission(pk, case_id, request.user)
        ser = TestCaseSerializer(case, data=request.data, partial=True)
        if not ser.is_valid():
            return api_response({"errors": ser.errors}, "Validation error", status_code=422)
        ser.save()
        return api_response(TestCaseSerializer(case).data, "Test case updated", status_code=200)

    def delete(self, request, pk: int, case_id: int):
        case = self._get_case_with_permission(pk, case_id, request.user)
        case.delete()
        return api_response(None, "Test case deleted", status_code=204)

class TagListCreateView(APIView):
    """GET /tags/ 取得所有標籤
    POST /tags/ 建立新標籤（需要登入，建議僅教師/管理員；此處暫允任何登入使用者）
    """

    def get_permissions(self):
        from rest_framework.permissions import AllowAny
        if self.request.method == 'GET':
            return [AllowAny()]
        # POST 使用全域預設：登入 + email verified
        return []

    def get(self, request):
        tags = Tags.objects.all().order_by('name')
        return api_response(TagSerializer(tags, many=True).data, "取得標籤列表成功", status_code=200)

    def post(self, request):
        if not request.user.is_authenticated:
            return api_response(None, "Authentication required.", status_code=401)
        ser = TagSerializer(data=request.data)
        if not ser.is_valid():
            return api_response(ser.errors, "Validation error", status_code=422)
        tag = ser.save()
        return api_response(TagSerializer(tag).data, "Tag created", status_code=201)


def _has_problem_manage_permission(problem, user) -> bool:
    if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
        return True
    # 含 TA
    return Course_members.objects.filter(course_id=problem.course_id, user_id=user, role__in=['ta', 'teacher']).exists()


class ProblemTestCaseUploadInitiateView(APIView):

    def post(self, request, pk: int):
        problem = get_object_or_404(Problems, pk=pk)
        if not _has_problem_manage_permission(problem, request.user):
            return api_response(None, "Not enough permission", status_code=403)
        try:
            length = int(request.data.get('length'))
            part_size = int(request.data.get('part_size'))
        except (TypeError, ValueError):
            return api_response(None, "length and part_size are required integers", status_code=422)
        upload_id = str(uuid.uuid4())
        ttl_seconds = 600
        cache.set(f"prob_tc_multipart:{upload_id}", {
            "problem_id": problem.id,
            "user_id": request.user.id,
            "length": length,
            "part_size": part_size,
            "parts": [],
        }, ttl_seconds)
        # 本地 storage 無 presigned URL，提供本服務的分片上傳端點占位
        part_endpoint = f"/problem/{problem.id}/test-case-upload-part"
        return api_response({
            "upload_id": upload_id,
            "ttl": ttl_seconds,
            "part_endpoint": part_endpoint,
        }, "Upload initiated", status_code=200)


# 移除本地分片端點，改以三端點規格運作：initiate、complete、download


class ProblemTestCaseUploadCompleteView(APIView):

    def post(self, request, pk: int):
        problem = get_object_or_404(Problems, pk=pk)
        if not _has_problem_manage_permission(problem, request.user):
            return api_response(None, "Not enough permission", status_code=403)
        upload_id = request.data.get('upload_id')
        if not upload_id:
            return api_response(None, "upload_id is required", status_code=422)
        info = cache.get(f"prob_tc_multipart:{upload_id}")
        if not info:
            return api_response(None, "upload_id expired or invalid", status_code=410)
        # 合併所有分片為一個 zip 或原始檔（此處直接存為完整檔，並驗證檔名成對）
        tmp_dir = os.path.join(settings.MEDIA_ROOT, "tmp_uploads", upload_id)
        part_files = sorted([os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.startswith('part_')])
        if not part_files:
            return api_response(None, "No uploaded parts", status_code=422)
        from io import BytesIO
        buffer = BytesIO()
        for p in part_files:
            with open(p, 'rb') as f:
                buffer.write(f.read())
        buffer.seek(0)
        # 驗證同名成對：內容為 zip，檢查內部包含 .in/.out 配對（僅驗證，不產生 meta）
        import zipfile
        try:
            with zipfile.ZipFile(buffer) as zf:
                names = zf.namelist()
                ins = {n for n in names if n.endswith('.in')}
                outs = {n for n in names if n.endswith('.out')}
                def stem(n):
                    base = os.path.basename(n)
                    return os.path.splitext(base)[0]
                ins_stems = {stem(n) for n in ins}
                outs_stems = {stem(n) for n in outs}
                missing_pairs = sorted(list(ins_stems ^ outs_stems))
                if missing_pairs:
                    return api_response({"missing_pairs": missing_pairs}, "Validation error: missing paired .in/.out", status_code=400)
        except zipfile.BadZipFile:
            return api_response(None, "Uploaded content must be a valid zip", status_code=400)

        # 保存 zip 到本地 storage（不包含 meta.json；完整分片合併結果）
        from ..services.storage import _storage
        zip_rel = os.path.join("testcases", f"p{problem.id}", "problem.zip")
        buffer.seek(0)
        # 覆蓋舊檔，確保下載端永遠拿到最新版本
        try:
            if _storage.exists(zip_rel):
                _storage.delete(zip_rel)
        except Exception:
            pass
        saved = _storage.save(zip_rel, buffer)
        # 清理臨時檔
        try:
            for p in part_files:
                os.remove(p)
            os.rmdir(tmp_dir)
        except Exception:
            pass
        cache.delete(f"prob_tc_multipart:{upload_id}")
        return api_response({"path": saved.replace('\\','/')}, "Upload completed", status_code=201)


class ProblemTestCaseDownloadView(APIView):

    def get(self, request, pk: int):
        problem = get_object_or_404(Problems, pk=pk)
        if not _has_problem_manage_permission(problem, request.user):
            return api_response(None, "Not enough permission", status_code=403)
        # 嘗試提供問題層級的 zip
        from ..services.storage import _storage
        rel = os.path.join("testcases", f"p{problem.id}", "problem.zip")
        if not _storage.exists(rel):
            raise Http404("No test case archive")
        fh = _storage.open(rel, 'rb')
        resp = FileResponse(fh, content_type='application/zip')
        resp["Content-Disposition"] = f"attachment; filename=\"problem-{problem.id}-testcases.zip\""
        return resp


def _build_testcases_list(pairs_map: dict, max_ss: int) -> list:
    """
    建立 testcases 列表，記錄每個測資檔案的詳細資訊
    
    Args:
        pairs_map (dict): 映射 subtask_index -> {'in': set(tt), 'out': set(tt)}
        max_ss (int): 最大的 subtask index
    
    Returns:
        list: 包含每個測資詳細資訊的列表，每個元素包含 stem, no, in, out, subtask 欄位
    """
    testcases = []
    testcase_no = 1
    for ss in range(max_ss + 1):
        entry = pairs_map.get(ss, {'in': set(), 'out': set()})
        matched_tts = sorted(entry['in'] & entry['out'])
        for tt in matched_tts:
            stem = f"{ss:02d}{tt:02d}"
            testcases.append({
                "stem": stem,
                "no": testcase_no,
                "in": f"{stem}.in",
                "out": f"{stem}.out",
                "subtask": ss + 1  # subtask 從 1 開始
            })
            testcase_no += 1
    return testcases


class ProblemTestCaseZipUploadView(APIView):
    """
    POST /problem/<pk>/test-cases/upload-zip
    需求（目前版）：前端拖一個 zip 直接上傳，我們僅保存 zip 檔到問題目錄，不解析內容、不產生 Test_cases 紀錄。

    參數：multipart form-data
      - file: zip 檔案（必填）

    權限：題目擁有者 / 課程 TA / 教師 / 管理員。
    行為：
      - 將 zip 存到 `MEDIA_ROOT/testcases/p<problem.id>/problem.zip`。
      - 回傳保存路徑。
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk: int):
        problem = get_object_or_404(Problems, pk=pk)
        if not _has_problem_manage_permission(problem, request.user):
            return api_response(None, "Not enough permission", status_code=403)

        upload = request.FILES.get('file')
        if not upload:
            return api_response({"errors": {"file": "required"}}, "Validation error", status_code=422)

        # 讀取 zip、解析檔名規則 sstt.in/out，生成 meta.json 並一併寫入 zip
        import zipfile
        from io import BytesIO
        data = upload.read()
        try:
            src_zip = zipfile.ZipFile(BytesIO(data))
        except zipfile.BadZipFile:
            return api_response(None, "Uploaded file must be a valid zip", status_code=400)

        names = src_zip.namelist()
        # 映射：subtask_index -> { 'in': set(tt), 'out': set(tt) }
        pairs_map = {}
        for n in names:
            base = os.path.basename(n)
            stem, ext = os.path.splitext(base)
            # 規則：四位數 sstt，兩位子題、兩位測資，從 00 開始
            if ext not in ('.in', '.out'):
                continue
            if len(stem) != 4 or not stem.isdigit():
                continue
            ss = int(stem[:2])
            tt = int(stem[2:])
            entry = pairs_map.setdefault(ss, {'in': set(), 'out': set()})
            entry['in' if ext == '.in' else 'out'].add(tt)

        # 以「同時存在 in/out」的 tt 數量作為 caseCount
        case_counts = {}
        for ss, entry in pairs_map.items():
            count = len(entry['in'] & entry['out'])
            case_counts[ss] = count

        # 從資料庫讀取既有子題設定（time/memory/score），對應 ss -> subtask_no = ss+1
        subtask_map = {st.subtask_no - 1: st for st in Problem_subtasks.objects.filter(problem_id=problem)}

        def build_meta_entry(ss_idx: int):
            st = subtask_map.get(ss_idx)
            case_count = case_counts.get(ss_idx, 0)
            time_limit = getattr(st, 'time_limit_ms', None) or 1000
            mem_mb = getattr(st, 'memory_limit_mb', None)
            memory_limit = (mem_mb * 1024) if mem_mb is not None else 134218
            task_score = getattr(st, 'weight', None) or 0
            return {
                "caseCount": case_count,
                "memoryLimit": memory_limit // 1024,  # Sandbox uses MB for memoryLimit in meta
                "memoryLimitKB": memory_limit,
                "taskScore": task_score,
                "timeLimit": time_limit,
            }

        # 產生 meta.json 結構，子題索引由 0..max(ss)
        if case_counts:
            max_ss = max(case_counts.keys())
        else:
            max_ss = -1
        
        meta = {
            "tasks": [build_meta_entry(ss) for ss in range(max_ss + 1)],
            "testcases": _build_testcases_list(pairs_map, max_ss)
        }

        # 重打包 zip：複製原檔案並加入 meta.json
        out_buf = BytesIO()
        with zipfile.ZipFile(out_buf, mode='w', compression=zipfile.ZIP_DEFLATED) as out_zip:
            for n in names:
                with src_zip.open(n, 'r') as f:
                    out_zip.writestr(n, f.read())
            import json
            out_zip.writestr('meta.json', json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
            # 若題目有 solution code，依語言加入對應副檔名的檔案
            try:
                sol_code = getattr(problem, 'solution_code', None)
                if sol_code and str(sol_code).strip():
                    lang = (getattr(problem, 'solution_code_language', '') or '').lower()
                    ext_map = {
                        'python': 'py', 'py': 'py',
                        'cpp': 'cpp', 'c++': 'cpp',
                        'c': 'c',
                        'java': 'java',
                        'javascript': 'js', 'js': 'js',
                        'go': 'go',
                    }
                    ext = ext_map.get(lang, 'txt')
                    out_zip.writestr(f'solution.{ext}', sol_code)
            except Exception:
                # 寫入解答失敗不影響上傳流程
                pass
        out_buf.seek(0)

        # 保存 zip 到本地 storage
        from ..services.storage import _storage
        rel = os.path.join("testcases", f"p{problem.id}", "problem.zip")
        # 覆蓋舊檔，確保下載端永遠拿到最新版本
        try:
            if _storage.exists(rel):
                _storage.delete(rel)
        except Exception:
            pass
        saved = _storage.save(rel, out_buf)
        
        # 計算已儲存檔案的 SHA256 hash 並儲存到 problem
        import hashlib
        with _storage.open(rel, 'rb') as fh:
            sha256_hash = hashlib.sha256(fh.read()).hexdigest()
        problem.testcase_hash = sha256_hash
        problem.save(update_fields=['testcase_hash'])
        
        return api_response({"path": saved.replace('\\','/'), "testcase_hash": sha256_hash}, "Zip uploaded with meta", status_code=201)


class ProblemTestCaseChecksumView(APIView):
    """GET /problem/<pk>/checksum (Sandbox 專用)
    目的：沙盒下載測資 zip 後驗證 SHA256 完整性。
    驗證：使用 query string `token` 與後端設定的 SANDBOX_TOKEN 比對。
    回傳：{"checksum": "<sha256>"}
    錯誤：401 token 無效；404 題目或測資不存在。
    """
    permission_classes = []  # 以 sandbox token 驗證，不用一般身份驗證

    def get(self, request, pk: int):
        token_req = request.GET.get('token')
        token_expected = getattr(settings, 'SANDBOX_TOKEN', os.environ.get('SANDBOX_TOKEN'))
        if not token_expected or token_req != token_expected:
            return api_response(None, "Invalid sandbox token", status_code=401)
        problem = get_object_or_404(Problems, pk=pk)
        # 使用儲存的 testcase_hash
        if not problem.testcase_hash:
            return api_response(None, "Test case hash not available", status_code=404)
        return api_response({"checksum": problem.testcase_hash}, "OK", status_code=200)


class ProblemTestCaseMetaView(APIView):
    """GET /problem/<pk>/meta (Sandbox 專用)
    目的：沙盒在判題前取得測資結構描述。
    回傳 tasks：每個測試對象包含 in/out 檔名與序號；若有不成對檔案列於 missing_pairs。
    驗證：query string `token`。
    """
    permission_classes = []

    def get(self, request, pk: int):
        token_req = request.GET.get('token')
        token_expected = getattr(settings, 'SANDBOX_TOKEN', os.environ.get('SANDBOX_TOKEN'))
        if not token_expected or token_req != token_expected:
            return api_response(None, "Invalid sandbox token", status_code=401)
        problem = get_object_or_404(Problems, pk=pk)
        from ..services.storage import _storage
        rel = os.path.join("testcases", f"p{problem.id}", "problem.zip")
        if not _storage.exists(rel):
            raise Http404("Test case archive not found")
        import zipfile, json
        with _storage.open(rel, 'rb') as fh:
            data = fh.read()
        from io import BytesIO
        buffer = BytesIO(data)
        # 優先讀取 zip 內的 meta.json；若不存在則回退為檔名掃描
        try:
            with zipfile.ZipFile(buffer) as zf:
                # 先嘗試 meta.json
                if 'meta.json' in zf.namelist():
                    with zf.open('meta.json') as mf:
                        meta = json.loads(mf.read().decode('utf-8'))
                    # 依需求直接回傳 meta.json 的 JSON 結構
                    return api_response(meta, "OK", status_code=200)
                # fallback：掃描 .in/.out，組出與 meta.json 相同格式
                names = zf.namelist()
                # 計算各子題的成對數量
                pairs_map = {}
                for n in names:
                    base = os.path.basename(n)
                    stem, ext = os.path.splitext(base)
                    if ext not in ('.in', '.out'):
                        continue
                    if len(stem) != 4 or not stem.isdigit():
                        continue
                    ss = int(stem[:2])
                    tt = int(stem[2:])
                    entry = pairs_map.setdefault(ss, {'in': set(), 'out': set()})
                    entry['in' if ext == '.in' else 'out'].add(tt)

                case_counts = {ss: len(entry['in'] & entry['out']) for ss, entry in pairs_map.items()}

                # 從資料庫讀取子題設定，與 upload-zip 的預設一致
                subtask_map = {st.subtask_no - 1: st for st in Problem_subtasks.objects.filter(problem_id=problem)}
                def build_meta_entry(ss_idx: int):
                    st = subtask_map.get(ss_idx)
                    case_count = case_counts.get(ss_idx, 0)
                    time_limit = getattr(st, 'time_limit_ms', None) or 1000
                    mem_mb = getattr(st, 'memory_limit_mb', None)
                    memory_limit = (mem_mb * 1024) if mem_mb is not None else 134218
                    task_score = getattr(st, 'weight', None) or 0
                    return {
                        "caseCount": case_count,
                        "memoryLimit": memory_limit // 1024,
                        "memoryLimitKB": memory_limit,
                        "taskScore": task_score,
                        "timeLimit": time_limit,
                    }
                max_ss = max(case_counts.keys()) if case_counts else -1
                
                meta = {
                    "tasks": [build_meta_entry(ss) for ss in range(max_ss + 1)],
                    "testcases": _build_testcases_list(pairs_map, max_ss)
                }
        except zipfile.BadZipFile:
            return api_response(None, "Corrupted test case archive", status_code=500)
        # 回傳 fallback 生成的 meta 結構
        return api_response(meta, "OK", status_code=200)


class ProblemTagAddView(APIView):
    """POST /problem/<id>/tags  將現有標籤加入題目
    Body: {"tag_id": 1} 或 {"tagId": 1}
    權限：題目擁有者 / 課程 TA / 教師 / 管理員
    若標籤已存在於題目，回傳 400。
    """

    def _get_problem_for_modify(self, problem_id, user):
        problem = get_object_or_404(Problems, pk=problem_id)
        if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
            return problem
        if problem.creator_id == user:
            return problem
        if problem.course_id:
            from courses.models import Course_members
            is_staff = Course_members.objects.filter(
                course_id=problem.course_id,
                user_id=user,
                role__in=['ta', 'teacher']
            ).exists()
            if is_staff:
                return problem
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Not enough permission to modify problem tags.")

    def post(self, request, pk):
        problem = self._get_problem_for_modify(pk, request.user)
        tag_id = request.data.get('tag_id') or request.data.get('tagId')
        if tag_id is None:
            return api_response(None, "tag_id is required", status_code=400)
        try:
            tag_id = int(tag_id)
        except (ValueError, TypeError):
            return api_response(None, "Invalid tag_id", status_code=400)
        tag = Tags.objects.filter(pk=tag_id).first()
        if not tag:
            return api_response(None, "Tag not found.", status_code=404)
        # 已存在關聯？
        if Problem_tags.objects.filter(problem_id=problem, tag_id=tag).exists():
            return api_response(None, "Tag already attached to problem.", status_code=400)
        from django.db.models import F
        Problem_tags.objects.create(problem_id=problem, tag_id=tag, added_by=request.user)
        Tags.objects.filter(pk=tag.pk).update(usage_count=F('usage_count') + 1)
        tag.refresh_from_db()
        return api_response({"tag": TagSerializer(tag).data}, "Tag added", status_code=201)


class ProblemTagRemoveView(APIView):
    """DELETE /problem/<id>/tags/<tag_id>  從題目移除標籤
    權限：題目擁有者 / 課程 TA / 教師 / 管理員
    若關聯不存在則回傳 404。
    """

    def _get_problem_for_modify(self, problem_id, user):
        problem = get_object_or_404(Problems, pk=problem_id)
        if user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']:
            return problem
        if problem.creator_id == user:
            return problem
        if problem.course_id:
            from courses.models import Course_members
            is_staff = Course_members.objects.filter(
                course_id=problem.course_id,
                user_id=user,
                role__in=['ta', 'teacher']
            ).exists()
            if is_staff:
                return problem
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Not enough permission to modify problem tags.")

    def delete(self, request, pk, tag_id):
        problem = self._get_problem_for_modify(pk, request.user)
        try:
            tag_id_int = int(tag_id)
        except (ValueError, TypeError):
            return api_response(None, "Invalid tag_id", status_code=400)
        tag = Tags.objects.filter(pk=tag_id_int).first()
        if not tag:
            return api_response(None, "Tag not found.", status_code=404)
        rel = Problem_tags.objects.filter(problem_id=problem, tag_id=tag).first()
        if not rel:
            return api_response(None, "Tag not attached to this problem.", status_code=404)
        from django.db.models import F
        rel.delete()
        Tags.objects.filter(pk=tag.pk).update(usage_count=F('usage_count') - 1)
        tag.refresh_from_db()
        return api_response({"tag": TagSerializer(tag).data}, "Tag removed", status_code=200)


class ProblemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return api_response({
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        }, "OK", status_code=200)


class ProblemListView(APIView):
    """
    GET /api/problem/ — 題目列表
    支援篩選: ?difficulty=easy&is_public=public|course|hidden&course_id=3
    支援分頁: ?page=1&page_size=20
    """
    permission_classes = []

    def get_permissions(self):
        # allow anonymous GET, but require teacher/admin for POST
        if getattr(self, 'request', None) is not None and self.request.method == 'POST':
            return [IsTeacherOrAdmin()]
        return []

    def get(self, request):
        queryset = Problems.objects.all().select_related('creator_id', 'course_id').prefetch_related('tags', 'subtasks')
        
        # 篩選：difficulty
        difficulty = request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 篩選：is_public
        visibility = request.query_params.get('is_public')
        if visibility in ('public','course','hidden'):
            queryset = queryset.filter(is_public=visibility)
        
        # 篩選：course_id（若帶入 course_id，需驗證課程成員或管理員/教師）
        course_id = request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            user = request.user
            # 未登入則不允許瀏覽特定課程的題目清單
            if not user.is_authenticated:
                return api_response(None, "Authentication required.", status_code=401)
            # 管理員/教師視為允許（沿用既有規則）
            is_staff_like = bool(getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False) or getattr(user, 'identity', None) in ['admin', 'teacher'])
            if not is_staff_like:
                try:
                    cid = int(course_id)
                except (TypeError, ValueError):
                    cid = None
                from courses.models import Course_members
                is_member = cid is not None and Course_members.objects.filter(course_id_id=cid, user_id=user).exists()
                if not is_member:
                    # 針對課程頁的題目列表，非成員一律擋下
                    return api_response(None, "You are not in this course.", status_code=403)
        
    # 權限過濾：未登入或非 owner/課程成員只能看 is_public=public
        user = request.user
        if not user.is_authenticated:
            # Fallback: treat legacy boolean true as public during migration window
            queryset = queryset.filter(is_public__in=['public', True, 1])
        elif not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']):
            # 普通使用者：只能看公開的 + 自己建的 + 所屬課程的
            from django.db.models import Q
            from courses.models import Course_members
            user_courses = Course_members.objects.filter(user_id=user).values_list('course_id', flat=True)
            queryset = queryset.filter(
                Q(is_public__in=['public', True, 1]) | Q(creator_id=user) | Q(is_public='course', course_id__in=user_courses)
            )
        
        # 排序
        ordering = request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        # 分頁
        paginator = ProblemPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ProblemSerializer(page, many=True)
            data = serializer.data
            # Inject per-user submit_count
            if request.user.is_authenticated:
                from submissions.models import Submission
                problem_ids = [item['id'] for item in data]
                user_submissions = Submission.objects.filter(
                    user=request.user, problem_id__in=problem_ids
                ).values_list('problem_id', flat=True)
                submit_counts = {}
                for pid in problem_ids:
                    submit_counts[pid] = list(user_submissions).count(pid)
                for item in data:
                    item['submit_count'] = submit_counts.get(item['id'], 0)
            return paginator.get_paginated_response(data)
        
        serializer = ProblemSerializer(queryset, many=True)
        data = serializer.data
        # Inject per-user submit_count
        if request.user.is_authenticated:
            from submissions.models import Submission
            problem_ids = [item['id'] for item in data]
            user_submissions = Submission.objects.filter(
                user=request.user, problem_id__in=problem_ids
            ).values_list('problem_id', flat=True)
            submit_counts = {}
            for pid in problem_ids:
                submit_counts[pid] = list(user_submissions).count(pid)
            for item in data:
                item['submit_count'] = submit_counts.get(item['id'], 0)
        return api_response(data, "OK", status_code=200)

    # 重要：不允許在 /problem/ 進行建立，統一走 /problem/manage
    # 若誤用 POST /problem/，回傳 405，請改用 /problem/manage
    def post(self, request):
        return api_response(None, "Method Not Allowed. Use POST /problem/manage to create.", status_code=405)


class ProblemDetailView(APIView):
    """GET /problem/<id> — 題目詳情（依產品需求格式）

    需求格式（回傳 data 內）：
      problemName: 題目名稱
      description: 聚合描述（description, input_description, output_description, hint, sample_input, sample_output）
      owner: { id, username, real_name }
      tags: [{ id, name, usage_count }]
      allowedLanguage: 位元遮罩（c=1, cpp=2, java=4, python=8，其餘延伸可再擴充）
      courses: [{ id, name }]
      quota: total_quota
      defaultCode: { language: code }（目前無資料以空字串占位）
      status: is_public
      type: 題目類型（目前模型無，預設 0；後續若加欄位可替換）
      testCase: 測試案例任務列表（若存在 zip：[{ no, stem, in, out }]）
      fillInTemplate: 僅 type=1 時提供，否則 null
      submitCount: 個人提交次數（若 submissions table 缺失或未登入則 null）
      highScore: 個人最高分（同上）

    權限：允許匿名存取公開題目；非公開題目與個人相關欄位（如 submitCount、highScore）於內部依題目可見性與使用者身分檢查。
    """

    permission_classes = []  # 允許匿名，實際權限在內部依題目可見性檢查

    LANGUAGE_BIT_MAP = {
        'c': 1,
        'cpp': 2,
        'java': 4,
        'python': 8,
    }

    def _language_mask(self, langs):
        mask = 0
        for l in langs or []:
            mask |= self.LANGUAGE_BIT_MAP.get(l, 0)
        return mask

    def _build_testcase_tasks(self, problem):
        from ..services.storage import _storage
        rel = os.path.join('testcases', f'p{problem.id}', 'problem.zip')
        if not _storage.exists(rel):
            return []
        try:
            with _storage.open(rel, 'rb') as fh:
                data = fh.read()
            from io import BytesIO
            import zipfile, os as _os
            buf = BytesIO(data)
            tasks = []
            with zipfile.ZipFile(buf) as zf:
                names = zf.namelist()
                ins = [n for n in names if n.endswith('.in')]
                outs = [n for n in names if n.endswith('.out')]
                def stem(n):
                    b = _os.path.basename(n)
                    return _os.path.splitext(b)[0]
                in_map = {stem(n): n for n in ins}
                out_map = {stem(n): n for n in outs}
                all_stems = sorted(set(list(in_map.keys()) + list(out_map.keys())))
                for idx, s in enumerate(all_stems, start=1):
                    tasks.append({
                        'no': idx,
                        'stem': s,
                        'in': in_map.get(s),
                        'out': out_map.get(s),
                    })
            return tasks
        except Exception:
            return []

    def get(self, request, pk):
        try:
            problem = Problems.objects.select_related('creator_id', 'course_id').prefetch_related('tags').get(pk=pk)
        except Problems.DoesNotExist:
            return api_response(None, "Problem not found.", status_code=404)

        user = request.user

        # 權限：公開題目開放；course/hidden 需符合既有規則
        visibility = getattr(problem, 'is_public', 'hidden')
        legacy_public = visibility in (True, 1)
        visibility_normalized = 'public' if legacy_public else visibility
        if visibility_normalized not in ('public'):
            if not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher'] or problem.creator_id == user):
                if visibility_normalized == 'course' and problem.course_id:
                    from courses.models import Course_members
                    is_course_member = Course_members.objects.filter(course_id=problem.course_id, user_id=user).exists()
                    if not is_course_member:
                        return api_response(None, "Not enough permission", status_code=403)
                else:
                    return api_response(None, "Not enough permission", status_code=403)

        # 聚合描述
        # 將 sampleInput / sampleOutput 轉成陣列：依換行分割，空白行略過；若原始為空字串返回 []
        def _to_list(text: str):
            if not text or not str(text).strip():
                return []
            return [line for line in str(text).splitlines() if line.strip()]

        description_block = {
            'description': problem.description,
            'input': getattr(problem, 'input_description', ''),
            'output': getattr(problem, 'output_description', ''),
            'hint': getattr(problem, 'hint', ''),
            'sampleInput': _to_list(getattr(problem, 'sample_input', '')),
            'sampleOutput': _to_list(getattr(problem, 'sample_output', '')),
        }

        # 語言遮罩
        allowed_lang_mask = self._language_mask(getattr(problem, 'supported_languages', []))

        # tags
        tags_data = [
            {'id': t.id, 'name': t.name, 'usage_count': getattr(t, 'usage_count', 0)}
            for t in problem.tags.all()
        ]

        # course list（目前單一課程，仍以陣列呈現）
        courses_data = []
        if problem.course_id:
            courses_data.append({'id': problem.course_id_id, 'name': getattr(problem.course_id, 'name', '')})

        # 預設程式碼（占位）
        default_code = {lang: '' for lang in getattr(problem, 'supported_languages', [])}

        # 題目類型（尚未有欄位，先給 0）
        problem_type = getattr(problem, 'problem_type', 0) or 0
        fill_in_template = None if problem_type != 1 else getattr(problem, 'fill_in_template', '')

        # 測試案例（若 zip 存在）
        test_case_tasks = self._build_testcase_tasks(problem)

        # 個人統計（若 Submission table 存在）
        submit_count = None
        high_score = None
        from django.db.utils import OperationalError
        try:
            if user.is_authenticated:
                from submissions.models import Submission  # Lazy import 防止遷移缺失崩潰
                agg = Submission.objects.filter(problem_id=problem.id, user=user).aggregate(
                    submit_count=Count('id'), high_score=Max('score')
                )
                submit_count = agg.get('submit_count') or 0
                high_score = agg.get('high_score') or 0
        except OperationalError:
            # 資料表缺失時保持 null，避免 500
            pass

        data = {
            'problemName': problem.title,
            'description': description_block,
            'owner': {
                'id': problem.creator_id_id,
                'username': getattr(problem.creator_id, 'username', ''),
                'real_name': getattr(problem.creator_id, 'real_name', ''),
            },
            'tags': tags_data,
            'allowedLanguage': allowed_lang_mask,
            'courses': courses_data,
            'quota': getattr(problem, 'total_quota', -1),
            'defaultCode': default_code,
            'status': visibility_normalized,
            'type': problem_type,
            'testCase': test_case_tasks,
            'fillInTemplate': fill_in_template,
            'submitCount': submit_count,
            'highScore': high_score,
            'subtaskDescription': getattr(problem, 'subtask_description', ''),
            # Custom checker settings
            'use_custom_checker': getattr(problem, 'use_custom_checker', False),
            'checker_name': getattr(problem, 'checker_name', 'diff'),
            # Static analysis settings
            'static_analysis_rules': getattr(problem, 'static_analysis_rules', []),
            'forbidden_functions': getattr(problem, 'forbidden_functions', []),
            'use_static_analysis': getattr(problem, 'use_static_analysis', False),
            'static_analysis_config': problem.get_static_analysis_config() if hasattr(problem, 'get_static_analysis_config') else {'enabled': False},
        }

        return api_response(data, "Problem can view.", status_code=200)


import math

class ProblemStatsView(APIView):
    """
    GET /problem/<id>/stats — 題目統計資訊
    權限：需要登入
    回傳：AC 用戶、嘗試用戶、平均分數、標準差、分數分布、狀態統計、top10執行時間/記憶體
    """

    def get(self, request, pk):
        # Defensive: some dependent apps/tables may be missing while local migrations are being fixed.
        # Wrap DB access in OperationalError to return a clear 503 instead of crashing the server.
        from django.db.utils import OperationalError
        try:
            from courses.models import Course_members
            from submissions.models import Submission

            # 1. 題目存在性
            try:
                problem = Problems.objects.get(pk=pk)
            except Problems.DoesNotExist:
                return api_response(None, "Problem not found.", status_code=404)

            # 2. 總學生數（該課程所有學生）
            course_id = getattr(problem, 'course_id', None)
            total_students = 0
            if course_id:
                total_students = Course_members.objects.filter(course_id=course_id, role='student').count()

            # 3. 所有提交
            submissions = Submission.objects.filter(problem_id=pk)

            # 4. 嘗試過的用戶數（distinct count 避免載入整批資料）
            tried_user_count = submissions.values('user').distinct().count()

            # 5. AC 用戶數
            # Submission.status 以 NOJ 代碼字串儲存，AC 為 '0'
            ac_user_count = submissions.filter(status='0').values('user').distinct().count()

            # 6. 分數統計
            scores = list(submissions.values_list('score', flat=True))
            average = sum(scores) / len(scores) if scores else 0
            std = math.sqrt(sum((s - average) ** 2 for s in scores) / len(scores)) if scores else 0

            # 7. 分數分布
            score_distribution = {}
            for s in scores:
                score_distribution[s] = score_distribution.get(s, 0) + 1
            score_distribution = [ {'score': k, 'count': v} for k, v in sorted(score_distribution.items()) ]

            # 8. 狀態統計
            status_count = {}
            for row in submissions.values('status').annotate(cnt=Count('id')):
                status_count[row['status']] = row['cnt']

            # 9. top10執行時間（含使用者 username，方便前端顯示）
            runtime_qs = submissions.filter(execution_time__gt=0).select_related('user').order_by('execution_time')[:10]
            top10_runtime = [
                {
                    'id': s.id,
                    'user': s.user_id,
                    'username': getattr(s.user, 'username', ''),
                    'execution_time': s.execution_time,
                    'score': s.score,
                    'status': s.status,
                }
                for s in runtime_qs
            ]

            # 10. top10記憶體（含使用者 username）
            memory_qs = submissions.filter(memory_usage__gt=0).select_related('user').order_by('memory_usage')[:10]
            top10_memory = [
                {
                    'id': s.id,
                    'user': s.user_id,
                    'username': getattr(s.user, 'username', ''),
                    'memory_usage': s.memory_usage,
                    'score': s.score,
                    'status': s.status,
                }
                for s in memory_qs
            ]

            return api_response({
                "acUserRatio": [ac_user_count, total_students],
                "triedUserCount": tried_user_count,
                "average": average,
                "std": std,
                "scoreDistribution": score_distribution,
                "statusCount": status_count,
                "top10RunTime": top10_runtime,
                "top10MemoryUsage": top10_memory,
            }, "OK", status_code=200)
        except OperationalError as e:
            # Helpful diagnostic for local dev when migrations/tables are missing
            return api_response({"error": str(e)}, "Service temporarily unavailable: dependent database tables appear to be missing.", status_code=503)

class ProblemHighScoreView(APIView):
    """
    GET /api/problem/<id>/high-score — 取得使用者在該題目的最高分數
    需要登入；回傳該使用者在此題的最高分
    """

    def get(self, request, pk):
        try:
            problem = Problems.objects.get(pk=pk)
        except Problems.DoesNotExist:
            return api_response(None, "Problem not found.", status_code=404)
        
        user = request.user
        high_score = Submission.objects.filter(
            problem_id=problem.id,
            user=user
        ).aggregate(high_score=Max('score')).get('high_score')
        
        # 若從未提交過，回傳 0
        if high_score is None:
            high_score = 0
        
        return api_response({"score": high_score}, "OK", status_code=200)


class ProblemManageView(APIView):
    """
    POST /api/problem/manage — 建立題目（僅 admin/teacher）
    """
    # 允許已登入；實際權限在 post() 內判斷：
    # admin/teacher 直接允許；否則需為該 course 的 TA

    def post(self, request):
        serializer = ProblemSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return api_response({"errors": serializer.errors}, "Validation error", status_code=422)

        # 權限檢查：
        user = request.user
        is_admin_teacher = bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or getattr(user, "identity", None) in ["admin", "teacher"]
        )

        course_obj = serializer.validated_data.get("course_id")
        if not is_admin_teacher:
            # 必須是該課程 TA 才能出題
            from courses.models import Course_members
            is_course_ta = Course_members.objects.filter(
                course_id=course_obj,
                user_id=user,
                role='ta',
            ).exists()
            if not is_course_ta:
                return api_response(None, "Not enough permission: need admin/teacher or TA of the course.", status_code=403)

        # 嚴格驗證 tags（若提供）
        tags_data = request.data.get('tags')
        tag_ids = []
        if tags_data is not None:
            if isinstance(tags_data, (list, tuple)):
                for v in tags_data:
                    try:
                        tag_ids.append(int(v))
                    except (ValueError, TypeError):
                        return api_response({"tags": f"Invalid tag id: {v}"}, "Validation error", status_code=400)

                from ..models import Tags
                existing_ids = set(Tags.objects.filter(id__in=tag_ids).values_list('id', flat=True))
                missing_ids = [tid for tid in tag_ids if tid not in existing_ids]
                if missing_ids:
                    return api_response({"errors": {"tags": f"Tag IDs do not exist: {missing_ids}"}}, "Validation error", status_code=400)

        problem = serializer.save(creator_id=request.user)

        # 綁定已驗證之 tags
        if tags_data is not None:
            from ..models import Tags
            tags_qs = Tags.objects.filter(id__in=tag_ids)
            problem.tags.set(tags_qs)

        return api_response({"problem_id": problem.id}, "題目建立成功", status_code=201)


class ProblemCloneView(APIView):
    """POST /problem/clone - 複製題目

    Body JSON:
      - problem_id (int): 要複製的題目 ID
      - target (string): 目標課程名稱
      - status (optional int): 新題目狀態（0: hidden, 1: course, 2: public）

    需要管理員或教師（含該課程 TA）權限。
    回傳：
      - 200: { message: "Success.", data: { problemId: 新題目ID } }
      - 403: { message: "Problem can not view." }
    """

    def post(self, request):
        user = request.user
        payload = request.data or {}
        problem_id = payload.get("problem_id")
        target_name = payload.get("target")
        new_status_raw = payload.get("status")
        dry_run = payload.get("dry_run", False)

        if not problem_id or not target_name:
            return api_response(None, "Missing required fields: problem_id, target", status_code=400)

        try:
            src = Problems.objects.select_related("course_id", "creator_id").get(pk=int(problem_id))
        except (Problems.DoesNotExist, ValueError, TypeError):
            return api_response(None, "Problem not found", status_code=404)

        # 檢查是否有權限檢視來源題目
        if user.is_staff or getattr(user, 'is_superuser', False):
            can_view = True
        else:
            vis = src.is_public
            if vis == Problems.Visibility.PUBLIC:
                can_view = True
            elif vis == Problems.Visibility.COURSE:
                can_view = Course_members.objects.filter(course_id=src.course_id, user_id=user).exists()
            else:
                can_view = (src.creator_id_id == user.id)
        if not can_view:
            return api_response(None, "Problem can not view.", status_code=403)

        # 目標課程查詢（以名稱）
        try:
            target_course = Courses.objects.get(name=target_name)
        except Courses.DoesNotExist:
            return api_response(None, "Target course not found", status_code=404)

        # 權限：管理員或目標課程教師/TA
        if not (user.is_staff or getattr(user, 'is_superuser', False)):
            qs = Course_members.objects.filter(course_id=target_course, user_id=user)
            is_teacher = qs.filter(role=Course_members.Role.TEACHER).exists() or (target_course.teacher_id_id == user.id)
            is_ta = qs.filter(role=Course_members.Role.TA).exists()
            if not (is_teacher or is_ta):
                return api_response(None, "Permission denied", status_code=403)

        # 狀態映射：接受數字 0/1/2 或字串 "hidden"/"course"/"public"
        visibility_map_int = {0: Problems.Visibility.HIDDEN, 1: Problems.Visibility.COURSE, 2: Problems.Visibility.PUBLIC}
        visibility_map_str = {
            "hidden": Problems.Visibility.HIDDEN,
            "course": Problems.Visibility.COURSE,
            "public": Problems.Visibility.PUBLIC,
        }
        if new_status_raw is None:
            new_visibility = src.is_public
        else:
            if isinstance(new_status_raw, str):
                new_visibility = visibility_map_str.get(new_status_raw.lower(), src.is_public)
            else:
                try:
                    new_visibility = visibility_map_int.get(int(new_status_raw), src.is_public)
                except (ValueError, TypeError):
                    new_visibility = src.is_public

        # 建立新題目（統計歸零）
        # 注意：部分環境下 request.user.id 可能為非整數（例如 UUID 字串），
        # 而 Problems.creator_id 的 FK 目標 PK 為整數，直接指定可能造成型別錯誤。
        # 為避免 500 錯誤，這裡沿用來源題目的 creator 作為新題目的建立者。
        # 若日後要改為目前使用者，可在確認 User PK 型別相容後再調整。
        new_problem = Problems.objects.create(
            title=src.title,
            difficulty=src.difficulty,
            max_score=src.max_score,
            is_public=new_visibility,
            total_submissions=0,
            accepted_submissions=0,
            acceptance_rate=0,
            like_count=0,
            view_count=0,
            total_quota=src.total_quota,
            description=src.description,
            input_description=src.input_description,
            output_description=src.output_description,
            sample_input=src.sample_input,
            sample_output=src.sample_output,
            hint=src.hint,
            subtask_description=src.subtask_description,
            supported_languages=src.supported_languages,
            # 明確指定 FK 原始 id，避免 ORM 嘗試型別轉換造成錯誤
            creator_id_id=src.creator_id_id,
            course_id_id=target_course.id,
        )

        # 僅建立 Problems，本次請求不複製關聯資料，用於隔離與定位問題
        if dry_run:
            return api_response({"problemId": new_problem.id}, "Success (dry_run: only problem created).", status_code=200)

        # 複製 tags（使用 *_id 明確指定原始型別，避免不必要的型別轉換）
        tag_ids = list(src.tags.values_list('id', flat=True))
        for tid in tag_ids:
            Problem_tags.objects.get_or_create(
                problem_id_id=new_problem.id,
                tag_id_id=tid,
                defaults={"added_by_id": user.id},
            )

        # 複製 subtasks + test cases（同樣以 *_id 指派 FK）
        for st in Problem_subtasks.objects.filter(problem_id=src).order_by('subtask_no'):
            new_st = Problem_subtasks.objects.create(
                problem_id_id=new_problem.id,
                subtask_no=st.subtask_no,
                weight=st.weight,
                time_limit_ms=st.time_limit_ms,
                memory_limit_mb=st.memory_limit_mb,
            )
            tcs = Test_cases.objects.filter(subtask_id=st).order_by('idx')
            bulk = []
            for tc in tcs:
                bulk.append(Test_cases(
                    subtask_id_id=new_st.id,
                    idx=tc.idx,
                    input_path=tc.input_path,
                    output_path=tc.output_path,
                    input_size=tc.input_size,
                    output_size=tc.output_size,
                    checksum_in=tc.checksum_in,
                    checksum_out=tc.checksum_out,
                    status=tc.status,
                ))
            if bulk:
                Test_cases.objects.bulk_create(bulk)

        return api_response({"problemId": new_problem.id}, "Success.", status_code=200)


@api_view(['POST', 'DELETE'])
def problem_like_toggle(request, pk):
    """POST /problem/<id>/like - 按讚
    DELETE /problem/<id>/like - 取消按讚
    """
    try:
        problem = Problems.objects.get(pk=pk)
    except Problems.DoesNotExist:
        return api_response(None, "Problem not found.", status_code=404)

    user = request.user

    try:
        with transaction.atomic():
            existing = ProblemLike.objects.filter(problem=problem, user=user).first()

            if request.method == 'POST':
                if existing:
                    return api_response(None, "You already liked this problem.", status_code=400)
                ProblemLike.objects.create(problem=problem, user=user)
                # update counter
                Problems.objects.filter(pk=pk).update(like_count=dj_models.F('like_count') + 1)
                problem.refresh_from_db()
                return api_response({"likes_count": problem.like_count}, "Liked", status_code=201)

            # method == DELETE
            if not existing:
                return api_response(None, "You have not liked this problem.", status_code=400)
            existing.delete()
            Problems.objects.filter(pk=pk).update(like_count=dj_models.F('like_count') - 1)
            problem.refresh_from_db()
            return api_response({"likes_count": problem.like_count}, "Unliked", status_code=200)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"problem_like_toggle failed: {e}", exc_info=True)
        return api_response(None, "Operation failed", status_code=500)


@api_view(['GET'])
def problem_likes_count(request, pk):
    """GET /problem/<id>/likes - 取得點讚數（簡單回傳 like_count）"""
    try:
        problem = Problems.objects.get(pk=pk)
    except Problems.DoesNotExist:
        return api_response(None, "Problem not found.", status_code=404)
    return api_response({"likes_count": problem.like_count}, "OK", status_code=200)


class UserLikedProblemsView(generics.ListAPIView):
    """GET /user/likes - 列出已按讚的題目（需登入）"""
    serializer_class = ProblemStudentSerializer
    pagination_class = ProblemPagination

    def get_queryset(self):
        user = self.request.user
        liked_ids = ProblemLike.objects.filter(user=user).values_list('problem', flat=True)
        return Problems.objects.filter(id__in=liked_ids).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # pagination_class.get_paginated_response already wraps
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(serializer.data, "OK", status_code=200)


# PUT/DELETE /api/problem/manage/<id> — 修改/刪除題目
# GET /api/problem/manage/<id> — 管理員視角題目詳情
class ProblemManageDetailView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get_object_for_modify(self, pk, user):
        """用於 PUT/DELETE，檢查修改/刪除權限。
        規則：
        - Admin（is_superuser/is_staff 或 identity=admin）可直接操作任何題目
        - 題目擁有者可操作
        - 課程 TA/teacher 可操作
        """
        problem = get_object_or_404(Problems, pk=pk)
        # Admin 最高權限：允許直接修改/刪除
        if (
            getattr(user, 'is_superuser', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'identity', None) == 'admin'
        ):
            return problem
        
        if problem.creator_id == user:
            return problem
        
        if problem.course_id:
            from courses.models import Course_members
            is_course_staff = Course_members.objects.filter(
                course_id=problem.course_id,
                user_id=user,
                role__in=['ta', 'teacher']
            ).exists()
            if is_course_staff:
                return problem
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Only admin, the problem owner, or course TA/teacher can modify or delete this problem.")

    def get(self, request, pk):
        """
        GET /api/problem/manage/<id> — 管理員視角的題目詳情
        回傳：完整測試案例 + 統計資訊（ACUser, submitter）
        權限：Teacher/Admin 可看全部；或是 owner/課程 TA
        """
        try:
            problem = Problems.objects.select_related('creator_id', 'course_id').prefetch_related(
                'tags', 'subtasks__test_cases'
            ).get(pk=pk)
        except Problems.DoesNotExist:
            return api_response(None, "Problem not found.", status_code=404)
        
        # 權限檢查：admin/teacher 可看全部
        user = request.user
        if not (user.is_staff or user.is_superuser or getattr(user, 'identity', None) in ['admin', 'teacher']):
            # 不是 admin/teacher，檢查是否為 owner 或課程 TA
            if problem.creator_id != user:
                if problem.course_id:
                    from courses.models import Course_members
                    is_course_staff = Course_members.objects.filter(
                        course_id=problem.course_id,
                        user_id=user,
                        role__in=['ta', 'teacher']
                    ).exists()
                    if not is_course_staff:
                        return api_response(None, "Not enough permission", status_code=403)
                else:
                    return api_response(None, "Not enough permission", status_code=403)
        
        # 使用完整版 serializer
        serializer = ProblemDetailSerializer(problem)
        data = serializer.data 
        data['ac_user_count'] = 0  # 暫時預設值
        data['submitter_count'] = 0
        data['can_view_stdout'] = True  # 預設值，可從 settings 或題目設定讀取
        return api_response(data, "取得題目（管理）成功", status_code=200)

    @transaction.atomic
    def put(self, request, pk):
        problem = self.get_object_for_modify(pk, request.user)
        serializer = ProblemSerializer(problem, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            return api_response({"errors": serializer.errors}, "Validation error", status_code=422)
        
        # Extract and validate tags before saving
        tags_data = request.data.get('tags')
        tag_ids = []
        if tags_data is not None:
            if isinstance(tags_data, (list, tuple)):
                for v in tags_data:
                    try:
                        tag_ids.append(int(v))
                    except (ValueError, TypeError):
                        return api_response({"errors": {"tags": f"Invalid tag id: {v}"}}, "Validation error", status_code=400)
                
                # Strict validation: all tag ids must exist
                from ..models import Tags
                existing_tags = Tags.objects.filter(id__in=tag_ids)
                existing_ids = set(existing_tags.values_list('id', flat=True))
                missing_ids = [tid for tid in tag_ids if tid not in existing_ids]
                if missing_ids:
                    return api_response({"tags": f"Tag IDs do not exist: {missing_ids}"}, "Validation error", status_code=400)
        
        serializer.save(creator_id=problem.creator_id)  # 保留 owner
        
        # Update tags if provided
        if tags_data is not None:
            from ..models import Tags
            tags_qs = Tags.objects.filter(id__in=tag_ids)
            problem.tags.set(tags_qs)
        
        return api_response({"problem_id": problem.id}, "題目更新成功", status_code=200)

    @transaction.atomic
    def delete(self, request, pk):
        problem = self.get_object_for_modify(pk, request.user)
        problem.delete()
        return api_response(None, "題目刪除成功", status_code=204)
