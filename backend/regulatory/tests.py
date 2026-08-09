from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership
from core.models import Country

from .models import ChangeAlertSubscription, RegulatoryChange


class RegulatoryApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.country = Country.objects.create(code="TZ", name="Tanzania", is_eac_member=True)
		RegulatoryChange.objects.create(
			title="VAT adjustment",
			summary="summary",
			business_impact="impact",
			required_action="action",
			category=RegulatoryChange.Category.TAX,
			risk_level=RegulatoryChange.RiskLevel.MEDIUM,
			source_url="https://example.com/vat",
			country=self.country,
		)

		self.user = User.objects.create_user(username="reg-user", password="StrongPass123")
		self.org = Organization.objects.create(name="Reg Org", slug="reg-org", origin_country="DE")
		OrganizationMembership.objects.create(user=self.user, organization=self.org)

	def _auth(self):
		token = self.client.post(
			"/api/v1/auth/login/",
			{"username": "reg-user", "password": "StrongPass123"},
			format="json",
		).json()["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

	def test_changes_endpoint_is_public(self):
		resp = self.client.get("/api/v1/regulatory/changes/")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)

	def test_changes_can_filter_by_category(self):
		resp = self.client.get(
			"/api/v1/regulatory/changes/",
			{"category": RegulatoryChange.Category.CUSTOMS},
		)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 0)

	def test_alerts_list_requires_auth_and_organization(self):
		self._auth()
		resp = self.client.get("/api/v1/regulatory/alerts/")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 0)

	def test_alert_create_without_membership_forbidden(self):
		no_membership = User.objects.create_user(username="no-org-reg", password="StrongPass123")
		client = APIClient()
		token = client.post(
			"/api/v1/auth/login/",
			{"username": "no-org-reg", "password": "StrongPass123"},
			format="json",
		).json()["access"]
		client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

		resp = client.post(
			"/api/v1/regulatory/alerts/",
			{"email": "alerts@example.com", "country_code": "TZ", "category": "tax"},
			format="json",
		)
		self.assertEqual(resp.status_code, 403)

	def test_alert_create_sets_country_from_country_code(self):
		self._auth()
		resp = self.client.post(
			"/api/v1/regulatory/alerts/",
			{"email": "ops@example.com", "country_code": "TZ", "category": "tax"},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org.id),
		)
		self.assertEqual(resp.status_code, 201)
		sub = ChangeAlertSubscription.objects.get(email="ops@example.com")
		self.assertEqual(sub.country.code, "TZ")
