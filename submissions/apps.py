from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'submissions'
    
    def ready(self):
        """Import signal handlers"""
        import submissions.cache.signals  # noqa
        
        # 註解: Bloom filter 會在第一次使用時自動延遲初始化
        # 避免在 Django 啟動時訪問資料庫造成警告
