from django.urls import include, path

from . import course_coursename as detail_urls
from . import courses as course_urls
from . import summary as summary_urls

app_name = "courses"

urlpatterns = [
    path(
        "summary/",
        include((summary_urls.urlpatterns, "summary"), namespace="summary"),
    ),
    path(
        "",
        include((course_urls.urlpatterns, "courses"), namespace="courses"),
    ),
    path(
        "",
        include(
            (detail_urls.urlpatterns, "course_coursename"),
            namespace="course_coursename",
        ),
    ),
]
