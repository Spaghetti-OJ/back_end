from django.urls import path
from .views import GlobalProblemSearchView,ProblemSearchView

urlpatterns = [
    # 最後會對應成 GET /search/?q=xxx
    path("", GlobalProblemSearchView.as_view(), name="global-problem-search"),
    path("problems", ProblemSearchView.as_view(), name="problem-search"),
]