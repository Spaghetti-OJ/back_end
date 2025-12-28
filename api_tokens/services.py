import secrets
import hashlib

from django.utils.crypto import constant_time_compare, pbkdf2

TOKEN_PREFIX = "noj_pat_" 
TOKEN_LENGTH = 32 

def generate_api_token(prefix=TOKEN_PREFIX, length=TOKEN_LENGTH):
    """
    生成一個安全的 API Token 和它的雜湊值。

    返回 (full_token, token_hash)
    - full_token: "noj_pat__A..." (這是給用戶看的，只會顯示這一次)
    - token_hash: (這是儲存在資料庫的)
    """
    random_part = secrets.token_urlsafe(length)
    
    full_token = f"{prefix}{random_part}"
    
    token_hash = hashlib.sha256(full_token.encode('utf-8')).hexdigest()
    
    return full_token, token_hash

def check_api_token(token_hash_to_check, full_token):
    """
    安全地比對用戶提供的 full_token 是否與資料庫中的 token_hash_to_check 相符。
    
    (你之後在 "Token 認證" 時會需要這個函式)
    """
    re_hashed_token = hashlib.sha256(full_token.encode('utf-8')).hexdigest()
    
    return constant_time_compare(token_hash_to_check, re_hashed_token)