from django.urls import include, path

app_name = "courses"

urlpatterns = [
    path(
        "",
        include((f"{__package__}.urls.courses", "courses"), namespace="courses"),
    ),
    path(
        "summary/",
        include((f"{__package__}.urls.summary", "summary"), namespace="summary"),
    ),
]
