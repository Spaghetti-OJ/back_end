from django.urls import include, path

from . import course_courseid as detail_urls
from . import courses as course_urls
from . import summary as summary_urls
from . import grade as grade_urls
from . import join as join_urls

app_name = "courses"

urlpatterns = [
    path(
        "",
        include((course_urls.urlpatterns, "courses"), namespace="courses"),
    ),
    path(
        "<course_id>/grade/",
        include((grade_urls.urlpatterns, "grade"), namespace="grade"),
    ),
    path(
        "summary/",
        include((summary_urls.urlpatterns, "summary"), namespace="summary"),
    ),
    path(
        "<course_id>/join/",
        include((join_urls.urlpatterns, "join"), namespace="join"),
    ),
    path(
        "<course_id>/",
        include((detail_urls.urlpatterns, "course_courseid"), namespace="course_courseid"),
    ),
    path("", include("courses.urls.homework")),
]
