from app.routers.admin_dashboard import (
    router as admin_dashboard_router,
)
from app.routers.admin_service_requests import (
    router as admin_service_requests_router,
)
from app.routers.auth import router as auth_router
from app.routers.service_requests import (
    router as service_requests_router,
)
from app.routers.telegram_webhook import (
    router as telegram_webhook_router,
)


__all__ = [
    "admin_dashboard_router",
    "admin_service_requests_router",
    "auth_router",
    "service_requests_router",
    "telegram_webhook_router",
]