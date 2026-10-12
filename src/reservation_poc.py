"""Small Django/SQLite experiment, not the full application. AI-assisted code."""
import platform
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import django
from django.conf import settings

# A new temporary file is used for every run; no existing user database is touched.
TEMP = tempfile.TemporaryDirectory(prefix="equipment-poc-")
settings.configure(
    INSTALLED_APPS=[], USE_TZ=True, TIME_ZONE="America/New_York",
    DATABASES={"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(TEMP.name) / "poc.sqlite3"),
        "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 5},
    }},
)
django.setup()
from django.db import connection, connections, models, transaction, OperationalError, IntegrityError
from django.utils import timezone


class Equipment(models.Model):
    asset_tag = models.CharField(max_length=40, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "reservation_poc"


class Reservation(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=10, default="pending")

    class Meta:
        app_label = "reservation_poc"
        constraints = [
            models.CheckConstraint(condition=models.Q(end_at__gt=models.F("start_at")), name="valid_interval"),
            models.CheckConstraint(condition=models.Q(status__in=["pending", "approved", "rejected", "cancelled"]), name="valid_status"),
        ]
        indexes = [models.Index(fields=["equipment", "status", "start_at"])]


def approve(reservation_id):
    """Serialize the conflict check and update; caller authorization is out of scope."""
    try:
        with transaction.atomic():
            request = Reservation.objects.select_related("equipment").get(pk=reservation_id)
            if request.status != "pending":
                return "not_pending"
            if not request.equipment.is_active:
                return "inactive"
            if request.start_at <= timezone.now():
                return "expired"
            conflict = Reservation.objects.filter(
                equipment_id=request.equipment_id, status="approved",
                start_at__lt=request.end_at, end_at__gt=request.start_at,
            ).exclude(pk=request.pk).exists()
            if conflict:
                return "conflict"
            request.status = "approved"
            request.save(update_fields=["status"])
            return "approved"
    except OperationalError as exc:
        # Only lock contention is retryable; unrelated database errors must surface.
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            return "retry"
        raise


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        Reservation.objects.all().delete()
        Equipment.objects.all().delete()
        self.item = Equipment.objects.create(asset_tag="LAPTOP-001")
        self.base = timezone.now() + timedelta(days=1)

    def request(self, start=0, end=60, item=None, status="pending"):
        return Reservation.objects.create(
            equipment=item or self.item, start_at=self.base + timedelta(minutes=start),
            end_at=self.base + timedelta(minutes=end), status=status,
        )

    def test_valid_request_persists_after_reconnect(self):
        request = self.request()
        self.assertEqual(approve(request.pk), "approved")
        connection.close()
        self.assertEqual(Reservation.objects.get(pk=request.pk).status, "approved")

    def test_overlap_shapes_rejected_without_change(self):
        self.request(0, 60, status="approved")
        for start, end in [(-30, 30), (30, 90), (0, 60), (10, 50), (-10, 70)]:
            with self.subTest(interval=(start, end)):
                request = self.request(start, end)
                self.assertEqual(approve(request.pk), "conflict")
                request.refresh_from_db()
                self.assertEqual(request.status, "pending")

    def test_back_to_back_allowed_on_both_sides(self):
        self.request(0, 60, status="approved")
        for start, end in [(-60, 0), (60, 120)]:
            self.assertEqual(approve(self.request(start, end).pk), "approved")

    def test_different_equipment_allowed(self):
        self.request(status="approved")
        other = Equipment.objects.create(asset_tag="LAPTOP-002")
        self.assertEqual(approve(self.request(item=other).pk), "approved")

    def test_nonblocking_statuses(self):
        for status in ["pending", "cancelled", "rejected"]:
            self.request(status=status)
        self.assertEqual(approve(self.request().pk), "approved")

    def test_invalid_intervals_database_rejects(self):
        for start, end in [(10, 10), (20, 10)]:
            with self.assertRaises(IntegrityError):
                self.request(start, end)

    def test_invalid_status_database_rejects(self):
        with self.assertRaises(IntegrityError):
            self.request(status="unknown")

    def test_duplicate_asset_database_rejects(self):
        with self.assertRaises(IntegrityError):
            Equipment.objects.create(asset_tag="LAPTOP-001")

    def test_repeated_approval(self):
        request = self.request()
        self.assertEqual(approve(request.pk), "approved")
        self.assertEqual(approve(request.pk), "not_pending")
        self.assertEqual(Reservation.objects.filter(status="approved").count(), 1)

    def test_inactive_equipment(self):
        request = self.request()
        self.item.is_active = False
        self.item.save()
        self.assertEqual(approve(request.pk), "inactive")
        request.refresh_from_db()
        self.assertEqual(request.status, "pending")

    def test_past_start(self):
        request = self.request(-3000, -2900)
        self.assertEqual(approve(request.pk), "expired")

    def test_cancelled_request_cannot_be_approved(self):
        self.assertEqual(approve(self.request(status="cancelled").pk), "not_pending")

    def test_simultaneous_approvals_20_rounds(self):
        for round_number in range(20):
            with self.subTest(round=round_number):
                Reservation.objects.all().delete()
                first, second = self.request(), self.request(30, 90)
                barrier = threading.Barrier(2)

                def worker(pk):
                    try:
                        barrier.wait(timeout=10)
                        return approve(pk)
                    finally:
                        connections.close_all()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(worker, r.pk) for r in (first, second)]
                    outcomes = [f.result(timeout=15) for f in futures]
                self.assertEqual(sorted(outcomes), ["approved", "conflict"])
                self.assertEqual(Reservation.objects.filter(status="approved").count(), 1)
                self.assertEqual(Reservation.objects.filter(status="pending").count(), 1)

    def test_busy_database_returns_retry_without_update(self):
        request = self.request()
        ready, release = threading.Event(), threading.Event()

        def hold_write_lock():
            try:
                with transaction.atomic():
                    ready.set()
                    if not release.wait(timeout=10):
                        raise TimeoutError("Lock-holder release timed out")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as pool:
            holder = pool.submit(hold_write_lock)
            self.assertTrue(ready.wait(timeout=5))
            try:
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA busy_timeout=50")
                self.assertEqual(approve(request.pk), "retry")
            finally:
                release.set()
                holder.result(timeout=10)
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA busy_timeout=5000")
        request.refresh_from_db()
        self.assertEqual(request.status, "pending")


if __name__ == "__main__":
    import sys
    print("Environment:", platform.system(), platform.machine(), "Python", platform.python_version(),
          "Django", django.get_version(), "SQLite", sqlite3.sqlite_version, flush=True)
    print("Temporary file-backed database; IMMEDIATE transactions; two independent worker connections.", flush=True)
    try:
        with connection.schema_editor() as editor:
            editor.create_model(Equipment)
            editor.create_model(Reservation)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ApprovalTests)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        connections.close_all()
        TEMP.cleanup()
    sys.exit(0 if result.wasSuccessful() else 1)
