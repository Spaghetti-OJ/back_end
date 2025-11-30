# assignments/urls.py
from django.urls import path
from . import views

app_name = "assignments"

urlpatterns = [
    # POST /homework/
    path("", views.HomeworkCreateView.as_view(), name="homework-create"),

    # GET/PUT/DELETE /homework/<id>
    path("<int:homework_id>", views.HomeworkDetailView.as_view(), name="homework-detail"),
    path("<int:homework_id>/", views.HomeworkDetailView.as_view(), name="homework-detail-slash"),

    # POST /homework/<id>/problems
    path("<int:homework_id>/problems", views.AddProblemsToHomeworkView.as_view(), name="homework-add-problems"),
    path("<int:homework_id>/problems/", views.AddProblemsToHomeworkView.as_view(), name="homework-add-problems-slash"),
    
    path("<int:homework_id>/deadline/",views.HomeworkDeadlineUpdateAPIView.as_view(),name="homework-deadline-update",),
    # GET /homework/course/<course_id>  (course_id 為 UUID)
    #path("course/<uuid:course_id>", views.CourseHomeworkListView.as_view(), name="course-homework-list"),
    #path("course/<uuid:course_id>/", views.CourseHomeworkListView.as_view(), name="course-homework-list-slash"),
]
