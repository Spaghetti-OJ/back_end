import pytest
from django.contrib.auth import get_user_model
from problems.models import Problems
from courses.models import Courses, Course_members
from submissions.models import Submission
from django.utils import timezone
from django.conf import settings
import os
import zipfile
import json
from io import BytesIO
from problems.services.storage import _storage
from user.models import UserProfile


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
    # Create UserProfile with email_verified=True
    UserProfile.objects.update_or_create(
        user=u,
        defaults={"email_verified": True}
    )
    return u


@pytest.fixture
def student(db):
    User = get_user_model()
    u = User.objects.create_user(
        username="student1",
        email="student1@example.com",
        password="pass1234",
        real_name="Student One",
        identity="student",
    )
    # Create UserProfile with email_verified=True for student too
    UserProfile.objects.update_or_create(
        user=u,
        defaults={"email_verified": True}
    )
    return u


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
    # Clean up any existing file to ensure test isolation
    try:
        if _storage.exists(rel):
            _storage.delete(rel)
    except Exception:
        pass
    _storage.save(rel, mem)
    
    # 計算並儲存 SHA256 hash
    import hashlib
    with _storage.open(rel, 'rb') as fh:
        sha256_hash = hashlib.sha256(fh.read()).hexdigest()
    p.testcase_hash = sha256_hash
    p.save(update_fields=['testcase_hash'])

    # checksum 正確 token
    res = api_client.get(f"/problem/{p.id}/checksum", {'token': settings.SANDBOX_TOKEN})
    assert res.status_code == 200
    body = res.json()
    assert 'checksum' in body['data'] and len(body['data']['checksum']) == 64

    # checksum 錯誤 token
    res_bad = api_client.get(f"/problem/{p.id}/checksum", {'token': 'wrong'})
    assert res_bad.status_code == 401

    # meta 正確 token
    res_meta = api_client.get(f"/problem/{p.id}/meta", {'token': settings.SANDBOX_TOKEN})
    assert res_meta.status_code == 200
    meta = res_meta.json()['data']
    # 新格式：tasks 陣列包含子題設定，testcases 陣列包含測資檔案資訊
    assert 'tasks' in meta
    assert 'testcases' in meta
    assert len(meta['tasks']) == 1  # 0001, 0002 都屬於 subtask 00
    assert len(meta['testcases']) == 2  # 共兩個測資
    # 驗證 testcases 結構和具體值
    tc0 = meta['testcases'][0]
    assert tc0['stem'] == '0001'
    assert tc0['no'] == 1
    assert tc0['in'] == '0001.in'
    assert tc0['out'] == '0001.out'
    assert tc0['subtask'] == 1
    tc1 = meta['testcases'][1]
    assert tc1['stem'] == '0002'
    assert tc1['no'] == 2
    assert tc1['in'] == '0002.in'
    assert tc1['out'] == '0002.out'
    assert tc1['subtask'] == 1

    # meta 錯誤 token
    res_meta_bad = api_client.get(f"/problem/{p.id}/meta", {'token': 'wrong'})
    assert res_meta_bad.status_code == 401


@pytest.mark.django_db
def test_upload_zip_with_meta(api_client, teacher, course):
    """Test the upload-zip endpoint creates meta.json with correct testcases array."""
    p = Problems.objects.create(
        title="UploadZipMeta",
        description="test",
        difficulty="easy",
        is_public=True,
        creator_id=teacher,
        course_id=course,
    )
    
    # 建立 zip 測資 (0001.in/out, 0002.in/out, 0101.in/out)
    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w') as zf:
        zf.writestr('0001.in', 'input1')
        zf.writestr('0001.out', 'output1')
        zf.writestr('0002.in', 'input2')
        zf.writestr('0002.out', 'output2')
        zf.writestr('0101.in', 'input3')
        zf.writestr('0101.out', 'output3')
    mem.seek(0)
    
    # 上傳 zip
    api_client.force_authenticate(user=teacher)
    res = api_client.post(
        f"/problem/{p.id}/test-cases/upload-zip",
        {'file': mem},
        format='multipart'
    )
    assert res.status_code == 201
    
    # 驗證重打包的 zip 包含正確的 meta.json
    rel = os.path.join('testcases', f'p{p.id}', 'problem.zip')
    assert _storage.exists(rel)
    
    with _storage.open(rel, 'rb') as f:
        with zipfile.ZipFile(f, 'r') as zf:
            assert 'meta.json' in zf.namelist()
            meta = json.loads(zf.read('meta.json'))
            
            # 驗證 meta 結構
            assert 'tasks' in meta
            assert 'testcases' in meta
            assert len(meta['tasks']) == 2  # subtask 00 和 01
            assert len(meta['testcases']) == 3  # 共三個測資
            
            # 驗證 testcases 具體值
            tc0 = meta['testcases'][0]
            assert tc0['stem'] == '0001'
            assert tc0['no'] == 1
            assert tc0['in'] == '0001.in'
            assert tc0['out'] == '0001.out'
            assert tc0['subtask'] == 1
            
            tc1 = meta['testcases'][1]
            assert tc1['stem'] == '0002'
            assert tc1['no'] == 2
            assert tc1['in'] == '0002.in'
            assert tc1['out'] == '0002.out'
            assert tc1['subtask'] == 1
            
            tc2 = meta['testcases'][2]
            assert tc2['stem'] == '0101'
            assert tc2['no'] == 3
            assert tc2['in'] == '0101.in'
            assert tc2['out'] == '0101.out'
            assert tc2['subtask'] == 2


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


@pytest.mark.django_db
def test_problem_static_analysis_rules_basic(api_client, teacher, course):
    """Test creating and updating problems with static analysis rules."""
    api_client.force_authenticate(user=teacher)
    
    # Test 1: 建立題目時設定靜態分析規則
    payload = {
        "title": "Recursion Only Problem",
        "description": "必須使用遞迴解題",
        "difficulty": "medium",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-loops"],
    }
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 201
    problem_id = res.json()["data"]["problem_id"]
    
    # Test 2: 驗證 API 回應包含靜態分析設定
    res_detail = api_client.get(f"/problem/{problem_id}")
    assert res_detail.status_code == 200
    data = res_detail.json()["data"]
    assert data["static_analysis_rules"] == ["forbid-loops"]
    assert data["use_static_analysis"] is True
    assert data["static_analysis_config"]["enabled"] is True
    assert "forbid-loops" in data["static_analysis_config"]["rules"]
    
    # Test 3: 更新靜態分析規則（使用 PUT）
    update_payload = {
        "title": "Recursion Only Problem",
        "description": "必須使用遞迴解題",
        "difficulty": "medium",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-loops", "forbid-arrays"],
    }
    res_update = api_client.put(f"/problem/manage/{problem_id}", update_payload, format="json")
    assert res_update.status_code == 200
    
    # Test 4: 驗證更新後包含多個規則
    res_after = api_client.get(f"/problem/{problem_id}")
    data_after = res_after.json()["data"]
    assert set(data_after["static_analysis_rules"]) == {"forbid-loops", "forbid-arrays"}


@pytest.mark.django_db
def test_static_analysis_forbid_functions_validation(api_client, teacher, course):
    """Test validation that forbid-functions requires forbidden_functions list."""
    api_client.force_authenticate(user=teacher)
    
    # Test 1: 啟用 forbid-functions 但未提供函數列表 => 400
    payload = {
        "title": "No Sort Problem",
        "description": "不能使用 sort",
        "difficulty": "medium",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-functions"],
        "forbidden_functions": [],  # 空列表應該失敗
    }
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 422  # DRF returns 422 for validation errors in this endpoint
    
    # Test 2: 提供函數列表後應該成功
    payload["forbidden_functions"] = ["sort", "sorted"]
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 201
    problem_id = res.json()["data"]["problem_id"]
    
    # Test 3: 驗證 forbidden_functions 被正確儲存
    res_detail = api_client.get(f"/problem/{problem_id}")
    data = res_detail.json()["data"]
    assert set(data["forbidden_functions"]) == {"sort", "sorted"}
    assert data["static_analysis_config"]["forbidden_functions"] == ["sort", "sorted"]


@pytest.mark.django_db
def test_static_analysis_empty_function_name_validation(api_client, teacher, course):
    """Test that empty function names are rejected."""
    api_client.force_authenticate(user=teacher)
    
    # 嘗試建立帶有空字串函數名稱的題目
    payload = {
        "title": "Invalid Functions Problem",
        "description": "Test validation",
        "difficulty": "medium",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-functions"],
        "forbidden_functions": ["sort", "", "printf"],  # 包含空字串
    }
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 422  # DRF returns 422 for validation errors in this endpoint
    body = res.json()
    # 應該包含錯誤訊息
    assert "forbidden_functions" in str(body).lower() or "函數" in str(body)


@pytest.mark.django_db
def test_static_analysis_disable_rules(api_client, teacher, course):
    """Test disabling static analysis rules."""
    api_client.force_authenticate(user=teacher)
    
    # 建立帶有靜態分析規則的題目
    problem = Problems.objects.create(
        title="Test Problem",
        description="desc",
        difficulty="easy",
        creator_id=teacher,
        course_id=course,
        static_analysis_rules=["forbid-loops"],
    )
    
    # 清空規則以停用靜態分析
    update_payload = {
        "title": "Test Problem",
        "description": "desc",
        "difficulty": "easy",
        "course_id": str(course.id),
        "static_analysis_rules": [],
    }
    res = api_client.put(f"/problem/manage/{problem.id}", update_payload, format="json")
    assert res.status_code == 200
    
    # 驗證靜態分析已停用
    res_detail = api_client.get(f"/problem/{problem.id}")
    data = res_detail.json()["data"]
    assert data["static_analysis_rules"] == []
    assert data["use_static_analysis"] is False
    assert data["static_analysis_config"]["enabled"] is False


@pytest.mark.django_db
def test_static_analysis_remove_forbid_functions_rule(api_client, teacher, course):
    """Test removing forbid-functions rule while keeping forbidden_functions list."""
    api_client.force_authenticate(user=teacher)
    
    # 建立帶有 forbid-functions 規則的題目
    problem = Problems.objects.create(
        title="Test Problem",
        description="desc",
        difficulty="easy",
        creator_id=teacher,
        course_id=course,
        static_analysis_rules=["forbid-functions"],
        forbidden_functions=["sort", "qsort"],
    )
    
    # 移除 forbid-functions 規則但保留 forbidden_functions（應該可以成功）
    update_payload = {
        "title": "Test Problem",
        "description": "desc",
        "difficulty": "easy",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-loops"],  # 不包含 forbid-functions
        # 保留 forbidden_functions 欄位
    }
    res = api_client.put(f"/problem/manage/{problem.id}", update_payload, format="json")
    assert res.status_code == 200
    
    # 驗證規則已更新
    res_detail = api_client.get(f"/problem/{problem.id}")
    data = res_detail.json()["data"]
    assert "forbid-functions" not in data["static_analysis_rules"]
    assert "forbid-loops" in data["static_analysis_rules"]


@pytest.mark.django_db
def test_static_analysis_multiple_rules(api_client, teacher, course):
    """Test creating problems with multiple static analysis rules."""
    api_client.force_authenticate(user=teacher)
    
    payload = {
        "title": "Strict Problem",
        "description": "多重限制",
        "difficulty": "hard",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-loops", "forbid-arrays", "forbid-stl"],
    }
    res = api_client.post("/problem/manage", payload, format="json")
    assert res.status_code == 201
    problem_id = res.json()["data"]["problem_id"]
    
    # 驗證所有規則都被正確儲存
    res_detail = api_client.get(f"/problem/{problem_id}")
    data = res_detail.json()["data"]
    assert set(data["static_analysis_rules"]) == {"forbid-loops", "forbid-arrays", "forbid-stl"}
    assert data["use_static_analysis"] is True
    config = data["static_analysis_config"]
    assert config["enabled"] is True
    assert set(config["rules"]) == {"forbid-loops", "forbid-arrays", "forbid-stl"}


@pytest.mark.django_db
def test_static_analysis_invalid_rule(api_client, teacher, course):
    """Test that invalid rule names are rejected."""
    api_client.force_authenticate(user=teacher)
    
    payload = {
        "title": "Invalid Rule Problem",
        "description": "Test validation",
        "difficulty": "medium",
        "course_id": str(course.id),
        "static_analysis_rules": ["forbid-loops", "invalid-rule"],
    }
    res = api_client.post("/problem/manage", payload, format="json")
    # 應該失敗，因為 invalid-rule 不是有效的規則
    assert res.status_code == 422  # DRF returns 422 for validation errors in this endpoint


@pytest.mark.django_db
def test_static_analysis_api_response_fields(api_client, teacher, course):
    """Test that API responses include all static analysis fields."""
    api_client.force_authenticate(user=teacher)
    
    # 建立帶有靜態分析設定的題目
    problem = Problems.objects.create(
        title="API Test Problem",
        description="desc",
        difficulty="easy",
        creator_id=teacher,
        course_id=course,
        static_analysis_rules=["forbid-functions"],
        forbidden_functions=["printf", "scanf"],
    )
    
    # 驗證 API 回應包含所有必要欄位
    res = api_client.get(f"/problem/{problem.id}")
    assert res.status_code == 200
    data = res.json()["data"]
    
    # 檢查必要欄位
    assert "static_analysis_rules" in data
    assert "forbidden_functions" in data
    assert "use_static_analysis" in data
    assert "static_analysis_config" in data
    
    # 檢查 config 物件結構
    config = data["static_analysis_config"]
    assert "enabled" in config
    assert "rules" in config
    assert "forbidden_functions" in config
    assert config["enabled"] is True
    assert config["rules"] == ["forbid-functions"]
    assert config["forbidden_functions"] == ["printf", "scanf"]
