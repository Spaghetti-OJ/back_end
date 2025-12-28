#!/usr/bin/env python
"""
測試 Sandbox Callback APIs

測試 Backend 接收 Sandbox 判題結果的 callback endpoints:
1. POST /submission/callback/ - 正式提交結果
2. POST /submission/custom-test-callback/ - 自定義測試結果

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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from django.conf import settings
from submissions.models import Submission, SubmissionResult, CustomTest
from user.models import User
from problems.models import Problems, Problem_subtasks, Test_cases
from courses.models import Courses
import uuid

# API 設定
BASE_URL = "http://localhost:8000"
API_KEY = settings.SANDBOX_API_KEY  # 從 settings 讀取


class Colors:
    """終端顏色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """列印標題"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")


def print_success(text):
    """列印成功訊息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """列印錯誤訊息"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    """列印資訊"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_warning(text):
    """列印警告"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def create_test_data():
    """建立測試資料"""
    print_header("準備測試資料")
    
    try:
        # 1. 確保有測試用戶
        user, created = User.objects.get_or_create(
            username='test_callback_user',
            defaults={
                'email': 'test_callback@example.com',
                'real_name': 'Test Callback User',
                'identity': 'student'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print_success(f"建立測試用戶: {user.username}")
        else:
            print_info(f"使用現有測試用戶: {user.username}")
        
        # 2. 確保有課程（題目需要課程）
        course, created = Courses.objects.get_or_create(
            name='Test Course for Callback',
            defaults={
                'description': 'Test course for callback testing',
                'teacher_id': user,
                'is_active': True
            }
        )
        if created:
            print_success(f"建立測試課程: {course.name}")
        else:
            print_info(f"使用現有測試課程: {course.name}")
        
        # 3. 使用現有題目或建立最簡單的題目
        try:
            # 嘗試找任意一個現有題目
            problem = Problems.objects.first()
            if not problem:
                # 如果沒有題目，建立最基本的題目（只填必要欄位）
                problem = Problems.objects.create(
                    title='Test Problem for Callback',
                    difficulty='easy',
                    description='Test problem',
                    creator_id=user,
                    course_id=course,
                    is_public='public'
                )
                print_success(f"建立測試題目: {problem.title}")
            else:
                print_info(f"使用現有題目: ID={problem.id}, {problem.title}")
        except Exception as e:
            print_error(f"無法存取題目資料: {str(e)}")
            raise
        
        # 4. 確保有 subtask 和 test case
        subtask = Problem_subtasks.objects.filter(problem_id=problem).first()
        if not subtask:
            subtask = Problem_subtasks.objects.create(
                problem_id=problem,
                subtask_no=1,
                weight=100,
                time_limit_ms=1000,
                memory_limit_mb=256
            )
            print_success(f"建立 Subtask 1")
        else:
            print_info(f"使用現有 Subtask: {subtask.subtask_no}")
        
        test_case = Test_cases.objects.filter(subtask_id=subtask).first()
        if not test_case:
            test_case = Test_cases.objects.create(
                subtask_id=subtask,
                idx=1,
                input_path='test/1.in',
                output_path='test/1.out',
                status='ready'
            )
            print_success(f"建立 Test Case 1")
        else:
            print_info(f"使用現有 Test Case: {test_case.idx}")
        
        # 5. 建立測試 Submission
        submission = Submission.objects.create(
            user=user,
            problem_id=problem.id,
            language_type=2,  # Python
            source_code='print(sum(map(int, input().split())))',
            status=-1,  # Pending
            score=0
        )
        print_success(f"建立測試 Submission: {submission.id}")
        
        # 6. 建立測試 CustomTest
        custom_test = CustomTest.objects.create(
            id=str(uuid.uuid4()),
            user=user,
            problem_id=problem.id,
            language_type=2,  # Python
            source_code='print("Hello, World!")',
            input_data='',
            status=0  # Pending
        )
        print_success(f"建立測試 CustomTest: {custom_test.id}")
        
        return {
            'user': user,
            'problem': problem,
            'test_case': test_case,
            'submission': submission,
            'custom_test': custom_test
        }
        
    except Exception as e:
        print_error(f"建立測試資料失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_submission_callback_success(submission_id, test_case_id):
    """測試 1: 正式提交 Callback - 成功案例"""
    print_header("測試 1: 正式提交 Callback - 成功案例 (Accepted)")
    
    # 重置 submission
    submission = Submission.objects.get(id=submission_id)
    submission.status = -1  # Pending
    submission.score = 0
    submission.save()
    SubmissionResult.objects.filter(submission=submission).delete()
    
    url = f"{BASE_URL}/submission/callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    data = {
        'submission_id': str(submission_id),
        'status': 'accepted',
        'score': 100,
        'execution_time': 123,
        'memory_usage': 1024,
        'test_results': [
            {
                'test_case_id': test_case_id,
                'test_case_index': 1,
                'status': 'accepted',
                'execution_time': 123,
                'memory_usage': 1024,
                'score': 100,
                'max_score': 100,
                'error_message': None
            }
        ]
    }
    
    print_info(f"POST {url}")
    print_info(f"Submission ID: {submission_id}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print_info(f"狀態碼: {response.status_code}")
        print_info(f"回應: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                print_success("測試通過 - Callback 成功處理")
                
                # 驗證資料庫更新
                submission = Submission.objects.get(id=submission_id)
                if submission.status == '0' and submission.score == 100:  # '0' = AC
                    print_success("資料庫驗證通過 - Submission 已更新")
                else:
                    print_error(f"資料庫驗證失敗 - status={submission.status} (期望 '0'), score={submission.score} (期望 100)")
                
                # 驗證 SubmissionResult 建立
                results_count = SubmissionResult.objects.filter(submission=submission).count()
                if results_count == 1:
                    print_success("資料庫驗證通過 - SubmissionResult 已建立")
                else:
                    print_error(f"資料庫驗證失敗 - 期望 1 筆結果，實際 {results_count} 筆")
                
                return True
            else:
                print_error(f"測試失敗 - 回應狀態錯誤: {result}")
                return False
        else:
            print_error(f"測試失敗 - HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_submission_callback_wrong_answer(submission_id, test_case_id):
    """測試 2: 正式提交 Callback - Wrong Answer"""
    print_header("測試 2: 正式提交 Callback - Wrong Answer")
    
    # 重置 submission
    submission = Submission.objects.get(id=submission_id)
    submission.status = -1
    submission.score = 0
    submission.save()
    SubmissionResult.objects.filter(submission=submission).delete()
    
    url = f"{BASE_URL}/submission/callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    data = {
        'submission_id': str(submission_id),
        'status': 'wrong_answer',
        'score': 50,
        'execution_time': 100,
        'memory_usage': 1024,
        'test_results': [
            {
                'test_case_id': test_case_id,
                'test_case_index': 1,
                'status': 'wrong_answer',
                'execution_time': 100,
                'memory_usage': 1024,
                'score': 50,
                'max_score': 100,
                'error_message': 'Expected: 5, Got: 4'
            }
        ]
    }
    
    print_info(f"POST {url}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                print_success("測試通過 - WA 回應成功處理")
                
                submission = Submission.objects.get(id=submission_id)
                if submission.status == '1' and submission.score == 50:  # '1' = WA
                    print_success("資料庫驗證通過 - WA 狀態正確")
                    return True
                else:
                    print_error(f"資料庫驗證失敗 - status={submission.status} (期望 '1'), score={submission.score} (期望 50)")
                    return False
        
        print_error(f"測試失敗 - HTTP {response.status_code}")
        return False
        
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def test_submission_callback_no_api_key(submission_id):
    """測試 3: 正式提交 Callback - 缺少 API Key"""
    print_header("測試 3: 正式提交 Callback - 缺少 API Key (應失敗)")
    
    url = f"{BASE_URL}/submission/callback/"
    headers = {
        'Content-Type': 'application/json'
        # 故意不加 X-API-KEY
    }
    data = {
        'submission_id': str(submission_id),
        'status': 'accepted',
        'score': 100,
        'execution_time': 123,
        'memory_usage': 1024,
        'test_results': []
    }
    
    print_info(f"POST {url}")
    print_warning("故意不傳送 API Key")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 401:
            print_success("測試通過 - 正確拒絕未授權請求 (401)")
            return True
        else:
            print_error(f"測試失敗 - 期望 401，實際 {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def test_submission_callback_wrong_api_key(submission_id):
    """測試 4: 正式提交 Callback - 錯誤的 API Key"""
    print_header("測試 4: 正式提交 Callback - 錯誤的 API Key (應失敗)")
    
    url = f"{BASE_URL}/submission/callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': 'wrong-api-key-123456'
    }
    data = {
        'submission_id': str(submission_id),
        'status': 'accepted',
        'score': 100,
        'execution_time': 123,
        'memory_usage': 1024,
        'test_results': []
    }
    
    print_info(f"POST {url}")
    print_warning("傳送錯誤的 API Key")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 401:
            print_success("測試通過 - 正確拒絕錯誤 API Key (401)")
            return True
        else:
            print_error(f"測試失敗 - 期望 401，實際 {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def test_submission_callback_not_found():
    """測試 5: 正式提交 Callback - Submission 不存在"""
    print_header("測試 5: 正式提交 Callback - Submission 不存在 (應失敗)")
    
    fake_id = str(uuid.uuid4())
    url = f"{BASE_URL}/submission/callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    data = {
        'submission_id': fake_id,
        'status': 'accepted',
        'score': 100,
        'execution_time': 123,
        'memory_usage': 1024,
        'test_results': []
    }
    
    print_info(f"POST {url}")
    print_warning(f"使用不存在的 Submission ID: {fake_id}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 404:
            print_success("測試通過 - 正確回傳 404 Not Found")
            return True
        else:
            print_error(f"測試失敗 - 期望 404，實際 {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def test_submission_callback_missing_field():
    """測試 6: 正式提交 Callback - 缺少必要欄位"""
    print_header("測試 6: 正式提交 Callback - 缺少 submission_id (應失敗)")
    
    url = f"{BASE_URL}/submission/callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    data = {
        # 故意不傳 submission_id
        'status': 'accepted',
        'score': 100,
        'execution_time': 123,
        'memory_usage': 1024,
        'test_results': []
    }
    
    print_info(f"POST {url}")
    print_warning("故意不傳送 submission_id")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 400:
            print_success("測試通過 - 正確回傳 400 Bad Request")
            return True
        else:
            print_error(f"測試失敗 - 期望 400，實際 {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def test_custom_test_callback_success(custom_test_id):
    """測試 7: 自定義測試 Callback - 成功案例"""
    print_header("測試 7: 自定義測試 Callback - 成功案例")
    
    # 重置 custom test
    custom_test = CustomTest.objects.get(id=custom_test_id)
    custom_test.status = 0  # Pending
    custom_test.actual_output = None
    custom_test.error_message = None
    custom_test.save()
    
    url = f"{BASE_URL}/submission/custom-test-callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    data = {
        'submission_id': str(custom_test_id),
        'status': 'completed',
        'stdout': 'Hello, World!\n',
        'stderr': '',
        'execution_time': 50,
        'memory_usage': 512,
        'exit_code': 0
    }
    
    print_info(f"POST {url}")
    print_info(f"CustomTest ID: {custom_test_id}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print_info(f"狀態碼: {response.status_code}")
        print_info(f"回應: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                print_success("測試通過 - Custom Test Callback 成功處理")
                
                # 驗證資料庫更新
                custom_test = CustomTest.objects.get(id=custom_test_id)
                if custom_test.status == 'completed' and custom_test.actual_output == 'Hello, World!\n':
                    print_success("資料庫驗證通過 - CustomTest 已更新")
                    return True
                else:
                    print_error(f"資料庫驗證失敗 - status={custom_test.status} (期望 'completed'), actual_output={repr(custom_test.actual_output)}")
                    return False
        
        print_error(f"測試失敗 - HTTP {response.status_code}")
        return False
        
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_custom_test_callback_error(custom_test_id):
    """測試 8: 自定義測試 Callback - 錯誤案例"""
    print_header("測試 8: 自定義測試 Callback - 執行錯誤")
    
    # 重置 custom test
    custom_test = CustomTest.objects.get(id=custom_test_id)
    custom_test.status = 0  # Pending
    custom_test.actual_output = None
    custom_test.error_message = None
    custom_test.save()
    
    url = f"{BASE_URL}/submission/custom-test-callback/"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY
    }
    data = {
        'submission_id': str(custom_test_id),
        'status': 'error',
        'stdout': '',
        'stderr': 'ZeroDivisionError: division by zero',
        'execution_time': 10,
        'memory_usage': 512,
        'exit_code': 1
    }
    
    print_info(f"POST {url}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                print_success("測試通過 - Error 回應成功處理")
                
                custom_test = CustomTest.objects.get(id=custom_test_id)
                if custom_test.status == 'error' and custom_test.error_message:  # 'error' 狀態
                    print_success("資料庫驗證通過 - Error 狀態正確")
                    return True
                else:
                    print_error(f"資料庫驗證失敗 - status={custom_test.status} (期望 'error'), error_message={custom_test.error_message}")
                    return False
        
        print_error(f"測試失敗 - HTTP {response.status_code}")
        return False
        
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def test_custom_test_callback_no_auth(custom_test_id):
    """測試 9: 自定義測試 Callback - 缺少認證"""
    print_header("測試 9: 自定義測試 Callback - 缺少認證 (應失敗)")
    
    url = f"{BASE_URL}/submission/custom-test-callback/"
    headers = {
        'Content-Type': 'application/json'
        # 故意不加 X-API-KEY
    }
    data = {
        'submission_id': str(custom_test_id),
        'status': 'completed',
        'stdout': 'test',
        'stderr': '',
        'execution_time': 50,
        'memory_usage': 512,
        'exit_code': 0
    }
    
    print_info(f"POST {url}")
    print_warning("故意不傳送 API Key")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 401:
            print_success("測試通過 - 正確拒絕未授權請求 (401)")
            return True
        else:
            print_error(f"測試失敗 - 期望 401，實際 {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"測試失敗 - {str(e)}")
        return False


def main():
    """主測試流程"""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║          Sandbox Callback APIs 測試工具                          ║
║    測試 Backend 接收 Sandbox 判題結果的功能                       ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # 檢查 Django Server
    print_header("前置檢查")
    try:
        # 改用 admin 頁面檢查，因為 /api/ 可能不存在
        response = requests.get(f"{BASE_URL}/admin/", timeout=5, allow_redirects=False)
        if response.status_code in [200, 302]:  # 200 或重定向都表示 server 運行中
            print_success("Django Server 運行中")
        else:
            print_error(f"Django Server 異常 - HTTP {response.status_code}")
            print_warning("請確認 Django Server 是否正常運行")
            return
    except requests.RequestException as e:
        print_error(f"無法連接到 Django Server: {str(e)}")
        print_warning("請先啟動 Django Server: python manage.py runserver")
        return
    
    # 建立測試資料
    test_data = create_test_data()
    if not test_data:
        print_error("無法建立測試資料，終止測試")
        return
    
    submission_id = test_data['submission'].id
    custom_test_id = test_data['custom_test'].id
    test_case_id = test_data['test_case'].id
    
    # 執行測試
    results = []
    
    # 正式提交 Callback 測試
    results.append(("正式提交 - 成功案例", test_submission_callback_success(submission_id, test_case_id)))
    results.append(("正式提交 - Wrong Answer", test_submission_callback_wrong_answer(submission_id, test_case_id)))
    results.append(("正式提交 - 缺少 API Key", test_submission_callback_no_api_key(submission_id)))
    results.append(("正式提交 - 錯誤 API Key", test_submission_callback_wrong_api_key(submission_id)))
    results.append(("正式提交 - Submission 不存在", test_submission_callback_not_found()))
    results.append(("正式提交 - 缺少必要欄位", test_submission_callback_missing_field()))
    
    # 自定義測試 Callback 測試
    results.append(("自定義測試 - 成功案例", test_custom_test_callback_success(custom_test_id)))
    results.append(("自定義測試 - 執行錯誤", test_custom_test_callback_error(custom_test_id)))
    results.append(("自定義測試 - 缺少認證", test_custom_test_callback_no_auth(custom_test_id)))
    
    # 測試總結
    print_header("測試總結")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print(f"\n{Colors.BOLD}總計: {passed}/{total} 測試通過{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有測試通過！{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  有 {total - passed} 個測試失敗{Colors.END}")
    
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.END}\n")


if __name__ == "__main__":
    main()
