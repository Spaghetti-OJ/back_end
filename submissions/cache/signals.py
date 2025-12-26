"""
快取失效 Signal Handlers

當資料庫發生變更時，自動清除相關快取
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from submissions.models import Submission
from submissions.cache.keys import CacheKeys
from submissions.cache.fallback import cache_fallback
from submissions.cache.protection import submission_bloom_filter

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Submission)
def on_submission_created(sender, instance, created, **kwargs):
    """
    提交建立後清除相關快取
    
    清除範圍：
    - 用戶提交列表快取
    - 用戶統計快取
    - 用戶題目高分快取
    - 排行榜快取（延遲）
    - 布隆過濾器（新增 ID）
    """
    if not created:
        # 只處理新建立的提交
        return
    
    user_id = str(instance.user.id)
    problem_id = instance.problem_id
    submission_id = str(instance.id)
    
    try:
        # 1. 清除用戶提交列表快取（模式匹配）
        pattern = CacheKeys.submission_list_pattern(user_id)
        cache_fallback.delete_pattern_safe(pattern)
        logger.debug(f"Cleared submission list cache for user {user_id}")
        
        # 2. 清除用戶統計快取
        cache_key = CacheKeys.user_stats(user_id)
        cache_fallback.delete_safe(cache_key)
        logger.debug(f"Cleared user stats cache for user {user_id}")
        
        # 3. 清除用戶題目高分快取
        cache_key = CacheKeys.high_score(problem_id, user_id)
        cache_fallback.delete_safe(cache_key)
        logger.debug(f"Cleared high score cache for user {user_id}, problem {problem_id}")
        
        # 4. 清除排行榜快取
        pattern = CacheKeys.ranking_pattern()
        cache_fallback.delete_pattern_safe(pattern)
        logger.debug("Cleared ranking cache")
        
        # 5. 將新 submission_id 加入布隆過濾器
        submission_bloom_filter.add(submission_id)
        logger.debug(f"Added submission {submission_id} to bloom filter")
        
    except Exception as e:
        logger.error(f"Error in on_submission_created signal: {e}")


@receiver(post_delete, sender=Submission)
def on_submission_deleted(sender, instance, **kwargs):
    """
    提交刪除後清除相關快取
    """
    user_id = str(instance.user.id)
    submission_id = str(instance.id)
    
    try:
        # 1. 清除提交詳情快取
        cache_key = CacheKeys.submission_detail(submission_id)
        cache_fallback.delete_safe(cache_key)
        
        # 2. 清除用戶相關快取
        pattern = CacheKeys.submission_list_pattern(user_id)
        cache_fallback.delete_pattern_safe(pattern)
        
        cache_key = CacheKeys.user_stats(user_id)
        cache_fallback.delete_safe(cache_key)
        
        logger.debug(f"Cleared caches for deleted submission {submission_id}")
        
    except Exception as e:
        logger.error(f"Error in on_submission_deleted signal: {e}")
