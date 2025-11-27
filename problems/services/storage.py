import hashlib
import os
from typing import BinaryIO, Tuple

from django.conf import settings
from django.core.files.storage import FileSystemStorage

_storage = FileSystemStorage(location=settings.MEDIA_ROOT)


def _sha256_of_fileobj(f: BinaryIO) -> str:
    hasher = hashlib.sha256()
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        hasher.update(chunk)
    return hasher.hexdigest()


def save_testcase_file(problem_id: int, subtask_id: int, idx: int, kind: str, file_obj) -> Tuple[str, int, str]:
    assert kind in ("in", "out")
    rel_dir = os.path.join("testcases", f"p{problem_id}", f"s{subtask_id}", f"i{idx}")
    filename = getattr(file_obj, 'name', f"{kind}.txt")
    rel_path = os.path.join(rel_dir, os.path.basename(filename))
    saved_path = _storage.save(rel_path, file_obj)
    abs_path = _storage.path(saved_path)
    size = os.path.getsize(abs_path)
    with open(abs_path, "rb") as f:
        checksum = _sha256_of_fileobj(f)
    return saved_path.replace("\\", "/"), size, checksum


def open_testcase_file(rel_path: str):
    return _storage.open(rel_path, "rb")
