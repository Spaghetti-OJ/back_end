from django.urls import path
from .views import CopycatView

urlpatterns = [
    # POST /copycat/ -> 觸發
    # GET  /copycat/?problem_id=1 -> 查詢
    path('', CopycatView.as_view(), name='copycat'),
]