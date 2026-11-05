"""Tests for the stripe_billing scaffold.

The app is not yet wired into INSTALLED_APPS / the root URLconf, so these tests supply their own
URLconf and template directory. Stripe and the Postgres-only SQL are replaced with fakes, so no
network, Stripe account or Postgres server is needed.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import include, path

# The stripe SDK is not a project dependency yet; every test fakes it, so a stand-in module is
# enough for the scaffold's top-level `import stripe` when the real SDK is absent.
if importlib.util.find_spec("stripe") is None:
    sys.modules["stripe"] = ModuleType("stripe")

client = importlib.import_module("stripe_billing.client")
db = importlib.import_module("stripe_billing.db")
webhook_handlers = importlib.import_module("stripe_billing.webhook_handlers")

urlpatterns = [path("stripe/", include("stripe_billing.urls"))]

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _templates_with_scaffold():
    configured = [dict(entry) for entry in settings.TEMPLATES]
    configured[0]["DIRS"] = [*configured[0].get("DIRS", []), TEMPLATE_DIR]
    return configured


class FakeStripeError(Exception):
    pass


class FakeSignatureError(Exception):
    pass


def make_stripe(**overrides):
    """Minimal stand-in for the stripe SDK module."""
    fake = SimpleNamespace(
        error=SimpleNamespace(StripeError=FakeStripeError, SignatureVerificationError=FakeSignatureError),
        Webhook=SimpleNamespace(construct_event=mock.Mock()),
        checkout=SimpleNamespace(Session=SimpleNamespace(create=mock.Mock(), retrieve=mock.Mock())),
        billing_portal=SimpleNamespace(Session=SimpleNamespace(create=mock.Mock())),
    )
    for key, value in overrides.items():
        setattr(fake, key, value)
    return fake


class FakeCursor:
    def __init__(self, row=None):
        self.row = row
        self.calls: list[tuple[str, list]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))

    def fetchone(self):
        return self.row


class ClientTests(SimpleTestCase):
    def test_key_is_read_and_stripped(self):
        with mock.patch.dict(os.environ, {"STRIPE_SECRET_KEY": "  test-key-value  "}):
            self.assertEqual(client.stripe_api_key(), "test-key-value")

    def test_missing_key_is_empty_string(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(client.stripe_api_key(), "")

    def test_get_stripe_requires_a_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                client.get_stripe()

    def test_get_stripe_configures_sdk(self):
        fake_sdk = SimpleNamespace(api_key=None)
        with mock.patch.dict(os.environ, {"STRIPE_SECRET_KEY": "test-key-value"}):
            with mock.patch.object(client, "stripe_sdk", fake_sdk):
                self.assertIs(client.get_stripe(), fake_sdk)
        self.assertEqual(fake_sdk.api_key, "test-key-value")


@override_settings(ROOT_URLCONF=__name__, TEMPLATES=_templates_with_scaffold())
class ViewTestBase(TestCase):
    def setUp(self):
        self.fake = make_stripe()
        patcher = mock.patch("stripe_billing.views.get_stripe", return_value=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def login(self, username="bob"):
        user = User.objects.create_user(username, f"{username}@example.test", "pw-for-tests-only")
        self.client.force_login(user)
        return user

    def set_session_customer(self, customer_id):
        session = self.client.session
        session["stripe_customer_id"] = customer_id
        session.save()


class HealthViewTests(ViewTestBase):
    def test_health_view(self):
        from .health_views import health

        response = health(None)
        body = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["checks"], {"app": "ok"})
        self.assertTrue(body["timestamp"])


class WebhookViewTests(ViewTestBase):
    url = "/stripe/webhook"

    def post(self, signature="sig"):
        extra = {"HTTP_STRIPE_SIGNATURE": signature} if signature else {}
        return self.client.post(self.url, data="{}", content_type="application/json", **extra)

    def test_get_is_rejected(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_missing_signature_is_rejected(self):
        with mock.patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_for_tests"}):
            self.assertEqual(self.post(signature=None).status_code, 400)

    def test_missing_secret_is_rejected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.post().status_code, 400)

    def test_invalid_payload_is_rejected(self):
        self.fake.Webhook.construct_event.side_effect = ValueError("bad json")
        with mock.patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_for_tests"}):
            response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"Invalid payload")

    def test_invalid_signature_is_rejected(self):
        self.fake.Webhook.construct_event.side_effect = FakeSignatureError("nope")
        with mock.patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_for_tests"}):
            response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"Invalid signature")

    def test_handler_failure_returns_500(self):
        self.fake.Webhook.construct_event.return_value = {"id": "evt_1", "type": "x"}
        with mock.patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_for_tests"}):
            with mock.patch("stripe_billing.views.dispatch_stripe_event", side_effect=RuntimeError("db down")):
                response = self.post()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "handler failed"})

    def test_valid_event_is_dispatched(self):
        event = {"id": "evt_1", "type": "checkout.session.completed"}
        self.fake.Webhook.construct_event.return_value = event
        with mock.patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_for_tests"}):
            with mock.patch("stripe_billing.views.dispatch_stripe_event") as dispatch:
                response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"received": True})
        dispatch.assert_called_once_with(event)


class CheckoutViewTests(ViewTestBase):
    url = "/stripe/checkout"

    def setUp(self):
        super().setUp()
        self.fake.checkout.Session.create.return_value = SimpleNamespace(url="https://checkout.example.test/s/1")

    def test_price_id_is_required(self):
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)

    def test_invalid_json_body_counts_as_missing_price(self):
        response = self.client.post(self.url, data="{not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_anonymous_json_checkout_redirects_to_stripe(self):
        body = json.dumps({"priceId": "price_1", "customerEmail": "a@example.test"})
        with mock.patch.dict(os.environ, {"APP_URL": "https://app.example.test"}):
            response = self.client.post(self.url, data=body, content_type="application/json")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.example.test/s/1")
        kwargs = self.fake.checkout.Session.create.call_args.kwargs
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(kwargs["customer_email"], "a@example.test")
        self.assertIsNone(kwargs["client_reference_id"])
        self.assertEqual(kwargs["line_items"], [{"price": "price_1", "quantity": 1}])
        self.assertTrue(kwargs["success_url"].startswith("https://app.example.test/stripe/success/"))
        self.assertEqual(kwargs["cancel_url"], "https://app.example.test/stripe/pricing/")

    def test_authenticated_form_checkout_uses_user_details(self):
        user = self.login()
        response = self.client.post(self.url, {"priceId": "price_2"})
        self.assertEqual(response.status_code, 302)
        kwargs = self.fake.checkout.Session.create.call_args.kwargs
        self.assertEqual(kwargs["client_reference_id"], str(user.pk))
        self.assertEqual(kwargs["customer_email"], "bob@example.test")

    def test_default_app_url_is_used_when_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "APP_URL"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.client.post(self.url, {"priceId": "price_3"})
        kwargs = self.fake.checkout.Session.create.call_args.kwargs
        self.assertTrue(kwargs["cancel_url"].endswith("/stripe/pricing/"))
        self.assertTrue(kwargs["cancel_url"].startswith("https://"))


class PortalViewTests(ViewTestBase):
    url = "/stripe/portal"

    def setUp(self):
        super().setUp()
        self.fake.billing_portal.Session.create.return_value = SimpleNamespace(url="https://portal.example.test/p/1")

    def test_customer_is_required(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "customerId required"})

    def test_explicit_customer_id(self):
        response = self.client.post(self.url, {"customerId": "cus_1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://portal.example.test/p/1")
        kwargs = self.fake.billing_portal.Session.create.call_args.kwargs
        self.assertEqual(kwargs["customer"], "cus_1")
        self.assertTrue(kwargs["return_url"].endswith("/stripe/account/"))

    def test_customer_from_session(self):
        self.set_session_customer("cus_session")
        self.client.post(self.url, {})
        self.assertEqual(self.fake.billing_portal.Session.create.call_args.kwargs["customer"], "cus_session")

    def test_customer_from_database_for_logged_in_user(self):
        user = self.login()
        with mock.patch("stripe_billing.db.get_stripe_customer_for_user", return_value="cus_db") as lookup:
            self.client.post(self.url, {})
        lookup.assert_called_once_with(user.pk)
        self.assertEqual(self.fake.billing_portal.Session.create.call_args.kwargs["customer"], "cus_db")


class SessionInfoViewTests(ViewTestBase):
    url = "/stripe/session"

    def post_json(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_invalid_json(self):
        response = self.client.post(self.url, data="{nope", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid JSON"})

    def test_session_id_required(self):
        response = self.post_json({})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "sessionId required"})

    def test_stripe_error_is_reported(self):
        self.fake.checkout.Session.retrieve.side_effect = FakeStripeError("no such session")
        response = self.post_json({"sessionId": "cs_1"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "no such session"})

    def test_string_customer(self):
        self.fake.checkout.Session.retrieve.return_value = SimpleNamespace(
            customer="cus_1", customer_email="a@example.test", status="complete"
        )
        response = self.post_json({"sessionId": "cs_1"})
        self.assertEqual(response.json(), {"customerId": "cus_1", "email": "a@example.test", "status": "complete"})

    def test_expanded_customer_object(self):
        self.fake.checkout.Session.retrieve.return_value = SimpleNamespace(
            customer=SimpleNamespace(id="cus_2"), customer_email=None, status="open"
        )
        self.assertEqual(self.post_json({"sessionId": "cs_2"}).json()["customerId"], "cus_2")


class StripeMeViewTests(ViewTestBase):
    url = "/stripe/me"

    def test_anonymous_gets_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"customerId": None, "source": None})

    def test_customer_from_database_with_subscription(self):
        self.login()
        subscription = {"subscriptionId": "sub_1", "status": "active", "tier": "pro", "currentPeriodEnd": None}
        with mock.patch("stripe_billing.db.get_stripe_customer_for_user", return_value="cus_db"):
            with mock.patch("stripe_billing.db.get_active_subscription_for_customer", return_value=subscription):
                body = self.client.get(self.url).json()
        self.assertEqual(body, {"customerId": "cus_db", "source": "database", "subscription": subscription})

    def test_customer_from_session_without_subscription(self):
        self.login()
        self.set_session_customer("cus_session")
        with mock.patch("stripe_billing.db.get_stripe_customer_for_user", return_value=None):
            with mock.patch("stripe_billing.db.get_active_subscription_for_customer", return_value=None):
                body = self.client.get(self.url).json()
        self.assertEqual(body, {"customerId": "cus_session", "source": "session"})

    def test_no_customer_anywhere(self):
        self.login()
        with mock.patch("stripe_billing.db.get_stripe_customer_for_user", return_value=None):
            body = self.client.get(self.url).json()
        self.assertEqual(body, {"customerId": None, "source": None})


class PageViewTests(ViewTestBase):
    def test_pricing_page_lists_checkout_forms(self):
        response = self.client.get("/stripe/pricing")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose your plan")
        self.assertContains(response, 'action="/stripe/checkout"')

    def test_success_page_without_session_id(self):
        response = self.client.get("/stripe/success")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment successful")
        self.fake.checkout.Session.retrieve.assert_not_called()

    def test_success_page_stores_customer_in_session(self):
        self.fake.checkout.Session.retrieve.return_value = SimpleNamespace(customer="cus_paid")
        response = self.client.get("/stripe/success", {"session_id": "cs_1"})
        self.assertContains(response, "Reference: cs_1")
        self.assertEqual(self.client.session["stripe_customer_id"], "cus_paid")

    def test_success_page_with_expanded_customer(self):
        self.fake.checkout.Session.retrieve.return_value = SimpleNamespace(customer=SimpleNamespace(id="cus_obj"))
        self.client.get("/stripe/success", {"session_id": "cs_2"})
        self.assertEqual(self.client.session["stripe_customer_id"], "cus_obj")

    def test_success_page_without_customer_keeps_session_clean(self):
        self.fake.checkout.Session.retrieve.return_value = SimpleNamespace(customer=None)
        self.client.get("/stripe/success", {"session_id": "cs_3"})
        self.assertNotIn("stripe_customer_id", self.client.session)

    def test_success_page_survives_stripe_errors(self):
        self.fake.checkout.Session.retrieve.side_effect = FakeStripeError("boom")
        response = self.client.get("/stripe/success", {"session_id": "cs_4"})
        self.assertEqual(response.status_code, 200)

    def test_account_page_without_customer(self):
        response = self.client.get("/stripe/account")
        self.assertContains(response, "No Stripe customer linked yet")

    def test_account_page_with_session_customer(self):
        self.set_session_customer("cus_session")
        response = self.client.get("/stripe/account")
        self.assertContains(response, "Manage subscription")
        self.assertContains(response, "cus_session")

    def test_account_page_with_database_customer(self):
        self.login()
        with mock.patch("stripe_billing.db.get_stripe_customer_for_user", return_value="cus_db"):
            response = self.client.get("/stripe/account")
        self.assertContains(response, "cus_db")


class DatabaseSyncTests(SimpleTestCase):
    def use_cursor(self, row=None):
        cursor = FakeCursor(row)
        patcher = mock.patch.object(db, "_cursor", return_value=cursor)
        patcher.start()
        self.addCleanup(patcher.stop)
        return cursor

    def run_atomic_free(self):
        patcher = mock.patch.object(db.transaction, "atomic", return_value=mock.MagicMock())
        patcher.start()
        self.addCleanup(patcher.stop)

    def setUp(self):
        self.run_atomic_free()

    def test_cursor_helper_uses_the_django_connection(self):
        with mock.patch.object(db, "connection") as connection:
            self.assertIs(db._cursor(), connection.cursor.return_value)

    def test_link_customer_ignores_sessions_without_customer(self):
        cursor = self.use_cursor()
        db.link_customer_from_checkout({"id": "cs_1"})
        self.assertEqual(cursor.calls, [])

    def test_link_customer_with_user_reference(self):
        cursor = self.use_cursor()
        db.link_customer_from_checkout(
            {"customer": "cus_1", "customer_email": "a@example.test", "client_reference_id": 42}
        )
        sql, params = cursor.calls[0]
        self.assertIn("auth_user_id", sql)
        self.assertEqual(params, ["cus_1", "a@example.test", "42"])

    def test_link_customer_with_metadata_user_and_details_email(self):
        cursor = self.use_cursor()
        db.link_customer_from_checkout(
            {
                "customer": "cus_1",
                "customer_details": {"email": "d@example.test"},
                "metadata": {"userId": "u-7"},
            }
        )
        self.assertEqual(cursor.calls[0][1], ["cus_1", "d@example.test", "u-7"])

    def test_link_customer_without_user_reference(self):
        cursor = self.use_cursor()
        db.link_customer_from_checkout({"customer": "cus_1", "customer_email": "a@example.test"})
        sql, params = cursor.calls[0]
        self.assertNotIn("auth_user_id", sql)
        self.assertEqual(params, ["cus_1", "a@example.test"])

    def test_sync_subscription_full_payload(self):
        cursor = self.use_cursor()
        db.sync_subscription_from_stripe(
            {
                "id": "sub_1",
                "customer": {"id": "cus_1"},
                "items": {"data": [{"price": {"id": "price_1"}}]},
                "status": "active",
                "metadata": {"tier": "pro"},
                "current_period_end": 1_800_000_000,
                "cancel_at_period_end": True,
            }
        )
        params = cursor.calls[0][1]
        self.assertEqual(
            params,
            ["sub_1", "cus_1", "price_1", "active", "pro", datetime.fromtimestamp(1_800_000_000, tz=timezone.utc), True],
        )

    def test_sync_subscription_minimal_payload(self):
        cursor = self.use_cursor()
        db.sync_subscription_from_stripe({"id": "sub_2", "customer": "cus_2", "status": "canceled"})
        self.assertEqual(cursor.calls[0][1], ["sub_2", "cus_2", None, "canceled", None, None, False])

    def test_customer_lookup_for_user(self):
        cursor = self.use_cursor(row=("cus_9",))
        self.assertEqual(db.get_stripe_customer_for_user(5), "cus_9")
        self.assertEqual(cursor.calls[0][1], ["5"])

    def test_customer_lookup_for_unknown_user(self):
        self.use_cursor(row=None)
        self.assertIsNone(db.get_stripe_customer_for_user(5))

    def test_active_subscription_lookup(self):
        period_end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        cursor = self.use_cursor(row=("sub_1", "active", "pro", period_end))
        result = db.get_active_subscription_for_customer("cus_1")
        self.assertEqual(
            result,
            {"subscriptionId": "sub_1", "status": "active", "tier": "pro", "currentPeriodEnd": period_end.isoformat()},
        )
        self.assertEqual(cursor.calls[0][1], ["cus_1"])

    def test_active_subscription_without_period_end(self):
        self.use_cursor(row=("sub_1", "trialing", None, None))
        self.assertIsNone(db.get_active_subscription_for_customer("cus_1")["currentPeriodEnd"])

    def test_no_active_subscription(self):
        self.use_cursor(row=None)
        self.assertIsNone(db.get_active_subscription_for_customer("cus_1"))

    def test_record_webhook_event_stores_event_data(self):
        cursor = self.use_cursor()
        db.record_webhook_event({"id": "evt_1", "type": "ping", "data": {"object": {"a": 1}}})
        self.assertEqual(cursor.calls[0][1], ["evt_1", "ping", json.dumps({"object": {"a": 1}})])

    def test_record_webhook_event_without_data(self):
        cursor = self.use_cursor()
        db.record_webhook_event({"id": "evt_2", "type": "ping"})
        self.assertEqual(cursor.calls[0][1], ["evt_2", "ping", "{}"])


class DispatchTests(SimpleTestCase):
    def dispatch(self, event_type, obj=None):
        event = {"id": "evt_1", "type": event_type, "data": {"object": obj or {}}}
        with mock.patch.object(webhook_handlers.db, "record_webhook_event") as record:
            with mock.patch.object(webhook_handlers.db, "link_customer_from_checkout") as link:
                with mock.patch.object(webhook_handlers.db, "sync_subscription_from_stripe") as sync:
                    webhook_handlers.dispatch_stripe_event(event)
        record.assert_called_once_with(event)
        return link, sync

    def test_checkout_completed_links_customer(self):
        link, sync = self.dispatch("checkout.session.completed", {"customer": "cus_1"})
        link.assert_called_once_with({"customer": "cus_1"})
        sync.assert_not_called()

    def test_subscription_events_sync_subscription(self):
        for event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            with self.subTest(event_type=event_type):
                link, sync = self.dispatch(event_type, {"id": "sub_1"})
                sync.assert_called_once_with({"id": "sub_1"})
                link.assert_not_called()

    def test_payment_failed_and_unknown_events_are_only_recorded(self):
        for event_type in ("invoice.payment_failed", "something.else"):
            with self.subTest(event_type=event_type):
                link, sync = self.dispatch(event_type)
                link.assert_not_called()
                sync.assert_not_called()
