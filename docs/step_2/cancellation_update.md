# Increment after Week 3: reservation cancellation
Implemented November 13, 2026, with OpenAI assistance. Earlier milestone documents remain unchanged.

FR-07 is partially implemented: owners can cancel pending or approved reservations before their start time. Cancelled records and reviewer history are preserved; cancelled_at records the action. The conservative pre-start cutoff is an interim policy until FR-08 checkout state exists. The full before-checkout requirement is not claimed complete. FR-02 ownership checks and FR-04 availability are integrated.

Run migration 0003 before starting the updated application. My requests now includes a Cancel reservation button for eligible records. Cancellation uses authenticated POST with CSRF protection. Server-side checks reject other owners (including administrators), inactive users, terminal statuses and started reservations. Cancelled reservations cannot subsequently be approved. SQLite IMMEDIATE transactions serialize service writes.

Verification: 30 automated tests passed, including nine new cancellation tests, using a fresh Python 3.12 environment and pinned dependencies. Tests use Django's HTTP client and synthetic records; no new manual browser run or cancellation concurrency stress test is claimed. Evidence is in docs/step_3/evidence/. An initial environment failure (duplicate Django migrations) and an initial test timezone mistake are preserved and explained in the evidence README. Checkout, returns and overdue reporting remain planned.
