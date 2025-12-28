#!/usr/bin/env python
"""
測試 Sandbox Callback APIs

測試以下兩個 API：
1. SubmissionCallbackAPIView - 正式提交的 callback
2. CustomTestCallbackAPIView - 自定義測試的 callback

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/test_callback_apis.py
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# 設定 Django 環境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from django.contrib.auth import get_user_model
from submissions.models import Submission, SubmissionResult, CustomTest
from problems.models import Problems, Problem_subtasks, Test_cases
from django.conf import settings

User = get_user_model()

# 測試配置
BACKEND_URL = "http://127.0.0.1:8443"
API_KEY = getattr(settings, 'SANDBOX_API_KEY', 'happylittle7')


def print_section(title):
    """列印分隔線"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(success, message):
    """列印測試結果"""
    status = "✓ 成功" if success else "✗ 失敗"
    print(f"{status}: {message}")


def create_test_data():
    """創建測試用的資料"""
    print_section("準備測試資料")
    
    # 1. 創建測試用戶
    try:
        user = User.objects.get(username='test_callback')
        print_result(True, f"使用現有用戶: {user.username}")
    except User.DoesNotExist:
        try:
            user = User.objects.create_user(
                username='test_callback',
                email='test_callback@example.com',
                password='test123456'
            )
            print_result(True, f"創建新用戶: {user.username}")
        except Exception as e:
            # 如果 email 已存在，嘗試找到該用戶或使用不同的 email
            try:
                user = User.objects.get(email='test_callback@example.com')
                print_result(True, f"使用現有用戶 (透過 email): {user.username}")
            except User.DoesNotExist:
                # 使用帶時間戳的 email
                import time
                unique_email = f'test_callback_{int(time.time())}@example.com'
                user = User.objects.create_user(
                    username='test_callback',
                    email=unique_email,
                    password='test123456'
                )
                print_result(True, f"創建新用戶 (unique email): {user.username}")
    
    # 2. 創建測試題目（如果不存在）
    try:
        problem = Problems.objects.get(id=1)
        print_result(True, f"使用現有題目: Problem ID {problem.id}")
    except Problems.DoesNotExist:
        print_result(False, "找不到 Problem ID 1，請先創建測試題目")
        return None, None, None, None
    
    # 3. 創建 subtask 和 test_case（如果不存在）
    subtask, created = Problem_subtasks.objects.get_or_create(
        problem_id=problem.id,
        subtask_no=1,
        defaults={
            'time_limit_ms': 1000,
            'memory_limit_mb': 256,
            'score': 100
        }
    )
    if created:
        print_result(True, f"創建 Subtask 1")
    else:
        print_result(True, f"使用現有 Subtask 1")
    
    test_case, created = Test_cases.objects.get_or_create(
        subtask_id=subtask,  # 使用 subtask 實例
        idx=1,
        defaults={
            'input_path': '/media/testcases/problem_1/subtask_1/1.in',
            'output_path': '/media/testcases/problem_1/subtask_1/1.out',
            'status': 'ready'
        }
    )
    if created:
        print_result(True, f"創建 Test Case 1")
    else:
        print_result(True, f"使用現有 Test Case 1 (ID: {test_case.id})")
    
    # 4. 創建測試提交
    submission = Submission.objects.create(
        user=user,
        problem_id=problem.id,
        language_type=2,  # Python
        source_code='print(int(input()) + int(input()))',
        status='-1',  # Pending
        score=0
    )
    print_result(True, f"創建測試提交: {submission.id}")
    
    return user, problem, test_case, submission


def test_submission_callback(submission_id, test_case_id):
    """測試正式提交的 callback API"""
    print_section("測試 1: Submission Callback API (AC 情況)")
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    # 準備測試資料（按照文件規格）
    payload = {
        "submission_id": str(submission_id),
        "status": "accepted",
        "score": 100,
        "execution_time": 123,
        "memory_usage": 1024,
        "test_results": [
            {
                "test_case_id": test_case_id,  # 使用實際的資料庫 ID
                "test_case_index": 1,           # 顯示編號
                "status": "accepted",
                "execution_time": 50,
                "memory_usage": 512,
                "score": 100,
                "max_score": 100,
                "error_message": None
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"API Key: {API_KEY}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "Callback 處理成功")
            
            # 驗證資料庫更新
            submission = Submission.objects.get(id=submission_id)
            if submission.status == '0':  # AC
                print_result(True, f"Submission 狀態已更新為 AC")
            else:
                print_result(False, f"Submission 狀態錯誤: {submission.status}")
            
            if submission.score == 100:
                print_result(True, f"Submission 分數已更新: {submission.score}")
            else:
                print_result(False, f"Submission 分數錯誤: {submission.score}")
            
            # 檢查 SubmissionResult
            results = SubmissionResult.objects.filter(submission_id=submission_id)
            if results.count() > 0:
                print_result(True, f"已創建 {results.count()} 筆 SubmissionResult")
                for result in results:
                    print(f"  - Test Case {result.test_case_index}: {result.status}, Score: {result.score}/{result.max_score}")
            else:
                print_result(False, "沒有創建 SubmissionResult")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        return False


def test_submission_callback_with_ce():
    """測試編譯錯誤的 callback（test_case_id 為 None）"""
    print_section("測試 2: Submission Callback API (Compile Error)")
    
    # 創建新的提交用於測試 CE
    try:
        user = User.objects.filter(username='test_callback').first() or User.objects.first()
        if not user:
            print_result(False, "找不到任何用戶")
            return False
        problem = Problems.objects.get(id=1)
    except Problems.DoesNotExist:
        print_result(False, "找不到測試題目")
        return False
    except Exception as e:
        print_result(False, f"錯誤: {str(e)}")
        return False
    
    ce_submission = Submission.objects.create(
        user=user,
        problem_id=problem.id,
        language_type=2,  # Python
        source_code='print(invalid syntax',  # 故意的語法錯誤
        status='-1',  # Pending
        score=0
    )
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    # CE 的測試資料（test_case_id 為 None）
    payload = {
        "submission_id": str(ce_submission.id),
        "status": "compile_error",
        "score": 0,
        "execution_time": 0,
        "memory_usage": 0,
        "test_results": [
            {
                "test_case_id": None,  # CE 時沒有 test_case_id
                "test_case_index": 1,
                "status": "compile_error",
                "execution_time": 0,
                "memory_usage": 0,
                "score": 0,
                "max_score": 100,
                "error_message": "SyntaxError: invalid syntax at line 1"
            },
            {
                "test_case_id": None,
                "test_case_index": 2,
                "status": "compile_error",
                "execution_time": 0,
                "memory_usage": 0,
                "score": 0,
                "max_score": 100,
                "error_message": "SyntaxError: invalid syntax at line 1"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"Submission ID: {ce_submission.id}")
    print(f"測試多筆 CE 測資...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "CE Callback 處理成功")
            
            # 驗證資料庫更新
            submission = Submission.objects.get(id=ce_submission.id)
            if submission.status == '2':  # CE
                print_result(True, f"Submission 狀態已更新為 CE")
            else:
                print_result(False, f"Submission 狀態錯誤: {submission.status}")
            
            # 檢查 SubmissionResult（CE 應該也要有記錄）
            results = SubmissionResult.objects.filter(submission_id=ce_submission.id)
            if results.count() == 2:
                print_result(True, f"已創建 {results.count()} 筆 CE SubmissionResult（多筆測資）")
                for result in results:
                    print(f"  - Test Case {result.test_case_index}: {result.status}")
                    if result.error_message:
                        print(f"    Error: {result.error_message}")
            else:
                print_result(False, f"SubmissionResult 數量錯誤: {results.count()} (預期 2)")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        return False


def test_custom_test_callback():
    """測試自定義測試的 callback API"""
    print_section("測試 3: Custom Test Callback API")
    
    # 創建測試用的 CustomTest（如果 model 存在）
    try:
        user = User.objects.filter(username='test_callback').first() or User.objects.first()
        if not user:
            print_result(False, "找不到任何用戶")
            return False
        problem = Problems.objects.get(id=1)
        
        custom_test = CustomTest.objects.create(
            user=user,
            problem_id=problem.id,
            language_type=2,  # Python
            source_code='print(input())',
            stdin='Hello World',
            status='pending'
        )
        
        test_id = custom_test.id
        print_result(True, f"創建測試用 CustomTest: {test_id}")
        
    except Exception as e:
        print_result(False, f"無法創建 CustomTest: {str(e)}")
        print("跳過 Custom Test Callback 測試")
        return False
    
    url = f"{BACKEND_URL}/submission/custom-test-callback/"
    
    # 準備測試資料
    payload = {
        "submission_id": str(test_id),
        "status": "completed",
        "stdout": "Hello World\n",
        "stderr": "",
        "execution_time": 50,
        "memory_usage": 512,
        "exit_code": 0
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "Custom Test Callback 處理成功")
            
            # 驗證資料庫更新
            custom_test.refresh_from_db()
            if custom_test.status == 'completed':
                print_result(True, f"CustomTest 狀態已更新為 completed")
            else:
                print_result(False, f"CustomTest 狀態錯誤: {custom_test.status}")
            
            if custom_test.actual_output == "Hello World\n":
                print_result(True, f"CustomTest 輸出已保存")
            else:
                print_result(False, f"CustomTest 輸出錯誤: {custom_test.actual_output}")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        return False


def test_api_key_authentication():
    """測試 API Key 認證"""
    print_section("測試 4: API Key 認證")
    
    try:
        user = User.objects.filter(username='test_callback').first() or User.objects.first()
        if not user:
            print_result(False, "找不到任何用戶")
            return False
        problem = Problems.objects.get(id=1)
    except Problems.DoesNotExist:
        print_result(False, "找不到測試題目")
        return False
    except Exception as e:
        print_result(False, f"錯誤: {str(e)}")
        return False
    
    submission = Submission.objects.create(
        user=user,
        problem_id=problem.id,
        language_type=2,
        source_code='print("test")',
        status='-1',
        score=0
    )
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    payload = {
        "submission_id": str(submission.id),
        "status": "accepted",
        "score": 100,
        "execution_time": 100,
        "memory_usage": 1000,
        "test_results": []
    }
    
    # 測試錯誤的 API Key
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": "wrong_api_key"
    }
    
    print("\n測試錯誤的 API Key...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 401:
            print_result(True, "正確拒絕了錯誤的 API Key (401 Unauthorized)")
            return True
        else:
            print_result(False, f"應該回傳 401，但回傳了 {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        return False


def test_multiple_test_cases():
    """測試多筆測資的情況"""
    print_section("測試 5: 多筆測資 Callback")
    
    try:
        user = User.objects.filter(username='test_callback').first() or User.objects.first()
        if not user:
            print_result(False, "找不到任何用戶")
            return False
        problem = Problems.objects.get(id=1)
    except Problems.DoesNotExist:
        print_result(False, "找不到測試題目")
        return False
    except Exception as e:
        print_result(False, f"錯誤: {str(e)}")
        return False
    
    # 獲取或創建多個 test case
    subtask = Problem_subtasks.objects.filter(problem_id=problem.id).first()
    
    test_cases = []
    for i in range(1, 4):  # 創建 3 個 test case
        tc, created = Test_cases.objects.get_or_create(
            subtask_id=subtask,  # 使用 subtask 實例
            idx=i,
            defaults={
                'input_path': f'/media/testcases/problem_1/subtask_1/{i}.in',
                'output_path': f'/media/testcases/problem_1/subtask_1/{i}.out',
                'status': 'ready'
            }
        )
        test_cases.append(tc)
    
    # 創建新提交
    submission = Submission.objects.create(
        user=user,
        problem_id=problem.id,
        language_type=2,
        source_code='print("test")',
        status='-1',
        score=0
    )
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    # 準備多筆測資的結果
    payload = {
        "submission_id": str(submission.id),
        "status": "wrong_answer",  # 部分錯誤
        "score": 66,
        "execution_time": 200,
        "memory_usage": 2048,
        "test_results": [
            {
                "test_case_id": test_cases[0].id,
                "test_case_index": 1,
                "status": "accepted",
                "execution_time": 60,
                "memory_usage": 600,
                "score": 33,
                "max_score": 33,
                "error_message": None
            },
            {
                "test_case_id": test_cases[1].id,
                "test_case_index": 2,
                "status": "accepted",
                "execution_time": 70,
                "memory_usage": 700,
                "score": 33,
                "max_score": 33,
                "error_message": None
            },
            {
                "test_case_id": test_cases[2].id,
                "test_case_index": 3,
                "status": "wrong_answer",
                "execution_time": 70,
                "memory_usage": 748,
                "score": 0,
                "max_score": 34,
                "error_message": "Expected: 7, Got: 6"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"測試 3 筆測資（2 AC, 1 WA）...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "多筆測資 Callback 處理成功")
            
            # 驗證資料庫
            submission.refresh_from_db()
            results = SubmissionResult.objects.filter(submission_id=submission.id).order_by('test_case_index')
            
            if results.count() == 3:
                print_result(True, f"已創建 3 筆 SubmissionResult")
                for result in results:
                    print(f"  - Test Case {result.test_case_index}: {result.status}, Score: {result.score}/{result.max_score}")
                    if result.error_message:
                        print(f"    Error: {result.error_message}")
            else:
                print_result(False, f"SubmissionResult 數量錯誤: {results.count()} (預期 3)")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        return False


def main():
    """主函數"""
    print("\n╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "Sandbox Callback APIs 測試腳本" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # 確認 Django 伺服器正在運行
    print_section("檢查 Django 伺服器")
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        print_result(True, f"Django 伺服器運行中 ({BACKEND_URL})")
    except Exception as e:
        print_result(False, f"無法連接到 Django 伺服器: {str(e)}")
        print("\n請確保 Django 伺服器正在運行：")
        print("  python manage.py runserver 0.0.0.0:8443")
        return
    
    # 創建測試資料
    user, problem, test_case, submission = create_test_data()
    if not submission:
        print("\n測試終止：無法創建必要的測試資料")
        return
    
    # 執行測試
    results = []
    
    # Test 1: 正常的提交 callback (AC)
    results.append(test_submission_callback(submission.id, test_case.id))
    
    # Test 2: CE 的提交 callback（多筆測資）
    results.append(test_submission_callback_with_ce())
    
    # Test 3: 自定義測試 callback
    results.append(test_custom_test_callback())
    
    # Test 4: API Key 認證
    results.append(test_api_key_authentication())
    
    # Test 5: 多筆測資
    results.append(test_multiple_test_cases())
    
    # 總結
    print_section("測試總結")
    passed = sum(results)
    total = len(results)
    print(f"通過: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有測試通過！")
    else:
        print(f"\n⚠️  有 {total - passed} 個測試失敗")


if __name__ == '__main__':
    main()
