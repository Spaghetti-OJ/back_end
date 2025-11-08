# auths/services.py

import secrets
import hashlib

# 定義 Token 的固定前綴和長度
TOKEN_PREFIX = "ctp"  # Copycat Token Prefix
TOKEN_LENGTH_BYTES = 32  # 產生 32 bytes 的隨機資料，轉換後約為 43 個 URL 安全字元

def generate_api_token():
    """
    生成一個新的、安全的 API Token 和其對應的雜湊值。

    回傳:
        tuple: (full_token, token_hash)
            - full_token (str): 完整且包含前綴的 Token，只會顯示給使用者一次。
                                (例如: "ctp_aBcDeFgHiJkLmNoPqRsT...")
            - token_hash (str): Token 的 SHA256 雜湊值，用於儲存在資料庫中。
    """
    # 1. 生成 URL 安全的隨機字串
    random_part = secrets.token_urlsafe(TOKEN_LENGTH_BYTES)
    
    # 2. 組合完整的 Token
    full_token = f"{TOKEN_PREFIX}_{random_part}"
    
    # 3. 對完整的 Token 進行 SHA256 雜湊運算
    #    - .encode('utf-8') 是必要的，因為雜湊函數只接受 bytes
    #    - .hexdigest() 將雜湊結果轉換為十六進位字串
    token_hash = hashlib.sha256(full_token.encode('utf-8')).hexdigest()
    
    return full_token, token_hash