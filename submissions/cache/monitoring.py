"""
快取監控模組

提供快取命中率和 Redis 記憶體使用監控
"""

import logging
from collections import defaultdict
from typing import Dict, List
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


class CacheHitRateMonitor:
    """快取命中率監控"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {'hits': 0, 'misses': 0})
    
    def record_hit(self, cache_type: str):
        """記錄快取命中"""
        self.stats[cache_type]['hits'] += 1
    
    def record_miss(self, cache_type: str):
        """記錄快取未命中"""
        self.stats[cache_type]['misses'] += 1
    
    def get_hit_rate(self, cache_type: str) -> float:
        """計算命中率"""
        stats = self.stats[cache_type]
        total = stats['hits'] + stats['misses']
        if total == 0:
            return 0.0
        return stats['hits'] / total
    
    def report(self) -> List[Dict]:
        """生成監控報告"""
        report = []
        for cache_type, stats in self.stats.items():
            total = stats['hits'] + stats['misses']
            if total == 0:
                continue
            
            hit_rate = self.get_hit_rate(cache_type)
            status = 'OK' if hit_rate >= 0.7 else 'WARNING' if hit_rate >= 0.5 else 'CRITICAL'
            
            report.append({
                'type': cache_type,
                'hits': stats['hits'],
                'misses': stats['misses'],
                'total': total,
                'hit_rate': hit_rate,
                'status': status
            })
            
            # 低命中率警報
            if hit_rate < 0.5 and total > 100:
                logger.warning(
                    f"[{status}] Low cache hit rate for {cache_type}: "
                    f"{hit_rate:.1%} ({stats['hits']}/{total})"
                )
        
        return report
    
    def reset(self):
        """重置統計"""
        self.stats.clear()


class RedisMemoryMonitor:
    """Redis 記憶體監控"""
    
    def __init__(self, warning_threshold: float = 0.8, critical_threshold: float = 0.9):
        """
        Args:
            warning_threshold: 警告閾值（80%）
            critical_threshold: 嚴重閾值（90%）
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        try:
            self.redis = get_redis_connection("default")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    def get_memory_info(self) -> Dict:
        """獲取 Redis 記憶體使用情況"""
        if self.redis is None:
            return None
        
        try:
            info = self.redis.info('memory')
            used_memory = info['used_memory']
            max_memory = info.get('maxmemory', 0)
            
            if max_memory == 0:
                logger.warning("Redis maxmemory not set!")
                return {
                    'used_memory_mb': used_memory / (1024 * 1024),
                    'max_memory_mb': 0,
                    'usage_ratio': 0,
                    'status': 'UNKNOWN'
                }
            
            usage_ratio = used_memory / max_memory
            
            return {
                'used_memory_mb': used_memory / (1024 * 1024),
                'max_memory_mb': max_memory / (1024 * 1024),
                'usage_ratio': usage_ratio,
                'status': self._get_status(usage_ratio)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis memory info: {e}")
            return None
    
    def _get_status(self, usage_ratio: float) -> str:
        """判斷記憶體使用狀態"""
        if usage_ratio >= self.critical_threshold:
            return 'CRITICAL'
        elif usage_ratio >= self.warning_threshold:
            return 'WARNING'
        else:
            return 'OK'
    
    def check_and_alert(self) -> Dict:
        """檢查並發送警報"""
        info = self.get_memory_info()
        if not info:
            return None
        
        status = info['status']
        usage = info['usage_ratio']
        
        if status == 'CRITICAL':
            logger.critical(
                f"[CRITICAL] Redis memory CRITICAL: {usage:.1%} used "
                f"({info['used_memory_mb']:.1f}MB / {info['max_memory_mb']:.1f}MB)"
            )
        elif status == 'WARNING':
            logger.warning(
                f"[WARNING] Redis memory WARNING: {usage:.1%} used "
                f"({info['used_memory_mb']:.1f}MB / {info['max_memory_mb']:.1f}MB)"
            )
        else:
            logger.info(f"[OK] Redis memory OK: {usage:.1%} used")
        
        return info


# 全域實例
hit_rate_monitor = CacheHitRateMonitor()
memory_monitor = RedisMemoryMonitor()
