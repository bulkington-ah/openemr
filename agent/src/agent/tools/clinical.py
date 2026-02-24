"""Clinical data tools — allergies, medications, vitals, medical problems.

These tools retrieve clinical information for a specific patient. The agent
typically calls patient_search first to find the patient's UUID, then uses
these tools to get their clinical data.

API endpoints used:
- GET /api/patient/{puuid}/allergy          — Patient's allergy list
- GET /api/patient/{pid}/medication         — Current medications
- GET /api/patient/{pid}/encounter/{eid}/vital — Vital signs from an encounter
- GET /api/patient/{puuid}/medical_problem  — Active medical problems/diagnoses

TODO (Step 3): Implement real API calls using the OpenEMR HTTP client.
"""


def get_allergies(patient_uuid: str) -> str:
    """Get all recorded allergies for a patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        List of allergies (substance, reaction, severity) as a formatted string.
    """
    return f"[Stub] get_allergies({patient_uuid!r}) — not yet implemented"


def get_medications(patient_id: str) -> str:
    """Get current medications for a patient.

    Args:
        patient_id: The patient's ID in OpenEMR.

    Returns:
        List of medications (name, dosage, frequency) as a formatted string.
    """
    return f"[Stub] get_medications({patient_id!r}) — not yet implemented"


def get_vitals(patient_id: str, encounter_id: str) -> str:
    """Get vital signs from a specific encounter (visit).

    Vitals include blood pressure, heart rate, temperature, weight, etc.

    Args:
        patient_id: The patient's ID in OpenEMR.
        encounter_id: The encounter (visit) ID to get vitals from.

    Returns:
        Vital signs as a formatted string.
    """
    return (
        f"[Stub] get_vitals({patient_id!r}, {encounter_id!r}) — not yet implemented"
    )


def get_medical_problems(patient_uuid: str) -> str:
    """Get active medical problems (diagnoses) for a patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        List of medical problems (diagnosis, onset date, status) as a
        formatted string.
    """
    return f"[Stub] get_medical_problems({patient_uuid!r}) — not yet implemented"
