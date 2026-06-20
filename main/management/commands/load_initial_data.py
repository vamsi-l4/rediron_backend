from django.core.management.base import BaseCommand
from django.core.management import call_command
import os

class Command(BaseCommand):
    help = 'Loads core JSON fixtures safely and refreshes nutrition articles with new structured data'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🚀 REDIRON DATA LOADER - Automatic Deployment Update"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        self.stdout.write(self.style.WARNING("📦 Phase 1: Loading Master Database..."))
        exact_fixtures = [
            'main/fixtures/master_db.json'
        ]
        
        for fixture in exact_fixtures:
            if os.path.exists(fixture):
                self.stdout.write(f"  Loading: {fixture}...")
                try:
                    call_command('loaddata', fixture)
                    self.stdout.write(self.style.SUCCESS(f"  ✔ Success: {fixture}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✖ Error loading {fixture}: {str(e)}"))
                    self.stdout.write(self.style.WARNING("  Stopping to prevent messy database errors."))
                    return
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ Missing file (skipping): {fixture}"))

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("📚 Phase 2: Updating Premium Nutrition Articles..."))

        # Refresh NutritionArticle records after loading the master database fixture.
        # This replaces the legacy markdown-based nutrition articles with the
        # new structured JSON dataset from rediron_articles_complete_guide.json.
        try:
            self.stdout.write("Refreshing nutrition articles from rediron_articles_complete_guide.json...")
            call_command('refresh_nutrition_articles')
            self.stdout.write(self.style.SUCCESS("✔ Nutrition articles refreshed from structured fixture."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✖ Error refreshing nutrition articles: {str(e)}"))
            self.stdout.write(self.style.WARNING("Nutrition articles may still be stale if the refresh failed."))
            return

        self.stdout.write(self.style.SUCCESS("🎉 All specified data loaded perfectly!"))