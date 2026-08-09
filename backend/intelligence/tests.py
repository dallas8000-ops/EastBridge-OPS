from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Country

from .models import CountryRiskSnapshot, EconomicIndicator


class IntelligenceApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.ug = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.ke = Country.objects.create(code="KE", name="Kenya", is_eac_member=True)

		EconomicIndicator.objects.create(
			country=self.ug,
			indicator_type=EconomicIndicator.IndicatorType.INFLATION,
			label="Inflation",
			value="6.3",
			period=date(2025, 12, 31),
			source_url="https://example.com/inf",
		)
		EconomicIndicator.objects.create(
			country=self.ug,
			indicator_type=EconomicIndicator.IndicatorType.GDP_GROWTH,
			label="GDP",
			value="4.2",
			period=date(2024, 12, 31),
			source_url="https://example.com/gdp",
		)
		EconomicIndicator.objects.create(
			country=self.ke,
			indicator_type=EconomicIndicator.IndicatorType.INFLATION,
			label="Inflation",
			value="5.1",
			period=date(2025, 12, 31),
			source_url="https://example.com/ke",
		)

		CountryRiskSnapshot.objects.create(
			country=self.ug,
			overall_score="63.20",
			political_risk="61.00",
			regulatory_risk="68.00",
			trade_risk="60.00",
			summary="Moderate risk",
			as_of=date(2026, 1, 1),
		)

	def test_indicator_list_returns_results(self):
		resp = self.client.get("/api/v1/intelligence/indicators/")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 3)

	def test_indicator_filter_by_type(self):
		resp = self.client.get(
			"/api/v1/intelligence/indicators/",
			{"indicator_type": EconomicIndicator.IndicatorType.GDP_GROWTH},
		)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)
		self.assertEqual(resp.json()["results"][0]["label"], "GDP")

	def test_indicator_ordering_by_period(self):
		resp = self.client.get("/api/v1/intelligence/indicators/", {"ordering": "period"})
		self.assertEqual(resp.status_code, 200)
		results = resp.json()["results"]
		self.assertLess(results[0]["period"], results[-1]["period"])

	def test_risk_list_returns_snapshot(self):
		resp = self.client.get("/api/v1/intelligence/risk/")
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)
		self.assertEqual(resp.json()["results"][0]["country"]["code"], "UG")

	def test_model_str_contains_country_and_period(self):
		indicator = EconomicIndicator.objects.filter(country=self.ug).first()
		self.assertIn("UG", str(indicator))
