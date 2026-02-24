"""Configuration for the OpenEMR agent.

Loads settings from environment variables (via a .env file or the system
environment). Uses sensible defaults so the module can be imported even
when env vars are not set — this is important because CI needs to import
it for type checking without having real API keys.

At *runtime* (when actually serving requests), missing keys will cause
clear error messages rather than silent failures.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists (it won't exist in CI or Docker — that's fine)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# --- OpenEMR connection ---
# The base URL of the OpenEMR instance (the REST API lives under this)
OPENEMR_BASE_URL: str = os.getenv("OPENEMR_BASE_URL", "https://localhost:9300")

# OAuth2 client credentials — obtained by registering with OpenEMR's
# /oauth2/{site}/registration endpoint. We'll set these up in Step 2.
OPENEMR_CLIENT_ID: str = os.getenv("OPENEMR_CLIENT_ID", "")
OPENEMR_CLIENT_SECRET: str = os.getenv("OPENEMR_CLIENT_SECRET", "")

# --- LLM (Large Language Model) ---
# The API key for Anthropic's Claude, which powers the agent's reasoning
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# --- Observability ---
# LangSmith is a platform that records every step the agent takes,
# so you can debug and evaluate its behavior. These two env vars
# enable automatic tracing — no code changes needed.
LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")

# --- OpenEMR site identifier ---
# OpenEMR supports multiple "sites" (separate databases). The default
# installation uses "default" as the site name.
OPENEMR_SITE: str = os.getenv("OPENEMR_SITE", "default")
