import asyncio
from app.core.database import AsyncSessionLocal
from app.services.qa.service import CodeQAService
from app.models.repository import Repository

async def test():
    async with AsyncSessionLocal() as db:
        repo = await db.get(Repository, 1)
        qa = CodeQAService(db)
        res = await qa.answer_question(repo, "How is threat detection or get_uci_features handled in utils.py?")
        print("Answer:\n", res.answer)
        print("Citations:", res.citations)

asyncio.run(test())
