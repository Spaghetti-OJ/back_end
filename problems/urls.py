from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProblemsViewSet, SubtasksViewSet, TestCasesViewSet, TagsViewSet, ProblemManageView, ProblemManageDetailView

router = DefaultRouter()
router.register(r"problems", ProblemsViewSet, basename="problems")
router.register(r"subtasks", SubtasksViewSet, basename="subtasks")
router.register(r"test-cases", TestCasesViewSet, basename="test-cases")
router.register(r"tags", TagsViewSet, basename="tags")

urlpatterns = [
    path("problem/manage", ProblemManageView.as_view(), name="problem-manage"),
    path("problem/manage/<int:pk>", ProblemManageDetailView.as_view(), name="problem-manage-detail"),
    path("", include(router.urls)),
]
