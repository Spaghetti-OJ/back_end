from django.urls import path

from .views import SystemAnnouncementListView

app_name = "announcements"

urlpatterns = [
    path("", SystemAnnouncementListView.as_view(), name="list"),
]
