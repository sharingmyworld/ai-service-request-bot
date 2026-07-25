import json

import pytest
from pydantic import ValidationError

from app.schemas.ai_analysis import (
    AIServiceRequestAnalysis,
    ProblemCategory,
    UrgencyLevel,
)


def test_ai_analysis_accepts_valid_data() -> None:
    analysis = AIServiceRequestAnalysis.model_validate(
        {
            "category": "plumbing",
            "urgency": "high",
            "location": "Kitchen, apartment 12",
            "summary": (
                "Water is leaking from the pipe under the sink."
            ),
            "draft_response": (
                "Thank you for your report. "
                "A plumbing technician will be contacted."
            ),
        }
    )

    assert analysis.category == ProblemCategory.PLUMBING
    assert analysis.urgency == UrgencyLevel.HIGH
    assert analysis.location == "Kitchen, apartment 12"
    assert analysis.summary == (
        "Water is leaking from the pipe under the sink."
    )
    assert analysis.draft_response == (
        "Thank you for your report. "
        "A plumbing technician will be contacted."
    )


def test_ai_analysis_validates_json_string() -> None:
    raw_ai_response = json.dumps(
        {
            "category": "electrical",
            "urgency": "critical",
            "location": "Basement",
            "summary": (
                "Sparks are visible near the electrical panel."
            ),
            "draft_response": (
                "Please stay away from the electrical panel. "
                "An emergency technician will be notified."
            ),
        }
    )

    analysis = AIServiceRequestAnalysis.model_validate_json(
        raw_ai_response
    )

    assert analysis.category == ProblemCategory.ELECTRICAL
    assert analysis.urgency == UrgencyLevel.CRITICAL
    assert analysis.location == "Basement"


def test_ai_analysis_rejects_invalid_urgency() -> None:
    with pytest.raises(ValidationError):
        AIServiceRequestAnalysis.model_validate(
            {
                "category": "heating",
                "urgency": "extremely_urgent",
                "location": "Apartment 8",
                "summary": (
                    "The heating system is not working."
                ),
                "draft_response": (
                    "Thank you for reporting the heating problem."
                ),
            }
        )


def test_ai_analysis_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        AIServiceRequestAnalysis.model_validate(
            {
                "category": "security",
                "urgency": "high",
                "location": "Main entrance",
                "summary": (
                    "The entrance door cannot be locked."
                ),
                "draft_response": (
                    "Thank you for the report. "
                    "The security team will inspect the door."
                ),
                "invented_field": "unexpected value",
            }
        )