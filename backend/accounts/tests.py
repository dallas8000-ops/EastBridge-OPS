from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory

from .models import Organization, OrganizationMembership
from .permissions import IsOrganizationMember, get_user_organization


class AccountsAuthFlowTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(username="alice", password="StrongPass123")
		self.org = Organization.objects.create(name="Alpha GmbH", slug="alpha", origin_country="DE")
		self.membership = OrganizationMembership.objects.create(
			user=self.user,
			organization=self.org,
			role=OrganizationMembership.Role.ADMIN,
		)

	def _login(self, username="alice", password="StrongPass123"):
		return self.client.post(
			"/api/v1/auth/login/",
			{"username": username, "password": password},
			format="json",
		)

	def test_register_creates_user_org_and_admin_membership(self):
		resp = self.client.post(
			"/api/v1/auth/register/",
			{
				"username": "newuser",
				"email": "newuser@example.com",
				"password": "VeryStrong123",
				"organization_name": "New Org",
				"origin_country": "ug",
			},
			format="json",
		)

		self.assertEqual(resp.status_code, 201)
		user = User.objects.get(username="newuser")
		membership = user.memberships.select_related("organization").first()
		self.assertIsNotNone(membership)
		self.assertEqual(membership.role, OrganizationMembership.Role.ADMIN)
		self.assertEqual(membership.organization.origin_country, "UG")

	def test_register_rejects_duplicate_username(self):
		resp = self.client.post(
			"/api/v1/auth/register/",
			{
				"username": "alice",
				"email": "alice2@example.com",
				"password": "VeryStrong123",
				"organization_name": "Other Org",
				"origin_country": "KE",
			},
			format="json",
		)
		self.assertEqual(resp.status_code, 400)
		self.assertIn("username", resp.json())

	def test_login_returns_access_and_refresh_tokens(self):
		resp = self._login()
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertIn("access", data)
		self.assertIn("refresh", data)

	def test_me_requires_authentication(self):
		resp = self.client.get("/api/v1/auth/me/")
		self.assertEqual(resp.status_code, 401)

	def test_me_returns_user_and_memberships(self):
		token = self._login().json()["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

		resp = self.client.get("/api/v1/auth/me/")
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertEqual(body["username"], "alice")
		self.assertEqual(len(body["memberships"]), 1)
		self.assertEqual(body["memberships"][0]["organization"]["slug"], "alpha")

	def test_refresh_issues_new_access_token(self):
		login = self._login().json()
		resp = self.client.post("/api/v1/auth/refresh/", {"refresh": login["refresh"]}, format="json")
		self.assertEqual(resp.status_code, 200)
		self.assertIn("access", resp.json())


class OrganizationPermissionTests(TestCase):
	def setUp(self):
		self.factory = APIRequestFactory()
		self.perm = IsOrganizationMember()
		self.user = User.objects.create_user(username="bob", password="StrongPass123")
		self.org_a = Organization.objects.create(name="Org A", slug="org-a", origin_country="KE")
		self.org_b = Organization.objects.create(name="Org B", slug="org-b", origin_country="UG")
		OrganizationMembership.objects.create(user=self.user, organization=self.org_a)

	def test_is_organization_member_denies_anonymous(self):
		request = self.factory.get("/api/v1/vendors/")
		request.user = AnonymousUser()
		allowed = self.perm.has_permission(request, type("V", (), {"kwargs": {}})())
		self.assertFalse(allowed)

	def test_is_organization_member_header_must_match_membership(self):
		request = self.factory.get("/api/v1/vendors/", HTTP_X_ORGANIZATION_ID=str(self.org_b.id))
		request.user = self.user
		denied = self.perm.has_permission(request, type("V", (), {"kwargs": {}})())
		self.assertFalse(denied)

		request_ok = self.factory.get("/api/v1/vendors/", HTTP_X_ORGANIZATION_ID=str(self.org_a.id))
		request_ok.user = self.user
		allowed = self.perm.has_permission(request_ok, type("V", (), {"kwargs": {}})())
		self.assertTrue(allowed)

	def test_get_user_organization_prefers_header_then_fallback(self):
		request = self.factory.get("/api/v1/vendors/")
		request.user = self.user
		fallback_org = get_user_organization(request)
		self.assertEqual(fallback_org.id, self.org_a.id)

		request_with_header = self.factory.get(
			"/api/v1/vendors/",
			HTTP_X_ORGANIZATION_ID=str(self.org_b.id),
		)
		request_with_header.user = self.user
		self.assertEqual(get_user_organization(request_with_header).id, self.org_a.id)
