"""
分散式鎖模組

使用 Redis 實作分散式鎖，防止快取擊穿
"""

import logging
import uuid
import time
from typing import Optional
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


class RedisDistributedLock:
    """
    Redis 分散式鎖
    
    用於防止快取擊穿，確保只有一個請求去重建快取
    """
    
    def __init__(self):
        """初始化 Redis 連接"""
        try:
            self.redis = get_redis_connection("default")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    def acquire(self, key: str, expire: int = 10, timeout: int = 5) -> Optional[str]:
        """
        獲取分散式鎖（帶超時機制）
        
        Args:
            key: 鎖的鍵
            expire: 鎖的過期時間（秒），防止死鎖
            timeout: 獲取鎖的超時時間（秒），防止無限等待
        
        Returns:
            identifier: 鎖的唯一識別符，用於釋放鎖
            None: 獲取鎖失敗
        """
        if self.redis is None:
            logger.warning("Redis not available, lock acquire failed")
            return None
        
        identifier = str(uuid.uuid4())
        lock_key = f"lock:{key}"
        end_time = time.time() + timeout
        
        try:
            while time.time() < end_time:
                # 嘗試獲取鎖（NX: 不存在才設定，EX: 過期時間）
                if self.redis.set(lock_key, identifier, nx=True, ex=expire):
                    logger.debug(f"Lock acquired: {lock_key}")
                    return identifier
                
                # 短暫休息後重試
                time.sleep(0.01)  # 10ms
            
            # 超時未獲取到鎖
            logger.warning(f"Lock acquire timeout for {lock_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error acquiring lock for {lock_key}: {e}")
            return None
    
    def release(self, key: str, identifier: str) -> bool:
        """
        釋放分散式鎖（Lua 腳本確保原子性）
        
        Args:
            key: 鎖的鍵
            identifier: 獲取鎖時返回的識別符
        
        Returns:
            True: 釋放成功
            False: 釋放失敗
        """
        if self.redis is None:
            return False
        
        lock_key = f"lock:{key}"
        
        # Lua 腳本確保只釋放自己持有的鎖
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = self.redis.eval(lua_script, 1, lock_key, identifier)
            if result:
                logger.debug(f"Lock released: {lock_key}")
                return True
            else:
                logger.warning(f"Lock release failed: {lock_key} (not owner)")
                return False
                
        except Exception as e:
            logger.error(f"Error releasing lock for {lock_key}: {e}")
            return False
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        pass


# 全域實例
distributed_lock = RedisDistributedLock()
