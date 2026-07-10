import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import CustomUser, PaymentTransaction


class Command(BaseCommand):
    help = 'Find local users deleted in Clerk and remove their related RedIron data.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true', help='Delete matches. Defaults to a dry run.')

    def handle(self, *args, **options):
        secret = getattr(settings, 'CLERK_SECRET_KEY', '')
        if not secret:
            raise CommandError('CLERK_SECRET_KEY must be configured.')

        stale_users = []
        for user in CustomUser.objects.exclude(clerk_user_id__isnull=True).exclude(clerk_user_id='').iterator():
            response = requests.get(
                f'https://api.clerk.com/v1/users/{user.clerk_user_id}',
                headers={'Authorization': f'Bearer {secret}'},
                timeout=5,
            )
            if response.status_code == 404:
                stale_users.append(user)
                self.stdout.write(f'Stale: {user.id} {user.email} ({user.clerk_user_id})')
            elif not response.ok:
                raise CommandError(f'Clerk lookup failed for {user.clerk_user_id}: HTTP {response.status_code}')

        if not stale_users:
            self.stdout.write(self.style.SUCCESS('No deleted Clerk users found.'))
            return
        if not options['execute']:
            self.stdout.write(self.style.WARNING(
                f'Dry run: {len(stale_users)} local users would be deleted. Run again with --execute to confirm.'
            ))
            return

        with transaction.atomic():
            for user in stale_users:
                PaymentTransaction.objects.filter(user=user).delete()
                user.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {len(stale_users)} local users and their related data.'))
