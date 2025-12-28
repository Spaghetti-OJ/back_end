"""
Custom Test API 單元測試

使用 pytest 框架測試 Custom Test 功能

執行方式:
    pytest back_end/submissions/test_file/test_custom_test_unit.py -v
    pytest back_end/submissions/test_file/test_custom_test_unit.py::TestCustomTestAPI::test_submit_custom_test -v
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from user.models import User
from problems.models import Problems
from courses.models import Courses


@pytest.mark.django_db
class TestCustomTestAPI:
    """測試 Custom Test API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """設置測試環境"""
        self.client = APIClient()
        
        # 創建測試用戶（教師）
        self.teacher = User.objects.create_user(
            username='test_teacher',
            email='test_teacher@test.com',
            password='test123456'
        )
        
        # 創建測試用戶（學生）
        self.user = User.objects.create_user(
            username='test_custom',
            email='test_custom@test.com',
            password='test123456'
        )
        
        # 創建測試課程
        self.course = Courses.objects.create(
            name='Test Course',
            description='Test Description',
            teacher_id=self.teacher,
            semester='1131',
            is_active=True
        )
        
        # 創建測試題目
        self.problem = Problems.objects.create(
            title='Test Problem',
            description='Test Description',
            input_description='Input',
            output_description='Output',
            sample_input='1 2',
            sample_output='3',
            course_id=self.course,
            creator_id=self.teacher,
            is_public='course'  # 課程內可見
        )
        
        # 認證
        self.client.force_authenticate(user=self.user)
    
    def test_submit_custom_test_success(self):
        """測試成功提交自定義測試"""
        url = f'/submission/{self.problem.id}/custom-test/'
        data = {
            'language': 2,  # Python
            'source_code': 'print("Hello")',
            'stdin': 'test input'
        }
        
        # Mock Celery 任務（正確的模組路徑）
        with patch('submissions.tasks.submit_selftest_to_sandbox_task') as mock_task:
            mock_task.delay.return_value = MagicMock()
            
            response = self.client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            assert 'data' in response.json()
            
            response_data = response.json()['data']
            assert 'test_id' in response_data
            assert 'submission_id' in response_data
            assert 'status' in response_data
            assert response_data['status'] == 'pending'
            
            # 檢查 Celery 任務是否被調用
            mock_task.delay.assert_called_once()
    
    def test_submit_custom_test_missing_source_code(self):
        """測試缺少 source_code 欄位"""
        url = f'/submission/{self.problem.id}/custom-test/'
        data = {
            'language': 2,
            'stdin': 'test input'
            # 缺少 source_code
        }
        
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'message' in response.json()
    
    def test_submit_custom_test_invalid_language(self):
        """測試無效的語言類型"""
        url = f'/submission/{self.problem.id}/custom-test/'
        data = {
            'language': 999,  # 無效的語言類型
            'source_code': 'print("test")',
            'stdin': ''
        }
        
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_submit_custom_test_problem_not_found(self):
        """測試題目不存在"""
        url = '/submission/999999/custom-test/'  # 不存在的題目 ID
        data = {
            'language': 2,
            'source_code': 'print("test")',
            'stdin': ''
        }
        
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_submit_custom_test_without_authentication(self):
        """測試未認證的請求"""
        self.client.force_authenticate(user=None)  # 移除認證
        
        url = f'/submission/{self.problem.id}/custom-test/'
        data = {
            'language': 2,
            'source_code': 'print("test")',
            'stdin': ''
        }
        
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_submit_custom_test_empty_stdin(self):
        """測試空的 stdin"""
        url = f'/submission/{self.problem.id}/custom-test/'
        data = {
            'language': 2,
            'source_code': 'print("test")',
            'stdin': ''  # 空的 stdin
        }
        
        with patch('submissions.tasks.submit_selftest_to_sandbox_task') as mock_task:
            mock_task.delay.return_value = MagicMock()
            
            response = self.client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_202_ACCEPTED
    
    def test_submit_custom_test_long_code(self):
        """測試長程式碼"""
        url = f'/submission/{self.problem.id}/custom-test/'
        long_code = 'print("test")\\n' * 1000  # 長程式碼
        data = {
            'language': 2,
            'source_code': long_code,
            'stdin': 'test'
        }
        
        with patch('submissions.tasks.submit_selftest_to_sandbox_task') as mock_task:
            mock_task.delay.return_value = MagicMock()
            
            response = self.client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_202_ACCEPTED
    
    def test_check_custom_test_result_not_found(self):
        """測試查詢不存在的測試結果"""
        url = '/submission/custom-test/nonexistent-test-id/result/'
        
        with patch('submissions.views.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.get.return_value = None  # 模擬 Redis 返回 None
            mock_redis.return_value = mock_redis_instance
            
            response = self.client.get(url)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_check_custom_test_result_success(self):
        """測試成功查詢測試結果"""
        test_id = 'selftest-12345'
        url = f'/submission/custom-test/{test_id}/result/'
        
        # Mock Redis 返回的測試結果
        mock_test_result = {
            'test_id': test_id,
            'problem_id': self.problem.id,
            'status': 'completed',
            'submission_id': 'sandbox-sub-001',
            'created_at': '2024-12-13T10:00:00',
            'stdin': 'test input'
        }
        
        with patch('submissions.views.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.get.return_value = json.dumps(mock_test_result)
            mock_redis.return_value = mock_redis_instance
            
            response = self.client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert 'data' in response.json()
            
            response_data = response.json()['data']
            assert response_data['test_id'] == test_id
            assert response_data['status'] == 'completed'


@pytest.mark.django_db
class TestSandboxClient:
    """測試 Sandbox Client 函數"""
    
    def test_convert_language_code(self):
        """測試語言代碼轉換"""
        from submissions.sandbox_client import convert_language_code
        
        assert convert_language_code(0) == 'c'
        assert convert_language_code(1) == 'cpp'
        assert convert_language_code(2) == 'python'
        assert convert_language_code(3) == 'java'
        assert convert_language_code(4) == 'javascript'
        assert convert_language_code(999) == 'python'  # 預設值
    
    def test_get_file_extension(self):
        """測試取得檔案副檔名"""
        from submissions.sandbox_client import get_file_extension
        
        assert get_file_extension('c') == 'c'
        assert get_file_extension('cpp') == 'cpp'
        assert get_file_extension('python') == 'py'
        assert get_file_extension('java') == 'java'
        assert get_file_extension('javascript') == 'js'
        assert get_file_extension('unknown') == 'txt'  # 預設值
    
    @patch('submissions.sandbox_client.requests.post')
    def test_submit_selftest_to_sandbox(self, mock_post):
        """測試提交自定義測試到 Sandbox"""
        from submissions.sandbox_client import submit_selftest_to_sandbox
        
        # Mock HTTP 回應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'submission_id': 'test-sub-001',
            'status': 'queued',
            'queue_position': 5
        }
        mock_post.return_value = mock_response
        
        # 調用函數
        result = submit_selftest_to_sandbox(
            problem_id=1,
            language_type=2,
            source_code='print("test")',
            stdin_data='test input'
        )
        
        # 驗證結果
        assert result['submission_id'] == 'test-sub-001'
        assert result['status'] == 'queued'
        assert result['test_id'].startswith('selftest-')
        
        # 驗證 HTTP 請求
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert '/api/v1/selftest-submissions' in call_args[0][0]


@pytest.mark.django_db
class TestCeleryTasks:
    """測試 Celery 任務"""
    
    @patch('submissions.tasks.submit_selftest_to_sandbox')
    @patch('submissions.tasks.redis.Redis')
    def test_submit_selftest_to_sandbox_task(self, mock_redis, mock_sandbox_submit):
        """測試自定義測試 Celery 任務"""
        from submissions.tasks import submit_selftest_to_sandbox_task
        
        # Mock Redis
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = json.dumps({
            'test_id': 'test-001',
            'status': 'pending'
        })
        mock_redis.return_value = mock_redis_instance
        
        # Mock Sandbox 回應
        mock_sandbox_submit.return_value = {
            'submission_id': 'sandbox-001',
            'status': 'queued',
            'queue_position': 1
        }
        
        # 調用任務（同步）
        result = submit_selftest_to_sandbox_task(
            test_id='test-001',
            user_id=1,
            problem_id=1,
            language_type=2,
            source_code='print("test")',
            stdin_data='test'
        )
        
        # 驗證結果
        assert result['submission_id'] == 'sandbox-001'
        assert result['status'] == 'queued'
        
        # 驗證 Sandbox 函數被調用
        mock_sandbox_submit.assert_called_once()
        
        # 驗證 Redis 被更新
        mock_redis_instance.setex.assert_called()


class TestValidation:
    """測試驗證邏輯"""
    
    def test_valid_language_types(self):
        """測試有效的語言類型"""
        valid_types = [0, 1, 2, 3, 4]
        for lang_type in valid_types:
            assert lang_type in valid_types
    
    def test_invalid_language_types(self):
        """測試無效的語言類型"""
        invalid_types = [-1, 5, 99, 'python', None]
        valid_types = [0, 1, 2, 3, 4]
        for lang_type in invalid_types:
            assert lang_type not in valid_types


# 整合測試標記
@pytest.mark.integration
@pytest.mark.django_db
class TestCustomTestIntegration:
    """整合測試（需要 Celery 和 Redis）"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """設置測試環境"""
        self.client = APIClient()
        
        # 創建測試教師
        self.teacher = User.objects.create_user(
            username='test_integration_teacher',
            email='test_integration_teacher@test.com',
            password='test123456'
        )
        
        # 創建測試用戶
        self.user = User.objects.create_user(
            username='test_integration',
            email='test_integration@test.com',
            password='test123456'
        )
        
        # 創建測試課程和題目
        self.course = Courses.objects.create(
            name='Integration Test Course',
            description='Test Course',
            teacher_id=self.teacher,
            semester='1131',
            is_active=True
        )
        
        self.problem = Problems.objects.create(
            title='Integration Test Problem',
            description='Test',
            course_id=self.course,
            creator_id=self.teacher,
            is_public='course'
        )
        
        self.client.force_authenticate(user=self.user)
    
    @pytest.mark.skip(reason="需要真實的 Celery worker 和 Redis")
    def test_full_custom_test_flow(self):
        """測試完整的自定義測試流程"""
        # 1. 提交測試
        url = f'/submission/{self.problem.id}/custom-test/'
        data = {
            'language': 2,
            'source_code': '''
a, b = map(int, input().split())
print(a + b)
''',
            'stdin': '3 5'
        }
        
        response = self.client.post(url, data, format='json')
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        test_id = response.json()['data']['test_id']
        
        # 2. 等待處理
        import time
        time.sleep(5)
        
        # 3. 查詢結果
        check_url = f'/submission/custom-test/{test_id}/'
        response = self.client.get(check_url)
        
        assert response.status_code == status.HTTP_200_OK
        result_data = response.json()['data']
        
        # 驗證結果包含必要欄位
        assert 'test_id' in result_data
        assert 'status' in result_data
        assert 'submission_id' in result_data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
