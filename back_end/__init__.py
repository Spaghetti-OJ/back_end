"""
Django 專案初始化

這個檔案會在 Django 啟動時自動執行
"""

# 導入 Celery app，讓 Django 啟動時自動載入
from .celery import app as celery_app

__all__ = ('celery_app',)
