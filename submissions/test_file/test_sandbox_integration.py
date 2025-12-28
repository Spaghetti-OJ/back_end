#!/usr/bin/env python
"""
Sandbox 整合測試腳本
測試提交流程 → Celery 任務 → Sandbox API 調用

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/test_sandbox_integration.py
"""

import requests
import time
import json

# 測試配置
BASE_URL = "http://127.0.0.1:8000"
SANDBOX_URL = "http://34.81.90.111:8000"

def print_section(title):
    """列印分隔線"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_sandbox_api_reachable():
    """測試 Sandbox API 是否可達"""
    print_section("測試 1: Sandbox API 連通性")
    try:
        response = requests.get(f"{SANDBOX_URL}/docs", timeout=5)
        if response.status_code == 200:
            print(" Sandbox API 可訪問")
            return True
        else:
            print(f"  Sandbox API 返回狀態碼: {response.status_code}")
            return False
    except Exception as e:
        print(f" 無法連接到 Sandbox API: {e}")
        return False

def test_submission_flow_with_auth(token, problem_id=1):
    """測試完整的提交流程（需要認證 Token）"""
    print_section("測試 2: 完整提交流程")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 步驟 1: 創建提交
    print("\n[步驟 1] 創建提交...")
    print(f"  使用 Problem ID: {problem_id} (Backend) -> 會映射到 Sandbox 的 'hello_world'")
    
    # Hello World 程式碼（對應 Sandbox 的 hello_world 題目）
    code = """name = input()
print(f"Hello, {name}!")
"""
    
    payload = {
        "problem_id": problem_id,
        "language_type": 2,  # Python
        "source_code": code
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/submission/",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code != 201:
            print(" 創建提交失敗")
            return None
        
        # 從響應中提取 submission_id
        message = response.json().get("message", "")
        if "submission received." in message:
            submission_id = message.split(".")[-1]
            print(f" 提交已創建: {submission_id}")
        else:
            print(" 無法提取 submission_id")
            return None
            
    except Exception as e:
        print(f" 請求失敗: {e}")
        return None
    
    # 步驟 2: 上傳程式碼
    print(f"\n[步驟 2] 上傳程式碼到 {submission_id}...")
    source_code = """
def solve():
    a, b = map(int, input().split())
    print(a + b)

if __name__ == '__main__':
    solve()
"""
    
    payload = {"source_code": source_code}
    
    try:
        response = requests.put(
            f"{BASE_URL}/submission/{submission_id}/",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code != 200:
            print(" 上傳程式碼失敗")
            return submission_id
        
        print(f" 程式碼已上傳，應已觸發 Celery 任務")
        
    except Exception as e:
        print(f" 請求失敗: {e}")
        return submission_id
    
    # 步驟 3: 查詢提交狀態
    print(f"\n[步驟 3] 查詢提交狀態...")
    time.sleep(2)  # 等待 Celery 處理
    
    try:
        response = requests.get(
            f"{BASE_URL}/submission/{submission_id}/",
            headers=headers,
            timeout=10
        )
        
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            data = response.json().get("data", {})
            status = data.get("status")
            print(f"提交狀態: {status}")
            print(f"完整響應: {json.dumps(data, indent=2, ensure_ascii=False)}")
            print(" 查詢成功")
        else:
            print(f" 查詢失敗: {response.text}")
            
    except Exception as e:
        print(f" 請求失敗: {e}")
    
    return submission_id

def test_rejudge_flow(token, submission_id):
    """測試重新判題流程"""
    print_section("測試 3: 重新判題")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/submission/{submission_id}/rejudge",
            headers=headers,
            timeout=10
        )
        
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {response.text}")
        
        if response.status_code == 200:
            print(" 重新判題已觸發")
        else:
            print(f"  重新判題失敗（可能需要老師權限）")
            
    except Exception as e:
        print(f" 請求失敗: {e}")

def main():
    """主測試流程"""
    print("""
╔══════════════════════════════════════════════════════════╗
║           Sandbox 整合測試腳本                           ║
║    測試 Backend → Celery → Sandbox API 整合流程          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 測試 1: Sandbox API 連通性
    sandbox_reachable = test_sandbox_api_reachable()
    
    # 檢查是否有認證 Token
    print_section("認證檢查")
    token = input("\n請輸入你的 JWT Token（或按 Enter 跳過完整測試）: ").strip()
    
    if not token:
        print("\n  沒有提供 Token，跳過需要認證的測試")
        print("\n💡 要獲取 Token，請執行:")
        print("   python submissions/test_file/get_test_token.py")
        return
    
    # 測試 2: 完整提交流程
    problem_id = input("請輸入要測試的 Problem ID（預設 1）: ").strip() or "1"
    submission_id = test_submission_flow_with_auth(token, int(problem_id))
    
    if not submission_id:
        print("\n 提交流程失敗，無法繼續測試")
        return
    
    # 測試 3: 重新判題
    rejudge = input("\n是否測試重新判題？(y/N): ").strip().lower()
    if rejudge == 'y':
        test_rejudge_flow(token, submission_id)
    
    # 總結
    print_section("測試總結")
    print(f"""
測試完成！

 已完成的測試:
  - Sandbox API 連通性: {'通過' if sandbox_reachable else '失敗'}
  - 創建提交: {'通過' if submission_id else '失敗'}
  - 上傳程式碼並觸發 Celery: 請檢查 Celery Worker 日誌

 後續檢查項目:
  1. 查看 Celery Worker 終端，確認任務被執行
  2. 檢查是否有到 Sandbox API 的 HTTP 請求日誌
  3. 如果 Sandbox 返回錯誤，檢查請求參數是否正確

 Celery Worker 日誌位置:
  你運行 celery -A back_end worker -l info 的終端

  注意事項:
  - 如果沒有 Problem ID {problem_id}，會創建提交失敗
  - 重新判題需要老師/TA 權限
  - Sandbox API 可能有速率限制
    """)

if __name__ == "__main__":
    main()
