"""FastAPI server — the HTTP entry point for the agent.

This file defines the web API that clients (like our Streamlit frontend)
use to talk to the agent. It exposes two endpoints:

- GET  /health  — Simple check that the server is running
- POST /chat    — Send a message, get back the agent's response

FastAPI is a modern Python web framework that automatically generates
API documentation (visit /docs when running) and validates request/response
data using Pydantic models.

Run locally with:
    cd agent && uvicorn agent.app:app --reload

TODO (Step 5): Add session management so conversations persist across turns.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from agent.agent import run_agent

app = FastAPI(
    title="OpenEMR Healthcare AI Agent",
    description="Ask natural language questions about patients in OpenEMR",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    """What the client sends to the /chat endpoint."""

    message: str  # The clinician's question in plain English


class ChatResponse(BaseModel):
    """What the /chat endpoint sends back."""

    response: str  # The agent's answer


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint. Returns 200 if the server is running."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message through the AI agent.

    The client sends a natural language question, and the agent
    figures out which OpenEMR API calls to make, fetches the data,
    and returns a human-friendly answer.
    """
    result = await run_agent(request.message)
    return ChatResponse(response=result)
