from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.repositories import router as repos_router
from app.api.v1.indexing import router as indexing_router
from app.api.v1.qa import router as qa_router
from app.api.v1.relationships import router as rel_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.audit import router as audit_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(repos_router)
api_router.include_router(indexing_router)
api_router.include_router(qa_router)
api_router.include_router(rel_router)
api_router.include_router(reviews_router)
api_router.include_router(feedback_router)
api_router.include_router(evaluation_router)
api_router.include_router(webhooks_router)
api_router.include_router(audit_router)
