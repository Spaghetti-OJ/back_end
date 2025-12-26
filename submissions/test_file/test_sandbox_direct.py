#!/usr/bin/env python
"""
直接測試 Sandbox API
"""

import requests
from io import BytesIO
import hashlib

SANDBOX_URL = "http://34.81.90.111:8000"

print("\n" + "=" * 60)
print("  測試 Sandbox API /api/v1/submissions")
print("=" * 60)

# 準備測試資料 - 使用 Sandbox 已有的 hello_world 題目
data = {
    'submission_id': 'test-direct-api-hello-world',
    'problem_id': 'hello_world',
    'problem_hash': 'hello_world_hash',
    'mode': 'normal',
    'language': 'python',
    'file_hash': 'abc123',
    'time_limit': 1.0,
    'memory_limit': 262144,
    'use_checker': False,
    'checker_name': 'diff',
    'use_static_analysis': False,
    'priority': 0,
}

# 準備程式碼檔案 - hello world 程式
code = """print("Hello, World!")
"""

# 計算正確的 file_hash
import hashlib
file_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()
print(f"Calculated file_hash: {file_hash}")

# 更新 data 中的 file_hash
data['file_hash'] = file_hash

files = {
    'file': ('solution.py', BytesIO(code.encode('utf-8')), 'text/plain')
}

# 準備 headers
headers = {
    'X-API-KEY': 'happylittle7'
}

print("\n發送請求...")
print(f"URL: {SANDBOX_URL}/api/v1/submissions")
print(f"Data: {data}")

try:
    response = requests.post(
        f"{SANDBOX_URL}/api/v1/submissions",
        data=data,
        files=files,
        headers=headers,
        timeout=10
    )
    
    print(f"\n狀態碼: {response.status_code}")
    print(f"響應 Headers: {dict(response.headers)}")
    
    try:
        print(f"響應內容: {response.json()}")
    except:
        print(f"響應內容 (text): {response.text}")
    
    if response.status_code in [200, 201, 202]:
        print("\n✅ [成功] 提交成功！")
        if response.status_code == 202:
            print("   狀態: 已接受並排入佇列 (Accepted - Queued)")
    else:
        print(f"\n❌ [失敗] 提交失敗: {response.status_code}")
        
except Exception as e:
    print(f"\n[錯誤] 請求失敗: {e}")

print("\n" + "=" * 60)
