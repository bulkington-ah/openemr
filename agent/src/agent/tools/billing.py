"""Billing tools — insurance information.

API endpoints used:
- GET /api/patient/{puuid}/insurance  — Patient's insurance policies
"""

from __future__ import annotations

from agent.openemr_client import OpenEMRAPIError, get_client


async def get_insurance(patient_uuid: str) -> str:
    """Get insurance information for a patient.

    Args:
        patient_uuid: The patient's UUID from OpenEMR.

    Returns:
        Insurance details (provider, policy number, group, type).
    """
    client = await get_client()

    try:
        data = await client.get(f"/patient/{patient_uuid}/insurance")
    except OpenEMRAPIError as e:
        return f"Error fetching insurance: {e.detail}"

    results = data.get("data", [])
    if not results:
        return "No insurance information recorded for this patient."

    lines = ["Insurance:\n"]
    for ins in results:
        ins_type = ins.get("type", "Unknown type")
        provider = ins.get("provider", "Unknown provider")
        policy = ins.get("policy_number", "")
        group = ins.get("group_number", "")
        entry = f"- {ins_type}: {provider}"
        if policy:
            entry += f" | Policy: {policy}"
        if group:
            entry += f" | Group: {group}"
        lines.append(entry)

    return "\n".join(lines)
