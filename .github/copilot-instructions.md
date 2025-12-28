# GitHub Copilot Instructions for Spaghetti-OJ Backend

This document provides instructions for GitHub Copilot when working on the Spaghetti-OJ (NOJ) backend codebase.

## Project Overview

This is the backend system for an Online Judge (OJ) platform built with **Django 5.2.7** and **Django REST Framework 3.16.1**. The system handles code submission, evaluation, course management, and user authentication for programming contests and assignments.

## Technology Stack

- **Framework**: Django 5.2.7 with Django REST Framework 3.16.1
- **Database**: PostgreSQL (production), SQLite (development)
- **Cache & Message Queue**: Redis 7.1.0
- **Task Queue**: Celery 5.4.0
- **Authentication**: JWT (djangorestframework_simplejwt 5.5.1)
- **API Documentation**: drf-spectacular 0.29.0 (OpenAPI/Swagger)
- **Testing**: pytest with hypothesis for property-based testing
- **Python Version**: Managed via `.python-version` file

## Project Structure

### Main Django Apps

- **`auths/`** - Authentication and security (JWT tokens, permissions)
- **`user/`** - User management and profiles
- **`profiles/`** - Extended user profile information
- **`courses/`** - Course and member management
- **`problems/`** - Problem management and storage
- **`assignments/`** - Assignment system for courses
- **`submissions/`** - Code submission and evaluation
- **`copycat/`** - Plagiarism detection using MOSS
- **`editor/`** - Code editor related functionality
- **`announcements/`** - Announcement system
- **`search/`** - Search functionality
- **`api_tokens/`** - API token management

### Configuration

- **`back_end/settings.py`** - Main Django settings
- **`back_end/celery.py`** - Celery configuration
- **`manage.py`** - Django management script with dotenv support
- **`.env`** - Environment variables (not in Git, use `.env.example` as template)

## Development Setup

### Environment Setup

1. **Python Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Environment Variables**: Copy `.env.example` to `.env` and configure

### Required Services

The project requires **4 concurrent services** during development:

1. **Redis** (Message queue for Celery):
   ```bash
   docker-compose -f docker-compose.redis.yml up -d
   # Verify: redis-cli ping (should return PONG)
   ```

2. **Celery Worker** (Async task processing):
   ```bash
   celery -A back_end worker -l info
   # Note: Must restart after code changes in tasks.py
   ```

3. **Django Development Server**:
   ```bash
   python manage.py runserver
   # Available at http://localhost:8000
   ```

4. **Test/Command Terminal**: For running pytest, migrations, etc.

### API Documentation

- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`

## Coding Standards

### File Structure

- Each Django app follows standard structure: `models.py`, `views.py`, `serializers.py`, `urls.py`, `tests/`
- Tests are organized in `tests/` directories within each app or as `test_*.py` files
- Use pytest fixtures defined in `conftest.py` at the root level

### Testing

- **Framework**: pytest (configured in `pytest.ini`)
- **Property-based testing**: Hypothesis (profiles: dev, ci, debug)
- **Test markers**: `@pytest.mark.slow`, `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.hypothesis`
- **Fixtures**: 
  - `api_client()` - DRF APIClient for testing API endpoints
  - Tests automatically use in-memory cache to avoid Redis dependency
- **Run tests**: `pytest` or `pytest -m "not slow"` to skip slow tests

### Code Style

- Follow Django and DRF conventions
- Use Django's model validation and DRF serializers for data validation
- Handle authentication with JWT tokens via djangorestframework_simplejwt
- Use Celery tasks for long-running operations (e.g., code evaluation)

### Environment Variables

Always use environment variables for:
- `DJANGO_DEBUG` - Debug mode flag
- `DJANGO_SECRET_KEY` - Django secret key
- `DB_ENGINE` - Database engine (sqlite/postgresql)
- `CELERY_BROKER_URL` - Redis URL for Celery
- `SANDBOX_API_URL` - External sandbox API for code evaluation
- `CORS_ALLOWED_ORIGINS` - Frontend CORS settings
- `CSRF_TRUSTED_ORIGINS` - CSRF trusted origins

### Dependencies

- Add new dependencies to `requirements.txt` with version pinning
- Update via `pip freeze > requirements.txt` after installing new packages
- Coordinate dependency updates with team

## Git Workflow

### Branching Strategy

- **`main`** - Production branch (only team lead/PM can merge)
- **`dev`** - Main development branch (all features merge here)
- **Feature branches** - Created from `dev`, named as:
  - `feat/feature-name` - New features
  - `fix/bug-description` - Bug fixes
  - `docs/documentation-topic` - Documentation
  - `refactor/component-name` - Code refactoring
  - `chore/task-description` - Configuration/tooling

### Commit Convention

Format: `type: subject`

**Types**:
- `feat` - New feature or functionality
- `fix` - Bug fix
- `docs` - Documentation or comments
- `refactor` - Code refactoring (no functionality change)
- `chore` - Environment/configuration changes

**Examples**:
```
feat: add login backend support
fix: correct submission serializer bug
docs: update API usage in README
refactor: simplify course query logic
chore: update Django version to 5.2.7
```

**Best Practice**: Make small, focused commits - commit after completing each logical unit of work.

### Pull Request Workflow

1. Create feature branch from `dev`
2. Develop and commit changes
3. Submit PR to `dev`
4. Code review by team
5. Merge to `dev` after approval
6. Team lead/PM merges `dev` to `main` when stable

## Important Notes

### Celery Tasks

- Celery workers do **not** auto-reload on code changes
- After modifying `tasks.py` or related code, **restart the Celery worker** with Ctrl+C and restart
- Tasks are typically in `<app>/tasks.py` (e.g., `submissions/tasks.py`)

### Database

- Development uses **SQLite** (file: `db.sqlite3`)
- Production uses **PostgreSQL**
- Database file `db.sqlite3` is in `.gitignore`

### Sandbox Integration

- External sandbox API is used for code evaluation
- Configuration in `.env`: `SANDBOX_API_URL`, `SANDBOX_API_KEY`, `SANDBOX_TIMEOUT`
- Async submission handled via Celery tasks

### Security

- Never commit `.env` file (already in `.gitignore`)
- Keep `DJANGO_SECRET_KEY` secret and unique per environment
- Use JWT for API authentication
- Validate all user inputs via serializers

### Files to Ignore

Already configured in `.gitignore`:
- Virtual environments (`.venv/`, `venv/`, `env/`)
- Database (`db.sqlite3`)
- Python cache (`__pycache__/`, `*.pyc`)
- Environment config (`.env`)
- IDE settings (`.vscode/`, `.idea/`)
- Test artifacts (`.pytest_cache/`, `.hypothesis/`)

## Common Commands

```bash
# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Testing
pytest                          # Run all tests
pytest -m "not slow"           # Skip slow tests
pytest path/to/test_file.py    # Run specific test file

# Django shell
python manage.py shell

# Redis verification
redis-cli ping                 # Should return PONG

# Celery worker
celery -A back_end worker -l info

# API documentation
# Visit http://localhost:8000/api/schema/swagger-ui/
```

## Additional Resources

- Main developer documentation: `docs/developers.MD` (contains detailed Chinese documentation)
- App-specific documentation in `docs/` directory (e.g., `docs/submissions.MD`, `docs/auths.MD`)
- Cache usage documentation: `cache_usage.md`

## When Making Changes

1. **Check if services are running**: Redis, Celery, Django server
2. **Run existing tests** before making changes to understand baseline
3. **Make minimal, focused changes** aligned with the task
4. **Write/update tests** for new functionality (if test infrastructure exists)
5. **Update documentation** if changing user-facing behavior or APIs
6. **Follow commit conventions** when committing changes
7. **Restart Celery** if modifying async tasks
8. **Test manually** via API documentation (Swagger UI) when appropriate

## Language Note

- Code, comments, and commit messages are primarily in **English**
- Documentation in `docs/` is primarily in **Chinese (Traditional/Simplified)**
- Both languages are acceptable in documentation, but be consistent within a file
