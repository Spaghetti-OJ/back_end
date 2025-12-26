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
    # Note: user_stats_view is registered at root level in back_end/urls.py as /stats/user/<uuid:user_id>/
    path('<uuid:id>/output/<int:task_no>/<int:case_no>/', views.submission_output_view, name='submission-output'),
    
    # ===== Custom Test APIs =====
    path('<int:problem_id>/custom-test/', views.submit_custom_test, name='submit-custom-test'),
    path('custom-test/<str:custom_test_id>/result/', views.get_custom_test_result, name='get-custom-test-result'),
    
    # ===== Sandbox Callback API =====
    path('callback/', views.SubmissionCallbackAPIView.as_view(), name='submission-callback'),
    path('custom-test-callback/', views.CustomTestCallbackAPIView.as_view(), name='custom-test-callback'),
]
