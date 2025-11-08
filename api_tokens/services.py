# api_tokens/services.py

import secrets
import hashlib

# 這是 Django 建議用來生成安全雜湊的方式
from django.utils.crypto import constant_time_compare, pbkdf2

# 定義 Token 的前綴，例如 'gkt_' (Gemini Key Token)
# 你可以改成你們專案的縮寫
TOKEN_PREFIX = "ojt_" # Online Judge Token
TOKEN_LENGTH = 32 # Token 隨機部分的長度

def generate_api_token(prefix=TOKEN_PREFIX, length=TOKEN_LENGTH):
    """
    生成一個安全的 API Token 和它的雜湊值。

    返回 (full_token, token_hash)
    - full_token: "ojt_A..." (這是給用戶看的，只會顯示這一次)
    - token_hash: (這是儲存在資料庫的)
    """
    
    # 1. 生成一個安全的、URL 安全的隨機字串
    # secrets.token_urlsafe(n) 會生成約 1.3 * n 個字元
    random_part = secrets.token_urlsafe(length)
    
    # 2. 組合出完整的 Token
    full_token = f"{prefix}_{random_part}"
    
    # 3. 對 Token 進行雜湊 (Hash)
    # 我們使用 SHA-256 來儲存
    # 注意：我們儲存的是雜湊值，不是原始 Token
    # 這樣即使資料庫被盜，攻擊者也無法還原出原始 Token
    token_hash = hashlib.sha256(full_token.encode('utf-8')).hexdigest()
    
    # 4. 返回完整的 Token 和它的雜湊值
    return full_token, token_hash

def check_api_token(token_hash_to_check, full_token):
    """
    安全地比對用戶提供的 full_token 是否與資料庫中的 token_hash_to_check 相符。
    
    (你之後在 "Token 認證" 時會需要這個函式)
    """
    
    # 重新計算用戶提供的 full_token 的雜湊值
    re_hashed_token = hashlib.sha256(full_token.encode('utf-8')).hexdigest()
    
    # 使用 "constant_time_compare" (恆定時間比較) 來防止時序攻擊
    return constant_time_compare(token_hash_to_check, re_hashed_token)