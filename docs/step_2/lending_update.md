# Checkout and return increment - November 24, 2026

This extends the Week 3 reservation workflow and November 13 cancellation increment. Earlier milestone reports are preserved. Implementation and automated verification were performed with OpenAI assistance on November 24, not backdated.

## Implemented
- FR-08: an operator with inventory.manage_lending can record checkout for an approved reservation within its scheduled interval (start inclusive, end exclusive). Equipment must be active and have no unreturned checkout. The reservation end is the due time. Actor and timestamp are recorded.
- Return recording: the same permission allows return of checked-out equipment, including equipment retired after checkout. Actor and return timestamp are retained with approval history. Repeat checkout/return and invalid transitions are rejected.
- FR-02: explicit lending permission, login, POST-only mutations and CSRF protection; staff status alone does not grant lending access.
- Availability conservatively blocks an unreturned item for any requested interval, including after its due time. After return it no longer blocks. This may reject future approvals until the physical return is recorded; this is an intentional prototype policy.
- Database conditional uniqueness enforces at most one checked-out reservation per item. Service writes remain atomic with SQLite IMMEDIATE transactions.
- Borrowers see their own checkout/return status and timestamps. Authorized operators use the new Checkout and returns page.

FR-07 cancellation remains limited to pre-start pending/approved reservations. The broader before-checkout rule is not yet implemented. Cancellation after checkout is rejected. Overdue lists and usage reporting remain planned.

## Changed components
Under src/campus_checkout: inventory/models.py, migration 0004, services.py, views.py, config/urls.py, templates/inventory/base.html, templates/inventory/reservations.html and test_lending.py. Migration 0004 adds nullable lending metadata so earlier reservation records remain compatible.

## Verification
40 tests passed in 2.375 seconds: the prior 30 plus 10 lending tests. Tests exercise an integrated request/approval/checkout/return workflow through Django's HTTP client, timestamps/actors/history, permission denial, CSRF/GET protections, inactive equipment, time boundaries, duplicate actions, overdue blocking, database uniqueness, retired-item return and missing/invalid requests. Existing reservation concurrency tests still pass. No dedicated checkout/return concurrency stress run or manual browser usability review is claimed.

Evidence is in docs/step_2/lending_evidence/: test_output.txt, migrations.txt, migration_check.txt and system_check.txt. Fresh migrations passed; no missing migrations and no system-check issues. No failed tests in this run. Test data are synthetic and databases are excluded from Git.

## Run the updated application
Use a clean Python 3.12 virtual environment, install src/campus_checkout/requirements.txt, then from src/campus_checkout run:

```sh
python manage.py migrate
python manage.py check
python manage.py test inventory --verbosity 2
python manage.py runserver
```

Use your existing local accounts/database only after backing up the database. Do not upload that backup. The new checkout fields require migration 0004 before running the server. A superuser already has the new permission. For a normal operator, a superuser must grant **Can record equipment checkout and return** via Django admin; grant review permission separately if they also approve requests.

## Manual demonstration to perform
1. Borrower requests an item for a slot starting a few minutes in the future; reviewer approves before that slot starts.
2. Once the slot starts, an authorized operator opens Checkout and returns and selects Record checkout.
3. Confirm Checked out with checkout timestamp and due time. A second checkout must be denied while the item remains out.
4. Select Record return. Confirm Returned and the return timestamp; the borrower can see these in My requests.
5. Check a new valid future interval: the returned reservation no longer blocks availability.

Do not claim this manual demonstration has been completed until it is actually performed. Next priorities: manual UI review, a dedicated concurrent lending test, overdue listing, and deciding whether to allow cancellation after scheduled start but before physical checkout.
