from django.urls import path

from .views import CourseCreateView

urlpatterns = [
    path('', CourseCreateView.as_view(), name='course_create'),
]
