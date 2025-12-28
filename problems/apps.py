from django.apps import AppConfig


class ProblemsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'problems'

    def ready(self):
        # 導入 signals 以註冊 signal handlers
        import problems.signals  # noqa: F401
