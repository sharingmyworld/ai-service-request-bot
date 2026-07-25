from app.routers.auth import router as auth_router
from app.routers.service_requests import (
    router as service_requests_router,
)
from app.routers.telegram_webhook import (
    router as telegram_webhook_router,
)


__all__ = [
    "auth_router",
    "service_requests_router",
    "telegram_webhook_router",
]