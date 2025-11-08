from django.urls import path
from . import views

app_name = 'editorials'

urlpatterns = [
    # 題解相關 API
    path('problem/<int:problem_id>/solution/', 
         views.EditorialListCreateView.as_view(), 
         name='editorial-list-create'),
    
    path('problem/<int:problem_id>/solution/<uuid:solution_id>/', 
         views.EditorialDetailView.as_view(), 
         name='editorial-detail'),
    
    path('problem/<int:problem_id>/solution/<uuid:solution_id>/like/', 
         views.editorial_like_toggle, 
         name='editorial-like-toggle'),
]
