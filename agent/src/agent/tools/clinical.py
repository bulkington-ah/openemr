"""Clinical data tools — allergies, medications, vitals, medical problems.

API endpoints used:
- GET /api/patient/{puuid}/allergy          — Patient's allergy list
- GET /api/patient/{pid}/medication         — Current medications
- GET /api/patient/{pid}/encounter/{eid}/vital — Vital signs
- GET /api/patient/{puuid}/medical_problem  — Active diagnoses
"""

from __future__ import annotations

from agent.openemr_client import OpenEMRAPIError, get_client


async def get_allergies(patient_uuid: str) -> str:
    """Get all recorded allergies for a patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        List of allergies with substance, reaction, and severity.
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_uuid}/allergy")
    except OpenEMRAPIError as e:
        return f"Error fetching allergies: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No allergies recorded for this patient."

    lines = ["Allergies:\n"]
    for a in results:
        title = a.get("title", "Unknown substance")
        reaction = a.get("reaction", "No reaction listed")
        severity = a.get("severity_al", "Unknown severity")
        lines.append(f"- {title} | Reaction: {reaction} | Severity: {severity}")

    return "\n".join(lines)


async def get_medications(patient_id: str) -> str:
    """Get current medications for a patient.

    Note: This endpoint uses the numeric patient ID (pid), not UUID.

    Args:
        patient_id: The patient's numeric ID in OpenEMR.

    Returns:
        List of medications with name, dosage, and frequency.
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_id}/medication")
    except OpenEMRAPIError as e:
        return f"Error fetching medications: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No medications recorded for this patient."

    lines = ["Medications:\n"]
    for m in results:
        title = m.get("title", "Unknown medication")
        dose = m.get("dose", "")
        route = m.get("route", "")
        freq = m.get("frequency", "")
        detail = " | ".join(x for x in [dose, route, freq] if x)
        lines.append(f"- {title}" + (f" ({detail})" if detail else ""))

    return "\n".join(lines)


async def get_vitals(patient_id: str, encounter_id: str) -> str:
    """Get vital signs from a specific encounter (visit).

    Note: This endpoint uses numeric patient ID and encounter ID.

    Args:
        patient_id: The patient's numeric ID in OpenEMR.
        encounter_id: The encounter (visit) ID.

    Returns:
        Vital signs (BP, pulse, temperature, weight, height).
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_id}/encounter/{encounter_id}/vital")
    except OpenEMRAPIError as e:
        return f"Error fetching vitals: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No vitals recorded for this encounter."

    # Usually one set of vitals per encounter; show the most recent
    v = results[0]
    lines = ["Vital Signs:\n"]

    bps = v.get("bps", "")
    bpd = v.get("bpd", "")
    if bps and bpd:
        lines.append(f"  Blood Pressure: {bps}/{bpd} mmHg")
    if v.get("pulse"):
        lines.append(f"  Pulse: {v['pulse']} bpm")
    if v.get("temperature"):
        lines.append(f"  Temperature: {v['temperature']} F")
    if v.get("respiration"):
        lines.append(f"  Respiration: {v['respiration']} breaths/min")
    if v.get("weight"):
        lines.append(f"  Weight: {v['weight']} lbs")
    if v.get("height"):
        lines.append(f"  Height: {v['height']} in")
    if v.get("BMI"):
        lines.append(f"  BMI: {v['BMI']}")
    if v.get("date"):
        lines.append(f"  Recorded: {v['date']}")

    return "\n".join(lines)


async def get_medical_problems(patient_uuid: str) -> str:
    """Get active medical problems (diagnoses) for a patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        List of medical problems with diagnosis, onset date, and status.
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_uuid}/medical_problem")
    except OpenEMRAPIError as e:
        return f"Error fetching medical problems: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No medical problems recorded for this patient."

    lines = ["Medical Problems:\n"]
    for prob in results:
        title = prob.get("title", "Unknown")
        diagnosis = prob.get("diagnosis", "")
        onset = prob.get("begdate", "Unknown onset")
        status = prob.get("status", "")
        entry = f"- {title}"
        if diagnosis:
            entry += f" ({diagnosis})"
        entry += f" | Onset: {onset}"
        if status:
            entry += f" | Status: {status}"
        lines.append(entry)

    return "\n".join(lines)
