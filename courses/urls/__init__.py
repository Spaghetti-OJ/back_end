from django.urls import include, path

from . import course_courseid as detail_urls
from . import courses as course_urls
from . import summary as summary_urls
from . import grade as grade_urls
from . import join as join_urls
from . import invite as invite_urls
from . import assign_ta as assign_ta_urls
from . import scoreboard as scoreboard_urls
from . import import_csv as import_csv_urls

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
        "<course_id>/scoreboard/",
        include((scoreboard_urls.urlpatterns, "scoreboard"), namespace="scoreboard"),
    ),
    path(
        "<course_id>/invite-code/",
        include((invite_urls.urlpatterns, "invite"), namespace="invite"),
    ),
    path(
        "<course_id>/import-csv/",
        include((import_csv_urls.urlpatterns, "import_csv"), namespace="import_csv"),
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
        "<course_id>/assign-ta/",
        include((assign_ta_urls.urlpatterns, "assign_ta"), namespace="assign_ta"),
    ),
    path(
        "<course_id>/",
        include((detail_urls.urlpatterns, "course_courseid"), namespace="course_courseid"),
    ),
    path("", include("courses.urls.homework")),
]
