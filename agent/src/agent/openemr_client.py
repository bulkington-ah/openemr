"""HTTP client for the OpenEMR REST API with OAuth2 authentication.

This module provides the OpenEMRClient class, which handles:
1. OAuth2 client registration (optional, for first-time setup)
2. Token acquisition via the "password grant" flow
3. Automatic token refresh when the access token expires
4. Authenticated GET/POST requests to any OpenEMR REST API endpoint

Concept — OAuth2 Password Grant:
    Unlike the Authorization Code flow (which requires a browser redirect),
    the password grant sends the user's username and password directly to
    the token endpoint. The server responds with:
    - access_token: A short-lived token (1 hour) included in every API request
    - refresh_token: A long-lived token (3 months) used to get new access tokens
    - expires_in: Seconds until the access token expires

    This flow is ideal for backend services that have known credentials.

Usage:
    client = OpenEMRClient()
    await client.initialize()  # Gets initial token
    response = await client.get("/patient", params={"fname": "Phil"})
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from agent.config import (
    OPENEMR_BASE_URL,
    OPENEMR_CLIENT_ID,
    OPENEMR_CLIENT_SECRET,
    OPENEMR_PASSWORD,
    OPENEMR_SITE,
    OPENEMR_SSL_VERIFY,
    OPENEMR_USERNAME,
)

logger = logging.getLogger(__name__)

# The scopes we request when authenticating. Each scope grants access to
# a specific type of data in the OpenEMR REST API:
# - openid: Required for all OAuth2 flows (identifies the user)
# - offline_access: Lets us get a refresh_token for long-lived sessions
# - api:oemr: Access to OpenEMR's native REST API (as opposed to FHIR)
# - user/*: Access resources as a clinician/staff role
DEFAULT_SCOPES = (
    "openid "
    "offline_access "
    "api:oemr "
    "user/patient.read "
    "user/allergy.read "
    "user/medication.read "
    "user/encounter.read "
    "user/vital.read "
    "user/medical_problem.read "
    "user/appointment.read "
    "user/practitioner.read "
    "user/insurance.read"
)


class OpenEMRAuthError(Exception):
    """Raised when OAuth2 authentication or token refresh fails."""


class OpenEMRAPIError(Exception):
    """Raised when an API request returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class OpenEMRClient:
    """Async HTTP client for the OpenEMR REST API with OAuth2 auth.

    This client manages the full OAuth2 lifecycle:
    1. (Optional) Register a new OAuth2 client with OpenEMR
    2. Get an access token using the password grant
    3. Automatically refresh the token when it expires
    4. Add the Bearer token to every API request

    Attributes:
        base_url: The OpenEMR server URL (e.g., "https://localhost:9300").
        site: The OpenEMR site name (usually "default").
        api_base: Full API base URL (e.g., "https://localhost:9300/apis/default/api").
    """

    def __init__(
        self,
        base_url: str = OPENEMR_BASE_URL,
        site: str = OPENEMR_SITE,
        client_id: str = OPENEMR_CLIENT_ID,
        client_secret: str = OPENEMR_CLIENT_SECRET,
        username: str = OPENEMR_USERNAME,
        password: str = OPENEMR_PASSWORD,
        verify_ssl: bool = OPENEMR_SSL_VERIFY,
        scopes: str = DEFAULT_SCOPES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.site = site
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.scopes = scopes

        # Construct the key URLs from the base URL and site name.
        # oauth_base is for auth endpoints, api_base is for data endpoints.
        self.oauth_base = f"{self.base_url}/oauth2/{self.site}"
        self.api_base = f"{self.base_url}/apis/{self.site}/api"

        # Token state — starts empty, populated by _get_token()
        self._access_token: str = ""
        self._refresh_token: str = ""
        self._token_expires_at: float = 0.0  # Unix timestamp

        # httpx.AsyncClient is the HTTP library that actually sends requests.
        # verify=False disables SSL cert checking (needed for self-signed certs).
        self._http = httpx.AsyncClient(
            verify=verify_ssl,
            timeout=httpx.Timeout(30.0),
        )

    async def initialize(self) -> None:
        """Initialize the client: register (if needed) and get a token.

        Call this once after creating the client. It:
        1. Registers a new OAuth2 client if no client_id is configured
        2. Obtains an initial access token via the password grant

        Raises:
            OpenEMRAuthError: If registration or token acquisition fails.
        """
        if not self.client_id:
            logger.info("No client_id configured — attempting auto-registration")
            await self._register_client()
        await self._get_token()

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    # --- OAuth2 Methods ---

    async def _register_client(self) -> None:
        """Register a new OAuth2 client with OpenEMR.

        POSTs to /oauth2/{site}/registration with our app info.
        On success, stores the returned client_id and client_secret.

        Note: Registered clients that request user/* scopes may be
        DISABLED by default and require manual admin approval in
        the OpenEMR admin UI (Admin > System > API Clients).

        Raises:
            OpenEMRAuthError: If registration fails.
        """
        url = f"{self.oauth_base}/registration"
        payload = {
            "application_type": "private",
            "client_name": "OpenEMR AI Agent",
            "redirect_uris": ["https://localhost:9300/callback"],
            "token_endpoint_auth_method": "client_secret_post",
            "contacts": ["agent@openemr.local"],
            "scope": self.scopes,
        }
        try:
            response = await self._http.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            raise OpenEMRAuthError(
                f"Client registration failed (HTTP {exc.response.status_code}): {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenEMRAuthError(
                f"Client registration request failed: {exc}"
            ) from exc

        data = response.json()
        self.client_id = data["client_id"]
        self.client_secret = data.get("client_secret", "")
        logger.info(
            "Registered OAuth2 client: %s (NOTE: may need manual "
            "approval in OpenEMR admin UI at Admin > System > API Clients)",
            self.client_id,
        )

    async def _get_token(self) -> None:
        """Get an access token using the OAuth2 password grant.

        Sends username, password, and client credentials to the token
        endpoint. On success, stores the access token, refresh token,
        and expiration time.

        The "user_role": "users" field tells OpenEMR to authenticate as
        a staff user (not a patient). This is required for user/* scopes.

        Raises:
            OpenEMRAuthError: If the token request fails.
        """
        url = f"{self.oauth_base}/token"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "scope": self.scopes,
            "user_role": "users",
        }
        await self._token_request(url, payload)

    async def _refresh_token_grant(self) -> None:
        """Refresh an expired access token using the refresh token.

        Instead of re-sending the username/password, this exchanges the
        long-lived refresh token for a new access token. If the refresh
        fails (e.g., refresh token also expired), falls back to a full
        password grant.

        Raises:
            OpenEMRAuthError: If both refresh and fallback fail.
        """
        url = f"{self.oauth_base}/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
        }
        try:
            await self._token_request(url, payload)
        except OpenEMRAuthError:
            logger.warning("Token refresh failed — falling back to password grant")
            await self._get_token()

    async def _token_request(self, url: str, payload: dict[str, str]) -> None:
        """Send a token request and store the response.

        Shared implementation for _get_token() and _refresh_token_grant().
        The token endpoint expects form-encoded data
        (application/x-www-form-urlencoded), NOT JSON.

        Args:
            url: The token endpoint URL.
            payload: The form data to send.

        Raises:
            OpenEMRAuthError: If the request fails or returns an error.
        """
        try:
            response = await self._http.post(
                url,
                data=payload,  # data= sends form-encoded, json= would send JSON
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            raise OpenEMRAuthError(
                f"Token request failed (HTTP {exc.response.status_code}): {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenEMRAuthError(f"Token request failed: {exc}") from exc

        data = response.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        expires_in = data.get("expires_in", 3600)
        # Subtract 60 seconds so we refresh BEFORE the token actually expires.
        # This prevents requests from failing due to clock drift or latency.
        self._token_expires_at = time.time() + expires_in - 60
        logger.debug("Token acquired, expires in %d seconds", expires_in)

    async def _ensure_token(self) -> None:
        """Ensure we have a valid (non-expired) access token.

        Called automatically before every API request. If the token
        has expired (or will expire within 60 seconds), refreshes it.
        """
        if not self._access_token or time.time() >= self._token_expires_at:
            if self._refresh_token:
                logger.info("Access token expired — refreshing")
                await self._refresh_token_grant()
            else:
                logger.info("No token — authenticating")
                await self._get_token()

    # --- API Request Methods ---

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated GET request to the OpenEMR REST API.

        Args:
            endpoint: API path (e.g., "/patient" or "/patient/{uuid}/allergy").
                Appended to the api_base URL automatically.
            params: Optional query parameters (e.g., {"fname": "Phil"}).

        Returns:
            The JSON response body (usually a dict or list).

        Raises:
            OpenEMRAuthError: If authentication/token refresh fails.
            OpenEMRAPIError: If the API returns an error status code.
        """
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated POST request to the OpenEMR REST API.

        Args:
            endpoint: API path (e.g., "/patient").
            json_data: The JSON body to send.

        Returns:
            The JSON response body.

        Raises:
            OpenEMRAuthError: If authentication/token refresh fails.
            OpenEMRAPIError: If the API returns an error status code.
        """
        return await self._request("POST", endpoint, json_data=json_data)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Send an authenticated request to the OpenEMR API.

        This is the internal method that get() and post() delegate to.
        It handles:
        1. Ensuring we have a valid token (refreshing if needed)
        2. Setting the Authorization: Bearer header
        3. Retrying once on 401 (in case the token was revoked server-side)
        4. Raising clear errors for non-2xx responses

        Args:
            method: HTTP method ("GET" or "POST").
            endpoint: API path relative to api_base.
            params: Query parameters for GET requests.
            json_data: JSON body for POST requests.

        Returns:
            The parsed JSON response.

        Raises:
            OpenEMRAuthError: If token management fails.
            OpenEMRAPIError: If the API returns a non-2xx status.
        """
        await self._ensure_token()

        url = f"{self.api_base}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

        try:
            response = await self._http.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
            )
        except httpx.HTTPError as exc:
            raise OpenEMRAPIError(
                status_code=0,
                detail=f"Request to {url} failed: {exc}",
            ) from exc

        # If we get a 401, the token might have been revoked server-side.
        # Try re-authenticating once before giving up.
        if response.status_code == 401:
            logger.warning("Got 401 — retrying with fresh token")
            await self._get_token()
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = await self._http.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
            )

        if response.status_code >= 400:
            raise OpenEMRAPIError(
                status_code=response.status_code,
                detail=response.text,
            )

        return response.json()


# --- Module-level singleton ---
# Provides a single shared client for the entire application.
# FastAPI runs in a single event loop, so one client instance is fine.
# Each tool function will call get_client() to get this shared instance.

_client: OpenEMRClient | None = None


async def get_client() -> OpenEMRClient:
    """Get or create the shared OpenEMRClient singleton.

    The first call creates and initializes the client (including
    OAuth2 authentication). Subsequent calls return the same instance.

    Returns:
        The initialized OpenEMRClient instance.
    """
    global _client  # noqa: PLW0603
    if _client is None:
        _client = OpenEMRClient()
        await _client.initialize()
    return _client
