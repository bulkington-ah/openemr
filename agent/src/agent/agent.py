"""LangGraph ReAct agent for OpenEMR.

This module is the "brain" of the application. It wires together:
- An LLM (Claude) that reasons about what to do
- Tool functions that fetch data from the OpenEMR API
- A system prompt that guides Claude's behavior as a clinical assistant

The ReAct pattern (Reason → Act → Observe → Repeat):
1. Claude receives the clinician's question
2. Claude decides which tool to call (e.g., patient_search)
3. LangGraph executes the tool and feeds the result back to Claude
4. Claude either calls another tool or writes its final answer

LangGraph's `create_react_agent` manages this loop automatically.
We just provide the model, tools, and system prompt.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from pydantic import SecretStr

from agent.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

# Import the raw tool functions from each module.
# We import the functions (not the modules) so we can wrap each one
# as a StructuredTool for LangGraph.
from agent.tools.billing import get_insurance
from agent.tools.clinical import (
    get_allergies,
    get_medical_problems,
    get_medications,
    get_vitals,
)
from agent.tools.encounters import get_encounters
from agent.tools.patient import get_patient_details, patient_search
from agent.tools.scheduling import get_appointments, search_practitioners

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — instructions for Claude
# ---------------------------------------------------------------------------
# This is the most important part of the agent. The system prompt tells
# Claude *how* to behave: what role to play, which tools to use when,
# and what rules to follow. Think of it as the agent's "job description."

SYSTEM_PROMPT = """\
You are a clinical assistant for OpenEMR, an electronic medical records system.
You help healthcare providers look up patient information by querying the \
OpenEMR API through the tools available to you.

WORKFLOW:
1. When asked about a patient, ALWAYS start with patient_search to find them.
2. patient_search returns both a "pid" (numeric ID) and a "uuid" for each match.
3. Use the **uuid** for: get_patient_details, get_allergies, \
get_medical_problems, get_encounters, get_insurance.
4. Use the **pid** for: get_medications, get_appointments, get_vitals.
5. To get vitals, you first need an encounter ID — call get_encounters, \
then use the encounter ID with get_vitals.

RULES:
- Always confirm which patient you are looking at (name + DOB) before sharing \
clinical data.
- If multiple patients match a search, list them all and ask the user to \
clarify which one they mean.
- Never fabricate clinical data — only report what the API returns.
- Be concise but thorough.
- End every clinical response with: "This information is for reference only \
and does not replace clinical judgment."
"""

# ---------------------------------------------------------------------------
# Tool wrapping
# ---------------------------------------------------------------------------
# Our tool functions are plain async Python functions. LangGraph needs them
# wrapped as StructuredTool objects — a LangChain class that packages the
# function together with its name and description so the LLM knows what
# each tool does and what arguments it accepts.
#
# We use StructuredTool.from_function() instead of adding @tool decorators
# to the original functions. This way the original functions stay unchanged
# and our existing unit tests (which call them directly) keep working.


def _build_tools() -> list[StructuredTool]:
    """Wrap all raw tool functions as LangChain StructuredTools."""
    tool_functions: list[Callable[..., Coroutine[Any, Any, str]]] = [
        patient_search,
        get_patient_details,
        get_allergies,
        get_medications,
        get_vitals,
        get_medical_problems,
        get_encounters,
        get_appointments,
        search_practitioners,
        get_insurance,
    ]

    tools: list[StructuredTool] = []
    for fn in tool_functions:
        tool = StructuredTool.from_function(
            coroutine=fn,
            name=fn.__name__,
            description=fn.__doc__ or fn.__name__,
        )
        tools.append(tool)

    return tools


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------
# We build the agent lazily (on first use) so that importing this module
# doesn't fail when ANTHROPIC_API_KEY is not set (e.g., in CI).

_agent = None  # Will hold the compiled LangGraph agent


def _get_agent():  # type: ignore[no-untyped-def]
    """Create the LangGraph ReAct agent (lazily, on first call)."""
    global _agent  # noqa: PLW0603
    if _agent is not None:
        return _agent

    # mypy can't see Pydantic model fields as constructor kwargs, so we
    # suppress the type error here. This works correctly at runtime.
    model = ChatAnthropic(
        model_name=ANTHROPIC_MODEL,  # type: ignore[call-arg]
        anthropic_api_key=SecretStr(ANTHROPIC_API_KEY),  # type: ignore[call-arg]
    )

    tools = _build_tools()

    _agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return _agent


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_agent(message: str) -> str:
    """Process a user message and return the agent's response.

    This is the main entry point that the FastAPI server calls.

    When ANTHROPIC_API_KEY is not set (e.g., in CI), returns a placeholder
    response so that tests can pass without real API credentials.

    Args:
        message: The clinician's natural language question.

    Returns:
        The agent's response as a string.
    """
    # Fallback for CI / environments without an API key
    if not ANTHROPIC_API_KEY:
        return f"[Agent placeholder — no API key configured] You asked: {message}"

    agent = _get_agent()

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=message)]},
    )

    # The result contains the full message history. The last message
    # is the agent's final answer (an AIMessage).
    last_message = result["messages"][-1]
    return str(last_message.content)
