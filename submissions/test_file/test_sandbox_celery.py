#!/usr/bin/env python
"""
直接測試 Celery 任務和 Sandbox 客戶端
不需要創建完整的 Problem 和 Submission

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/test_sandbox_celery.py
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

from submissions.sandbox_client import submit_to_sandbox, SANDBOX_API_URL, SANDBOX_TIMEOUT
import requests

def test_sandbox_api_directly():
    """直接測試 Sandbox API 連通性"""
    print("=" * 70)
    print("  測試 1: Sandbox API 直接連接")
    print("=" * 70)
    
    print(f"\n Sandbox API URL: {SANDBOX_API_URL}")
    print(f"  Timeout: {SANDBOX_TIMEOUT}s")
    
    try:
        # 測試 Docs 端點
        response = requests.get(f"{SANDBOX_API_URL}/docs", timeout=5)
        print(f"\n GET /docs - 狀態碼: {response.status_code}")
        
        # 測試 API endpoint
        response = requests.get(f"{SANDBOX_API_URL}/api/v1/submissions", timeout=5)
        print(f" GET /api/v1/submissions - 狀態碼: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"\n 連接失敗: {e}")
        return False

def test_sandbox_client_with_mock_submission():
    """使用 Mock Submission 測試 sandbox_client"""
    print("\n" + "=" * 70)
    print("  測試 2: Sandbox Client 函數測試")
    print("=" * 70)
    
    from submissions.models import Submission
    from user.models import User
    from problems.models import Problems
    from unittest.mock import Mock
    
    # 創建 Mock Submission
    mock_submission = Mock(spec=Submission)
    mock_submission.id = "test-submission-12345"
    mock_submission.problem_id = 1
    mock_submission.language_type = 2  # Python
    # hello_world 題目的程式碼 (Problem 1 映射到 Sandbox 的 hello_world)
    mock_submission.source_code = """name = input()
print(f"Hello, {name}!")
"""
    mock_submission.code_hash = "abc123def456"  # Mock hash
    
    # 創建 Mock Problem (避免查詢真實資料庫)
    mock_problem = Mock()
    mock_problem.id = 1
    mock_problem.title = "A + B Problem"
    
    # Mock subtask
    mock_subtask = Mock()
    mock_subtask.time_limit_ms = 1000
    mock_subtask.memory_limit_mb = 256
    
    print(f"\n Mock Submission 資訊:")
    print(f"  - ID: {mock_submission.id}")
    print(f"  - Problem ID: {mock_submission.problem_id}")
    print(f"  - Language: {mock_submission.language_type} (Python)")
    print(f"  - Code Length: {len(mock_submission.source_code)} chars")
    
    print(f"\n🔧 嘗試調用 sandbox_client.submit_to_sandbox()...")
    
    try:
        # 注意：這會真的發送到 Sandbox API！
        # 如果不想真的發送，可以註解掉這部分
        
        print("\n  這將會發送真實的 HTTP 請求到 Sandbox API")
        print(f"   URL: {SANDBOX_API_URL}/api/v1/submissions")
        
        user_input = input("\n是否繼續？(y/N): ").strip().lower()
        
        if user_input != 'y':
            print(" 用戶取消測試")
            return False
        
        # 由於我們的 submit_to_sandbox 會查詢 Problem，我們需要 Mock Problems.objects
        print("\n  注意: submit_to_sandbox() 需要查詢資料庫中的 Problem")
        print("   因為資料庫沒有 Problem，這個測試會失敗")
        print("   但我們可以看到錯誤訊息和 Celery 的反應")
        
        result = submit_to_sandbox(mock_submission)
        print(f"\n Sandbox 響應:")
        print(f"   {result}")
        return True
        
    except Exception as e:
        print(f"\n 調用失敗: {e}")
        print(f"   錯誤類型: {type(e).__name__}")
        return False

def test_celery_task_discovery():
    """測試 Celery 是否能發現我們的任務"""
    print("\n" + "=" * 70)
    print("  測試 3: Celery 任務發現")
    print("=" * 70)
    
    try:
        from back_end.celery import app
        
        print(f"\n Celery App: {app}")
        print(f"   Name: {app.main}")
        print(f"   Broker: {app.conf.broker_url}")
        print(f"   Backend: {app.conf.result_backend}")
        
        # 列出已註冊的任務
        registered_tasks = list(app.tasks.keys())
        print(f"\n 已註冊的任務 ({len(registered_tasks)} 個):")
        for task_name in sorted(registered_tasks):
            if not task_name.startswith('celery.'):
                print(f"    {task_name}")
        
        # 檢查我們的任務
        if 'submissions.tasks.submit_to_sandbox_task' in registered_tasks:
            print(f"\n 找到我們的任務: submissions.tasks.submit_to_sandbox_task")
            return True
        else:
            print(f"\n 沒有找到: submissions.tasks.submit_to_sandbox_task")
            return False
            
    except Exception as e:
        print(f"\n 錯誤: {e}")
        return False

def test_celery_task_execution():
    """測試 Celery 任務是否能被調用（但不會真的執行）"""
    print("\n" + "=" * 70)
    print("  測試 4: Celery 任務調用測試")
    print("=" * 70)
    
    try:
        from submissions.tasks import submit_to_sandbox_task
        
        print(f"\n 任務函數: {submit_to_sandbox_task}")
        print(f"   Name: {submit_to_sandbox_task.name}")
        print(f"   Max Retries: {submit_to_sandbox_task.max_retries}")
        
        print(f"\n  注意: 如果資料庫沒有對應的 Submission，任務會失敗")
        print(f"   但我們可以觀察 Celery Worker 的日誌")
        
        user_input = input("\n是否發送測試任務到 Celery？(y/N): ").strip().lower()
        
        if user_input != 'y':
            print(" 用戶取消測試")
            return False
        
        # 發送一個測試任務（會失敗因為沒有這個 Submission）
        test_submission_id = "00000000-0000-0000-0000-000000000000"
        
        print(f"\n 發送任務到 Celery...")
        print(f"   Submission ID: {test_submission_id}")
        
        result = submit_to_sandbox_task.delay(test_submission_id)
        
        print(f"\n 任務已發送到 Celery！")
        print(f"   Task ID: {result.id}")
        print(f"   State: {result.state}")
        
        print(f"\n 請查看 Celery Worker 終端的日誌")
        print(f"   你應該會看到任務被接收並開始執行")
        print(f"   預期會失敗（因為找不到 Submission）")
        
        return True
        
    except Exception as e:
        print(f"\n 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║               Sandbox + Celery 整合測試工具                      ║
║    測試 Sandbox API 連通性、sandbox_client 和 Celery 任務       ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # 測試 1: Sandbox API 連通性
    results.append(("Sandbox API 連通性", test_sandbox_api_directly()))
    
    # 測試 2: Sandbox Client
    test_client = input("\n是否測試 Sandbox Client？(y/N): ").strip().lower()
    if test_client == 'y':
        results.append(("Sandbox Client", test_sandbox_client_with_mock_submission()))
    
    # 測試 3: Celery 任務發現
    results.append(("Celery 任務發現", test_celery_task_discovery()))
    
    # 測試 4: Celery 任務執行
    test_exec = input("\n是否測試 Celery 任務執行？(需要 Celery Worker 運行中) (y/N): ").strip().lower()
    if test_exec == 'y':
        results.append(("Celery 任務執行", test_celery_task_execution()))
    
    # 總結
    print("\n" + "=" * 70)
    print("  測試總結")
    print("=" * 70)
    
    for test_name, passed in results:
        status = " 通過" if passed else " 失敗"
        print(f"  {test_name}: {status}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n 總計: {passed_count}/{total_count} 個測試通過")
    
    print("\n" + "=" * 70)
    print("  下一步")
    print("=" * 70)
    print("""
1.  確認 Redis 正在運行
2.  確認 Celery Worker 正在運行 (celery -A back_end worker -l info)
3.  確認 Django Server 正在運行 (python manage.py runserver)
4.  創建一個真實的 Problem (使用 create_test_problem.py)
5.  創建一個真實的 Submission
6.  測試完整的提交流程 (使用 test_sandbox_integration.py)

提示: 
  - Celery Worker 日誌會顯示任務執行情況
  - Django Server 日誌會顯示 API 請求
  - 使用 submissions/test_file/get_test_token.py 獲取測試 Token
    """)

if __name__ == "__main__":
    main()
