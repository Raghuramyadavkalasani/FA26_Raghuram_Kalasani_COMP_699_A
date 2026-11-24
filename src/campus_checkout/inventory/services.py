"""Business rules. All application reservation writes go through these services."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Equipment, Reservation


def validate_interval(start, end):
    if start is None or end is None or timezone.is_naive(start) or timezone.is_naive(end):
        raise ValidationError("Enter valid timezone-aware start and end times.")
    if end <= start:
        raise ValidationError("End must be later than start.")
    if start <= timezone.now():
        raise ValidationError("Start must be in the future.")


def conflicts(equipment, start, end):
    return Reservation.objects.filter(Q(status="approved", start__lt=end, end__gt=start) | Q(status="checked_out"), equipment=equipment)


def require_user(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied


@transaction.atomic
def request_reservation(user, equipment_id, start, end):
    require_user(user)
    validate_interval(start, end)
    item = Equipment.objects.get(pk=equipment_id)
    if not item.is_active:
        raise ValidationError("This equipment is inactive.")
    # Pending requests may compete; only approval blocks the interval.
    return Reservation.objects.create(equipment=item, borrower=user, start=start, end=end)


@transaction.atomic
def review_reservation(user, reservation_id, decision):
    require_user(user)
    if not user.has_perm("inventory.review_reservation"):
        raise PermissionDenied
    if decision not in ("approved", "rejected"):
        raise ValidationError("Choose approve or reject.")
    reservation = Reservation.objects.select_related("equipment").get(pk=reservation_id)
    if reservation.status != "pending":
        raise ValidationError("Only pending requests can be reviewed.")
    if decision == "approved":
        validate_interval(reservation.start, reservation.end)
        if not reservation.equipment.is_active:
            raise ValidationError("This equipment is inactive.")
        if conflicts(reservation.equipment, reservation.start, reservation.end).exists():
            raise ValidationError("Approval blocked: this item already has an overlapping approved reservation.")
    reservation.status = decision
    reservation.reviewed_by = user
    reservation.reviewed_at = timezone.now()
    reservation.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    return reservation


@transaction.atomic
def cancel_reservation(user, reservation_id):
    """Owner-only cancellation before start; retain review history.

    Pre-start cutoff is conservative until checkout state is implemented.
    SQLite IMMEDIATE transactions serialize this with approval writes.
    """
    require_user(user)
    reservation = Reservation.objects.get(pk=reservation_id)
    if reservation.borrower_id != user.pk:
        raise PermissionDenied
    if not reservation.can_cancel:
        raise ValidationError("Only pending or approved reservations that have not started can be cancelled.")
    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.save(update_fields=["status", "cancelled_at"])
    return reservation


@transaction.atomic
def checkout_reservation(user, reservation_id):
    require_user(user)
    if not user.has_perm("inventory.manage_lending"):
        raise PermissionDenied
    row = Reservation.objects.select_related("equipment").get(pk=reservation_id)
    if not row.can_checkout:
        raise ValidationError("Checkout requires an approved reservation within its scheduled interval.")
    if not row.equipment.is_active:
        raise ValidationError("Inactive equipment cannot be checked out.")
    if Reservation.objects.filter(equipment=row.equipment, status="checked_out").exists():
        raise ValidationError("This equipment has an unreturned checkout.")
    row.status = "checked_out"
    row.checked_out_at = timezone.now()
    row.checked_out_by = user
    row.save(update_fields=["status", "checked_out_at", "checked_out_by"])
    return row


@transaction.atomic
def return_reservation(user, reservation_id):
    require_user(user)
    if not user.has_perm("inventory.manage_lending"):
        raise PermissionDenied
    row = Reservation.objects.get(pk=reservation_id)
    if row.status != "checked_out":
        raise ValidationError("Only checked-out equipment can be returned.")
    row.status = "returned"
    row.returned_at = timezone.now()
    row.returned_by = user
    row.save(update_fields=["status", "returned_at", "returned_by"])
    return row
