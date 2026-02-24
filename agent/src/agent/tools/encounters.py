"""Encounter history tools.

API endpoints used:
- GET /api/patient/{puuid}/encounter  — Patient's encounter list
"""

from __future__ import annotations

from agent.openemr_client import OpenEMRAPIError, get_client


async def get_encounters(patient_uuid: str) -> str:
    """Get encounter (visit) history for a patient.

    Encounters represent individual visits to the clinic. Each encounter
    has an ID that can be used with get_vitals() to retrieve vital signs.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        List of encounters with date, reason, and encounter ID.
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_uuid}/encounter")
    except OpenEMRAPIError as e:
        return f"Error fetching encounters: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No encounters found for this patient."

    lines = ["Encounters:\n"]
    for enc in results:
        date = enc.get("date", enc.get("encounterdate", "Unknown date"))
        reason = enc.get("reason", "")
        eid = enc.get("eid", enc.get("encounter", enc.get("id", "?")))
        pid = enc.get("pid", "?")
        entry = f"- Date: {date} | Encounter ID: {eid} | pid: {pid}"
        if reason:
            entry += f" | Reason: {reason}"
        lines.append(entry)

    return "\n".join(lines)
