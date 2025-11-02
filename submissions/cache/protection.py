"""
快取穿透保護模組

使用布隆過濾器防止查詢不存在的資料造成快取穿透
"""

import logging
from typing import Optional, Callable, Any
from pybloom_live import BloomFilter
from django.core.cache import cache
from django.http import Http404

logger = logging.getLogger(__name__)


class CachePenetrationProtection:
    """
    快取穿透保護
    
    使用布隆過濾器預先過濾不存在的 key，防止惡意查詢穿透快取直達資料庫
    """
    
    def __init__(self, capacity: int = 1000000, error_rate: float = 0.001):
        """
        初始化布隆過濾器
        
        Args:
            capacity: 預期容量（預設 100 萬）
            error_rate: 誤判率（預設 0.1%）
        """
        self.bloom_filter = BloomFilter(capacity=capacity, error_rate=error_rate)
        self.initialized = False
        logger.info(
            f"Bloom filter initialized: capacity={capacity}, error_rate={error_rate}"
        )
    
    def initialize_from_db(self, model_class, id_field: str = 'id'):
        """
        從資料庫載入所有 ID 到布隆過濾器
        
        Args:
            model_class: Django Model 類別
            id_field: ID 欄位名稱（預設 'id'）
        """
        try:
            ids = model_class.objects.values_list(id_field, flat=True)
            count = 0
            for obj_id in ids:
                self.bloom_filter.add(str(obj_id))
                count += 1
            
            self.initialized = True
            logger.info(
                f"Bloom filter loaded {count} IDs from {model_class.__name__}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize bloom filter: {e}")
            self.initialized = False
    
    def add(self, key: str):
        """
        將 key 加入布隆過濾器
        
        Args:
            key: 要加入的鍵
        """
        self.bloom_filter.add(str(key))
    
    def might_exist(self, key: str) -> bool:
        """
        檢查 key 是否可能存在
        
        Args:
            key: 要檢查的鍵
        
        Returns:
            True: 可能存在（需要進一步查詢）
            False: 確定不存在
        """
        return str(key) in self.bloom_filter
    
    def get_safe(
        self, 
        key: str, 
        cache_key: str,
        fetch_function: Callable[[], Any],
        cache_timeout: int = 300,
        raise_404: bool = True
    ) -> Optional[Any]:
        """
        安全獲取資料（帶布隆過濾器保護）
        
        Args:
            key: 布隆過濾器檢查的鍵（通常是 ID）
            cache_key: Redis 快取鍵
            fetch_function: 查詢資料庫的函數
            cache_timeout: 快取超時時間（秒）
            raise_404: 不存在時是否拋出 404
        
        Returns:
            查詢結果或 None
        
        Raises:
            Http404: 當 raise_404=True 且資料不存在時
        """
        # 1. 檢查布隆過濾器
        if not self.might_exist(key):
            logger.debug(f"Bloom filter: {key} definitely not exists")
            if raise_404:
                raise Http404(f"Object {key} not found")
            return None
        
        # 2. 檢查快取
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # 處理空值快取
            if cached_data == '__NULL__':
                if raise_404:
                    raise Http404(f"Object {key} not found")
                return None
            return cached_data
        
        # 3. 查詢資料庫
        try:
            result = fetch_function()
            
            if result is None:
                # 快取空值，防止重複查詢（較短 TTL）
                cache.set(cache_key, '__NULL__', 60)
                logger.warning(f"Bloom filter false positive for {key}")
                if raise_404:
                    raise Http404(f"Object {key} not found")
                return None
            
            # 4. 快取真實資料
            cache.set(cache_key, result, cache_timeout)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching data for {key}: {e}")
            if raise_404:
                raise
            return None


# 全域實例
submission_bloom_filter = CachePenetrationProtection()
