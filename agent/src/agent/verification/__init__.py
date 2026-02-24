"""Verification layer for the AI agent.

This package will contain verification nodes that run after the agent
generates a response but before it reaches the user. These checks help
ensure the agent's answers are accurate and safe.

Planned verifiers (Phase 2):
- Hallucination detection: Compare claims against actual API data
- Domain constraints: Enforce safety rules (allergy checks, disclaimers)
- Confidence scoring: Tag responses as high/medium/low confidence

TODO (Step 10): Implement verification nodes.
"""
