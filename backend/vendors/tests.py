from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership
from core.models import Country

from .models import Vendor, VendorContractRecord, VendorDocument, VendorPaymentRecord


class VendorApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.country_ug = Country.objects.create(code="UG", name="Uganda", is_eac_member=True)
		self.country_ke = Country.objects.create(code="KE", name="Kenya", is_eac_member=True)
		self.user = User.objects.create_user(username="vendor-user", password="StrongPass123")
		self.org1 = Organization.objects.create(name="Org One", slug="org-one", origin_country="DE")
		self.org2 = Organization.objects.create(name="Org Two", slug="org-two", origin_country="FR")
		OrganizationMembership.objects.create(user=self.user, organization=self.org1)
		OrganizationMembership.objects.create(user=self.user, organization=self.org2)

		self.v1 = Vendor.objects.create(
			organization=self.org1,
			name="Vendor One",
			registration_number="R1",
			country=self.country_ug,
			risk_score="40.0",
		)
		Vendor.objects.create(
			organization=self.org2,
			name="Vendor Two",
			registration_number="R2",
			country=self.country_ke,
			risk_score="70.0",
		)

	def _auth(self):
		token = self.client.post(
			"/api/v1/auth/login/",
			{"username": "vendor-user", "password": "StrongPass123"},
			format="json",
		).json()["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

	def test_list_requires_authentication(self):
		resp = self.client.get("/api/v1/vendors/")
		self.assertEqual(resp.status_code, 401)

	def test_list_is_scoped_by_active_org_header(self):
		self._auth()
		resp = self.client.get("/api/v1/vendors/", HTTP_X_ORGANIZATION_ID=str(self.org1.id))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["count"], 1)
		self.assertEqual(resp.json()["results"][0]["name"], "Vendor One")

	def test_create_without_header_uses_membership_fallback(self):
		self._auth()
		resp = self.client.post(
			"/api/v1/vendors/",
			{
				"name": "New Vendor",
				"registration_number": "RX",
				"country_code": "UG",
				"risk_score": "50.0",
			},
			format="json",
		)
		self.assertEqual(resp.status_code, 201)

	def test_create_vendor_with_country_code(self):
		self._auth()
		resp = self.client.post(
			"/api/v1/vendors/",
			{
				"name": "New Vendor",
				"registration_number": "RX",
				"country_code": "ug",
				"business_profile": "Importer",
				"risk_score": "45.5",
			},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org1.id),
		)
		self.assertEqual(resp.status_code, 201)
		self.assertEqual(Vendor.objects.filter(organization=self.org1).count(), 2)
		vendor = Vendor.objects.get(name="New Vendor")
		self.assertEqual(vendor.country.code, "UG")

	def test_partial_update_can_change_country_via_country_code(self):
		self._auth()
		resp = self.client.patch(
			f"/api/v1/vendors/{self.v1.id}/",
			{"country_code": "KE", "risk_score": "88.0"},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org1.id),
		)
		self.assertEqual(resp.status_code, 200)
		self.v1.refresh_from_db()
		self.assertEqual(self.v1.country.code, "KE")
		self.assertEqual(str(self.v1.risk_score), "88.00")

	def test_add_contract_and_payment_actions(self):
		self._auth()
		contract = self.client.post(
			f"/api/v1/vendors/{self.v1.id}/add_contract/",
			{
				"contract_ref": "C-001",
				"value_usd": "25000.00",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
			},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org1.id),
		)
		payment = self.client.post(
			f"/api/v1/vendors/{self.v1.id}/add_payment/",
			{
				"amount_usd": "5000.00",
				"payment_date": date(2026, 2, 10).isoformat(),
				"status": "completed",
			},
			format="json",
			HTTP_X_ORGANIZATION_ID=str(self.org1.id),
		)
		self.assertEqual(contract.status_code, 201)
		self.assertEqual(payment.status_code, 201)
		self.assertEqual(VendorContractRecord.objects.filter(vendor=self.v1).count(), 1)
		self.assertEqual(VendorPaymentRecord.objects.filter(vendor=self.v1).count(), 1)

	def test_upload_document_action_creates_document(self):
		self._auth()
		file_obj = SimpleUploadedFile("kyc.pdf", b"pdf-bytes", content_type="application/pdf")
		resp = self.client.post(
			f"/api/v1/vendors/{self.v1.id}/upload_document/",
			{"document_type": "kyc", "file": file_obj},
			HTTP_X_ORGANIZATION_ID=str(self.org1.id),
			format="multipart",
		)
		self.assertEqual(resp.status_code, 201)
		self.assertEqual(VendorDocument.objects.filter(vendor=self.v1).count(), 1)
