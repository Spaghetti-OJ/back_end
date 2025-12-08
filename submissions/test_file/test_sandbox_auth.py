#!/usr/bin/env python
"""
測試 Sandbox API 的認證需求
"""

import requests

SANDBOX_API_URL = "http://34.81.90.111:8000"

print("=" * 70)
print("  測試 Sandbox API 認證需求")
print("=" * 70)

# 測試 1: 不帶認證
print("\n測試 1: POST /api/v1/submissions (不帶認證)")
try:
    response = requests.post(
        f"{SANDBOX_API_URL}/api/v1/submissions",
        data={'test': 'data'},
        timeout=5
    )
    print(f"狀態碼: {response.status_code}")
    print(f"響應: {response.text[:200]}")
except Exception as e:
    print(f"錯誤: {e}")

# 測試 2: 帶 Bearer Token
print("\n測試 2: POST /api/v1/submissions (帶測試 Token)")
headers = {"Authorization": "Bearer test_token_123"}
try:
    response = requests.post(
        f"{SANDBOX_API_URL}/api/v1/submissions",
        data={'test': 'data'},
        headers=headers,
        timeout=5
    )
    print(f"狀態碼: {response.status_code}")
    print(f"響應: {response.text[:200]}")
except Exception as e:
    print(f"錯誤: {e}")

# 測試 3: 帶 API Key
print("\n測試 3: POST /api/v1/submissions (帶 API Key header)")
headers = {"X-API-Key": "test_key_123"}
try:
    response = requests.post(
        f"{SANDBOX_API_URL}/api/v1/submissions",
        data={'test': 'data'},
        headers=headers,
        timeout=5
    )
    print(f"狀態碼: {response.status_code}")
    print(f"響應: {response.text[:200]}")
except Exception as e:
    print(f"錯誤: {e}")

# 測試 4: 查看 API 文檔
print("\n測試 4: 查看 OpenAPI 規範")
try:
    response = requests.get(f"{SANDBOX_API_URL}/openapi.json", timeout=5)
    if response.status_code == 200:
        spec = response.json()
        
        # 檢查安全性配置
        if 'components' in spec and 'securitySchemes' in spec['components']:
            print("找到安全性配置:")
            for name, scheme in spec['components']['securitySchemes'].items():
                print(f"  - {name}: {scheme}")
        
        # 檢查端點的安全性要求
        if 'paths' in spec and '/api/v1/submissions' in spec['paths']:
            endpoint = spec['paths']['/api/v1/submissions']
            if 'post' in endpoint:
                post_method = endpoint['post']
                if 'security' in post_method:
                    print(f"\nPOST /api/v1/submissions 的安全性要求:")
                    print(f"  {post_method['security']}")
    else:
        print(f"無法獲取 OpenAPI 規範: {response.status_code}")
except Exception as e:
    print(f"錯誤: {e}")

print("\n" + "=" * 70)
print("建議: 請聯繫 Sandbox API 管理員獲取正確的認證方式")
print("=" * 70)
