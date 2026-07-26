from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import CurrentAdmin
from app.models.service_request import (
    ServiceRequest,
    ServiceRequestStatus,
)
from app.schemas.admin_dashboard import (
    AdminDashboardResponse,
)


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def get_status_counts(
    database_session: Session,
) -> dict[str, int]:
    status_counts = {
        request_status.value: 0
        for request_status in ServiceRequestStatus
    }

    statement = (
        select(
            ServiceRequest.status,
            func.count(ServiceRequest.id),
        )
        .group_by(ServiceRequest.status)
    )

    rows = database_session.execute(
        statement
    ).all()

    for request_status, request_count in rows:
        if isinstance(
            request_status,
            ServiceRequestStatus,
        ):
            status_name = request_status.value

        else:
            status_name = str(request_status)

        status_counts[status_name] = int(
            request_count
        )

    return status_counts


def get_category_counts(
    database_session: Session,
) -> dict[str, int]:
    statement = (
        select(
            ServiceRequest.category,
            func.count(ServiceRequest.id),
        )
        .where(
            ServiceRequest.category.is_not(None)
        )
        .group_by(ServiceRequest.category)
    )

    rows = database_session.execute(
        statement
    ).all()

    return {
        str(category): int(request_count)
        for category, request_count in rows
    }


def get_urgency_counts(
    database_session: Session,
) -> dict[str, int]:
    statement = (
        select(
            ServiceRequest.urgency,
            func.count(ServiceRequest.id),
        )
        .where(
            ServiceRequest.urgency.is_not(None)
        )
        .group_by(ServiceRequest.urgency)
    )

    rows = database_session.execute(
        statement
    ).all()

    return {
        str(urgency): int(request_count)
        for urgency, request_count in rows
    }


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
)
def read_admin_dashboard(
    current_admin: CurrentAdmin,
    database_session: DatabaseSession,
) -> AdminDashboardResponse:
    total_requests = database_session.scalar(
        select(
            func.count(ServiceRequest.id)
        )
    )

    status_counts = get_status_counts(
        database_session
    )

    category_counts = get_category_counts(
        database_session
    )

    urgency_counts = get_urgency_counts(
        database_session
    )

    return AdminDashboardResponse(
        total_requests=int(
            total_requests or 0
        ),
        pending_review=status_counts[
            ServiceRequestStatus.DRAFTED.value
        ],
        approved_not_sent=status_counts[
            ServiceRequestStatus.APPROVED.value
        ],
        critical_requests=urgency_counts.get(
            "critical",
            0,
        ),
        status_counts=status_counts,
        category_counts=category_counts,
        urgency_counts=urgency_counts,
    )