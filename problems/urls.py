from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProblemsViewSet, SubtasksViewSet, TestCasesViewSet, TagsViewSet, ProblemManageView, ProblemManageDetailView, ProblemListView, ProblemDetailView, ProblemHighScoreView, ProblemStatsView, problem_like_toggle, problem_likes_count, UserLikedProblemsView

router = DefaultRouter()
router.register(r"problems", ProblemsViewSet, basename="problems")
router.register(r"subtasks", SubtasksViewSet, basename="subtasks")
router.register(r"test-cases", TestCasesViewSet, basename="test-cases")
router.register(r"tags", TagsViewSet, basename="tags")

urlpatterns = [
    path("manage", ProblemManageView.as_view(), name="problem-manage"),
    path("manage/<int:pk>", ProblemManageDetailView.as_view(), name="problem-manage-detail"),
    path("<int:pk>/high-score", ProblemHighScoreView.as_view(), name="problem-high-score"),
    path("<int:pk>/stats", ProblemStatsView.as_view(), name="problem-stats"),
    path("<int:pk>/like", problem_like_toggle, name="problem-like-toggle"),
    path("<int:pk>/likes", problem_likes_count, name="problem-likes-count"),
    path("liked", UserLikedProblemsView.as_view(), name="user-liked-problems"),
    path("<int:pk>", ProblemDetailView.as_view(), name="problem-detail"),
    path("", ProblemListView.as_view(), name="problem-list"),
    path("router/", include(router.urls)),  # 保留 router 在子路徑避免衝突
]
