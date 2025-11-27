# assignments/views.py
from typing import List
from django.db import transaction
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions
from django.db.models import Sum, Count, Max, Q
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone

from assignments.models import Assignments, Assignment_problems
from courses.models import Courses, Course_members
from problems.models import Problems
from submissions.models import UserProblemStats
from .serializers import (
    HomeworkCreateSerializer,
    HomeworkDetailSerializer,
    HomeworkUpdateSerializer,
    AddProblemsInSerializer,
    make_list_item_from_instance,
    HomeworkScoreboardSerializer,
)

# --------- 權限 & 工具 ---------
def is_teacher_or_ta(user, course) -> bool:
    if getattr(course, "teacher_id_id", None) == user.id or getattr(course, "teacher_id", None) == user:
        return True
    return Course_members.objects.filter(
        course_id=course, user_id=user, role=Course_members.Role.TA
    ).exists()

def collect_problem_ids(hw: Assignments) -> List[int]:
    return list(
        hw.assignment_problems.order_by("order_index").values_list("problem_id", flat=True)
    )

def api_response(data=None, message="OK", status_code=status.HTTP_200_OK):
    """
    統一 API 回傳格式：
    {
      "data": <payload>,
      "message": "給人看的訊息",
      "status": "ok" | "error"
    }
    """
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response(
        {
            "data": data,
            "message": message,
            "status": status_str,
        },
        status=status_code,
    )

# --------- POST /homework/ ---------
class HomeworkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        ser = HomeworkCreateSerializer(data=request.data)
        try:
            ser.is_valid(raise_exception=True)
        except Exception as e:
            if isinstance(getattr(e, "detail", None), str) and str(e.detail) == "homework exists in this course":
                return Response("homework exists in this course", status=status.HTTP_400_BAD_REQUEST)
            raise

        course = ser.validated_data["_course"]
        if not is_teacher_or_ta(request.user, course):
            return Response(
                "user must be the teacher or ta of this course",
                status=status.HTTP_403_FORBIDDEN,
            )

        hw = Assignments.objects.create(
            title=ser.validated_data["name"],
            description=ser.validated_data.get("markdown", "") or "",
            course=course,
            creator=request.user,
            start_time=ser.validated_data.get("_start_dt"),
            due_time=ser.validated_data.get("_end_dt"),
        )

        pids = ser.validated_data.get("problem_ids", [])
        for idx, pid in enumerate(pids, start=1):
            Assignment_problems.objects.create(
                assignment=hw,
                problem_id=pid,
                order_index=idx,
                weight="1.00",
                special_judge=False,
            )

        return Response("Add homework Success", status=status.HTTP_200_OK)

# --------- GET/PUT/DELETE /homework/<id> ---------
class HomeworkDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_hw(self, pk: int) -> Assignments:
        try:
            return Assignments.objects.select_related("course").get(pk=pk)
        except Assignments.DoesNotExist:
            raise Http404

    def get(self, request, homework_id: int):
        hw = self._get_hw(homework_id)
        probs = collect_problem_ids(hw)
        status_flag = is_teacher_or_ta(request.user, hw.course)
        data = HomeworkDetailSerializer.from_instance(hw, probs, status_flag, penalty_text="")
        return Response(data, status=status.HTTP_200_OK)

    @transaction.atomic
    def put(self, request, homework_id: int):
        hw = self._get_hw(homework_id)
        if not is_teacher_or_ta(request.user, hw.course):
            return Response("user must be the teacher or ta of this course", status=status.HTTP_403_FORBIDDEN)

        ser = HomeworkUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        new_name = ser.validated_data.get("name", None)
        if new_name and Assignments.objects.filter(course=hw.course, title=new_name).exclude(pk=hw.pk).exists():
            return Response("homework exists in this course", status=status.HTTP_400_BAD_REQUEST)

        if new_name is not None:
            hw.title = new_name
        if "markdown" in ser.validated_data:
            hw.description = ser.validated_data.get("markdown") or ""
        if "_start_dt" in ser.validated_data:
            hw.start_time = ser.validated_data["_start_dt"]
        if "_end_dt" in ser.validated_data:
            hw.due_time = ser.validated_data["_end_dt"]
        hw.save()

        if "problem_ids" in ser.validated_data:
            pids = ser.validated_data.get("problem_ids") or []
            hw.assignment_problems.all().delete()
            for idx, pid in enumerate(pids, start=1):
                Assignment_problems.objects.create(
                    assignment=hw,
                    problem_id=pid,
                    order_index=idx,
                    weight="1.00",
                    special_judge=False,
                )

        return Response("Update homework Success", status=status.HTTP_200_OK)

    @transaction.atomic
    def delete(self, request, homework_id: int):
        hw = self._get_hw(homework_id)
        if not is_teacher_or_ta(request.user, hw.course):
            return Response("user must be the teacher or ta of this course", status=status.HTTP_403_FORBIDDEN)
        hw.delete()
        return Response("Delete homework Success", status=status.HTTP_200_OK)

# --------- NEW: GET /course/<course_name>/homework ---------
class CourseHomeworkListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        try:
            course = Courses.objects.get(pk=course_id)  # UUID or int 都能吃
        except Courses.DoesNotExist:
            return Response("course not exists", status=status.HTTP_404_NOT_FOUND)

        is_staff_like = is_teacher_or_ta(request.user, course)

        # 取該課程所有作業
        homeworks = (
            Assignments.objects.filter(course=course)
            .prefetch_related("assignment_problems")
            .order_by("-created_at", "id")
        )

        items = []
        for hw in homeworks:
            pids = collect_problem_ids(hw)
            items.append(
                make_list_item_from_instance(hw, pids, is_staff_like, penalty_text="")
            )

        payload = {"message": "get homeworks", "items": items}
        # 若要嚴格 schema，也可透過 HomeworkListResponseSerializer(payload).data 驗證
        return Response(payload, status=status.HTTP_200_OK)
class AddProblemsToHomeworkView(APIView):
    """
    POST /homework/{id}/problems — 新增題目到作業
    權限：需為該課程教師或 TA
    輸入：
      - 其一：
        {"problem_ids":[1,2,3]}
      - 或：
        {"problems":[{"id":1,"weight":1.2,"special_judge":true,"order_index":3}, ...]}
    行為：
      - 跳過已存在於該作業的題目（不報錯）
      - 未提供 order_index 時，依現有最大 order_index 之後遞增
      - 欄位缺省時使用預設：weight=1.00, special_judge=False, time_limit/memory_limit/attempt_quota=None
    回傳：
      200: "Add problems Success"
      403: "user must be the teacher or ta of this course"
      404: "homework not exists"
      400: 參數錯誤（如題目皆不存在）
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, homework_id: int):
        # 1) 找作業
        try:
            hw = Assignments.objects.select_related("course").get(pk=homework_id)
        except Assignments.DoesNotExist:
            return Response("homework not exists", status=status.HTTP_404_NOT_FOUND)

        # 2) 權限
        if not is_teacher_or_ta(request.user, hw.course):
            return Response(
                "user must be the teacher or ta of this course",
                status=status.HTTP_403_FORBIDDEN,
            )

        # 3) 解析輸入
        ser = AddProblemsInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        # 將兩種格式合併為統一列表 items: [{id, weight?, special_judge?, time_limit?, memory_limit?, attempt_quota?, order_index?}]
        items = []
        if "problems" in payload:
            items = payload["problems"]
        else:
            # 只有 problem_ids
            items = [{"id": pid} for pid in payload["problem_ids"]]

        if not items:
            return Response("no problems provided", status=status.HTTP_400_BAD_REQUEST)

        # 4) 取出實際存在的 Problems
        ids = [it["id"] for it in items]
        found = {p.id: p for p in Problems.objects.filter(id__in=ids)}
        if len(found) == 0:
            # 全部都不存在
            not_found = [pid for pid in ids if pid not in found]
            return Response(
                {"message": "no valid problems", "not_found": not_found},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5) 現有最大 order_index
        current_max_idx = (
            Assignment_problems.objects.filter(assignment=hw).aggregate(
                m=Max("order_index")
            )["m"]
            or 0
        )

        # 6) 過濾已存在的 pair（assignment, problem）
        existing_problem_ids = set(
            Assignment_problems.objects.filter(
                assignment=hw, problem_id__in=list(found.keys())
            ).values_list("problem_id", flat=True)
        )

        to_create = []
        skipped_existing = []
        # 先建一個 map 讓 dict 內容可查
        by_id = {}
        for it in items:
            if it["id"] not in by_id:
                by_id[it["id"]] = it  # 相同 id 後來者覆蓋前者（去重）

        # 7) 準備 bulk_create 資料
        next_index = current_max_idx
        for pid, it in by_id.items():
            if pid in existing_problem_ids:
                skipped_existing.append(pid)
                continue

            next_index = it.get("order_index") or (next_index + 1)

            to_create.append(
                Assignment_problems(
                    assignment=hw,
                    problem=found[pid],
                    order_index=next_index,
                    weight=it.get("weight", Decimal("1.00")),
                    special_judge=it.get("special_judge", False),
                    time_limit=it.get("time_limit"),
                    memory_limit=it.get("memory_limit"),
                    attempt_quota=it.get("attempt_quota"),
                    is_active=True,
                    partial_score=True,
                    hint_text="",
                )
            )

        # 8) 寫入
        with transaction.atomic():
            if to_create:
                Assignment_problems.objects.bulk_create(to_create)

        # 9) 回傳結果
        return Response("Add problems Success", status=status.HTTP_200_OK)

# --------- GET /homework/<id>/scoreboard ---------
class HomeworkScoreboardView(APIView):
    """
    GET /homework/{id}/scoreboard
    回傳作業排行榜，欄位名稱對齊 DB spec：
    - assignment_id, title, course_id
    - items[]:
        - rank, user_id, username, real_name
        - total_score, max_total_score, is_late
        - first_ac_time, last_submission_time
        - problems[]: problem_id, best_score, max_possible_score, solve_status
    """
    permission_classes = [IsAuthenticated]

    def _get_assignment(self, homework_id: int) -> Assignments:
        return get_object_or_404(
            Assignments.objects.select_related("course"),
            pk=homework_id,
        )

    def get(self, request, homework_id: int):
        assignment = self._get_assignment(homework_id)

        # 1. 取出這份作業的所有題目統計 (UserProblemStats)
        stats_qs = (
            UserProblemStats.objects
            .filter(assignment_id=assignment.id)
            .select_related("user")
            .order_by("user__username", "problem_id")
        )

        # 2. 依 user 聚合
        per_user = {}

        for s in stats_qs:
            uid = s.user_id
            if uid not in per_user:
                per_user[uid] = {
                    "user": s.user,
                    "total_score": 0,
                    "max_total_score": 0,
                    "is_late": False,
                    "first_ac_time": None,
                    "last_submission_time": None,
                    "problems": [],
                }

            row = per_user[uid]

            # 累積作業總分 / 總滿分
            row["total_score"] += s.best_score
            row["max_total_score"] += s.max_possible_score

            # 是否曾經晚交
            row["is_late"] = row["is_late"] or s.is_late

            # 最早 AC 時間
            if s.first_ac_time:
                if (
                    row["first_ac_time"] is None
                    or s.first_ac_time < row["first_ac_time"]
                ):
                    row["first_ac_time"] = s.first_ac_time

            # 最晚提交時間
            if s.last_submission_time:
                if (
                    row["last_submission_time"] is None
                    or s.last_submission_time > row["last_submission_time"]
                ):
                    row["last_submission_time"] = s.last_submission_time

            # 單題資訊
            row["problems"].append(
                {
                    "problem_id": s.problem_id,
                    "best_score": s.best_score,
                    "max_possible_score": s.max_possible_score,
                    "solve_status": s.solve_status,
                }
            )

        # 3. 變成 list，並排序 + 計算 rank
        rows = []
        for uid, agg in per_user.items():
            user: User = agg["user"]
            rows.append(
                {
                    # user 資訊：對齊 Users table
                    "user_id": user.id,
                    "username": user.username,
                    "real_name": getattr(user, "real_name", ""),

                    # scoreboard 統計欄位
                    "total_score": agg["total_score"],
                    "max_total_score": agg["max_total_score"],
                    "is_late": agg["is_late"],
                    "first_ac_time": agg["first_ac_time"],
                    "last_submission_time": agg["last_submission_time"],
                    "problems": agg["problems"],
                }
            )

        # 排序：總分 ↓，再最早 AC ↑，再 username
        def sort_key(r):
            # 沒有 first_ac_time 的當成「很晚」
            max_dt = timezone.datetime.max.replace(tzinfo=timezone.utc)
            first_ac = r["first_ac_time"] or max_dt
            return (-r["total_score"], first_ac, r["username"])

        rows.sort(key=sort_key)

        # 加 rank
        current_rank = 1
        last_score = None
        last_rank = 1
        for row in rows:
            if last_score is None or row["total_score"] != last_score:
                last_rank = current_rank
                last_score = row["total_score"]
            row["rank"] = last_rank
            current_rank += 1

        # 4. 組 payload：欄位名稱對齊 Assignments / Courses
        payload = {
            "assignment_id": assignment.id,
            "title": assignment.title,
            "course_id": assignment.course_id,  # 這裡會是 UUID(primary key)
            "items": rows,
        }

        serializer = HomeworkScoreboardSerializer(payload)
        return api_response(
            data=serializer.data,
            message="get homework scoreboard",
            status_code=200,
        )