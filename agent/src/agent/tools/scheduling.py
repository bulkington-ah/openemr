"""Scheduling tools — appointments and practitioners.

API endpoints used:
- GET /api/patient/{pid}/appointment  — Patient's appointments
- GET /api/practitioner               — Search practitioners
"""

from __future__ import annotations

from typing import Any

from agent.openemr_client import OpenEMRAPIError, get_client


async def get_appointments(patient_id: str) -> str:
    """Get appointments for a patient.

    Note: This endpoint uses the numeric patient ID (pid), not UUID.

    Args:
        patient_id: The patient's numeric ID in OpenEMR.

    Returns:
        List of appointments with date, time, title, and status.
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_id}/appointment")
    except OpenEMRAPIError as e:
        return f"Error fetching appointments: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No appointments found for this patient."

    lines = ["Appointments:\n"]
    for appt in results:
        title = appt.get("pc_title", "Untitled")
        date = appt.get("pc_eventDate", "Unknown date")
        time = appt.get("pc_startTime", "")
        status = appt.get("pc_apptstatus", "")
        lines.append(
            f"- {title} | Date: {date}"
            + (f" {time}" if time else "")
            + (f" | Status: {status}" if status else "")
        )

    return "\n".join(lines)


async def search_practitioners(query: str) -> str:
    """Search for practitioners (doctors, nurses, etc.) by name.

    Args:
        query: Search term (e.g., "Smith" or "Dr. Johnson").

    Returns:
        Matching practitioners with name, specialty, and NPI.
    """
    client = await get_client()

    params: dict[str, Any] = {}
    parts = query.strip().split()
    if len(parts) >= 2:
        params["fname"] = parts[0]
        params["lname"] = parts[-1]
    else:
        params["lname"] = query.strip()

    try:
        data = await client.get("/practitioner", params=params)
    except OpenEMRAPIError as e:
        return f"Error searching practitioners: {e.detail}"

    results = data.get("data", [])
    if not results:
        return f"No practitioners found matching '{query}'."

    lines = [f"Found {len(results)} practitioner(s):\n"]
    for pr in results:
        title = pr.get("title", "")
        name = f"{title} {pr.get('fname', '')} {pr.get('lname', '')}".strip()
        specialty = pr.get("specialty", "")
        npi = pr.get("npi", "")
        phone = pr.get("phonew1", pr.get("phone", ""))
        entry = f"- {name}"
        if specialty:
            entry += f" | Specialty: {specialty}"
        if npi:
            entry += f" | NPI: {npi}"
        if phone:
            entry += f" | Phone: {phone}"
        lines.append(entry)

    return "\n".join(lines)
