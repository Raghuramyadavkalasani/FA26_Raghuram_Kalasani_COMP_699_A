# Weeks 2 and 3: Campus Equipment Checkout
Software-development milestones prepared October 27, 2026 with AI assistance. Review the code and run the demonstration yourself before submission. The reports describe assistant-run verification, not a claim of student execution or three weeks of commits.

## Start from this package folder
Use your installed Python 3.12 interpreter (the Mac system Python 3.9 is not suitable for Django 5.2).
```
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r src/campus_checkout/requirements.txt
cd src/campus_checkout
python manage.py migrate
python manage.py createsuperuser
python manage.py create_demo_borrower
python manage.py runserver
```
Choose your own passwords when prompted. No passwords are included. create_demo_borrower creates fictional demo-borrower and DEMO-LAP-001. For an existing borrower use `python manage.py changepassword demo-borrower`.

## Browser demonstration
1. Open http://127.0.0.1:8000/ and log in as demo-borrower.
2. Search Laptop with a future start and later end in America/New_York time.
3. Click Request; enter the future interval and submit. My requests shows Pending.
4. Log out; log in with your superuser. Click Review requests, then Approve.
5. Log out; log in as demo-borrower. My requests shows Approved. Search the same interval; the equipment is Unavailable.
6. Try a request whose end is before its start. The form displays an error and creates no reservation.
7. Create a competing pending request; as the administrator try approving it. The conflict error preserves Pending.
8. Adjacent bookings are allowed: the second start may equal the first end.

A non-superuser reviewer must be granted the inventory 'Can approve or reject reservation requests' permission using /admin/ Users. Staff status alone is not permission to approve. Inventory changes continue through /admin/.

## Tests (stop server with Control+C first)
```
python manage.py test inventory --verbosity 2
python manage.py check
python manage.py makemigrations --check --dry-run
```
Tests use a separate file-backed test_campus.sqlite3 so concurrent database connections exercise real SQLite locking. Do not put personal data in that test filename. CAMPUS_TEST_DB can select another test path.

## Reproduce HTTP workflow evidence in a separate database
From src/campus_checkout:
```
CAMPUS_DB=/tmp/campus-demo.sqlite3 python manage.py migrate
CAMPUS_DB=/tmp/campus-demo.sqlite3 python manage.py demo_workflow
```
Each run creates new synthetic records. Its intentional unauthorized approval may print a PermissionDenied trace: HTTP 403 is the expected result. Accounts made by this evidence command have no usable password. Use create_demo_borrower for the interactive browser demo.

## Upload to GitHub
Upload the contents (docs, src, START_WEEK_1.md, START_WEEKS_2_3.md, and .gitignore) at repository root. In Finder Command+Shift+period reveals .gitignore. Keep earlier Step 1 and Week 1 submissions. Never upload .venv, __pycache__, or SQLite databases. Do not backdate commits. These milestone names organize deliverables; they do not establish weekly attendance or past progress.

## Reports
- docs/step_2/week_2/core_functionality.pdf
- docs/step_2/week_3/integration_and_progress.pdf
- docs/step_2/step_2_combined_review.pdf includes preserved Week 1 report and completion plan.

The assignment's last paragraph uses research section titles despite the software-specific tables. The combined review uses the software titles; confirm the final heading expectation with Prof Pitts. The full application is not finished: cancellation, lending, returns, overdue reports and usage reporting remain.

Student execution update (October 27): browser Pending -> Approved -> Unavailable observations and a 21-test pass in 1.791 seconds are recorded under docs/step_2/week_3/verification/student_run. See the updated Week 3 report.
