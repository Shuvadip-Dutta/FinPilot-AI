"""
Focused tests for auth throttle implementation (Phase 4 fix).

Verifies:
  - 'auth' scope is registered in DEFAULT_THROTTLE_RATES.
  - ThrottledTokenObtainPairView uses ScopedRateThrottle with scope 'auth'.
  - ThrottledTokenRefreshView uses ScopedRateThrottle with scope 'auth'.
  - Token endpoints remain publicly accessible and functional.
  - Token obtain endpoint does NOT consume the global AnonRateThrottle bucket
    (regression test with override_settings).

All test classes that require a database use plain TestCase; the test runner
automatically uses the SQLite in-memory database declared in
DATABASES["default"]["TEST"] in settings.py, so no external PostgreSQL
connection is needed when running these tests locally.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle


def _clear_throttle_cache():
    from django.core.cache import cache
    cache.clear()


# ---------------------------------------------------------------------------
# 1.  Settings-level structural tests — no DB required
# ---------------------------------------------------------------------------


class AuthThrottleScopeSettingsTest(TestCase):
    """Verify that the 'auth' scope is correctly declared in settings."""

    def test_auth_scope_present_in_throttle_rates(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertIn("auth", rates, "DEFAULT_THROTTLE_RATES must contain an 'auth' key.")

    def test_auth_scope_rate_is_non_empty_string(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        rate = rates.get("auth", "")
        self.assertTrue(
            isinstance(rate, str) and rate.strip(),
            f"'auth' throttle rate must be a non-empty string, got: {rate!r}",
        )

    def test_auth_scope_rate_format_is_valid(self):
        """Rate must match DRF's '<N>/<period>' format."""
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        rate = rates.get("auth", "")
        parts = rate.split("/")
        self.assertEqual(len(parts), 2, f"auth rate must be '<N>/<period>', got: {rate!r}")
        count, period = parts
        self.assertTrue(count.isdigit(), f"Rate count must be an integer, got: {count!r}")
        self.assertIn(
            period, ("second", "minute", "hour", "day"),
            f"Rate period must be one of second/minute/hour/day, got: {period!r}",
        )

    def test_existing_scopes_not_removed(self):
        """Ensure original throttle scopes are untouched."""
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        for scope in ("anon", "user", "ai_heavy"):
            self.assertIn(scope, rates, f"Scope '{scope}' must still be present.")


# ---------------------------------------------------------------------------
# 2.  View-level structural tests — no DB required
# ---------------------------------------------------------------------------


class AuthViewThrottleClassesTest(TestCase):
    """Verify that the throttled JWT view subclasses are wired correctly."""

    def test_token_obtain_view_uses_scoped_throttle(self):
        from apps.core.views import ThrottledTokenObtainPairView
        throttle_classes = getattr(ThrottledTokenObtainPairView, "throttle_classes", [])
        self.assertTrue(
            any(cls is ScopedRateThrottle for cls in throttle_classes),
            "ThrottledTokenObtainPairView must list ScopedRateThrottle in throttle_classes.",
        )

    def test_token_obtain_view_scope_is_auth(self):
        from apps.core.views import ThrottledTokenObtainPairView
        self.assertEqual(
            getattr(ThrottledTokenObtainPairView, "throttle_scope", None),
            "auth",
            "ThrottledTokenObtainPairView.throttle_scope must be 'auth'.",
        )

    def test_token_refresh_view_uses_scoped_throttle(self):
        from apps.core.views import ThrottledTokenRefreshView
        throttle_classes = getattr(ThrottledTokenRefreshView, "throttle_classes", [])
        self.assertTrue(
            any(cls is ScopedRateThrottle for cls in throttle_classes),
            "ThrottledTokenRefreshView must list ScopedRateThrottle in throttle_classes.",
        )

    def test_token_refresh_view_scope_is_auth(self):
        from apps.core.views import ThrottledTokenRefreshView
        self.assertEqual(
            getattr(ThrottledTokenRefreshView, "throttle_scope", None),
            "auth",
            "ThrottledTokenRefreshView.throttle_scope must be 'auth'.",
        )

    def test_url_resolves_to_throttled_obtain_view(self):
        from django.urls import resolve
        from apps.core.views import ThrottledTokenObtainPairView
        match = resolve("/api/v1/auth/token/")
        self.assertIs(
            match.func.view_class,
            ThrottledTokenObtainPairView,
            "URL /api/v1/auth/token/ must resolve to ThrottledTokenObtainPairView.",
        )

    def test_url_resolves_to_throttled_refresh_view(self):
        from django.urls import resolve
        from apps.core.views import ThrottledTokenRefreshView
        match = resolve("/api/v1/auth/token/refresh/")
        self.assertIs(
            match.func.view_class,
            ThrottledTokenRefreshView,
            "URL /api/v1/auth/token/refresh/ must resolve to ThrottledTokenRefreshView.",
        )


# ---------------------------------------------------------------------------
# 3.  Functional tests — DB required (SQLite via DATABASES["default"]["TEST"])
# ---------------------------------------------------------------------------


class AuthThrottleFunctionalTest(TestCase):
    """
    Functional tests: throttle configuration must not break the JWT flow.
    The test runner uses the SQLite in-memory database declared in
    DATABASES["default"]["TEST"] in settings.py.
    """

    def setUp(self):
        self.client = APIClient()
        _clear_throttle_cache()
        self.user = User.objects.create_user(
            username="throttleuser",
            email="throttleuser@example.com",
            password="ThrottlePass123!",
        )

    def test_token_obtain_returns_200_for_valid_credentials(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "throttleuser", "password": "ThrottlePass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_refresh_returns_200_for_valid_refresh_token(self):
        r = self.client.post(
            "/api/v1/auth/token/",
            {"username": "throttleuser", "password": "ThrottlePass123!"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r2 = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": r.data["refresh"]},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertIn("access", r2.data)

    def test_token_endpoint_publicly_accessible(self):
        """Token endpoint must not require a JWT; bad credentials yield 401
        from SimpleJWT (credential rejection), not 403 from a permission gate."""
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "nobody", "password": "bad"},
            format="json",
        )
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_token_refresh_endpoint_publicly_accessible(self):
        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": "invalid-token"},
            format="json",
        )
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# 4.  Regression: token endpoint must NOT consume the global AnonRateThrottle
#     bucket.
#
#     Mechanism: ThrottledTokenObtainPairView sets
#         throttle_classes = [ScopedRateThrottle]
#     which REPLACES the view's throttle list entirely. AnonRateThrottle is
#     therefore never instantiated for this view.
#
#     Test strategy:
#       - override 'anon' rate to '1/day' (one anonymous hit exhausts the bucket)
#       - keep 'auth' scope at '30/minute'
#       - clear throttle cache before the test
#       - make TWO consecutive valid token-obtain requests
#       - assert BOTH return HTTP 200
#
#     If the endpoint were still consuming the anon bucket the second request
#     would return HTTP 429 (Too Many Requests), failing the assertion.
# ---------------------------------------------------------------------------

_ANON_LOCKOUT_THROTTLE_RATES = {
    "anon": "1/day",       # exhausted after one anonymous request
    "user": "1000/day",
    "ai_heavy": "60/minute",
    "auth": "30/minute",   # must be the only scope applied to the auth endpoint
}


@override_settings(
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": _ANON_LOCKOUT_THROTTLE_RATES,
    }
)
class AuthAnonBucketRegressionTest(TestCase):
    """
    Regression: repeated token-obtain requests succeed even when the global
    AnonRateThrottle is set to '1/day', proving the auth endpoint is fully
    isolated from the shared anonymous quota.
    """

    def setUp(self):
        self.client = APIClient()
        _clear_throttle_cache()
        self.user = User.objects.create_user(
            username="regressionuser",
            email="regressionuser@example.com",
            password="RegressionPass123!",
        )

    def test_two_token_obtain_requests_both_succeed_despite_anon_lockout(self):
        """
        With anon='1/day', a bare AnonRateThrottle would 429 the second call.
        The dedicated auth ScopedRateThrottle (30/minute) must allow both.
        """
        credentials = {
            "username": "regressionuser",
            "password": "RegressionPass123!",
        }

        # First request — must succeed.
        r1 = self.client.post("/api/v1/auth/token/", credentials, format="json")
        self.assertEqual(
            r1.status_code,
            status.HTTP_200_OK,
            f"First token-obtain request failed unexpectedly with status {r1.status_code}.",
        )

        # Second request — must ALSO succeed.
        # If the view were consuming the anon bucket this would return HTTP 429.
        r2 = self.client.post("/api/v1/auth/token/", credentials, format="json")
        self.assertEqual(
            r2.status_code,
            status.HTTP_200_OK,
            (
                f"Second token-obtain request returned {r2.status_code}. "
                "The auth endpoint appears to be consuming the global anon "
                "throttle bucket (expected HTTP 200 from the 'auth' scope). "
                "Verify ThrottledTokenObtainPairView.throttle_classes replaces "
                "the default throttle list entirely."
            ),
        )
        self.assertIn("access", r2.data)
        self.assertIn("refresh", r2.data)

    def test_anon_rate_override_is_active_in_this_class(self):
        """Sanity-check: the override_settings decorator is in effect."""
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertEqual(
            rates.get("anon"),
            "1/day",
            "Expected 'anon' throttle rate to be overridden to '1/day' in this test class.",
        )
