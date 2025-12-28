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
        "<join_code>/join/",
        include((f"{__package__}.urls.join", "join"), namespace="join"),
    ),
    path(
        "<course_id>/assign-ta/",
        include((f"{__package__}.urls.assign_ta", "assign_ta"), namespace="assign_ta"),
    ),
    path(
        "<course_id>/",
        include(
            (f"{__package__}.urls.course_courseid", "course_courseid"),
            namespace="course_courseid",
        ),
    ),
    path(
        "<course_id>/import-csv/",
        include((f"{__package__}.urls.import_csv", "import_csv"), namespace="import_csv"),
    ),
    path(
        "<course_id>/homework/",
        include((f"{__package__}.urls.homework", "homework"), namespace="homework"),
    ),
]
