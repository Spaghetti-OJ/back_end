from django.urls import path

from ..views import grade as grade_views

app_name = "grade"

urlpatterns = [
    path(
        "<student>/",
        grade_views.CourseGradeView.as_view(),
        name="detail",
    ),
]
