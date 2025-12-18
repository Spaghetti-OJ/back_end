#!/usr/bin/env python
"""
檢查提交狀態
"""

import sys
import os
import django

sys.path.insert(0, '/Users/keliangyun/Desktop/software_engineering/back_end')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from submissions.models import Submission

# 查詢最近的提交
recent_submissions = Submission.objects.order_by('-created_at')[:5]

print("\n" + "=" * 60)
print("  最近的 5 筆提交")
print("=" * 60)

for sub in recent_submissions:
    print(f"\nSubmission ID: {sub.id}")
    print(f"  Problem ID: {sub.problem_id}")
    print(f"  User: {sub.user.username}")
    print(f"  Language: {sub.language_type}")
    print(f"  Status: {sub.status}")
    print(f"  Code Length: {len(sub.source_code)} chars")
    print(f"  Created: {sub.created_at}")
    print(f"  Judged: {sub.judged_at}")

# 檢查特定提交
submission_id = "17685351-891e-42c8-afb3-062c9d55290b"
print("\n" + "=" * 60)
print(f"  檢查提交: {submission_id}")
print("=" * 60)

try:
    sub = Submission.objects.get(id=submission_id)
    print(f"\n[找到提交]")
    print(f"  Problem ID: {sub.problem_id}")
    print(f"  User: {sub.user.username}")
    print(f"  Language: {sub.language_type}")
    print(f"  Status: {sub.status}")
    print(f"  Score: {sub.score}")
    print(f"  Execution Time: {sub.execution_time}")
    print(f"  Memory Usage: {sub.memory_usage}")
    print(f"  Code Hash: {sub.code_hash}")
    print(f"  Created: {sub.created_at}")
    print(f"  Judged: {sub.judged_at}")
    print(f"\n程式碼:")
    print(sub.source_code)
except Submission.DoesNotExist:
    print(f"\n[錯誤] 找不到 submission: {submission_id}")
