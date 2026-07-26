from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import CurrentAdmin
from app.models.activity_log import ActivityLog
from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)
from app.schemas.activity_log import ActivityLogRead
from app.schemas.admin_review import (
    ServiceRequestApprove,
    ServiceRequestReject,
)
from app.schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestRead,
)
from app.services.openai_service import (
    AIAnalysisError,
    OpenAIConfigurationError,
    OpenAIService,
)
from app.services.telegram_service import (
    TelegramAPIError,
    TelegramConfigurationError,
    TelegramService,
)


router = APIRouter(
    prefix="/service-requests",
    tags=["Service requests"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def provide_openai_service() -> OpenAIService:
    try:
        return OpenAIService()

    except OpenAIConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured",
        ) from error


def provide_telegram_service() -> TelegramService:
    try:
        return TelegramService()

    except TelegramConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram service is not configured",
        ) from error


AIService = Annotated[
    OpenAIService,
    Depends(provide_openai_service),
]


TelegramBotService = Annotated[
    TelegramService,
    Depends(provide_telegram_service),
]


def get_service_request_or_404(
    request_id: int,
    database_session: Session,
) -> ServiceRequest:
    service_request = database_session.get(
        ServiceRequest,
        request_id,
    )

    if service_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found",
        )

    return service_request


def ensure_request_is_drafted(
    service_request: ServiceRequest,
) -> None:
    if service_request.status != ServiceRequestStatus.DRAFTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only drafted service requests "
                "can be reviewed"
            ),
        )


def ensure_request_is_approved(
    service_request: ServiceRequest,
) -> None:
    if service_request.status != ServiceRequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only approved service requests "
                "can be sent"
            ),
        )


@router.post(
    "",
    response_model=ServiceRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_service_request(
    request_data: ServiceRequestCreate,
    database_session: DatabaseSession,
) -> ServiceRequest:
    service_request = ServiceRequest(
        telegram_chat_id=request_data.telegram_chat_id,
        telegram_user_id=request_data.telegram_user_id,
        user_message=request_data.user_message,
    )

    try:
        database_session.add(service_request)
        database_session.flush()

        actor_id = (
            str(request_data.telegram_user_id)
            if request_data.telegram_user_id is not None
            else str(request_data.telegram_chat_id)
        )

        activity_log = ActivityLog(
            service_request_id=service_request.id,
            action="service_request_created",
            actor_type="telegram_user",
            actor_id=actor_id,
            details={
                "telegram_chat_id": (
                    request_data.telegram_chat_id
                ),
                "message_length": len(
                    request_data.user_message
                ),
            },
        )

        database_session.add(activity_log)
        database_session.commit()
        database_session.refresh(service_request)

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save service request",
        ) from error

    return service_request


@router.get(
    "",
    response_model=list[ServiceRequestRead],
)
def get_service_requests(
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> list[ServiceRequest]:
    statement = (
        select(ServiceRequest)
        .order_by(ServiceRequest.created_at.desc())
    )

    service_requests = database_session.scalars(
        statement
    ).all()

    return list(service_requests)


@router.get(
    "/{request_id}",
    response_model=ServiceRequestRead,
)
def get_service_request(
    request_id: int,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> ServiceRequest:
    return get_service_request_or_404(
        request_id,
        database_session,
    )


@router.post(
    "/{request_id}/analyze",
    response_model=ServiceRequestRead,
)
def analyze_service_request(
    request_id: int,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
    ai_service: AIService,
) -> ServiceRequest:
    service_request = get_service_request_or_404(
        request_id,
        database_session,
    )

    try:
        analysis = ai_service.analyze_service_request(
            service_request.user_message
        )

    except (
        AIAnalysisError,
        OpenAIError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis failed",
        ) from error

    service_request.category = analysis.category.value
    service_request.urgency = analysis.urgency.value
    service_request.location = analysis.location
    service_request.draft_response = (
        analysis.draft_response
    )
    service_request.status = (
        ServiceRequestStatus.DRAFTED
    )

    activity_log = ActivityLog(
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
        database_session.add(activity_log)
        database_session.commit()
        database_session.refresh(service_request)

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save AI analysis",
        ) from error

    return service_request


@router.post(
    "/{request_id}/approve",
    response_model=ServiceRequestRead,
)
def approve_service_request(
    request_id: int,
    review_data: ServiceRequestApprove,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> ServiceRequest:
    service_request = get_service_request_or_404(
        request_id,
        database_session,
    )

    ensure_request_is_drafted(service_request)

    approved_response = (
        review_data.approved_response
        or service_request.draft_response
    )

    if approved_response is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service request has no draft response",
        )

    response_edited = (
        review_data.approved_response is not None
        and review_data.approved_response
        != service_request.draft_response
    )

    service_request.approved_response = approved_response
    service_request.status = (
        ServiceRequestStatus.APPROVED
    )

    activity_log = ActivityLog(
        service_request_id=service_request.id,
        action="service_request_approved",
        actor_type="admin",
        actor_id=str(current_admin.id),
        details={
            "admin_username": current_admin.username,
            "response_edited": response_edited,
        },
    )

    try:
        database_session.add(activity_log)
        database_session.commit()
        database_session.refresh(service_request)

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not approve service request",
        ) from error

    return service_request


@router.post(
    "/{request_id}/reject",
    response_model=ServiceRequestRead,
)
def reject_service_request(
    request_id: int,
    review_data: ServiceRequestReject,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> ServiceRequest:
    service_request = get_service_request_or_404(
        request_id,
        database_session,
    )

    ensure_request_is_drafted(service_request)

    service_request.status = (
        ServiceRequestStatus.REJECTED
    )
    service_request.approved_response = None

    activity_log = ActivityLog(
        service_request_id=service_request.id,
        action="service_request_rejected",
        actor_type="admin",
        actor_id=str(current_admin.id),
        details={
            "admin_username": current_admin.username,
            "reason": review_data.reason,
        },
    )

    try:
        database_session.add(activity_log)
        database_session.commit()
        database_session.refresh(service_request)

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reject service request",
        ) from error

    return service_request


@router.post(
    "/{request_id}/send",
    response_model=ServiceRequestRead,
)
def send_approved_response(
    request_id: int,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
    telegram_service: TelegramBotService,
) -> ServiceRequest:
    service_request = get_service_request_or_404(
        request_id,
        database_session,
    )

    ensure_request_is_approved(service_request)

    if service_request.approved_response is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service request has no approved response",
        )

    try:
        telegram_message_id = telegram_service.send_message(
            chat_id=service_request.telegram_chat_id,
            text=service_request.approved_response,
        )

    except TelegramAPIError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram message could not be sent",
        ) from error

    service_request.status = ServiceRequestStatus.SENT

    activity_log = ActivityLog(
        service_request_id=service_request.id,
        action="telegram_message_sent",
        actor_type="admin",
        actor_id=str(current_admin.id),
        details={
            "admin_username": current_admin.username,
            "telegram_chat_id": (
                service_request.telegram_chat_id
            ),
            "telegram_message_id": telegram_message_id,
        },
    )

    try:
        database_session.add(activity_log)
        database_session.commit()
        database_session.refresh(service_request)

    except SQLAlchemyError as error:
        database_session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save message delivery status",
        ) from error

    return service_request


@router.get(
    "/{request_id}/activity-logs",
    response_model=list[ActivityLogRead],
)
def get_service_request_activity_logs(
    request_id: int,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> list[ActivityLog]:
    get_service_request_or_404(
        request_id,
        database_session,
    )

    statement = (
        select(ActivityLog)
        .where(
            ActivityLog.service_request_id
            == request_id
        )
        .order_by(
            ActivityLog.created_at.asc(),
            ActivityLog.id.asc(),
        )
    )

    activity_logs = database_session.scalars(
        statement
    ).all()

    return list(activity_logs)