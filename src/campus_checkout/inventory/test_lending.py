from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Equipment, Reservation
from .services import checkout_reservation, return_reservation, request_reservation, review_reservation, cancel_reservation, conflicts

class LendingTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.borrower=User.objects.create_user('borrower')
        self.staff=User.objects.create_user('staff',is_staff=True)
        self.operator=User.objects.create_user('operator')
        self.operator.user_permissions.add(Permission.objects.get(codename='manage_lending'),Permission.objects.get(codename='review_reservation'))
        self.item=Equipment.objects.create(asset_tag='LOAN-1',name='Laptop',category='Laptop')
        self.now=timezone.now()
        self.row=Reservation.objects.create(borrower=self.borrower,equipment=self.item,status='approved',start=self.now-timedelta(minutes=1),end=self.now+timedelta(hours=1))
        self.client.force_login(self.operator)
        self.url=reverse('lending_action',args=[self.row.pk])

    def test_request_approve_checkout_return_workflow(self):
        self.row.delete()
        start=self.now+timedelta(hours=1);end=start+timedelta(hours=1)
        row=request_reservation(self.borrower,self.item.pk,start,end)
        review_reservation(self.operator,row.pk,'approved')
        url=reverse('lending_action',args=[row.pk])
        with patch('django.utils.timezone.now',return_value=start):
            self.assertContains(self.client.get(reverse('lending_queue')),'Record checkout')
            self.assertRedirects(self.client.post(url,{'action':'checkout'}),reverse('lending_queue'))
        row.refresh_from_db()
        self.assertEqual(row.status,'checked_out');self.assertEqual(row.checked_out_by,self.operator)
        self.assertEqual(row.checked_out_at,start);self.assertEqual(row.end,end)
        self.assertTrue(conflicts(self.item,end+timedelta(days=1),end+timedelta(days=2)).exists())
        self.assertContains(self.client.get(reverse('lending_queue')),'Record return')
        self.client.post(url,{'action':'return'})
        row.refresh_from_db()
        self.assertEqual(row.status,'returned');self.assertEqual(row.returned_by,self.operator)
        self.assertIsNotNone(row.returned_at);self.assertEqual(row.reviewed_by,self.operator)
        self.assertFalse(conflicts(self.item,start,end).exists())
        self.client.force_login(self.borrower)
        self.assertContains(self.client.get(reverse('my_reservations')),'Returned')

    def test_permission_denied_for_borrower_and_staff_without_permission(self):
        for user in (self.borrower,self.staff):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('lending_queue')).status_code,403)
            for action in ('checkout','return'):
                self.assertEqual(self.client.post(self.url,{'action':action}).status_code,403)
            with self.assertRaises(PermissionDenied): checkout_reservation(user,self.row.pk)
            with self.assertRaises(PermissionDenied): return_reservation(user,self.row.pk)
        self.row.refresh_from_db();self.assertEqual(self.row.status,'approved')

    def test_post_csrf_and_auth_required(self):
        self.assertEqual(self.client.get(self.url).status_code,405)
        client=Client(enforce_csrf_checks=True);client.force_login(self.operator)
        self.assertEqual(client.post(self.url,{'action':'checkout'}).status_code,403)
        self.client.logout();self.assertEqual(self.client.post(self.url,{'action':'checkout'}).status_code,302)
        self.operator.is_active=False
        with self.assertRaises(PermissionDenied): checkout_reservation(self.operator,self.row.pk)

    def test_only_approved_status_can_checkout(self):
        for status in ('pending','rejected','cancelled','returned','checked_out'):
            self.row.status=status;self.row.save()
            with self.assertRaises(ValidationError): checkout_reservation(self.operator,self.row.pk)

    def test_checkout_time_boundaries_and_inactive_equipment(self):
        for moment in (self.row.start-timedelta(seconds=1),self.row.end):
            with patch('django.utils.timezone.now',return_value=moment):
                with self.assertRaises(ValidationError): checkout_reservation(self.operator,self.row.pk)
        self.item.is_active=False;self.item.save()
        with self.assertRaises(ValidationError): checkout_reservation(self.operator,self.row.pk)

    def test_duplicate_checkout_return_and_cancellation_rejected(self):
        checkout_reservation(self.operator,self.row.pk)
        with self.assertRaises(ValidationError): checkout_reservation(self.operator,self.row.pk)
        with self.assertRaises(ValidationError): cancel_reservation(self.borrower,self.row.pk)
        return_reservation(self.operator,self.row.pk)
        with self.assertRaises(ValidationError): return_reservation(self.operator,self.row.pk)

    def test_overdue_open_checkout_blocks_next_until_return(self):
        old=Reservation.objects.create(borrower=self.borrower,equipment=self.item,status='checked_out',start=self.now-timedelta(days=2),end=self.now-timedelta(days=1),checked_out_at=self.now-timedelta(days=2),checked_out_by=self.operator)
        with self.assertRaises(ValidationError): checkout_reservation(self.operator,self.row.pk)
        return_reservation(self.operator,old.pk)
        checkout_reservation(self.operator,self.row.pk)
        self.row.refresh_from_db();self.assertEqual(self.row.status,'checked_out')

    def test_database_prevents_two_open_checkouts(self):
        checkout_reservation(self.operator,self.row.pk)
        with self.assertRaises(IntegrityError),transaction.atomic():
            Reservation.objects.create(borrower=self.borrower,equipment=self.item,status='checked_out',start=self.now,end=self.now+timedelta(hours=2))

    def test_return_allowed_after_equipment_retired(self):
        checkout_reservation(self.operator,self.row.pk)
        self.item.is_active=False;self.item.save()
        return_reservation(self.operator,self.row.pk)
        self.row.refresh_from_db();self.assertEqual(self.row.status,'returned')

    def test_invalid_action_missing_record_and_return_before_checkout(self):
        self.assertEqual(self.client.post(reverse('lending_action',args=[99999]),{'action':'checkout'}).status_code,404)
        self.assertContains(self.client.post(self.url,{'action':'invalid'},follow=True),'Choose checkout or return')
        with self.assertRaises(ValidationError): return_reservation(self.operator,self.row.pk)
        self.row.refresh_from_db();self.assertEqual(self.row.status,'approved')
