from django.urls import path

from ..views import join as join_views

app_name = "join"

urlpatterns = [
    path(
        "",
        join_views.CourseJoinView.as_view(),
        name="join",
    ),
]
