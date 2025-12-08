"""
Sandbox API Client

封裝與 Sandbox 判題系統的 API 互動邏輯
"""

import requests
import logging
from io import BytesIO
from django.conf import settings

logger = logging.getLogger(__name__)

# Sandbox API 設定
SANDBOX_API_URL = getattr(settings, 'SANDBOX_API_URL', 'http://34.81.90.111:8000')
SANDBOX_TIMEOUT = getattr(settings, 'SANDBOX_TIMEOUT', 30)  # 30 秒超時
SANDBOX_API_KEY = getattr(settings, 'SANDBOX_API_KEY', '')  # API Key


def convert_language_code(language_type):
    """
    將 Django 的語言代碼轉換成 Sandbox 的語言字串
    
    Django: 0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript
    Sandbox: 'c', 'cpp', 'python', 'java', 'javascript'
    """
    language_map = {
        0: 'c',
        1: 'cpp',
        2: 'python',
        3: 'java',
        4: 'javascript',
    }
    return language_map.get(language_type, 'python')  # 預設 python


def get_file_extension(language):
    """根據語言取得檔案副檔名"""
    extension_map = {
        'c': 'c',
        'cpp': 'cpp',
        'python': 'py',
        'java': 'java',
        'javascript': 'js',
    }
    return extension_map.get(language, 'txt')


def submit_to_sandbox(submission):
    """
    將 submission 提交到 Sandbox 進行判題
    
    Args:
        submission: Submission model instance
        
    Returns:
        dict: Sandbox API 的回應
        
    Raises:
        requests.RequestException: API 請求失敗
    """
    from problems.models import Problems, Problem_subtasks
    
    try:
        # 1. 取得 Problem 資訊
        problem = Problems.objects.select_related('course_id').get(id=submission.problem_id)
        
        # 2. 取得時間和記憶體限制（從第一個 subtask，如果沒有就用預設值）
        subtask = problem.subtasks.first()
        if subtask and subtask.time_limit_ms:
            time_limit = subtask.time_limit_ms / 1000.0  # 轉換成秒
        else:
            time_limit = 1.0  # 預設 1 秒
            
        if subtask and subtask.memory_limit_mb:
            memory_limit = subtask.memory_limit_mb * 1024  # 轉換成 KB
        else:
            memory_limit = 262144  # 預設 256 MB = 256 * 1024 KB
        
        # 3. 轉換語言代碼
        language = convert_language_code(submission.language_type)
        
        # 4. 組裝 payload（multipart/form-data）
        data = {
            'submission_id': str(submission.id),
            'problem_id': str(submission.problem_id),
            'problem_hash': f'TODO_HASH_{submission.problem_id}',  # TODO: 實現題目包管理後取得真實 hash
            'mode': 'normal',  # 目前只支援 single file
            'language': language,
            'file_hash': submission.code_hash,
            'time_limit': time_limit,
            'memory_limit': memory_limit,
            'use_checker': False,  # TODO: 從 problem 設定取得
            'checker_name': 'diff',
            'use_static_analysis': False,  # TODO: 從 assignment 設定取得
            'priority': 0,  # 一般優先級
        }
        
        # 5. 準備檔案
        filename = f'solution.{get_file_extension(language)}'
        file_content = submission.source_code.encode('utf-8')
        files = {
            'file': (filename, BytesIO(file_content), 'text/plain')
        }
        
        # 6. 發送請求
        url = f'{SANDBOX_API_URL}/api/v1/submissions'
        logger.info(f'Submitting to Sandbox: submission_id={submission.id}, problem_id={submission.problem_id}')
        
        # 準備 headers（包含認證）
        headers = {}
        if SANDBOX_API_KEY:
            headers['X-API-KEY'] = SANDBOX_API_KEY
        
        response = requests.post(
            url,
            data=data,
            files=files,
            headers=headers,
            timeout=SANDBOX_TIMEOUT
        )
        
        # 7. 檢查回應
        response.raise_for_status()
        result = response.json()
        
        logger.info(f'Sandbox response: {result}')
        return result
        
    except Problems.DoesNotExist:
        logger.error(f'Problem not found: problem_id={submission.problem_id}')
        raise ValueError(f'Problem {submission.problem_id} not found')
        
    except requests.RequestException as e:
        logger.error(f'Sandbox API error: {str(e)}')
        raise
        
    except Exception as e:
        logger.error(f'Unexpected error submitting to sandbox: {str(e)}')
        raise
