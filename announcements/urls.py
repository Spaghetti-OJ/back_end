from django.urls import path

from .views import AnnouncementCreateView, CourseAnnouncementListView

app_name = "announcements"

urlpatterns = [
    path("", AnnouncementCreateView.as_view(), name="create"),
    path("<uuid:course_id>/ann", CourseAnnouncementListView.as_view(), name="course"),
]
