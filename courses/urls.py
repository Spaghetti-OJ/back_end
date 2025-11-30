from django.urls import include, path

app_name = "courses"

urlpatterns = [
    path(
        "",
        include((f"{__package__}.urls.courses", "courses"), namespace="courses"),
    ),
    path(
        "<course_id>/grade/",
        include((f"{__package__}.urls.grade", "grade"), namespace="grade"),
    ),
    path(
        "<course_id>/invite-code/",
        include((f"{__package__}.urls.invite", "invite"), namespace="invite"),
    ),
    path(
        "<course_id>/scoreboard/",
        include((f"{__package__}.urls.scoreboard", "scoreboard"), namespace="scoreboard"),
    ),
    path(
        "summary/",
        include((f"{__package__}.urls.summary", "summary"), namespace="summary"),
    ),
    path(
        "<course_id>/join/",
        include((f"{__package__}.urls.join", "join"), namespace="join"),
    ),
    path(
        "<course_id>/",
        include(
            (f"{__package__}.urls.course_courseid", "course_courseid"),
            namespace="course_courseid",
        ),
    ),
    path("", include("courses.urls.homework")),
]
