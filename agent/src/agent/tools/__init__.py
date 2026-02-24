"""OpenEMR API tools for the AI agent.

Each module in this package contains "tools" — Python functions that the
AI agent can call to fetch data from OpenEMR's REST API. The agent reads
each tool's description (the docstring) to decide which one to use.

Tools are organized by domain:
- patient.py:           Search patients, get patient details
- clinical.py:          Allergies, medications, vitals, medical problems
- scheduling.py:        Appointments, practitioners
- billing.py:           Insurance information
- drug_interactions.py: Check drug interactions (uses external NLM API)
"""
