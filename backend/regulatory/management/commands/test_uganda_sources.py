"""Test command for Uganda legal sources and monitoring system."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import DataSource
from ingestion.services import indexer
from regulatory.services.change_detection import (
    detect_urgent_changes,
    analyze_regulatory_trends,
    generate_change_summary,
)


class Command(BaseCommand):
    help = "Test Uganda legal sources and monitoring system"

    def handle(self, *args, **options):
        self.stdout.write("Testing Uganda Legal Sources and Monitoring System")
        self.stdout.write("-" * 60)

        # Test 1: Check Uganda data sources
        self.stdout.write("\n1. Checking Uganda Data Sources:")
        uganda_sources = DataSource.objects.filter(
            is_active=True,
            country__code="UG"
        )
        
        for source in uganda_sources:
            self.stdout.write(f"   [OK] {source.name} ({source.source_type})")
            self.stdout.write(f"     URL: {source.url}")
            self.stdout.write(f"     Last checked: {source.last_checked_at}")
            self.stdout.write(f"     Config: {source.ingestion_config}")

        # Test 2: Test ingestion for each source
        self.stdout.write("\n2. Testing Ingestion for Uganda Sources:")
        test_results = []
        
        for source in uganda_sources:
            self.stdout.write(f"\n   Testing {source.name}...")
            try:
                result = indexer.run_source_ingestion(source)
                test_results.append({
                    "source": source.name,
                    "success": True,
                    "fetched": result.get("fetched", 0),
                    "indexed": result.get("indexed", 0),
                    "failed": result.get("failed", 0),
                })
                self.stdout.write(
                    f"   [OK] Fetched: {result.get('fetched', 0)}, "
                    f"Indexed: {result.get('indexed', 0)}, "
                    f"Failed: {result.get('failed', 0)}"
                )
            except Exception as e:
                test_results.append({
                    "source": source.name,
                    "success": False,
                    "error": str(e),
                })
                self.stdout.write(f"   [FAIL] Failed: {str(e)}")

        # Test 3: Check for urgent changes
        self.stdout.write("\n3. Checking for Urgent Regulatory Changes:")
        urgent_changes = detect_urgent_changes(hours=48)
        
        if urgent_changes:
            self.stdout.write(f"   Found {len(urgent_changes)} urgent changes:")
            for change in urgent_changes:
                self.stdout.write(f"   - {change.title}")
                self.stdout.write(f"     Risk: {change.risk_level}, Country: {change.country.code}")
        else:
            self.stdout.write("   No urgent changes found in the last 48 hours")

        # Test 4: Analyze regulatory trends
        self.stdout.write("\n4. Analyzing Regulatory Trends (30 days):")
        trends = analyze_regulatory_trends(days=30)
        
        self.stdout.write(f"   Total changes: {trends['total_changes']}")
        self.stdout.write("   Category breakdown:")
        for category, count in trends['category_breakdown'].items():
            self.stdout.write(f"     - {category}: {count}")
        
        self.stdout.write("   Risk level breakdown:")
        for risk, count in trends['risk_breakdown'].items():
            self.stdout.write(f"     - {risk}: {count}")

        # Test 5: Test change detection on recent changes
        self.stdout.write("\n5. Testing Change Detection:")
        from regulatory.models import RegulatoryChange
        
        recent_changes = RegulatoryChange.objects.filter(
            country__code="UG"
        ).order_by('-detected_at')[:3]
        
        for change in recent_changes:
            self.stdout.write(f"\n   Analyzing: {change.title}")
            try:
                summary = generate_change_summary(change)
                self.stdout.write(f"   Urgency factors: {summary['urgency_factors']}")
                self.stdout.write(f"   Related changes: {len(summary['related_changes'])}")
                self.stdout.write(f"   Recommendations: {len(summary['recommended_actions'])}")
                
                # Show stakeholder impact
                self.stdout.write("   Stakeholder impact:")
                for stakeholder, level in summary['stakeholder_impact'].items():
                    if level != "low":
                        self.stdout.write(f"     - {stakeholder}: {level}")
            except Exception as e:
                self.stdout.write(f"   [FAIL] Analysis failed: {str(e)}")

        # Summary
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write("Test Summary:")
        successful = sum(1 for r in test_results if r["success"])
        total = len(test_results)
        self.stdout.write(f"Sources tested: {total}")
        self.stdout.write(f"Successful: {successful}")
        self.stdout.write(f"Failed: {total - successful}")
        
        total_indexed = sum(r.get("indexed", 0) for r in test_results if r["success"])
        self.stdout.write(f"Total items indexed: {total_indexed}")
        
        if successful == total:
            self.stdout.write(self.style.SUCCESS("All tests passed!"))
        else:
            self.stdout.write(self.style.WARNING("Some tests failed - check logs above"))