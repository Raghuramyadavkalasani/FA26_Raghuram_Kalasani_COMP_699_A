import json
from datetime import timedelta
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client, override_settings
from django.utils import timezone
from inventory.models import Equipment, Reservation

class Command(BaseCommand):
    help='Run a synthetic HTTP workflow against the configured database; creates fresh demo records.'
    def handle(self,*args,**options):
        suffix=uuid4().hex[:8];User=get_user_model()
        borrower=User.objects.create_user('evidence-'+suffix)
        reviewer=User.objects.create_superuser('review-'+suffix)
        item=Equipment.objects.create(asset_tag='EVID-'+suffix.upper(),name='Evidence laptop',category='Laptop')
        start=timezone.now()+timedelta(days=2);end=start+timedelta(hours=1)
        client=Client()
        with override_settings(ALLOWED_HOSTS=['testserver','localhost','127.0.0.1']):
            client.force_login(borrower)
            invalid=client.post(f'/equipment/{item.pk}/reserve/',{'start':end.isoformat(),'end':start.isoformat()})
            assert invalid.status_code==200 and b'End must be later' in invalid.content
            assert not Reservation.objects.filter(equipment=item).exists()
            valid=client.post(f'/equipment/{item.pk}/reserve/',{'start':start.isoformat(),'end':end.isoformat()})
            assert valid.status_code==302
            row=Reservation.objects.get(equipment=item);assert row.status=='pending'
            denied=client.post(f'/review/{row.pk}/',{'decision':'approved'})
            assert denied.status_code==403
            client.force_login(reviewer)
            approved=client.post(f'/review/{row.pk}/',{'decision':'approved'})
            assert approved.status_code==302
            row.refresh_from_db();assert row.status=='approved'
            client.force_login(borrower)
            status=client.get('/reservations/');assert b'Approved' in status.content
            availability=client.get('/',{'q':'Evidence laptop','start':start.isoformat(),'end':end.isoformat()})
            assert b'Unavailable' in availability.content
        self.stdout.write(json.dumps({'runner':'assistant or whoever invokes this command','reservation_id':row.pk,'equipment':item.asset_tag,'invalid_input_http':invalid.status_code,'invalid_input_created_records':0,'valid_request_http':valid.status_code,'borrower_approval_http':denied.status_code,'reviewer_approval_http':approved.status_code,'stored_status':row.status,'reviewer_recorded':row.reviewed_by_id==reviewer.pk,'borrower_page':'Approved','availability':'Unavailable','start':start.isoformat(),'end':end.isoformat()},indent=2))
