"""
URL configuration for back_end project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from submissions import views as submission_views

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('course/', include(('courses.urls', 'courses'), namespace='courses')),
    path('ann/', include(('announcements.urls'), namespace='announcements')),
    path('user/', include('user.urls')), 
    path('problem/', include('problems.urls')),
    path('auth/', include('auths.urls')),
    path('editorials/', include('submissions.editorial_urls')),
    path('submission/', include('submissions.urls')),
    path('ranking/', submission_views.ranking_view, name='ranking'),
    path('stats/user/<uuid:user_id>/', submission_views.user_stats_view, name='user-stats-root'),
    path('api-tokens/', include('api_tokens.urls')),
    path('profile/', include('profiles.urls')),
    path('homework/',include('assignments.urls')),
    path('schema-viewer/', include('schema_viewer.urls')),
    path('editor/', include('editor.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('copycat/', include('copycat.urls')),
    
    ## Swagger API Documentation URLs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("search/", include("search.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
