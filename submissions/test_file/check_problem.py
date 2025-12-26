#!/usr/bin/env python
"""
查詢 Problem 資訊
"""

import sys
import os
import django

sys.path.insert(0, '/Users/keliangyun/Desktop/software_engineering/back_end')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from problems.models import Problems

try:
    problem = Problems.objects.get(id=1)
    print("\n" + "=" * 60)
    print("  Problem ID 1 資訊")
    print("=" * 60)
    print(f"Title: {problem.title}")
    print(f"Difficulty: {problem.difficulty}")
    print(f"Max Score: {problem.max_score}")
    print(f"Creator: {problem.creator_id.username}")
    print(f"Course: {problem.course_id.name if problem.course_id else 'None'}")
    print(f"Created: {problem.created_at}")
    
    print("\n" + "=" * 60)
    print("  Subtasks")
    print("=" * 60)
    for subtask in problem.subtasks.all():
        print(f"Subtask {subtask.subtask_no}:")
        print(f"  Weight: {subtask.weight}")
        print(f"  Time Limit: {subtask.time_limit_ms}ms")
        print(f"  Memory Limit: {subtask.memory_limit_mb}MB")
        print(f"  Test Cases: {subtask.test_cases.count()}")
        
except Problems.DoesNotExist:
    print("Problem ID 1 不存在")
