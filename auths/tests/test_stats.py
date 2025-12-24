from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from submissions.models import Submission

User = get_user_model()

class UserSubmissionActivityViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.other_user = User.objects.create_user(username='otheruser', email='other@example.com', password='password')
        
        # URL
        self.url_name = 'user-submission-activity'
        
        # Create some submissions in different dates
        today = timezone.now()
        yesterday = today - timedelta(days=1)
        # two_days_ago = today - timedelta(days=2)
        one_year_ago = today - timedelta(days=364)
        too_old = today - timedelta(days=366)

        # Helper to create and date submission
        def create_dated_submission(user, date):
            s = Submission.objects.create(
                user=user, 
                problem_id=1, 
                language_type=0, 
                source_code='code'
            )
            # Update created_at carefully to ensure db sees it
            Submission.objects.filter(id=s.id).update(created_at=date)

        create_dated_submission(self.user, today)
        create_dated_submission(self.user, yesterday)
        create_dated_submission(self.user, yesterday) # 2 yesterday
        create_dated_submission(self.user, one_year_ago)
        create_dated_submission(self.user, too_old)
        
        create_dated_submission(self.other_user, today)

    def test_get_submission_activity_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse(self.url_name, args=[self.user.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        
        today_str = timezone.now().strftime('%Y-%m-%d')
        yesterday_str = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        one_year_ago_str = (timezone.now() - timedelta(days=364)).strftime('%Y-%m-%d')
        
        self.assertEqual(data.get(today_str), 1)
        self.assertEqual(data.get(yesterday_str), 2)
        self.assertEqual(data.get(one_year_ago_str), 1)
        
        # Too old should not be there (or effectively 0/not in dict if sparse)
        too_old_str = (timezone.now() - timedelta(days=366)).strftime('%Y-%m-%d')
        self.assertNotIn(too_old_str, data)

    def test_get_other_user_activity(self):
        self.client.force_authenticate(user=self.user)
        url = reverse(self.url_name, args=[self.other_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        today_str = timezone.now().strftime('%Y-%m-%d')
        self.assertEqual(response.data['data'].get(today_str), 1)

    def test_unauthenticated(self):
        url = reverse(self.url_name, args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
