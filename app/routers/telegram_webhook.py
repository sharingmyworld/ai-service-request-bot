import secrets
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)
from app.schemas.telegram_update import (
    TelegramUpdate,
    TelegramWebhookResponse,
)
from app.services.openai_service import (
    AIAnalysisError,
    OpenAIConfigurationError,
    OpenAIService,
)


router = APIRouter(
    prefix="/telegram",
    tags=["Telegram"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def get_configured_telegram_webhook_secret() -> str:
    configured_secret = settings.telegram_webhook_secret

    if (
        configured_secret is None
        or not configured_secret.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram webhook is not configured",
        )

    return configured_secret.strip()


def verify_telegram_webhook_secret(
    configured_secret: Annotated[
        str,
        Depends(
            get_configured_telegram_webhook_secret
        ),
    ],
    supplied_secret: Annotated[
        str | None,
        Header(
            alias="X-Telegram-Bot-Api-Secret-Token"
        ),
    ] = None,
) -> bool:
    if (
        supplied_secret is None
        or not secrets.compare_digest(
            supplied_secret,
            configured_secret,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook secret",
        )

    return True


WebhookVerification = Annotated[
    bool,
    Depends(verify_telegram_webhook_secret),
]


def get_openai_service() -> OpenAIService:
    return OpenAIService()


def find_request_by_telegram_update_id(
    database_session: Session,
    telegram_update_id: int,
) -> ServiceRequest | None:
    statement = select(ServiceRequest).where(
        ServiceRequest.telegram_update_id
        == telegram_update_id
    )

    return database_session.scalar(statement)


def save_duplicate_update_log(
    database_session: Session,
    service_request: ServiceRequest,
    telegram_update_id: int,
) -> None:
    duplicate_log = ActivityLog(
        service_request_id=service_request.id,
        action="telegram_update_duplicate_ignored",
        actor_type="telegram",
        actor_id=None,
        details={
            "telegram_update_id": telegram_update_id,
        },
    )

    try:
        database_session.add(duplicate_log)
        database_session.commit()

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Could not save duplicate update log",
        ) from error


def duplicate_webhook_response(
    database_session: Session,
    service_request: ServiceRequest,
    telegram_update_id: int,
) -> TelegramWebhookResponse:
    save_duplicate_update_log(
        database_session=database_session,
        service_request=service_request,
        telegram_update_id=telegram_update_id,
    )

    return TelegramWebhookResponse(
        status="duplicate",
        service_request_id=service_request.id,
    )


def save_ai_failure_log(
    database_session: Session,
    service_request_id: int,
    error: Exception,
) -> None:
    failure_log = ActivityLog(
        service_request_id=service_request_id,
        action="ai_analysis_failed",
        actor_type="ai",
        actor_id=None,
        details={
            "error_type": error.__class__.__name__,
        },
    )

    try:
        database_session.add(failure_log)
        database_session.commit()

    except SQLAlchemyError as database_error:
        database_session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Could not save AI failure log",
        ) from database_error


@router.post(
    "/webhook",
    response_model=TelegramWebhookResponse,
)
def receive_telegram_webhook(
    update: TelegramUpdate,
    database_session: DatabaseSession,
    _webhook_verified: WebhookVerification,
) -> TelegramWebhookResponse:
    telegram_message = update.message

    if (
        telegram_message is None
        or telegram_message.text is None
        or not telegram_message.text.strip()
    ):
        return TelegramWebhookResponse(
            status="ignored",
            service_request_id=None,
        )

    existing_request = (
        find_request_by_telegram_update_id(
            database_session=database_session,
            telegram_update_id=update.update_id,
        )
    )

    if existing_request is not None:
        return duplicate_webhook_response(
            database_session=database_session,
            service_request=existing_request,
            telegram_update_id=update.update_id,
        )

    cleaned_message = telegram_message.text.strip()

    telegram_user_id = (
        telegram_message.sender.id
        if telegram_message.sender is not None
        else None
    )

    actor_id = (
        str(telegram_user_id)
        if telegram_user_id is not None
        else str(telegram_message.chat.id)
    )

    service_request = ServiceRequest(
        telegram_chat_id=telegram_message.chat.id,
        telegram_user_id=telegram_user_id,
        telegram_update_id=update.update_id,
        user_message=cleaned_message,
    )

    try:
        database_session.add(service_request)
        database_session.flush()

        creation_log = ActivityLog(
            service_request_id=service_request.id,
            action="service_request_created",
            actor_type="telegram_user",
            actor_id=actor_id,
            details={
                "source": "telegram_webhook",
                "telegram_update_id": update.update_id,
                "telegram_message_id": (
                    telegram_message.message_id
                ),
                "telegram_chat_id": (
                    telegram_message.chat.id
                ),
                "message_length": len(cleaned_message),
            },
        )

        database_session.add(creation_log)
        database_session.commit()
        database_session.refresh(service_request)

    except IntegrityError as error:
        database_session.rollback()

        existing_request = (
            find_request_by_telegram_update_id(
                database_session=database_session,
                telegram_update_id=update.update_id,
            )
        )

        if existing_request is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "Could not save Telegram "
                    "service request"
                ),
            ) from error

        return duplicate_webhook_response(
            database_session=database_session,
            service_request=existing_request,
            telegram_update_id=update.update_id,
        )

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Could not save Telegram "
                "service request"
            ),
        ) from error

    try:
        ai_service = get_openai_service()

        analysis = ai_service.analyze_service_request(
            cleaned_message
        )

    except (
        OpenAIConfigurationError,
        AIAnalysisError,
        OpenAIError,
    ) as error:
        save_ai_failure_log(
            database_session=database_session,
            service_request_id=service_request.id,
            error=error,
        )

        return TelegramWebhookResponse(
            status="accepted",
            service_request_id=service_request.id,
        )

    service_request.category = analysis.category.value
    service_request.urgency = analysis.urgency.value
    service_request.location = analysis.location
    service_request.draft_response = (
        analysis.draft_response
    )
    service_request.status = (
        ServiceRequestStatus.DRAFTED
    )

    analysis_log = ActivityLog(
        service_request_id=service_request.id,
        action="ai_analysis_completed",
        actor_type="ai",
        actor_id=None,
        details={
            "category": analysis.category.value,
            "urgency": analysis.urgency.value,
            "location": analysis.location,
            "summary": analysis.summary,
        },
    )

    try:
        database_session.add(analysis_log)
        database_session.commit()
        database_session.refresh(service_request)

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Could not save AI analysis",
        ) from error

    return TelegramWebhookResponse(
        status="accepted",
        service_request_id=service_request.id,
    )