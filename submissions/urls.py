from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    # ===== Submission APIs =====
    path('', views.SubmissionListCreateView.as_view(), name='submission-list-create'),
    path('<uuid:id>/', views.SubmissionRetrieveUpdateView.as_view(), name='submission-retrieve-update'),
    path('<uuid:id>/code/', views.SubmissionCodeView.as_view(), name='submission-code'),
    path('<uuid:id>/stdout/', views.SubmissionStdoutView.as_view(), name='submission-stdout'),
    path('<uuid:id>/rejudge/', views.submission_rejudge, name='submission-rejudge'),
    path("stats/user/<uuid:user_id>/", views.user_stats_view, name="user-stats"),
    path("submission/<uuid:id>/output/<int:task_no>/<int:case_no>/",views.submission_output_view,name="submission-output",)
]
