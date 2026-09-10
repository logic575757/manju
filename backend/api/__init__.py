from fastapi import APIRouter
from .auth import router as auth_router
from .scripts import router as scripts_router
from .ai import router as ai_router
from .tags import router as tags_router
from .imports import router as imports_router
from .characters import router as characters_router
from .episodes import router as episodes_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(scripts_router)
api_router.include_router(characters_router)
api_router.include_router(episodes_router)
api_router.include_router(ai_router)
api_router.include_router(tags_router)
api_router.include_router(imports_router)
