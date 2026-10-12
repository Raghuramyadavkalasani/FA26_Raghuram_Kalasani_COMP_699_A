# Reservation approval proof of concept

This is a small Django/SQLite experiment for the Campus Equipment Checkout System. It is not the full website. ChatGPT assisted with the implementation and test design; review the code and retain the conversation as your assistance record.

## Run from the repository root

Use Python 3.12 (the verified environment). The older Python shipped with some Macs will not work with this Django version.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r src/requirements-poc.txt
python src/reservation_poc.py
```

If your `python3` is already Python 3.12, you can use it instead of `python3.12`. Check with `python3 --version`. No web server, account, API key, or environment secret is needed.

The script creates two minimal tables in a new temporary SQLite file, runs 14 test methods, and removes the temporary database when finished. It exits with a nonzero code on test failure. Schema creation is included in the script with Django's schema editor; normal Django migrations will be added when this experiment is integrated into the application.

To save your own run output:

```sh
python src/reservation_poc.py > docs/poc_test_output_local.txt 2>&1
```

Read the output and check that it ends in `OK`. Do not upload `.venv`, database files, credentials, or `__pycache__` directories.

## How it works

`Equipment` identifies a physical asset. `Reservation` stores its requested time interval and status. The `approve()` function opens an immediate transaction, checks the item's state and existing approvals, and saves only if no overlap exists. The conflict comparison allows one booking to end exactly when another starts.

Return values are `approved`, `conflict`, `not_pending`, `inactive`, `expired`, and `retry`. Unexpected errors are allowed to surface. Every database writer must follow the service convention; direct SQL or arbitrary ORM updates can bypass the overlap rule.

The tests use fictional records. Two threads with independent connections attempt competing approvals in 20 rounds. Another test deliberately holds a write lock and verifies a controlled retry with no state change.

## Limits

The experiment does not implement login, borrower ownership, administrator authorization, review audit fields, checkout/return, UI, reports, migrations, or production hosting. The approval function is a service experiment, not a secure public endpoint. No claims are made about complete FR-02, FR-06, FR-11, or NFR-02 compliance. Full approval authorization and the rest of the application remain to be built.

Reconnecting to the database verifies saved data after connection closure; it is not a complete application-restart or power-failure test. Twenty concurrency rounds provide evidence for this environment, not a proof under every workload. The five-second lock timeout and error mapping are design choices to revisit during integration.
