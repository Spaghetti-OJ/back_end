from django.urls import path

from ..views import courses as course_views

app_name = "courses"

urlpatterns = [
    path("", course_views.CourseListCreateView.as_view(), name="list"),
]
