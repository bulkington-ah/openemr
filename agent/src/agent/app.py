"""FastAPI server — the HTTP entry point for the agent.

This file defines the web API that clients (like our Streamlit frontend)
use to talk to the agent. It exposes two endpoints:

- GET  /agent/health  — Simple check that the server is running
- POST /agent/chat    — Send a message, get back the agent's response

FastAPI is a modern Python web framework that automatically generates
API documentation (visit /docs when running) and validates request/response
data using Pydantic models.

Run locally with:
    cd agent && uvicorn agent.app:app --reload
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
    """What the client sends to the /agent/chat endpoint."""

    message: str  # The clinician's question in plain English
    session_id: str | None = None  # Optional: continue an existing conversation


class ChatResponse(BaseModel):
    """What the /agent/chat endpoint sends back."""

    response: str  # The agent's answer
    session_id: str  # The session ID (new or existing) for follow-up messages


@app.get("/agent/health")
async def health() -> dict[str, str]:
    """Health check endpoint. Returns 200 if the server is running."""
    return {"status": "ok"}


@app.post("/agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message through the AI agent.

    The client sends a natural language question, and the agent
    figures out which OpenEMR API calls to make, fetches the data,
    and returns a human-friendly answer.

    Include a session_id to continue a previous conversation. If omitted,
    a new session is created and its ID is returned in the response.
    """
    response_text, session_id = await run_agent(
        request.message, session_id=request.session_id
    )
    return ChatResponse(response=response_text, session_id=session_id)
