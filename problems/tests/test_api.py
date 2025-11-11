import pytest
from django.contrib.auth import get_user_model
from problems.models import Problems
from courses.models import Courses, Course_members
from submissions.models import Submission
from django.utils import timezone


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
    assert body.get("submit_count") is None
    assert body.get("high_score") is None

    # 建立兩次提交（student）
    Submission.objects.create(problem_id=p.id, user=student, language_type='python', source_code='print(1)', score=10, created_at=timezone.now())
    Submission.objects.create(problem_id=p.id, user=student, language_type='python', source_code='print(2)', score=80, created_at=timezone.now())

    # 登入後：submit_count=2, high_score=80
    api_client.force_authenticate(user=student)
    res = api_client.get(f"/problem/{p.id}")
    assert res.status_code == 200
    body = res.json()
    assert body.get("submit_count") == 2
    assert body.get("high_score") == 80


@pytest.mark.django_db
def test_problem_list_anonymous_filters_public(api_client, teacher, course):
    make_problem(title="P1", creator=teacher, course=course, is_public=True)
    make_problem(title="P2", creator=teacher, course=course, is_public=False)

    res = api_client.get("/problem/")
    assert res.status_code == 200
    data = res.json()
    # 若之後加上分頁，這裡可適配 'results'
    if isinstance(data, dict) and "results" in data:
        items = data["results"]
    else:
        items = data
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
    assert body["title"] == "Secret"


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
    assert body.get("success") is True
    assert "problem_id" in body

    created = Problems.objects.get(pk=body["problem_id"])
    assert created.title == "New Problem"
    assert created.course_id_id == course.id
