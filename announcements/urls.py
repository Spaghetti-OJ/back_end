from django.urls import path

from .views import AnnouncementCreateView, CourseAnnouncementListView, CourseAnnouncementRetrieveView

app_name = "announcements"

urlpatterns = [
    path("", AnnouncementCreateView.as_view(), name="create"),
    path("<uuid:course_id>/ann", CourseAnnouncementListView.as_view(), name="course"),
    path(
        "<uuid:course_id>/<int:ann_id>",
        CourseAnnouncementRetrieveView.as_view(),
        name="announcement",
    ),
]
