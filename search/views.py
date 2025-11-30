from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from problems.models import Problems
from courses.models import Courses


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
def serialize_problem(problem: Problems):
    return {
        "id": problem.id,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "max_score": problem.max_score,
        "is_public": problem.is_public,
        "total_submissions": problem.total_submissions,
        "accepted_submissions": problem.accepted_submissions,
        "acceptance_rate": str(problem.acceptance_rate),
        "like_count": problem.like_count,
        "view_count": problem.view_count,
        "total_quota": problem.total_quota,

        # 這兩個都是 FK → 回傳成字串（uuid 或 int 都會變字串）
        "creator_id": str(problem.creator_id_id) if problem.creator_id_id is not None else None,
        "course_id": str(problem.course_id_id) if problem.course_id_id is not None else None,

        "course_name": str(problem.course_id) if problem.course_id else None,

        "tags": [
            {
                "id": t.id,
                "name": t.name,
                "usage_count": t.usage_count,
            }
            for t in problem.tags.all()
        ],
    }
def get_user_visible_problems_queryset(user):
    """
    共用的可見範圍條件：
    - PUBLIC: 所有人可見
    - COURSE: 僅該課程內的成員可見
    - HIDDEN: 僅出題者本人可見
    """
    # 你有加入或授課的課程
    user_course_ids = Courses.objects.filter(
        Q(teacher_id=user) | Q(members__user_id=user)
    ).values_list("id", flat=True).distinct()

    visible_q = (
        Q(is_public=Problems.Visibility.PUBLIC)
        | Q(is_public=Problems.Visibility.COURSE, course_id__in=user_course_ids)
        | Q(is_public=Problems.Visibility.HIDDEN, creator_id=user)
    )

    qs = (
        Problems.objects.filter(visible_q)
        .select_related("course_id")
        .prefetch_related("tags")
        .distinct()
    )
    return qs

class GlobalProblemSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # === 1) 讀取查詢字串 ===
        keyword = request.query_params.get("q", "").strip()
        if not keyword:
            # 沒給關鍵字就回空陣列，但格式一樣
            return api_response(
                data={"items": [], "total": 0},
                message="keyword is empty",
                status_code=status.HTTP_200_OK,
            )

        # === 2) 題目/標籤關鍵字條件 ===
        base_q = Q(title__icontains=keyword) | Q(tags__name__icontains=keyword)

        # === 3) 可見範圍條件（依 is_public & 課程身分） ===
        user = request.user

        # 你有參與的課程（老師 / TA / 學生）
        user_course_ids = Courses.objects.filter(
            Q(teacher_id=user) | Q(members__user_id=user)
        ).values_list("id", flat=True).distinct()

        visible_q = (
            Q(is_public=Problems.Visibility.PUBLIC)
            | Q(is_public=Problems.Visibility.COURSE, course_id__in=user_course_ids)
            | Q(is_public=Problems.Visibility.HIDDEN, creator_id=user)
        )

        qs = (
            Problems.objects.filter(base_q)
            .filter(visible_q)
            .select_related("course_id")
            .prefetch_related("tags")
            .distinct()
            .order_by("id")
        )

        # === 4) 組回傳結構：欄位名對齊 table ===
        items = []
        for p in qs:
            items.append(
                {
                    # ----- Problems -----
                    "id": p.id,
                    "title": p.title,
                    "difficulty": p.difficulty,          # 'easy' | 'medium' | 'hard'
                    "max_score": p.max_score,
                    "is_public": p.is_public,            # 'hidden' | 'course' | 'public'
                    "total_submissions": p.total_submissions,
                    "accepted_submissions": p.accepted_submissions,
                    "acceptance_rate": str(p.acceptance_rate),
                    "like_count": p.like_count,
                    "view_count": p.view_count,
                    "total_quota": p.total_quota,
                    "creator_id": p.creator_id_id,       # uuid (Users.id)
                    "course_id": p.course_id_id,         # int (Courses.id) or None

                    # 額外方便前端顯示的欄位（不衝突 DB 命名）
                    "course_name": str(p.course_id) if p.course_id else None,

                    # ----- Tags (list) -----
                    "tags": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "usage_count": t.usage_count,
                        }
                        for t in p.tags.all()
                    ],
                }
            )

        return api_response(
            data={
                "items": items,
                "total": len(items),
            },
            message="search problems success",
            status_code=status.HTTP_200_OK,
        )

class ProblemSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = get_user_visible_problems_queryset(user)

        # === 1) 關鍵字搜尋 ===
        keyword = request.query_params.get("q", "").strip()
        if keyword:
            qs = qs.filter(
                Q(title__icontains=keyword) |
                Q(tags__name__icontains=keyword)
            )

        # === 2) 難度篩選 ===
        difficulty = request.query_params.get("difficulty")
        if difficulty in Problems.Difficulty.values:
            qs = qs.filter(difficulty=difficulty)

        # === 3) is_public 篩選 ===
        visibility = request.query_params.get("is_public")
        if visibility in Problems.Visibility.values:
            qs = qs.filter(is_public=visibility)

        # === 4) course_id 篩選 ===
        course_id = request.query_params.get("course_id")
        if course_id:
            # 目前資料庫的 Courses.id 實際上還是 BigAutoField(int)
            # 所以這裡先把 query string 的 course_id 當作「課程 int 主鍵」來用。
            # 若前端丟的是 UUID 之類非數字字串，就直接回 400，避免丟到 DB 造成 500。
            if course_id.isdigit():
                qs = qs.filter(course_id=int(course_id))
            else:
                return api_response(
                    data={"items": [], "total": 0},
                    message="invalid course_id format (expect integer id for now)",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        # === 5) tag 篩選 ===
        tag_id = request.query_params.get("tag_id")
        if tag_id:
            qs = qs.filter(tags__id=tag_id)

        qs = qs.order_by("id").distinct()
        items = [serialize_problem(p) for p in qs]

        return api_response(
            data={
                "items": items,
                "total": len(items),
            },
            message="search problems success",
            status_code=status.HTTP_200_OK,
        )