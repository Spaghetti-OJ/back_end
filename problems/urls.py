from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProblemsViewSet, SubtasksViewSet, TestCasesViewSet, TagsViewSet

router = DefaultRouter()
router.register(r"problems", ProblemsViewSet, basename="problems")
router.register(r"subtasks", SubtasksViewSet, basename="subtasks")
router.register(r"test-cases", TestCasesViewSet, basename="test-cases")
router.register(r"tags", TagsViewSet, basename="tags")

urlpatterns = [
    path("", include(router.urls)),
]
