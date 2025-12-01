from django.urls import path

from ..views import assign_ta as assign_ta_views

app_name = "assign_ta"

urlpatterns = [
    path(
        "",
        assign_ta_views.CourseAssignTAView.as_view(),
        name="assign",
    ),
]
