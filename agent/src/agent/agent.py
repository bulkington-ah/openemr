"""LangGraph ReAct agent for OpenEMR.

This module will contain the core agent logic — the "brain" that:
1. Receives a user's natural language question
2. Decides which OpenEMR API tool(s) to call
3. Calls them, reads the results
4. Formulates a human-friendly answer

It uses the ReAct pattern (Reason → Act → Observe → Repeat):
- "Reason": Claude thinks about what information it needs
- "Act": Claude calls one of our tools (e.g., patient_search)
- "Observe": Claude reads the tool's response (e.g., patient data)
- "Repeat": If more info is needed, Claude calls another tool
- "Done": Claude writes a final answer for the clinician

LangGraph manages this loop for us. We just need to define:
- The state (what data flows through the loop)
- The tools (what actions the agent can take)
- The system prompt (instructions for how Claude should behave)

TODO (Step 4): Build the actual LangGraph agent here.
"""


async def run_agent(message: str) -> str:
    """Process a user message and return the agent's response.

    This is the main entry point that the FastAPI server calls.
    For now it returns a placeholder — we'll wire up LangGraph in Step 4.

    Args:
        message: The clinician's natural language question.

    Returns:
        The agent's response as a string.
    """
    return f"[Agent placeholder] You asked: {message}"
