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
from submissions import views as submission_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'course/',
        include(('courses.urls', 'courses'), namespace='courses'),
    ),
    path('ann/', include(('announcements.urls', 'announcements'), namespace='system_announcements')),
    path('user/', include('user.urls')), 
    path('course/', include('courses.urls')),
    path('auth/', include('auths.urls')),
    path('editorials/', include('submissions.editorial_urls')),
    path('submission/', include('submissions.urls')),
    path('ranking/', submission_views.ranking_view, name='ranking'),
    path('api-tokens/', include('api_tokens.urls')),
    path('profile/', include('profiles.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
