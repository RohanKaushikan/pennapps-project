from fastapi import APIRouter
from .endpoints import users, countries, alerts, sources, location, reactive_alerts

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(countries.router, prefix="/countries", tags=["Countries"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(sources.router, prefix="/sources", tags=["Sources"])
api_router.include_router(location.router, tags=["Location"])
api_router.include_router(reactive_alerts.router, prefix="/reactive", tags=["Reactive Alerts"])

__all__ = ["api_router"]