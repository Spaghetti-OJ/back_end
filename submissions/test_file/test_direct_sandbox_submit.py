#!/usr/bin/env python
"""
直接向 Sandbox API 發送測試提交
不依賴資料庫中的 Problem 和 Submission

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/test_direct_sandbox_submit.py
"""

import requests
import json
from io import BytesIO
import hashlib

# Sandbox API 配置
SANDBOX_API_URL = "http://34.81.90.111:8000"
SANDBOX_API_KEY = "happylittle7"  # 從沙盒管理員獲取的 API Key

def submit_test_code_to_sandbox():
    """直接向 Sandbox 發送測試提交"""
    
    print("=" * 70)
    print("  直接向 Sandbox API 發送測試提交")
    print("  使用 Sandbox 上已存在的測試題目: test_sidecar")
    print("=" * 70)
    
    # 準備測試數據 - 使用 Sandbox 上已知存在的題目
    submission_id = "test-direct-submit-sidecar-001"
    problem_id = "test_sidecar"  # 使用 Sandbox 歷史記錄中確認存在的題目
    
    # Python A+B 程式
    source_code = """
def solve():
    a, b = map(int, input().split())
    print(a + b)

if __name__ == '__main__':
    solve()
"""
    
    # 準備檔案內容並計算 hash
    file_content = source_code.encode('utf-8')
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # 組裝 payload
    # 嘗試使用 problem_id 作為 hash（有些系統這樣設計）
    data = {
        'submission_id': submission_id,
        'problem_id': problem_id,
        'problem_hash': 'test_sidecar',  # 使用 problem_id 作為 hash
        'mode': 'normal',
        'language': 'python',
        'file_hash': file_hash,  # 使用實際計算的檔案 SHA256 hash
        'time_limit': 1.0,  # 1 秒
        'memory_limit': 262144,  # 256 MB = 256 * 1024 KB
        'use_checker': False,
        'checker_name': 'diff',
        'use_static_analysis': False,
        'priority': 0,
    }
    
    # 準備檔案
    filename = 'solution.py'
    files = {
        'file': (filename, BytesIO(file_content), 'text/plain')
    }
    
    # 顯示請求資訊
    print(f"\n提交資訊:")
    print(f"  - Submission ID: {submission_id}")
    print(f"  - Problem ID: {problem_id}")
    print(f"  - Language: Python")
    print(f"  - File Hash: {file_hash[:16]}...")  # 顯示前 16 個字元
    print(f"  - Time Limit: 1.0s")
    print(f"  - Memory Limit: 256MB")
    print(f"  - Code Length: {len(source_code)} chars")
    
    print(f"\n發送到: {SANDBOX_API_URL}/api/v1/submissions")
    
    # 確認
    user_input = input("\n是否發送真實的 HTTP 請求到 Sandbox？(y/N): ").strip().lower()
    
    if user_input != 'y':
        print("用戶取消")
        return None
    
    try:
        # 發送請求
        print("\n正在發送請求...")
        
        # 準備 headers（包含認證）
        headers = {
            'X-API-KEY': SANDBOX_API_KEY
        }
        
        response = requests.post(
            f"{SANDBOX_API_URL}/api/v1/submissions",
            data=data,
            files=files,
            headers=headers,
            timeout=30
        )
        
        print(f"\n請求已發送！")
        print(f"狀態碼: {response.status_code}")
        
        # 202 Accepted 是正確的回應（異步處理）
        if response.status_code in [200, 201, 202]:
            try:
                result = response.json()
                print(f"\nSandbox 響應:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                print(f"\n提交成功！現在可以到 Sandbox Dashboard 查看:")
                print(f"   {SANDBOX_API_URL}/dashboard")
                print(f"\n提交 ID: {submission_id}")
                
                return result
            except:
                print(f"\n響應內容:")
                print(response.text)
        else:
            print(f"\n  請求失敗")
            print(f"響應內容:")
            print(response.text)
            
    except requests.Timeout:
        print(f"\n 請求超時 (30秒)")
        
    except requests.RequestException as e:
        print(f"\n 請求失敗: {e}")
        
    except Exception as e:
        print(f"\n 錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def check_sandbox_dashboard():
    """檢查 Sandbox Dashboard 是否可訪問"""
    
    print("\n" + "=" * 70)
    print("  檢查 Sandbox Dashboard")
    print("=" * 70)
    
    try:
        response = requests.get(f"{SANDBOX_API_URL}/dashboard", timeout=5)
        
        if response.status_code == 200:
            print(f"\n Dashboard 可訪問: {SANDBOX_API_URL}/dashboard")
            print(f"   你可以在瀏覽器中打開查看提交記錄")
            return True
        else:
            print(f"\n !  Dashboard 返回狀態碼: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n 無法訪問 Dashboard: {e}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          直接向 Sandbox API 發送測試提交                         ║
║    不依賴資料庫，直接測試 Sandbox API 功能                       ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # 步驟 1: 檢查 Dashboard
    dashboard_ok = check_sandbox_dashboard()
    
    if not dashboard_ok:
        print("\n建議先確認 Sandbox API 是否正常運行")
        user_input = input("是否繼續測試提交？(y/N): ").strip().lower()
        if user_input != 'y':
            return
    
    # 步驟 2: 發送測試提交
    result = submit_test_code_to_sandbox()
    
    # 步驟 3: 總結
    print("\n" + "=" * 70)
    print("  測試總結")
    print("=" * 70)
    
    if result:
        print(f"""
 測試成功！

 下一步:
  1. 打開瀏覽器訪問: {SANDBOX_API_URL}/dashboard
  2. 查找 submission_id: test-direct-submit-001
  3. 查看判題狀態和結果
  
  注意:
  - 因為沒有真實的 problem_hash，Sandbox 可能會找不到測試數據
  - 但提交記錄應該會出現在 Dashboard 中
  - 你應該能看到提交被接收的記錄
        """)
    else:
        print(f"""
 測試失敗

 故障排除:
  1. 檢查 Sandbox API 是否正常運行: {SANDBOX_API_URL}
  2. 檢查網絡連接
  3. 查看錯誤訊息並調整參數
  4. 確認 API endpoint 正確: POST /api/v1/submissions
        """)

if __name__ == "__main__":
    main()
