from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from assistant.models import EvidenceDocument
from core.models import Country
from regulatory.models import RegulatoryChange
from trade.models import TradeProcedure
from vendors.models import Vendor


class InitializeDemoDataCommandTests(TestCase):
    @mock.patch("core.management.commands.initialize_demo_data.call_command")
    def test_empty_database_loads_embeds_and_verifies(self, mocked_call_command):
        call_command("initialize_demo_data")

        self.assertEqual(
            mocked_call_command.call_args_list,
            [
                mock.call("load_initial_data"),
                mock.call("embed_evidence", force=True),
                mock.call("verify_data"),
            ],
        )

    @mock.patch("core.management.commands.initialize_demo_data.Command._has_required_data", return_value=True)
    @mock.patch("core.management.commands.initialize_demo_data.call_command")
    def test_populated_database_only_runs_verification(
        self,
        mocked_call_command,
        _mocked_has_required_data,
    ):
        call_command("initialize_demo_data")

        mocked_call_command.assert_called_once_with("verify_data")


class InitializeDemoDataIntegrationTests(TestCase):
    @override_settings(EMBEDDING_PROVIDER="hash")
    def test_real_initializer_populates_and_is_idempotent(self):
        call_command("initialize_demo_data", verbosity=0)
        first_counts = (
            Country.objects.count(),
            Vendor.objects.count(),
            RegulatoryChange.objects.count(),
            TradeProcedure.objects.count(),
            EvidenceDocument.objects.count(),
        )

        call_command("initialize_demo_data", verbosity=0)

        self.assertEqual(
            (
                Country.objects.count(),
                Vendor.objects.count(),
                RegulatoryChange.objects.count(),
                TradeProcedure.objects.count(),
                EvidenceDocument.objects.count(),
            ),
            first_counts,
        )
        self.assertGreaterEqual(first_counts[0], 6)
        self.assertGreaterEqual(first_counts[1], 4)
        self.assertGreaterEqual(first_counts[2], 1)
        self.assertGreaterEqual(first_counts[3], 1)
        self.assertGreaterEqual(first_counts[4], 1)