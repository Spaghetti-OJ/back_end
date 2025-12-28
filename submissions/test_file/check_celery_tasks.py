#!/usr/bin/env python
"""
檢查 Celery 是否正確發現 submissions.tasks
"""
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

print("=" * 70)
print("  Celery 任務檢查")
print("=" * 70)

# 1. 檢查 Celery app
from back_end.celery import app

print(f"\n1. Celery App:")
print(f"   名稱: {app.main}")
print(f"   Broker: {app.conf.broker_url}")
print(f"   Backend: {app.conf.result_backend}")

# 2. 檢查已安裝的 apps
from django.conf import settings
print(f"\n2. INSTALLED_APPS 包含 submissions: {'submissions' in settings.INSTALLED_APPS}")

# 3. 嘗試導入任務
print(f"\n3. 導入任務:")
try:
    from submissions.tasks import submit_to_sandbox_task
    print(f"   成功導入: {submit_to_sandbox_task}")
    print(f"   任務名稱: {submit_to_sandbox_task.name}")
except ImportError as e:
    print(f"   導入失敗: {e}")
    sys.exit(1)

# 4. 檢查任務是否註冊
print(f"\n4. Celery 已註冊的任務:")
task_name = 'submissions.tasks.submit_to_sandbox_task'
if task_name in app.tasks:
    print(f"   找到: {task_name}")
else:
    print(f"   找不到: {task_name}")
    print(f"\n   已註冊的任務 ({len(app.tasks)}):")
    for name in sorted(app.tasks.keys()):
        if not name.startswith('celery.'):
            print(f"      - {name}")

# 5. 手動觸發 autodiscover
print(f"\n5. 手動觸發 autodiscover_tasks:")
app.autodiscover_tasks()
print(f"   完成")

# 6. 再次檢查
if task_name in app.tasks:
    print(f"   現在找到了: {task_name}")
else:
    print(f"   還是找不到: {task_name}")

print("\n" + "=" * 70)
