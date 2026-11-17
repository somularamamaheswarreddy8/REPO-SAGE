import pytest
import pytest_asyncio
import os
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Ensure environment uses test database and mock providers
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_reposage.db"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///./test_reposage.db"
os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
os.environ["DEFAULT_EMBEDDING_PROVIDER"] = "mock"
os.environ["MOCK_GITHUB_ENABLED"] = "true"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app.core.database import Base, get_db
from app.main import app

test_engine = create_async_engine("sqlite+aiosqlite:///./test_reposage.db", echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed default organizations, users, and demo repository for test session
    from app.models.user import Organization, User
    from app.models.repository import Repository, RepositorySettings
    from app.core.auth import hash_password

    async with TestingSessionLocal() as session:
        org = Organization(name="Acme Security Corp", slug="acme-corp")
        session.add(org)
        await session.flush()

        h_dev, s_dev = hash_password("DeveloperPassword123!")
        session.add(User(
            username="developer",
            email="developer@reposage.io",
            hashed_password=h_dev,
            salt=s_dev,
            github_id="developer_1",
            organization_id=org.id
        ))

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
            summary="**[DEMO REPOSITORY]** E-commerce microservice featuring order processing."
        )
        session.add(demo_repo)
        await session.flush()

        demo_settings = RepositorySettings(
            repository_id=demo_repo.id,
            optional_ci_enabled=False,
            blocking_ci_enabled=False,
            auto_review_prs=False,
            min_severity_to_alert="medium"
        )
        session.add(demo_settings)
        await session.commit()

    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists("./test_reposage.db"):
        try:
            os.remove("./test_reposage.db")
        except Exception:
            pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
