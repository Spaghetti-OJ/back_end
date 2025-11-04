from django.urls import path

from .views import CourseView, CourseSummaryView

urlpatterns = [
    path('', CourseView.as_view(), name='course'),
    path('summary/', CourseSummaryView.as_view(), name='course_summary'),
]
