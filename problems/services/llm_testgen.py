"""
LLM Test Data Generation Service

封裝與 LLM 測資生成服務的 API 互動邏輯
"""

import requests
import logging
from io import BytesIO
from typing import Optional, List, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)

# LLM 測資生成服務設定
LLM_TESTGEN_API_URL = getattr(settings, 'LLM_TESTGEN_API_URL', 'http://34.81.90.111:8001')
LLM_TESTGEN_TIMEOUT = getattr(settings, 'LLM_TESTGEN_TIMEOUT', 120)  # 120 秒超時（LLM 生成可能較慢）


def get_solution_runtime(language: str) -> str:
    """
    將 Django 的語言名稱轉換成 LLM 服務的 runtime 格式
    
    Django: 'c', 'cpp', 'python', 'java', 'javascript'
    LLM Service: 'c', 'cpp', 'python', 'java'
    """
    language_map = {
        'c': 'c',
        'cpp': 'cpp',
        'c++': 'cpp',
        'python': 'python',
        'py': 'python',
        'java': 'java',
        'javascript': 'python',  # LLM 服務不支援 JS，暫時用 python
        'js': 'python',
    }
    return language_map.get(language.lower(), 'python')


def upload_solution(source_code: str, language: str) -> Dict[str, Any]:
    """
    上傳正解程式到 LLM 服務
    
    Args:
        source_code: 正解程式碼
        language: 程式語言 (c, cpp, python, java)
    
    Returns:
        dict: {
            'ok': bool,
            'solution_id': str (如果成功),
            'error': str (如果失敗)
        }
    """
    try:
        runtime = get_solution_runtime(language)
        
        # 建立檔案物件
        extension_map = {
            'c': 'c',
            'cpp': 'cpp',
            'python': 'py',
            'java': 'java',
        }
        ext = extension_map.get(runtime, 'txt')
        filename = f'solution.{ext}'
        
        files = {
            'file': (filename, BytesIO(source_code.encode('utf-8')), 'text/plain')
        }
        data = {
            'runtime': runtime
        }
        
        url = f'{LLM_TESTGEN_API_URL}/api/upload-solution'
        logger.info(f'Uploading solution to LLM service: {url}')
        
        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=LLM_TESTGEN_TIMEOUT
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f'Upload solution response: {result}')
        return result
        
    except requests.exceptions.Timeout:
        logger.error('Upload solution timeout')
        return {'ok': False, 'error': 'LLM 服務連線逾時'}
    except requests.exceptions.ConnectionError:
        logger.error('Upload solution connection error')
        return {'ok': False, 'error': 'LLM 服務連線失敗'}
    except requests.exceptions.RequestException as e:
        logger.error(f'Upload solution request error: {str(e)}')
        return {'ok': False, 'error': f'請求錯誤: {str(e)}'}
    except Exception as e:
        logger.error(f'Upload solution error: {str(e)}')
        return {'ok': False, 'error': f'未知錯誤: {str(e)}'}


def generate_testcases(
    problem_statement: str,
    input_spec: str,
    output_spec: Optional[str] = None,
    constraints: Optional[str] = None,
    subtasks: Optional[List[Dict]] = None,
    num_cases: Optional[int] = None,
    mode: str = 'LLM_DIRECT',
    solution_id: Optional[str] = None,
    examples: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    呼叫 LLM 服務生成測資
    
    Args:
        problem_statement: 題目敘述
        input_spec: 輸入格式說明
        output_spec: 輸出格式說明
        constraints: 限制條件
        subtasks: 子任務列表 [{'id': 1, 'name': 'subtask1', 'desc': '...', 'num': 5}]
        num_cases: 測資數量（若無 subtasks）
        mode: 模式 - 'LLM_INPUT_ONLY' 或 'LLM_DIRECT'
        solution_id: 正解 ID（LLM_INPUT_ONLY 必填）
        examples: 範例測資 [{'input': '...', 'output': '...'}]
    
    Returns:
        dict: {
            'ok': bool,
            'data': {...} (如果成功),
            'error': str (如果失敗)
        }
    """
    try:
        payload = {
            'problem_statement': problem_statement,
            'input_spec': input_spec,
            'mode': mode,
        }
        
        if output_spec:
            payload['output_spec'] = output_spec
        
        if constraints:
            payload['constraints'] = constraints
        
        if subtasks:
            payload['subtasks'] = subtasks
        
        if num_cases:
            payload['num_cases'] = num_cases
        
        if solution_id:
            payload['solution_id'] = solution_id
        
        if examples:
            payload['examples'] = examples
        
        url = f'{LLM_TESTGEN_API_URL}/api/generate-testcases'
        logger.info(f'Generating testcases via LLM service: {url}')
        logger.debug(f'Generate request payload: {payload}')
        
        response = requests.post(
            url,
            json=payload,
            timeout=LLM_TESTGEN_TIMEOUT
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f'Generate testcases response ok: {result.get("ok")}')
        return result
        
    except requests.exceptions.Timeout:
        logger.error('Generate testcases timeout')
        return {'ok': False, 'error': 'LLM 服務連線逾時（生成測資可能需要較長時間）'}
    except requests.exceptions.ConnectionError:
        logger.error('Generate testcases connection error')
        return {'ok': False, 'error': 'LLM 服務連線失敗'}
    except requests.exceptions.RequestException as e:
        logger.error(f'Generate testcases request error: {str(e)}')
        return {'ok': False, 'error': f'請求錯誤: {str(e)}'}
    except Exception as e:
        logger.error(f'Generate testcases error: {str(e)}')
        return {'ok': False, 'error': f'未知錯誤: {str(e)}'}


def list_solutions() -> Dict[str, Any]:
    """
    列出所有已上傳的正解
    
    Returns:
        dict: API 回應
    """
    try:
        url = f'{LLM_TESTGEN_API_URL}/api/solutions'
        response = requests.get(url, timeout=LLM_TESTGEN_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f'List solutions error: {str(e)}')
        return {'error': str(e)}


def delete_solution(solution_id: str) -> Dict[str, Any]:
    """
    刪除正解
    
    Args:
        solution_id: 正解 ID
    
    Returns:
        dict: API 回應
    """
    try:
        url = f'{LLM_TESTGEN_API_URL}/api/solutions/{solution_id}'
        response = requests.delete(url, timeout=LLM_TESTGEN_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f'Delete solution error: {str(e)}')
        return {'error': str(e)}


def health_check() -> bool:
    """
    檢查 LLM 服務健康狀態
    
    Returns:
        bool: 服務是否正常
    """
    try:
        url = f'{LLM_TESTGEN_API_URL}/health'
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def generate_testcases_for_problem(problem) -> Dict[str, Any]:
    """
    根據題目資訊自動選擇模式並生成測資
    
    Args:
        problem: Problems model instance
    
    Returns:
        dict: {
            'ok': bool,
            'mode': str,
            'data': {...},
            'error': str (如果失敗)
        }
    """
    from problems.models import Problem_subtasks
    
    # 建構題目敘述
    problem_statement = problem.description
    
    # 輸入/輸出格式
    input_spec = problem.input_description or ''
    output_spec = problem.output_description or ''
    
    # 限制條件（從 subtask_description 或其他欄位取得）
    constraints = problem.subtask_description or problem.hint or ''
    
    # 範例測資
    examples = []
    if problem.sample_input and problem.sample_output:
        examples.append({
            'input': problem.sample_input,
            'output': problem.sample_output
        })
    
    # 取得 subtasks
    subtasks_qs = Problem_subtasks.objects.filter(problem_id=problem.id).order_by('subtask_no')
    subtasks = []
    
    if subtasks_qs.exists():
        for st in subtasks_qs:
            subtasks.append({
                'id': st.subtask_no,
                'name': f'Subtask {st.subtask_no}',
                'desc': st.description or '',
                'num': st.num_testcases if hasattr(st, 'num_testcases') else 5
            })
    
    # 決定生成模式
    has_solution = bool(problem.solution_code and problem.solution_code.strip())
    
    if has_solution:
        # 使用 LLM_INPUT_ONLY 模式：先上傳正解，再生成測資
        logger.info(f'Problem {problem.id} has solution code, using LLM_INPUT_ONLY mode')
        
        # 上傳正解
        upload_result = upload_solution(
            source_code=problem.solution_code,
            language=problem.solution_code_language or 'python'
        )
        
        if not upload_result.get('ok'):
            return {
                'ok': False,
                'mode': 'LLM_INPUT_ONLY',
                'error': f"上傳正解失敗: {upload_result.get('error', '未知錯誤')}"
            }
        
        solution_id = upload_result.get('solution_id')
        
        # 生成測資
        gen_result = generate_testcases(
            problem_statement=problem_statement,
            input_spec=input_spec,
            output_spec=output_spec,
            constraints=constraints,
            subtasks=subtasks if subtasks else None,
            num_cases=5 if not subtasks else None,
            mode='LLM_INPUT_ONLY',
            solution_id=solution_id,
            examples=examples if examples else None
        )
        
        # 清理上傳的正解
        try:
            delete_solution(solution_id)
        except Exception as e:
            logger.warning(f'Failed to delete solution {solution_id}: {str(e)}')
        
        gen_result['mode'] = 'LLM_INPUT_ONLY'
        return gen_result
    
    else:
        # 使用 LLM_DIRECT 模式：直接生成 input 和 output
        logger.info(f'Problem {problem.id} has no solution code, using LLM_DIRECT mode')
        
        gen_result = generate_testcases(
            problem_statement=problem_statement,
            input_spec=input_spec,
            output_spec=output_spec,
            constraints=constraints,
            subtasks=subtasks if subtasks else None,
            num_cases=5 if not subtasks else None,
            mode='LLM_DIRECT',
            examples=examples if examples else None
        )
        
        gen_result['mode'] = 'LLM_DIRECT'
        return gen_result
