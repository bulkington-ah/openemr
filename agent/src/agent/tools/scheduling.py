"""Scheduling tools — appointments and practitioners.

These tools let the agent look up appointment information and find
practitioners (doctors, nurses, etc.) in the system.

API endpoints used:
- GET /api/patient/{pid}/appointment  — Patient's appointments
- GET /api/practitioner               — Search practitioners by name/specialty

TODO (Step 3): Implement real API calls using the OpenEMR HTTP client.
"""


def get_appointments(patient_id: str) -> str:
    """Get appointments for a patient.

    Args:
        patient_id: The patient's ID in OpenEMR.

    Returns:
        List of appointments (date, time, provider, status) as a
        formatted string.
    """
    return f"[Stub] get_appointments({patient_id!r}) — not yet implemented"


def search_practitioners(query: str) -> str:
    """Search for practitioners (doctors, nurses, etc.) by name or specialty.

    Args:
        query: Search term (e.g., "Dr. Smith" or "cardiology").

    Returns:
        Matching practitioners as a formatted string.
    """
    return f"[Stub] search_practitioners({query!r}) — not yet implemented"
