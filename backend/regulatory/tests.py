from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership
from core.models import Country, DataSource

from .models import ChangeAlertSubscription, RegulatoryChange
from .services import change_detection


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


class ChangeDetectorTests(TestCase):
	def setUp(self):
		self.detector = change_detection.ChangeDetector()

	def test_detect_content_changes(self):
		self.assertEqual(self.detector.detect_content_changes("", "new")["change_type"], "new_content")
		self.assertFalse(self.detector.detect_content_changes("same text", "same text")["has_changes"])

		result = self.detector.detect_content_changes(
			"Tax rules apply to importers.", "Section repealed entirely. New schedule published."
		)
		self.assertTrue(result["has_changes"])
		self.assertEqual(result["change_type"], "legislative_amendment")
		self.assertIn("Section repealed entirely", result["added_text"])
		self.assertIn("Tax rules apply to importers", result["removed_text"])

	def test_classify_change_type_branches(self):
		classify = self.detector._classify_change_type
		self.assertEqual(classify("rate 10 fee 20", "rate 15 fee 25"), "numeric_change")
		self.assertEqual(classify("due 2026-01-01 ok", "due 2026-02-01 ok"), "date_change")
		self.assertEqual(classify("abc", "abc abc abc"), "significant_expansion")
		self.assertEqual(classify("long text here", "lo"), "significant_reduction")
		self.assertEqual(classify("hello world", "world hello"), "content_modification")


class ChangeAnalysisTests(TestCase):
	def setUp(self):
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.source = DataSource.objects.create(
			name="URA",
			source_type=DataSource.SourceType.TAX_AUTHORITY,
			url="https://example.com/ura",
			country=self.country,
		)

	def _change(self, title, risk, category=RegulatoryChange.Category.TAX, source=None, summary="summary"):
		return RegulatoryChange.objects.create(
			title=title,
			summary=summary,
			business_impact="impact",
			required_action="action",
			category=category,
			risk_level=risk,
			source_url=f"https://example.com/{title.replace(' ', '-')}",
			source=source,
			country=self.country,
		)

	def test_detect_urgent_changes_returns_high_and_critical_only(self):
		high = self._change("High one", RegulatoryChange.RiskLevel.HIGH)
		critical = self._change("Critical one", RegulatoryChange.RiskLevel.CRITICAL)
		self._change("Low one", RegulatoryChange.RiskLevel.LOW)

		self.assertEqual(set(change_detection.detect_urgent_changes()), {high, critical})

	def test_analyze_regulatory_trends_handles_changes_without_source(self):
		self._change("With source", RegulatoryChange.RiskLevel.LOW, source=self.source)
		self._change("No source", RegulatoryChange.RiskLevel.HIGH)

		trends = change_detection.analyze_regulatory_trends()

		self.assertEqual(trends["total_changes"], 2)
		self.assertEqual(trends["source_activity"], {"URA": 1, "unknown": 1})
		self.assertEqual(trends["country_breakdown"], {"UG": 2})
		self.assertEqual(trends["risk_breakdown"], {"low": 1, "high": 1})

	def test_generate_change_summary_finds_related_and_urgency(self):
		change = self._change("Urgent tax update", RegulatoryChange.RiskLevel.HIGH, summary="VAT rate changes")
		related = self._change("Another tax update", RegulatoryChange.RiskLevel.LOW, summary="VAT rate changes")

		summary = change_detection.generate_change_summary(change)

		self.assertEqual(
			summary["urgency_factors"], ["high_risk_level", "urgent_keywords", "recent_detection"]
		)
		self.assertEqual(summary["related_changes"], [related])
		self.assertTrue(summary["recommended_actions"][0].startswith("HIGH PRIORITY"))
		self.assertEqual(summary["stakeholder_impact"]["finance"], "high")

	def test_recommendations_by_category_and_risk(self):
		critical_tax = self._change("Tax", RegulatoryChange.RiskLevel.CRITICAL)
		customs = self._change("Customs", RegulatoryChange.RiskLevel.LOW, RegulatoryChange.Category.CUSTOMS)
		investment = self._change("Invest", RegulatoryChange.RiskLevel.LOW, RegulatoryChange.Category.INVESTMENT)

		self.assertTrue(change_detection._generate_recommendations(critical_tax)[0].startswith("IMMEDIATE"))
		self.assertIn("Verify tariff classifications", change_detection._generate_recommendations(customs))
		self.assertEqual(len(change_detection._generate_recommendations(investment)), 4)

	def test_assess_stakeholder_impact_flags_each_area(self):
		change = self._change(
			"Tax compliance process",
			RegulatoryChange.RiskLevel.LOW,
			summary="employment data rules",
		)
		impact = change_detection._assess_stakeholder_impact(change)
		self.assertEqual(
			impact,
			{"operations": "medium", "finance": "high", "legal": "high", "hr": "medium", "it": "medium"},
		)


class LegalSourceCommandTests(TestCase):
	def setUp(self):
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.ok_source = DataSource.objects.create(
			name="ULRC",
			source_type=DataSource.SourceType.LEGAL_REFORM,
			url="https://example.com/ulrc",
			country=self.country,
			ingestion_config={"type": "html_list", "max_items": 5},
		)
		self.bad_source = DataSource.objects.create(
			name="Gazette",
			source_type=DataSource.SourceType.GAZETTE,
			url="https://example.com/gazette",
			country=self.country,
			ingestion_config={"type": "gazette"},
		)
		RegulatoryChange.objects.create(
			title="Urgent levy notice",
			summary="tax levy",
			business_impact="impact",
			required_action="action",
			category=RegulatoryChange.Category.TAX,
			risk_level=RegulatoryChange.RiskLevel.HIGH,
			source_url="https://example.com/levy",
			source=self.ok_source,
			country=self.country,
		)

	@mock.patch("regulatory.management.commands.test_uganda_sources.indexer.run_source_ingestion")
	def test_test_uganda_sources_reports_results(self, run_source):
		def ingest(source):
			if source == self.bad_source:
				raise RuntimeError("offline")
			return {"fetched": 2, "indexed": 1, "failed": 0}

		run_source.side_effect = ingest
		out = StringIO()

		call_command("test_uganda_sources", stdout=out)

		output = out.getvalue()
		self.assertIn("[FAIL] Failed: offline", output)
		self.assertIn("Found 1 urgent changes", output)
		self.assertIn("Analyzing: Urgent levy notice", output)
		self.assertIn("Some tests failed", output)

	@mock.patch(
		"regulatory.management.commands.test_uganda_sources.indexer.run_source_ingestion",
		return_value={"fetched": 0, "indexed": 0, "failed": 0},
	)
	def test_test_uganda_sources_all_pass(self, _run_source):
		RegulatoryChange.objects.all().delete()
		out = StringIO()

		call_command("test_uganda_sources", stdout=out)

		self.assertIn("No urgent changes found", out.getvalue())
		self.assertIn("All tests passed!", out.getvalue())

	def test_test_all_regions_config_lists_sources(self):
		out = StringIO()

		call_command("test_all_regions_config", stdout=out)

		output = out.getvalue()
		self.assertIn("[OK] UG - Found 2 sources", output)
		self.assertIn("[INFO] KE - No active sources configured", output)
		self.assertIn("gazette: 1", output)
