from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.schemas.ai_analysis import (
    AIServiceRequestAnalysis,
    ProblemCategory,
    UrgencyLevel,
)
from app.services.openai_service import (
    AIAnalysisError,
    OpenAIService,
    SYSTEM_PROMPT,
)


def test_openai_service_returns_validated_analysis() -> None:
    expected_analysis = AIServiceRequestAnalysis(
        category=ProblemCategory.PLUMBING,
        urgency=UrgencyLevel.HIGH,
        location="Kitchen, apartment 12",
        summary=(
            "Water is leaking from the pipe under the sink."
        ),
        draft_response=(
            "Thank you for reporting the leak. "
            "The maintenance team will review your request."
        ),
    )

    mock_client = Mock()

    mock_client.responses.parse.return_value = (
        SimpleNamespace(
            output_parsed=expected_analysis
        )
    )

    service = OpenAIService(
        client=mock_client,
        model="test-model",
    )

    result = service.analyze_service_request(
        "Water is leaking under the kitchen sink "
        "in apartment 12."
    )

    assert result == expected_analysis
    assert result.category == ProblemCategory.PLUMBING
    assert result.urgency == UrgencyLevel.HIGH
    assert result.location == "Kitchen, apartment 12"

    mock_client.responses.parse.assert_called_once_with(
        model="test-model",
        instructions=SYSTEM_PROMPT,
        input=(
            "Water is leaking under the kitchen sink "
            "in apartment 12."
        ),
        text_format=AIServiceRequestAnalysis,
    )


def test_openai_service_raises_error_when_result_is_missing(
) -> None:
    mock_client = Mock()

    mock_client.responses.parse.return_value = (
        SimpleNamespace(
            output_parsed=None
        )
    )

    service = OpenAIService(
        client=mock_client,
        model="test-model",
    )

    with pytest.raises(
        AIAnalysisError,
        match="OpenAI did not return a valid analysis",
    ):
        service.analyze_service_request(
            "The heating is not working."
        )