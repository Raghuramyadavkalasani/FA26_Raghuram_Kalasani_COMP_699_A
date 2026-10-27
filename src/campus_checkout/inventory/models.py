from django.core.validators import RegexValidator
from django.db import models


class Equipment(models.Model):
    asset_tag = models.CharField(
        max_length=50, unique=True,
        validators=[RegexValidator(r"^[A-Z0-9-]+$", "Use uppercase letters, numbers, and hyphens.")],
        help_text="Unique inventory identifier, for example LAP-001.",
    )
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Clear to retire equipment from lending.")

    class Meta:
        ordering = ["asset_tag"]

    def __str__(self):
        return f"{self.asset_tag} — {self.name}"


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    borrower = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="reservations")
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.PROTECT, related_name="reviews")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("review_reservation", "Can approve or reject reservation requests")]
        constraints = [models.CheckConstraint(condition=models.Q(end__gt=models.F("start")), name="reservation_positive_interval")]
        indexes = [models.Index(fields=["equipment", "status", "start", "end"])]
