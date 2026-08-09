from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership
from assistant.models import EvidenceDocument
from core.models import Country
from trade.models import TradeProcedure, TradeProcedureStep

from . import generator
from .models import Industry, MarketEntryPlaybook, PlaybookStep


class PlaybooksApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.industry = Industry.objects.create(slug="solar-equipment", name="Solar Equipment")
		self.user = User.objects.create_user(username="play-user", password="StrongPass123")
		self.org = Organization.objects.create(name="Play Org", slug="play-org", origin_country="DE")
		OrganizationMembership.objects.create(user=self.user, organization=self.org)

		token = self.client.post(
			"/api/v1/auth/login/",
			{"username": "play-user", "password": "StrongPass123"},
			format="json",
		).json()["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

	def test_industries_list_is_public(self):
		anon = APIClient()
		resp = anon.get("/api/v1/playbooks/industries/")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)

	def test_playbook_list_scoped_to_organization(self):
		other_org = Organization.objects.create(name="Other", slug="other", origin_country="FR")
		MarketEntryPlaybook.objects.create(
			organization=self.org,
			origin_country="DE",
			industry=self.industry,
			target_country=self.country,
		)
		MarketEntryPlaybook.objects.create(
			organization=other_org,
			origin_country="FR",
			industry=self.industry,
			target_country=self.country,
		)

		resp = self.client.get("/api/v1/playbooks/", HTTP_X_ORGANIZATION_ID=str(self.org.id))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)

	def test_generate_requires_active_organization(self):
		no_membership = User.objects.create_user(username="no-org", password="StrongPass123")
		client = APIClient()
		token = client.post(
			"/api/v1/auth/login/",
			{"username": "no-org", "password": "StrongPass123"},
			format="json",
		).json()["access"]
		client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

		resp = client.post(
			"/api/v1/playbooks/generate/",
			{
				"origin_country": "DE",
				"industry_slug": "solar-equipment",
				"target_country_code": "UG",
			},
			format="json",
		)
		self.assertEqual(resp.status_code, 403)

	def test_generate_rejects_unknown_industry_or_country(self):
		resp = self.client.post(
			"/api/v1/playbooks/generate/",
			{
				"origin_country": "DE",
				"industry_slug": "missing-industry",
				"target_country_code": "ZZ",
			},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org.id),
		)
		self.assertEqual(resp.status_code, 400)

	def test_generate_creates_playbook_with_steps(self):
		resp = self.client.post(
			"/api/v1/playbooks/generate/",
			{
				"origin_country": "de",
				"industry_slug": self.industry.slug,
				"target_country_code": self.country.code,
				"company_description": "Mid-size EU solar exporter",
			},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org.id),
		)
		self.assertEqual(resp.status_code, 201)
		self.assertGreater(len(resp.json()["steps"]), 0)

	def test_step_partial_update_allows_only_is_completed(self):
		playbook = MarketEntryPlaybook.objects.create(
			organization=self.org,
			origin_country="DE",
			industry=self.industry,
			target_country=self.country,
		)
		step = PlaybookStep.objects.create(
			playbook=playbook,
			step_type=PlaybookStep.StepType.REGISTRATION,
			title="Register",
			description="desc",
			sort_order=0,
		)

		bad = self.client.patch(
			f"/api/v1/playbooks/steps/{step.id}/",
			{"title": "Nope", "is_completed": True},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org.id),
		)
		self.assertEqual(bad.status_code, 400)

		ok = self.client.patch(
			f"/api/v1/playbooks/steps/{step.id}/",
			{"is_completed": True},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org.id),
		)
		self.assertEqual(ok.status_code, 200)
		step.refresh_from_db()
		self.assertTrue(step.is_completed)


class PlaybookGeneratorTests(TestCase):
	def setUp(self):
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.industry = Industry.objects.create(slug="solar-equipment", name="Solar Equipment")
		self.org = Organization.objects.create(name="Gen Org", slug="gen-org", origin_country="DE")

	def test_find_evidence_keyword_match_then_fallback(self):
		none_found = generator._find_evidence("UG", "solar-equipment")
		self.assertIsNone(none_found)

		doc_generic = EvidenceDocument.objects.create(
			title="General note",
			source_url="https://example.com/generic",
			country_code="",
			category="other",
			content="some text",
		)
		doc_match = EvidenceDocument.objects.create(
			title="Solar import update",
			source_url="https://example.com/solar",
			country_code="UG",
			category="trade_procedure",
			content="solar equipment import customs guidance",
		)

		found = generator._find_evidence("UG", "solar-equipment")
		self.assertEqual(found.id, doc_match.id)

		doc_match.delete()
		fallback = generator._find_evidence("UG", "solar-equipment")
		self.assertEqual(fallback.id, doc_generic.id)

	def test_find_trade_procedure_keyword_match_then_fallback(self):
		self.assertIsNone(generator._find_trade_procedure("UG", "solar-equipment"))

		proc_fallback = TradeProcedure.objects.create(
			external_id="p-fallback",
			title="General registration",
			slug="general-registration",
			country=self.country,
			activity_type=TradeProcedure.ActivityType.REGISTRATION,
			summary="generic",
			source_url="https://example.com/p-fallback",
		)
		proc_match = TradeProcedure.objects.create(
			external_id="p-match",
			title="Solar import clearance",
			slug="solar-import-clearance",
			country=self.country,
			activity_type=TradeProcedure.ActivityType.IMPORT,
			summary="customs and import process",
			source_url="https://example.com/p-match",
		)

		found = generator._find_trade_procedure("UG", "solar-equipment")
		self.assertEqual(found.id, proc_match.id)

		proc_match.delete()
		fallback = generator._find_trade_procedure("UG", "solar-equipment")
		self.assertEqual(fallback.id, proc_fallback.id)

	def test_generate_playbook_enriches_with_trade_and_evidence_and_company_context(self):
		EvidenceDocument.objects.create(
			title="Indexed source",
			source_url="https://example.com/evidence",
			country_code="UG",
			category="trade_procedure",
			content="solar import guidance",
		)
		proc = TradeProcedure.objects.create(
			external_id="p-live",
			title="Solar import procedure",
			slug="solar-import-procedure",
			country=self.country,
			activity_type=TradeProcedure.ActivityType.IMPORT,
			summary="import",
			source_url="https://example.com/proc",
			source_portal="TIP",
		)
		TradeProcedureStep.objects.create(
			procedure=proc,
			sort_order=0,
			title="Import documentation",
			description="Submit complete import packet",
		)

		playbook = generator.generate_playbook(
			origin_country="de",
			industry=self.industry,
			target_country=self.country,
			company_description="Company profile text",
			organization=self.org,
		)

		self.assertEqual(playbook.origin_country, "DE")
		self.assertEqual(playbook.organization_id, self.org.id)
		self.assertEqual(playbook.estimated_timeline_weeks, generator.COUNTRY_TIMELINE_WEEKS["UG"])

		steps = list(playbook.steps.order_by("sort_order"))
		self.assertTrue(steps)
		self.assertIn("Company context", steps[0].description)

		import_step = next(s for s in steps if s.step_type == PlaybookStep.StepType.IMPORT)
		self.assertEqual(import_step.source_url, "https://example.com/proc")
		self.assertIn("See Solar import procedure", import_step.description)

	def test_generate_playbook_uses_default_template_for_unknown_slug(self):
		industry = Industry.objects.create(slug="unknown-segment", name="Unknown Segment")
		playbook = generator.generate_playbook("de", industry, self.country, organization=self.org)
		first = playbook.steps.order_by("sort_order").first()
		self.assertEqual(first.step_type, PlaybookStep.StepType.REGISTRATION)
