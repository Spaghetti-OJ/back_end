from django.urls import path

from ..views import summary as summary_views

app_name = "summary"

urlpatterns = [
    path("", summary_views.CourseSummaryView.as_view(), name="overview"),
]
