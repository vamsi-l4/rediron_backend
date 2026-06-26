import json
from collections import OrderedDict
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction


class Command(BaseCommand):
    help = "Import the RedIron all_data.json fixture model-by-model."

    def add_arguments(self, parser):
        parser.add_argument(
            "fixture",
            nargs="?",
            default="main/fixtures/all_data.json",
            help="Fixture path. Defaults to main/fixtures/all_data.json.",
        )
        parser.add_argument(
            "--only",
            action="append",
            default=[],
            help="Import only a model label, e.g. --only main.musclegroup. Can be repeated.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database alias to import into.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"])
        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        with fixture_path.open("r", encoding="utf-8") as fixture_file:
            records = json.load(fixture_file)

        only = {label.lower() for label in options["only"]}
        grouped = OrderedDict()
        for record in records:
            model_label = record.get("model", "").lower()
            if only and model_label not in only:
                continue
            grouped.setdefault(model_label, []).append(record)

        if not grouped:
            raise CommandError("No matching records found in fixture.")

        database = options["database"]
        connection = connections[database]
        total = 0

        with connection.constraint_checks_disabled():
            for model_label, model_records in grouped.items():
                imported = 0
                self.stdout.write(f"Importing {model_label}: {len(model_records)} object(s)")
                with transaction.atomic(using=database):
                    for record in model_records:
                        payload = json.dumps([record], ensure_ascii=False)
                        try:
                            for deserialized in serializers.deserialize(
                                "json",
                                payload,
                                ignorenonexistent=True,
                                handle_forward_references=True,
                            ):
                                deserialized.save(using=database)
                                imported += 1
                        except Exception as exc:
                            pk = record.get("pk", "natural")
                            raise CommandError(f"Failed importing {model_label}(pk={pk}): {exc}") from exc

                total += imported
                self.stdout.write(self.style.SUCCESS(f"Imported {model_label}: {imported}"))

        self.stdout.write(self.style.SUCCESS(f"Imported {total} object(s) from {fixture_path}"))
