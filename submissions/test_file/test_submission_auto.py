#!/usr/bin/env python
"""
自動化 Submission 測試
測試一般提交流程
"""

import requests
import time
import sys
import os
import django

# Django 設置
sys.path.insert(0, '/Users/keliangyun/Desktop/software_engineering/back_end')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

BASE_URL = "http://127.0.0.1:8000"
SANDBOX_URL = "http://34.81.90.111:8000"

def get_token():
    """獲取測試用戶的 Token"""
    try:
        user = User.objects.get(username='test_sandbox')
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    except User.DoesNotExist:
        print("錯誤: 找不到 test_sandbox 用戶")
        print("請先執行: python submissions/test_file/get_test_token.py")
        return None

def test_submission(token, problem_id=1):
    """測試提交流程"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n" + "=" * 60)
    print("  步驟 1: 創建提交")
    print("=" * 60)
    
    # A + B Problem 的 Python 解答
    code = """a, b = map(int, input().split())
print(a + b)
"""
    
    create_data = {
        "problem_id": problem_id,
        "language_type": 2,  # Python
        "source_code": code
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/submission/",
            json=create_data,
            headers=headers,
            timeout=10
        )
        
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {response.json()}")
        
        if response.status_code != 201:
            print(f"[錯誤] 創建提交失敗")
            return None
            
        # 從 message 中提取 submission_id
        message = response.json().get('message', '')
        if 'submission received.' in message:
            submission_id = message.split('submission received.')[1]
            print(f"\n[成功] 提交已創建並上傳")
            print(f"  Submission ID: {submission_id}")
            print(f"  Celery 任務應該已觸發")
        else:
            print(f"[錯誤] 無法獲取 submission_id")
            return None
        
    except Exception as e:
        print(f"[錯誤] 請求失敗: {e}")
        return None
    
    print("\n" + "=" * 60)
    print("  步驟 2: 查詢提交狀態")
    print("=" * 60)
    
    for i in range(6):
        time.sleep(2)
        
        try:
            response = requests.get(
                f"{BASE_URL}/submission/{submission_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', -1)
                verdict = data.get('verdict', 'Unknown')
                
                print(f"\n[查詢 {i+1}]")
                print(f"  Status: {status}")
                print(f"  Verdict: {verdict}")
                
                if status != -1:  # 不是 Pending
                    print(f"\n[完成] 判題完成")
                    print(f"  最終狀態: {verdict}")
                    break
            else:
                print(f"[查詢 {i+1}] 狀態碼: {response.status_code}")
                
        except Exception as e:
            print(f"[查詢 {i+1}] 請求失敗: {e}")
    
    return submission_id

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         自動化 Submission 測試                           ║
║    測試 Backend → Celery → Sandbox API 整合流程          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 檢查 Sandbox API
    print("\n" + "=" * 60)
    print("  前置檢查: Sandbox API 連通性")
    print("=" * 60)
    
    try:
        response = requests.get(f"{SANDBOX_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("[成功] Sandbox API 可訪問")
        else:
            print(f"[警告] Sandbox API 返回狀態碼: {response.status_code}")
    except Exception as e:
        print(f"[錯誤] 無法連接到 Sandbox API: {e}")
    
    # 獲取 Token
    print("\n" + "=" * 60)
    print("  前置檢查: 獲取認證 Token")
    print("=" * 60)
    
    token = get_token()
    if not token:
        return
    
    print("[成功] Token 已獲取")
    
    # 執行測試
    submission_id = test_submission(token, problem_id=1)
    
    if submission_id:
        print("\n" + "=" * 60)
        print("  測試總結")
        print("=" * 60)
        print(f"[完成] Submission ID: {submission_id}")
        print("\n請檢查:")
        print("  1. Celery Worker 終端日誌")
        print("  2. Django Server 終端日誌")
        print(f"  3. Sandbox Dashboard: {SANDBOX_URL}/dashboard")
    else:
        print("\n[失敗] 測試未完成")

if __name__ == '__main__':
    main()
