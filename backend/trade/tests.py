from datetime import date
import importlib
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Country

from .models import TradeProcedure, TradeProcedureStep
from .services import sync_trade_procedures


class TradeApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.proc = TradeProcedure.objects.create(
			external_id="proc-1",
			title="Import machinery",
			slug="import-machinery",
			country=self.country,
			activity_type=TradeProcedure.ActivityType.IMPORT,
			summary="Import summary",
			source_url="https://example.com/proc",
			estimated_days=12,
		)
		TradeProcedureStep.objects.create(
			procedure=self.proc,
			sort_order=1,
			title="Submit declaration",
			description="Submit import declaration",
		)

	def test_procedure_list_is_public(self):
		resp = self.client.get("/api/v1/trade/procedures/")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)

	def test_filter_by_activity_type(self):
		resp = self.client.get(
			"/api/v1/trade/procedures/",
			{"activity_type": TradeProcedure.ActivityType.EXPORT},
		)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 0)


class TradeSyncServiceTests(TestCase):
	def setUp(self):
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)

	def _parsed(self):
		return SimpleNamespace(
			external_id="ug-import-license",
			title="Import license process",
			activity_type=TradeProcedure.ActivityType.IMPORT,
			summary="Apply for license",
			url="https://tip.example.com/ug/import-license",
			estimated_days=10,
			estimated_cost="USD 100",
			steps=[
				{
					"sort_order": 0,
					"title": "Collect docs",
					"description": "Collect required documents",
					"responsible_agency": "URA",
					"documents_required": ["invoice"],
					"estimated_days": 2,
				}
			],
		)

	@mock.patch("assistant.tasks.embed_document")
	@mock.patch("trade.services.fetch_country_procedures")
	def test_sync_trade_procedures_creates_records(self, fetch_country_procedures, embed_document):
		fetch_country_procedures.return_value = ([self._parsed()], "live")

		result = sync_trade_procedures(country_codes=["UG"], offline=False)

		self.assertEqual(result["created"], 1)
		self.assertEqual(result["updated"], 0)
		self.assertFalse(result["errors"])
		self.assertTrue(TradeProcedure.objects.filter(external_id="ug-import-license").exists())
		self.assertEqual(TradeProcedureStep.objects.count(), 1)
		embed_document.assert_called_once()

	def test_sync_trade_procedures_reports_unknown_country(self):
		result = sync_trade_procedures(country_codes=["XX"], offline=True)
		self.assertEqual(result["created"], 0)
		self.assertIn("Unknown country: XX", result["errors"][0])

	@mock.patch("assistant.tasks.embed_document")
	@mock.patch("trade.services.fetch_country_procedures")
	def test_sync_trade_procedures_records_fallback_warning(self, fetch_country_procedures, _embed_document):
		fetch_country_procedures.return_value = ([self._parsed()], "fallback")

		result = sync_trade_procedures(country_codes=["UG"], offline=False)
		self.assertTrue(result["errors"])
		self.assertIn("fallback procedures", result["errors"][0])


class TipFetcherTests(TestCase):
	def _tip_module(self):
		try:
			from trade.fetchers import tip
		except ModuleNotFoundError as exc:
			self.skipTest(f"tip parser dependency missing: {exc}")
		return importlib.reload(tip)

	def test_unreachable_error_detection(self):
		tip = self._tip_module()
		self.assertTrue(tip._is_unreachable_error(OSError("getaddrinfo failed")))
		self.assertTrue(tip._is_unreachable_error(Exception("11001 dns error")))
		self.assertFalse(tip._is_unreachable_error(Exception("random")))

	def test_infer_activity(self):
		tip = self._tip_module()
		self.assertEqual(tip._infer_activity("Export declaration", ""), "export")
		self.assertEqual(tip._infer_activity("Import docs", ""), "import")
		self.assertEqual(tip._infer_activity("Transit route", ""), "transit")
		self.assertEqual(tip._infer_activity("Company register", ""), "registration")
		self.assertEqual(tip._infer_activity("Permit processing", ""), "licensing")
		self.assertEqual(tip._infer_activity("Customs clearance", ""), "customs")

	def test_parse_steps_from_page_with_structured_and_heading_fallback(self):
		tip = self._tip_module()
		soup = tip.BeautifulSoup(
			"""
			<html><body>
				<div class='procedure-step'><h3>Submit form</h3><p>Do x</p><em>URA</em><ul><li>Invoice</li></ul></div>
			</body></html>
			""",
			"lxml",
		)
		steps = tip._parse_steps_from_page(soup)
		self.assertGreaterEqual(len(steps), 1)
		self.assertEqual(steps[0]["title"], "Submit form")

		soup2 = tip.BeautifulSoup("<html><body><h2>Long heading title</h2><p>desc</p></body></html>", "lxml")
		steps2 = tip._parse_steps_from_page(soup2)
		self.assertEqual(len(steps2), 1)

	def test_parse_procedure_page_success_and_failures(self):
		tip = self._tip_module()
		http_get = mock.patch.object(tip, "_http_get").start()
		self.addCleanup(mock.patch.stopall)
		http_get.return_value = """
		<html>
			<head><meta name='description' content='Procedure summary'></head>
			<body>
				<h1>Import Procedure</h1>
				<div class='procedure-step'><h3>Submit docs</h3><p>Do this in 5 days</p></div>
				<p>cost: USD 20</p>
			</body>
		</html>
		"""
		parsed = tip._parse_procedure_page("https://example.com/p1", "UG")
		self.assertIsNotNone(parsed)
		self.assertEqual(parsed.activity_type, "import")

		http_get.return_value = "<html><body><h1>x</h1></body></html>"
		self.assertIsNone(tip._parse_procedure_page("https://example.com/p2", "UG"))

		http_get.side_effect = OSError("down")
		self.assertIsNone(tip._parse_procedure_page("https://example.com/p3", "UG"))

	def test_discover_from_list_url_filters_and_unreachable(self):
		tip = self._tip_module()
		http_get = mock.patch.object(tip, "_http_get").start()
		self.addCleanup(mock.patch.stopall)
		http_get.return_value = """
		<html><body>
			<a href='/procedures/a'>Import declaration process</a>
			<a href='https://external.example/x'>Export flow</a>
			<a href='/procedures/a'>Import declaration process</a>
		</body></html>
		"""
		links, fatal = tip._discover_from_list_url("https://trade.go.ug/procedures", "https://trade.go.ug/", 5)
		self.assertEqual(len(links), 1)
		self.assertIsNone(fatal)

		http_get.side_effect = OSError("getaddrinfo failed")
		links2, fatal2 = tip._discover_from_list_url("https://trade.go.ug/procedures", "https://trade.go.ug/", 5)
		self.assertEqual(links2, [])
		self.assertIsNotNone(fatal2)

	def test_discover_procedure_links_paths(self):
		tip = self._tip_module()
		discover = mock.patch.object(tip, "_discover_from_list_url").start()
		self.addCleanup(mock.patch.stopall)
		discover.side_effect = [([], None), (["https://trade.go.ug/p1"], None)]
		links = tip.discover_procedure_links("UG", max_items=3)
		self.assertEqual(links, ["https://trade.go.ug/p1"])

		self.assertEqual(tip.discover_procedure_links("XX"), [])

	def test_fetch_country_procedures_live_and_fallback(self):
		tip = self._tip_module()
		fallback = mock.patch.object(tip, "get_fallback_procedures", return_value=[SimpleNamespace(steps=[{"title": "a"}])]).start()
		discover = mock.patch.object(tip, "discover_procedure_links", return_value=["https://trade.go.ug/p1"]).start()
		parse_page = mock.patch.object(tip, "_parse_procedure_page").start()
		self.addCleanup(mock.patch.stopall)
		parse_page.return_value = SimpleNamespace(steps=[{"title": "a"}])
		procedures, source = tip.fetch_country_procedures("UG", offline=False)
		self.assertEqual(source, "live")
		self.assertEqual(len(procedures), 1)

		parse_page.return_value = None
		procedures2, source2 = tip.fetch_country_procedures("UG", offline=False)
		self.assertEqual(source2, "fallback")
		self.assertEqual(len(procedures2), 1)

		procedures3, source3 = tip.fetch_country_procedures("UG", offline=True)
		self.assertEqual(source3, "fallback")
		self.assertEqual(len(procedures3), 1)
