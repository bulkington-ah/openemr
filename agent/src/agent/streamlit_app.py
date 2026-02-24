"""Streamlit chat frontend for the OpenEMR AI agent.

Streamlit is a Python library that turns scripts into web apps. This file
creates a simple chat interface where clinicians can type questions and
see the agent's responses.

Run locally with:
    streamlit run src/agent/streamlit_app.py

The frontend talks to the FastAPI backend (app.py) which runs the agent.

TODO (Step 6): Build the actual chat UI with message history.
"""

import streamlit as st

st.set_page_config(
    page_title="OpenEMR AI Agent",
    page_icon="🏥",
)

st.title("OpenEMR Healthcare AI Agent")
st.caption("Ask questions about patients, medications, appointments, and more.")

# Placeholder — will be replaced with actual chat interface in Step 6
st.info(
    "The agent is not yet connected. "
    "Complete Steps 2-5 to wire up the LangGraph agent and FastAPI backend."
)

user_input = st.chat_input("Ask a question about a patient...")
if user_input:
    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(
        f"[Placeholder] You asked: {user_input}"
    )
