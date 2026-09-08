# chorely

A small Django app for shared households: one shared chore list per household, with claiming, completion, simple recurrence, and completion history.

## Local setup

Requires Python 3.13+.

```bash
# from the repository root
py -m venv .venv                     # Windows (py launcher)
python3 -m venv .venv                # macOS/Linux
source .venv/Scripts/activate        # Git Bash on Windows
source .venv/bin/activate            # macOS/Linux
pip install -r requirements.txt
```

## Database

```bash
.venv/Scripts/python.exe manage.py migrate     # Windows
.venv/bin/python manage.py migrate             # macOS/Linux
```

The dev database is `db.sqlite3`, created on first migrate. No manual data edits are needed; sign up, create or join a household, and start adding chores.

## Development server

```bash
.venv/Scripts/python.exe manage.py runserver
```

Then open http://127.0.0.1:8000/ and sign up.

## Checks and tests

```bash
.venv/Scripts/python.exe manage.py check   # Django configuration check
.venv/Scripts/python.exe manage.py test    # full test suite (fresh test database)
```

## Configuration

Settings read production-sensitive values from the environment; local defaults are safe for development only:

- `DJANGO_SECRET_KEY` - secret key; falls back to a development-only key
- `DJANGO_DEBUG` - `true`/`false`; defaults to `true` locally
- `DJANGO_ALLOWED_HOSTS` - comma-separated hosts; defaults to `localhost,127.0.0.1`

For production, set all three explicitly and never rely on the defaults.

## MVP boundary

This MVP intentionally excludes reminders, push/email notifications, gamification, multiple-household membership, analytics, photo proof, advanced recurrence rules, and calendar/smart-home integrations. Deferred capabilities are tracked in the repository issue tracker.
