from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, MeView

urlpatterns = [
    #path('signup/', RegisterView.as_view(), name='register'),
    #path('session/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    #path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    #path('me/', MeView.as_view(), name='me'),
]
