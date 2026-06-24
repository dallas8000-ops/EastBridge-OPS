"""Verify production/demo dataset after Railway seed commands."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from assistant.models import EvidenceDocument
from core.models import Country, DataSource
from intelligence.models import EconomicIndicator
from playbooks.models import Industry
from regulatory.models import RegulatoryChange
from trade.models import TradeProcedure
from vendors.models import Vendor

from accounts.models import Organization


class Command(BaseCommand):
    help = "Report dataset counts and pass/fail against expected minimums after seeding."

    def handle(self, *args, **options):
        checks: list[tuple[str, int, int, str]] = [
            ("Countries (EAC + SS)", Country.objects.count(), 6, "seed_data"),
            ("Industries", Industry.objects.count(), 5, "seed_data"),
            ("Active data sources", DataSource.objects.filter(is_active=True).count(), 7, "seed_data"),
            ("Organizations", Organization.objects.count(), 2, "seed_demo_org"),
            ("Vendors", Vendor.objects.count(), 4, "seed_demo_org"),
            ("Demo user (demo)", User.objects.filter(username="demo").count(), 1, "seed_demo_org"),
            ("Regulatory changes", RegulatoryChange.objects.count(), 1, "ingest --target all"),
            ("Economic indicators", EconomicIndicator.objects.count(), 1, "ingest --target all"),
            ("Trade procedures", TradeProcedure.objects.count(), 1, "sync_trade_procedures --offline"),
            (
                "Evidence docs (embedded)",
                EvidenceDocument.objects.exclude(embedding__isnull=True).count(),
                1,
                "embed_evidence --force",
            ),
        ]

        failed = 0
        self.stdout.write("EastBridge data verification\n")
        for label, count, minimum, command in checks:
            ok = count >= minimum
            if not ok:
                failed += 1
            status = self.style.SUCCESS("OK") if ok else self.style.ERROR("MISSING")
            self.stdout.write(f"  [{status}] {label}: {count} (need >= {minimum}) — {command}")

        if failed:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{failed} check(s) failed. Run the full seed sequence in deploy/DATA-SEED.md"
                )
            )
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("\nAll data checks passed."))
