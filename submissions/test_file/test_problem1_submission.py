#!/usr/bin/env python
"""
測試 Problem 1 的提交流程
診斷為何 submission 卡在 pending

使用方式:
    cd back_end
    python submissions/test_file/test_problem1_submission.py
"""
import os
import sys
import hashlib

# 設置 Django 環境
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')

import django
django.setup()

from django.conf import settings
from problems.models import Problems, Problem_subtasks
from user.models import User
from submissions.models import Submission
import requests

# ========== 配置 ==========
PROBLEM_ID = 1
SANDBOX_API_URL = getattr(settings, 'SANDBOX_API_URL', 'http://34.81.90.111:8000')
SANDBOX_API_KEY = getattr(settings, 'SANDBOX_API_KEY', '') or os.getenv('SANDBOX_API_KEY', '')
SANDBOX_TOKEN = getattr(settings, 'SANDBOX_TOKEN', None) or os.getenv('SANDBOX_TOKEN', '')
BACKEND_BASE_URL = getattr(settings, 'BACKEND_BASE_URL', 'http://localhost:8000')

# 如果 API Key 仍未設定，可在此處手動填入（僅供測試）
# SANDBOX_API_KEY = 'your-sandbox-api-key-here'


def print_env_variables():
    """顯示讀取到的環境變數"""
    print("\n" + "=" * 60)
    print("  環境變數設定")
    print("=" * 60)
    print(f"SANDBOX_API_URL     : {SANDBOX_API_URL}")
    print(f"SANDBOX_API_KEY     : {'[已設定]' if SANDBOX_API_KEY else '[未設定]'} (長度: {len(SANDBOX_API_KEY)})")
    print(f"SANDBOX_TOKEN       : {'[已設定]' if SANDBOX_TOKEN else '[未設定]'} (長度: {len(SANDBOX_TOKEN) if SANDBOX_TOKEN else 0})")
    print(f"BACKEND_BASE_URL    : {BACKEND_BASE_URL}")
    print(f"MEDIA_ROOT          : {settings.MEDIA_ROOT}")
    
    # 顯示原始環境變數（未經 settings 處理）
    print("\n--- 原始環境變數 ---")
    print(f"os.getenv('SANDBOX_API_URL')    : {os.getenv('SANDBOX_API_URL', '[未設定]')}")
    print(f"os.getenv('SANDBOX_API_KEY')    : {'[已設定]' if os.getenv('SANDBOX_API_KEY') else '[未設定]'}")
    print(f"os.getenv('SANDBOX_TOKEN')      : {'[已設定]' if os.getenv('SANDBOX_TOKEN') else '[未設定]'}")
    print(f"os.getenv('BACKEND_BASE_URL')   : {os.getenv('BACKEND_BASE_URL', '[未設定]')}")


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_problem_exists():
    """檢查題目是否存在"""
    print_section("步驟 1: 檢查題目")
    
    try:
        problem = Problems.objects.get(id=PROBLEM_ID)
        print(f"✓ 題目存在: {problem.title}")
        print(f"  - ID: {problem.id}")
        print(f"  - 難度: {problem.difficulty}")
        print(f"  - 建立者: {problem.creator_id}")
        print(f"  - 課程: {problem.course_id}")
        
        # 檢查 subtasks
        subtasks = problem.subtasks.all()
        print(f"  - Subtasks 數量: {subtasks.count()}")
        for st in subtasks:
            print(f"    - Subtask {st.subtask_no}: time={st.time_limit_ms}ms, mem={st.memory_limit_mb}MB, weight={st.weight}")
        
        return problem
    except Problems.DoesNotExist:
        print(f"✗ 題目 {PROBLEM_ID} 不存在！")
        return None


def check_testcase_package():
    """檢查測資包是否存在"""
    print_section("步驟 2: 檢查測資包")
    
    testcase_dir = os.path.join(settings.MEDIA_ROOT, "testcases", f"p{PROBLEM_ID}")
    zip_path = os.path.join(testcase_dir, "problem.zip")
    
    print(f"測資目錄: {testcase_dir}")
    
    if not os.path.exists(testcase_dir):
        print(f"✗ 測資目錄不存在！")
        print(f"  請先上傳測資包: POST /problem/{PROBLEM_ID}/test-cases/upload-zip")
        return None, None
    
    # 列出目錄內容
    print(f"目錄內容:")
    for f in os.listdir(testcase_dir):
        fpath = os.path.join(testcase_dir, f)
        size = os.path.getsize(fpath)
        print(f"  - {f} ({size} bytes)")
    
    # 檢查 zip
    problem_hash = None
    meta = None
    
    if os.path.exists(zip_path):
        print(f"✓ problem.zip 存在")
        
        # 計算 hash
        sha256_hash = hashlib.sha256()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        problem_hash = sha256_hash.hexdigest()
        print(f"  - SHA256 Hash: {problem_hash}")
        
        # 檢查 ZIP 內部的 meta.json
        import zipfile
        import json
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # 列出 ZIP 內容
                print(f"  - ZIP 內容:")
                for name in zf.namelist():
                    info = zf.getinfo(name)
                    print(f"      {name} ({info.file_size} bytes)")
                
                # 檢查 meta.json
                if 'meta.json' in zf.namelist():
                    print(f"✓ meta.json 存在 (在 ZIP 內)")
                    with zf.open('meta.json') as mf:
                        meta = json.load(mf)
                        print(f"  - 內容: {json.dumps(meta, indent=2)}")
                else:
                    print(f"✗ meta.json 不在 ZIP 內")
        except zipfile.BadZipFile:
            print(f"✗ problem.zip 不是有效的 ZIP 檔案")
    else:
        print(f"✗ problem.zip 不存在！")
    
    return problem_hash, meta


def check_sandbox_connection():
    """檢查 Sandbox 連線"""
    print_section("步驟 3: 檢查 Sandbox 連線")
    
    print(f"Sandbox URL: {SANDBOX_API_URL}")
    print(f"API Key: {'已設定' if SANDBOX_API_KEY else '❌ 未設定'}")
    
    if not SANDBOX_API_KEY:
        print(f"⚠ 請在 .env 設定 SANDBOX_API_KEY，或在腳本中手動填入")
        return False
    
    headers = {'X-API-KEY': SANDBOX_API_KEY}
    
    try:
        # 嘗試連線 /docs 端點（通常不需要認證）
        response = requests.get(f"{SANDBOX_API_URL}/docs", timeout=5)
        if response.status_code == 200:
            print(f"✓ Sandbox API 可連線 (/docs)")
        
        # 嘗試連線需要認證的端點
        response = requests.get(f"{SANDBOX_API_URL}/api/v1/health", headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"✓ Sandbox API 認證成功")
            return True
        elif response.status_code == 401:
            print(f"✗ API Key 無效或未授權")
            return False
        else:
            print(f"⚠ Sandbox API 回應: {response.status_code}")
            # 即使 health 端點不存在，也可能正常工作
            return True
    except Exception as e:
        print(f"✗ 無法連線到 Sandbox: {e}")
        return False


def check_celery_status():
    """檢查 Celery 狀態"""
    print_section("步驟 4: 檢查 Celery")
    
    try:
        from back_end.celery import app
        
        # 檢查已註冊的任務
        registered_tasks = list(app.tasks.keys())
        sandbox_tasks = [t for t in registered_tasks if 'sandbox' in t.lower() or 'submission' in t.lower()]
        
        print(f"已註冊的相關任務:")
        for task in sandbox_tasks:
            print(f"  - {task}")
        
        # 檢查 broker 連線
        try:
            from celery import current_app
            inspector = current_app.control.inspect()
            active = inspector.active()
            if active:
                print(f"✓ Celery Worker 運行中")
                for worker, tasks in active.items():
                    print(f"  - {worker}: {len(tasks)} 個活動任務")
            else:
                print(f"✗ 沒有 Celery Worker 運行")
                print(f"  請執行: celery -A back_end worker -l info")
        except Exception as e:
            print(f"⚠ 無法檢查 Worker 狀態: {e}")
        
        return True
    except Exception as e:
        print(f"✗ Celery 檢查失敗: {e}")
        return False


def check_redis_status():
    """檢查 Redis 狀態"""
    print_section("步驟 5: 檢查 Redis")
    
    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.ping()
        print(f"✓ Redis 連線正常")
        return True
    except Exception as e:
        print(f"✗ Redis 連線失敗: {e}")
        print(f"  請執行: docker-compose -f docker-compose.redis.yml up -d")
        return False


def test_direct_sandbox_submit(problem_hash):
    """直接測試向 Sandbox 提交"""
    print_section("步驟 6: 測試直接提交到 Sandbox")
    
    if not problem_hash:
        print("✗ 沒有 problem_hash，無法測試")
        return False
    
    # A + B 程式碼
    source_code = """
a, b = map(int, input().split())
print(a + b)
"""
    
    file_content = source_code.encode('utf-8')
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    data = {
        'submission_id': 'test-problem1-direct-001',
        'problem_id': str(PROBLEM_ID),
        'problem_hash': problem_hash,
        'mode': 'normal',
        'language': 'python',
        'file_hash': file_hash,
        'time_limit': 1.0,
        'memory_limit': 262144,
        'use_checker': False,
        'checker_name': 'diff',
        'use_static_analysis': False,
        'priority': 0,
        'callback_url': f'{settings.BACKEND_BASE_URL}/submissions/callback/',
    }
    
    from io import BytesIO
    files = {
        'file': ('solution.py', BytesIO(file_content), 'text/plain')
    }
    
    headers = {}
    if SANDBOX_API_KEY:
        headers['X-API-KEY'] = SANDBOX_API_KEY
    
    print(f"提交資料:")
    print(f"  - submission_id: {data['submission_id']}")
    print(f"  - problem_id: {data['problem_id']}")
    print(f"  - problem_hash: {data['problem_hash'][:16]}...")
    print(f"  - language: {data['language']}")
    print(f"  - file_hash: {data['file_hash'][:16]}...")
    
    confirm = input("\n是否發送測試提交到 Sandbox? (y/N): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return False
    
    try:
        response = requests.post(
            f"{SANDBOX_API_URL}/api/v1/submissions",
            data=data,
            files=files,
            headers=headers,
            timeout=30
        )
        
        print(f"\n回應狀態碼: {response.status_code}")
        print(f"回應內容: {response.text}")
        
        if response.status_code in [200, 201, 202]:
            print(f"✓ 提交成功！")
            return True
        else:
            print(f"✗ 提交失敗")
            return False
            
    except Exception as e:
        print(f"✗ 請求失敗: {e}")
        return False


def create_test_submission():
    """透過 API 建立測試提交"""
    print_section("步驟 7: 透過 Django 建立提交")
    
    # 找一個測試用戶
    user = User.objects.first()
    if not user:
        print("✗ 沒有可用的用戶")
        return None
    
    print(f"使用用戶: {user.username}")
    
    # 建立提交
    source_code = """
a, b = map(int, input().split())
print(a + b)
"""
    
    code_hash = hashlib.sha256(source_code.encode()).hexdigest()
    
    submission = Submission.objects.create(
        user=user,
        problem_id=PROBLEM_ID,
        language_type=2,  # Python
        source_code=source_code,
        code_hash=code_hash,
        status='-1',  # Pending
    )
    
    print(f"✓ 提交已建立:")
    print(f"  - ID: {submission.id}")
    print(f"  - Status: {submission.status}")
    
    return submission


def trigger_sandbox_task(submission):
    """觸發 Sandbox 任務"""
    print_section("步驟 8: 觸發 Celery 任務")
    
    from submissions.tasks import submit_to_sandbox_task
    
    print(f"發送任務: submit_to_sandbox_task({submission.id})")
    
    confirm = input("是否觸發任務? (y/N): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    try:
        result = submit_to_sandbox_task.delay(str(submission.id))
        print(f"✓ 任務已發送")
        print(f"  - Task ID: {result.id}")
        print(f"  - 請查看 Celery Worker 日誌")
    except Exception as e:
        print(f"✗ 發送失敗: {e}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           Problem 1 提交測試 - 診斷 Sandbox 連線                 ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # 顯示環境變數設定
    print_env_variables()
    
    # 步驟 1: 檢查題目
    problem = check_problem_exists()
    if not problem:
        print("\n請先建立題目 1")
        return
    
    # 步驟 2: 檢查測資包
    problem_hash, meta = check_testcase_package()
    
    # 步驟 3: 檢查 Sandbox
    sandbox_ok = check_sandbox_connection()
    
    # 步驟 4: 檢查 Celery
    check_celery_status()
    
    # 步驟 5: 檢查 Redis
    check_redis_status()
    
    # 總結
    print_section("診斷總結")
    
    issues = []
    if not problem_hash:
        issues.append("缺少測資包 (problem.zip)")
    if not meta:
        issues.append("缺少 meta.json")
    if not sandbox_ok:
        issues.append("Sandbox 無法連線")
    
    if issues:
        print("發現以下問題:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        if not problem_hash:
            print(f"\n建議: 上傳測資包")
            print(f"  curl -X POST 'http://127.0.0.1:8000/problem/{PROBLEM_ID}/test-cases/upload-zip' \\")
            print(f"    -H 'Authorization: Bearer $TOKEN' \\")
            print(f"    -F 'file=@testcases.zip'")
    else:
        print("✓ 所有檢查通過！")
        
        # 詢問是否進行測試
        test_direct = input("\n是否進行直接 Sandbox 提交測試? (y/N): ").strip().lower()
        if test_direct == 'y':
            test_direct_sandbox_submit(problem_hash)
        
        test_full = input("\n是否進行完整提交流程測試? (y/N): ").strip().lower()
        if test_full == 'y':
            submission = create_test_submission()
            if submission:
                trigger_sandbox_task(submission)


if __name__ == "__main__":
    main()