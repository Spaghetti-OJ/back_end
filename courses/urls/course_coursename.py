from django.urls import path

from ..views import course_coursename as detail_views

app_name = "course_coursename"

urlpatterns = [
    path("<str:course_name>/", detail_views.CourseDetailView.as_view(), name="detail"),
]
