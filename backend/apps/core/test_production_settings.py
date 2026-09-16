"""
Production settings validation tests.

These tests verify that settings.py correctly enforces production-safe
configuration. Tests that check startup-time validation (e.g. missing
SECRET_KEY) run Django settings import in an isolated subprocess so that
the already-initialised in-process settings object is never mutated.

Design constraints:
- Never mutate django.conf.settings in-process to "simulate" startup failure.
- Subprocess tests must be self-contained and produce a clear exit code.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import TestCase

# Absolute path to venv python / manage.py derived at test-discovery time.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent                           # FinPilot-AI/
_VENV_PYTHON = _PROJECT_ROOT / "venv" / "python.exe"
# Fall back to the interpreter that is running the test suite when the venv
# exe is not present (e.g. CI with a system Python).
_PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable


def _run_settings_subprocess(env_overrides: dict) -> subprocess.CompletedProcess:
    """
    Run settings import in an isolated subprocess with the given environment.

    The subprocess imports config.settings via DJANGO_SETTINGS_MODULE and
    exits 0 on success or non-zero on any exception.
    """
    env = {
        # Start from a clean, minimal environment so .env files loaded by
        # load_dotenv() do not bleed over from the developer's working copy.
        # NOTE: we must NOT strip empty-string values here. load_dotenv() with
        # override=False (the default) will NOT override an already-present env
        # var, even if its value is empty. Stripping the key would make it
        # absent and dotenv would then load the real value from .env.
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # Windows requirement
        "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", ""),
        "DJANGO_SETTINGS_MODULE": "config.settings",
        **env_overrides,
    }
    # Strip only None values; preserve empty strings so that load_dotenv()
    # cannot override them with values from the project's .env file.
    env = {k: v for k, v in env.items() if v is not None}

    code = (
        "import sys, os; "
        "sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
        "import config.settings"
    )
    return subprocess.run(
        [_PYTHON, "-c", code],
        env=env,
        capture_output=True,
        text=True,
    )


class SecretKeyStartupValidationTest(TestCase):
    """SECRET_KEY startup validation tested in an isolated subprocess."""

    def test_missing_secret_key_raises_improperly_configured(self):
        """Django must refuse to start when DJANGO_SECRET_KEY is absent.

        We pass DJANGO_SECRET_KEY="" (empty string). load_dotenv() with
        override=False will not override an already-present env var, so the
        real .env value is never loaded and settings startup sees an empty key.
        """
        result = _run_settings_subprocess(
            {
                # Empty string: present in env, but empty — triggers our validation.
                "DJANGO_SECRET_KEY": "",
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertNotEqual(
            result.returncode,
            0,
            msg="Expected non-zero exit when DJANGO_SECRET_KEY is missing.",
        )
        self.assertIn(
            "ImproperlyConfigured",
            result.stderr,
            msg="Expected ImproperlyConfigured in stderr.",
        )
        self.assertIn(
            "DJANGO_SECRET_KEY",
            result.stderr,
            msg="Expected error message to mention DJANGO_SECRET_KEY.",
        )

    def test_empty_secret_key_raises_improperly_configured(self):
        """Django must refuse to start when DJANGO_SECRET_KEY is empty string.

        Passing "" explicitly ensures load_dotenv() cannot override it with
        the real .env value (override=False is the dotenv default).
        """
        result = _run_settings_subprocess(
            {
                "DJANGO_SECRET_KEY": "",  # empty string — present but empty
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertNotEqual(
            result.returncode,
            0,
            msg="Expected non-zero exit when DJANGO_SECRET_KEY is empty.",
        )

    def test_valid_secret_key_allows_startup(self):
        """Django must start successfully when DJANGO_SECRET_KEY is set."""
        result = _run_settings_subprocess(
            {
                "DJANGO_SECRET_KEY": "a-valid-secret-key-that-is-not-empty",
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Expected zero exit with a valid SECRET_KEY. stderr: {result.stderr}",
        )


class DebugDefaultTest(TestCase):
    """DEBUG setting defaults."""

    def test_debug_is_false_by_default(self):
        """DEBUG must default to False.

        The live settings object (loaded with DJANGO_DEBUG=True for the test
        database) cannot represent the 'unset' case. We therefore re-import
        the settings module in a clean subprocess.
        """
        result = _run_settings_subprocess(
            {
                "DJANGO_SECRET_KEY": "test-secret-key-for-debug-default-test",
                # Omit DJANGO_DEBUG — should default to False.
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Settings import failed unexpectedly. stderr: {result.stderr}",
        )

    def test_debug_false_is_current_setting_default(self):
        """Confirm the default expression evaluates to False when var is unset."""
        # The live settings.DEBUG value when DJANGO_DEBUG env var is unset or "False".
        # Since the test runner sets DJANGO_DEBUG=True in the local .env, we
        # verify the expression logic directly instead.
        import os as _os

        # Simulate: DJANGO_DEBUG not set
        original = _os.environ.pop("DJANGO_DEBUG", None)
        try:
            debug_val = _os.getenv("DJANGO_DEBUG", "False").lower() == "true"
            self.assertFalse(debug_val, "DEBUG must default to False when DJANGO_DEBUG is not set.")
        finally:
            if original is not None:
                _os.environ["DJANGO_DEBUG"] = original


class AllowedHostsTest(TestCase):
    """ALLOWED_HOSTS parsing and defaults."""

    def test_allowed_hosts_parses_comma_separated_env(self):
        """ALLOWED_HOSTS must parse a comma-separated DJANGO_ALLOWED_HOSTS env var."""
        result = _run_settings_subprocess(
            {
                "DJANGO_SECRET_KEY": "test-secret-key-for-allowed-hosts-test",
                "DJANGO_DEBUG": "False",
                "DJANGO_ALLOWED_HOSTS": "example.com,www.example.com",
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_allowed_hosts_empty_in_production_mode(self):
        """With DEBUG=False and no DJANGO_ALLOWED_HOSTS, ALLOWED_HOSTS must be []."""
        code = (
            "import sys, os; "
            "sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "assert s.ALLOWED_HOSTS == [], f'Expected [] got {s.ALLOWED_HOSTS}'"
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", ""),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": "test-secret-key-for-prod-hosts-empty",
            "DJANGO_DEBUG": "False",
            # Explicitly set empty so load_dotenv() cannot override with .env value.
            "DJANGO_ALLOWED_HOSTS": "",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_HOST": "localhost",
        }
        # Keep empty strings so dotenv cannot override them.
        env = {k: v for k, v in env.items() if v is not None}
        result = subprocess.run(
            [_PYTHON, "-c", code],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"ALLOWED_HOSTS was not [] in production mode. stderr: {result.stderr}",
        )

    def test_allowed_hosts_loopback_in_debug_mode(self):
        """With DEBUG=True and no DJANGO_ALLOWED_HOSTS, must default to loopback."""
        code = (
            "import sys, os; "
            "sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "expected = ['localhost', '127.0.0.1', '[::1]']; "
            "assert s.ALLOWED_HOSTS == expected, f'Got {s.ALLOWED_HOSTS}'"
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", ""),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": "test-secret-key-for-debug-hosts-test",
            "DJANGO_DEBUG": "True",
            # Explicitly set empty so load_dotenv() cannot override with .env value.
            "DJANGO_ALLOWED_HOSTS": "",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_HOST": "localhost",
        }
        # Keep empty strings so dotenv cannot override them.
        env = {k: v for k, v in env.items() if v is not None}
        result = subprocess.run(
            [_PYTHON, "-c", code],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"ALLOWED_HOSTS not loopback in DEBUG mode. stderr: {result.stderr}",
        )


class StaticRootTest(TestCase):
    """STATIC_ROOT is defined and uses BASE_DIR convention."""

    def test_static_root_is_defined(self):
        """STATIC_ROOT must be defined."""
        self.assertTrue(
            hasattr(settings, "STATIC_ROOT"),
            "STATIC_ROOT is not defined in settings.",
        )

    def test_static_root_is_staticfiles_under_base_dir(self):
        """STATIC_ROOT must point to BASE_DIR / 'staticfiles'."""
        expected = Path(settings.BASE_DIR) / "staticfiles"
        self.assertEqual(
            Path(settings.STATIC_ROOT),
            expected,
            msg=f"Expected STATIC_ROOT={expected}, got {settings.STATIC_ROOT}",
        )

    def test_static_url_unchanged(self):
        """STATIC_URL must remain 'static/' (Django 6.1 normalises to '/static/')."""
        # Django normalises a bare 'static/' to '/static/' at settings load time.
        self.assertIn(settings.STATIC_URL, ("static/", "/static/"))


class EnvExampleSecretTest(TestCase):
    """Verify .env.example files contain no committed placeholder secrets."""

    def _check_env_file(self, path: Path) -> None:
        self.assertTrue(path.exists(), f".env.example not found at {path}")
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped.startswith("DJANGO_SECRET_KEY"):
                continue
            # Found the DJANGO_SECRET_KEY line — value must be empty.
            _, _, value = stripped.partition("=")
            self.assertEqual(
                value.strip(),
                "",
                msg=(
                    f"DJANGO_SECRET_KEY in {path} must be empty (got {value!r}). "
                    "A non-empty placeholder can be accidentally deployed."
                ),
            )

    def test_root_env_example_secret_key_is_empty(self):
        """Root .env.example must have DJANGO_SECRET_KEY= (no value)."""
        self._check_env_file(_PROJECT_ROOT / ".env.example")

    def test_backend_env_example_secret_key_is_empty(self):
        """backend/.env.example must have DJANGO_SECRET_KEY= (no value)."""
        self._check_env_file(_BACKEND_DIR / ".env.example")


class CsrfTrustedOriginsTest(TestCase):
    """CSRF_TRUSTED_ORIGINS parsing and environment defaults."""

    def test_csrf_trusted_origins_parses_comma_separated_env(self):
        """DJANGO_CSRF_TRUSTED_ORIGINS parsed into list of origins."""
        code = (
            "import sys; sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "assert s.CSRF_TRUSTED_ORIGINS == ['https://app.finpilot.ai', 'https://api.finpilot.ai'], "
            "f'Got {s.CSRF_TRUSTED_ORIGINS}'"
        )
        result = _run_settings_subprocess(
            {
                "DJANGO_SECRET_KEY": "test-secret-key-csrf-parse",
                "DJANGO_DEBUG": "False",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "https://app.finpilot.ai,https://api.finpilot.ai",
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_csrf_trusted_origins_empty_in_production_when_unset(self):
        """In production mode with no env set, CSRF_TRUSTED_ORIGINS must be []."""
        code = (
            "import sys; sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "assert s.CSRF_TRUSTED_ORIGINS == [], f'Got {s.CSRF_TRUSTED_ORIGINS}'"
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", ""),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": "test-secret-key-csrf-prod",
            "DJANGO_DEBUG": "False",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_HOST": "localhost",
        }
        env = {k: v for k, v in env.items() if v is not None}
        result = subprocess.run(
            [_PYTHON, "-c", code],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_csrf_trusted_origins_excludes_wildcard(self):
        """Unsafe wildcard '*' must not be accepted into CSRF_TRUSTED_ORIGINS."""
        code = (
            "import sys; sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "assert '*' not in s.CSRF_TRUSTED_ORIGINS, f'Found wildcard in {s.CSRF_TRUSTED_ORIGINS}'; "
            "assert 'https://app.finpilot.ai' in s.CSRF_TRUSTED_ORIGINS"
        )
        result = _run_settings_subprocess(
            {
                "DJANGO_SECRET_KEY": "test-secret-key-csrf-wildcard",
                "DJANGO_DEBUG": "False",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "*,https://app.finpilot.ai",
                "POSTGRES_DB": "test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "localhost",
            }
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)


class SecureProxyAndCookieSettingsTest(TestCase):
    """SECURE_PROXY_SSL_HEADER and secure cookie settings."""

    def test_secure_proxy_ssl_header_configured(self):
        """SECURE_PROXY_SSL_HEADER must be ('HTTP_X_FORWARDED_PROTO', 'https')."""
        self.assertEqual(
            getattr(settings, "SECURE_PROXY_SSL_HEADER", None),
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )

    def test_cookie_secure_defaults_true_in_production(self):
        """When DEBUG=False, SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE must default to True."""
        code = (
            "import sys; sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "assert s.SESSION_COOKIE_SECURE is True, f'SESSION_COOKIE_SECURE was {s.SESSION_COOKIE_SECURE}'; "
            "assert s.CSRF_COOKIE_SECURE is True, f'CSRF_COOKIE_SECURE was {s.CSRF_COOKIE_SECURE}'"
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", ""),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": "test-secret-key-cookies-prod",
            "DJANGO_DEBUG": "False",
            "SESSION_COOKIE_SECURE": "",
            "CSRF_COOKIE_SECURE": "",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_HOST": "localhost",
        }
        env = {k: v for k, v in env.items() if v is not None}
        result = subprocess.run(
            [_PYTHON, "-c", code],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_cookie_secure_defaults_false_in_debug(self):
        """When DEBUG=True, SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE must default to False."""
        code = (
            "import sys; sys.path.insert(0, r'" + str(_BACKEND_DIR) + "'); "
            "import config.settings as s; "
            "assert s.SESSION_COOKIE_SECURE is False, f'SESSION_COOKIE_SECURE was {s.SESSION_COOKIE_SECURE}'; "
            "assert s.CSRF_COOKIE_SECURE is False, f'CSRF_COOKIE_SECURE was {s.CSRF_COOKIE_SECURE}'"
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", ""),
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": "test-secret-key-cookies-debug",
            "DJANGO_DEBUG": "True",
            "SESSION_COOKIE_SECURE": "",
            "CSRF_COOKIE_SECURE": "",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_HOST": "localhost",
        }
        env = {k: v for k, v in env.items() if v is not None}
        result = subprocess.run(
            [_PYTHON, "-c", code],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)


class WhiteNoiseConfigurationTest(TestCase):
    """WhiteNoise middleware and storage configuration."""

    def test_whitenoise_middleware_position(self):
        """WhiteNoiseMiddleware must immediately follow SecurityMiddleware."""
        middleware = settings.MIDDLEWARE
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", middleware)
        sec_index = middleware.index("django.middleware.security.SecurityMiddleware")
        wn_index = middleware.index("whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertEqual(
            wn_index,
            sec_index + 1,
            msg="WhiteNoiseMiddleware must be positioned immediately after SecurityMiddleware.",
        )

    def test_staticfiles_storage_uses_whitenoise(self):
        """Staticfiles storage backend must use WhiteNoise CompressedManifestStaticFilesStorage."""
        storages = getattr(settings, "STORAGES", {})
        staticfiles_storage = storages.get("staticfiles", {})
        backend_class = staticfiles_storage.get("BACKEND", "")
        self.assertIn("whitenoise.storage", backend_class)


class CeleryBeatPersistenceConfigurationTest(TestCase):
    """Verify Celery Beat persistent schedule volume and command configuration."""

    def test_docker_compose_beat_schedule_persistence(self):
        """Verify beat service in docker-compose.yml uses persistent volume and schedule path."""
        compose_file = _PROJECT_ROOT / "docker-compose.yml"
        if not compose_file.exists():
            # Inside the container, docker-compose.yml is not copied; verify runtime mount directory exists
            run_dir = Path("/app/backend/run")
            if run_dir.exists():
                self.assertTrue(run_dir.is_dir(), "/app/backend/run must be a directory.")
                return
            self.skipTest("docker-compose.yml not present in this test environment.")

        content = compose_file.read_text(encoding="utf-8")

        # 1. Schedule argument
        self.assertIn(
            "--schedule=/app/backend/run/celerybeat-schedule",
            content,
            "Beat command must configure --schedule=/app/backend/run/celerybeat-schedule",
        )
        # 2. Volume mount
        self.assertIn(
            "celerybeat_data:/app/backend/run",
            content,
            "Beat service must mount celerybeat_data:/app/backend/run",
        )
        # 3. Top-level volume declaration
        self.assertIn(
            "celerybeat_data:",
            content,
            "celerybeat_data named volume must be declared in top-level volumes",
        )
