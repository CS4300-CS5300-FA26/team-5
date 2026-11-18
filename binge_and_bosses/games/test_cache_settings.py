"""Cache configuration tests use fake environment values and never connect to Redis."""
import os
import runpy
from pathlib import Path
from unittest.mock import patch

from decouple import Config, RepositoryEmpty
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class CacheSettingsTests(SimpleTestCase):
    def load_cache(self, **values):
        environment = {
            "SECRET_KEY": "test-only", "IGDB_CLIENT_ID": "test-id",
            "IGDB_CLIENT_SECRET": "test-secret", "DEBUG": "False",
            **values,
        }
        settings_path = Path(__file__).resolve().parents[1] / "binge_and_bosses" / "settings.py"
        with patch.dict(os.environ, environment, clear=True), patch(
            "decouple.config", Config(RepositoryEmpty())
        ):
            return runpy.run_path(str(settings_path))["CACHES"]["default"]

    def test_production_requires_redis_url(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "REDIS_URL"):
            self.load_cache()

    def test_production_rejects_blank_url(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "REDIS_URL"):
            self.load_cache(REDIS_URL="   ")

    def test_local_debug_uses_local_redis(self):
        cache = self.load_cache(DEBUG="True")
        self.assertEqual(cache["LOCATION"], "redis://127.0.0.1:6379/0")
        self.assertNotIn("ssl_cert_reqs", cache["OPTIONS"])

    def test_tls_verifies_certificates_by_default(self):
        cache = self.load_cache(REDIS_URL="rediss://cache.example:6379/0")
        self.assertEqual(cache["OPTIONS"]["ssl_cert_reqs"], "required")

    def test_heroku_self_signed_certificates_require_explicit_opt_out(self):
        cache = self.load_cache(
            REDIS_URL="rediss://cache.example:6379/0", REDIS_SSL_VERIFY="False"
        )
        self.assertEqual(cache["LOCATION"], "rediss://cache.example:6379/0")
        self.assertIsNone(cache["OPTIONS"]["ssl_cert_reqs"])

    def test_plain_redis_does_not_receive_tls_options(self):
        cache = self.load_cache(
            REDIS_URL="redis://127.0.0.1:6379/0", REDIS_SSL_VERIFY="False"
        )
        self.assertNotIn("ssl_cert_reqs", cache["OPTIONS"])
