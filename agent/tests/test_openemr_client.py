"""Tests for the OpenEMR API client.

These tests use httpx's MockTransport to simulate HTTP responses from the
OpenEMR server. No real server connection is needed — everything is faked.

Concept — Mocking HTTP calls:
    Instead of making real network requests (which would require a running
    OpenEMR instance), we replace httpx's transport layer with a function
    that returns pre-defined responses. This lets us test token acquisition,
    refresh logic, and error handling without any external dependencies.
"""

import time

import httpx
import pytest

from agent.openemr_client import (
    OpenEMRAPIError,
    OpenEMRAuthError,
    OpenEMRClient,
)

# --- Test helpers ---


def _token_response(
    access_token: str = "test-access-token",
    refresh_token: str = "test-refresh-token",
    expires_in: int = 3600,
) -> dict[str, object]:
    """Build a fake token endpoint response."""
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": "Bearer",
        "scope": "openid offline_access api:oemr",
    }


def _registration_response(
    client_id: str = "test-client-id",
    client_secret: str = "test-client-secret",
) -> dict[str, object]:
    """Build a fake client registration response."""
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": int(time.time()),
        "registration_access_token": "test-reg-token",
    }


def _make_client(**kwargs: object) -> OpenEMRClient:
    """Create a client with test defaults (no real server contact)."""
    defaults: dict[str, object] = {
        "base_url": "https://localhost:9300",
        "site": "default",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "username": "admin",
        "password": "pass",
        "verify_ssl": False,
    }
    defaults.update(kwargs)
    return OpenEMRClient(**defaults)  # type: ignore[arg-type]


# --- Token acquisition tests ---


class TestTokenAcquisition:
    """Tests for getting and refreshing OAuth2 tokens."""

    @pytest.mark.asyncio
    async def test_get_token_success(self) -> None:
        """Password grant should store access + refresh tokens."""

        async def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return httpx.Response(200, json=_token_response())
            return httpx.Response(404)

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        await client._get_token()

        assert client._access_token == "test-access-token"
        assert client._refresh_token == "test-refresh-token"
        assert client._token_expires_at > time.time()

        await client.close()

    @pytest.mark.asyncio
    async def test_get_token_failure_raises_auth_error(self) -> None:
        """Failed token request should raise OpenEMRAuthError."""

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": "invalid_grant"},
            )

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        with pytest.raises(OpenEMRAuthError, match="401"):
            await client._get_token()

        await client.close()

    @pytest.mark.asyncio
    async def test_token_refresh_on_expiry(self) -> None:
        """_ensure_token() should refresh when token is expired."""
        call_log: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            body = request.content.decode()
            if "grant_type=password" in body:
                call_log.append("password")
                return httpx.Response(200, json=_token_response())
            if "grant_type=refresh_token" in body:
                call_log.append("refresh")
                return httpx.Response(
                    200,
                    json=_token_response(access_token="refreshed-token"),
                )
            return httpx.Response(404)

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        # Get initial token
        await client._get_token()
        assert call_log == ["password"]

        # Simulate token expiry by setting the expiration to the past
        client._token_expires_at = time.time() - 1

        # _ensure_token should detect expiry and trigger a refresh
        await client._ensure_token()
        assert call_log == ["password", "refresh"]
        assert client._access_token == "refreshed-token"

        await client.close()

    @pytest.mark.asyncio
    async def test_refresh_failure_falls_back_to_password(self) -> None:
        """If refresh fails, should fall back to full password grant."""
        call_count = {"password": 0, "refresh": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            body = request.content.decode()
            if "grant_type=refresh_token" in body:
                call_count["refresh"] += 1
                return httpx.Response(401, json={"error": "invalid_grant"})
            if "grant_type=password" in body:
                call_count["password"] += 1
                return httpx.Response(200, json=_token_response())
            return httpx.Response(404)

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        await client._get_token()  # Initial password grant
        client._token_expires_at = time.time() - 1

        await client._ensure_token()  # Try refresh → fail → password fallback
        assert call_count["refresh"] == 1
        assert call_count["password"] == 2  # Initial + fallback

        await client.close()


# --- Client registration tests ---


class TestClientRegistration:
    """Tests for the OAuth2 client registration flow."""

    @pytest.mark.asyncio
    async def test_register_success(self) -> None:
        """Registration should store client_id and client_secret."""

        async def handler(request: httpx.Request) -> httpx.Response:
            if "/registration" in str(request.url):
                return httpx.Response(200, json=_registration_response())
            return httpx.Response(404)

        client = _make_client(client_id="", client_secret="")
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        await client._register_client()

        assert client.client_id == "test-client-id"
        assert client.client_secret == "test-client-secret"

        await client.close()

    @pytest.mark.asyncio
    async def test_register_failure_raises_auth_error(self) -> None:
        """Registration failure should raise OpenEMRAuthError."""

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "invalid_client_metadata"})

        client = _make_client(client_id="", client_secret="")
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        with pytest.raises(OpenEMRAuthError, match="registration failed"):
            await client._register_client()

        await client.close()


# --- API request tests ---


class TestAPIRequests:
    """Tests for authenticated GET/POST requests."""

    @pytest.mark.asyncio
    async def test_get_adds_bearer_header(self) -> None:
        """GET requests should include Authorization: Bearer header."""
        captured_headers: dict[str, str] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return httpx.Response(200, json=_token_response())
            if "/api/patient" in str(request.url):
                captured_headers.update(dict(request.headers))
                return httpx.Response(200, json={"data": [{"id": "1"}]})
            return httpx.Response(404)

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        await client.initialize()

        await client.get("/patient", params={"fname": "Phil"})

        assert "authorization" in captured_headers
        assert captured_headers["authorization"] == "Bearer test-access-token"

        await client.close()

    @pytest.mark.asyncio
    async def test_post_sends_json_body(self) -> None:
        """POST requests should send JSON body with Bearer token."""

        async def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return httpx.Response(200, json=_token_response())
            if "/api/patient" in str(request.url) and request.method == "POST":
                return httpx.Response(200, json={"data": {"uuid": "new-uuid"}})
            return httpx.Response(404)

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        await client.initialize()

        result = await client.post("/patient", json_data={"fname": "Test"})
        assert result["data"]["uuid"] == "new-uuid"

        await client.close()

    @pytest.mark.asyncio
    async def test_401_triggers_retry(self) -> None:
        """A 401 response should trigger re-auth and one retry."""
        attempt = {"count": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return httpx.Response(200, json=_token_response())
            if "/api/patient" in str(request.url):
                attempt["count"] += 1
                if attempt["count"] == 1:
                    return httpx.Response(401, text="Token expired")
                return httpx.Response(200, json={"data": []})
            return httpx.Response(404)

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        await client.initialize()

        result = await client.get("/patient")
        assert result["data"] == []
        assert attempt["count"] == 2  # First try (401) + retry (200)

        await client.close()

    @pytest.mark.asyncio
    async def test_api_error_raises_exception(self) -> None:
        """Non-401 errors should raise OpenEMRAPIError."""

        async def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return httpx.Response(200, json=_token_response())
            return httpx.Response(500, text="Internal Server Error")

        client = _make_client()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        await client.initialize()

        with pytest.raises(OpenEMRAPIError, match="500"):
            await client.get("/patient")

        await client.close()


# --- Initialize flow tests ---


class TestInitialize:
    """Tests for the full initialization flow."""

    @pytest.mark.asyncio
    async def test_initialize_with_client_id_skips_registration(self) -> None:
        """When client_id is set, initialize() should skip registration."""
        call_log: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/registration" in url:
                call_log.append("register")
                return httpx.Response(200, json=_registration_response())
            if "/token" in url:
                call_log.append("token")
                return httpx.Response(200, json=_token_response())
            return httpx.Response(404)

        client = _make_client()  # Has client_id set
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        await client.initialize()

        assert call_log == ["token"]  # No registration

        await client.close()

    @pytest.mark.asyncio
    async def test_initialize_without_client_id_registers_first(self) -> None:
        """When client_id is empty, initialize() should register first."""
        call_log: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/registration" in url:
                call_log.append("register")
                return httpx.Response(200, json=_registration_response())
            if "/token" in url:
                call_log.append("token")
                return httpx.Response(200, json=_token_response())
            return httpx.Response(404)

        client = _make_client(client_id="")
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        await client.initialize()

        assert call_log == ["register", "token"]

        await client.close()
