"""
Sandbox API Client

封裝與 Sandbox 判題系統的 API 互動邏輯
"""

import requests
import logging
from io import BytesIO
from django.conf import settings

from problems.services.storage import get_problem_testcase_hash


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
        ValueError: 題目測資包不存在
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
        
        # 4. 取得題目包 hash
        problem_hash = get_problem_testcase_hash(submission.problem_id)
        if not problem_hash:
            raise ValueError(f"Problem {submission.problem_id} has no testcase package")
        
        # 5. 組裝 payload（multipart/form-data）
        data = {
            'submission_id': str(submission.id),
            'problem_id': str(submission.problem_id),
            'problem_hash': problem_hash,
            'mode': 'normal',
            'language': language,
            'file_hash': submission.code_hash,
            'time_limit': time_limit,
            'memory_limit': memory_limit,
            'use_checker': getattr(problem, 'use_custom_checker', False),
            'checker_name': getattr(problem, 'checker_name', 'diff') or 'diff',
            'use_static_analysis': False,
            'priority': 0,
            'callback_url': f'{settings.BACKEND_BASE_URL}/submissions/callback/',
        }
        
        # 6. 準備程式碼檔案
        source_code = submission.source_code or ''
        file_extension = get_file_extension(submission.language_type)
        files = {
            'file': (f'solution{file_extension}', BytesIO(source_code.encode('utf-8')), 'text/plain')
        }
        
        # 7. 發送請求
        headers = {}
        api_key = getattr(settings, 'SANDBOX_API_KEY', None)
        if api_key:
            headers['X-API-KEY'] = api_key
        
        response = requests.post(
            f'{settings.SANDBOX_API_URL}/api/v1/submissions',
            data=data,
            files=files,
            headers=headers,
            timeout=getattr(settings, 'SANDBOX_TIMEOUT', 30)
        )
        
        response.raise_for_status()
        return response.json()
        
    except Problems.DoesNotExist:
        raise ValueError(f"Problem {submission.problem_id} does not exist")


def submit_selftest_to_sandbox(problem_id, language_type, source_code, stdin_data):
    """
    提交自定義測試到 Sandbox
    使用 /api/v1/selftest-submissions 端點
    
    Args:
        problem_id: 題目 ID
        language_type: 語言類型（0=C, 1=C++, 2=Python, 3=Java, 4=JavaScript）
        source_code: 程式碼
        stdin_data: 標準輸入資料
    
    Returns:
        dict: Sandbox 回應，包含 submission_id 和 status
    """
    import uuid
    import hashlib
    
    try:
        # 產生臨時 ID（不存 DB，只用於追蹤）
        temp_id = f"selftest-{uuid.uuid4()}"
        
        # 轉換語言代碼
        language = convert_language_code(language_type)
        
        # 計算檔案 hash
        file_content = source_code.encode('utf-8')
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 組裝 payload
        data = {
            'submission_id': temp_id,
            'problem_id': str(problem_id),
            'problem_hash': f'selftest-{problem_id}',  # 特殊標記，區分自定義測試
            'mode': 'normal',
            'language': language,
            'file_hash': file_hash,
            'stdin': stdin_data,  # 關鍵：使用 stdin 參數
            'time_limit': 2.0,  # 自定義測試設較短的時間限制
            'memory_limit': 262144,  # 256 MB
            'use_checker': False,
            'checker_name': 'diff',
            'use_static_analysis': False,
            'priority': -1,  # 低優先級（自定義測試不影響正式提交）
            'callback_url': f'{settings.BACKEND_BASE_URL}/submissions/custom-test-callback/',  # Custom test callback URL
        }
        # POST {url}
        # 準備檔案
        filename = f'solution.{get_file_extension(language)}'
        files = {
            'file': (filename, BytesIO(file_content), 'text/plain')
        }
        
        # 準備認證 header
        headers = {}
        if SANDBOX_API_KEY:
            headers['X-API-KEY'] = SANDBOX_API_KEY
        
        # 發送到 selftest 端點
        url = f'{SANDBOX_API_URL}/api/v1/selftest-submissions'
        logger.info(f'Submitting selftest: temp_id={temp_id}, problem_id={problem_id}, language={language}')
        
        response = requests.post(
            url,
            data=data,
            files=files,
            headers=headers,
            timeout=SANDBOX_TIMEOUT
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f'Selftest response: {result}')
        return {
            'test_id': temp_id,
            'submission_id': result.get('submission_id', temp_id),
            'status': result.get('status', 'queued'),
            'queue_position': result.get('queue_position'),
        }
        
    except requests.RequestException as e:
        logger.error(f'Selftest API error: {str(e)}')
        raise
        
    except Exception as e:
        logger.error(f'Unexpected error in selftest: {str(e)}')
        raise
