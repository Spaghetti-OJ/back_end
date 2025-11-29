from django.urls import path

from ..views import scoreboard as scoreboard_views

app_name = "scoreboard"

urlpatterns = [
    path(
        "<course_id>/scoreboard/",
        scoreboard_views.CourseScoreboardView.as_view(),
        name="detail",
    ),
]
