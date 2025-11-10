# conftest.py - pytest 和 Hypothesis 全域設定
import pytest
import os
import django
from django.conf import settings
from django.test.utils import get_runner
from hypothesis import settings as hypothesis_settings, Verbosity

# 設定 Django 環境
def pytest_configure(config):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'back_end.settings')
    django.setup()

# Hypothesis 設定
hypothesis_settings.register_profile("ci", max_examples=1000)
hypothesis_settings.register_profile("dev", max_examples=100)
hypothesis_settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)

# 根據環境變數選擇設定檔
profile_name = os.getenv("HYPOTHESIS_PROFILE", "dev")
hypothesis_settings.load_profile(profile_name)

@pytest.fixture
def api_client():
    """提供 Django REST framework 測試客戶端"""
    from rest_framework.test import APIClient
    return APIClient()
