from django.urls import path

from ..views import invite as invite_views

app_name = "invite"

urlpatterns = [
    path("", invite_views.CourseInviteCodeView.as_view(), name="create"),
    path("<code>/", invite_views.CourseInviteCodeView.as_view(), name="delete"),
]
