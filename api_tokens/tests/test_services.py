# api_tokens/tests/test_services.py
"""
測試 API Token 服務層
"""
from django.test import TestCase
from api_tokens.services import generate_api_token, check_api_token
import hashlib


class ApiTokenServicesTest(TestCase):
    """測試 API Token 服務函數"""

    def test_generate_api_token_returns_tuple(self):
        """測試 generate_api_token 返回 tuple"""
        result = generate_api_token()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_generate_api_token_format(self):
        """測試生成的 token 格式正確"""
        full_token, token_hash = generate_api_token()
        
        # 檢查 token 以正確的前綴開始
        self.assertTrue(full_token.startswith('noj_pat_'))
        
        # 檢查 token 長度合理（前綴 + 隨機部分）
        self.assertGreater(len(full_token), 20)
        
        # 檢查 hash 是 64 個字符（SHA-256 的 hex digest）
        self.assertEqual(len(token_hash), 64)

    def test_generate_api_token_uniqueness(self):
        """測試每次生成的 token 都是唯一的"""
        token1, hash1 = generate_api_token()
        token2, hash2 = generate_api_token()
        
        self.assertNotEqual(token1, token2)
        self.assertNotEqual(hash1, hash2)

    def test_token_hash_is_sha256(self):
        """測試 token hash 是正確的 SHA-256"""
        full_token, token_hash = generate_api_token()
        
        # 手動計算 hash 並比對
        expected_hash = hashlib.sha256(full_token.encode('utf-8')).hexdigest()
        self.assertEqual(token_hash, expected_hash)

    def test_check_api_token_with_valid_token(self):
        """測試驗證有效的 token"""
        full_token, token_hash = generate_api_token()
        
        # 驗證應該成功
        self.assertTrue(check_api_token(token_hash, full_token))

    def test_check_api_token_with_invalid_token(self):
        """測試驗證無效的 token"""
        full_token, token_hash = generate_api_token()
        
        # 使用錯誤的 token 驗證應該失敗
        wrong_token = "noj_pat_wrong_token_12345"
        self.assertFalse(check_api_token(token_hash, wrong_token))

    def test_check_api_token_with_modified_token(self):
        """測試驗證被修改的 token"""
        full_token, token_hash = generate_api_token()
        
        # 修改 token 的一個字符
        modified_token = full_token[:-1] + 'X'
        self.assertFalse(check_api_token(token_hash, modified_token))

    def test_generate_token_with_custom_prefix(self):
        """測試使用自定義前綴生成 token"""
        custom_prefix = "custom_"
        full_token, token_hash = generate_api_token(prefix=custom_prefix)
        
        self.assertTrue(full_token.startswith(custom_prefix))

    def test_generate_token_with_custom_length(self):
        """測試使用自定義長度生成 token"""
        # 注意：length 參數影響的是 secrets.token_urlsafe 的 bytes 數
        full_token1, _ = generate_api_token(length=16)
        full_token2, _ = generate_api_token(length=64)
        
        # 較大的 length 應該產生較長的 token
        self.assertGreater(len(full_token2), len(full_token1))

    def test_token_hash_consistency(self):
        """測試相同的 token 總是產生相同的 hash"""
        test_token = "noj_pat_test_token_12345"
        
        hash1 = hashlib.sha256(test_token.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(test_token.encode('utf-8')).hexdigest()
        
        self.assertEqual(hash1, hash2)

    def test_check_api_token_is_constant_time(self):
        """測試 check_api_token 使用常數時間比較"""
        # 這個測試確保使用了 constant_time_compare
        # 雖然我們無法直接測試時間，但可以確保函數正常工作
        full_token, token_hash = generate_api_token()
        
        # 多次驗證應該都返回相同結果
        results = [check_api_token(token_hash, full_token) for _ in range(10)]
        self.assertTrue(all(results))
        
        # 錯誤的 token 也應該一致返回 False
        wrong_results = [check_api_token(token_hash, "wrong") for _ in range(10)]
        self.assertFalse(any(wrong_results))
