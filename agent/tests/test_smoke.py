"""Smoke tests — verify the scaffolding is wired up correctly.

These tests don't check real functionality (we haven't built any yet).
They ensure that:
1. All modules can be imported without errors
2. The FastAPI app starts up properly
3. Configuration loads with default values

This is the first thing CI runs, so if these fail, nothing else will work.
"""

from fastapi.testclient import TestClient


def test_imports() -> None:
    """Verify all modules can be imported without crashing."""
    import agent  # noqa: F401
    import agent.config  # noqa: F401
    import agent.agent  # noqa: F401
    import agent.app  # noqa: F401
    import agent.tools  # noqa: F401
    import agent.tools.patient  # noqa: F401
    import agent.tools.clinical  # noqa: F401
    import agent.tools.scheduling  # noqa: F401
    import agent.tools.billing  # noqa: F401
    import agent.tools.drug_interactions  # noqa: F401
    import agent.verification  # noqa: F401


def test_config_defaults() -> None:
    """Config should load with sensible defaults even without a .env file."""
    from agent.config import OPENEMR_BASE_URL, OPENEMR_SITE

    assert OPENEMR_BASE_URL == "https://localhost:9300"
    assert OPENEMR_SITE == "default"


def test_health_endpoint() -> None:
    """The /health endpoint should return 200 OK."""
    from agent.app import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_placeholder() -> None:
    """The /chat endpoint should accept a message and return a response."""
    from agent.app import app

    client = TestClient(app)
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "Hello" in data["response"]
