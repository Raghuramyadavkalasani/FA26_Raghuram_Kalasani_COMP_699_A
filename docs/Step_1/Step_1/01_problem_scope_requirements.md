# Campus Equipment Checkout System
## Step 1 planning draft: Problem, scope, stakeholders, and requirements

Status: Initial design draft. These are proposed requirements, not implemented features or test results. Review and revise them before committing. This file covers the first four assignment sections; architecture, data design, interfaces, technology decisions, proof of concept, evaluation, risks, and schedule remain to be developed.

## 1. Problem Definition and Project Scope

### Problem and intended outcome
A university department that lends laptops, projectors, and laboratory equipment needs to know which items are available, who has borrowed them, and when they are due back. If availability and lending records are maintained in separate spreadsheets or messages, staff may have difficulty identifying booking conflicts and overdue returns. Students and staff may also need to contact an administrator merely to learn whether an item is available.

This is a proposed scenario for an academic prototype. It has not been verified through interviews with a particular department, and no measured claim about current delays or error rates is being made.

The proposed system will centralize equipment records, reservation requests, approvals, and checkout history. Software is appropriate because the problem involves repeated record updates, time-interval comparisons, permissions, and queries across related records. The intended outcome is a working departmental prototype with testable booking and access-control rules, rather than a production university service.

### In scope
- Login and logout for administrator-created accounts.
- Borrower and equipment-administrator roles.
- Equipment catalog with unique asset identifiers and active or inactive status.
- Availability lookup for a requested time interval.
- Reservation requests, administrator approval or rejection, and borrower cancellation before checkout.
- Checkout and return recording by administrators.
- Overdue-item identification and a basic usage summary.
- Synthetic accounts and equipment records for testing and demonstration.
- A browser-based interface and persistent local database.

### Out of scope
- University single sign-on and integration with official student systems.
- Payments, fines, purchasing, and equipment delivery.
- Email or SMS notifications, barcode hardware, and a native mobile application.
- Recurring bookings, multi-department administration, and high-availability hosting.
- Use of real student records or claims of production readiness.

### Initial business rules and assumptions
- A reservation is for one individually identified physical item; quantity-based bookings are excluded.
- Users enter times in America/New_York. Stored timestamps must represent timezone-aware instants.
- Intervals are start-inclusive and end-exclusive: 10:00-11:00 and 11:00-12:00 may coexist.
- Pending requests do not block availability. Approved reservations do. Approval must recheck conflicts, including competing requests approved concurrently.
- Two blocking intervals overlap when existing_start < requested_end and existing_end > requested_start.
- A checked-out item cannot be checked out again until its return is recorded, even if its original due time has passed.
- Overdue means a checkout has no return timestamp and its due timestamp is earlier than the current time.
- Approval is not a guarantee of physical availability if a previous borrower returns equipment late; checkout must check the current lending state.
- The intended scale is one department. Performance targets below are proposed acceptance targets, not observed results.

## 2. Users and Stakeholders

| Role | Goals and tasks | Design constraints |
|---|---|---|
| Borrower: student or staff member | Find equipment; request a time slot; review own requests and loans; cancel an eligible reservation. | Must authenticate; cannot view other borrowers' personal records or perform administrative actions. Students and staff share the same permissions. |
| Equipment administrator | Maintain inventory; review competing requests; approve or reject requests; record loans and returns; inspect overdue items and usage. | Must use explicit administrative permissions; needs clear status and validation messages. |
| Department manager | Assess whether the prototype supports accountability and basic usage reporting. | Stakeholder only; no separate login role is planned. An administrator can present the report. |
| Student developer and course instructor | Implement and evaluate the design; review source code, test evidence, limitations, and demonstration. | Use synthetic data and reproducible instructions; keep implementation limited to a meaningful proof of concept for this assignment. |

## 3. Functional Requirements

| ID | Requirement | Acceptance example |
|---|---|---|
| FR-01 | The system shall allow active users with valid credentials to log in and log out, and reject invalid credentials. | A valid account reaches its dashboard; an invalid password fails; a logged-out user cannot access protected pages. |
| FR-02 | The system shall enforce borrower and administrator permissions on the server. | A borrower submitting a direct request to approve a reservation is denied and the record is unchanged. |
| FR-03 | Administrators shall create and update equipment with a unique asset identifier, name, category, description, and active status. | A duplicate asset identifier is rejected; an inactive item cannot receive a new reservation. |
| FR-04 | Authenticated users shall search active equipment by name or category and check availability for a valid start/end interval. | An item with an overlapping approved reservation is reported unavailable for that interval. |
| FR-05 | Borrowers shall request a reservation for an active item with a future start and an end later than its start. | A valid request is stored as pending and linked to the requester; invalid times are rejected. |
| FR-06 | Administrators shall approve or reject pending requests. Approval shall reject an overlap with an existing approved reservation for the same item. | Two overlapping pending requests may exist, but at most one can become approved; back-to-back bookings are permitted. |
| FR-07 | Borrowers shall view their own reservation status and cancel their own pending or approved reservations before checkout. | Cancellation changes the status and releases any booking block; another user's cancellation attempt is denied. |
| FR-08 | Administrators shall record checkout against an approved reservation during its scheduled interval, provided the item is active and has no open checkout. | Checkout stores the administrator and timestamp, uses the reservation end as the due time, and cannot be recorded twice. |
| FR-09 | Administrators shall record return of an open checkout. | A return timestamp is saved; the checkout is no longer open; repeating the return action does not create another return record. |
| FR-10 | Administrators shall view all overdue open checkouts with equipment, borrower, and due time. | A past-due unreturned item appears; a returned item and a not-yet-due item do not. |
| FR-11 | The system shall preserve reservation and checkout records across restarts and retain their links to users and equipment. | Records remain queryable after restart; deactivating equipment preserves its historical loans. |
| FR-12 | Administrators shall view a basic usage summary giving checkout counts per equipment item for a selected checkout-date range. | Counts match a small prepared dataset, including items with zero checkouts. |

## 4. Nonfunctional Requirements

| ID | Proposed measurable requirement | Planned verification |
|---|---|---|
| NFR-01 Security | Every protected operation shall check authentication, role, and record ownership as appropriate. Passwords shall use framework-managed hashing; state-changing browser requests shall require CSRF protection. | Positive and negative access tests, password-storage inspection, and a CSRF rejection test. |
| NFR-02 Data integrity | A failed approval shall leave no partial update. Concurrent approval attempts for overlapping reservations shall result in at most one approved reservation. | Database integration tests including concurrent requests. The transaction strategy remains a design decision to validate. |
| NFR-03 Performance | With 200 equipment items and 2,000 reservation records, at least 95 of 100 sequential authenticated availability requests shall complete within two seconds on the documented local test machine after warm-up. | Record machine details, fixture generation, request timings, and percentile calculation. This target does not establish multiuser production capacity. |
| NFR-04 Persistence | A committed reservation and checkout shall survive an application restart with their values and relationships intact. | Restart and query a known dataset; document results. |
| NFR-05 Usability and accessibility | Login, availability search, reservation submission, and administrator approval shall be usable by keyboard, with labeled controls and visible validation errors. | Manual task checklist; this is a limited evaluation, not a claim of full accessibility-standard compliance. |
| NFR-06 Privacy | Demonstration and test datasets shall contain only fictional user information; borrowers shall not access other borrowers' records. | Inspect fixtures and test record-ownership checks. |
| NFR-07 Reproducibility | The proof of concept shall run from a clean checkout using documented dependency installation, database initialization, and test commands, without committed secrets. | Repeat the documented setup in a fresh environment and retain actual command output. |
| NFR-08 Compatibility | Core browser workflows shall pass the same manual checklist in the installed Chrome and Safari versions on the development Mac. | Record browser versions and checklist outcomes during final evaluation. |

## Next planning work
1. Review these assumptions and reduce scope if needed.
2. Draw the architecture and data model; resolve transaction and concurrent-approval behavior before selecting a final persistence strategy.
3. Map requirements to screens, internal operations, and tests.
4. Develop a focused database-backed reservation-conflict proof of concept and record real results. Do not implement the full application for this assignment.
5. Complete the remaining report sections and dated milestones. Canvas shows Wednesday at 23:59; October 14, 2026 is the working Step 1 deadline based on the October 12 screenshot. Confirm the final-system deadline separately.

## AI assistance disclosure
This initial planning draft was prepared with OpenAI assistant support. The student should review the requirements, retain the actual conversation as a record of assistance, and follow the instructor's disclosure requirements. No stakeholder interviews, implementation results, or test passes are claimed in this draft.
