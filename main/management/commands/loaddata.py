import json
import os

from django.conf import settings
from django.core.management.commands.loaddata import Command as DjangoLoadDataCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import FitnessArticle


FITNESS_FIXTURE_NAME = "fitness_article_django_fixture.json"


def parse_fixture_datetime(value):
    if not value:
        return None
    parsed = parse_datetime(str(value))
    if parsed and timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


class Command(DjangoLoadDataCommand):
    def handle(self, *fixture_labels, **options):
        fitness_labels = [
            label for label in fixture_labels
            if os.path.basename(str(label)).lower() == FITNESS_FIXTURE_NAME
        ]
        passthrough_labels = [
            label for label in fixture_labels
            if os.path.basename(str(label)).lower() != FITNESS_FIXTURE_NAME
        ]

        installed = 0
        for label in fitness_labels:
            installed += self.load_fitness_articles_fixture(label, options.get("database"))

        if passthrough_labels:
            super().handle(*passthrough_labels, **options)

        if fitness_labels:
            fixture_word = "fixture" if len(fitness_labels) == 1 else "fixtures"
            self.stdout.write(f"Installed {installed} object(s) from {len(fitness_labels)} {fixture_word}(s)")

    def load_fitness_articles_fixture(self, label, database):
        fixture_path = self.resolve_fitness_fixture_path(label)
        with open(fixture_path, "r", encoding="utf-8") as fixture_file:
            records = json.load(fixture_file)

        manager = FitnessArticle.objects
        if database:
            manager = manager.using(database)

        installed = 0
        for record in records:
            fields = record.get("fields", record)
            code = fields.get("code")
            if not code:
                continue

            defaults = {
                "category": fields.get("category") or "Beginner",
                "title": fields.get("title") or code,
                "slug": fields.get("slug") or "",
                "featured_image_url": fields.get("featured_image_url") or "",
                "author": fields.get("author") or "RedIron Team",
                "overview": fields.get("overview") or "",
                "coreConcepts": fields.get("coreConcepts") or [],
                "whyItMatters": fields.get("whyItMatters") or [],
                "scienceExplained": fields.get("scienceExplained") or [],
                "practicalApplication": fields.get("practicalApplication") or [],
                "commonMyths": fields.get("commonMyths") or [],
                "coachInsight": fields.get("coachInsight") or "",
                "keyTakeaways": fields.get("keyTakeaways") or [],
                "videoTitle": fields.get("videoTitle") or "",
                "youtubeUrl": fields.get("youtubeUrl") or "",
                "relatedArticles": fields.get("relatedArticles") or [],
                "published_at": parse_fixture_datetime(fields.get("published_at")) or timezone.now(),
                "is_published": fields.get("is_published", True),
            }
            obj, _ = manager.update_or_create(code=code, defaults=defaults)

            timestamp_updates = {}
            created_at = parse_fixture_datetime(fields.get("created_at"))
            updated_at = parse_fixture_datetime(fields.get("updated_at"))
            if created_at:
                timestamp_updates["created_at"] = created_at
            if updated_at:
                timestamp_updates["updated_at"] = updated_at
            if timestamp_updates:
                manager.filter(pk=obj.pk).update(**timestamp_updates)

            installed += 1
        return installed

    def resolve_fitness_fixture_path(self, label):
        if os.path.isabs(label) and os.path.exists(label):
            return label

        candidate = os.path.abspath(label)
        if os.path.exists(candidate):
            return candidate

        main_fixture = os.path.join(settings.BASE_DIR, "main", "fixtures", FITNESS_FIXTURE_NAME)
        if os.path.exists(main_fixture):
            return main_fixture

        return label
