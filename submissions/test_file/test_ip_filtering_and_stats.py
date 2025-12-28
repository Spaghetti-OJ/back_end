# submissions/test_file/test_ip_filtering_and_stats.py
"""
Tests for IP filtering functionality and user problem stats updates
"""

import pytest
import uuid
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, Mock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from ..models import Submission, UserProblemSolveStatus
from ..views import update_user_problem_stats
from problems.models import Problems
from courses.models import Courses

User = get_user_model()


@pytest.mark.django_db
class TestIPFilteringAPI(APITestCase):
    """Test IP filtering functionality in submission list API"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for IP filtering tests"""
        from user.models import UserProfile
        
        # Create test user
        cls.user = User.objects.create_user(
            username='ip_test_user',
            email='ip_test@test.com',
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=cls.user)
        profile.email_verified = True
        profile.save()
        
        # Create test problem
        cls.course = Courses.objects.create(
            course_name='Test Course',
            year=2024,
            semester=1,
            teacher_id=cls.user.id
        )
        
        cls.problem = Problems.objects.create(
            problem_name='Test Problem',
            time_limit=1000,
            memory_limit=256000,
            course_id=cls.course.id
        )
        
        # Create submissions with different IPs
        cls.submission1 = Submission.objects.create(
            user=cls.user,
            problem_id=cls.problem.id,
            language_type=1,
            source_code='print("test")',
            ip_address='192.168.1.10',
            status='-1',
            score=0
        )
        
        cls.submission2 = Submission.objects.create(
            user=cls.user,
            problem_id=cls.problem.id,
            language_type=1,
            source_code='print("test2")',
            ip_address='192.168.1.20',
            status='-1',
            score=0
        )
        
        cls.submission3 = Submission.objects.create(
            user=cls.user,
            problem_id=cls.problem.id,
            language_type=1,
            source_code='print("test3")',
            ip_address='192.168.2.10',
            status='-1',
            score=0
        )
        
        cls.submission4 = Submission.objects.create(
            user=cls.user,
            problem_id=cls.problem.id,
            language_type=1,
            source_code='print("test4")',
            ip_address='10.0.0.5',
            status='-1',
            score=0
        )
    
    def setUp(self):
        """Set up for each test"""
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_simple_prefix_filtering(self):
        """Test simple IP prefix filtering (e.g., '192.168.1.')"""
        response = self.client.get('/submission/', {'ip_prefix': '192.168.1.'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only return submissions with IPs starting with 192.168.1.
        submission_ids = [item['id'] for item in data['data']]
        self.assertIn(str(self.submission1.id), submission_ids)
        self.assertIn(str(self.submission2.id), submission_ids)
        self.assertNotIn(str(self.submission3.id), submission_ids)
        self.assertNotIn(str(self.submission4.id), submission_ids)
    
    def test_cidr_filtering(self):
        """Test CIDR notation IP filtering (e.g., '192.168.1.0/24')"""
        response = self.client.get('/submission/', {'ip_prefix': '192.168.1.0/24'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return submissions in the 192.168.1.0/24 range
        submission_ids = [item['id'] for item in data['data']]
        self.assertIn(str(self.submission1.id), submission_ids)
        self.assertIn(str(self.submission2.id), submission_ids)
        self.assertNotIn(str(self.submission3.id), submission_ids)
        self.assertNotIn(str(self.submission4.id), submission_ids)
    
    def test_cidr_filtering_larger_network(self):
        """Test CIDR filtering with larger network (e.g., '192.168.0.0/16')"""
        response = self.client.get('/submission/', {'ip_prefix': '192.168.0.0/16'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return all submissions in the 192.168.0.0/16 range
        submission_ids = [item['id'] for item in data['data']]
        self.assertIn(str(self.submission1.id), submission_ids)
        self.assertIn(str(self.submission2.id), submission_ids)
        self.assertIn(str(self.submission3.id), submission_ids)
        self.assertNotIn(str(self.submission4.id), submission_ids)
    
    def test_invalid_ip_prefix_returns_error(self):
        """Test that invalid IP prefix returns validation error"""
        response = self.client.get('/submission/', {'ip_prefix': 'invalid_ip'})
        
        # Should return 400 Bad Request with validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('ip_prefix', str(data))
    
    def test_invalid_cidr_returns_error(self):
        """Test that invalid CIDR notation returns validation error"""
        response = self.client.get('/submission/', {'ip_prefix': '192.168.1.0/99'})
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_no_ip_prefix_returns_all(self):
        """Test that without ip_prefix parameter, all submissions are returned"""
        response = self.client.get('/submission/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return all submissions
        submission_ids = [item['id'] for item in data['data']]
        self.assertIn(str(self.submission1.id), submission_ids)
        self.assertIn(str(self.submission2.id), submission_ids)
        self.assertIn(str(self.submission3.id), submission_ids)
        self.assertIn(str(self.submission4.id), submission_ids)


@pytest.mark.django_db
class TestUserProblemStatsUpdate(TestCase):
    """Test update_user_problem_stats function"""
    
    def setUp(self):
        """Set up test data"""
        from user.models import UserProfile
        
        # Create test user
        self.user = User.objects.create_user(
            username='stats_test_user',
            email='stats_test@test.com',
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.email_verified = True
        profile.save()
        
        # Create test problem
        self.course = Courses.objects.create(
            course_name='Test Course',
            year=2024,
            semester=1,
            teacher_id=self.user.id
        )
        
        self.problem = Problems.objects.create(
            problem_name='Test Problem',
            time_limit=1000,
            memory_limit=256000,
            course_id=self.course.id
        )
    
    def test_first_submission_creates_stats(self):
        """Test that first submission creates UserProblemSolveStatus"""
        submission = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test")',
            ip_address='127.0.0.1',
            status='1',  # WA
            score=0,
            execution_time=100,
            memory_usage=1024
        )
        
        update_user_problem_stats(submission)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        
        self.assertEqual(stats.total_submissions, 1)
        self.assertEqual(stats.ac_submissions, 0)
        self.assertEqual(stats.best_score, 0)
        self.assertEqual(stats.solve_status, 'attempted')
        self.assertIsNone(stats.first_solve_time)
    
    def test_ac_submission_updates_stats(self):
        """Test that AC submission updates stats correctly"""
        submission = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test")',
            ip_address='127.0.0.1',
            status='0',  # AC
            score=100,
            execution_time=100,
            memory_usage=1024,
            judged_at=datetime.now(dt_timezone.utc)
        )
        
        update_user_problem_stats(submission)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        
        self.assertEqual(stats.total_submissions, 1)
        self.assertEqual(stats.ac_submissions, 1)
        self.assertEqual(stats.best_score, 100)
        self.assertEqual(stats.solve_status, 'fully_solved')
        self.assertIsNotNone(stats.first_solve_time)
    
    def test_partial_score_updates_status(self):
        """Test that partial score updates solve status to 'partial_solved'"""
        submission = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test")',
            ip_address='127.0.0.1',
            status='1',  # WA
            score=50,
            execution_time=100,
            memory_usage=1024
        )
        
        update_user_problem_stats(submission)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        
        self.assertEqual(stats.best_score, 50)
        self.assertEqual(stats.solve_status, 'partial_solved')
    
    def test_multiple_submissions_update_correctly(self):
        """Test that multiple submissions update stats correctly"""
        # First submission - low score
        submission1 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test1")',
            ip_address='127.0.0.1',
            status='1',  # WA
            score=30,
            execution_time=150,
            memory_usage=2048
        )
        update_user_problem_stats(submission1)
        
        # Second submission - higher score
        submission2 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test2")',
            ip_address='127.0.0.1',
            status='1',  # WA
            score=70,
            execution_time=100,
            memory_usage=1024
        )
        update_user_problem_stats(submission2)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        
        self.assertEqual(stats.total_submissions, 2)
        self.assertEqual(stats.best_score, 70)
        self.assertEqual(stats.best_execution_time, 100)
        self.assertEqual(stats.best_memory_usage, 1024)
        self.assertEqual(stats.solve_status, 'partial_solved')
    
    def test_best_execution_time_updated(self):
        """Test that best execution time is tracked correctly"""
        submission1 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test1")',
            ip_address='127.0.0.1',
            status='0',  # AC
            score=100,
            execution_time=200,
            memory_usage=1024
        )
        update_user_problem_stats(submission1)
        
        submission2 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test2")',
            ip_address='127.0.0.1',
            status='0',  # AC
            score=100,
            execution_time=100,
            memory_usage=1024
        )
        update_user_problem_stats(submission2)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        
        self.assertEqual(stats.best_execution_time, 100)
    
    def test_invalid_execution_time_ignored(self):
        """Test that invalid (zero or negative) execution times are ignored"""
        submission = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test")',
            ip_address='127.0.0.1',
            status='0',  # AC
            score=100,
            execution_time=0,  # Invalid
            memory_usage=1024
        )
        
        update_user_problem_stats(submission)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        
        # execution_time should not be updated since it's 0
        self.assertIsNone(stats.best_execution_time)
    
    def test_solve_status_transitions(self):
        """Test that solve status transitions correctly"""
        # Start with attempted
        submission1 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test")',
            ip_address='127.0.0.1',
            status='1',  # WA
            score=0,
            execution_time=100,
            memory_usage=1024
        )
        update_user_problem_stats(submission1)
        
        stats = UserProblemSolveStatus.objects.get(
            user=self.user,
            problem_id=self.problem.id
        )
        self.assertEqual(stats.solve_status, 'attempted')
        
        # Move to partial_solved
        submission2 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test2")',
            ip_address='127.0.0.1',
            status='1',  # WA
            score=50,
            execution_time=100,
            memory_usage=1024
        )
        update_user_problem_stats(submission2)
        
        stats.refresh_from_db()
        self.assertEqual(stats.solve_status, 'partial_solved')
        
        # Move to fully_solved
        submission3 = Submission.objects.create(
            user=self.user,
            problem_id=self.problem.id,
            language_type=1,
            source_code='print("test3")',
            ip_address='127.0.0.1',
            status='0',  # AC
            score=100,
            execution_time=100,
            memory_usage=1024
        )
        update_user_problem_stats(submission3)
        
        stats.refresh_from_db()
        self.assertEqual(stats.solve_status, 'fully_solved')
