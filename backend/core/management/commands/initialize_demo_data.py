"""Initialize the committed EastBridge demo dataset when production is empty."""

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import Organization
from assistant.models import EvidenceDocument
from core.models import Country, DataSource
from intelligence.models import EconomicIndicator
from playbooks.models import Industry
from regulatory.models import RegulatoryChange
from trade.models import TradeProcedure
from vendors.models import Vendor


class Command(BaseCommand):
    help = "Load and verify the committed demo dataset only when required records are missing."

    def _counts(self) -> dict[str, int]:
        return {
            "countries": Country.objects.count(),
            "industries": Industry.objects.count(),
            "active_sources": DataSource.objects.filter(is_active=True).count(),
            "organizations": Organization.objects.count(),
            "vendors": Vendor.objects.count(),
            "demo_users": User.objects.filter(username="demo").count(),
            "regulatory_changes": RegulatoryChange.objects.count(),
            "economic_indicators": EconomicIndicator.objects.count(),
            "trade_procedures": TradeProcedure.objects.count(),
            "embedded_evidence": EvidenceDocument.objects.exclude(embedding__isnull=True).count(),
        }

    def _has_required_data(self) -> bool:
        counts = self._counts()
        minimums = {
            "countries": 6,
            "industries": 5,
            "active_sources": 7,
            "organizations": 2,
            "vendors": 4,
            "demo_users": 1,
            "regulatory_changes": 1,
            "economic_indicators": 1,
            "trade_procedures": 1,
            "embedded_evidence": 1,
        }
        return all(counts[name] >= minimum for name, minimum in minimums.items())

    def handle(self, *args, **options):
        before = self._counts()
        self.stdout.write(f"EastBridge dataset before initialization: {before}")

        if not self._has_required_data():
            self.stdout.write("Required demo data is missing; loading committed fixtures.")
            call_command("load_initial_data")
            call_command("embed_evidence", force=True)
        else:
            self.stdout.write("Required demo data already exists; skipping fixture reload.")

        call_command("verify_data")
        self.stdout.write(
            self.style.SUCCESS(f"EastBridge dataset ready: {self._counts()}")
        )