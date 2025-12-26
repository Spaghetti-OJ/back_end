# submissions/test_file/test_editorial_api.py - 題解 API 測試
import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.django import TestCase as HypothesisTestCase

from ..models import Editorial, EditorialLike
from ..serializers import EditorialCreateSerializer, EditorialSerializer
from problems.models import Problems
from courses.models import Courses, Course_members

User = get_user_model()


class EditorialAPIHypothesisTests(HypothesisTestCase):
    """題解 API 的 Hypothesis 測試"""
    
    def setUp(self):
        """測試準備"""
        unique_id = str(uuid.uuid4())[:8]
        
        # 創建測試用戶
        self.teacher = User.objects.create_user(
            username=f'teacher_{unique_id}',
            email=f'teacher_{unique_id}@example.com',
            password='testpass123'
        )
        self.student = User.objects.create_user(
            username=f'student_{unique_id}',
            email=f'student_{unique_id}@example.com',
            password='testpass123'
        )
        self.another_teacher = User.objects.create_user(
            username=f'teacher2_{unique_id}',
            email=f'teacher2_{unique_id}@example.com',
            password='testpass123'
        )
        self.ta_user = User.objects.create_user(
            username=f'ta_{unique_id}',
            email=f'ta_{unique_id}@example.com',
            password='testpass123'
        )
        
        # 創建課程
        self.course = Courses.objects.create(
            name=f'測試課程_{unique_id}',
            description='測試課程描述',
            teacher_id=self.teacher
        )
        
        # 創建另一個課程
        self.another_course = Courses.objects.create(
            name=f'另一個課程_{unique_id}',
            description='另一個測試課程',
            teacher_id=self.another_teacher
        )
        
        # 將學生和 TA 加入課程
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.student,
            role=Course_members.Role.STUDENT
        )
        Course_members.objects.create(
            course_id=self.course,
            user_id=self.ta_user,
            role=Course_members.Role.TA
        )
        
        # 創建測試問題
        self.problem = Problems.objects.create(
            title=f'測試問題_{unique_id}',
            description='測試問題描述',
            creator_id=self.teacher,
            course_id=self.course
        )
        
        # 創建另一個問題（不同課程）
        self.another_problem = Problems.objects.create(
            title=f'另一個問題_{unique_id}',
            description='另一個測試問題',
            creator_id=self.another_teacher,
            course_id=self.another_course
        )
        
        # JWT Token
        self.teacher_token = RefreshToken.for_user(self.teacher).access_token
        self.student_token = RefreshToken.for_user(self.student).access_token
        self.another_teacher_token = RefreshToken.for_user(self.another_teacher).access_token
        self.ta_token = RefreshToken.for_user(self.ta_user).access_token
    
    def authenticate_user(self, token):
        """設置認證"""
        from rest_framework.test import APIClient
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client
    
    @given(
        title=st.text(min_size=10, max_size=100, alphabet=st.characters(
            blacklist_categories=['Cc', 'Cs'],
            blacklist_characters=['\x00']
        )).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=500, alphabet=st.characters(
            blacklist_categories=['Cc', 'Cs'], 
            blacklist_characters=['\x00']
        )).filter(lambda x: x.strip()),
        difficulty_rating=st.floats(min_value=1.0, max_value=5.0).map(
            lambda x: round(x, 1)
        ),
        is_official=st.booleans()
    )
    @settings(max_examples=10)
    def test_teacher_can_create_editorial_with_random_data(
        self, title, content, difficulty_rating, is_official
    ):
        """測試老師可以用各種隨機資料創建題解"""
        assume(title.strip())
        assume(content.strip())
        
        client = self.authenticate_user(self.teacher_token)
        
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id
        })
        data = {
            'title': title,
            'content': content,
            'difficulty_rating': difficulty_rating,
            'is_official': is_official
        }
        
        response = client.post(url, data, format='json')
        
        # 驗證創建成功
        assert response.status_code == status.HTTP_201_CREATED, f"Failed with data: {data}, errors: {response.data}"
        assert response.data['title'] == title.strip()
        assert response.data['content'] == content.strip()
        assert float(response.data['difficulty_rating']) == difficulty_rating
        assert response.data['is_official'] == is_official
        assert response.data['author_username'] == self.teacher.username
        assert response.data['status'] == 'published'
        
        # 驗證資料庫
        editorial = Editorial.objects.get(id=response.data['id'])
        assert editorial.problem_id == self.problem.id
        assert editorial.author == self.teacher
    
    @given(
        invalid_data=st.one_of(
            st.fixed_dictionaries({
                'title': st.just(''),  # 空標題
                'content': st.just('這是有效的內容，足夠長度'),
                'difficulty_rating': st.just(3.0),
                'is_official': st.just(False)
            }),
            st.fixed_dictionaries({
                'title': st.just('有效標題'),
                'content': st.just('太短'),  # 內容太短
                'difficulty_rating': st.just(3.0),
                'is_official': st.just(False)
            }),
            st.fixed_dictionaries({
                'title': st.text(min_size=256, max_size=300),  # 標題太長
                'content': st.just('這是有效的內容，足夠長度'),
                'difficulty_rating': st.just(3.0),
                'is_official': st.just(False)
            })
        )
    )
    @settings(max_examples=3)
    def test_editorial_creation_validation_failures(self, invalid_data):
        """測試題解創建的各種驗證失敗情況"""
        client = self.authenticate_user(self.teacher_token)
        
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id
        })
        
        response = client.post(url, invalid_data, format='json')
        
        # 應該驗證失敗
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_student_cannot_create_editorial(self):
        """測試學生無法創建題解"""
        client = self.authenticate_user(self.student_token)
        
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id
        })
        data = {
            'title': '學生嘗試創建的題解',
            'content': '這是學生嘗試創建的題解內容',
            'difficulty_rating': 3.0,
            'is_official': False
        }
        
        response = client.post(url, data, format='json')
        
        # 應該權限不足
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert '沒有權限' in response.data['error']
    
    def test_other_course_teacher_cannot_create_editorial(self):
        """測試其他課程的老師無法創建題解"""
        client = self.authenticate_user(self.another_teacher_token)
        
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id  # 使用第一個課程的問題
        })
        data = {
            'title': '其他老師嘗試創建的題解',
            'content': '這是其他老師嘗試創建的題解內容',
            'difficulty_rating': 3.0,
            'is_official': False
        }
        
        response = client.post(url, data, format='json')
        
        # 應該權限不足
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert '沒有權限' in response.data['error']
    
    def test_ta_can_create_editorial(self):
        """測試 TA 可以創建題解"""
        client = self.authenticate_user(self.ta_token)
        
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id
        })
        data = {
            'title': 'TA 創建的題解',
            'content': '這是 TA 創建的題解內容，需要有足夠的長度',
            'difficulty_rating': 3.0,
            'is_official': False
        }
        
        response = client.post(url, data, format='json')
        
        # 應該成功創建
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'TA 創建的題解'
        assert response.data['author_username'] == self.ta_user.username
        
        # 驗證資料庫
        editorial = Editorial.objects.get(id=response.data['id'])
        assert editorial.author == self.ta_user
    
    def test_anyone_can_get_editorial_list(self):
        """測試任何認證用戶都可以獲取題解列表"""
        # 先創建一個題解
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='測試題解',
            content='這是測試題解的內容',
            difficulty_rating=3.5,
            status='published'
        )
        
        # 學生訪問
        client = self.authenticate_user(self.student_token)
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id
        })
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['title'] == '測試題解'
    
    def test_teacher_can_update_editorial(self):
        """測試老師可以更新題解"""
        # 創建題解
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='原始題解',
            content='原始內容',
            difficulty_rating=3.0,
            status='published'
        )
        
        client = self.authenticate_user(self.teacher_token)
        url = reverse('submissions:editorial-detail', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        data = {
            'title': '更新後的題解',
            'content': '更新後的內容，這裡有足夠的字元數',
            'difficulty_rating': 4.0
        }
        
        response = client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == '更新後的題解'
        
        # 驗證資料庫
        editorial.refresh_from_db()
        assert editorial.title == '更新後的題解'
        assert editorial.content == '更新後的內容，這裡有足夠的字元數'
    
    def test_ta_can_update_editorial(self):
        """測試 TA 可以更新題解"""
        # 先創建一個題解
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='原始題解',
            content='原始內容，有足夠的長度來滿足驗證要求',
            status='published'
        )
        
        client = self.authenticate_user(self.ta_token)
        url = reverse('submissions:editorial-detail', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        data = {
            'title': 'TA 更新的題解',
            'content': 'TA 更新的內容，這裡有足夠的字元數',
            'difficulty_rating': 4.0
        }
        
        response = client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'TA 更新的題解'
        
        # 驗證資料庫
        editorial.refresh_from_db()
        assert editorial.title == 'TA 更新的題解'
        assert editorial.content == 'TA 更新的內容，這裡有足夠的字元數'
    
    def test_student_cannot_update_editorial(self):
        """測試學生無法更新題解"""
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='原始題解',
            content='原始內容',
            status='published'
        )
        
        client = self.authenticate_user(self.student_token)
        url = reverse('submissions:editorial-detail', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        data = {
            'title': '學生嘗試更新',
            'content': '學生嘗試更新的內容'
        }
        
        response = client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_teacher_can_delete_editorial(self):
        """測試老師可以刪除題解"""
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='要被刪除的題解',
            content='要被刪除的內容',
            status='published'
        )
        
        client = self.authenticate_user(self.teacher_token)
        url = reverse('submissions:editorial-detail', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 驗證已刪除
        assert not Editorial.objects.filter(id=editorial.id).exists()
    
    def test_ta_can_delete_editorial(self):
        """測試 TA 可以刪除題解"""
        # 先創建一個題解
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='待刪除的題解',
            content='待刪除的內容，有足夠的長度來滿足驗證要求',
            status='published'
        )
        
        client = self.authenticate_user(self.ta_token)
        url = reverse('submissions:editorial-detail', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 驗證已刪除
        assert not Editorial.objects.filter(id=editorial.id).exists()
    
    def test_student_cannot_delete_editorial(self):
        """測試學生無法刪除題解"""
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='原始題解',
            content='原始內容',
            status='published'
        )
        
        client = self.authenticate_user(self.student_token)
        url = reverse('submissions:editorial-detail', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # 驗證未被刪除
        assert Editorial.objects.filter(id=editorial.id).exists()
    
    @given(
        like_count=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=5)
    def test_editorial_like_functionality(self, like_count):
        """測試題解按讚功能"""
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='測試按讚題解',
            content='測試按讚功能的內容',
            status='published',
            likes_count=like_count
        )
        
        client = self.authenticate_user(self.student_token)
        url = reverse('submissions:editorial-like-toggle', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        
        # 按讚
        response = client.post(url)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['is_liked'] == True
        assert response.data['likes_count'] == like_count + 1
        
        # 驗證資料庫
        assert EditorialLike.objects.filter(
            editorial=editorial,
            user=self.student
        ).exists()
        
        editorial.refresh_from_db()
        assert editorial.likes_count == like_count + 1
        
        # 取消按讚
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_liked'] == False
        assert response.data['likes_count'] == like_count
        
        # 驗證資料庫
        assert not EditorialLike.objects.filter(
            editorial=editorial,
            user=self.student
        ).exists()
    
    def test_duplicate_like_prevention(self):
        """測試防止重複按讚"""
        editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='測試重複按讚',
            content='測試重複按讚的內容',
            status='published'
        )
        
        # 先創建按讚記錄
        EditorialLike.objects.create(
            editorial=editorial,
            user=self.student
        )
        
        client = self.authenticate_user(self.student_token)
        url = reverse('submissions:editorial-like-toggle', kwargs={
            'problem_id': self.problem.id,
            'solution_id': editorial.id
        })
        
        # 嘗試重複按讚
        response = client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '已經對這篇題解按過讚了' in response.data['detail']
    
    def test_editorial_ordering(self):
        """測試題解排序（官方 > 按讚數 > 創建時間）"""
        # 創建不同類型的題解
        normal_editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='普通題解',
            content='普通題解內容',
            status='published',
            likes_count=5
        )
        
        official_editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='官方題解',
            content='官方題解內容',
            status='published',
            is_official=True,
            likes_count=3
        )
        
        popular_editorial = Editorial.objects.create(
            problem_id=self.problem.id,
            author=self.teacher,
            title='熱門題解',
            content='熱門題解內容',
            status='published',
            likes_count=10
        )
        
        client = self.authenticate_user(self.student_token)
        url = reverse('submissions:editorial-list-create', kwargs={
            'problem_id': self.problem.id
        })
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        
        # 檢查排序：官方題解 > 熱門題解 > 普通題解
        assert response.data[0]['title'] == '官方題解'
        assert response.data[1]['title'] == '熱門題解'
        assert response.data[2]['title'] == '普通題解'