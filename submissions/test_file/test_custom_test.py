#!/usr/bin/env python
"""
Custom Test (自定義測試) 功能測試
測試 /submission/custom-test/ API 端點

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/test_custom_test.py

功能說明:
    1. 測試 Custom Test API 端點
    2. 測試 Celery 異步任務
    3. 測試 Redis 快取機制
    4. 測試查詢測試結果
"""

import os
import sys
import django
import time
import json

# 添加專案根目錄到 Python 路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

import requests
from user.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from problems.models import Problems

# 測試配置
BASE_URL = "http://127.0.0.1:8000"
SANDBOX_URL = "http://34.81.90.111:8000"

def print_section(title):
    """列印分隔線"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def get_or_create_test_user():
    """取得或創建測試用戶"""
    username = "test_custom_test"
    email = "test_custom@example.com"
    password = "test123456"
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_active': True,
        }
    )
    
    if created:
        user.set_password(password)
        user.save()
        print(f"OK:  創建新用戶: {username}")
    else:
        print(f"OK:  使用現有用戶: {username}")
    
    return user

def get_jwt_token(user):
    """生成 JWT Token"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def check_problem_exists(problem_id=1):
    """檢查題目是否存在"""
    try:
        problem = Problems.objects.get(id=problem_id)
        print(f"OK:  找到題目: {problem.title} (ID: {problem_id})")
        return True
    except Problems.DoesNotExist:
        print(f"Not good:  題目不存在 (ID: {problem_id})")
        return False

def test_custom_test_submit(token, problem_id=1):
    """測試提交自定義測試"""
    print_section("測試 1: 提交 Custom Test")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 準備測試數據（注意：problem_id 在 URL 中，不在 body 裡）
    test_data = {
        "language": 2,  # Python
        "source_code": """
def solve():
    a, b = map(int, input().split())
    print(a + b)

if __name__ == '__main__':
    solve()
""",
        "stdin": "3 5"  # 測試輸入: 3 + 5 = 8
    }
    
    print("\n[提交資料]")
    print(f"  - Problem ID: {problem_id}")
    print(f"  - Language: Python (2)")
    print(f"  - Stdin: '{test_data['stdin']}'")
    print(f"  - Code: {len(test_data['source_code'])} 字元")
    
    try:
        response = requests.post(
            f"{BASE_URL}/submission/{problem_id}/custom-test/",
            headers=headers,
            json=test_data,
            timeout=15
        )
        
        print(f"\n 回應狀態: {response.status_code}")
        
        if response.status_code == 202:  # Accepted
            result = response.json()
            print(f"[OK] 提交成功")
            print(f"\n回應內容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 提取 test_id
            data = result.get('data', {})
            test_id = data.get('test_id')
            submission_id = data.get('submission_id')
            status_val = data.get('status')
            
            print(f"\n測試資訊:")
            print(f"  - Test ID: {test_id}")
            print(f"  - Submission ID: {submission_id}")
            print(f"  - Status: {status_val}")
            
            return test_id
            
        else:
            print(f"Not good:  提交失敗")
            print(f"回應: {response.text}")
            return None
            
    except Exception as e:
        print(f"Not good:  請求發生錯誤: {e}")
        return None

def test_check_custom_test_result(token, test_id, max_attempts=10):
    """測試查詢自定義測試結果"""
    print_section("測試 2: 查詢 Custom Test 結果")
    
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    print(f"\n查詢 Test ID: {test_id}")
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n嘗試 {attempt}/{max_attempts}...")
        
        try:
            response = requests.get(
                f"{BASE_URL}/submission/custom-test/{test_id}/result/",
                headers=headers,
                timeout=10
            )
            
            print(f"狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                status_val = data.get('status')
                
                print(f"OK:  查詢成功")
                print(f"\n當前狀態: {status_val}")
                print(f"\n完整回應:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # 檢查是否已完成
                if status_val in ['accepted', 'wrong_answer', 'runtime_error', 'time_limit_exceeded', 'completed']:
                    print(f"\nGOOD!! : 測試已完成: {status_val}")
                    return data
                elif status_val == 'failed':
                    print(f"\nNot good:  測試失敗")
                    return data
                else:
                    print(f" 測試進行中: {status_val}")
                    
            elif response.status_code == 404:
                print(f"Not good:  測試結果不存在或已過期")
                return None
            else:
                print(f"Not good:  查詢失敗: {response.text}")
                
        except Exception as e:
            print(f"Not good:  請求發生錯誤: {e}")
        
        # 等待後再次查詢
        if attempt < max_attempts:
            wait_time = 3
            print(f"等待 {wait_time} 秒後重試...")
            time.sleep(wait_time)
    
    print(f"\nWarning :  達到最大查詢次數，測試可能還在執行中")
    return None

def test_invalid_requests(token):
    """測試錯誤的請求"""
    print_section("測試 3: 錯誤請求處理")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 測試 3.1: 缺少必要欄位
    print("\n測試 3.1: 缺少 source_code")
    try:
        response = requests.post(
            f"{BASE_URL}/submission/1/custom-test/",
            headers=headers,
            json={
                "language": 2,
                "stdin": "1 2"
            },
            timeout=10
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 400:
            print(f"OK:  正確回傳 400 Bad Request")
        else:
            print(f"Warning :  預期 400，實際 {response.status_code}")
        print(f"回應: {response.text[:200]}")
    except Exception as e:
        print(f"Not good:  請求錯誤: {e}")
    
    # 測試 3.2: 無效的語言類型
    print("\n測試 3.2: 無效的語言類型")
    try:
        response = requests.post(
            f"{BASE_URL}/submission/1/custom-test/",
            headers=headers,
            json={
                "language": 999,  # 無效
                "source_code": "print('test')",
                "stdin": ""
            },
            timeout=10
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 400:
            print(f"OK:  正確回傳 400 Bad Request")
        else:
            print(f"Warning :  預期 400，實際 {response.status_code}")
        print(f"回應: {response.text[:200]}")
    except Exception as e:
        print(f"Not good:  請求錯誤: {e}")
    
    # 測試 3.3: 不存在的題目
    print("\n測試 3.3: 不存在的題目")
    try:
        response = requests.post(
            f"{BASE_URL}/submission/999999/custom-test/",
            headers=headers,
            json={
                "language": 2,
                "source_code": "print('test')",
                "stdin": ""
            },
            timeout=10
        )
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 404:
            print(f"OK:  正確回傳 404 Not Found")
        else:
            print(f"Warning :  預期 404，實際 {response.status_code}")
        print(f"回應: {response.text[:200]}")
    except Exception as e:
        print(f"Not good:  請求錯誤: {e}")

def test_redis_cache(token, problem_id=1):
    """測試 Redis 快取功能"""
    print_section("測試 4: Redis 快取機制")
    
    print("\n提交多個測試，檢查快取是否正常...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_ids = []
    
    # 提交 3 個測試
    for i in range(3):
        print(f"\n提交測試 #{i+1}...")
        test_data = {
            "language": 2,
            "source_code": f"print('Test {i+1}')",
            "stdin": f"input_{i+1}"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/submission/{problem_id}/custom-test/",
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 202:
                result = response.json()
                test_id = result.get('data', {}).get('test_id')
                test_ids.append(test_id)
                print(f"OK:  提交成功: {test_id}")
            else:
                print(f"Not good:  提交失敗: {response.status_code}")
                
        except Exception as e:
            print(f"Not good:  請求錯誤: {e}")
        
        time.sleep(0.5)  # 短暫延遲
    
    print(f"\n總共提交了 {len(test_ids)} 個測試")
    
    # 查詢所有測試
    print("\n查詢所有測試的狀態...")
    for test_id in test_ids:
        try:
            response = requests.get(
                f"{BASE_URL}/submission/custom-test/{test_id}/result/",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                status_val = response.json().get('data', {}).get('status')
                print(f"  - {test_id}: {status_val}")
            else:
                print(f"  - {test_id}: 查詢失敗 ({response.status_code})")
        except Exception as e:
            print(f"  - {test_id}: 錯誤 ({e})")

def test_celery_task_direct():
    """直接測試 Celery 任務"""
    print_section("測試 5: 直接調用 Celery 任務")
    
    try:
        from submissions.tasks import submit_selftest_to_sandbox_task
        
        print("\n 直接調用 submit_selftest_to_sandbox_task...")
        
        test_data = {
            'test_id': 'direct-test-001',
            'user_id': 1,
            'problem_id': 1,
            'language_type': 2,
            'source_code': 'print("Hello from direct task")',
            'stdin_data': ''
        }
        
        print(f"測試資料: {test_data}")
        
        # 同步調用（測試用）
        result = submit_selftest_to_sandbox_task.apply(
            kwargs=test_data
        )
        
        print(f"\nOK:  任務執行完成")
        print(f"結果: {result.result}")
        
        return result.result
        
    except Exception as e:
        print(f"Not good:  任務執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主測試流程"""
def main():
    """主測試流程"""
    print("""
======================================================================
              Custom Test (自定義測試) 功能測試
        測試 Backend -> Celery -> Redis -> Sandbox 整合
======================================================================
    """)
    
    # 準備測試環境
    print_section("環境準備")
    
    print("\n1. 檢查用戶...")
    user = get_or_create_test_user()
    token = get_jwt_token(user)
    print(f"[OK] Token 已生成")
    
    print("\n2. 檢查題目...")
    problem_id = 1
    if not check_problem_exists(problem_id):
        print(f"\n[WARNING] 題目 {problem_id} 不存在")
        print("\n[提示] 請先創建測試題目:")
        print("   python submissions/test_file/create_test_problem.py")
        create_problem = input("\n是否繼續測試（會失敗）？(y/N): ").strip().lower()
        if create_problem != 'y':
            print("\n測試取消")
            print("\n[步驟] 快速創建題目步驟:")
            print("   1. python submissions/test_file/create_test_problem.py")
            print("   2. python submissions/test_file/test_custom_test.py")
            return
    
    # 準備測試環境
    print_section("環境準備")
    
    print("\n1. 檢查用戶...")
    user = get_or_create_test_user()
    token = get_jwt_token(user)
    print(f"OK:  Token 已生成")
    
    print("\n2. 檢查題目...")
    problem_id = 1
    if not check_problem_exists(problem_id):
        print(f"\nWarning :  題目 {problem_id} 不存在，請先創建題目")
        create_problem = input("是否繼續測試？(y/N): ").strip().lower()
        if create_problem != 'y':
            print("測試取消")
            return
    
    print("\n3. 檢查 Backend 服務...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"OK:  Backend 服務運行中 (狀態碼: {response.status_code})")
    except Exception as e:
        print(f"Not good:  Backend 服務無法連接: {e}")
        print("請確認 Django 開發伺服器已啟動")
        return
    
    print("\n4. 檢查 Sandbox API...")
    try:
        response = requests.get(f"{SANDBOX_URL}/docs", timeout=5)
        print(f"OK:  Sandbox API 可訪問")
    except Exception as e:
        print(f"Warning :  Sandbox API 無法連接: {e}")
        print("測試將繼續，但可能無法完成判題")
    
    # 開始測試
    input("\n按 Enter 開始測試...")
    
    # 測試 1: 提交 Custom Test
    test_id = test_custom_test_submit(token, problem_id)
    
    if test_id:
        # 測試 2: 查詢結果
        test_check_custom_test_result(token, test_id)
    
    # 測試 3: 錯誤請求
    test_invalid_requests(token)
    
    # 測試 4: Redis 快取
    test_redis_cache(token, problem_id)
    
    # 測試 5: 直接測試 Celery 任務（可選）
    print("\n")
    test_celery = input("是否直接測試 Celery 任務？(y/N): ").strip().lower()
    if test_celery == 'y':
        test_celery_task_direct()
    
    # 測試完成
    print_section("測試完成")
    print("""
OK:  測試流程已完成

 後續步驟:
   1. 檢查 Django logs 確認 Celery 任務是否執行
   2. 檢查 Redis 確認快取是否正確儲存
   3. 檢查 Sandbox logs 確認是否收到請求
   
 相關指令:
   - 查看 Celery worker: celery -A back_end worker -l info
   - 查看 Redis: redis-cli -n 2
   - 清除 Redis 快取: redis-cli -n 2 FLUSHDB
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWarning :  測試被使用者中斷")
    except Exception as e:
        print(f"\n\nNot good:  測試發生未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()
