from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Equipment, Reservation
from .services import cancel_reservation, conflicts, review_reservation

class CancellationTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('owner')
        self.other = get_user_model().objects.create_superuser('reviewer', '', 'test-only')
        self.item = Equipment.objects.create(asset_tag='CANCEL-1', name='Laptop', category='Laptop')
        self.row = Reservation.objects.create(borrower=self.owner, equipment=self.item,
            start=timezone.now()+timedelta(days=1), end=timezone.now()+timedelta(days=1,hours=1))
        self.url = reverse('cancel_reservation', args=[self.row.pk])
        self.client.force_login(self.owner)

    def test_pending_owner_can_cancel_with_timestamp_and_history(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('my_reservations'))
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, 'cancelled')
        self.assertIsNotNone(self.row.cancelled_at)
        self.assertTrue(Reservation.objects.filter(pk=self.row.pk).exists())

    def test_approved_cancel_releases_availability_and_allows_competing_approval(self):
        review_reservation(self.other, self.row.pk, 'approved')
        self.assertTrue(conflicts(self.item,self.row.start,self.row.end).exists())
        cancel_reservation(self.owner,self.row.pk)
        self.assertFalse(conflicts(self.item,self.row.start,self.row.end).exists())
        self.row.refresh_from_db()
        self.assertEqual(self.row.reviewed_by,self.other)
        self.assertIsNotNone(self.row.reviewed_at)
        replacement=Reservation.objects.create(borrower=self.owner,equipment=self.item,start=self.row.start,end=self.row.end)
        review_reservation(self.other,replacement.pk,'approved')
        response=self.client.get(reverse('catalog'),{'start':timezone.localtime(self.row.start).strftime('%Y-%m-%dT%H:%M'),'end':timezone.localtime(self.row.end).strftime('%Y-%m-%dT%H:%M'),'q':'Laptop'})
        self.assertContains(response,'Unavailable')

    def test_other_user_even_superuser_cannot_cancel(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code,403)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status,'pending')

    def test_anonymous_redirect_and_inactive_service_denial(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code,302)
        self.owner.is_active=False
        with self.assertRaises(PermissionDenied): cancel_reservation(self.owner,self.row.pk)

    def test_get_and_missing_csrf_cannot_mutate(self):
        self.assertEqual(self.client.get(self.url).status_code,405)
        secure=Client(enforce_csrf_checks=True); secure.force_login(self.owner)
        self.assertEqual(secure.post(self.url).status_code,403)
        self.row.refresh_from_db(); self.assertEqual(self.row.status,'pending')

    def test_rejected_and_repeated_cancellation_are_rejected(self):
        self.row.status='rejected';self.row.save()
        with self.assertRaises(ValidationError): cancel_reservation(self.owner,self.row.pk)
        self.row.status='pending';self.row.save()
        cancel_reservation(self.owner,self.row.pk)
        with self.assertRaises(ValidationError): cancel_reservation(self.owner,self.row.pk)
        with self.assertRaises(ValidationError): review_reservation(self.other,self.row.pk,'approved')

    def test_started_reservation_is_retained(self):
        self.row.start=timezone.now()-timedelta(minutes=1);self.row.save()
        response=self.client.post(self.url,follow=True)
        self.assertContains(response,'have not started')
        self.row.refresh_from_db();self.assertEqual(self.row.status,'pending')

    def test_button_visible_only_for_eligible_reservations(self):
        self.assertContains(self.client.get(reverse('my_reservations')),'Cancel reservation')
        cancel_reservation(self.owner,self.row.pk)
        response=self.client.get(reverse('my_reservations'))
        self.assertNotContains(response,'Cancel reservation')
        self.assertContains(response,'Cancelled')

    def test_unknown_id_returns_404(self):
        self.assertEqual(self.client.post(reverse('cancel_reservation',args=[99999])).status_code,404)
