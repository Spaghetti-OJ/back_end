from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'

    def ready(self):  # pragma: no cover - import side-effect
        from rest_framework import generics as drf_generics

        if not hasattr(drf_generics, "ListCreateAPIView") and hasattr(
            drf_generics, "courseAPIView"
        ):
            drf_generics.ListCreateAPIView = drf_generics.courseAPIView
