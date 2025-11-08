"""
快取工具模組

提供便捷的快取操作函數，簡化 views 中的快取使用
"""

import logging
from typing import Optional, Callable, Any, Dict
from django.conf import settings
from .keys import CacheKeys
from .protection import submission_bloom_filter
from .lock import distributed_lock
from .fallback import cache_fallback
from .monitoring import hit_rate_monitor

logger = logging.getLogger(__name__)


def get_submission_with_cache(
    submission_id: str,
    fetch_function: Callable[[], Any],
    only_completed: bool = True
) -> Optional[Any]:
    """
    獲取提交詳情（帶快取和布隆過濾器保護）
    
    Args:
        submission_id: 提交 ID
        fetch_function: 查詢資料庫的函數
        only_completed: 是否只快取已完成的提交
    
    Returns:
        提交資料或 None
    """
    cache_key = CacheKeys.submission_detail(submission_id)
    cache_timeout = settings.CACHE_TIMEOUTS.get('submission_detail', 120)
    
    # 使用布隆過濾器保護
    result = submission_bloom_filter.get_safe(
        key=submission_id,
        cache_key=cache_key,
        fetch_function=fetch_function,
        cache_timeout=cache_timeout,
        raise_404=False
    )
    
    # 記錄監控
    if result is not None:
        hit_rate_monitor.record_hit('submission_detail')
    else:
        hit_rate_monitor.record_miss('submission_detail')
    
    return result


def get_user_stats_with_cache(
    user_id: str,
    calculate_function: Callable[[], Dict]
) -> Optional[Dict]:
    """
    獲取用戶統計（帶快取和分散式鎖）
    
    Args:
        user_id: 用戶 ID
        calculate_function: 計算統計的函數
    
    Returns:
        用戶統計資料
    """
    cache_key = CacheKeys.user_stats(user_id)
    cache_timeout = settings.CACHE_TIMEOUTS.get('user_stats', 300)
    
    # 1. 檢查快取
    cached_data = cache_fallback.get_safe(cache_key)
    if cached_data:
        hit_rate_monitor.record_hit('user_stats')
        return cached_data
    
    hit_rate_monitor.record_miss('user_stats')
    
    # 2. 使用分散式鎖防止重複計算
    lock_id = distributed_lock.acquire(cache_key, expire=30, timeout=3)
    
    if not lock_id:
        # 獲取鎖失敗，直接計算（超時降級）
        logger.warning(f"Failed to acquire lock for {cache_key}, falling back to direct calculation")
        return calculate_function()
    
    try:
        # 3. 雙重檢查
        cached_data = cache_fallback.get_safe(cache_key)
        if cached_data:
            return cached_data
        
        # 4. 計算統計
        stats = calculate_function()
        
        # 5. 寫入快取
        cache_fallback.set_safe(cache_key, stats, cache_timeout)
        
        return stats
        
    finally:
        # 6. 釋放鎖
        distributed_lock.release(cache_key, lock_id)


def get_submission_list_with_cache(
    user_id: str,
    fetch_function: Callable[[], list],
    **filters
) -> list:
    """
    獲取提交列表（帶快取）
    
    Args:
        user_id: 用戶 ID
        fetch_function: 查詢資料庫的函數
        **filters: 篩選條件
    
    Returns:
        提交列表
    """
    cache_key = CacheKeys.submission_list(user_id, **filters)
    cache_timeout = settings.CACHE_TIMEOUTS.get('submission_list', 30)
    
    # 檢查快取
    result = cache_fallback.get_safe(cache_key, fetch_function, cache_timeout)
    
    # 記錄監控
    if result is not None and cache_fallback.get_safe(cache_key) is not None:
        hit_rate_monitor.record_hit('submission_list')
    else:
        hit_rate_monitor.record_miss('submission_list')
    
    return result or []


def get_high_score_with_cache(
    problem_id: int,
    user_id: str,
    fetch_function: Callable[[], Optional[int]]
) -> Optional[int]:
    """
    獲取用戶題目高分（帶快取）
    
    Args:
        problem_id: 題目 ID
        user_id: 用戶 ID
        fetch_function: 查詢資料庫的函數
    
    Returns:
        最高分數或 None
    """
    cache_key = CacheKeys.high_score(problem_id, user_id)
    cache_timeout = settings.CACHE_TIMEOUTS.get('high_score', 600)
    
    result = cache_fallback.get_safe(cache_key, fetch_function, cache_timeout)
    
    # 記錄監控
    if result is not None and cache_fallback.get_safe(cache_key) is not None:
        hit_rate_monitor.record_hit('high_score')
    else:
        hit_rate_monitor.record_miss('high_score')
    
    return result


def get_permission_with_cache(
    submission_id: str,
    user_id: str,
    check_function: Callable[[], Dict]
) -> Dict:
    """
    獲取提交權限（帶快取）
    
    Args:
        submission_id: 提交 ID
        user_id: 用戶 ID
        check_function: 檢查權限的函數
    
    Returns:
        權限字典 (can_view, can_edit, can_delete 等)
    """
    cache_key = CacheKeys.permission(submission_id, user_id)
    cache_timeout = settings.CACHE_TIMEOUTS.get('permission', 60)
    
    result = cache_fallback.get_safe(cache_key, check_function, cache_timeout)
    
    # 記錄監控
    if result is not None and cache_fallback.get_safe(cache_key) is not None:
        hit_rate_monitor.record_hit('permission')
    else:
        hit_rate_monitor.record_miss('permission')
    
    return result or {}


def invalidate_user_caches(user_id: str):
    """
    清除用戶相關的所有快取
    
    Args:
        user_id: 用戶 ID
    """
    # 清除提交列表
    pattern = CacheKeys.submission_list_pattern(user_id)
    cache_fallback.delete_pattern_safe(pattern)
    
    # 清除用戶統計
    cache_key = CacheKeys.user_stats(user_id)
    cache_fallback.delete_safe(cache_key)
    
    logger.debug(f"Invalidated caches for user {user_id}")
