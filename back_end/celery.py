"""
Celery 配置文件

這個檔案負責初始化 Celery app 並與 Django 整合
"""

import os
from celery import Celery

# 設定 Django settings 模組
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')

# 創建 Celery app
app = Celery('back_end')

# 從 Django settings 中讀取配置（所有 CELERY_ 開頭的設定）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自動發現所有 app 中的 tasks.py
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """測試用的 task"""
    print(f'Request: {self.request!r}')
