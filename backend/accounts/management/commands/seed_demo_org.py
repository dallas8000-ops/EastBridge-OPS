from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Organization, OrganizationMembership
from core.models import Country
from regulatory.models import ChangeAlertSubscription
from vendors.models import Vendor, VendorContractRecord, VendorPaymentRecord


class Command(BaseCommand):
    help = "Create a demo EU organization, user, vendors, and alert subscription."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com", "is_staff": True},
        )
        if created:
            user.set_password("demo12345")
            user.save()

        org, _ = Organization.objects.get_or_create(
            slug="helio-solar-gmbh",
            defaults={
                "name": "Helio Solar GmbH",
                "origin_country": "DE",
            },
        )
        OrganizationMembership.objects.get_or_create(
            user=user,
            organization=org,
            defaults={"role": OrganizationMembership.Role.ADMIN},
        )

        uganda = Country.objects.filter(code="UG").first()
        if uganda:
            vendor1, _ = Vendor.objects.get_or_create(
                organization=org,
                name="Kampala Solar Installers Ltd",
                defaults={
                    "registration_number": "UG-REG-88421",
                    "country": uganda,
                    "business_profile": "Local EPC contractor for commercial solar installations.",
                    "verification_status": Vendor.VerificationStatus.IN_REVIEW,
                    "risk_score": 42.5,
                    "red_flags": [],
                },
            )
            VendorContractRecord.objects.get_or_create(
                vendor=vendor1,
                contract_ref="HELIOS-UG-2025-01",
                defaults={
                    "value_usd": Decimal("125000.00"),
                    "start_date": date(2025, 3, 1),
                    "end_date": date(2026, 2, 28),
                    "notes": "Turnkey 500kW commercial rooftop installation.",
                },
            )
            VendorPaymentRecord.objects.get_or_create(
                vendor=vendor1,
                payment_date=date(2025, 4, 15),
                amount_usd=Decimal("37500.00"),
                defaults={"status": "completed", "notes": "30% mobilization payment"},
            )
            Vendor.objects.get_or_create(
                organization=org,
                name="East Africa Freight Solutions",
                defaults={
                    "registration_number": "UG-REG-55210",
                    "country": uganda,
                    "business_profile": "Customs clearing and logistics for equipment imports.",
                    "verification_status": Vendor.VerificationStatus.PENDING,
                    "risk_score": 58.0,
                    "red_flags": ["Late payment on prior contract (2024)"],
                },
            )

        if uganda:
            ChangeAlertSubscription.objects.get_or_create(
                organization=org,
                email="compliance@helio-solar.example",
                defaults={
                    "country": uganda,
                    "category": "",
                    "is_active": True,
                },
            )

        org2, _ = Organization.objects.get_or_create(
            slug="nordwind-energy-ag",
            defaults={
                "name": "NordWind Energy AG",
                "origin_country": "DE",
            },
        )
        OrganizationMembership.objects.get_or_create(
            user=user,
            organization=org2,
            defaults={"role": OrganizationMembership.Role.MEMBER},
        )

        kenya = Country.objects.filter(code="KE").first()
        if kenya:
            Vendor.objects.get_or_create(
                organization=org2,
                name="Nairobi Grid Services Ltd",
                defaults={
                    "registration_number": "KE-REG-44102",
                    "country": kenya,
                    "business_profile": "Grid connection and utility liaison for renewable projects.",
                    "verification_status": Vendor.VerificationStatus.VERIFIED,
                    "risk_score": 28.0,
                    "red_flags": [],
                },
            )
            Vendor.objects.get_or_create(
                organization=org2,
                name="Mombasa Customs Brokers",
                defaults={
                    "registration_number": "KE-REG-22981",
                    "country": kenya,
                    "business_profile": "Port clearance and bonded warehouse logistics.",
                    "verification_status": Vendor.VerificationStatus.FLAGGED,
                    "risk_score": 71.5,
                    "red_flags": ["URA watchlist match (2024)", "Incomplete tax clearance"],
                },
            )
            ChangeAlertSubscription.objects.get_or_create(
                organization=org2,
                email="ops@nordwind-energy.example",
                defaults={
                    "country": kenya,
                    "category": "customs",
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo user: demo / demo12345\n"
                "  Orgs: Helio Solar GmbH (UG vendors), NordWind Energy AG (KE vendors)\n"
                "  Use the sidebar org switcher to toggle between them."
            )
        )
