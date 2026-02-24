"""Patient search and details tools.

API endpoints used:
- GET /api/patient          — Search patients by name, DOB, etc.
- GET /api/patient/{puuid}  — Get full details for a specific patient
"""

from __future__ import annotations

from typing import Any

from agent.openemr_client import OpenEMRAPIError, get_client


async def patient_search(query: str) -> str:
    """Search for patients by name, date of birth, or other demographics.

    If the query contains a space, the first word is treated as first name
    and the last word as last name. Otherwise it searches by last name.

    Args:
        query: Search term (e.g., "Phil Dixon" or "Dixon").

    Returns:
        Matching patient records with pid, uuid, name, and DOB.
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
        data = await client.get("/patient", params=params)
    except OpenEMRAPIError as e:
        return f"Error searching for patients: {e.detail}"

    results = data.get("data", [])

    # If last-name-only search found nothing, try as first name
    if not results and len(parts) == 1:
        try:
            data = await client.get("/patient", params={"fname": query.strip()})
            results = data.get("data", [])
        except OpenEMRAPIError:
            pass

    if not results:
        return f"No patients found matching '{query}'."

    lines = [f"Found {len(results)} patient(s) matching '{query}':\n"]
    for p in results:
        name = f"{p.get('fname', '')} {p.get('lname', '')}".strip()
        dob = p.get("DOB", "Unknown DOB")
        pid = p.get("pid", "?")
        puuid = p.get("uuid", p.get("puuid", "?"))
        sex = p.get("sex", "Unknown")
        lines.append(f"- {name} | DOB: {dob} | Sex: {sex} | pid: {pid} | uuid: {puuid}")

    return "\n".join(lines)


async def get_patient_details(patient_uuid: str) -> str:
    """Get full demographic details for a specific patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        Patient demographics (name, DOB, address, phone, etc.).
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_uuid}")
    except OpenEMRAPIError as e:
        return f"Error fetching patient details: {e.detail}"

    p = data.get("data", {})
    if not p:
        return f"No patient found with UUID '{patient_uuid}'."

    name = f"{p.get('fname', '')} {p.get('lname', '')}".strip()
    lines = [
        f"Patient: {name}",
        f"  DOB: {p.get('DOB', 'Unknown')}",
        f"  Sex: {p.get('sex', 'Unknown')}",
        f"  pid: {p.get('pid', '?')}",
        f"  uuid: {p.get('uuid', p.get('puuid', '?'))}",
    ]

    # Address
    street = p.get("street", "")
    city = p.get("city", "")
    state = p.get("state", "")
    postal = p.get("postal_code", "")
    if any([street, city, state, postal]):
        addr = ", ".join(x for x in [street, city, state, postal] if x)
        lines.append(f"  Address: {addr}")

    # Contact info
    for field, label in [
        ("phone_home", "Home phone"),
        ("phone_cell", "Cell phone"),
        ("email", "Email"),
    ]:
        val = p.get(field, "")
        if val:
            lines.append(f"  {label}: {val}")

    return "\n".join(lines)
