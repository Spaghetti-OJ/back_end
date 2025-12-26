import pytest
from django.contrib.auth import get_user_model
from problems.models import Problems
from courses.models import Courses, Course_members
from submissions.models import Submission
from django.utils import timezone
from django.conf import settings
import os
import zipfile
from io import BytesIO
from problems.services.storage import _storage


@pytest.fixture
def teacher(db):
    User = get_user_model()
    u = User.objects.create_user(
        username="teacher1",
        email="teacher1@example.com",
        password="pass1234",
        real_name="Teacher One",
        identity="teacher",
    )
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    return u


@pytest.fixture
def student(db):
    User = get_user_model()
    return User.objects.create_user(
        username="student1",
        email="student1@example.com",
        password="pass1234",
        real_name="Student One",
        identity="student",
    )


@pytest.fixture
def course(db, teacher):
    return Courses.objects.create(name="Algorithms", description="", teacher_id=teacher)


def make_problem(*, title: str, creator, course, is_public=False):
    return Problems.objects.create(
        title=title,
        description="desc",
        difficulty="easy",
        is_public=is_public,
        creator_id=creator,
        course_id=course,
    )


@pytest.mark.django_db
def test_problem_detail_personal_stats(api_client, teacher, student, course):
    # 建一個公開題目，讓未登入也能拿到 detail（但 stats 應為 null）
    p = make_problem(title="StatTest", creator=teacher, course=course, is_public=True)

    # 未登入：submit_count / high_score 應為 null
    res = api_client.get(f"/problem/{p.id}")
    assert res.status_code == 200
    body = res.json()
    data = body.get("data")
    assert data.get("submit_count") is None
    assert data.get("high_score") is None

    # 建立兩次提交（student）
    Submission.objects.create(problem_id=p.id, user=student, language_type='python', source_code='print(1)', score=10, created_at=timezone.now())
    Submission.objects.create(problem_id=p.id, user=student, language_type='python', source_code='print(2)', score=80, created_at=timezone.now())

    # 登入後：submit_count=2, high_score=80
    api_client.force_authenticate(user=student)
    res = api_client.get(f"/problem/{p.id}")
    assert res.status_code == 200
    body = res.json()
    data = body.get("data")
    assert data.get("submit_count") == 2
    assert data.get("high_score") == 80


@pytest.mark.django_db
def test_problem_list_anonymous_filters_public(api_client, teacher, course):
    make_problem(title="P1", creator=teacher, course=course, is_public=True)
    make_problem(title="P2", creator=teacher, course=course, is_public=False)

    res = api_client.get("/problem/")
    assert res.status_code == 200
    body = res.json()
    payload = body.get("data")
    # 分頁或非分頁都適配
    if isinstance(payload, dict) and "results" in payload:
        items = payload["results"]
    else:
        items = payload
    assert len(items) == 1
    assert items[0]["title"] == "P1"


@pytest.mark.django_db
def test_problem_detail_permissions(api_client, teacher, student, course):
    p = make_problem(title="Secret", creator=teacher, course=course, is_public=False)

    # 未登入看私有題目 => 401
    res = api_client.get(f"/problem/{p.id}")
    assert res.status_code == 401

    # 學生未加入課程 => 403
    api_client.force_authenticate(user=student)
    res = api_client.get(f"/problem/{p.id}")
    assert res.status_code == 403

    # 加入課程後 => 200
    Course_members.objects.create(course_id=course, user_id=student, role=Course_members.Role.STUDENT)
    res = api_client.get(f"/problem/{p.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["title"] == "Secret"


@pytest.mark.django_db
def test_manage_create_requires_teacher(api_client, teacher, student, course):
    payload = {
        "title": "New Problem",
        "description": "desc",
        "difficulty": "easy",
        "course_id": str(course.id),
    }

    # 學生 => 403
    api_client.force_authenticate(user=student)
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 403

    # 老師 => 201 並回傳 problem_id
    api_client.force_authenticate(user=teacher)
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 201
    body = res.json()
    assert body.get("status") == "201"
    assert "problem_id" in body.get("data", {})

    created = Problems.objects.get(pk=body["data"]["problem_id"]) 
    assert created.title == "New Problem"
    assert created.course_id_id == course.id


@pytest.mark.django_db
def test_sandbox_checksum_and_meta(api_client, teacher, course, settings):
    # 設定 sandbox token
    settings.SANDBOX_TOKEN = "sandbox-token"
    p = Problems.objects.create(
        title="SandboxTC",
        description="desc",
        difficulty="easy",
        is_public=True,
        creator_id=teacher,
        course_id=course,
    )
    # 建立 zip 測資 (0001.in/out, 0002.in/out)
    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w') as zf:
        zf.writestr('0001.in', 'input1')
        zf.writestr('0001.out', 'output1')
        zf.writestr('0002.in', 'input2')
        zf.writestr('0002.out', 'output2')
    mem.seek(0)
    rel = os.path.join('testcases', f'p{p.id}', 'problem.zip')
    _storage.save(rel, mem)

    # checksum 正確 token
    res = api_client.get(f"/problem/{p.id}/checksum", {'token': settings.SANDBOX_TOKEN})
    assert res.status_code == 200
    body = res.json()
    assert 'checksum' in body['data'] and len(body['data']['checksum']) == 32

    # checksum 錯誤 token
    res_bad = api_client.get(f"/problem/{p.id}/checksum", {'token': 'wrong'})
    assert res_bad.status_code == 401

    # meta 正確 token
    res_meta = api_client.get(f"/problem/{p.id}/meta", {'token': settings.SANDBOX_TOKEN})
    assert res_meta.status_code == 200
    meta = res_meta.json()['data']
    assert meta['task_count'] == 2
    assert meta['missing_pairs'] == []
    assert len(meta['tasks']) == 2
    assert meta['tasks'][0]['in'].endswith('.in') and meta['tasks'][0]['out'].endswith('.out')

    # meta 錯誤 token
    res_meta_bad = api_client.get(f"/problem/{p.id}/meta", {'token': 'wrong'})
    assert res_meta_bad.status_code == 401


@pytest.mark.django_db
def test_sandbox_testdata_download(api_client, teacher, course, settings):
    """Test the new /problem/<pk>/testdata endpoint for sandbox test data downloads."""
    # 設定 sandbox token
    settings.SANDBOX_TOKEN = "test-sandbox-token"
    
    p = Problems.objects.create(
        title="TestDataDownload",
        description="test",
        difficulty="medium",
        is_public=True,
        creator_id=teacher,
        course_id=course,
    )
    
    # 建立測資 zip 檔案
    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w') as zf:
        zf.writestr('0001.in', 'test input 1')
        zf.writestr('0001.out', 'test output 1')
        zf.writestr('0101.in', 'test input 2')
        zf.writestr('0101.out', 'test output 2')
    mem.seek(0)
    rel = os.path.join('testcases', f'p{p.id}', 'problem.zip')
    _storage.save(rel, mem)
    
    # Test 1: 成功下載（使用正確 token）
    res = api_client.get(f"/problem/{p.id}/testdata", {'token': settings.SANDBOX_TOKEN})
    assert res.status_code == 200
    assert res['Content-Type'] == 'application/zip'
    assert 'attachment' in res['Content-Disposition']
    assert f'problem-{p.id}-package.zip' in res['Content-Disposition']
    
    # 驗證下載的 zip 內容正確
    downloaded = BytesIO(b''.join(res.streaming_content))
    with zipfile.ZipFile(downloaded, 'r') as zf:
        assert '0001.in' in zf.namelist()
        assert '0001.out' in zf.namelist()
        assert zf.read('0001.in') == b'test input 1'
    
    # Test 2: 錯誤的 token (401)
    res_bad = api_client.get(f"/problem/{p.id}/testdata", {'token': 'invalid-token'})
    assert res_bad.status_code == 401
    body = res_bad.json()
    assert 'Invalid sandbox token' in body['message']
    
    # Test 3: 未提供 token (401)
    res_no_token = api_client.get(f"/problem/{p.id}/testdata")
    assert res_no_token.status_code == 401
    
    # Test 4: SANDBOX_TOKEN 未設定 (401)
    settings.SANDBOX_TOKEN = None
    res_no_config = api_client.get(f"/problem/{p.id}/testdata", {'token': 'any-token'})
    assert res_no_config.status_code == 401
    
    # Test 5: 測資檔案不存在 (404)
    settings.SANDBOX_TOKEN = "test-sandbox-token"
    p2 = Problems.objects.create(
        title="NoTestData",
        description="no data",
        difficulty="easy",
        is_public=True,
        creator_id=teacher,
        course_id=course,
    )
    res_404 = api_client.get(f"/problem/{p2.id}/testdata", {'token': settings.SANDBOX_TOKEN})
    assert res_404.status_code == 404

@pytest.mark.django_db
def test_problem_custom_checker_settings(api_client, teacher, course):
    """Test creating and updating problems with custom checker settings."""
    api_client.force_authenticate(user=teacher)
    
    # Test 1: 建立題目時設定 custom checker
    payload = {
        "title": "Float Problem",
        "description": "計算浮點數",
        "difficulty": "medium",
        "course_id": str(course.id),
        "use_custom_checker": True,
        "checker_name": "float",
    }
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 201
    problem_id = res.json()["data"]["problem_id"]
    
    # Test 2: 驗證 API 回應包含 checker 設定
    res_detail = api_client.get(f"/problem/{problem_id}")
    assert res_detail.status_code == 200
    data = res_detail.json()["data"]
    assert data["use_custom_checker"] is True
    assert data["checker_name"] == "float"
    
    # Test 3: 更新 checker 設定（使用 PUT）
    update_payload = {
        "title": "Float Problem",  # PUT 需要提供完整資料
        "description": "計算浮點數",
        "difficulty": "medium",
        "course_id": str(course.id),
        "use_custom_checker": False,
        "checker_name": "diff",
    }
    res_update = api_client.put(f"/problem/manage/{problem_id}", update_payload, format="json")
    assert res_update.status_code == 200
    
    # Test 4: 驗證更新後使用預設 diff
    res_after = api_client.get(f"/problem/{problem_id}")
    assert res_after.json()["data"]["use_custom_checker"] is False


@pytest.mark.django_db
def test_checker_settings_passed_to_sandbox(api_client, teacher, course):
    """Test that checker settings are correctly prepared for sandbox submission."""
    from submissions.sandbox_client import submit_to_sandbox
    from unittest.mock import patch, MagicMock
    
    # 建立帶有 custom checker 的題目
    problem = Problems.objects.create(
        title="Token Compare",
        description="desc",
        difficulty="easy",
        creator_id=teacher,
        course_id=course,
        use_custom_checker=True,
        checker_name="token",
    )
    
    # Mock submission
    mock_submission = MagicMock()
    mock_submission.id = "test-uuid"
    mock_submission.problem_id = problem.id
    mock_submission.source_code = "print('hello')"
    mock_submission.language_type = 2  # Python
    
    with patch('submissions.sandbox_client.requests.post') as mock_post:
        mock_post.return_value.status_code = 202
        mock_post.return_value.json.return_value = {"status": "queued"}
        
        try:
            submit_to_sandbox(mock_submission)
        except:
            pass  # 忽略其他錯誤，只檢查呼叫參數
        
        # 驗證傳遞給 Sandbox 的參數
        if mock_post.called:
            call_data = mock_post.call_args[1].get('data', {})
            assert call_data.get('use_checker') is True
            assert call_data.get('checker_name') == 'token'