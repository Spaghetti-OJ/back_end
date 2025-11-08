# profile/urls.py
from django.urls import path
from .views import MeProfileView

urlpatterns = [
    path("", MeProfileView.as_view(), name="profile-me"),
]
