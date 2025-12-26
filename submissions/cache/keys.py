"""
快取鍵管理模組

統一管理所有快取鍵的生成，確保命名一致性
"""

import hashlib
from typing import Any, Optional


class CacheKeys:
    """快取鍵生成器"""
    
    # 快取鍵前綴
    PREFIX_SUBMISSION_LIST = "SUBMISSION_LIST"
    PREFIX_USER_STATS = "USER_STATS"
    PREFIX_SUBMISSION_DETAIL = "SUBMISSION_DETAIL"
    PREFIX_HIGH_SCORE = "HIGH_SCORE"
    PREFIX_PERMISSION = "SUBMISSION_PERMISSION"
    PREFIX_TOKEN = "TOKEN"
    PREFIX_RANKING = "RANKING"
    
    @staticmethod
    def submission_list(user_id: str, **filters) -> str:
        """
        提交列表快取鍵
        
        Args:
            user_id: 用戶 ID
            **filters: 其他篩選條件 (problem_id, status, language, offset, limit 等)
        
        Returns:
            快取鍵字符串
        """
        # 將 filters 排序後生成唯一 hash
        filter_str = ':'.join(f"{k}={v}" for k, v in sorted(filters.items()) if v is not None)
        if filter_str:
            return f"{CacheKeys.PREFIX_SUBMISSION_LIST}:{user_id}:{filter_str}"
        return f"{CacheKeys.PREFIX_SUBMISSION_LIST}:{user_id}"
    
    @staticmethod
    def submission_list_pattern(user_id: str) -> str:
        """
        提交列表快取鍵模式（用於批量刪除）
        
        Args:
            user_id: 用戶 ID
        
        Returns:
            快取鍵模式
        """
        return f"{CacheKeys.PREFIX_SUBMISSION_LIST}:{user_id}:*"
    
    @staticmethod
    def user_stats(user_id: str) -> str:
        """
        用戶統計快取鍵
        
        Args:
            user_id: 用戶 ID
        
        Returns:
            快取鍵字符串
        """
        return f"{CacheKeys.PREFIX_USER_STATS}:{user_id}"
    
    @staticmethod
    def submission_detail(submission_id: str) -> str:
        """
        提交詳情快取鍵
        
        Args:
            submission_id: 提交 ID
        
        Returns:
            快取鍵字符串
        """
        return f"{CacheKeys.PREFIX_SUBMISSION_DETAIL}:{submission_id}"
    
    @staticmethod
    def high_score(problem_id: int, user_id: str) -> str:
        """
        用戶題目高分快取鍵
        
        Args:
            problem_id: 題目 ID
            user_id: 用戶 ID
        
        Returns:
            快取鍵字符串
        """
        return f"{CacheKeys.PREFIX_HIGH_SCORE}:{problem_id}:{user_id}"
    
    @staticmethod
    def permission(submission_id: str, user_id: str) -> str:
        """
        提交權限快取鍵
        
        Args:
            submission_id: 提交 ID
            user_id: 用戶 ID
        
        Returns:
            快取鍵字符串
        """
        return f"{CacheKeys.PREFIX_PERMISSION}:{submission_id}:{user_id}"
    
    @staticmethod
    def token(submission_id: str) -> str:
        """
        驗證 Token 快取鍵
        
        Args:
            submission_id: 提交 ID
        
        Returns:
            快取鍵字符串
        """
        return f"{CacheKeys.PREFIX_TOKEN}:{submission_id}"
    
    @staticmethod
    def ranking(scope: str, time_range: str = "all_time") -> str:
        """
        排行榜快取鍵
        
        Args:
            scope: 範圍 (global, course:123 等)
            time_range: 時間範圍 (all_time, this_week, this_month 等)
        
        Returns:
            快取鍵字符串
        """
        return f"{CacheKeys.PREFIX_RANKING}:{scope}:{time_range}"
    
    @staticmethod
    def ranking_pattern() -> str:
        """
        排行榜快取鍵模式（用於批量刪除）
        
        Returns:
            快取鍵模式
        """
        return f"{CacheKeys.PREFIX_RANKING}:*"
    
    @staticmethod
    def lock(key: str) -> str:
        """
        分散式鎖鍵
        
        Args:
            key: 原始快取鍵
        
        Returns:
            鎖鍵字符串
        """
        return f"lock:{key}"
