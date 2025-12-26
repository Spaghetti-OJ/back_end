from django.urls import path
from courses.views.homework import CourseHomeworkListByIdView

urlpatterns = [
    path("", CourseHomeworkListByIdView.as_view(), name="course-homework-list"),
]
