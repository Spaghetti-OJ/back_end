from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.api import (
    ProblemsViewSet, SubtasksViewSet, TestCasesViewSet,
    ProblemManageView, ProblemManageDetailView,
    ProblemListView, ProblemDetailView, ProblemHighScoreView, ProblemStatsView,
    problem_like_toggle, problem_likes_count, UserLikedProblemsView,
    TagListCreateView, ProblemTagAddView, ProblemTagRemoveView,
    ProblemCloneView,
    ProblemTestCaseUploadInitiateView, ProblemTestCaseUploadCompleteView, ProblemTestCaseDownloadView,
    ProblemTestCaseChecksumView, ProblemTestCaseMetaView,
    ProblemSubtaskListCreateView, ProblemSubtaskDetailView,
    ProblemTestCaseListCreateView, ProblemTestCaseDetailView, ProblemTestCaseZipUploadView,
    ProblemSubtaskListCreateView, ProblemSubtaskDetailView,
    ProblemTestCaseListCreateView, ProblemTestCaseDetailView, ProblemTestCaseZipUploadView,
)
from .views.sandbox import ProblemTestCasePackageView

router = DefaultRouter()
router.register(r"problems", ProblemsViewSet, basename="problems")
# 已改用 problem-scoped 子題路徑，避免重複與混淆，移除舊 router subtasks
router.register(r"test-cases", TestCasesViewSet, basename="test-cases")
# 移除舊 tags ViewSet：改用統一 APIViews (GET/POST /tags, POST/DELETE /problem/<id>/tags)

urlpatterns = [
    path("manage", ProblemManageView.as_view(), name="problem-manage"),
    path("manage/<int:pk>", ProblemManageDetailView.as_view(), name="problem-manage-detail"),
    path("clone", ProblemCloneView.as_view(), name="problem-clone"),
    # Subtasks under specific problem
    path("<int:pk>/subtasks", ProblemSubtaskListCreateView.as_view(), name="problem-subtasks"),
    path("<int:pk>/subtasks/<int:subtask_id>", ProblemSubtaskDetailView.as_view(), name="problem-subtask-detail"),
    path("<int:pk>/high-score", ProblemHighScoreView.as_view(), name="problem-high-score"),
    path("<int:pk>/stats", ProblemStatsView.as_view(), name="problem-stats"),
    path("<int:pk>/like", problem_like_toggle, name="problem-like-toggle"),
    path("<int:pk>/likes", problem_likes_count, name="problem-likes-count"),
    path("liked", UserLikedProblemsView.as_view(), name="user-liked-problems"),
    path("<int:pk>", ProblemDetailView.as_view(), name="problem-detail"),
    path("", ProblemListView.as_view(), name="problem-list"),
    # 問題層級測資上傳/完成/下載
    path("<int:pk>/initiate-test-case-upload", ProblemTestCaseUploadInitiateView.as_view(), name="problem-initiate-testcase"),
    path("<int:pk>/complete-test-case-upload", ProblemTestCaseUploadCompleteView.as_view(), name="problem-complete-testcase"),
    path("<int:pk>/test-case", ProblemTestCaseDownloadView.as_view(), name="problem-testcase-download"),
    path("<int:pk>/test-cases/upload-zip", ProblemTestCaseZipUploadView.as_view(), name="problem-testcases-upload-zip"),
    # 題目巢狀測資 CRUD（資料表 Test_cases）
    path("<int:pk>/test-cases", ProblemTestCaseListCreateView.as_view(), name="problem-testcases"),
    path("<int:pk>/test-cases/<int:case_id>", ProblemTestCaseDetailView.as_view(), name="problem-testcase-detail"),
    # Sandbox 專用：測資檔案完整性（MD5）、結構資訊、下載
    path("<int:pk>/checksum", ProblemTestCaseChecksumView.as_view(), name="problem-testcase-checksum"),
    path("<int:pk>/meta", ProblemTestCaseMetaView.as_view(), name="problem-testcase-meta"),
    path("<int:pk>/testdata", ProblemTestCasePackageView.as_view(), name="problem-testcase-package"),
    # 新標籤 API
    path("tags", TagListCreateView.as_view(), name="tag-list-create"),
    path("<int:pk>/tags", ProblemTagAddView.as_view(), name="problem-tag-add"),
    path("<int:pk>/tags/<int:tag_id>", ProblemTagRemoveView.as_view(), name="problem-tag-remove"),
    path("router/", include(router.urls)),  # 保留 router 在子路徑避免衝突
]
