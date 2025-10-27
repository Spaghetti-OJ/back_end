from django.urls import path
from .views import (
    HomeworkCreateView,
    HomeworkDetailView,
    HomeworkUpdateView,
    HomeworkDeleteView,
    CourseHomeworkListView,
)

urlpatterns = [
    # /homework
    path("homework/", HomeworkCreateView.as_view(), name="homework-create"),
    path("homework/<int:id>", HomeworkDetailView.as_view(), name="homework-detail"),
    path("homework/<int:id>", HomeworkUpdateView.as_view(), name="homework-update"),
    path("homework/<int:id>", HomeworkDeleteView.as_view(), name="homework-delete"),
    path("homework/course/<course_id>/", CourseHomeworkListView.as_view(), name="course-homework-list"),
]
