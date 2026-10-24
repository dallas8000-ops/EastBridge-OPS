import importlib
import os
import sys
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

_STRONG_KEY = "k" * 64


class ConfigSettingsBranchTests(TestCase):
	def _load_settings_module(self, env: dict[str, str]):
		with mock.patch.dict(os.environ, env, clear=True):
			sys.modules.pop("config.settings", None)
			mod = importlib.import_module("config.settings")
			return importlib.reload(mod)

	def test_debug_default_true_without_railway(self):
		mod = self._load_settings_module({
			"SECRET_KEY": _STRONG_KEY,
			"DEBUG": "true",
		})
		self.assertTrue(mod.DEBUG)

	def test_debug_default_false_with_railway(self):
		mod = self._load_settings_module({
			"SECRET_KEY": _STRONG_KEY,
			"DEBUG": "",
			"RAILWAY_ENVIRONMENT": "production",
			"RAILWAY_PUBLIC_DOMAIN": "app.railway.app",
		})
		self.assertFalse(mod.DEBUG)
		self.assertIn("app.railway.app", mod.ALLOWED_HOSTS)
		self.assertIn("https://app.railway.app", mod.CSRF_TRUSTED_ORIGINS)

	def test_secure_ssl_redirect_env_branches(self):
		mod_true = self._load_settings_module({
			"SECRET_KEY": _STRONG_KEY,
			"DEBUG": "false",
			"SECURE_SSL_REDIRECT": "true",
		})
		self.assertTrue(mod_true.SECURE_SSL_REDIRECT)

		mod_false = self._load_settings_module({
			"SECRET_KEY": _STRONG_KEY,
			"DEBUG": "false",
			"SECURE_SSL_REDIRECT": "false",
		})
		self.assertFalse(mod_false.SECURE_SSL_REDIRECT)

		mod_railway = self._load_settings_module({
			"SECRET_KEY": _STRONG_KEY,
			"DEBUG": "false",
			"RAILWAY_ENVIRONMENT": "production",
		})
		self.assertFalse(mod_railway.SECURE_SSL_REDIRECT)

	def test_secret_key_guard_rejects_public_default_on_railway(self):
		with self.assertRaises(ImproperlyConfigured):
			self._load_settings_module({
				"SECRET_KEY": "django-insecure-dev-only-change-me",
				"RAILWAY_ENVIRONMENT": "production",
			})

	def test_secret_key_guard_rejects_short_key_when_not_debug(self):
		with self.assertRaises(ImproperlyConfigured):
			self._load_settings_module({
				"SECRET_KEY": "too-short",
				"DEBUG": "false",
			})

	def test_secret_key_guard_rejects_short_key_on_railway_even_if_debug(self):
		with self.assertRaises(ImproperlyConfigured):
			self._load_settings_module({
				"SECRET_KEY": "x" * 49,
				"DEBUG": "true",
				"RAILWAY_SERVICE_ID": "svc",
			})

	def test_secret_key_guard_allows_dev_default_in_local_debug(self):
		mod = self._load_settings_module({
			"SECRET_KEY": "django-insecure-dev-only-change-me",
			"DEBUG": "true",
		})
		self.assertTrue(mod.DEBUG)

	def test_secret_key_guard_accepts_strong_key_on_railway(self):
		mod = self._load_settings_module({
			"SECRET_KEY": _STRONG_KEY,
			"RAILWAY_ENVIRONMENT": "production",
		})
		self.assertEqual(mod.SECRET_KEY, _STRONG_KEY)


class ConfigUrlsBranchTests(TestCase):
	def test_urlpatterns_without_debug_static(self):
		with override_settings(DEBUG=False):
			import config.urls as config_urls
			mod = importlib.reload(config_urls)
			self.assertFalse(any("media" in str(getattr(p, "pattern", "")) for p in mod.urlpatterns))

	def test_urlpatterns_with_debug_static(self):
		with override_settings(DEBUG=True):
			import config.urls as config_urls
			mod = importlib.reload(config_urls)
			self.assertTrue(any("media" in str(getattr(p, "pattern", "")) for p in mod.urlpatterns))
