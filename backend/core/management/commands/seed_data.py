from django.core.management.base import BaseCommand

from core.models import Country, DataSource
from playbooks.models import Industry


class Command(BaseCommand):
    help = "Seed EAC countries, data sources, and sample industries."

    def handle(self, *args, **options):
        countries = [
            ("UG", "Uganda", True, "UGX"),
            ("KE", "Kenya", True, "KES"),
            ("TZ", "Tanzania", True, "TZS"),
            ("RW", "Rwanda", True, "RWF"),
            ("BI", "Burundi", True, "BIF"),
            ("SS", "South Sudan", True, "SSP"),
        ]
        for code, name, eac, currency in countries:
            Country.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_eac_member": eac, "currency_code": currency},
            )

        uganda = Country.objects.get(code="UG")
        kenya = Country.objects.get(code="KE")
        tanzania = Country.objects.get(code="TZ")
        rwanda = Country.objects.get(code="RW")

        sources = [
            {
                "name": "Uganda Revenue Authority",
                "source_type": DataSource.SourceType.TAX_AUTHORITY,
                "url": "https://www.ura.go.ug/",
                "country": uganda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.ura.go.ug/en/media-centre/news/",
                    "link_selector": "a",
                    "max_items": 8,
                },
            },
            {
                "name": "Uganda Investment Authority",
                "source_type": DataSource.SourceType.INVESTMENT_AUTHORITY,
                "url": "https://www.ugainvest.go.ug/",
                "country": uganda,
                "feed_url": "https://www.ugainvest.go.ug/feed/",
                "ingestion_config": {"type": "rss", "max_items": 10},
            },
            {
                "name": "Uganda Law Reform Commission",
                "source_type": DataSource.SourceType.LEGAL_REFORM,
                "url": "http://ulrc.go.ug/",
                "country": uganda,
                "feed_url": "http://www.ulrc.go.ug/blog/",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "http://www.ulrc.go.ug/blog/",
                    "link_selector": "a",
                    "max_items": 10,
                },
            },
            {
                "name": "Parliament of Uganda",
                "source_type": DataSource.SourceType.PARLIAMENT,
                "url": "https://www.parliament.go.ug/",
                "country": uganda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.parliament.go.ug/hansards",
                    "link_selector": "a",
                    "max_items": 12,
                },
            },
            {
                "name": "Uganda Legal Information Institute",
                "source_type": DataSource.SourceType.JUDICIARY,
                "url": "https://ulii.org/",
                "country": uganda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://ulii.org/en/judgments/",
                    "link_selector": "a",
                    "max_items": 15,
                },
            },
            {
                "name": "Uganda Gazette",
                "source_type": DataSource.SourceType.GAZETTE,
                "url": "https://www.uppc.go.ug/egazettes",
                "country": uganda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "gazette",
                    "list_url": "https://www.uppc.go.ug/egazettes",
                    "max_items": 10,
                },
            },
            {
                "name": "Ministry of Justice Uganda",
                "source_type": DataSource.SourceType.JUSTICE_MINISTRY,
                "url": "https://justice.go.ug/",
                "country": uganda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://justice.go.ug/",
                    "link_selector": "a",
                    "max_items": 8,
                },
            },
            {
                "name": "Kenya Revenue Authority",
                "source_type": DataSource.SourceType.TAX_AUTHORITY,
                "url": "https://www.kra.go.ke/",
                "country": kenya,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.kra.go.ke/",
                    "link_selector": "a",
                    "max_items": 8,
                },
            },
            {
                "name": "Kenya Law Reform Commission",
                "source_type": DataSource.SourceType.LEGAL_REFORM,
                "url": "https://klrc.go.ke/",
                "country": kenya,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://klrc.go.ke/index.php/bills",
                    "link_selector": "a",
                    "max_items": 10,
                },
            },
            {
                "name": "Parliament of Kenya",
                "source_type": DataSource.SourceType.PARLIAMENT,
                "url": "https://www.parliament.go.ke/",
                "country": kenya,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://parliament.go.ke/the-national-assembly/house-business/bills",
                    "link_selector": "a",
                    "max_items": 12,
                },
            },
            {
                "name": "Kenya Law (Judiciary)",
                "source_type": DataSource.SourceType.JUDICIARY,
                "url": "https://kenyalaw.org/",
                "country": kenya,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://kenyalaw.org/kl/index.php?id=87",
                    "link_selector": "a",
                    "max_items": 15,
                },
            },
            {
                "name": "Kenya Gazette",
                "source_type": DataSource.SourceType.GAZETTE,
                "url": "https://www.governmentpress.go.ke/the-kenya-gazette-",
                "country": kenya,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://new.kenyalaw.org/gazettes/ke/",
                    "link_selector": "a",
                    "max_items": 10,
                },
            },
            {
                "name": "EAC Secretariat News",
                "source_type": DataSource.SourceType.EAC_TRADE,
                "url": "https://www.eac.int/",
                "country": None,
                "feed_url": "https://www.eac.int/index.php?option=com_content&view=featured&format=feed&type=rss",
                "ingestion_config": {"type": "rss", "max_items": 15},
            },
            {
                "name": "World Bank Open Data Blog",
                "source_type": DataSource.SourceType.RSS,
                "url": "https://blogs.worldbank.org/opendata/",
                "country": None,
                "feed_url": "https://blogs.worldbank.org/opendata/rss.xml",
                "ingestion_config": {"type": "rss", "max_items": 15},
            },
            {
                "name": "World Bank Open Data API",
                "source_type": DataSource.SourceType.WORLD_BANK,
                "url": "https://data.worldbank.org/",
                "country": None,
                "feed_url": "",
                "ingestion_config": {"type": "world_bank_api"},
            },
            {
                "name": "Tanzania Revenue Authority",
                "source_type": DataSource.SourceType.TAX_AUTHORITY,
                "url": "https://www.tra.go.tz/",
                "country": tanzania,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.tra.go.tz/news",
                    "link_selector": "a",
                    "max_items": 8,
                },
            },
            {
                "name": "Rwanda Revenue Authority",
                "source_type": DataSource.SourceType.TAX_AUTHORITY,
                "url": "https://www.rra.gov.rw/",
                "country": rwanda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.rra.gov.rw/en/news",
                    "link_selector": "a",
                    "max_items": 8,
                },
            },
            {
                "name": "Rwanda Law Reform Commission",
                "source_type": DataSource.SourceType.LEGAL_REFORM,
                "url": "https://www.rlrc.gov.rw/",
                "country": rwanda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.rlrc.gov.rw/",
                    "link_selector": "a",
                    "max_items": 10,
                },
            },
            {
                "name": "Parliament of Rwanda",
                "source_type": DataSource.SourceType.PARLIAMENT,
                "url": "https://www.parliament.gov.rw/",
                "country": rwanda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://www.parliament.gov.rw/parliament/our-mandate/bills-and-laws",
                    "link_selector": "a",
                    "max_items": 12,
                },
            },
            {
                "name": "Rwanda Judiciary",
                "source_type": DataSource.SourceType.JUDICIARY,
                "url": "https://www.judiciary.gov.rw/",
                "country": rwanda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://amategeko.gov.rw/",
                    "link_selector": "a",
                    "max_items": 15,
                },
            },
            {
                "name": "Rwanda Gazette",
                "source_type": DataSource.SourceType.GAZETTE,
                "url": "https://rwandalii.org/",
                "country": rwanda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://rwandalii.org/",
                    "link_selector": "a",
                    "max_items": 10,
                },
            },
            {
                "name": "Rwanda Ministry of Justice",
                "source_type": DataSource.SourceType.JUSTICE_MINISTRY,
                "url": "https://minijust.gov.rw/",
                "country": rwanda,
                "feed_url": "",
                "ingestion_config": {
                    "type": "html_list",
                    "list_url": "https://minijust.gov.rw/",
                    "link_selector": "a",
                    "max_items": 8,
                },
            },
        ]

        for src in sources:
            DataSource.objects.update_or_create(
                name=src["name"],
                defaults={
                    "source_type": src["source_type"],
                    "url": src["url"],
                    "country": src["country"],
                    "feed_url": src["feed_url"],
                    "ingestion_config": src["ingestion_config"],
                    "is_active": True,
                },
            )

        industries = [
            ("solar-equipment", "Solar Equipment"),
            ("agri-processing", "Agricultural Processing"),
            ("fintech", "Fintech"),
            ("logistics", "Logistics & Freight"),
            ("manufacturing", "Manufacturing"),
        ]
        for slug, name in industries:
            Industry.objects.update_or_create(slug=slug, defaults={"name": name})

        active_names = {src["name"] for src in sources}
        DataSource.objects.exclude(name__in=active_names).update(is_active=False)

        self.stdout.write(self.style.SUCCESS("Seed data loaded."))
