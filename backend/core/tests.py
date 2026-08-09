import importlib
import os
import sys
from unittest import mock

from django.test import TestCase, override_settings


class ConfigSettingsBranchTests(TestCase):
	def _load_settings_module(self, env: dict[str, str]):
		with mock.patch.dict(os.environ, env, clear=True):
			sys.modules.pop("config.settings", None)
			mod = importlib.import_module("config.settings")
			return importlib.reload(mod)

	def test_debug_default_true_without_railway(self):
		mod = self._load_settings_module({
			"SECRET_KEY": "x",
			"DEBUG": "true",
		})
		self.assertTrue(mod.DEBUG)

	def test_debug_default_false_with_railway(self):
		mod = self._load_settings_module({
			"SECRET_KEY": "x",
			"DEBUG": "",
			"RAILWAY_ENVIRONMENT": "production",
			"RAILWAY_PUBLIC_DOMAIN": "app.railway.app",
		})
		self.assertFalse(mod.DEBUG)
		self.assertIn("app.railway.app", mod.ALLOWED_HOSTS)
		self.assertIn("https://app.railway.app", mod.CSRF_TRUSTED_ORIGINS)

	def test_secure_ssl_redirect_env_branches(self):
		mod_true = self._load_settings_module({
			"SECRET_KEY": "x",
			"DEBUG": "false",
			"SECURE_SSL_REDIRECT": "true",
		})
		self.assertTrue(mod_true.SECURE_SSL_REDIRECT)

		mod_false = self._load_settings_module({
			"SECRET_KEY": "x",
			"DEBUG": "false",
			"SECURE_SSL_REDIRECT": "false",
		})
		self.assertFalse(mod_false.SECURE_SSL_REDIRECT)

		mod_railway = self._load_settings_module({
			"SECRET_KEY": "x",
			"DEBUG": "false",
			"RAILWAY_ENVIRONMENT": "production",
		})
		self.assertFalse(mod_railway.SECURE_SSL_REDIRECT)


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
