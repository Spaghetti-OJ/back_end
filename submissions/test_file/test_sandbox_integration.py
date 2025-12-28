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
import threading
from datetime import datetime

# 測試配置
BASE_URL = "http://127.0.0.1:8443"  # Django 後端運行在 8443 端口
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
    
    # 步驟 2: 上傳程式碼（或檔案）
    print(f"\n[步驟 2] 上傳程式碼到 {submission_id}...")
    source_code = """name = input()
print(f"Hello, {name}!")
"""
    
    # 使用文字提交（source_code）
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

def test_bulk_submissions(token, problem_id=1, total=200, rate_per_second=20):
    """批量提交測試 - 一秒 20 筆，總共 200 筆"""
    print_section(f"批量測試: {total} 筆提交 ({rate_per_second} 筆/秒)")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 準備測試程式碼（簡單的 Hello World）
    test_code = """name = input()
print(f"Hello, {name}!")
"""
    
    # 統計資料
    results = {
        'success': 0,
        'failed': 0,
        'submission_ids': [],
        'errors': []
    }
    
    # 鎖定，保護共享資源
    results_lock = threading.Lock()
    
    def submit_one(batch_num, index_in_batch):
        """提交單筆 submission"""
        try:
            # 步驟 1: 創建提交
            payload = {
                "problem_id": problem_id,
                "language_type": 2,  # Python
                "source_code": test_code
            }
            
            response = requests.post(
                f"{BASE_URL}/submission/",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 201:
                message = response.json().get("message", "")
                if "submission received." in message:
                    submission_id = message.split(".")[-1]
                    
                    # 步驟 2: 立即上傳程式碼
                    upload_payload = {"source_code": test_code}
                    upload_response = requests.put(
                        f"{BASE_URL}/submission/{submission_id}/",
                        headers=headers,
                        json=upload_payload,
                        timeout=10
                    )
                    
                    with results_lock:
                        if upload_response.status_code == 200:
                            results['success'] += 1
                            results['submission_ids'].append(submission_id)
                            print(f"  [{batch_num:02d}-{index_in_batch:02d}] ✓ {submission_id}")
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Upload failed: {submission_id}")
                            print(f"  [{batch_num:02d}-{index_in_batch:02d}] ✗ Upload failed")
                else:
                    with results_lock:
                        results['failed'] += 1
                        results['errors'].append("No submission_id in response")
            else:
                with results_lock:
                    results['failed'] += 1
                    results['errors'].append(f"Create failed: {response.status_code}")
                    print(f"  [{batch_num:02d}-{index_in_batch:02d}] ✗ Create failed: {response.status_code}")
                    
        except Exception as e:
            with results_lock:
                results['failed'] += 1
                results['errors'].append(str(e))
                print(f"  [{batch_num:02d}-{index_in_batch:02d}] ✗ Exception: {e}")
    
    # 計算需要多少批次
    batches = total // rate_per_second
    remaining = total % rate_per_second
    
    print(f"\n開始批量提交:")
    print(f"  總數: {total} 筆")
    print(f"  速率: {rate_per_second} 筆/秒")
    print(f"  批次: {batches} 批 + {remaining} 筆")
    print(f"  預計時間: {batches + (1 if remaining > 0 else 0)} 秒\n")
    
    start_time = datetime.now()
    
    # 執行批次提交
    for batch_num in range(batches):
        batch_start = time.time()
        threads = []
        
        print(f"批次 {batch_num + 1}/{batches} (第 {batch_num * rate_per_second + 1}-{(batch_num + 1) * rate_per_second} 筆):")
        
        # 在這一秒內啟動 rate_per_second 個執行緒
        for i in range(rate_per_second):
            thread = threading.Thread(target=submit_one, args=(batch_num + 1, i + 1))
            threads.append(thread)
            thread.start()
        
        # 等待所有執行緒完成
        for thread in threads:
            thread.join()
        
        # 確保這一批次至少花費 1 秒
        elapsed = time.time() - batch_start
        if elapsed < 1.0 and batch_num < batches - 1:
            time.sleep(1.0 - elapsed)
    
    # 處理剩餘的提交
    if remaining > 0:
        print(f"\n最後一批 (第 {batches * rate_per_second + 1}-{total} 筆):")
        threads = []
        for i in range(remaining):
            thread = threading.Thread(target=submit_one, args=(batches + 1, i + 1))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 顯示結果
    print_section("批量測試結果")
    print(f"""
總提交數: {total} 筆
成功: {results['success']} 筆 ({results['success']/total*100:.1f}%)
失敗: {results['failed']} 筆 ({results['failed']/total*100:.1f}%)
總耗時: {duration:.2f} 秒
平均速率: {total/duration:.1f} 筆/秒

前 10 個 Submission IDs:
{chr(10).join(f"  - {sid}" for sid in results['submission_ids'][:10])}

{f"錯誤摘要 (前 5 個):" if results['errors'] else ""}
{chr(10).join(f"  - {err}" for err in results['errors'][:5])}
    """)
    
    return results

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
    print_section("選擇測試模式")
    print("1. 單筆測試 (詳細流程)")
    print("2. 批量測試 (200 筆，20 筆/秒)")
    mode = input("\n請選擇測試模式 (1/2，預設 1): ").strip() or "1"
    
    if mode == "2":
        # 批量測試模式
        problem_id = input("請輸入 Problem ID（預設 1）: ").strip() or "1"
        total = input("總提交數（預設 200）: ").strip() or "200"
        rate = input("每秒提交數（預設 20）: ").strip() or "20"
        
        confirm = input(f"\n將提交 {total} 筆到 Problem {problem_id}，速率 {rate} 筆/秒。確認？(y/N): ").strip().lower()
        if confirm == 'y':
            test_bulk_submissions(token, int(problem_id), int(total), int(rate))
        else:
            print("已取消批量測試")
    else:
        # 單筆測試模式
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
  - 如果沒有 Problem ID，會創建提交失敗
  - 重新判題需要老師/TA 權限
  - Sandbox API 可能有速率限制
    """)

if __name__ == "__main__":
    main()

    print_section("測試總結")