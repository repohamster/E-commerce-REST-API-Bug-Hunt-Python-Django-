# Installation and Execution

## Requirements

- Python 3.10 or newer
- pip

No database server or database credentials are required. Django uses the local SQLite file `db.sqlite3` in the project root.

## Install

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

On Windows, activate the environment with `.venv\\Scripts\\activate`. `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` can be set in `.env`. The example values are for local development; use a private secret key and disable debug mode before deployment. No database URL is used.

## Run

```sh
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`.

## Tests

```sh
python manage.py test hello_world.core
```

The suite contains exactly six Django tests, one per intentional defect. They are expected to fail against the starter implementation and pass after all six behaviors are fixed. Django creates a temporary SQLite database for tests; the project's local database is not used by the test run.
