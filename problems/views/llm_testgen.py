"""
LLM Test Data Generation Views

提供 LLM 自動生成測資的 API endpoints
"""

import logging
import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from problems.models import Problems, Problem_subtasks, Test_cases
from problems.services.llm_testgen import (
    generate_testcases_for_problem,
    generate_testcases,
    upload_solution,
    delete_solution,
    health_check,
)

logger = logging.getLogger(__name__)


def api_response(data=None, message="OK", status_code=200):
    """統一的 API 響應格式"""
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)


class LLMTestGenHealthView(APIView):
    """
    GET /problem/llm-testgen/health
    
    檢查 LLM 測資生成服務健康狀態
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        is_healthy = health_check()
        
        if is_healthy:
            return api_response(
                data={'status': 'healthy'},
                message='LLM 測資生成服務正常',
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                data={'status': 'unhealthy'},
                message='LLM 測資生成服務無法連線',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class LLMTestGenGenerateView(APIView):
    """
    POST /problem/{pk}/llm-testgen/generate
    
    根據題目資訊自動生成測資
    
    Request Body (optional):
    {
        "num_cases": 5,  // 覆蓋預設測資數量
        "subtasks": [    // 覆蓋 subtask 設定
            {"id": 1, "name": "Easy", "desc": "N <= 100", "num": 3},
            {"id": 2, "name": "Hard", "desc": "N <= 10000", "num": 5}
        ]
    }
    
    Response:
    {
        "data": {
            "ok": true,
            "mode": "LLM_INPUT_ONLY" | "LLM_DIRECT",
            "testcases": [
                {"input": "...", "output": "...", "subtask_id": 1}
            ]
        },
        "message": "測資生成成功",
        "status": "ok"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        # 取得題目
        problem = get_object_or_404(Problems, pk=pk)
        
        # 權限檢查：只有題目創建者或管理員可以生成測資
        if problem.creator_id != request.user and not request.user.is_staff:
            return api_response(
                data=None,
                message='沒有權限操作此題目',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # 檢查題目是否有基本資訊
        if not problem.description:
            return api_response(
                data=None,
                message='題目缺少描述，無法生成測資',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not problem.input_description:
            return api_response(
                data=None,
                message='題目缺少輸入格式說明，無法生成測資',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f'Generating testcases for problem {pk} by user {request.user.id}')
        
        try:
            # 呼叫 LLM 服務生成測資
            result = generate_testcases_for_problem(problem)
            
            if result.get('ok'):
                return api_response(
                    data={
                        'ok': True,
                        'mode': result.get('mode'),
                        'testcases': result.get('data', {}).get('testcases', []),
                        'raw_response': result.get('data')
                    },
                    message=f"測資生成成功（模式: {result.get('mode')}）",
                    status_code=status.HTTP_200_OK
                )
            else:
                return api_response(
                    data={'ok': False, 'error': result.get('error')},
                    message=f"測資生成失敗: {result.get('error', '未知錯誤')}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f'LLM testgen error for problem {pk}: {str(e)}', exc_info=True)
            return api_response(
                data={'ok': False, 'error': str(e)},
                message=f'測資生成失敗: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LLMTestGenCustomView(APIView):
    """
    POST /problem/{pk}/llm-testgen/custom
    
    使用自訂參數生成測資
    
    Request Body:
    {
        "problem_statement": "...",  // 可覆蓋題目敘述
        "input_spec": "...",         // 可覆蓋輸入格式
        "output_spec": "...",        // 可覆蓋輸出格式
        "constraints": "...",        // 限制條件
        "mode": "LLM_DIRECT",        // LLM_DIRECT 或 LLM_INPUT_ONLY
        "num_cases": 5,              // 測資數量
        "subtasks": [...],           // 子任務設定
        "solution_code": "...",      // 正解程式碼（LLM_INPUT_ONLY 必填）
        "solution_language": "python" // 正解語言
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        # 取得題目
        problem = get_object_or_404(Problems, pk=pk)
        
        # 權限檢查
        if problem.creator_id != request.user and not request.user.is_staff:
            return api_response(
                data=None,
                message='沒有權限操作此題目',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data
        
        # 取得參數（優先使用請求中的參數，否則使用題目欄位）
        problem_statement = data.get('problem_statement') or problem.description
        input_spec = data.get('input_spec') or problem.input_description
        output_spec = data.get('output_spec') or problem.output_description
        constraints = data.get('constraints') or problem.subtask_description or ''
        mode = data.get('mode', 'LLM_DIRECT')
        num_cases = data.get('num_cases', 5)
        subtasks = data.get('subtasks')
        
        # 範例測資
        examples = []
        if problem.sample_input and problem.sample_output:
            examples.append({
                'input': problem.sample_input,
                'output': problem.sample_output
            })
        
        # 驗證必填欄位
        if not problem_statement:
            return api_response(
                data=None,
                message='缺少題目敘述',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not input_spec:
            return api_response(
                data=None,
                message='缺少輸入格式說明',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            solution_id = None
            
            # LLM_INPUT_ONLY 模式需要正解
            if mode == 'LLM_INPUT_ONLY':
                solution_code = data.get('solution_code') or problem.solution_code
                solution_language = data.get('solution_language') or problem.solution_code_language
                
                if not solution_code:
                    return api_response(
                        data=None,
                        message='LLM_INPUT_ONLY 模式需要提供正解程式碼',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # 上傳正解
                upload_result = upload_solution(solution_code, solution_language or 'python')
                
                if not upload_result.get('ok'):
                    return api_response(
                        data={'ok': False, 'error': upload_result.get('error')},
                        message=f"上傳正解失敗: {upload_result.get('error')}",
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                solution_id = upload_result.get('solution_id')
            
            # 生成測資
            result = generate_testcases(
                problem_statement=problem_statement,
                input_spec=input_spec,
                output_spec=output_spec,
                constraints=constraints,
                subtasks=subtasks,
                num_cases=num_cases if not subtasks else None,
                mode=mode,
                solution_id=solution_id,
                examples=examples if examples else None
            )
            
            # 清理上傳的正解
            if solution_id:
                try:
                    delete_solution(solution_id)
                except Exception as e:
                    logger.warning(f'Failed to delete solution {solution_id}: {str(e)}')
            
            if result.get('ok'):
                return api_response(
                    data={
                        'ok': True,
                        'mode': mode,
                        'testcases': result.get('data', {}).get('testcases', []),
                        'raw_response': result.get('data')
                    },
                    message=f"測資生成成功（模式: {mode}）",
                    status_code=status.HTTP_200_OK
                )
            else:
                return api_response(
                    data={'ok': False, 'error': result.get('error')},
                    message=f"測資生成失敗: {result.get('error', '未知錯誤')}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f'LLM custom testgen error for problem {pk}: {str(e)}', exc_info=True)
            return api_response(
                data={'ok': False, 'error': str(e)},
                message=f'測資生成失敗: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LLMTestGenSaveView(APIView):
    """
    POST /problem/{pk}/llm-testgen/save
    
    將 LLM 生成的測資保存到題目
    
    Request Body:
    {
        "testcases": [
            {
                "input": "...",
                "output": "...",
                "subtask_id": 1  // optional, 對應到 subtask_no
            }
        ],
        "create_subtasks": true  // 是否自動建立不存在的 subtask
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        # 取得題目
        problem = get_object_or_404(Problems, pk=pk)
        
        # 權限檢查
        if problem.creator_id != request.user and not request.user.is_staff:
            return api_response(
                data=None,
                message='沒有權限操作此題目',
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data
        testcases = data.get('testcases', [])
        create_subtasks = data.get('create_subtasks', True)
        
        if not testcases:
            return api_response(
                data=None,
                message='沒有測資可保存',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            saved_count = 0
            created_subtasks = set()
            
            for tc in testcases:
                input_data = tc.get('input', '')
                output_data = tc.get('output', '')
                subtask_no = tc.get('subtask_id', 1)
                
                # 確保 subtask 存在
                subtask, created = Problem_subtasks.objects.get_or_create(
                    problem_id=problem,
                    subtask_no=subtask_no,
                    defaults={
                        'score': 100 // len(set(t.get('subtask_id', 1) for t in testcases)),
                        'description': f'Subtask {subtask_no}'
                    }
                )
                
                if created:
                    created_subtasks.add(subtask_no)
                
                # 計算 idx（該 subtask 下的測資數量 + 1）
                existing_count = Test_cases.objects.filter(subtask_id=subtask).count()
                
                # 建立測資
                Test_cases.objects.create(
                    subtask_id=subtask,
                    idx=existing_count + 1,
                    input_data=input_data,
                    expected_output=output_data
                )
                
                saved_count += 1
            
            return api_response(
                data={
                    'saved_count': saved_count,
                    'created_subtasks': list(created_subtasks)
                },
                message=f'成功保存 {saved_count} 筆測資',
                status_code=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f'Save testcases error for problem {pk}: {str(e)}', exc_info=True)
            return api_response(
                data=None,
                message=f'保存測資失敗: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
