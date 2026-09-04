import base64
import json
import os
import unittest
from unittest.mock import patch

from app_config import AppConfig, ConfigurationError
from auth import AuthError, SupabaseAuthVerifier, bearer_token
from server import create_app
from supabase_storage import SupabaseMockStore, SupabaseRestClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload
        self.ok = 200 <= status_code < 300
        self.content = b"{}" if payload is not None else b""

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class CloudConfigurationTests(unittest.TestCase):
    def test_public_config_exposes_only_publishable_values(self):
        config = AppConfig("https://demo.supabase.co", "publishable")
        payload = config.public_payload()
        self.assertEqual(payload["mode"], "supabase")
        self.assertEqual(payload["supabase"]["publishable_key"], "publishable")

    def test_bearer_token_requires_bearer_scheme(self):
        self.assertEqual(bearer_token("Bearer abc"), "abc")
        with self.assertRaises(AuthError):
            bearer_token("Basic abc")

    def test_environment_rejects_modern_secret_key(self):
        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://demo.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_secret_never-browser"},
            clear=False,
        ):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_environment_rejects_legacy_service_role_jwt(self):
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "service_role"}).encode()
        ).decode().rstrip("=")
        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://demo.supabase.co", "SUPABASE_PUBLISHABLE_KEY": f"header.{payload}.signature"},
            clear=False,
        ):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_vercel_requires_supabase_configuration(self):
        with patch.dict(
            os.environ,
            {
                "VERCEL": "1",
                "SUPABASE_URL": "",
                "SUPABASE_PUBLISHABLE_KEY": "",
                "SUPABASE_ANON_KEY": "",
            },
            clear=False,
        ):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()


class CloudAuthTests(unittest.TestCase):
    def test_verifier_returns_user_identity(self):
        session = FakeSession(
            [FakeResponse(payload={"id": "user-1", "email": "me@example.com", "user_metadata": {"full_name": "Me"}})]
        )
        identity = SupabaseAuthVerifier("https://demo.supabase.co", "key", session).verify("token")
        self.assertEqual(identity.id, "user-1")
        self.assertEqual(identity.display_name, "Me")
        self.assertNotIn("token", str(identity.public_payload()))

    def test_verifier_rejects_expired_session(self):
        session = FakeSession([FakeResponse(401, {"message": "expired"})])
        with self.assertRaises(AuthError):
            SupabaseAuthVerifier("https://demo.supabase.co", "key", session).verify("secret")


class CloudStorageTests(unittest.TestCase):
    def test_mock_queries_are_user_scoped(self):
        session = FakeSession([FakeResponse(payload=[{"payload": {"slug": "mock-1"}}])])
        client = SupabaseRestClient("https://demo.supabase.co", "key", "access", session)
        mocks = SupabaseMockStore(client, "user-1").all()

        self.assertEqual(mocks[0]["slug"], "mock-1")
        params = session.calls[0][2]["params"]
        self.assertEqual(params["user_id"], "eq.user-1")

    def test_mock_upsert_writes_owner_id(self):
        session = FakeSession([FakeResponse(204)])
        client = SupabaseRestClient("https://demo.supabase.co", "key", "access", session)
        SupabaseMockStore(client, "user-1").upsert(
            {"slug": "mock-1", "title": "Mock 1", "imported_at": "2026-01-01T00:00:00Z"}
        )

        self.assertEqual(session.calls[0][2]["json"]["user_id"], "user-1")
        self.assertEqual(session.calls[0][2]["params"]["on_conflict"], "user_id,slug")


class CloudServerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            config=AppConfig("https://demo.supabase.co", "publishable"),
            auth_verifier=object(),
        )
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_public_config_does_not_require_authentication(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["auth_enabled"])

    def test_candidate_data_requires_authentication(self):
        response = self.client.get("/api/summary")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["code"], "AUTH_REQUIRED")


if __name__ == "__main__":
    unittest.main()