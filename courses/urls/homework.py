from django.urls import path
from courses.views.homework import CourseHomeworkListByIdView

urlpatterns = [
    path("<uuid:course_id>/homework",  CourseHomeworkListByIdView.as_view(), name="course-homework-list"),
    path("<uuid:course_id>/homework/", CourseHomeworkListByIdView.as_view(), name="course-homework-list-slash"),
]
