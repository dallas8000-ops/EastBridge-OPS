from django.core.management.base import BaseCommand

from trade.services import sync_trade_procedures


class Command(BaseCommand):
    help = "Sync structured trade procedures from EAC Trade Information Portals."

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            action="append",
            dest="countries",
            help="ISO country code (UG, KE, TZ, RW). Repeatable.",
        )
        parser.add_argument(
            "--offline",
            action="store_true",
            help="Skip live portal fetch; load curated fallback procedures only (fast).",
        )

    def handle(self, *args, **options):
        countries = options.get("countries")
        offline = options.get("offline", False)
        if offline:
            self.stdout.write("Offline mode: loading curated procedures only.")
        result = sync_trade_procedures(country_codes=countries, offline=offline)
        self.stdout.write(
            self.style.SUCCESS(
                f"Trade procedures: {result['created']} created, {result['updated']} updated"
            )
        )
        if result.get("errors"):
            self.stdout.write(self.style.WARNING("Notes:"))
            for err in result["errors"]:
                self.stdout.write(f"  - {err}")
