"""
快取降級機制模組

當 Redis 故障或超時時，自動降級到資料庫查詢
"""

import logging
from typing import Optional, Callable, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheWithFallback:
    """
    帶降級機制的快取操作
    
    Redis 故障或超時時自動降級到資料庫，保證服務可用
    """
    
    def __init__(self, timeout: float = 0.5):
        """
        Args:
            timeout: Redis 操作超時時間（秒），預設 0.5 秒
        """
        self.timeout = timeout
    
    def get_safe(
        self, 
        key: str, 
        fetch_function: Optional[Callable[[], Any]] = None,
        cache_timeout: int = 300
    ) -> Optional[Any]:
        """
        安全獲取快取，Redis 故障時降級到資料庫
        
        Args:
            key: 快取鍵
            fetch_function: Redis 失敗時的降級函數（查詢資料庫）
            cache_timeout: 快取超時時間（秒）
        
        Returns:
            快取資料或資料庫查詢結果
        """
        try:
            # 嘗試從 Redis 獲取（帶超時）
            result = cache.get(key, default=None)
            
            if result is not None:
                return result
            
            # 快取 miss，但 Redis 正常
            if fetch_function:
                result = fetch_function()
                # 嘗試寫入快取
                try:
                    cache.set(key, result, cache_timeout)
                except Exception as e:
                    logger.warning(f"Cache set failed for {key}: {e}")
                return result
            
            return None
            
        except Exception as e:
            # Redis 故障，降級到資料庫
            logger.error(f"Redis get failed for {key}: {e}, falling back to database")
            
            if fetch_function:
                try:
                    return fetch_function()
                except Exception as fetch_error:
                    logger.error(f"Database fallback also failed: {fetch_error}")
                    raise
            
            return None
    
    def set_safe(self, key: str, value: Any, timeout: int = 300) -> bool:
        """
        安全寫入快取，失敗不阻塞主流程
        
        Args:
            key: 快取鍵
            value: 快取值
            timeout: TTL（秒）
        
        Returns:
            True/False 表示是否成功
        """
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            # Redis 故障，記錄日誌但不拋出異常
            logger.error(f"Redis set failed for {key}: {e}")
            return False
    
    def delete_safe(self, key: str) -> bool:
        """
        安全刪除快取，失敗不阻塞主流程
        
        Args:
            key: 快取鍵
        
        Returns:
            True/False 表示是否成功
        """
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed for {key}: {e}")
            return False
    
    def delete_pattern_safe(self, pattern: str) -> bool:
        """
        安全刪除符合模式的所有快取
        
        Args:
            pattern: 快取鍵模式（例如 "SUBMISSION_LIST:123:*"）
        
        Returns:
            True/False 表示是否成功
        """
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection("default")
            keys = conn.keys(pattern)
            if keys:
                conn.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis pattern delete failed for {pattern}: {e}")
            return False


# 全域實例
cache_fallback = CacheWithFallback(timeout=0.5)
