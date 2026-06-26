from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export RedIron admin data into one fixture for PostgreSQL migration."

    DEFAULT_APPS = [
        "accounts",
        "main",
        "rediron_shop",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="main/fixtures/all_data.json",
            help="Output fixture path. Defaults to main/fixtures/all_data.json.",
        )
        parser.add_argument(
            "--indent",
            type=int,
            default=2,
            help="JSON indentation. Defaults to 2.",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as output:
            call_command(
                "dumpdata",
                *self.DEFAULT_APPS,
                stdout=output,
                indent=options["indent"],
                natural_foreign=True,
                natural_primary=True,
                exclude=[
                    "contenttypes",
                    "auth.permission",
                    "sessions.session",
                    "admin.logentry",
                ],
            )

        self.stdout.write(self.style.SUCCESS(f"Exported RedIron data to {output_path}"))
