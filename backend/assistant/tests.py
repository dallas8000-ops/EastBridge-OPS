from datetime import date
from decimal import Decimal
import types
import sys
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership

from . import llm
from . import embeddings
from .models import AssistantQuery, Citation, EvidenceDocument
from .tasks import _needs_reembed, _sync_pgvector, embed_all_evidence
from .views import _clamp_relevance_score


class AssistantAskFlowTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(username="assistant-user", password="StrongPass123")
		self.org = Organization.objects.create(name="Assist Org", slug="assist-org", origin_country="DE")
		OrganizationMembership.objects.create(user=self.user, organization=self.org)
		token = self.client.post(
			"/api/v1/auth/login/",
			{"username": "assistant-user", "password": "StrongPass123"},
			format="json",
		).json()["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

	def _doc(self, suffix="1"):
		return EvidenceDocument.objects.create(
			title=f"Doc {suffix}",
			source_url=f"https://example.com/doc-{suffix}",
			country_code="UG",
			category="tax",
			content="tax filing update and import process guidance",
			published_at=date(2026, 1, 1),
		)

	@mock.patch("assistant.views.search_evidence", return_value=([], "keyword"))
	def test_ask_returns_refusal_when_no_matches(self, _search_evidence):
		resp = self.client.post("/api/v1/assistant/queries/ask/", {"question": "What changed?"}, format="json")
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertFalse(data["has_sufficient_evidence"])
		self.assertIn("Insufficient source evidence", data["refusal_reason"])

	@mock.patch("assistant.views.generate_grounded_answer", return_value="Grounded answer [1]")
	@mock.patch("assistant.views.search_evidence")
	def test_ask_creates_citations_and_uses_llm_answer(self, search_evidence, _llm):
		doc = self._doc("a")
		search_evidence.return_value = ([(doc, Decimal("1.25"))], "hybrid+hash")

		resp = self.client.post(
			"/api/v1/assistant/queries/ask/",
			{"question": "What tax changes apply?", "country_code": "ug"},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org.id),
		)
		self.assertEqual(resp.status_code, 201)
		body = resp.json()
		self.assertEqual(body["answer"], "Grounded answer [1]")
		self.assertTrue(body["retrieval_method"].endswith("+llm"))
		self.assertEqual(Citation.objects.count(), 1)

	@mock.patch("assistant.views.synthesize_answer", return_value="Template answer")
	@mock.patch("assistant.views.generate_grounded_answer", return_value=None)
	@mock.patch("assistant.views.search_evidence")
	def test_ask_falls_back_to_template_synthesis(self, search_evidence, _llm, _synth):
		doc = self._doc("b")
		search_evidence.return_value = ([(doc, Decimal("0.87"))], "hybrid+hash")

		resp = self.client.post(
			"/api/v1/assistant/queries/ask/",
			{"question": "What import rules apply?"},
			format="json",
		)
		self.assertEqual(resp.status_code, 201)
		self.assertEqual(resp.json()["answer"], "Template answer")

	def test_clamp_relevance_score_handles_bounds_and_invalid(self):
		self.assertEqual(_clamp_relevance_score(Decimal("1000000")), Decimal("999999.9999"))
		self.assertEqual(_clamp_relevance_score(Decimal("-4")), Decimal("0"))
		self.assertEqual(_clamp_relevance_score("not-a-number"), Decimal("0"))

	def test_query_list_is_scoped_to_user_organization(self):
		other_org = Organization.objects.create(name="Other", slug="other", origin_country="KE")
		AssistantQuery.objects.create(question="Org A", organization=self.org)
		AssistantQuery.objects.create(question="Org B", organization=other_org)

		resp = self.client.get("/api/v1/assistant/queries/", HTTP_X_ORGANIZATION_ID=str(self.org.id))
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertEqual(data["count"], 1)
		self.assertEqual(data["results"][0]["question"], "Org A")


class AssistantLlmTests(TestCase):
	def _doc(self):
		return EvidenceDocument(
			title="Revenue guidance",
			source_url="https://example.com/revenue",
			country_code="UG",
			category="tax",
			content="Revenue authority guidance on filing obligations.",
			published_at=date(2026, 1, 2),
		)

	@override_settings(ANSWER_PROVIDER="template")
	def test_should_use_llm_false_for_template_provider(self):
		self.assertFalse(llm.should_use_llm())

	def test_generate_grounded_answer_returns_none_without_matches(self):
		self.assertIsNone(llm.generate_grounded_answer("question", []))

	@mock.patch("assistant.llm.should_use_llm", return_value=True)
	@mock.patch("assistant.llm.openai_api_key", return_value="sk-valid-key-1234567890")
	@mock.patch("assistant.llm.httpx.post")
	def test_generate_grounded_answer_returns_stripped_text(self, post, _key, _enabled):
		response = mock.Mock()
		response.raise_for_status.return_value = None
		response.json.return_value = {
			"choices": [{"message": {"content": "  grounded response [1]  "}}]
		}
		post.return_value = response

		answer = llm.generate_grounded_answer("question", [(self._doc(), Decimal("1"))])
		self.assertEqual(answer, "grounded response [1]")

	@mock.patch("assistant.llm.should_use_llm", return_value=True)
	@mock.patch("assistant.llm.openai_api_key", return_value="sk-valid-key-1234567890")
	@mock.patch("assistant.llm.httpx.post", side_effect=RuntimeError("timeout"))
	def test_generate_grounded_answer_returns_none_on_http_error(self, _post, _key, _enabled):
		answer = llm.generate_grounded_answer("question", [(self._doc(), Decimal("1"))])
		self.assertIsNone(answer)


class EmbeddingsUnitTests(TestCase):
	def test_openai_key_validation_and_provider_config(self):
		with self.settings(OPENAI_API_KEY="", EMBEDDING_PROVIDER="openai"):
			self.assertFalse(embeddings.is_openai_key_configured())
			self.assertIsNotNone(embeddings.provider_config_error())

		with self.settings(OPENAI_API_KEY="sk-valid-key-1234567890", EMBEDDING_PROVIDER="openai"):
			self.assertTrue(embeddings.is_openai_key_configured())

	def test_openai_key_validation_rejects_ellipsis_suffix(self):
		with self.settings(OPENAI_API_KEY="sk-sample-key-1234567890...", EMBEDDING_PROVIDER="openai"):
			self.assertFalse(embeddings.is_openai_key_configured())

	def test_fastembed_availability_and_provider_config_error_fastembed(self):
		real_import = __import__

		def fake_import(name, *args, **kwargs):
			if name == "fastembed":
				raise ImportError("missing")
			return real_import(name, *args, **kwargs)

		with mock.patch("builtins.__import__", side_effect=fake_import):
			self.assertFalse(embeddings._fastembed_available())

		with self.settings(EMBEDDING_PROVIDER="fastembed"):
			with mock.patch("assistant.embeddings._fastembed_available", return_value=False):
				err = embeddings.provider_config_error()
				self.assertIn("fastembed is not installed", err)

	@mock.patch("assistant.embeddings._fastembed_available", return_value=False)
	def test_resolve_provider_paths(self, _fastembed):
		with self.settings(EMBEDDING_PROVIDER="hash"):
			self.assertEqual(embeddings.resolve_provider(), "hash")
		with self.settings(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY=""):
			self.assertEqual(embeddings.resolve_provider(), "hash")
		with self.settings(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY="sk-valid-key-1234567890"):
			self.assertEqual(embeddings.resolve_provider(), "openai")

	def test_resolve_provider_auto_and_fastembed_and_fallback_helper(self):
		with self.settings(EMBEDDING_PROVIDER="fastembed"):
			with mock.patch("assistant.embeddings._fastembed_available", return_value=True):
				self.assertEqual(embeddings.resolve_provider(), "fastembed")

		with self.settings(EMBEDDING_PROVIDER="auto", OPENAI_API_KEY="sk-valid-key-1234567890"):
			with mock.patch("assistant.embeddings._fastembed_available", return_value=False):
				self.assertEqual(embeddings.resolve_provider(), "openai")

		with self.settings(EMBEDDING_PROVIDER="auto", OPENAI_API_KEY=""):
			with mock.patch("assistant.embeddings._fastembed_available", return_value=False):
				self.assertEqual(embeddings.resolve_provider(), "hash")

		with mock.patch("assistant.embeddings._fastembed_available", return_value=True):
			self.assertEqual(embeddings._fallback_after_openai(), "fastembed")

	def test_embed_text_hash_and_empty(self):
		vec, provider, model = embeddings.embed_text("abc", provider="hash")
		self.assertEqual(provider, "hash")
		self.assertEqual(model, "hash-v1")
		self.assertEqual(len(vec), embeddings.EMBEDDING_DIM)

		empty_hash = embeddings._embed_hash("  ")
		self.assertTrue(all(v == 0.0 for v in empty_hash))

		empty_vec, empty_provider, empty_model = embeddings.embed_text("   ")
		self.assertEqual(empty_provider, "hash")
		self.assertEqual(empty_model, "hash-v1")
		self.assertTrue(all(v == 0.0 for v in empty_vec))

	def test_get_fastembed_model_and_embed_fastembed_branches(self):
		class FakeTextEmbedding:
			def __init__(self, model_name):
				self.model_name = model_name

		fake_mod = types.SimpleNamespace(TextEmbedding=FakeTextEmbedding)
		embeddings._get_fastembed_model.cache_clear()
		with self.settings(EMBEDDING_MODEL="my-model"):
			with mock.patch.dict(sys.modules, {"fastembed": fake_mod}):
				model = embeddings._get_fastembed_model()
				self.assertEqual(model.model_name, "my-model")

		class VecWithToList:
			def tolist(self):
				return [0.3, 0.7]

		model_with_tolist = mock.Mock()
		model_with_tolist.embed.return_value = [VecWithToList()]
		with mock.patch("assistant.embeddings._get_fastembed_model", return_value=model_with_tolist):
			self.assertEqual(embeddings._embed_fastembed("hello"), [0.3, 0.7])

		model_plain = mock.Mock()
		model_plain.embed.return_value = [(0.4, 0.6)]
		with mock.patch("assistant.embeddings._get_fastembed_model", return_value=model_plain):
			self.assertEqual(embeddings._embed_fastembed("hello"), [0.4, 0.6])

	def test_embed_openai_raises_without_key(self):
		with self.settings(OPENAI_API_KEY=""):
			with self.assertRaises(ValueError):
				embeddings._embed_openai("hello")

	@mock.patch("httpx.post")
	def test_embed_openai_success_and_fallback(self, post):
		response = mock.Mock()
		response.raise_for_status.return_value = None
		response.json.return_value = {"data": [{"embedding": [0.2, 0.8]}]}
		post.return_value = response

		with self.settings(OPENAI_API_KEY="sk-valid-key-1234567890", OPENAI_EMBEDDING_MODEL="text-embedding-3-small"):
			vec, provider, model = embeddings.embed_text("hello", provider="openai")
		self.assertEqual(vec, [0.2, 0.8])
		self.assertEqual(provider, "openai")
		self.assertEqual(model, "text-embedding-3-small")

		post.side_effect = RuntimeError("down")
		vec2, provider2, model2 = embeddings.embed_text("hello", provider="openai", allow_fallback=True)
		self.assertEqual(provider2, "hash")
		self.assertEqual(model2, "hash-v1")
		self.assertEqual(len(vec2), embeddings.EMBEDDING_DIM)

		with self.assertRaises(RuntimeError):
			embeddings.embed_text("hello", provider="openai", allow_fallback=False)

	@mock.patch("assistant.embeddings._embed_fastembed", return_value=[0.6, 0.8])
	def test_embed_text_fastembed_provider_and_model_name(self, _embed_fastembed):
		with self.settings(EMBEDDING_MODEL="bge-mini"):
			vec, provider, model = embeddings.embed_text("hello", provider="fastembed")
		self.assertEqual(vec, [0.6, 0.8])
		self.assertEqual(provider, "fastembed")
		self.assertEqual(model, "bge-mini")

	def test_active_model_name_fastembed_branch(self):
		with self.settings(EMBEDDING_MODEL="bge-tiny"):
			self.assertEqual(embeddings.active_model_name("fastembed"), "bge-tiny")

	def test_cosine_similarity(self):
		self.assertAlmostEqual(embeddings.cosine_similarity([1, 0], [1, 0]), 1.0, places=6)
		self.assertEqual(embeddings.cosine_similarity([1, 0], [0, 1]), 0.0)
		self.assertEqual(embeddings.cosine_similarity([], [1]), 0.0)
		self.assertEqual(embeddings.cosine_similarity([0, 0], [1, 0]), 0.0)


class AssistantTaskUnitTests(TestCase):
	def test_needs_reembed_force_or_model_or_dims(self):
		doc = EvidenceDocument(
			title="Doc",
			content="content",
			embedding=[0.1],
			embedding_dims=1,
			embedding_model="hash:hash-v1",
		)

		with self.settings(EMBEDDING_PROVIDER="hash"):
			self.assertTrue(_needs_reembed(doc, force=True))
			doc.embedding_dims = embeddings.EMBEDDING_DIM
			doc.embedding = [0.0] * embeddings.EMBEDDING_DIM
			self.assertFalse(_needs_reembed(doc, force=False))
			doc.embedding_model = "openai:text-embedding-3-small"
			self.assertTrue(_needs_reembed(doc, force=False))

	@mock.patch("assistant.tasks.embed_text", return_value=([0.1, 0.2], "hash", "hash-v1"))
	@mock.patch("assistant.tasks._sync_pgvector")
	def test_embed_document_updates_and_skips(self, sync_pg, _embed_text):
		doc = EvidenceDocument.objects.create(
			title="Doc",
			source_url="https://example.com/doc",
			country_code="UG",
			category="tax",
			content="content",
			embedding=[],
			embedding_dims=0,
			embedding_model="",
		)

		from .tasks import embed_document

		self.assertTrue(embed_document(doc, force=True))
		doc.refresh_from_db()
		self.assertEqual(doc.embedding_dims, 2)
		self.assertEqual(doc.embedding_model, "hash:hash-v1")
		sync_pg.assert_called_once()

		doc.embedding = [0.0] * embeddings.EMBEDDING_DIM
		doc.embedding_dims = embeddings.EMBEDDING_DIM
		doc.embedding_model = "hash:hash-v1"
		doc.save(update_fields=["embedding", "embedding_dims", "embedding_model"])
		with self.settings(EMBEDDING_PROVIDER="hash"):
			self.assertFalse(embed_document(doc, force=False))

	def test_sync_pgvector_branches(self):
		_sync_pgvector(1, [])
		_sync_pgvector(1, [0.1])

		with mock.patch("assistant.tasks.connection") as conn:
			conn.vendor = "postgresql"
			conn.cursor.side_effect = RuntimeError("db down")
			_sync_pgvector(1, [0.0] * embeddings.EMBEDDING_DIM)

	@mock.patch("assistant.tasks.embed_document")
	@mock.patch("assistant.tasks.active_model_name", return_value="hash-v1")
	@mock.patch("assistant.tasks.resolve_provider", return_value="hash")
	def test_embed_all_evidence_counts(self, _provider, _model, embed_doc):
		EvidenceDocument.objects.create(
			title="D1", source_url="https://e/1", country_code="UG", category="tax", content="a"
		)
		EvidenceDocument.objects.create(
			title="D2", source_url="https://e/2", country_code="UG", category="tax", content="b"
		)
		embed_doc.side_effect = [True, False]

		result = embed_all_evidence(force=True)
		self.assertEqual(result["embedded"], 1)
		self.assertEqual(result["skipped"], 1)
		self.assertEqual(result["provider"], "hash")
