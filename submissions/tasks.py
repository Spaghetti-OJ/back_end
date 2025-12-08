"""
Submissions 異步任務

使用 Celery 處理耗時的判題相關任務
"""

import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def submit_to_sandbox_task(self, submission_id):
    """
    異步提交到 Sandbox 進行判題
    
    Args:
        submission_id: Submission 的 UUID
        
    Returns:
        dict: Sandbox 的回應結果
    """
    from .models import Submission
    from .sandbox_client import submit_to_sandbox
    
    try:
        # 取得 submission（加鎖避免並發問題）
        with transaction.atomic():
            submission = Submission.objects.select_for_update().get(id=submission_id)
            
            # 檢查狀態（避免重複提交）
            if submission.status not in ['-2', '-1']:  # 非 Pending 狀態
                logger.warning(f'Submission {submission_id} already judged, skipping')
                return {'status': 'skipped', 'reason': 'already_judged'}
        
        # 提交到 Sandbox
        logger.info(f'Submitting to Sandbox: {submission_id}')
        result = submit_to_sandbox(submission)
        
        logger.info(f'Submitted successfully: {submission_id}')
        return result
        
    except Submission.DoesNotExist:
        logger.error(f'Submission not found: {submission_id}')
        return {'status': 'error', 'reason': 'submission_not_found'}
        
    except Exception as exc:
        # 記錄錯誤並重試
        logger.error(f'Error submitting to sandbox: {str(exc)}')
        
        # 如果是網路錯誤，重試
        if 'RequestException' in str(type(exc).__name__):
            try:
                # 重試（exponential backoff）
                raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
            except self.MaxRetriesExceededError:
                # 重試次數用完，標記為 Judge Error
                logger.error(f'Max retries exceeded for {submission_id}')
                with transaction.atomic():
                    submission = Submission.objects.select_for_update().get(id=submission_id)
                    submission.status = '6'  # Judge Error
                    submission.save(update_fields=['status'])
                return {'status': 'error', 'reason': 'max_retries_exceeded'}
        
        # 其他錯誤直接標記為 Judge Error
        with transaction.atomic():
            submission = Submission.objects.select_for_update().get(id=submission_id)
            submission.status = '6'  # Judge Error
            submission.save(update_fields=['status'])
        
        return {'status': 'error', 'reason': str(exc)}
