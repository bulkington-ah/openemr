"""Drug interaction checking tool.

This tool uses the National Library of Medicine (NLM) RxNorm API to check
whether a proposed medication might interact with a patient's current
medications or allergies. This is a critical safety feature.

The NLM RxNorm API is free and public — no API key needed.

API endpoints used:
- OpenEMR: GET /api/patient/{pid}/medication (to get current meds)
- OpenEMR: GET /api/patient/{puuid}/allergy (to get allergies)
- NLM: RxNorm interaction API (to check drug-drug interactions)

TODO (Step 9): Implement drug interaction checking.
"""


def drug_interaction_check(patient_id: str, proposed_drug: str) -> str:
    """Check a proposed drug against a patient's current medications and allergies.

    This is a safety-critical tool. It:
    1. Fetches the patient's current medications from OpenEMR
    2. Fetches the patient's allergies from OpenEMR
    3. Checks the proposed drug against both using the NLM RxNorm API
    4. Returns any interactions or allergy conflicts found

    Args:
        patient_id: The patient's ID in OpenEMR.
        proposed_drug: The name of the drug being considered.

    Returns:
        Interaction report as a formatted string, including any warnings.
    """
    return (
        f"[Stub] drug_interaction_check({patient_id!r}, {proposed_drug!r})"
        " — not yet implemented"
    )
