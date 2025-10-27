# assignments/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from courses.models import Courses, Course_members
from assignments.models import Assignments

def is_course_teacher_or_ta(user, course: Courses) -> bool:
    if not (user and user.is_authenticated) or not course:
        return False
    if getattr(course, "teacher_id_id", None) == user.id:
        return True
    return Course_members.objects.filter(
        course_id=course,
        user_id=user,
        role__in=[Course_members.Role.TEACHER, Course_members.Role.TA],
    ).exists()

class IsAuthenticatedRead_AndCourseStaffWrite(BasePermission):
    def has_permission(self, request, view):
        # 讀取
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        # 新增：從 body 的 course_id 判斷
        if request.method == "POST":
            cid = request.data.get("course_id")
            try:
                course = Courses.objects.get(pk=cid)
            except Exception:
                return False  # 讓 serializer 回 "course not exists"
            return is_course_teacher_or_ta(request.user, course)

        # 更新/刪除：由 homework_id 反查課程
        if request.method in ("PUT", "PATCH", "DELETE"):
            homework_id = view.kwargs.get(getattr(view, "lookup_url_kwarg", "homework_id"))
            try:
                assignment = Assignments.objects.select_related("course").get(pk=homework_id)
                return is_course_teacher_or_ta(request.user, assignment.course)
            except Assignments.DoesNotExist:
                return True  # 交給 view 回 404

        return False
