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


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def submit_selftest_to_sandbox_task(self, test_id, user_id, problem_id, language_type, source_code, stdin_data):
    """
    異步提交自定義測試到 Sandbox
    
    Args:
        test_id: 測試 ID (selftest-uuid)
        user_id: 使用者 ID
        problem_id: 題目 ID
        language_type: 語言類型
        source_code: 程式碼
        stdin_data: 標準輸入
    
    Returns:
        dict: Sandbox 的回應結果
    """
    import redis
    import json
    from django.utils import timezone
    from .sandbox_client import submit_selftest_to_sandbox
    
    # 初始化 Redis
    try:
        redis_client = redis.Redis(
            host='127.0.0.1',
            port=6379,
            db=2,
            decode_responses=True
        )
    except Exception as e:
        logger.error(f'Redis connection failed in task: {str(e)}')
        return {'status': 'error', 'reason': 'redis_unavailable'}
    
    cache_key = f"custom_test:{user_id}:{test_id}"
    
    try:
        # 1. 提交到 Sandbox
        logger.info(f'Submitting selftest to Sandbox: {test_id}')
        result = submit_selftest_to_sandbox(
            test_id=test_id,
            problem_id=problem_id,
            language_type=language_type,
            source_code=source_code,
            stdin_data=stdin_data
        )
        
        # 2. 更新 Redis（狀態改為 queued 或 Sandbox 返回的狀態）
        cached = redis_client.get(cache_key)
        if cached:
            test_info = json.loads(cached)
            test_info['submission_id'] = result['submission_id']
            test_info['status'] = result['status']
            test_info['queue_position'] = result.get('queue_position')
            test_info['submitted_at'] = str(timezone.now())
            redis_client.setex(cache_key, 1800, json.dumps(test_info))
        
        logger.info(f'Selftest submitted successfully: {test_id}')
        return result
        
    except Exception as exc:
        logger.error(f'Error submitting selftest: {str(exc)}')
        
        # 更新 Redis 狀態為 failed
        try:
            cached = redis_client.get(cache_key)
            if cached:
                test_info = json.loads(cached)
                test_info['status'] = 'failed'
                test_info['error'] = str(exc)
                test_info['failed_at'] = str(timezone.now())
                redis_client.setex(cache_key, 1800, json.dumps(test_info))
        except Exception as redis_error:
            logger.error(f'Failed to update Redis: {str(redis_error)}')
        
        # 如果是網路錯誤，重試
        if 'RequestException' in str(type(exc).__name__):
            try:
                # 重試（較短的 backoff）
                raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
            except self.MaxRetriesExceededError:
                logger.error(f'Max retries exceeded for selftest {test_id}')
                return {'status': 'error', 'reason': 'max_retries_exceeded'}
        
        return {'status': 'error', 'reason': str(exc)}
