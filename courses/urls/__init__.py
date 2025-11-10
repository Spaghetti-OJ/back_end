from django.urls import include, path

from . import course_courseid as detail_urls
from . import courses as course_urls
from . import summary as summary_urls
from . import grade as grade_urls

app_name = "courses"

urlpatterns = [
    # /course/...
    path("", include(course_urls)),

    # /course/summary/...
    path("summary/", include(summary_urls)),

    # /course/<course_id>/grade/...
    path("<course_id>/grade/", include(grade_urls)),

    # /course/<course_id>/...（
    path("<course_id>/", include(detail_urls)),

    # /course/<course_id>/homework/...
    path("<course_id>/homework/", include("courses.urls.homework")),
]
