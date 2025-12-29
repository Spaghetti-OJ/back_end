"""
Problems app signals - 處理題目相關的 signal 事件
"""
import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='problems.Problems')
def track_quota_change(sender, instance, **kwargs):
    """
    在保存前追蹤 total_quota 是否變更
    將舊值存入 instance._old_total_quota
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_total_quota = old_instance.total_quota
        except sender.DoesNotExist:
            instance._old_total_quota = None
    else:
        instance._old_total_quota = None


@receiver(post_save, sender='problems.Problems')
def reset_user_quotas_on_change(sender, instance, created, **kwargs):
    """
    當題目的 total_quota 被修改時，重置所有該題目的 UserProblemQuota 記錄
    
    邏輯：
    - 如果是新建題目，不需要處理
    - 如果 total_quota 沒有變更，不需要處理
    - 如果 total_quota 變更了，重置所有相關的 UserProblemQuota
    """
    if created:
        return
    
    old_quota = getattr(instance, '_old_total_quota', None)
    new_quota = instance.total_quota
    
    # 如果 quota 沒有變更，不需要處理
    if old_quota == new_quota:
        return
    
    # 延遲導入避免循環依賴
    from submissions.models import UserProblemQuota
    
    # 重置所有該題目的配額記錄
    updated_count = UserProblemQuota.objects.filter(
        problem_id=instance.id,
        assignment_id__isnull=True  # 只重置全域配額，不影響作業配額
    ).update(
        total_quota=new_quota,
        remaining_attempts=new_quota
    )
    
    logger.info(
        f"Problem {instance.id} total_quota changed from {old_quota} to {new_quota}. "
        f"Reset {updated_count} user quota records."
    )
