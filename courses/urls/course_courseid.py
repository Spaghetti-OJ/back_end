from django.urls import path

from ..views import course_courseid as detail_views

app_name = "course_courseid"

urlpatterns = [
    path(
        "<uuid:course_id>/",
        detail_views.CourseDetailView.as_view(),
        name="detail",
    ),
]
