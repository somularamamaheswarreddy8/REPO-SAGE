import asyncio
from app.core.database import AsyncSessionLocal
from app.services.indexing.pipeline import run_indexing_pipeline

async def reindex_repo1():
    async with AsyncSessionLocal() as db:
        res = await run_indexing_pipeline(db, 1, "main", force_full_reindex=True)
        print("Re-indexed Repo 1:", res)

asyncio.run(reindex_repo1())
