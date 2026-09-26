from fastapi import APIRouter, Depends

from app.api.routes import articles, auth, health, integrations, wordpress
from app.api.routes.auth import require_user

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    articles.router, prefix="/articles", tags=["articles"], dependencies=[Depends(require_user)]
)
api_router.include_router(
    wordpress.router, prefix="/wordpress", tags=["wordpress"], dependencies=[Depends(require_user)]
)
api_router.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_user)],
)
