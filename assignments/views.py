from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Assignments, Assignment_problems
from .serializers import HomeworkInSerializer, HomeworkDetailOutSerializer
from courses.models import Courses, Course_members

def epoch_to_dt(v):
    if v is None:
        return None
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return timezone.datetime.fromtimestamp(v, tz=timezone.utc)

def is_teacher_or_ta(user, course: Courses) -> bool:
    # 老師
    if course.teacher_id_id == user.id:
        return True
    # 助教
    return Course_members.objects.filter(
        course_id=course, user_id=user, role=Course_members.Role.TA
    ).exists()

def get_course_or_400(course_id_str):
    # POST/PUT 用：需要 400 + {"course_id": "course not exists"}
    try:
        return Courses.objects.get(pk=course_id_str)
    except (Courses.DoesNotExist, ValueError):
        return None

def make_detail_payload(hw: Assignments, message="get homework"):
    problem_ids = list(
        hw.assignment_problems.values_list("problem_id", flat=True)
    )
    start_epoch = int(hw.start_time.timestamp()) if hw.start_time else None
    end_epoch = int(hw.due_time.timestamp()) if hw.due_time else None
    return {
        "id": hw.id,
        "message": message,
        "name": hw.title,
        "course_id": hw.course_id,
        "markdown": hw.description or "",
        "start": start_epoch,
        "end": end_epoch,
        "problemIds": problem_ids,
    }

# POST /homework — 建立作業
class HomeworkCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = HomeworkInSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        course_id = ser.validated_data["course_id"]
        course = get_course_or_400(course_id)
        if course is None:
            # 符合測試要求
            return Response({"course_id": "course not exists"}, status=400)

        # 權限：老師或 TA
        if not is_teacher_or_ta(request.user, course):
            # 測試會搜尋 "teacher or ta" 字眼
            raise PermissionDenied("teacher or ta only")

        name = ser.validated_data["name"].strip()
        markdown = ser.validated_data.get("markdown", "")
        start = epoch_to_dt(ser.validated_data.get("start"))
        end = epoch_to_dt(ser.validated_data.get("end"))
        problem_ids = ser.validated_data.get("problem_ids", [])

        # 同課程重名要 400 並回 "homework exists in this course"
        if Assignments.objects.filter(course=course, title=name).exists():
            return Response("homework exists in this course", status=400)

        hw = Assignments.objects.create(
            title=name,
            description=markdown or "",
            course=course,
            creator=request.user,
            start_time=start,
            due_time=end,
        )

        # 依序建立 Assignment_problems
        order_idx = 1
        for pid in problem_ids:
            Assignment_problems.objects.create(
                assignment=hw,
                problem_id=pid,
                order_index=order_idx,
            )
            order_idx += 1

        return Response("Add homework Success", status=200)

# GET /homework/{id} — 作業詳情
class HomeworkDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id: int):
        hw = get_object_or_404(Assignments, pk=id)
        # 學生可讀
        payload = make_detail_payload(hw, message="get homework")
        return Response(payload, status=200)

# PUT /homework/{id} — 修改作業
class HomeworkUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, id: int):
        hw = get_object_or_404(Assignments, pk=id)

        # 權限：老師或 TA
        if not is_teacher_or_ta(request.user, hw.course):
            raise PermissionDenied("teacher or ta only")

        ser = HomeworkInSerializer(data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        new_course = hw.course
        if "course_id" in ser.validated_data:
            course = get_course_or_400(ser.validated_data["course_id"])
            if course is None:
                return Response({"course_id": "course not exists"}, status=400)
            new_course = course

        new_name = ser.validated_data.get("name")
        if new_name is not None:
            new_name = new_name.strip()

        new_markdown = ser.validated_data.get("markdown")
        new_start = epoch_to_dt(ser.validated_data.get("start")) if "start" in ser.validated_data else hw.start_time
        new_end = epoch_to_dt(ser.validated_data.get("end")) if "end" in ser.validated_data else hw.due_time

        # 時間檢核（符合測試：在 'end' 欄位報）
        if new_start and new_end and new_end < new_start:
            return Response({"end": "end must be >= start"}, status=400)

        # 重名檢查（以更新後的 course + name）
        if new_name:
            exists = Assignments.objects.filter(course=new_course, title=new_name).exclude(id=hw.id).exists()
            if exists:
                return Response("homework exists in this course", status=400)

        # 權限再檢查一次（若課程被改到別課）
        if new_course and not is_teacher_or_ta(request.user, new_course):
            raise PermissionDenied("teacher or ta only")

        # 實際更新
        if new_name is not None:
            hw.title = new_name
        if new_markdown is not None:
            hw.description = new_markdown
        hw.course = new_course
        hw.start_time = new_start
        hw.due_time = new_end
        hw.save()

        # 若提供 problem_ids，視為覆蓋重建
        if "problem_ids" in ser.validated_data:
            ids_in = ser.validated_data.get("problem_ids") or []
            hw.assignment_problems.all().delete()
            for idx, pid in enumerate(ids_in, start=1):
                Assignment_problems.objects.create(
                    assignment=hw, problem_id=pid, order_index=idx
                )

        return Response("Update homework Success", status=200)

# DELETE /homework/{id} — 刪除作業
class HomeworkDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id: int):
        hw = get_object_or_404(Assignments, pk=id)
        if not is_teacher_or_ta(request.user, hw.course):
            raise PermissionDenied("teacher or ta only")
        hw.delete()
        return Response("Delete homework Success", status=200)

# GET /homework/course/{course_id} — 列出某課程作業
class CourseHomeworkListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id: str):
        try:
            course = Courses.objects.get(pk=course_id)
        except (Courses.DoesNotExist, ValueError):
            return Response("course not exists", status=404)

        items = []
        qs = Assignments.objects.filter(course=course).order_by("-created_at")
        for hw in qs:
            items.append({
                "id": hw.id,
                "name": hw.title,
            })

        return Response({"message": "get homeworks", "items": items}, status=200)
