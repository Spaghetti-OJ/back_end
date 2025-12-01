import csv
import io
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import generics, permissions, status, parsers
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response

from ..common.responses import api_response
from ..models import Batch_imports, Course_members
from ..serializers import CourseImportCSVSerializer
from .course_courseid import CourseDetailView
from user.models import UserProfile

User = get_user_model()


class CourseImportCSVView(generics.GenericAPIView):
    """
    CSV 批次匯入學生：
     - POST /course/<course_id>/import-csv
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseImportCSVSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    REQUIRED_HEADERS = {"username", "email", "real_name"}

    def post(self, request, course_id, *args, **kwargs):
        course = CourseDetailView._get_course_or_response(course_id)
        if isinstance(course, Response):
            return course

        permission_error = self._check_permission(request.user, course)
        if permission_error is not None:
            return permission_error

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            detail = self._extract_error_detail(serializer.errors)
            message = str(detail) if detail else "Invalid data."
            return api_response(message=message, status_code=status.HTTP_400_BAD_REQUEST)

        current_student_count = Course_members.objects.filter(
            course_id=course,
            role=Course_members.Role.STUDENT,
        ).count()
        if course.student_limit is not None and current_student_count >= course.student_limit:
            return api_response(
                message="Course is full.", status_code=status.HTTP_403_FORBIDDEN
            )

        upload = serializer.validated_data["file"]
        file_bytes = upload.read()
        if not file_bytes:
            return api_response(
                message="File is empty.", status_code=status.HTTP_400_BAD_REQUEST
            )

        batch = self._create_batch_record(
            course=course,
            user=request.user,
            original_name=getattr(upload, "name", "students.csv"),
            file_bytes=file_bytes,
        )

        try:
            import_result = self._import_students(
                file_bytes=file_bytes,
                course=course,
                remaining_slots=self._remaining_slots(course, current_student_count),
            )
        except ValueError as exc:
            self._mark_batch_failed(batch, [{"message": str(exc)}])
            return api_response(
                message=str(exc), status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            self._mark_batch_failed(batch, [{"message": "Unexpected error during import."}])
            raise

        self._mark_batch_completed(batch, import_result["errors"])

        response_payload = {
            "import": {
                "id": str(batch.id),
                "status": batch.status,
                "fileName": batch.file_name,
                "fileSize": batch.file_size,
                "importResult": batch.import_result,
                "createdUsers": import_result["created_users"],
                "newMembers": import_result["new_members"],
                "skippedExistingMembers": import_result["skipped_members"],
                "errorCount": len(import_result["errors"]),
                "errors": import_result["errors"],
            }
        }

        return api_response(
            data=response_payload,
            message="Success.",
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def _check_permission(user, course):
        identity = getattr(user, "identity", None)
        if identity not in (User.Identity.TEACHER, User.Identity.ADMIN):
            return api_response(
                message="Forbidden.", status_code=status.HTTP_403_FORBIDDEN
            )
        if identity == User.Identity.TEACHER and course.teacher_id_id != getattr(user, "id", None):
            return api_response(
                message="You are not in this course.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return None

    @classmethod
    def _extract_error_detail(cls, errors):
        if isinstance(errors, dict):
            for value in errors.values():
                detail = cls._extract_error_detail(value)
                if detail is not None:
                    return detail
        elif isinstance(errors, list):
            for item in errors:
                detail = cls._extract_error_detail(item)
                if detail is not None:
                    return detail
        elif isinstance(errors, ErrorDetail):
            return errors
        return None

    @staticmethod
    def _remaining_slots(course, current_student_count):
        if course.student_limit is None:
            return None
        return max(course.student_limit - current_student_count, 0)

    def _create_batch_record(self, *, course, user, original_name, file_bytes):
        storage_path = self._save_csv(file_bytes, original_name)
        return Batch_imports.objects.create(
            course_id=course,
            imported_by=user,
            file_name=Path(original_name).name,
            csv_path=storage_path,
            file_size=len(file_bytes),
            status=Batch_imports.Status.PROCESSING,
        )

    @staticmethod
    def _save_csv(file_bytes, original_name):
        safe_name = Path(original_name or "students.csv").name
        unique_name = f"{uuid.uuid4()}_{safe_name}"
        return default_storage.save(
            f"batch_imports/{unique_name}",
            ContentFile(file_bytes),
        )

    def _import_students(self, *, file_bytes, course, remaining_slots):
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("CSV must be UTF-8 encoded.")

        reader = csv.DictReader(io.StringIO(text))
        normalized_headers = {self._normalize_key(h) for h in (reader.fieldnames or [])}
        missing = sorted(self.REQUIRED_HEADERS - normalized_headers)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}.")

        seen_usernames = set()
        seen_emails = set()

        created_users = 0
        new_members = 0
        skipped_members = 0
        errors = []

        for idx, raw_row in enumerate(reader, start=2):  # header is row 1
            row = {self._normalize_key(k): (v if v is not None else "") for k, v in raw_row.items()}
            username = self._clean(row.get("username"))
            email = self._clean(row.get("email")).lower()
            real_name = self._clean(row.get("real_name"))
            student_id = self._clean(row.get("student_id"))
            password = self._clean(row.get("password"))

            if not username or not email or not real_name:
                errors.append({"row": idx, "message": "username, email, and real_name are required."})
                continue

            if username.lower() in seen_usernames:
                errors.append({"row": idx, "message": f"Duplicate username in file: {username}."})
                continue
            if email in seen_emails:
                errors.append({"row": idx, "message": f"Duplicate email in file: {email}."})
                continue
            seen_usernames.add(username.lower())
            seen_emails.add(email)

            if remaining_slots is not None and remaining_slots <= 0:
                errors.append({"row": idx, "message": "Course is full."})
                continue

            try:
                with transaction.atomic():
                    user, created = self._get_or_create_student_user(
                        username=username,
                        email=email,
                        real_name=real_name,
                        password=password,
                        student_id=student_id,
                    )
                    if created:
                        created_users += 1

                    membership, membership_created = Course_members.objects.get_or_create(
                        course_id=course,
                        user_id=user,
                        defaults={"role": Course_members.Role.STUDENT},
                    )

                    if membership.role != Course_members.Role.STUDENT:
                        errors.append({"row": idx, "message": f"{username} is already in course with role {membership.role}."})
                        continue

                    if membership_created:
                        new_members += 1
                        if remaining_slots is not None:
                            remaining_slots -= 1
                    else:
                        skipped_members += 1
            except ValueError as exc:
                errors.append({"row": idx, "message": str(exc)})
            except IntegrityError as exc:
                errors.append({"row": idx, "message": f"Integrity error: {exc}."})

        if new_members > 0:
            type(course).objects.filter(pk=course.pk).update(
                student_count=F("student_count") + new_members
            )

        return {
            "created_users": created_users,
            "new_members": new_members,
            "skipped_members": skipped_members,
            "errors": errors,
        }

    @staticmethod
    def _normalize_key(key):
        return str(key or "").strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        return str(value).strip()

    def _get_or_create_student_user(self, *, username, email, real_name, password, student_id):
        try:
            user = User.objects.get(username=username)
            created = False
            if user.email.lower() != email.lower():
                raise ValueError("Username belongs to a different email.")
        except User.DoesNotExist:
            if User.objects.filter(email__iexact=email).exists():
                raise ValueError("Email already exists.")
            user = User(
                username=username,
                email=email,
                real_name=real_name,
                identity=User.Identity.STUDENT,
            )
            user.set_password(password or User.objects.make_random_password(length=12))
            user.save()
            created = True

        if user.identity != User.Identity.STUDENT:
            raise ValueError("User is not a student.")

        if user.real_name != real_name:
            user.real_name = real_name
            user.save(update_fields=["real_name"])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if student_id:
            if profile.student_id and profile.student_id != student_id:
                raise ValueError("student_id already bound to another user.")
            if not profile.student_id:
                if UserProfile.objects.exclude(user=user).filter(student_id=student_id).exists():
                    raise ValueError("student_id already used.")
                profile.student_id = student_id
                profile.updated_at = timezone.now()
                profile.save(update_fields=["student_id", "updated_at"])

        return user, created

    @staticmethod
    def _mark_batch_failed(batch, error_log):
        batch.status = Batch_imports.Status.FAILED
        batch.import_result = False
        batch.error_log = error_log
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "import_result", "error_log", "completed_at"])

    @staticmethod
    def _mark_batch_completed(batch, errors):
        batch.status = Batch_imports.Status.COMPLETED
        batch.import_result = len(errors) == 0
        batch.error_log = errors or None
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "import_result", "error_log", "completed_at"])
