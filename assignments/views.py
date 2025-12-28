# assignments/views.py
from typing import List
from django.db import transaction
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Max,Sum
from django.db.models import Sum, Count, Max, Q
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from collections import defaultdict
from .serializers import to_epoch_from_dt
import datetime

from assignments.models import Assignments, Assignment_problems
from courses.models import Courses, Course_members
from problems.models import Problems
from submissions.models import UserProblemStats 
from submissions.models import Submission
from .serializers import (
    HomeworkCreateSerializer,
    HomeworkDetailSerializer,
    HomeworkUpdateSerializer,
    AddProblemsInSerializer,
    HomeworkSubmissionListItemSerializer,
    make_list_item_from_instance,
    HomeworkDeadlineSerializer,
    HomeworkStatsSerializer,
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
def is_course_member(user, course) -> bool:
    """
    判斷使用者是否為該課程成員（學生 / TA / 老師都算）
    """
    return Course_members.objects.filter(course_id=course, user_id=user).exists()
def require_course_member_or_staff(request_user, course):
    """
    規則：
      - teacher/TA：放行
      - 其他：必須是 course member 才放行
    回傳：
      - None 代表放行
      - Response(api_response) 代表拒絕
    """
    if is_teacher_or_ta(request_user, course):
        return None
    if is_course_member(request_user, course):
        return None
    return api_response(
        data=None,
        message="permission denied: user is not a member of this course",
        status_code=status.HTTP_403_FORBIDDEN,
    )

# --------- 統一回傳格式 ---------
def api_response(data=None, message="OK", status_code=200):
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
    def _get_hw(self, pk: int) -> Assignments:
        try:
            return Assignments.objects.select_related("course").get(pk=pk)
        except Assignments.DoesNotExist:
            raise Http404

    def get(self, request, homework_id: int):
        hw = self._get_hw(homework_id)
        course = hw.course

        # 權限：至少要是課程成員（學生/TA/老師都算）
        if not is_course_member(request.user, course) and not is_teacher_or_ta(request.user, course):
            return api_response(
                data=None,
                message="permission denied: user is not a member of this course",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 作業底下有哪些題目
        problem_ids = collect_problem_ids(hw)

        #  全班成員（只限這門課的成員）
        # 這裡會取出課程成員（包含學生/TA/老師，依Course_members 的資料）
        members = (
            Course_members.objects
            .filter(course_id=course)
            .select_related("user_id")
        )
        users = [m.user_id for m in members]  # user object list（依 Course_members）

        # 確保主授老師也在 users 清單中（即使他/她沒有出現在 Course_members）
        teacher_user = getattr(course, "teacher_id", None)
        if teacher_user is not None and teacher_user not in users:
            users.append(teacher_user)
        # 1) studentStatus 骨架：每人每題預設值
        student_status = {}
        for u in users:
            uname = u.username
            student_status[uname] = {}
            for pid in problem_ids:
                student_status[uname][str(pid)] = {
                    "problemStatus": None,
                    "score": 0,
                    "submissionIds": [],
                }

        # 2) 查 submissions（只查：本作業題目 + 本課程成員）
        if problem_ids and users:
            qs = (
                Submission.objects
                .filter(problem_id__in=problem_ids, user__in=users)
                .select_related("user")
                .only("id", "problem_id", "user_id", "status", "score", "created_at")
                .order_by("created_at")  # 讓 submissionIds 按時間排序（可改 -created_at）
                .iterator(chunk_size=2000)  # 使用 iterator 分批讀取，避免一次載入所有 submissions
            )

            # NOJ status code -> text（你要 problemStatus 有值）
            def status_text(code: str):
                m = {
                    "-2": None,
                    "-1": "pending",
                    "0": "accepted",
                    "1": "wrong_answer",
                    "2": "compilation_error",
                    "3": "time_limit_exceeded",
                    "4": "memory_limit_exceeded",
                    "5": "runtime_error",
                    "6": "judge_error",
                    "7": "output_limit_exceeded",
                }
                return m.get(str(code), None)

            # 我們用「最好狀態」概念來填 problemStatus：
            # - 只要出現 accepted -> 就是 accepted
            # - 否則取最後一次非 pending 的狀態（若都 pending -> pending）
            status_rank = {
                None: 0,
                "pending": 1,
                "wrong_answer": 2,
                "compilation_error": 2,
                "runtime_error": 2,
                "time_limit_exceeded": 2,
                "memory_limit_exceeded": 2,
                "output_limit_exceeded": 2,
                "judge_error": 2,
                "accepted": 3,
            }

            best_score = {}       # (uname, pid) -> int
            best_status = {}      # (uname, pid) -> str|None

            for sub in qs:
                uname = sub.user.username
                pid = str(sub.problem_id)

                # 保護：如果某人/題目不在骨架（理論上不會）
                cell = student_status.get(uname, {}).get(pid)
                if cell is None:
                    continue

                # submissionIds 全部列出
                cell["submissionIds"].append(str(sub.id))

                # score：取最高分（最直覺）
                sc = int(sub.score or 0)
                prev_sc = best_score.get((uname, pid), 0)
                if sc > prev_sc:
                    best_score[(uname, pid)] = sc
                    cell["score"] = sc

                # problemStatus：用 rank 選「最好」的
                st = status_text(sub.status)
                prev_st = best_status.get((uname, pid))
                if status_rank.get(st, 0) >= status_rank.get(prev_st, 0):
                    best_status[(uname, pid)] = st

            # 回填 problemStatus
            for (uname, pid), st in best_status.items():
                student_status[uname][pid]["problemStatus"] = st

        payload = {
            "end": to_epoch_from_dt(hw.due_time),
            "markdown": hw.description or "",
            "name": hw.title,
            "penalty": "",                 
            "problemIds": problem_ids,
            "start": to_epoch_from_dt(hw.start_time),
            "studentStatus": student_status,
        }

        #  api_response 形狀
        return api_response(
            data=payload,
            message="get homework",
            status_code=status.HTTP_200_OK,
        )
    
# --------- NEW: GET /course/<course_name>/homework ---------
class CourseHomeworkListView(APIView):
    def get(self, request, course_id):
        try:
            course = Courses.objects.get(pk=course_id)  # UUID or int 都能吃
        except Courses.DoesNotExist:
            return Response("course not exists", status=status.HTTP_404_NOT_FOUND)
        deny = require_course_member_or_staff(request.user, course)
        if deny is not None:
            return deny
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

class HomeworkDeadlineUpdateAPIView(APIView):
    """
    PUT /homework/<homework_id>/deadline/
    功能：只更新作業截止時間（due_time）
    權限：需為該課程老師或 TA
    請求格式(JSON)：
      {
        "end": "2025-12-31T23:59:59Z"  # ISO 8601, 或 null
      }
    """

    def put(self, request, homework_id: int):
        # 1) 先把作業抓出來，連同 course 一次 select_related
        homework = get_object_or_404(
            Assignments.objects.select_related("course"),
            pk=homework_id,
        )

        course = homework.course  # 和其他 API 一樣的寫法

        # 2) 權限檢查
        if not is_teacher_or_ta(request.user, course):
            return Response(
                "user must be the teacher or ta of this course",
                status=status.HTTP_403_FORBIDDEN,
            )

        # 3) 檢查 end 是否有給
        if "end" not in request.data:
            return Response(
                "end is required",
                status=status.HTTP_400_BAD_REQUEST,
            )

        end_value = request.data.get("end", None)

        # 4) end = null → 清掉 deadline
        if end_value is None:
            homework.due_time = None
            homework.save(update_fields=["due_time"])
            return Response(
                "Update homework deadline Success",
                status=status.HTTP_200_OK,
            )

        # 5) end 有值 → 解析成 datetime
        dt = parse_datetime(end_value)
        if dt is None:
            return Response(
                "end must be ISO 8601 datetime string or null",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 6) 如果有 start_time，避免 end < start
        if homework.start_time and dt < homework.start_time:
            return Response(
                "end must be greater than or equal to start",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 7) 實際更新 due_time
        homework.due_time = dt
        homework.save(update_fields=["due_time"])

        return Response(
            "Update homework deadline Success",
            status=status.HTTP_200_OK,
        )
class HomeworkDeadlineView(APIView):
    """
    GET /homework/<homework_id>/deadline — 取得作業截止時間

    權限：
      - 老師 / TA：可查看自己課程的所有作業
      - 其他登入使用者：必須是該課程成員（學生）才能查看

    命名規則：
      - 舊 API 已存在的欄位名：沿用（name, markdown, start, end）
      - 其餘欄位：沿用 Assignments table（id, course_id）
      - 新增欄位：is_overdue, server_time
    """

    def get(self, request, homework_id: int):
        # 1) 先把作業抓出來，連同 course 一次 select_related
        homework = get_object_or_404(
            Assignments.objects.select_related("course"),
            pk=homework_id,
        )
        course = homework.course

        # 2) 權限：
        #    - 老師 / TA 直接通過
        #    - 其他使用者必須是課程成員
        if not is_teacher_or_ta(request.user, course):
            if not is_course_member(request.user, course):
                return api_response(
                    data=None,
                    message="permission denied: user is not a member of this course",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 3) 組出回傳 payload
        now = timezone.now()
        payload = {
            "id": homework.id,
            "name": homework.title,
            "markdown": homework.description or "",
            "course_id": homework.course_id,
            "start": homework.start_time,
            "end": homework.due_time,
            "is_overdue": bool(homework.due_time and now > homework.due_time),
            "server_time": now,
        }

        ser = HomeworkDeadlineSerializer(payload)
        return api_response(
            data=ser.data,
            message="get homework deadline",
            status_code=status.HTTP_200_OK,
        )
# --------- NEW: GET /homework/<homework_id>/stats ---------
class HomeworkStatsView(APIView):
    """
    GET /homework/{homework_id}/stats
    取得指定作業的統計資訊（只有課程教師或 TA 可看）

    回傳格式（包在 api_response 的 data 裡）：

    {
      "homework_id": 1,
      "course_id": 3,
      "title": "HW1",
      "description": "...",
      "start_time": "...",
      "due_time": "...",
      "problem_count": 3,
      "overview": {
        "participant_count": 25,
        "total_submission_count": 120,
        "avg_submissions_per_user": 4.8,
        "avg_total_score": 230.5,
        "max_total_score": 300,
        "solved_all_problem_user_count": 8,
        "partially_solved_user_count": 12,
        "unsolved_all_problem_user_count": 5
      },
      "problems": [
        {
          "problem_id": 101,
          "order_index": 1,
          "weight": "1.00",
          "title": "A - Two Sum",
          "participant_count": 20,
          "total_submission_count": 80,
          "avg_attempts_per_user": 4.0,
          "avg_score": 75.5,
          "ac_user_count": 10,
          "partial_user_count": 5,
          "unsolved_user_count": 5,
          "first_ac_time": "2025-11-02T12:34:56Z"
        }
      ]
    }
    """

    def get(self, request, homework_id: int):
        # 1) 找作業
        try:
            hw = Assignments.objects.select_related("course").get(pk=homework_id)
        except Assignments.DoesNotExist:
            return api_response(
                data=None,
                message="homework not exists",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 2) 權限檢查：沿用你原本的 is_teacher_or_ta
        if not is_teacher_or_ta(request.user, hw.course):
            return api_response(
                data=None,
                message="user must be the teacher or ta of this course",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 3) 抓作業題目列表
        problems_qs = Assignment_problems.objects.filter(
            assignment=hw,
            is_active=True,
        ).select_related("problem")

        problems = list(problems_qs)
        problem_ids = [p.problem_id for p in problems]

        # 如果沒有題目 → 回傳空統計
        if not problems:
            payload = {
                "homework_id": hw.id,
                "course_id": hw.course_id,
                "title": hw.title,
                "description": hw.description,
                "start_time": hw.start_time,
                "due_time": hw.due_time,
                "problem_count": 0,
                "overview": {
                    "participant_count": 0,
                    "total_submission_count": 0,
                    "avg_submissions_per_user": 0.0,
                    "avg_total_score": 0.0,
                    "max_total_score": 0,
                    "solved_all_problem_user_count": 0,
                    "partially_solved_user_count": 0,
                    "unsolved_all_problem_user_count": 0,
                },
                "problems": [],
            }
            serializer = HomeworkStatsSerializer(payload)
            return api_response(
                data=serializer.data,
                message="取得作業統計成功（目前作業沒有題目）",
                status_code=status.HTTP_200_OK,
            )

        # 4) 用 UserProblemStats 當統計基礎
        stats_qs = UserProblemStats.objects.filter(
            assignment_id=hw.id,
            problem_id__in=problem_ids,
        ).select_related("user", "best_submission")

        # 4-1) 整體 overview
        participant_count = stats_qs.values("user_id").distinct().count()
        total_submission_count = (
            stats_qs.aggregate(total=Sum("total_submissions"))["total"] or 0
        )

        from collections import defaultdict
        user_summary = defaultdict(
            lambda: {
                "total_score": 0,
                "max_total": 0,
                "solved_count": 0,
            }
        )

        for s in stats_qs:
            u = s.user_id
            user_summary[u]["total_score"] += s.best_score
            user_summary[u]["max_total"] += s.max_possible_score
            if s.solve_status == "solved":
                user_summary[u]["solved_count"] += 1

        user_count = len(user_summary)
        if user_count > 0:
            avg_total_score = sum(
                v["total_score"] for v in user_summary.values()
            ) / user_count
        else:
            avg_total_score = 0.0

        total_problems = len(problems)
        max_total_score = 100 * total_problems  # 先假設每題滿分 100

        solved_all_problem_user_count = 0
        partially_solved_user_count = 0
        unsolved_all_problem_user_count = 0

        if total_problems > 0:
            for v in user_summary.values():
                if v["solved_count"] == 0:
                    unsolved_all_problem_user_count += 1
                elif v["solved_count"] == total_problems:
                    solved_all_problem_user_count += 1
                else:
                    partially_solved_user_count += 1

        avg_submissions_per_user = (
            float(total_submission_count) / participant_count
            if participant_count > 0
            else 0.0
        )

        overview = {
            "participant_count": participant_count,
            "total_submission_count": total_submission_count,
            "avg_submissions_per_user": avg_submissions_per_user,
            "avg_total_score": avg_total_score,
            "max_total_score": max_total_score,
            "solved_all_problem_user_count": solved_all_problem_user_count,
            "partially_solved_user_count": partially_solved_user_count,
            "unsolved_all_problem_user_count": unsolved_all_problem_user_count,
        }

        # 4-2) 每題的統計
        stats_by_problem = {p.problem_id: [] for p in problems}
        for s in stats_qs:
            stats_by_problem[s.problem_id].append(s)

        problem_stats_list = []
        for ap in problems:
            s_list = stats_by_problem.get(ap.problem_id, [])

            participant_ids_p = {s.user_id for s in s_list}
            participant_count_p = len(participant_ids_p)
            total_submission_count_p = sum(s.total_submissions for s in s_list)

            if participant_count_p > 0:
                avg_attempts_per_user = (
                    float(total_submission_count_p) / participant_count_p
                )
            else:
                avg_attempts_per_user = 0.0

            if s_list:
                avg_score_p = sum(s.best_score for s in s_list) / len(s_list)
            else:
                avg_score_p = 0.0

            ac_user_count = sum(1 for s in s_list if s.solve_status == "solved")
            partial_user_count = sum(1 for s in s_list if s.solve_status == "partial")
            unsolved_user_count = sum(1 for s in s_list if s.solve_status == "unsolved")

            first_ac_time = min(
                (s.first_ac_time for s in s_list if s.first_ac_time is not None),
                default=None,
            )

            problem_stats_list.append(
                {
                    "problem_id": ap.problem_id,
                    "order_index": ap.order_index,
                    "weight": ap.weight,
                    "title": str(ap.problem),
                    "participant_count": participant_count_p,
                    "total_submission_count": total_submission_count_p,
                    "avg_attempts_per_user": avg_attempts_per_user,
                    "avg_score": avg_score_p,
                    "ac_user_count": ac_user_count,
                    "partial_user_count": partial_user_count,
                    "unsolved_user_count": unsolved_user_count,
                    "first_ac_time": first_ac_time,
                }
            )

        # 5) 組 payload → serializer 驗證 → api_response
        payload = {
            "homework_id": hw.id,
            "course_id": hw.course_id,
            "title": hw.title,
            "description": hw.description,
            "start_time": hw.start_time,
            "due_time": hw.due_time,
            "problem_count": len(problems),
            "overview": overview,
            "problems": problem_stats_list,
        }

        serializer = HomeworkStatsSerializer(payload)
        return api_response(
            data=serializer.data,
            message="取得作業統計成功",
            status_code=status.HTTP_200_OK,
        )
# --------- GET /homework/<id>/scoreboard ---------
class HomeworkScoreboardView(APIView):
    """
    GET /homework/<homework_id>/scoreboard/
    取得某份作業的排行榜
    """

    def get_assignment(self, homework_id: int) -> Assignments:
        return get_object_or_404(
            Assignments.objects.select_related("course"), pk=homework_id
        )

    def check_permission(self, request, assignment: Assignments):
        user = request.user
        course = assignment.course

        # ✅ teacher/TA 放行；否則必須是成員
        if is_teacher_or_ta(user, course):
            return None
        if is_course_member(user, course):
            return None

        return api_response(
            data=None,
            message="permission denied: user is not a member of this course",
            status_code=403,
        )

    def get(self, request, homework_id: int):
        # 1. 取出作業
        assignment = self.get_assignment(homework_id)

        # 2. 權限檢查
        resp = self.check_permission(request, assignment)
        if resp is not None:
            return resp

        # 3. 取出這份作業底下所有 UserProblemStats
        stats_qs = (
            UserProblemStats.objects
            .filter(assignment_id=assignment.id)
            .select_related("user")
            .order_by("user_id", "problem_id")
        )

        # 如果完全沒有統計資料，直接回空排行榜
        if not stats_qs.exists():
            payload = {
                "homework_id": assignment.id,
                "homework_title": assignment.title,
                "course_id": assignment.course_id,
                "items": [],
            }
            serializer = HomeworkScoreboardSerializer(payload)
            return api_response(
                data=serializer.data,
                message="get homework scoreboard",
                status_code=200,
            )

        # 4. 以 user 分組，累計成績 & 題目資訊
        user_map = {}  # user_id -> dict

        for s in stats_qs:
            uid = s.user_id
            if uid not in user_map:
                user_obj = s.user
                user_map[uid] = {
                    "user_id": user_obj.id,
                    "username": user_obj.username,
                    "real_name": getattr(user_obj, "real_name", None),

                    "total_score": 0,
                    "max_total_score": 0,
                    "is_late": False,
                    "first_ac_time": None,
                    "last_submission_time": None,
                    "problems": [],
                }

            entry = user_map[uid]

            # 累加題目資訊
            entry["problems"].append({
                "problem_id": s.problem_id,
                "best_score": s.best_score,
                "max_possible_score": s.max_possible_score,
                "solve_status": s.solve_status,
            })

            # 累加總分
            entry["total_score"] += s.best_score
            entry["max_total_score"] += s.max_possible_score

            # 是否有遲交
            entry["is_late"] = entry["is_late"] or bool(s.is_late)

            # 最早 AC 時間（取最小）
            if s.first_ac_time:
                if (
                    entry["first_ac_time"] is None
                    or s.first_ac_time < entry["first_ac_time"]
                ):
                    entry["first_ac_time"] = s.first_ac_time

            # 最後提交時間（取最大）
            if s.last_submission_time:
                if (
                    entry["last_submission_time"] is None
                    or s.last_submission_time > entry["last_submission_time"]
                ):
                    entry["last_submission_time"] = s.last_submission_time

        # 5. 轉成 list 並排序
        items = list(user_map.values())

        # 為了排序用的「最大時間」(避免 timezone.datetime.max 在某些平台出錯)
        dummy_max = datetime.datetime(9999, 12, 31, tzinfo=datetime.timezone.utc)

        def sort_key(item):
            total = item["total_score"]
            first_ac = item["first_ac_time"] or dummy_max
            last_sub = item["last_submission_time"] or dummy_max
            username = item["username"] or ""
            # 分數降冪、AC 時間升冪、最後提交時間升冪、username 升冪
            return (-total, first_ac, last_sub, username)

        items.sort(key=sort_key)

        # 6. 指定名次（同分同 AC 時間的人名次一樣）
        current_rank = 0
        prev_key = None

        for index, item in enumerate(items, start=1):
            key = (
                item["total_score"],
                item["first_ac_time"] or dummy_max,
            )
            if key != prev_key:
                current_rank = index
                prev_key = key
            item["rank"] = current_rank

        # 7. 組成 payload -> serializer -> api_response
        payload = {
            "homework_id": assignment.id,
            "homework_title": assignment.title,
            "course_id": assignment.course_id,
            "items": items,
        }
        serializer = HomeworkScoreboardSerializer(payload)

        return api_response(
            data=serializer.data,
            message="get homework scoreboard",
            status_code=200,
        )
    
class HomeworkSubmissionsListView(APIView):
    """
    GET /homework/{homework_id}/submissions

    權限：
      - 老師 / TA：可看該課程成員的所有 submissions
      - 學生：只能看自己 submissions
      - 非課程成員：403

    query（可選）：
      - ?user_id=<UUID>（只有老師/TA可用）
      - ?status=<str>   （Submission.status 篩選，例如 '0','1','-1'...）
    """
    def get(self, request, homework_id: int):
        # 1) 找 homework + course
        hw = get_object_or_404(
            Assignments.objects.select_related("course").prefetch_related("assignment_problems"),
            pk=homework_id,
        )
        course = hw.course

        # 2) 權限判斷
        staff_like = is_teacher_or_ta(request.user, course)
        member_like = is_course_member(request.user, course) or staff_like

        if not member_like:
            return api_response(
                data=None,
                message="permission denied: user is not a member of this course",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 3) homework 底下有哪些 problem
        problem_ids = collect_problem_ids(hw)
        if not problem_ids:
            return api_response(
                data={"homeworkId": hw.id, "items": []},
                message="get submissions",
                status_code=status.HTTP_200_OK,
            )

        # 4) 限制「只能看本課程成員」的 submissions（避免撈到外課/外部使用者）
        course_member_ids = Course_members.objects.filter(
            course_id=course
        ).values_list("user_id", flat=True)

        qs = (
            Submission.objects
            .filter(problem_id__in=problem_ids, user_id__in=course_member_ids)
            .select_related("user")
            .order_by("-created_at")
        )

        # 5) 學生只能看自己的 submissions
        if not staff_like:
            qs = qs.filter(user=request.user)

        # 6) query 篩選（老師/TA 才能用 user_id 篩別人）
        user_id = request.query_params.get("user_id")
        if user_id and staff_like:
            qs = qs.filter(user_id=user_id)

        status_param = request.query_params.get("status")
        if status_param is not None:
            qs = qs.filter(status=status_param)

        # 7) serialize
        ser = HomeworkSubmissionListItemSerializer(qs, many=True)

        return api_response(
            data={"homeworkId": hw.id, "items": ser.data},
            message="get submissions",
            status_code=status.HTTP_200_OK,
        )

