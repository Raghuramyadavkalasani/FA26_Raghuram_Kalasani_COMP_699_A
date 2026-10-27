from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connections, IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Equipment, Reservation
from .services import request_reservation, review_reservation, conflicts

class ReservationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('borrower', password='synthetic-test-only')
        self.other = User.objects.create_user('other')
        self.reviewer = User.objects.create_user('reviewer', is_staff=True)
        self.reviewer.user_permissions.add(Permission.objects.get(codename='review_reservation'))
        self.item = Equipment.objects.create(asset_tag='TEST-1', name='Laptop', category='Computers')
        self.start = timezone.now() + timedelta(days=2)
        self.end = self.start + timedelta(hours=1)

    def make(self, **kwargs):
        return request_reservation(kwargs.get('user', self.user), kwargs.get('item', self.item.pk), kwargs.get('start', self.start), kwargs.get('end', self.end))

    def test_valid_request_persists_owner_and_pending(self):
        r=self.make(); r.refresh_from_db()
        self.assertEqual((r.borrower_id,r.status,r.equipment_id),(self.user.pk,'pending',self.item.pk))

    def test_invalid_intervals_do_not_write(self):
        for start,end in [(self.start,self.start),(self.end,self.start),(timezone.now()-timedelta(hours=1),self.end)]:
            with self.assertRaises(ValidationError): self.make(start=start,end=end)
        self.assertEqual(Reservation.objects.count(),0)

    def test_inactive_equipment_rejected(self):
        self.item.is_active=False;self.item.save()
        with self.assertRaises(ValidationError): self.make()

    def test_database_rejects_reversed_interval(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(equipment=self.item,borrower=self.user,start=self.end,end=self.start)

    def test_pending_does_not_block_and_boundary_does_not_overlap(self):
        r=self.make()
        self.assertFalse(conflicts(self.item,self.start,self.end).exists())
        review_reservation(self.reviewer,r.pk,'approved')
        self.assertTrue(conflicts(self.item,self.start,self.end).exists())
        self.assertFalse(conflicts(self.item,self.end,self.end+timedelta(hours=1)).exists())
        adjacent=self.make(start=self.end,end=self.end+timedelta(hours=1))
        review_reservation(self.reviewer,adjacent.pk,'approved')

    def test_overlap_rollback_and_different_item_allowed(self):
        a=self.make();b=self.make()
        review_reservation(self.reviewer,a.pk,'approved')
        with self.assertRaises(ValidationError):review_reservation(self.reviewer,b.pk,'approved')
        b.refresh_from_db();self.assertEqual(b.status,'pending');self.assertIsNone(b.reviewed_by)
        other=Equipment.objects.create(asset_tag='TEST-2',name='Other',category='Computers')
        c=self.make(item=other.pk);review_reservation(self.reviewer,c.pk,'approved')

    def test_reject_and_repeated_decision(self):
        r=self.make();review_reservation(self.reviewer,r.pk,'rejected')
        self.assertFalse(conflicts(self.item,self.start,self.end).exists())
        with self.assertRaises(ValidationError):review_reservation(self.reviewer,r.pk,'approved')

    def test_approval_rechecks_retirement_and_time(self):
        r=self.make();self.item.is_active=False;self.item.save()
        with self.assertRaises(ValidationError):review_reservation(self.reviewer,r.pk,'approved')
        self.item.is_active=True;self.item.save()
        Reservation.objects.filter(pk=r.pk).update(start=timezone.now()-timedelta(hours=1))
        with self.assertRaises(ValidationError):review_reservation(self.reviewer,r.pk,'approved')

    def test_borrower_and_unprivileged_staff_denied(self):
        r=self.make()
        for u in [self.user,get_user_model().objects.create_user('staff',is_staff=True)]:
            with self.assertRaises(PermissionDenied):review_reservation(u,r.pk,'approved')
            self.client.force_login(u)
            self.assertEqual(self.client.post(reverse('decide',args=[r.pk]),{'decision':'approved'}).status_code,403)
        r.refresh_from_db();self.assertEqual(r.status,'pending')

    def test_ownership_and_forged_owner(self):
        other=self.make(user=self.other)
        self.client.force_login(self.user)
        response=self.client.post(reverse('reserve',args=[self.item.pk]),{'start':self.start.isoformat(),'end':self.end.isoformat(),'borrower':self.other.pk,'status':'approved'})
        self.assertEqual(response.status_code,302)
        mine=Reservation.objects.exclude(pk=other.pk).get()
        self.assertEqual(mine.borrower_id,self.user.pk);self.assertEqual(mine.status,'pending')
        self.assertEqual(list(self.client.get(reverse('my_reservations')).context['rows']),[mine])

    def test_login_logout_invalid_credentials_and_anonymous(self):
        self.assertEqual(self.client.get('/').status_code,302)
        self.assertContains(self.client.post(reverse('login'),{'username':'borrower','password':'wrong'}),'Please enter a correct')
        self.assertTrue(self.client.login(username='borrower',password='synthetic-test-only'))
        self.assertEqual(self.client.get('/').status_code,200)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get('/').status_code,302)

    def test_search_availability_and_invalid_time(self):
        r=self.make();review_reservation(self.reviewer,r.pk,'approved')
        Equipment.objects.create(asset_tag='OFF',name='Hidden',category='Computers',is_active=False)
        self.client.force_login(self.user)
        response=self.client.get('/',{'q':'computers','start':self.start.isoformat(),'end':self.end.isoformat()})
        self.assertContains(response,'Unavailable');self.assertNotContains(response,'Hidden')
        response=self.client.get('/',{'q':'nothing','start':self.start.isoformat(),'end':self.end.isoformat()})
        self.assertContains(response,'No equipment to display')
        self.assertContains(self.client.get('/',{'start':'bad','end':'bad'}),'Enter a valid date/time')

    def test_csrf_and_get_cannot_mutate(self):
        r=self.make();client=Client(enforce_csrf_checks=True);client.force_login(self.reviewer)
        self.assertEqual(client.post(reverse('decide',args=[r.pk]),{'decision':'approved'}).status_code,403)
        self.assertEqual(client.get(reverse('decide',args=[r.pk])).status_code,405)
        r.refresh_from_db();self.assertEqual(r.status,'pending')

    def test_integrated_workflow_valid_and_invalid(self):
        self.client.force_login(self.user)
        invalid=self.client.post(reverse('reserve',args=[self.item.pk]),{'start':self.end.isoformat(),'end':self.start.isoformat()})
        self.assertContains(invalid,'End must be later');self.assertEqual(Reservation.objects.count(),0)
        valid=self.client.post(reverse('reserve',args=[self.item.pk]),{'start':self.start.isoformat(),'end':self.end.isoformat()},follow=True)
        self.assertContains(valid,'Pending');r=Reservation.objects.get()
        self.client.force_login(self.reviewer)
        result=self.client.post(reverse('decide',args=[r.pk]),{'decision':'approved'},follow=True)
        self.assertContains(result,'Reservation decision saved')
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('my_reservations')),'Approved')
        self.assertContains(self.client.get('/',{'start':self.start.isoformat(),'end':self.end.isoformat()}),'Unavailable')
        r.refresh_from_db();self.assertEqual(r.reviewed_by_id,self.reviewer.pk)

class ConcurrentApprovalTests(TransactionTestCase):
    def test_two_connections_approve_at_most_one(self):
        # File-backed SQLite is required; shared in-memory SQLite has different lock behavior.
        self.assertNotIn('memory',str(connections['default'].settings_dict['NAME']))
        user=get_user_model().objects.create_superuser('concurrent-admin')
        item=Equipment.objects.create(asset_tag='RACE',name='Race item',category='Test')
        start=timezone.now()+timedelta(days=3);end=start+timedelta(hours=1)
        for _ in range(10):
            Reservation.objects.all().delete()
            rows=[request_reservation(user,item.pk,start,end) for n in range(2)]
            barrier=Barrier(2)
            def attempt(pk):
                connections.close_all()
                actor=get_user_model().objects.get(pk=user.pk)
                barrier.wait(timeout=10)
                try:
                    review_reservation(actor,pk,'approved')
                    return 'approved'
                except ValidationError:
                    return 'conflict'
                finally:
                    connections.close_all()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(attempt,[r.pk for r in rows]))
            self.assertCountEqual(results,['approved','conflict'])
            self.assertEqual(Reservation.objects.filter(status='approved').count(),1)
