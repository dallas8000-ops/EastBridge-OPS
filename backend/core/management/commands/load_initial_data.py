"""Load committed JSON fixtures — data files shipped in the GitHub zip."""

from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load initial data from backend/fixtures/*.json (visible in the repo zip)."

    def handle(self, *args, **options):
        fixtures_dir = Path(__file__).resolve().parents[3] / "fixtures"
        files = sorted(fixtures_dir.glob("initial_*.json"))
        if not files:
            self.stderr.write("No backend/fixtures/initial_*.json files found.")
            return

        for path in files:
            self.stdout.write(f"Loading {path.name}...")
            call_command("loaddata", str(path))

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(files)} fixture file(s)."))
