import pytest
from app.services.retrieval.hybrid import cosine_similarity, HybridRetriever
from app.services.ai.mock import MockEmbeddingProvider
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from sqlalchemy.ext.asyncio import AsyncSession


def test_cosine_similarity():
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v1) == pytest.approx(1.0)

    # Orthogonal vectors
    v2 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(0.0)

    # Opposite vectors
    v3 = [-1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v3) == pytest.approx(-1.0)


@pytest.mark.asyncio
async def test_hybrid_retrieval(db_session: AsyncSession):
    emb_provider = MockEmbeddingProvider()

    # Create test repository
    repo = Repository(
        full_name="test-org/payment-service",
        owner="test-org",
        name="payment-service",
        default_branch="main",
        is_private=False,
        is_demo=True,
        indexing_status="completed",
        indexing_progress=100.0,
        indexed_commit_sha="c0ffee123456"
    )
    db_session.add(repo)
    await db_session.flush()

    # Insert test chunks
    c1_text = "def process_payment(amount: int, user_id: str):\n    return stripe_client.charge(amount)"
    c1_emb = await emb_provider.get_embedding(c1_text)
    chunk1 = CodeChunk(
        repository_id=repo.id,
        commit_sha=repo.indexed_commit_sha,
        file_path="services/payment.py",
        language="python",
        symbol_name="process_payment",
        symbol_type="function",
        start_line=10,
        end_line=15,
        content=c1_text,
        content_hash="hash1",
        embedding=c1_emb
    )

    c2_text = "def calculate_inventory_stock(item_id: int):\n    return warehouse.get_stock(item_id)"
    c2_emb = await emb_provider.get_embedding(c2_text)
    chunk2 = CodeChunk(
        repository_id=repo.id,
        commit_sha=repo.indexed_commit_sha,
        file_path="services/inventory.py",
        language="python",
        symbol_name="calculate_inventory_stock",
        symbol_type="function",
        start_line=20,
        end_line=25,
        content=c2_text,
        content_hash="hash2",
        embedding=c2_emb
    )

    db_session.add_all([chunk1, chunk2])
    await db_session.commit()

    retriever = HybridRetriever(db_session, emb_provider)

    # Query about payments
    results = await retriever.retrieve(
        repository_id=repo.id,
        query="process payment stripe charge",
        commit_sha=repo.indexed_commit_sha,
        top_k=2
    )

    assert len(results) > 0
    top_result = results[0]
    assert top_result["file_path"] == "services/payment.py"
    assert top_result["symbol_name"] == "process_payment"
    assert top_result["score"] > 0
