from datetime import date
from decimal import Decimal
import importlib
from types import SimpleNamespace
from unittest import mock

import httpx
from django.test import TestCase
from rest_framework.test import APIClient

from assistant.models import EvidenceDocument
from core.models import Country, DataSource
from intelligence.models import EconomicIndicator
from regulatory.models import ChangeAlertSubscription, RegulatoryChange
from trade.models import TradeProcedure

from .fetchers.base import FetchedItem
from .fetchers import world_bank
from .models import IngestedItem, IngestionRun
from .services import indexer
from .services import retrieval
from .tasks import dispatch_change_alerts, run_economic_ingestion, run_regulatory_ingestion


class IngestionPipelineTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.country = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.source = DataSource.objects.create(
			name="URA News",
			source_type=DataSource.SourceType.TAX_AUTHORITY,
			url="https://example.com/news",
			country=self.country,
			ingestion_config={"type": "rss"},
		)

	def _item(self, external_id="x-1", title="Tax update", content="urgent tax deadline"):
		return FetchedItem(
			external_id=external_id,
			title=title,
			url=f"https://example.com/{external_id}",
			content=content,
			published_at=date(2026, 1, 1),
		)

	def test_infer_risk_level_classifies_high_medium_low(self):
		self.assertEqual(indexer._infer_risk_level("Urgent notice", "deadline is immediate"), "high")
		self.assertEqual(indexer._infer_risk_level("Tax amendment", "new rate"), "medium")
		self.assertEqual(indexer._infer_risk_level("Weekly bulletin", "general info"), "low")

	def test_summarize_impact_special_cases_tax_and_customs(self):
		tax_summary = indexer._summarize_impact("URA tax circular", "details")
		self.assertIn("tax", tax_summary[1].lower())
		customs_summary = indexer._summarize_impact("Customs import process", "details")
		self.assertIn("import", customs_summary[1].lower())

	@mock.patch("assistant.tasks.embed_document")
	def test_process_fetched_item_creates_evidence_and_change(self, embed_document):
		ingested = indexer.process_fetched_item(self.source, self._item())

		self.assertEqual(ingested.status, IngestedItem.Status.INDEXED)
		self.assertTrue(EvidenceDocument.objects.filter(source_url="https://example.com/x-1").exists())
		self.assertTrue(RegulatoryChange.objects.filter(source_url="https://example.com/x-1").exists())
		embed_document.assert_called_once()

	@mock.patch("assistant.tasks.embed_document")
	def test_process_fetched_item_marks_duplicate_as_skipped(self, _embed_document):
		indexer.process_fetched_item(self.source, self._item(external_id="x-dup"))
		second = indexer.process_fetched_item(self.source, self._item(external_id="x-dup"))
		self.assertEqual(second.status, IngestedItem.Status.SKIPPED)

	@mock.patch("ingestion.services.indexer.process_fetched_item")
	@mock.patch("ingestion.services.indexer.fetch_from_source")
	def test_run_source_ingestion_marks_failed_items(self, fetch_from_source, process_fetched_item):
		fetch_from_source.return_value = [self._item(external_id="x-fail")]
		process_fetched_item.side_effect = RuntimeError("boom")

		result = indexer.run_source_ingestion(self.source)
		self.assertEqual(result["failed"], 1)
		failed = IngestedItem.objects.get(external_id="x-fail")
		self.assertEqual(failed.status, IngestedItem.Status.FAILED)

	def test_fetch_from_source_unknown_type_raises(self):
		source = DataSource.objects.create(
			name="Unknown",
			source_type=DataSource.SourceType.OTHER,
			url="https://example.com/other",
			ingestion_config={"type": "mystery"},
		)
		with self.assertRaises(ValueError):
			indexer.fetch_from_source(source)

	@mock.patch("ingestion.services.indexer.fetch_world_bank_as_items", return_value=[])
	@mock.patch("ingestion.services.indexer.fetch_html_list", return_value=[])
	@mock.patch("ingestion.services.indexer.fetch_rss", return_value=[])
	def test_fetch_from_source_dispatches_by_type(self, fetch_rss, fetch_html, fetch_wb):
		rss_source = DataSource.objects.create(
			name="RSS",
			source_type=DataSource.SourceType.RSS,
			url="https://example.com/rss",
			ingestion_config={"type": "rss", "max_items": 4},
		)
		html_source = DataSource.objects.create(
			name="HTML",
			source_type=DataSource.SourceType.TAX_AUTHORITY,
			url="https://example.com/html",
			ingestion_config={"type": "html_list", "list_url": "https://example.com/list"},
		)
		wb_profile = DataSource.objects.create(
			name="WB profile",
			source_type=DataSource.SourceType.WORLD_BANK,
			url="https://example.com/wb",
			ingestion_config={"type": "world_bank_profile"},
		)
		wb_api = DataSource.objects.create(
			name="WB API",
			source_type=DataSource.SourceType.WORLD_BANK,
			url="https://example.com/wb-api",
			ingestion_config={"type": "world_bank_api"},
		)

		self.assertEqual(indexer.fetch_from_source(rss_source), [])
		self.assertEqual(indexer.fetch_from_source(html_source), [])
		self.assertEqual(indexer.fetch_from_source(wb_profile), [])
		self.assertEqual(indexer.fetch_from_source(wb_api), [])
		fetch_rss.assert_called_once()
		fetch_html.assert_called_once()
		fetch_wb.assert_called_once()

	@mock.patch("assistant.tasks.embed_document")
	def test_process_fetched_item_updates_existing_when_content_changes(self, _embed_document):
		indexer.process_fetched_item(self.source, self._item(external_id="x-update", content="old body"))
		updated = indexer.process_fetched_item(self.source, self._item(external_id="x-update", content="new body"))

		self.assertEqual(updated.status, IngestedItem.Status.INDEXED)
		updated.refresh_from_db()
		self.assertEqual(updated.raw_content, "new body")

	def test_process_fetched_item_non_regulatory_source_skips_change_creation(self):
		non_reg_source = DataSource.objects.create(
			name="Other feed",
			source_type=DataSource.SourceType.OTHER,
			url="https://example.com/other",
			ingestion_config={"type": "rss"},
			country=None,
		)
		with mock.patch("assistant.tasks.embed_document"):
			ingested = indexer.process_fetched_item(non_reg_source, self._item(external_id="x-other"))

		self.assertEqual(ingested.status, IngestedItem.Status.INDEXED)
		self.assertIsNone(ingested.regulatory_change_id)
		evidence = EvidenceDocument.objects.get(source_url=ingested.url)
		self.assertEqual(evidence.country_code, "")

	@mock.patch("ingestion.services.indexer.fetch_from_source", side_effect=RuntimeError("downstream"))
	def test_run_source_ingestion_handles_fetch_failure(self, _fetch):
		result = indexer.run_source_ingestion(self.source)
		self.assertEqual(result["source"], self.source.name)
		self.assertEqual(result["new"], 0)
		self.assertIn("error", result)

	@mock.patch("ingestion.services.indexer.run_source_ingestion")
	def test_run_regulatory_ingestion_skips_world_bank_types(self, run_source):
		DataSource.objects.create(
			name="WB API",
			source_type=DataSource.SourceType.WORLD_BANK,
			url="https://example.com/wb-api",
			ingestion_config={"type": "world_bank_api"},
		)
		DataSource.objects.create(
			name="WB Profile",
			source_type=DataSource.SourceType.WORLD_BANK,
			url="https://example.com/wb-prof",
			ingestion_config={"type": "world_bank_profile"},
		)
		run_source.return_value = {"source": self.source.name, "fetched": 1, "indexed": 1, "failed": 0}

		run = indexer.run_regulatory_ingestion()
		self.assertEqual(run.items_new, 1)
		self.assertEqual(run.items_fetched, 1)
		run_source.assert_called_once_with(self.source)

	@mock.patch("ingestion.views.active_model_name", return_value="hash-v1")
	@mock.patch("ingestion.views.resolve_provider", return_value="hash")
	def test_ingestion_status_endpoint_returns_counts(self, _provider, _model):
		EvidenceDocument.objects.create(
			title="Doc",
			source_url="https://example.com/doc",
			country_code="UG",
			category="tax",
			content="body",
		)
		RegulatoryChange.objects.create(
			title="Rule",
			summary="s",
			business_impact="i",
			required_action="a",
			category=RegulatoryChange.Category.TAX,
			source_url="https://example.com/rule",
			country=self.country,
		)
		EconomicIndicator.objects.create(
			country=self.country,
			indicator_type=EconomicIndicator.IndicatorType.INFLATION,
			label="Inflation",
			value="5.5",
			period=date(2025, 12, 31),
		)
		TradeProcedure.objects.create(
			external_id="tp-1",
			title="Import declaration",
			slug="import-declaration",
			country=self.country,
			activity_type="import",
			summary="summary",
			source_url="https://example.com/tp",
		)

		resp = self.client.get("/api/v1/ingestion/status/")
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertEqual(data["evidence_count"], 1)
		self.assertEqual(data["regulatory_changes_count"], 1)
		self.assertEqual(data["economic_indicators_count"], 1)
		self.assertEqual(data["trade_procedures_count"], 1)
		self.assertEqual(data["embedding_provider"], "hash")


class AlertDispatchTests(TestCase):
	def setUp(self):
		self.country = Country.objects.create(code="KE", name="Kenya", is_eac_member=True)
		self.change = RegulatoryChange.objects.create(
			title="Customs amendment",
			summary="summary",
			business_impact="impact",
			required_action="action",
			category=RegulatoryChange.Category.CUSTOMS,
			risk_level=RegulatoryChange.RiskLevel.HIGH,
			source_url="https://example.com/customs",
			country=self.country,
		)

	@mock.patch("ingestion.tasks.send_mail")
	def test_dispatch_change_alerts_sends_matching_emails(self, send_mail):
		ChangeAlertSubscription.objects.create(email="a@example.com", country=self.country, category="")
		ChangeAlertSubscription.objects.create(email="b@example.com", country=self.country, category=self.change.category)
		ChangeAlertSubscription.objects.create(email="c@example.com", country=None, category="")
		ChangeAlertSubscription.objects.create(email="d@example.com", country=self.country, category="tax")

		result = dispatch_change_alerts(self.change)
		self.assertEqual(result["emails_sent"], 3)
		send_mail.assert_called_once()

	@mock.patch("ingestion.tasks.send_mail")
	@mock.patch("ingestion.tasks.httpx.Client")
	@mock.patch("ingestion.tasks.settings.ALERT_WEBHOOK_URL", "https://hooks.example.com/ingest")
	def test_dispatch_change_alerts_captures_webhook_errors(self, client_cls, _send_mail):
		ChangeAlertSubscription.objects.create(email="a@example.com", country=self.country, category="")
		client_ctx = client_cls.return_value.__enter__.return_value
		client_ctx.post.side_effect = RuntimeError("webhook down")

		result = dispatch_change_alerts(self.change)
		self.assertEqual(result["emails_sent"], 1)
		self.assertTrue(result["errors"])

	@mock.patch("ingestion.tasks.send_mail")
	def test_dispatch_change_alerts_no_subscribers_no_email(self, send_mail):
		ChangeAlertSubscription.objects.all().delete()
		result = dispatch_change_alerts(self.change)
		self.assertEqual(result["emails_sent"], 0)
		send_mail.assert_not_called()


class IngestionTaskWrapperTests(TestCase):
	@mock.patch("ingestion.tasks.indexer.run_regulatory_ingestion")
	def test_run_regulatory_ingestion_task_wrapper(self, run_ingestion):
		run_ingestion.return_value = SimpleNamespace(id=99, items_new=7, items_failed=1)
		result = run_regulatory_ingestion()
		self.assertEqual(result["run_id"], 99)
		self.assertEqual(result["items_new"], 7)
		self.assertEqual(result["items_failed"], 1)

	@mock.patch("ingestion.tasks.fetch_world_bank_indicators", return_value={"created": 2, "updated": 3, "errors": []})
	def test_run_economic_ingestion_success(self, _fetch):
		result = run_economic_ingestion()
		self.assertEqual(result["created"], 2)

		last = IngestionRun.objects.order_by("-id").first()
		self.assertEqual(last.run_type, IngestionRun.RunType.ECONOMIC)
		self.assertEqual(last.items_new, 2)
		self.assertEqual(last.items_fetched, 5)

	@mock.patch("ingestion.tasks.fetch_world_bank_indicators", side_effect=RuntimeError("wb down"))
	def test_run_economic_ingestion_failure(self, _fetch):
		result = run_economic_ingestion()
		self.assertIn("error", result)

		last = IngestionRun.objects.order_by("-id").first()
		self.assertEqual(last.items_failed, 1)


class RssFetcherTests(TestCase):
	def _rss_module(self):
		try:
			from ingestion.fetchers import rss as rss_fetcher
		except ModuleNotFoundError as exc:
			self.skipTest(f"rss parser dependency missing: {exc}")
		return importlib.reload(rss_fetcher)

	def test_parse_date_supports_rfc_and_iso_and_invalid(self):
		rss_fetcher = self._rss_module()
		self.assertIsNotNone(rss_fetcher._parse_date("Mon, 09 Aug 2026 10:20:30 GMT"))
		self.assertIsNotNone(rss_fetcher._parse_date("2026-08-09"))
		self.assertIsNotNone(rss_fetcher._parse_date("2026-08-09T10:20:30Z"))
		self.assertIsNone(rss_fetcher._parse_date("not-a-date"))

	def test_fetch_rss_parses_entries(self):
		rss_fetcher = self._rss_module()
		http_get = mock.patch.object(rss_fetcher, "_http_get").start()
		parse = mock.patch.object(rss_fetcher.feedparser, "parse").start()
		self.addCleanup(mock.patch.stopall)
		http_get.return_value = "<xml />"
		parse.return_value = SimpleNamespace(
			entries=[
				{
					"id": "doc-1",
					"title": "Tax update title",
					"link": "https://example.com/doc-1",
					"summary": "<p>summary</p>",
					"published": "2026-08-09",
				}
			],
			bozo=False,
		)

		items = rss_fetcher.fetch_rss("https://example.com/feed", max_items=5)
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].external_id, "doc-1")
		self.assertEqual(items[0].content, "summary")
		self.assertEqual(items[0].published_at.isoformat(), "2026-08-09")

	def test_fetch_rss_falls_back_to_direct_feed_parse(self):
		rss_fetcher = self._rss_module()
		mock.patch.object(rss_fetcher, "_http_get", side_effect=httpx.HTTPError("offline")).start()
		parse = mock.patch.object(rss_fetcher.feedparser, "parse").start()
		self.addCleanup(mock.patch.stopall)
		parse.return_value = SimpleNamespace(
			entries=[{"link": "https://example.com/x", "title": "Fallback title", "description": "desc"}],
			bozo=False,
		)
		items = rss_fetcher.fetch_rss("https://example.com/feed")
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].title, "Fallback title")

	def test_fetch_rss_raises_on_no_entries(self):
		rss_fetcher = self._rss_module()
		mock.patch.object(rss_fetcher, "_http_get").start()
		parse = mock.patch.object(rss_fetcher.feedparser, "parse").start()
		self.addCleanup(mock.patch.stopall)
		parse.return_value = SimpleNamespace(entries=[], bozo=True, bozo_exception="bad xml")
		with self.assertRaises(ValueError):
			rss_fetcher.fetch_rss("https://example.com/feed")

	def test_fetch_html_list_discovers_links_and_uses_page_content(self):
		rss_fetcher = self._rss_module()
		http_get = mock.patch.object(rss_fetcher, "_http_get").start()
		self.addCleanup(mock.patch.stopall)
		http_get.side_effect = [
			"""
			<html><body>
				<a href='/a1'>A very descriptive anchor title</a>
				<a href='/a1'>A very descriptive anchor title</a>
				<a href='/short'>tiny</a>
			</body></html>
			""",
			"<html><body><main><p>Deep content body</p></main></body></html>",
		]

		items = rss_fetcher.fetch_html_list("https://example.com/list", max_items=2)
		self.assertEqual(len(items), 1)
		self.assertIn("Deep content body", items[0].content)

	def test_fetch_html_list_falls_back_to_title_on_page_fetch_error(self):
		rss_fetcher = self._rss_module()
		http_get = mock.patch.object(rss_fetcher, "_http_get").start()
		self.addCleanup(mock.patch.stopall)
		http_get.side_effect = [
			"<html><body><a href='/a1'>A very descriptive anchor title</a></body></html>",
			httpx.HTTPError("boom"),
		]
		items = rss_fetcher.fetch_html_list("https://example.com/list", max_items=2)
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].content, "A very descriptive anchor title")


class WorldBankFetcherTests(TestCase):
	def setUp(self):
		self.ug = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)

	def _wb_response(self, value="5.5", year="2025"):
		response = mock.Mock()
		response.raise_for_status.return_value = None
		response.json.return_value = [
			{"page": 1},
			[{"value": value, "date": year}],
		]
		return response

	@mock.patch("ingestion.fetchers.world_bank._index_world_bank_evidence")
	@mock.patch("ingestion.fetchers.world_bank.httpx.Client")
	def test_fetch_world_bank_indicators_creates_and_updates(self, client_cls, _index):
		client = client_cls.return_value.__enter__.return_value
		client.get.return_value = self._wb_response()

		with mock.patch.dict(world_bank.INDICATORS, {"X.TEST": (EconomicIndicator.IndicatorType.INFLATION, "Inflation")}, clear=True):
			first = world_bank.fetch_world_bank_indicators(country_codes=["UG"])
			second = world_bank.fetch_world_bank_indicators(country_codes=["UG"])

		self.assertEqual(first["created"], 1)
		self.assertEqual(second["updated"], 1)
		self.assertEqual(EconomicIndicator.objects.count(), 1)

	@mock.patch("ingestion.fetchers.world_bank._index_world_bank_evidence")
	@mock.patch("ingestion.fetchers.world_bank.httpx.Client")
	def test_fetch_world_bank_indicators_handles_http_and_payload_errors(self, client_cls, _index):
		bad_http = mock.Mock()
		bad_http.raise_for_status.side_effect = httpx.HTTPError("unavailable")
		bad_payload = mock.Mock()
		bad_payload.raise_for_status.return_value = None
		bad_payload.json.return_value = {"unexpected": True}
		client = client_cls.return_value.__enter__.return_value
		client.get.side_effect = [bad_http, bad_payload]

		with mock.patch.dict(world_bank.INDICATORS, {
			"A": (EconomicIndicator.IndicatorType.INFLATION, "Inflation"),
			"B": (EconomicIndicator.IndicatorType.GDP_GROWTH, "GDP"),
		}, clear=True):
			result = world_bank.fetch_world_bank_indicators(country_codes=["UG"])

		self.assertEqual(result["created"], 0)
		self.assertEqual(len(result["errors"]), 2)

	def test_fetch_world_bank_as_items_returns_existing_country_only(self):
		with mock.patch("ingestion.fetchers.world_bank.EAC_ISO2", ["UG", "XX"]):
			items = world_bank.fetch_world_bank_as_items()
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].external_id, "wb-country-UG")

	def test_update_risk_snapshots_creates_snapshot(self):
		world_bank._update_risk_snapshots({"UG": [Decimal("12"), Decimal("5")]})
		snapshot = EconomicIndicator.objects.filter(country=self.ug).count()
		self.assertEqual(snapshot, 0)
		self.assertEqual(self.ug.risk_snapshots.count(), 1)


class RetrievalServiceTests(TestCase):
	def setUp(self):
		self.doc_a = EvidenceDocument.objects.create(
			title="Import tax guidance",
			source_url="https://example.com/a",
			country_code="UG",
			category="trade_procedure",
			content="import duty and tax documentation",
			embedding=[0.9, 0.1],
			embedding_dims=2,
			embedding_model="hash:hash-v1",
		)
		self.doc_b = EvidenceDocument.objects.create(
			title="Unrelated notice",
			source_url="https://example.com/b",
			country_code="",
			category="tax",
			content="general update",
			embedding=[0.1, 0.9],
			embedding_dims=2,
			embedding_model="hash:hash-v1",
		)

	def test_tokenize_removes_stopwords(self):
		tokens = retrieval.tokenize("What are the import tax rules in Uganda?")
		self.assertIn("import", tokens)
		self.assertNotIn("what", tokens)

	def test_keyword_and_vector_score(self):
		kw = retrieval._keyword_score(self.doc_a, ["import", "tax"])
		self.assertGreater(kw, Decimal("0"))

		with mock.patch("ingestion.services.retrieval._current_embedding_model", return_value="hash:hash-v1"):
			vec = retrieval._vector_score(self.doc_a, [0.9, 0.1])
			self.assertGreater(vec, Decimal("0"))

		with mock.patch("ingestion.services.retrieval._current_embedding_model", return_value="openai:x"):
			mismatch = retrieval._vector_score(self.doc_a, [0.9, 0.1])
			self.assertEqual(mismatch, Decimal("0"))

	def test_pgvector_search_returns_empty_on_non_postgres(self):
		self.assertEqual(retrieval._pgvector_search("q", "UG", 5), [])

	@mock.patch("ingestion.services.retrieval._current_embedding_model", return_value="hash:hash-v1")
	@mock.patch("ingestion.services.retrieval._query_embedding", return_value=[0.1, 0.2])
	@mock.patch("ingestion.services.retrieval.connection")
	def test_pgvector_search_postgres_paths_and_threshold_filter(self, conn, _embed, _model):
		conn.vendor = "postgresql"

		schema_cursor = mock.Mock()
		schema_cursor.fetchone.return_value = (1,)
		schema_ctx = mock.Mock()
		schema_ctx.__enter__ = mock.Mock(return_value=schema_cursor)
		schema_ctx.__exit__ = mock.Mock(return_value=False)

		query_cursor = mock.Mock()
		query_cursor.fetchall.return_value = [(1, 0.05), (2, 0.8)]
		query_ctx = mock.Mock()
		query_ctx.__enter__ = mock.Mock(return_value=query_cursor)
		query_ctx.__exit__ = mock.Mock(return_value=False)

		conn.cursor.side_effect = [schema_ctx, query_ctx]

		hits = retrieval._pgvector_search("import question", "UG", 5)
		self.assertEqual(hits, [(2, 0.8)])
		self.assertIn("country_code IN", query_cursor.execute.call_args.args[0])

	@mock.patch("ingestion.services.retrieval._current_embedding_model", return_value="hash:hash-v1")
	@mock.patch("ingestion.services.retrieval._query_embedding", return_value=[0.1, 0.2])
	@mock.patch("ingestion.services.retrieval.connection")
	def test_pgvector_search_returns_empty_when_column_missing_or_query_errors(self, conn, _embed, _model):
		conn.vendor = "postgresql"

		no_col_cursor = mock.Mock()
		no_col_cursor.fetchone.return_value = None
		no_col_ctx = mock.Mock()
		no_col_ctx.__enter__ = mock.Mock(return_value=no_col_cursor)
		no_col_ctx.__exit__ = mock.Mock(return_value=False)
		conn.cursor.return_value = no_col_ctx
		self.assertEqual(retrieval._pgvector_search("q", "", 3), [])

		schema_cursor = mock.Mock()
		schema_cursor.fetchone.return_value = (1,)
		schema_ctx = mock.Mock()
		schema_ctx.__enter__ = mock.Mock(return_value=schema_cursor)
		schema_ctx.__exit__ = mock.Mock(return_value=False)

		query_cursor = mock.Mock()
		query_cursor.execute.side_effect = RuntimeError("db down")
		query_ctx = mock.Mock()
		query_ctx.__enter__ = mock.Mock(return_value=query_cursor)
		query_ctx.__exit__ = mock.Mock(return_value=False)

		conn.cursor.side_effect = [schema_ctx, query_ctx]
		self.assertEqual(retrieval._pgvector_search("q", "", 3), [])

	@mock.patch("ingestion.services.retrieval.resolve_provider", return_value="hash")
	@mock.patch("ingestion.services.retrieval._query_embedding", return_value=[0.9, 0.1])
	@mock.patch("ingestion.services.retrieval._pgvector_search", return_value=[])
	def test_search_evidence_hybrid_and_keyword_methods(self, _pg, _embed, _provider):
		with mock.patch("ingestion.services.retrieval._current_embedding_model", return_value="hash:hash-v1"):
			matches, method = retrieval.search_evidence("import tax guidance", country_code="UG", limit=5)

		self.assertTrue(matches)
		self.assertTrue(method.startswith("hybrid+"))

		self.doc_a.embedding = []
		self.doc_a.save(update_fields=["embedding"])
		self.doc_b.embedding = []
		self.doc_b.save(update_fields=["embedding"])
		matches2, method2 = retrieval.search_evidence("general update", limit=5)
		self.assertEqual(method2, "keyword")
		self.assertTrue(matches2)

	@mock.patch("ingestion.services.retrieval.resolve_provider", return_value="hash")
	@mock.patch("ingestion.services.retrieval._query_embedding", return_value=[0.1, 0.1])
	@mock.patch("ingestion.services.retrieval._pgvector_search", return_value=[])
	@mock.patch("ingestion.services.retrieval._vector_score", return_value=Decimal("0.9"))
	def test_search_evidence_zeroes_mismatched_model_vector_before_threshold(
		self, _vec, _pg, _embed, _provider
	):
		self.doc_a.embedding_model = "openai:text-embedding-3-small"
		self.doc_a.category = "tax"
		self.doc_a.title = "Completely unrelated"
		self.doc_a.content = "plain body without keyword matches"
		self.doc_a.save(update_fields=["embedding_model", "category", "title", "content"])
		self.doc_b.embedding_model = "openai:text-embedding-3-small"
		self.doc_b.title = "Also unrelated"
		self.doc_b.content = "plain body without keyword matches"
		self.doc_b.save(update_fields=["embedding_model", "title", "content"])

		with mock.patch("ingestion.services.retrieval._current_embedding_model", return_value="hash:hash-v1"):
			matches, method = retrieval.search_evidence("import-tax-match-token", min_score=Decimal("0.5"))

		self.assertFalse(matches)
		self.assertEqual(method, "keyword")

	@mock.patch("ingestion.services.retrieval.resolve_provider", return_value="hash")
	@mock.patch("ingestion.services.retrieval._pgvector_search", return_value=[(999999, 0.9)])
	def test_search_evidence_pgvector_path(self, _pg, _provider):
		matches, method = retrieval.search_evidence("import", limit=2)
		self.assertEqual(matches, [])
		self.assertEqual(method, "pgvector+hash")

	def test_best_excerpt_and_synthesize_answer(self):
		short = retrieval.best_excerpt("abc", ["x"], max_len=10)
		self.assertEqual(short, "abc")

		long_text = "x" * 600
		excerpt = retrieval.best_excerpt(long_text, ["zzz"], max_len=50)
		self.assertEqual(len(excerpt), 50)

		empty = retrieval.synthesize_answer("q", [])
		self.assertEqual(empty, "")

		one = retrieval.synthesize_answer("import", [(self.doc_a, Decimal("1.0"))])
		self.assertIn("Based on", one)

		two = retrieval.synthesize_answer("import", [(self.doc_a, Decimal("1.0")), (self.doc_b, Decimal("0.9"))])
		self.assertIn("supporting source", two)

	def test_best_excerpt_token_match_returns_window_around_token(self):
		content = ("a" * 130) + " import-rule " + ("z" * 200)
		excerpt = retrieval.best_excerpt(content, ["import"], max_len=140)
		self.assertEqual(len(excerpt), 140)
		self.assertIn("import", excerpt.lower())
