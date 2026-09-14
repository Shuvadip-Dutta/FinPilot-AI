from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APIClient


class AuthFoundationTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_jwt_authentication_configured(self):
        auth_classes = settings.REST_FRAMEWORK.get(
            "DEFAULT_AUTHENTICATION_CLASSES", ()
        )
        self.assertIn(
            "rest_framework_simplejwt.authentication.JWTAuthentication",
            auth_classes,
        )

    def test_is_authenticated_default_permission_configured(self):
        permission_classes = settings.REST_FRAMEWORK.get(
            "DEFAULT_PERMISSION_CLASSES", ()
        )
        self.assertIn(
            "rest_framework.permissions.IsAuthenticated",
            permission_classes,
        )

    def test_health_endpoint_remains_publicly_accessible(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok", "service": "finpilot-api"})

    def test_protected_ai_chat_endpoint_requires_authentication(self):
        response = self.client.post("/api/v1/ai/chat/", {"message": "Hello"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_research_endpoint_requires_authentication(self):
        response = self.client.get("/api/v1/research/company/?ticker=RELIANCE&market=IN")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthEndpointsTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.valid_payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

    def test_successful_registration(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newuser")
        self.assertEqual(response.data["email"], "newuser@example.com")
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirm", response.data)

        from django.contrib.auth.models import User
        user = User.objects.get(username="newuser")
        self.assertTrue(user.check_password("SecurePassword123!"))

    def test_password_confirmation_mismatch_rejected(self):
        payload = dict(self.valid_payload)
        payload["password_confirm"] = "DifferentPassword123!"
        response = self.client.post(
            "/api/v1/auth/register/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_duplicate_username_rejected(self):
        self.client.post("/api/v1/auth/register/", self.valid_payload, format="json")
        payload = dict(self.valid_payload)
        payload["email"] = "otheremail@example.com"
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_duplicate_email_rejected(self):
        self.client.post("/api/v1/auth/register/", self.valid_payload, format="json")
        payload = dict(self.valid_payload)
        payload["username"] = "otheruser"
        payload["email"] = "NEWUSER@example.com"
        response = self.client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_successful_token_acquisition(self):
        self.client.post("/api/v1/auth/register/", self.valid_payload, format="json")
        token_response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": "newuser",
                "password": "SecurePassword123!",
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

    def test_invalid_credentials_rejected(self):
        self.client.post("/api/v1/auth/register/", self.valid_payload, format="json")
        token_response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": "newuser",
                "password": "WrongPassword!",
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_token_refresh(self):
        self.client.post("/api/v1/auth/register/", self.valid_payload, format="json")
        token_response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": "newuser",
                "password": "SecurePassword123!",
            },
            format="json",
        )
        refresh_token = token_response.data["refresh"]

        refresh_response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_bearer_authenticated_access_to_protected_endpoint(self):
        self.client.post("/api/v1/auth/register/", self.valid_payload, format="json")
        token_response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": "newuser",
                "password": "SecurePassword123!",
            },
            format="json",
        )
        access_token = token_response.data["access"]

        response = self.client.get(
            "/api/v1/research/company/?ticker=RELIANCE&market=IN",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class APISecurityTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_drf_throttling_classes_configured(self):
        throttle_classes = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_CLASSES", ())
        self.assertIn("rest_framework.throttling.AnonRateThrottle", throttle_classes)
        self.assertIn("rest_framework.throttling.UserRateThrottle", throttle_classes)
        self.assertIn("rest_framework.throttling.ScopedRateThrottle", throttle_classes)

    def test_drf_throttle_rates_configured(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.assertIn("anon", rates)
        self.assertIn("user", rates)
        self.assertIn("ai_heavy", rates)

    def test_ai_chat_view_has_stricter_throttle_scope(self):
        from apps.ai.views import AIChatView
        self.assertEqual(getattr(AIChatView, "throttle_scope", None), "ai_heavy")

    def test_cors_configuration_safe(self):
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)
        self.assertIsInstance(settings.CORS_ALLOWED_ORIGINS, list)

    def test_unauthenticated_requests_to_protected_endpoints_rejected(self):
        endpoints = [
            ("POST", "/api/v1/ai/chat/"),
            ("GET", "/api/v1/research/company/?ticker=AAPL&market=US"),
            ("GET", "/api/v1/research/sessions/"),
            ("GET", "/api/v1/research/sessions/00000000-0000-0000-0000-000000000000/"),
        ]
        for method, url in endpoints:
            if method == "POST":
                res = self.client.post(url, {})
            else:
                res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {url} did not return 401",
            )

    def test_public_endpoints_accessible_without_auth(self):
        res_health = self.client.get("/api/v1/health/")
        self.assertEqual(res_health.status_code, status.HTTP_200_OK)

        res_reg = self.client.post("/api/v1/auth/register/", {})
        self.assertEqual(res_reg.status_code, status.HTTP_400_BAD_REQUEST)

        res_token = self.client.post("/api/v1/auth/token/", {})
        self.assertEqual(res_token.status_code, status.HTTP_400_BAD_REQUEST)

        res_refresh = self.client.post("/api/v1/auth/token/refresh/", {})
        self.assertEqual(res_refresh.status_code, status.HTTP_400_BAD_REQUEST)


class HealthEndpointThrottleTestCase(TestCase):
    """Regression test proving the health endpoint is NOT subject to global DRF throttles.

    The Docker HEALTHCHECK fires repeatedly (every 10–30 s).  If it consumed the
    global AnonRateThrottle bucket it would eventually return HTTP 429 and cause
    Docker to mark the container unhealthy.  This test ensures the endpoint is
    permanently exempt from all throttle classes.
    """

    def setUp(self):
        self.client = APIClient()

    @override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {
                **settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
                "anon": "1/day",  # extremely restrictive — would normally block the 2nd request
            },
        }
    )
    def test_repeated_anonymous_health_requests_are_not_throttled(self):
        """Even under a 1/day anon rate, repeated health requests must all return 200.

        This proves the health endpoint does NOT consume the global AnonRateThrottle
        bucket regardless of how often it is called.
        """
        from django.core.cache import cache
        cache.clear()  # ensure throttle cache is clean

        for attempt in range(1, 6):
            response = self.client.get("/api/v1/health/")
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Request #{attempt} to /health/ returned {response.status_code} — should be 200",
            )
