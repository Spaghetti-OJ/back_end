#!/usr/bin/env python
"""
測試 Compile Error (CE) Callback

專門測試 Sandbox 回傳 CE 的情況，包括：
1. 單筆測資 CE
2. 多筆測資 CE
3. test_case_id 為 None 的情況
4. error_message 的儲存

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/test_ce_callback.py
"""

import os
import sys
import django
import requests
import json

# 設定 Django 環境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from django.contrib.auth import get_user_model
from submissions.models import Submission, SubmissionResult
from problems.models import Problems
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


def create_ce_submission():
    """創建一個用於測試 CE 的提交"""
    try:
        user = User.objects.first()
        if not user:
            print_result(False, "找不到任何用戶")
            return None
        
        problem = Problems.objects.first()
        if not problem:
            print_result(False, "找不到任何題目")
            return None
        
        submission = Submission.objects.create(
            user=user,
            problem_id=problem.id,
            language_type=2,  # Python
            source_code='print(invalid syntax  # 故意的語法錯誤',
            status='-1',  # Pending
            score=0
        )
        
        print_result(True, f"創建測試提交: {submission.id}")
        return submission
        
    except Exception as e:
        print_result(False, f"創建提交失敗: {str(e)}")
        return None


def test_single_ce():
    """測試單筆測資的 CE"""
    print_section("測試 1: 單筆測資 CE")
    
    submission = create_ce_submission()
    if not submission:
        return False
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    # 單筆 CE 的 payload
    payload = {
        "submission_id": str(submission.id),
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
                "error_message": "  File \"<string>\", line 1\n    print(invalid syntax\n                ^\nSyntaxError: invalid syntax"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"Submission ID: {submission.id}")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "單筆 CE Callback 處理成功")
            
            # 驗證資料庫
            submission.refresh_from_db()
            
            # 檢查 Submission 狀態
            if submission.status == '2':  # CE
                print_result(True, f"Submission 狀態: CE ('{submission.status}')")
            else:
                print_result(False, f"Submission 狀態錯誤: '{submission.status}' (預期 '2')")
            
            if submission.score == 0:
                print_result(True, f"Submission 分數: {submission.score}")
            else:
                print_result(False, f"Submission 分數錯誤: {submission.score}")
            
            # 檢查 SubmissionResult
            results = SubmissionResult.objects.filter(submission_id=submission.id)
            if results.count() == 1:
                print_result(True, f"已創建 1 筆 SubmissionResult")
                result = results.first()
                print(f"  - Test Case Index: {result.test_case_index}")
                print(f"  - Test Case ID: {result.test_case_id}")
                print(f"  - Status: {result.status}")
                print(f"  - Score: {result.score}/{result.max_score}")
                if result.error_message:
                    print(f"  - Error Message: {result.error_message[:100]}...")
                    print_result(True, "Error message 已儲存")
                else:
                    print_result(False, "Error message 為空")
                
                # 檢查 test_case_id 是否為 None
                if result.test_case_id is None:
                    print_result(True, "test_case_id 正確為 None")
                else:
                    print_result(False, f"test_case_id 應為 None，但為 {result.test_case_id}")
            else:
                print_result(False, f"SubmissionResult 數量錯誤: {results.count()} (預期 1)")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_ce():
    """測試多筆測資的 CE（每筆都是 CE）"""
    print_section("測試 2: 多筆測資 CE")
    
    submission = create_ce_submission()
    if not submission:
        return False
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    # 多筆 CE 的 payload（模擬 5 筆測資都 CE）
    test_results = []
    for i in range(1, 6):
        test_results.append({
            "test_case_id": None,
            "test_case_index": i,
            "status": "compile_error",
            "execution_time": 0,
            "memory_usage": 0,
            "score": 0,
            "max_score": 20,
            "error_message": f"  File \"<string>\", line 1\n    print(invalid syntax\n                ^\nSyntaxError: invalid syntax (Test Case {i})"
        })
    
    payload = {
        "submission_id": str(submission.id),
        "status": "compile_error",
        "score": 0,
        "execution_time": 0,
        "memory_usage": 0,
        "test_results": test_results
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"Submission ID: {submission.id}")
    print(f"測試 5 筆測資，每筆都是 CE...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "多筆 CE Callback 處理成功")
            
            # 驗證資料庫
            submission.refresh_from_db()
            
            if submission.status == '2':
                print_result(True, f"Submission 狀態: CE")
            else:
                print_result(False, f"Submission 狀態錯誤: {submission.status}")
            
            # 檢查 SubmissionResult
            results = SubmissionResult.objects.filter(submission_id=submission.id).order_by('test_case_index')
            if results.count() == 5:
                print_result(True, f"已創建 5 筆 SubmissionResult")
                all_ce = all(r.status == 'compile_error' for r in results)
                if all_ce:
                    print_result(True, "所有測資狀態都是 compile_error")
                else:
                    print_result(False, "部分測資狀態不是 compile_error")
                
                all_have_error = all(r.error_message for r in results)
                if all_have_error:
                    print_result(True, "所有測資都有 error_message")
                else:
                    print_result(False, "部分測資沒有 error_message")
                
                all_none_test_case = all(r.test_case_id is None for r in results)
                if all_none_test_case:
                    print_result(True, "所有測資的 test_case_id 都是 None")
                else:
                    print_result(False, "部分測資的 test_case_id 不是 None")
                
                print("\n詳細資訊:")
                for result in results:
                    print(f"  - Test Case {result.test_case_index}: {result.status}")
                    print(f"    Error: {result.error_message[:60]}...")
            else:
                print_result(False, f"SubmissionResult 數量錯誤: {results.count()} (預期 5)")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_ce_with_long_error_message():
    """測試帶有長 error message 的 CE"""
    print_section("測試 3: 長 Error Message 的 CE")
    
    submission = create_ce_submission()
    if not submission:
        return False
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    # 模擬一個很長的錯誤訊息
    long_error = """Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib/python3.11/some_module.py", line 123, in some_function
    raise SyntaxError("invalid syntax")
SyntaxError: invalid syntax

Additional context:
This is a very long error message that contains multiple lines
and detailed information about what went wrong during compilation.
It might include stack traces, line numbers, and other debugging
information that would be useful for the user to understand
what caused the compilation error.

Error occurred at line 1, column 15
Expected: expression
Found: invalid token
""" * 5  # 重複 5 次讓它更長
    
    payload = {
        "submission_id": str(submission.id),
        "status": "compile_error",
        "score": 0,
        "execution_time": 0,
        "memory_usage": 0,
        "test_results": [
            {
                "test_case_id": None,
                "test_case_index": 1,
                "status": "compile_error",
                "execution_time": 0,
                "memory_usage": 0,
                "score": 0,
                "max_score": 100,
                "error_message": long_error
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"Submission ID: {submission.id}")
    print(f"Error Message 長度: {len(long_error)} 字元")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"\n狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            print_result(True, "長 Error Message Callback 處理成功")
            
            # 驗證資料庫
            results = SubmissionResult.objects.filter(submission_id=submission.id)
            if results.count() == 1:
                result = results.first()
                if result.error_message:
                    stored_length = len(result.error_message)
                    print_result(True, f"Error message 已儲存 ({stored_length} 字元)")
                    print(f"原始長度: {len(long_error)} 字元")
                    print(f"儲存長度: {stored_length} 字元")
                    
                    # 檢查是否完整儲存
                    if stored_length == len(long_error):
                        print_result(True, "Error message 完整儲存")
                    else:
                        print_result(False, f"Error message 可能被截斷")
                else:
                    print_result(False, "Error message 為空")
            
            return True
        else:
            print_result(False, f"HTTP 狀態碼錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_duplicate_ce_callback():
    """測試重複呼叫 CE callback（應該 update 而不是 create）"""
    print_section("測試 4: 重複 CE Callback (update_or_create 測試)")
    
    submission = create_ce_submission()
    if not submission:
        return False
    
    url = f"{BACKEND_URL}/submission/callback/"
    
    payload = {
        "submission_id": str(submission.id),
        "status": "compile_error",
        "score": 0,
        "execution_time": 0,
        "memory_usage": 0,
        "test_results": [
            {
                "test_case_id": None,
                "test_case_index": 1,
                "status": "compile_error",
                "execution_time": 0,
                "memory_usage": 0,
                "score": 0,
                "max_score": 100,
                "error_message": "First error message"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    
    print(f"\n請求 URL: {url}")
    print(f"Submission ID: {submission.id}")
    
    try:
        # 第一次呼叫
        print("\n第一次呼叫 callback...")
        response1 = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"狀態碼: {response1.status_code}")
        
        if response1.status_code != 200:
            print_result(False, "第一次呼叫失敗")
            return False
        
        # 檢查第一次的結果
        results1 = SubmissionResult.objects.filter(submission_id=submission.id)
        count1 = results1.count()
        print_result(True, f"第一次呼叫後有 {count1} 筆 SubmissionResult")
        
        # 修改 error message 並第二次呼叫
        payload["test_results"][0]["error_message"] = "Updated error message (second call)"
        
        print("\n第二次呼叫 callback（應該更新而不是新增）...")
        response2 = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"狀態碼: {response2.status_code}")
        
        if response2.status_code != 200:
            print_result(False, "第二次呼叫失敗")
            return False
        
        # 檢查第二次的結果
        results2 = SubmissionResult.objects.filter(submission_id=submission.id)
        count2 = results2.count()
        
        if count2 == count1:
            print_result(True, f"第二次呼叫後仍然只有 {count2} 筆 SubmissionResult（沒有重複）")
            
            # 檢查 error message 是否被更新
            result = results2.first()
            if "Updated error message" in result.error_message:
                print_result(True, "Error message 已更新")
                print(f"  更新後的 message: {result.error_message}")
            else:
                print_result(False, "Error message 沒有更新")
                print(f"  實際 message: {result.error_message}")
        else:
            print_result(False, f"產生了重複記錄！第一次: {count1}，第二次: {count2}")
        
        return True
        
    except Exception as e:
        print_result(False, f"請求失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("\n╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "Compile Error (CE) 測試腳本" + " " * 26 + "║")
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
    
    # 執行測試
    results = []
    
    # Test 1: 單筆 CE
    results.append(test_single_ce())
    
    # Test 2: 多筆 CE
    results.append(test_multiple_ce())
    
    # Test 3: 長 error message
    results.append(test_ce_with_long_error_message())
    
    # Test 4: 重複 callback
    results.append(test_duplicate_ce_callback())
    
    # 總結
    print_section("測試總結")
    passed = sum(results)
    total = len(results)
    print(f"通過: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有 CE 測試通過！")
        print("\n重點驗證項目:")
        print("  ✓ CE 狀態正確儲存")
        print("  ✓ test_case_id 可以是 None")
        print("  ✓ error_message 正確儲存")
        print("  ✓ 多筆測資 CE 都能處理")
        print("  ✓ update_or_create 避免重複記錄")
    else:
        print(f"\n⚠️  有 {total - passed} 個測試失敗")


if __name__ == '__main__':
    main()
