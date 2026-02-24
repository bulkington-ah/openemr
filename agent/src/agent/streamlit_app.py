"""Streamlit chat frontend for the OpenEMR AI agent.

Streamlit is a Python library that turns scripts into web apps. This file
creates a chat interface where clinicians can type questions and see the
agent's responses, with full conversation history.

How it works:
- Streamlit re-runs this entire script on every user interaction
- We use st.session_state to persist data (messages, session ID) between reruns
- Each message is sent to the FastAPI backend (app.py) via HTTP POST
- The backend runs the LangGraph agent and returns a response

Run locally with:
    streamlit run src/agent/streamlit_app.py

The FastAPI backend must be running at the URL configured below.
"""

import os

import requests
import streamlit as st

# The URL of the FastAPI backend. Defaults to localhost for local dev.
# In production (Docker), the backend runs on port 8000 in the same container
# or a neighboring container.
BACKEND_URL = os.getenv("AGENT_BACKEND_URL", "http://localhost:8000")

# --- Page config ---
st.set_page_config(
    page_title="OpenEMR AI Agent",
    page_icon="\U0001f3e5",
)

st.title("OpenEMR Healthcare AI Agent")
st.caption("Ask questions about patients, medications, appointments, and more.")

# --- Session state initialization ---
# st.session_state is a dictionary that persists across Streamlit reruns
# (each browser tab gets its own session_state).

if "messages" not in st.session_state:
    # Each entry: {"role": "user"|"assistant", "content": str}
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = None  # Will be set by the first backend response

# --- Display chat history ---
# On each rerun, redraw all previous messages so the conversation is visible.

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- Handle new user input ---

user_input = st.chat_input("Ask a question about a patient...")

if user_input:
    # Show the user's message immediately
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Send to the FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={
                        "message": user_input,
                        "session_id": st.session_state.session_id,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["response"]
                st.session_state.session_id = data.get("session_id")
            except requests.exceptions.ConnectionError:
                answer = (
                    "Could not connect to the backend. "
                    f"Is the FastAPI server running at {BACKEND_URL}?"
                )
            except requests.exceptions.Timeout:
                answer = (
                    "The request timed out. The agent may be "
                    "processing a complex query."
                )
            except Exception as e:
                answer = f"Error: {e}"

        st.write(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
