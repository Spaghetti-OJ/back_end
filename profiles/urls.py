# profile/urls.py
from django.urls import path
from .views import MeProfileView, PublicProfileView

urlpatterns = [
    path("", MeProfileView.as_view(), name="profile-me"),
    path("<str:username>/", PublicProfileView.as_view(), name="profile-public"),
]
