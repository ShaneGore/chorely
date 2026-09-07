# Agent Instructions

- `_docs/process.md` - how work is organized

## Roles

- PM - grooms a task before anyone implements it, follows _docs/team/pm.md
- Engineer - implements one groomed task, follows _docs/team/software-engineer.md
- QA - checks the result against the acceptance criteria, follows _docs/team/qa-engineer.md

## Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file
- `.\.venv\Scripts\python.exe manage.py check` - Django configuration check
- `.\.venv\Scripts\python.exe manage.py test` - Django test suite

## Project

- This is a Django project rooted at `manage.py`.
- Project configuration lives in `chorely/`; application code belongs in `chores/`.
- Use the local `.venv` for Python commands until the project is migrated to `uv`.

## Workflow

- Run the relevant check or test after changing Django code.
- Create migrations with `manage.py makemigrations` and apply them with `manage.py migrate`.

## Rules

- Dependencies are added in `pyproject.toml`. Do not add one without asking
