# submissions/test_file/test_submission_noj_compatibility.py - NOJ 兼容性測試
"""
專門測試 NOJ 兼容格式的 API 響應
確保錯誤消息和響應格式與 NOJ 原有規範一致
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, Mock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from ..models import Submission, SubmissionResult
from problems.models import Problems
from courses.models import Courses, Course_members
from .test_submission_views_api import SubmissionAPITestSetup

User = get_user_model()


class NOJCompatibilityTestCase(APITestCase):
    """NOJ 兼容性測試基類"""
    
    @classmethod
    def setUpTestData(cls):
        """設置測試數據"""
        SubmissionAPITestSetup.create_test_users()
        SubmissionAPITestSetup.create_test_courses()
        SubmissionAPITestSetup.create_test_problems()
        SubmissionAPITestSetup.create_test_submissions()
        
        # 複製測試數據
        cls.student1 = SubmissionAPITestSetup.student1
        cls.student2 = SubmissionAPITestSetup.student2
        cls.teacher = SubmissionAPITestSetup.teacher
        cls.ta = SubmissionAPITestSetup.ta
        cls.admin = SubmissionAPITestSetup.admin
        cls.course1 = SubmissionAPITestSetup.course1
        cls.course2 = SubmissionAPITestSetup.course2
        cls.problem1 = SubmissionAPITestSetup.problem1
        cls.problem2 = SubmissionAPITestSetup.problem2
        cls.submission1 = SubmissionAPITestSetup.submission1
        cls.submission2 = SubmissionAPITestSetup.submission2
    
    def authenticate_as(self, user):
        """以指定用戶身份認證"""
        self.client.force_authenticate(user=user)
    
    def get_api_message(self, response):
        """
        從 api_response 格式的響應中提取 message
        新格式: {"data": ..., "message": "...", "status": "ok/error"}
        """
        if isinstance(response.data, dict) and 'message' in response.data:
            return response.data['message']
        # 兼容舊格式（直接返回字串）
        return response.data
    
    def get_api_data(self, response):
        """
        從 api_response 格式的響應中提取 data
        新格式: {"data": {...}, "message": "...", "status": "ok/error"}
        """
        if isinstance(response.data, dict) and 'data' in response.data:
            return response.data['data']
        # 兼容舊格式（直接返回數據）
        return response.data
    
    def get_api_status(self, response):
        """
        從 api_response 格式的響應中提取 status
        新格式: {"data": ..., "message": "...", "status": "ok/error"}
        """
        if isinstance(response.data, dict) and 'status' in response.data:
            return response.data['status']
        # 根據 HTTP 狀態碼推斷
        return "ok" if 200 <= response.status_code < 400 else "error"
    
    def get_submission_create_url(self):
        """獲取創建提交的 URL"""
        return reverse('submissions:submission-list-create')
    
    def get_submission_upload_url(self, submission_id):
        """獲取上傳程式碼的 URL"""
        return reverse('submissions:submission-retrieve-update', kwargs={'id': submission_id})
    
    def get_submission_detail_url(self, submission_id):
        """獲取提交詳情的 URL"""
        return reverse('submissions:submission-retrieve-update', kwargs={'id': submission_id})
    
    def get_submission_code_url(self, submission_id):
        """獲取提交程式碼的 URL"""
        return reverse('submissions:submission-code', kwargs={'id': submission_id})
    
    def get_submission_stdout_url(self, submission_id):
        """獲取提交輸出的 URL"""
        return reverse('submissions:submission-stdout', kwargs={'id': submission_id})
    
    def get_submission_rejudge_url(self, submission_id):
        """獲取重新判題的 URL"""
        return reverse('submissions:submission-rejudge', kwargs={'id': submission_id})


class TestNOJSubmissionCreateAPI(NOJCompatibilityTestCase):
    """測試 POST /submission/ NOJ 兼容性"""
    
    def test_create_submission_missing_problem_id(self):
        """測試 NOJ 格式：缺少 problem_id"""
        self.authenticate_as(self.student1)
        
        data = {
            'language_type': 2  # Python (整數格式)
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "problemId is required!")
    
    def test_create_submission_invalid_problem_id(self):
        """測試 NOJ 格式：無效的 problem_id"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': 'invalid',
            'language_type': 2
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "problemId is required!")
    
    def test_create_submission_missing_language_type(self):
        """測試 NOJ 格式：缺少 language_type"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': self.problem1.id
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "post data missing!")
    
    def test_create_submission_invalid_language_type(self):
        """測試 NOJ 格式：無效的 language_type"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': self.problem1.id,
            'language_type': 999  # 無效的語言類型
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.get_api_message(response), "not allowed language")
    
    def test_create_submission_nonexistent_problem(self):
        """測試 NOJ 格式：不存在的題目"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': 99999,
            'language_type': 2
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get_api_message(response), "Unexisted problem id.")
    
    def test_create_submission_success_noj_format(self):
        """測試 NOJ 格式：成功創建提交"""
        self.authenticate_as(self.student1)
        
        data = {
            'problem_id': self.problem1.id,
            'language_type': 2  # Python
        }
        
        response = self.client.post(self.get_submission_create_url(), data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # NOJ 格式：submission received.{submissionId}
        self.assertTrue(self.get_api_message(response).startswith("submission received."))
        
        # 驗證提交已創建
        submission_id = self.get_api_message(response).split('.')[1]
        self.assertTrue(Submission.objects.filter(id=submission_id).exists())
    
    def test_create_submission_valid_languages(self):
        """測試所有有效的語言類型 (NOJ 整數格式)"""
        self.authenticate_as(self.student1)
        
        valid_languages = [0, 1, 2, 3, 4]  # C, C++, Python, Java, JavaScript
        
        for lang_type in valid_languages:
            data = {
                'problem_id': self.problem1.id,
                'language_type': lang_type
            }
            
            response = self.client.post(self.get_submission_create_url(), data)
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(self.get_api_message(response).startswith("submission received."))


class TestNOJSubmissionUploadAPI(NOJCompatibilityTestCase):
    """測試 PUT /submission/{id} NOJ 兼容性"""
    
    def setUp(self):
        """為每個測試設置新的提交"""
        super().setUp()
        # 創建一個新的空提交
        self.empty_submission = Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student1,
            language_type=2,
            source_code='',  # 空程式碼
            status='-2'  # Pending before upload
        )
    
    def test_upload_code_user_not_equal(self):
        """測試 NOJ 格式：用戶不匹配"""
        self.authenticate_as(self.student2)  # 不同的用戶
        
        data = {
            'source_code': 'print("Hello World")'
        }
        
        response = self.client.put(
            self.get_submission_upload_url(self.empty_submission.id), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.get_api_message(response), "user not equal!")
    
    def test_upload_code_already_judged(self):
        """測試 NOJ 格式：已完成判題"""
        # 設置提交為已判題
        judged_submission = Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student1,
            language_type=2,
            source_code='print("test")',
            status='0',  # Accepted - 這會使 is_judged 為 True
        )
        
        self.authenticate_as(self.student1)
        
        data = {
            'source_code': 'print("Hello World")'
        }
        
        response = self.client.put(
            self.get_submission_upload_url(judged_submission.id), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.get_api_message(response), f"{judged_submission.id} has finished judgement.")
    
    def test_upload_code_already_uploaded(self):
        """測試 NOJ 格式：已上傳程式碼"""
        # 設置提交已有程式碼
        uploaded_submission = Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student1,
            language_type=2,
            source_code='existing code',
            status='-1'  # Pending
        )
        
        self.authenticate_as(self.student1)
        
        data = {
            'source_code': 'print("Hello World")'
        }
        
        response = self.client.put(
            self.get_submission_upload_url(uploaded_submission.id), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.get_api_message(response), f"{uploaded_submission.id} has been uploaded source file!")
    
    def test_upload_code_empty_file(self):
        """測試 NOJ 格式：空檔案"""
        self.authenticate_as(self.student1)
        
        data = {
            'source_code': ''  # 空程式碼
        }
        
        response = self.client.put(
            self.get_submission_upload_url(self.empty_submission.id), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "empty file")
    
    def test_upload_code_whitespace_only(self):
        """測試 NOJ 格式：只有空白字符"""
        self.authenticate_as(self.student1)
        
        data = {
            'source_code': '   \n\t  \n   '  # 只有空白
        }
        
        response = self.client.put(
            self.get_submission_upload_url(self.empty_submission.id), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "empty file")
    
    def test_upload_code_nonexistent_submission(self):
        """測試 NOJ 格式：提交不存在"""
        self.authenticate_as(self.student1)
        
        fake_uuid = str(uuid.uuid4())
        data = {
            'source_code': 'print("Hello World")'
        }
        
        response = self.client.put(
            self.get_submission_upload_url(fake_uuid), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "can not find the source file")
    
    def test_upload_code_success_noj_format(self):
        """測試 NOJ 格式：成功上傳程式碼"""
        self.authenticate_as(self.student1)
        
        data = {
            'source_code': 'print("Hello World")'
        }
        
        response = self.client.put(
            self.get_submission_upload_url(self.empty_submission.id), 
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_api_message(response), f"{self.empty_submission.id} send to judgement.")
        
        # 驗證程式碼已保存
        self.empty_submission.refresh_from_db()
        self.assertEqual(self.empty_submission.source_code, 'print("Hello World")')


class TestNOJSubmissionRetrieveAPI(NOJCompatibilityTestCase):
    """測試 GET 端點的 NOJ 兼容性"""
    
    def test_get_submission_list_noj_format(self):
        """測試 NOJ 格式：獲取提交列表"""
        self.authenticate_as(self.student1)
        
        response = self.client.get('/submission/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(self.get_api_message(response), 'here you are, bro')
    
    def test_get_submission_detail_noj_format(self):
        """測試 NOJ 格式：獲取提交詳情"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(self.get_submission_detail_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(self.get_api_message(response), 'here you are, bro')
    
    def test_get_submission_detail_no_permission(self):
        """測試 NOJ 格式：無權限查看提交"""
        self.authenticate_as(self.student2)  # 不同用戶
        
        response = self.client.get(self.get_submission_detail_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.get_api_message(response), "no permission")
    
    def test_get_submission_detail_not_found(self):
        """測試 NOJ 格式：提交不存在"""
        self.authenticate_as(self.student1)
        
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(self.get_submission_detail_url(fake_uuid))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get_api_message(response), "can not find submission")
    
    def test_get_submission_code_noj_format(self):
        """測試 NOJ 格式：獲取提交程式碼"""
        # 確保提交有程式碼
        self.submission1.source_code = 'print("test")'
        self.submission1.save()
        
        self.authenticate_as(self.student1)
        
        response = self.client.get(self.get_submission_code_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(self.get_api_message(response), 'here you are, bro')
    
    def test_get_submission_code_no_source_file(self):
        """測試 NOJ 格式：找不到程式碼檔案"""
        # 確保提交沒有程式碼
        self.submission1.source_code = ''
        self.submission1.save()
        
        self.authenticate_as(self.student1)
        
        response = self.client.get(self.get_submission_code_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get_api_message(response), "can not find the source file")
    
    def test_get_submission_stdout_noj_format(self):
        """測試 NOJ 格式：獲取提交輸出"""
        self.authenticate_as(self.student1)
        
        response = self.client.get(self.get_submission_stdout_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(self.get_api_message(response), 'here you are, bro')


class TestNOJSubmissionRejudgeAPI(NOJCompatibilityTestCase):
    """測試 GET /submission/{id}/rejudge NOJ 兼容性"""
    
    def test_rejudge_submission_no_permission(self):
        """測試 NOJ 格式：無權限重新判題"""
        self.authenticate_as(self.student1)  # 普通學生
        
        response = self.client.get(self.get_submission_rejudge_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.get_api_message(response), "no permission")
    
    def test_rejudge_submission_not_found(self):
        """測試 NOJ 格式：提交不存在"""
        self.authenticate_as(self.teacher)  # 有權限的老師
        
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(self.get_submission_rejudge_url(fake_uuid))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get_api_message(response), "can not find submission")
    
    def test_rejudge_submission_no_source_code(self):
        """測試 NOJ 格式：沒有程式碼無法重新判題"""
        # 創建沒有程式碼的提交
        empty_submission = Submission.objects.create(
            problem_id=self.problem1.id,
            user=self.student1,
            language_type=2,
            source_code='',
            status='-2'  # Pending before upload
        )
        
        self.authenticate_as(self.teacher)  # 有權限的老師
        
        response = self.client.get(self.get_submission_rejudge_url(empty_submission.id))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.get_api_message(response), "can not find the source file")
    
    def test_rejudge_submission_success_noj_format(self):
        """測試 NOJ 格式：成功重新判題"""
        # 確保提交有程式碼且已判題
        self.submission1.source_code = 'print("test")'
        self.submission1.status = '0'  # Accepted
        self.submission1.save()
        
        self.authenticate_as(self.teacher)  # 有權限的老師
        
        response = self.client.get(self.get_submission_rejudge_url(self.submission1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.get_api_message(response), f"{self.submission1.id} rejudge successfully.")


class TestNOJRankingAPI(NOJCompatibilityTestCase):
    """測試 GET /ranking NOJ 兼容性"""
    
    def test_get_ranking_noj_format(self):
        """測試 NOJ 格式：獲取排行榜"""
        self.authenticate_as(self.student1)
        
        response = self.client.get('/ranking/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(self.get_api_message(response), 'here you are, bro')
        self.assertIn('ranking', self.get_api_data(response))
        self.assertIsInstance(self.get_api_data(response)['ranking'], list)


class TestNOJLanguageTypes(NOJCompatibilityTestCase):
    """測試 NOJ 整數語言類型兼容性"""
    
    def test_language_type_integers(self):
        """測試所有語言類型都是整數"""
        from ..models import Submission
        
        expected_languages = {
            0: 'C',
            1: 'C++',
            2: 'Python',
            3: 'Java',
            4: 'JavaScript'
        }
        
        # 驗證模型中的語言選項
        model_languages = dict(Submission.LANGUAGE_CHOICES)
        
        for lang_id, lang_name in expected_languages.items():
            self.assertIn(lang_id, model_languages)
            self.assertEqual(model_languages[lang_id], lang_name)
    
    def test_create_submission_with_integer_languages(self):
        """測試使用整數語言類型創建提交"""
        self.authenticate_as(self.student1)
        
        # 測試所有支援的語言類型
        for lang_type in [0, 1, 2, 3, 4]:
            data = {
                'problem_id': self.problem1.id,
                'language_type': lang_type
            }
            
            response = self.client.post(self.get_submission_create_url(), data)
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(self.get_api_message(response).startswith("submission received."))
            
            # 驗證創建的提交有正確的語言類型
            submission_id = self.get_api_message(response).split('.')[1]
            submission = Submission.objects.get(id=submission_id)
            self.assertEqual(submission.language_type, lang_type)