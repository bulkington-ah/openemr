"""Tests for the OpenEMR tool functions.

Each test mocks the get_client() singleton so no real OpenEMR server is
needed. We verify that tools return formatted strings and handle edge
cases (empty data, multiple results, API errors).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# We patch get_client in each tool module to return a mock client.
# The mock client's .get() method returns fake API responses.


def _mock_client(get_response: dict[str, Any]) -> AsyncMock:
    """Create a mock OpenEMRClient whose .get() returns get_response."""
    client = AsyncMock()
    client.get.return_value = get_response
    return client


# --- patient_search ---


@pytest.mark.asyncio
@patch("agent.tools.patient.get_client")
async def test_patient_search_found(mock_gc: AsyncMock) -> None:
    """Should list all matching patients with pid/uuid/DOB."""
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "fname": "Phil",
                    "lname": "Dixon",
                    "DOB": "1980-01-01",
                    "pid": "1",
                    "uuid": "abc-123",
                    "sex": "Male",
                },
            ]
        }
    )
    from agent.tools.patient import patient_search

    result = await patient_search("Phil Dixon")
    assert "Phil Dixon" in result
    assert "pid: 1" in result
    assert "abc-123" in result


@pytest.mark.asyncio
@patch("agent.tools.patient.get_client")
async def test_patient_search_multiple(mock_gc: AsyncMock) -> None:
    """Multiple matches should all appear so agent can disambiguate."""
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "fname": "John",
                    "lname": "Smith",
                    "DOB": "1970-05-15",
                    "pid": "1",
                    "uuid": "aaa",
                    "sex": "Male",
                },
                {
                    "fname": "Jane",
                    "lname": "Smith",
                    "DOB": "1985-08-20",
                    "pid": "2",
                    "uuid": "bbb",
                    "sex": "Female",
                },
            ]
        }
    )
    from agent.tools.patient import patient_search

    result = await patient_search("Smith")
    assert "2 patient(s)" in result
    assert "John Smith" in result
    assert "Jane Smith" in result


@pytest.mark.asyncio
@patch("agent.tools.patient.get_client")
async def test_patient_search_not_found(mock_gc: AsyncMock) -> None:
    """No matches should return a clear message."""
    mock_gc.return_value = _mock_client({"data": []})
    from agent.tools.patient import patient_search

    result = await patient_search("Nonexistent")
    assert "No patients found" in result


# --- get_allergies ---


@pytest.mark.asyncio
@patch("agent.tools.clinical.get_client")
async def test_get_allergies(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "title": "Penicillin",
                    "reaction": "Hives",
                    "severity_al": "severe",
                }
            ]
        }
    )
    from agent.tools.clinical import get_allergies

    result = await get_allergies("uuid-1")
    assert "Penicillin" in result
    assert "Hives" in result


@pytest.mark.asyncio
@patch("agent.tools.clinical.get_client")
async def test_get_allergies_empty(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client({"data": []})
    from agent.tools.clinical import get_allergies

    result = await get_allergies("uuid-1")
    assert "No allergies" in result


# --- get_medications ---


@pytest.mark.asyncio
@patch("agent.tools.clinical.get_client")
async def test_get_medications(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "title": "Lisinopril",
                    "dose": "10mg",
                    "route": "oral",
                    "frequency": "once daily",
                }
            ]
        }
    )
    from agent.tools.clinical import get_medications

    result = await get_medications("1")
    assert "Lisinopril" in result
    assert "10mg" in result


# --- get_encounters ---


@pytest.mark.asyncio
@patch("agent.tools.encounters.get_client")
async def test_get_encounters(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "date": "2024-01-15",
                    "reason": "Annual physical",
                    "eid": "5",
                    "pid": "1",
                }
            ]
        }
    )
    from agent.tools.encounters import get_encounters

    result = await get_encounters("uuid-1")
    assert "2024-01-15" in result
    assert "Annual physical" in result


# --- get_appointments ---


@pytest.mark.asyncio
@patch("agent.tools.scheduling.get_client")
async def test_get_appointments(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "pc_title": "Follow-up",
                    "pc_eventDate": "2024-02-15",
                    "pc_startTime": "09:00",
                    "pc_apptstatus": "-",
                }
            ]
        }
    )
    from agent.tools.scheduling import get_appointments

    result = await get_appointments("1")
    assert "Follow-up" in result
    assert "2024-02-15" in result


# --- get_insurance ---


@pytest.mark.asyncio
@patch("agent.tools.billing.get_client")
async def test_get_insurance(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "type": "primary",
                    "provider": "Blue Cross",
                    "policy_number": "BC123",
                    "group_number": "GRP1",
                }
            ]
        }
    )
    from agent.tools.billing import get_insurance

    result = await get_insurance("uuid-1")
    assert "Blue Cross" in result
    assert "BC123" in result


# --- search_practitioners ---


@pytest.mark.asyncio
@patch("agent.tools.scheduling.get_client")
async def test_search_practitioners(mock_gc: AsyncMock) -> None:
    mock_gc.return_value = _mock_client(
        {
            "data": [
                {
                    "title": "Dr.",
                    "fname": "Sarah",
                    "lname": "Johnson",
                    "specialty": "Family Medicine",
                    "npi": "1234567890",
                }
            ]
        }
    )
    from agent.tools.scheduling import search_practitioners

    result = await search_practitioners("Johnson")
    assert "Sarah Johnson" in result
    assert "Family Medicine" in result
