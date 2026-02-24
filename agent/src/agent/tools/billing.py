"""Billing tools — insurance information.

This tool retrieves insurance details for a patient, which is useful
for checking coverage before recommending treatments or procedures.

API endpoints used:
- GET /api/patient/{puuid}/insurance  — Patient's insurance policies

TODO (Step 3): Implement real API calls using the OpenEMR HTTP client.
"""


def get_insurance(patient_uuid: str) -> str:
    """Get insurance information for a patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        Insurance details (provider, policy number, group, coverage type)
        as a formatted string.
    """
    return f"[Stub] get_insurance({patient_uuid!r}) — not yet implemented"
