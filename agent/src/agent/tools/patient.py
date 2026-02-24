"""Patient search and details tools.

These tools let the agent find patients and retrieve their demographic
information from OpenEMR.

API endpoints used:
- GET /api/patient          — Search patients by name, DOB, etc.
- GET /api/patient/{puuid}  — Get full details for a specific patient

TODO (Step 3): Implement real API calls using the OpenEMR HTTP client.
"""


def patient_search(query: str) -> str:
    """Search for patients by name, date of birth, or other demographics.

    Args:
        query: Search term (e.g., patient name like "Phil Dixon").

    Returns:
        Matching patient records as a formatted string.
    """
    return f"[Stub] patient_search({query!r}) — not yet implemented"


def get_patient_details(patient_uuid: str) -> str:
    """Get full demographic details for a specific patient.

    Args:
        patient_uuid: The patient's UUID (universally unique identifier)
            from OpenEMR.

    Returns:
        Patient details (name, DOB, address, phone, etc.) as a formatted string.
    """
    return f"[Stub] get_patient_details({patient_uuid!r}) — not yet implemented"
