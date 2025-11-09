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
        "summary/",
        include((f"{__package__}.urls.summary", "summary"), namespace="summary"),
    ),
    path(
        "",
        include(
            (f"{__package__}.urls.course_courseid", "course_courseid"),
            namespace="course_courseid",
        ),
    ),
    path("", include("courses.urls.homework")),
]
