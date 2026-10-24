"""Simple test command for all regional legal sources configuration."""

from django.core.management.base import BaseCommand
from core.models import DataSource


class Command(BaseCommand):
    help = "Test all regional legal sources configuration"

    def handle(self, *args, **options):
        self.stdout.write("Testing All Regional Legal Sources Configuration")
        self.stdout.write("-" * 60)

        # Check all data sources by country
        countries = ["UG", "KE", "RW", "TZ"]
        
        for country_code in countries:
            country_sources = DataSource.objects.filter(
                is_active=True,
                country__code=country_code
            )
            
            if country_sources.exists():
                self.stdout.write(f"\n[OK] {country_code} - Found {country_sources.count()} sources:")
                
                for source in country_sources:
                    self.stdout.write(f"  - {source.name} ({source.source_type})")
            else:
                self.stdout.write(f"\n[INFO] {country_code} - No active sources configured")

        # Source type breakdown by country
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write("Detailed Source Configuration:")
        
        for country_code in countries:
            country_sources = DataSource.objects.filter(
                is_active=True,
                country__code=country_code
            )
            
            if country_sources.exists():
                self.stdout.write(f"\n{country_code} Sources:")
                
                for source in country_sources:
                    self.stdout.write(f"\n  [OK] {source.name}")
                    self.stdout.write(f"    Type: {source.source_type}")
                    self.stdout.write(f"    URL: {source.url}")
                    self.stdout.write(f"    Ingestion: {source.ingestion_config.get('type', 'N/A')}")
                    self.stdout.write(f"    Max Items: {source.ingestion_config.get('max_items', 'N/A')}")
                    self.stdout.write(f"    Last Checked: {source.last_checked_at or 'Never'}")

        # Total summary
        total_sources = DataSource.objects.filter(is_active=True).count()
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(f"Total Active Sources: {total_sources}")
        
        # Source type breakdown
        all_sources = DataSource.objects.filter(is_active=True)
        source_types = {}
        for source in all_sources:
            stype = source.source_type
            if stype not in source_types:
                source_types[stype] = 0
            source_types[stype] += 1
        
        self.stdout.write("Source Type Breakdown:")
        for stype, count in source_types.items():
            self.stdout.write(f"  {stype}: {count}")

        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(self.style.SUCCESS("Configuration test completed successfully!"))