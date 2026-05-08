from django.core.management.base import BaseCommand
from django.core.management import call_command
import os

class Command(BaseCommand):
    help = 'Loads core JSON fixtures safely in the exact required order'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting strict data sync...")
        
        # EXACT FILES ONLY: No auto-discovery, no messy duplicates.
        # Just add any new files to this list in the exact order you want them loaded.
        exact_fixtures = [
            'main/fixtures/seed_data.json',
            'main/fixtures/equipment.json',
            'rediron_shop/fixtures/equipment_products_clean.json'
        ]
        
        for fixture in exact_fixtures:
            if os.path.exists(fixture):
                self.stdout.write(f"Loading file: {fixture}...")
                try:
                    call_command('loaddata', fixture)
                    self.stdout.write(self.style.SUCCESS(f"✔ Success: {fixture}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✖ Error loading {fixture}: {str(e)}"))
                    self.stdout.write(self.style.WARNING("Stopping to prevent messy database errors."))
                    return
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Missing file (skipping): {fixture}"))
                
        self.stdout.write(self.style.SUCCESS("🎉 All specified data loaded perfectly!"))