from django.urls import include, path

from . import courses as course_urls
from . import summary as summary_urls

app_name = "courses"

urlpatterns = [
    path(
        "",
        include((course_urls.urlpatterns, "courses"), namespace="courses"),
    ),
    path(
        "summary/",
        include((summary_urls.urlpatterns, "summary"), namespace="summary"),
    ),
    path('', include('courses.urls.homework')),
]
