from django.urls import path

from .views import CourseAnnouncementListView, CourseAnnouncementRetrieveView

app_name = "announcements"

urlpatterns = [
    path("<uuid:course_id>/ann", CourseAnnouncementListView.as_view(), name="course"),
    path(
        "<uuid:course_id>/<int:ann_id>",
        CourseAnnouncementRetrieveView.as_view(),
        name="announcement",
    ),
]
