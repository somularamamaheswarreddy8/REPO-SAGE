import os
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, request_id_ctx
from app.core.database import init_db, AsyncSessionLocal
from app.api.v1.router import api_router
from app.models.repository import Repository, RepositorySettings
from app.services.github.mock import MOCK_REPOSITORIES
from sqlalchemy import select, func

setup_logging("DEBUG" if settings.DEBUG else "INFO")
logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


async def seed_demo_data_if_needed():
    """Seeds organizations, default role users, and demo repositories into the database."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.user import Organization, User
        from app.core.auth import hash_password

        async with AsyncSessionLocal() as db:
            # 1. Seed Organizations
            stmt_org = select(Organization).where(Organization.slug == "acme-corp")
            res_org = await db.execute(stmt_org)
            org = res_org.scalar_one_or_none()
            if not org:
                logger.info("Seeding default organizations...")
                org = Organization(name="Acme Security Corp", slug="acme-corp")
                db.add(org)
                ext_org = Organization(name="External Tenant Corp", slug="external-tenant")
                db.add(ext_org)
                await db.flush()

            # 2. Seed Default User (GitHub authenticated)
            stmt_users = select(User)
            res_users = await db.execute(stmt_users)
            if not res_users.scalars().first():
                logger.info("Seeding default connected GitHub user...")
                h_dev, s_dev = hash_password("DeveloperPassword123!")
                db.add(User(
                    username="developer",
                    email="developer@reposage.io",
                    hashed_password=h_dev,
                    salt=s_dev,
                    github_id="gh_developer_101",
                    avatar_url="https://avatars.githubusercontent.com/u/101?v=4",
                    organization_id=org.id
                ))
                await db.flush()

            # 3. Seed Demo Repositories
            stmt = select(Repository).where(Repository.is_demo == True)
            res = await db.execute(stmt)
            existing = res.scalars().first()
            if not existing:
                logger.info("Seeding initial demo repositories...")
                demo_repo = Repository(
                    full_name="reposage-demo/ecommerce-api",
                    owner="reposage-demo",
                    name="ecommerce-api",
                    default_branch="main",
                    is_private=False,
                    is_demo=True,
                    organization_id=org.id,
                    indexed_commit_sha="7b9f8e4a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
                    indexing_status="completed",
                    indexing_progress=100.0,
                    summary=(
                        "**[DEMO REPOSITORY]** E-commerce microservice featuring order processing, "
                        "Stripe payment integration with idempotency keys, and JWT authentication token handling."
                    )
                )
                db.add(demo_repo)
                await db.flush()

                # Seed settings (optional CI disabled by default)
                demo_settings = RepositorySettings(
                    repository_id=demo_repo.id,
                    optional_ci_enabled=False,
                    auto_review_prs=False,
                    min_severity_to_alert="medium"
                )
                db.add(demo_settings)

                # Polyglot demo repo
                poly_repo = Repository(
                    full_name="reposage-demo/polyglot-platform",
                    owner="reposage-demo",
                    name="polyglot-platform",
                    default_branch="main",
                    is_private=False,
                    is_demo=True,
                    organization_id=org.id,
                    indexed_commit_sha="d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9",
                    indexing_status="completed",
                    indexing_progress=100.0,
                    summary="Polyglot microservices platform featuring Rust, Go, Java, C#, Solidity, Bash, SQL, and YAML configurations."
                )
                db.add(poly_repo)
                await db.flush()

                poly_settings = RepositorySettings(
                    repository_id=poly_repo.id,
                    optional_ci_enabled=False,
                    auto_review_prs=False,
                    min_severity_to_alert="medium"
                )
                db.add(poly_settings)

                await db.commit()
                logger.info("Demo repositories seeded successfully.")

            # Ensure demo repos have indexed code chunks
            for r_name in ["reposage-demo/ecommerce-api", "reposage-demo/polyglot-platform"]:
                repo_res = await db.execute(select(Repository).where(Repository.full_name == r_name))
                target_r = repo_res.scalar_one_or_none()
                if target_r:
                    from app.models.code_chunk import CodeChunk
                    cnt_res = await db.execute(select(func.count(CodeChunk.id)).where(CodeChunk.repository_id == target_r.id))
                    if cnt_res.scalar() == 0:
                        from app.services.indexing.pipeline import run_indexing_pipeline
                        try:
                            await run_indexing_pipeline(db, target_r.id, target_r.default_branch, True)
                            logger.info(f"Auto-indexed demo repository '{r_name}'.")
                        except Exception as idx_err:
                            logger.warning(f"Failed to auto-index demo repo {r_name}: {idx_err}")

            # Audit and re-profile existing repositories to guarantee strict data isolation
            from app.models.code_chunk import CodeChunk
            from app.services.profiler.builder import RepositoryProfiler
            all_r_res = await db.execute(select(Repository))
            for repo_item in all_r_res.scalars().all():
                if repo_item.indexing_status == "completed":
                    chunk_q = await db.execute(select(CodeChunk).where(CodeChunk.repository_id == repo_item.id))
                    r_chunks = chunk_q.scalars().all()
                    if r_chunks:
                        chunk_paths = {c.file_path for c in r_chunks}
                        needs_reprofile = False
                        if repo_item.summary and any(f in repo_item.summary for f in ["app.py", "payment.py", "routers/tasks.py"]) and not any(f in chunk_paths for f in ["app.py", "payment.py", "routers/tasks.py"]):
                            needs_reprofile = True
                        if repo_item.deep_analysis and any(f in repo_item.deep_analysis for f in ["app.py", "payment.py", "routers/tasks.py"]) and not any(f in chunk_paths for f in ["app.py", "payment.py", "routers/tasks.py"]):
                            needs_reprofile = True
                        if needs_reprofile:
                            profiler = RepositoryProfiler(repo_item, r_chunks)
                            _, deep_obj, summary_md = profiler.build_profile()
                            repo_item.summary = summary_md
                            repo_item.deep_analysis = deep_obj.model_dump_json()
                            logger.info(f"Reconciled and refreshed isolated profile for repository '{repo_item.full_name}'.")

            await db.commit()
    except Exception as e:
        logger.warning(f"Could not seed demo data: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.ENVIRONMENT})")
    await init_db()
    await seed_demo_data_if_needed()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Secure AI Code Review & Repository Assistant",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Correlation ID Middleware
app.add_middleware(CorrelationIdMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Static frontend SPA serving (Single unified host)
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist"))
if not os.path.exists(frontend_dist):
    # Try alternate relative path
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

if os.path.isdir(frontend_dist) and os.path.exists(os.path.join(frontend_dist, "index.html")):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API endpoints and docs to be handled normally
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")

        target = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "demo_mode": settings.MOCK_GITHUB_ENABLED,
            "status": "operational"
        }
