from django.core.management.base import BaseCommand

from ingestion.fetchers.world_bank import fetch_world_bank_indicators
from ingestion.services.indexer import run_regulatory_ingestion, run_source_ingestion
from core.models import DataSource


class Command(BaseCommand):
    help = "Run data ingestion for regulatory sources and/or economic indicators."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=["all", "regulatory", "economic", "source"],
            default="all",
            help="Which ingestion pipeline to run.",
        )
        parser.add_argument(
            "--source-id",
            type=int,
            help="Run a single DataSource by ID (use with --target source).",
        )

    def handle(self, *args, **options):
        target = options["target"]

        if target in ("all", "regulatory"):
            self.stdout.write("Running regulatory ingestion...")
            run = run_regulatory_ingestion()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Regulatory: {run.items_new} new, {run.items_failed} failed, "
                    f"{run.items_fetched} fetched"
                )
            )

        if target in ("all", "economic"):
            self.stdout.write("Syncing World Bank indicators...")
            result = fetch_world_bank_indicators()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Economic: {result.get('created', 0)} created, "
                    f"{result.get('updated', 0)} updated"
                )
            )

        if target == "source":
            source_id = options.get("source_id")
            if not source_id:
                self.stderr.write("--source-id required for --target source")
                return
            source = DataSource.objects.get(pk=source_id)
            result = run_source_ingestion(source)
            self.stdout.write(self.style.SUCCESS(str(result)))
