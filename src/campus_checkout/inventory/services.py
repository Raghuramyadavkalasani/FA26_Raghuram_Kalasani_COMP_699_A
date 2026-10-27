"""Business rules. All application reservation writes go through these services."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
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
    return Reservation.objects.filter(equipment=equipment, status="approved", start__lt=end, end__gt=start)


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
