# Software development: Week 1

This guide replaces the earlier research-input guide. The software project is Campus Equipment Checkout. The previous research documents remain historical material, not the current milestone submission.

## Run from the repository root

Use Python 3.12, not the Mac system Python 3.9. If python3.12 is not on PATH, use your installed Python 3.12 executable or reuse the working Python 3.12 virtual environment.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r src/campus_checkout/requirements.txt
cd src/campus_checkout
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/admin/ and sign in. Add, edit, search, and retire synthetic equipment. Stop the server with Control+C, then run:

```sh
python manage.py check
python manage.py test inventory --verbosity 2
```

The assistant reran all six inventory tests successfully on October 27, 2026. See docs/step_2/week_1/verification for captured results and implementation_foundation.pdf for scope and limitations. Reservation and lending workflows remain planned.

This package has no live accounts or database. Do not upload .venv, db.sqlite3, __pycache__, .env, or real credentials. Settings are for local development only. ChatGPT assisted with this package. Review and reproduce the work before demonstrating it.
