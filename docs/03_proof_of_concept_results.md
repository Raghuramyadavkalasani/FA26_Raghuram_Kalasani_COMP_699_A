# Technical Proof of Concept and Results

## Purpose
The main risk tested here is whether two overlapping reservations for one item can both become approved. The experiment uses Django models and SQLite immediate transactions, as proposed in the architecture draft. It focuses on the conflict-checking part of FR-06 and the transactional behavior in NFR-02.

## Implementation
The standalone `src/reservation_poc.py` creates a temporary file-backed database containing Equipment and Reservation tables. It checks interval validity and asset uniqueness at database level. Approval checks pending status, active equipment, a future start, and interval overlap inside one immediate transaction. A busy database produces a retry result without an approval update.

This deliberately small implementation omits the website and other workflows. It does not replace the full schema described in the design. No real university information is used.

## Recorded execution
The assistant executed the tests in the local workspace while preparing this deliverable; these results are not a claim that the student independently ran them. The student should repeat the documented command and be prepared to explain it.

Command: `python src/reservation_poc.py` (using the isolated Python environment).

Environment reported by the run: macOS/Darwin arm64, Python 3.12.14, Django 5.2.18, SQLite 3.53.1. Exact installed dependencies are recorded in `src/requirements-poc.txt`.

Result: **14 test methods passed**, with a reported test runtime of **0.157 seconds**. This runtime is not an application performance benchmark. The unedited captured output is in `docs/poc_test_output.txt`.

| Check | Observed result |
|---|---|
| Valid approval and database reconnection | Saved approval remained available after closing and reopening the connection. |
| Partial, identical, contained, and containing overlaps | Conflicts were rejected and requests stayed pending. |
| Back-to-back bookings on both boundaries | Both permitted. |
| Same interval for different equipment | Permitted. |
| Pending, rejected, and cancelled records | Did not block a new approval. |
| Zero-length/reversed intervals, invalid status, duplicate asset tag | Rejected by database constraints. |
| Repeated approval, inactive item, past start, cancelled request | Returned the corresponding failure outcome. |
| Two competing approvals, 20 rounds | Every round produced exactly one approved result and one conflict; database contained one approved and one pending request. |
| Deliberately held write lock | Returned retry and left the reservation pending. |

## What this demonstrates
The recorded run supports the feasibility of keeping the conflict check and update together in a short SQLite transaction. It also shows boundary handling and several failure paths. The concurrency tests use independent connections to the same file, rather than merely calling the approval function twice in sequence.

## What remains
Authentication, authorization, borrower identity, review audit fields, HTTP forms, CSRF handling, checkout and return, usage reports, performance testing, and final deployment are not implemented. Full requirement compliance has not been established. Persistence was checked after reconnecting, not after a full application restart or unexpected shutdown. The observed concurrency result should be repeated on the student's machine and re-evaluated after integration.

## AI assistance
ChatGPT helped write and run this experiment and summarize its actual output. The source and tests are included so their behavior can be reviewed and reproduced.
