#!/usr/bin/env python
"""
快速創建測試用戶並獲取 Token

使用方式:
    cd /Users/keliangyun/Desktop/software_engineering/back_end
    python submissions/test_file/get_test_token.py
"""
import os
import sys
import django

# 添加專案根目錄到 Python 路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
django.setup()

from user.models import User
from rest_framework_simplejwt.tokens import RefreshToken

def create_test_user():
    """創建測試用戶"""
    username = "test_sandbox"
    email = "test_sandbox@example.com"
    password = "test123456"
    
    # 檢查用戶是否已存在
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_active': True,
        }
    )
    
    if created:
        user.set_password(password)
        user.save()
        print(f"✓ 創建新用戶: {username}")
    else:
        print(f"✓ 使用現有用戶: {username}")
    
    # 確保 email 已驗證（測試用）
    try:
        from user.models import UserProfile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'email_verified': True}
        )
        if not profile.email_verified:
            profile.email_verified = True
            profile.save()
            print(f"✓ Email 已設為驗證狀態")
        else:
            print(f"✓ Email 已是驗證狀態")
    except Exception as e:
        print(f"⚠ 無法設置 email 驗證狀態: {e}")
    
    return user, password

def get_jwt_token(user):
    """為用戶生成 JWT Token"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def main():
    print("=" * 60)
    print("  創建測試用戶並獲取 JWT Token")
    print("=" * 60)
    
    user, password = create_test_user()
    tokens = get_jwt_token(user)
    
    print("\n" + "=" * 60)
    print("  用戶資訊")
    print("=" * 60)
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Password: {password}")
    print(f"User ID: {user.id}")
    
    print("\n" + "=" * 60)
    print("  JWT Tokens")
    print("=" * 60)
    print("\nAccess Token (用於 API 請求):")
    print(tokens['access'])
    print("\nRefresh Token (用於刷新):")
    print(tokens['refresh'])
    
    print("\n" + "=" * 60)
    print("  使用方式")
    print("=" * 60)
    print("\n在 HTTP 請求的 Header 中加入:")
    print(f'Authorization: Bearer {tokens["access"]}')
    print("\n或者複製上面的 Access Token 貼到測試腳本中")
    
    return tokens['access']

if __name__ == "__main__":
    token = main()
