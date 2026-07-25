from openai import OpenAI

from app.config import settings
from app.schemas.ai_analysis import AIServiceRequestAnalysis


SYSTEM_PROMPT = """
You are an assistant for a property maintenance service.

Analyze a service request submitted by a building resident.

Determine:
- the problem category,
- the urgency level,
- the location mentioned by the user,
- a short factual summary,
- a polite draft response for the user.

Use only the information contained in the user's message.

If the location is not provided, set location to null.

Do not invent apartment numbers, addresses, people, dates,
technicians, appointment times, or completed actions.

The draft response must acknowledge the report, but it must not
claim that a technician has already been assigned or dispatched.
""".strip()


class OpenAIConfigurationError(RuntimeError):
    """Raised when OpenAI configuration is missing."""


class AIAnalysisError(RuntimeError):
    """Raised when AI analysis cannot be produced."""


class OpenAIService:
    def __init__(
        self,
        client: OpenAI | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or settings.openai_model

        if client is not None:
            self.client = client
            return

        if not settings.openai_api_key:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY is not configured"
            )

        self.client = OpenAI(
            api_key=settings.openai_api_key
        )

    def analyze_service_request(
        self,
        user_message: str,
    ) -> AIServiceRequestAnalysis:
        response = self.client.responses.parse(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=user_message,
            text_format=AIServiceRequestAnalysis,
        )

        analysis = response.output_parsed

        if analysis is None:
            raise AIAnalysisError(
                "OpenAI did not return a valid analysis"
            )

        return analysis