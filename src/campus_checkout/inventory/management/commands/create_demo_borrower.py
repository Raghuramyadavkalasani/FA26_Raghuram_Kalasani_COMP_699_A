from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from inventory.models import Equipment

class Command(BaseCommand):
    help = 'Create a fictional borrower with a password you enter, and one demo item.'
    def handle(self, *args, **options):
        User=get_user_model()
        if User.objects.filter(username='demo-borrower').exists():
            raise CommandError('demo-borrower already exists; use changepassword demo-borrower if needed.')
        password=getpass('Choose demo-borrower password: ')
        if password != getpass('Confirm password: '):
            raise CommandError('Passwords do not match.')
        user=User(username='demo-borrower')
        try: validate_password(password,user)
        except ValidationError as exc: raise CommandError('; '.join(exc.messages))
        user.set_password(password);user.save()
        Equipment.objects.get_or_create(asset_tag='DEMO-LAP-001',defaults={'name':'Demo laptop','category':'Laptop','description':'Fictional classroom equipment'})
        self.stdout.write(self.style.SUCCESS('Created demo-borrower and ensured demo equipment exists.'))
