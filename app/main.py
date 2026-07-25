from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.routers.service_requests import (
    router as service_requests_router,
)
from app.routers.telegram_webhook import (
    router as telegram_webhook_router,
)


app = FastAPI(
    title="AI Service Request Bot API",
    description=(
        "API for managing AI-classified "
        "service requests."
    ),
    version="0.1.0",
)


app.include_router(service_requests_router)
app.include_router(telegram_webhook_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": (
            "AI Service Request Bot API is running"
        )
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy"
    }


@app.get("/health/database")
def database_health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1")
            )
            result.scalar_one()

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail="Database connection failed",
        ) from error

    return {
        "status": "healthy",
        "database": "connected",
    }