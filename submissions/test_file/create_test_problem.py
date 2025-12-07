#!/usr/bin/env python
"""
創建測試用的 Problem 和 Subtask

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/create_test_problem.py
"""
import os
import sys
import django

# 添加專案根目錄到 Python 路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from problems.models import Problems, Problem_subtasks, Test_cases
from user.models import User

def create_test_problem():
    """創建測試題目"""
    
    # 找一個管理員用戶作為 creator
    admin_user = User.objects.filter(is_staff=True).first()
    if not admin_user:
        # 如果沒有管理員，使用第一個用戶
        admin_user = User.objects.first()
        if not admin_user:
            print("沒有可用的用戶")
            return None
    
    # 創建或獲取測試題目
    problem, created = Problems.objects.get_or_create(
        id=1,
        defaults={
            'title': 'A + B Problem (測試用)',
            'description': '輸入兩個整數 a 和 b，輸出它們的和。',
            'input_description': '一行兩個整數 a 和 b (-10^9 ≤ a, b ≤ 10^9)',
            'output_description': '輸出 a + b 的結果',
            'difficulty': 'easy',
            'creator_id': admin_user,
            'is_public': True,
        }
    )
    
    if created:
        print(f"創建新題目: {problem.title} (ID: {problem.id})")
    else:
        print(f"使用現有題目: {problem.title} (ID: {problem.id})")
    
    # 創建 Subtask
    subtask, created = Problem_subtasks.objects.get_or_create(
        problem_id=problem,
        subtask_no=1,
        defaults={
            'time_limit_ms': 1000,
            'memory_limit_mb': 256,
            'score': 100,
        }
    )
    
    if created:
        print(f"  創建 Subtask 1")
    else:
        print(f"  使用現有 Subtask 1")
    
    # 創建測試案例
    test_case, created = Test_cases.objects.get_or_create(
        subtask_id=subtask,
        idx=1,
        defaults={
            'input_data': '1 2\n',
            'output_data': '3\n',
            'score': 100,
        }
    )
    
    if created:
        print(f"    創建 Test Case 1")
    else:
        print(f"    使用現有 Test Case 1")
    
    return problem

def main():
    print("=" * 60)
    print("  創建測試 Problem")
    print("=" * 60)
    
    problem = create_test_problem()
    
    if problem:
        print("\n" + "=" * 60)
        print("  題目資訊")
        print("=" * 60)
        print(f"Problem ID: {problem.id}")
        print(f"Title: {problem.title}")
        print(f"Difficulty: {problem.difficulty}")
        print(f"\nSubtasks: {problem.subtasks.count()}")
        for subtask in problem.subtasks.all():
            print(f"  - Subtask {subtask.subtask_no}: {subtask.test_cases.count()} test cases")
        
        print("\n測試環境準備完成！")
        print(f"\n現在可以使用 Problem ID: {problem.id} 進行測試")

if __name__ == "__main__":
    main()
