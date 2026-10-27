from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from .models import Equipment


class InventoryTests(TestCase):
    def setUp(self):
        self.item = Equipment.objects.create(asset_tag="LAP-001", name="Demo laptop", category="Laptop")

    def test_duplicate_asset_tag_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Equipment.objects.create(asset_tag="LAP-001", name="Other", category="Laptop")

    def test_invalid_asset_tag_rejected(self):
        self.item.asset_tag = "bad tag"
        with self.assertRaises(ValidationError):
            self.item.full_clean()

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse("admin:inventory_equipment_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_regular_user_cannot_add_equipment(self):
        user = get_user_model().objects.create_user(username="borrower")
        self.client.force_login(user)
        response = self.client.post(reverse("admin:inventory_equipment_add"), {
            "asset_tag": "LAP-002", "name": "Blocked", "category": "Laptop", "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Equipment.objects.filter(asset_tag="LAP-002").exists())

    def test_staff_without_permissions_cannot_add_equipment(self):
        user = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:inventory_equipment_add")).status_code, 403)

    def test_admin_can_create_edit_and_retire_equipment(self):
        user = get_user_model().objects.create_superuser(username="admin", password="test-only-password")
        self.client.force_login(user)
        response = self.client.post(reverse("admin:inventory_equipment_add"), {
            "asset_tag": "PROJ-001", "name": "Demo projector", "category": "Projector", "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        item = Equipment.objects.get(asset_tag="PROJ-001")
        response = self.client.post(reverse("admin:inventory_equipment_change", args=[item.pk]), {
            "asset_tag": item.asset_tag, "name": "Retired projector", "category": item.category,
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertFalse(item.is_active)
        self.assertEqual(item.name, "Retired projector")
        self.assertEqual(self.client.post(reverse("admin:inventory_equipment_delete", args=[item.pk])).status_code, 403)
        self.assertTrue(Equipment.objects.filter(pk=item.pk).exists())
