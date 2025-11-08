from django.urls import path

from .views import CourseAnnouncementListView

app_name = "announcements"

urlpatterns = [
    path("<uuid:course_id>/ann", CourseAnnouncementListView.as_view(), name="course"),
]
