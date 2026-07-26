from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import CurrentAdmin
from app.models.activity_log import ActivityLog
from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)
from app.schemas.activity_log import ActivityLogRead
from app.schemas.admin_service_requests import (
    AdminServiceRequestListResponse,
)
from app.schemas.ai_analysis import (
    ProblemCategory,
    UrgencyLevel,
)
from app.schemas.service_request import ServiceRequestRead


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


StatusFilter = Annotated[
    ServiceRequestStatus | None,
    Query(
        alias="status",
        description="Filter requests by status.",
    ),
]


CategoryFilter = Annotated[
    ProblemCategory | None,
    Query(
        description="Filter requests by category.",
    ),
]


UrgencyFilter = Annotated[
    UrgencyLevel | None,
    Query(
        description="Filter requests by urgency.",
    ),
]


SearchFilter = Annotated[
    str | None,
    Query(
        min_length=1,
        max_length=100,
        description=(
            "Search in the user message and location."
        ),
    ),
]


OffsetParameter = Annotated[
    int,
    Query(
        ge=0,
        description="Number of requests to skip.",
    ),
]


LimitParameter = Annotated[
    int,
    Query(
        ge=1,
        le=100,
        description=(
            "Maximum number of requests to return."
        ),
    ),
]


def get_admin_service_request_or_404(
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


@router.get(
    "/service-requests",
    response_model=AdminServiceRequestListResponse,
)
def read_admin_service_requests(
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
    request_status: StatusFilter = None,
    category: CategoryFilter = None,
    urgency: UrgencyFilter = None,
    search: SearchFilter = None,
    offset: OffsetParameter = 0,
    limit: LimitParameter = 20,
) -> AdminServiceRequestListResponse:
    filters = []

    if request_status is not None:
        filters.append(
            ServiceRequest.status == request_status
        )

    if category is not None:
        filters.append(
            ServiceRequest.category == category.value
        )

    if urgency is not None:
        filters.append(
            ServiceRequest.urgency == urgency.value
        )

    if search is not None:
        cleaned_search = search.strip()

        search_pattern = (
            f"%{cleaned_search}%"
        )

        filters.append(
            or_(
                ServiceRequest.user_message.ilike(
                    search_pattern
                ),
                ServiceRequest.location.ilike(
                    search_pattern
                ),
            )
        )

    count_statement = select(
        func.count(ServiceRequest.id)
    )

    request_statement = select(
        ServiceRequest
    )

    if filters:
        count_statement = count_statement.where(
            *filters
        )

        request_statement = request_statement.where(
            *filters
        )

    total = database_session.scalar(
        count_statement
    )

    request_statement = (
        request_statement
        .order_by(
            ServiceRequest.created_at.desc(),
            ServiceRequest.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    service_requests = database_session.scalars(
        request_statement
    ).all()

    return AdminServiceRequestListResponse(
        items=list(service_requests),
        total=int(total or 0),
        offset=offset,
        limit=limit,
    )


@router.get(
    "/service-requests/{request_id}",
    response_model=ServiceRequestRead,
)
def read_admin_service_request(
    request_id: int,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> ServiceRequest:
    return get_admin_service_request_or_404(
        request_id=request_id,
        database_session=database_session,
    )


@router.get(
    "/service-requests/{request_id}/activity-logs",
    response_model=list[ActivityLogRead],
)
def read_admin_service_request_activity_logs(
    request_id: int,
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> list[ActivityLog]:
    get_admin_service_request_or_404(
        request_id=request_id,
        database_session=database_session,
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