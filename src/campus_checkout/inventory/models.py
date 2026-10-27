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
