import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data

    resp_ready = await client.get("/api/v1/health/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_repository_lifecycle_and_indexing(client: AsyncClient):
    # Connect a demo repository
    resp = await client.post(
        "/api/v1/repositories",
        json={"full_name": "reposage-demo/ecommerce-api", "is_demo": True}
    )
    # May be 201 or 409 if seeded during lifespan
    assert resp.status_code in {201, 409}

    # List repositories
    list_resp = await client.get("/api/v1/repositories")
    assert list_resp.status_code == 200
    repos = list_resp.json()
    assert len(repos) >= 1
    repo = [r for r in repos if r["full_name"] == "reposage-demo/ecommerce-api"][0]
    repo_id = repo["id"]

    # Trigger indexing
    idx_resp = await client.post(
        f"/api/v1/repositories/{repo_id}/index",
        json={"force_full_reindex": True}
    )
    assert idx_resp.status_code == 202

    # Check indexing status
    status_resp = await client.get(f"/api/v1/repositories/{repo_id}/index/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "status" in status_data
    assert "total_chunks" in status_data


@pytest.mark.asyncio
async def test_code_qa_endpoint(client: AsyncClient):
    # Find existing repo
    list_resp = await client.get("/api/v1/repositories")
    repos = list_resp.json()
    repo_id = repos[0]["id"]

    # Ask code question
    qa_resp = await client.post(
        f"/api/v1/repositories/{repo_id}/qa",
        json={"query": "How is authentication handled?", "max_citations": 3}
    )
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert "answer" in qa_data
    assert "citations" in qa_data


@pytest.mark.asyncio
async def test_pr_review_and_feedback(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo_id = list_resp.json()[0]["id"]

    # Create PR review
    rev_resp = await client.post(
        f"/api/v1/repositories/{repo_id}/reviews",
        json={
            "pr_number": 101,
            "title": "feat: Add payment retry & gateway webhook support"
        }
    )
    assert rev_resp.status_code == 201
    rev_data = rev_resp.json()
    assert rev_data["pr_number"] == 101
    assert "findings" in rev_data
    assert len(rev_data["findings"]) > 0

    first_finding = rev_data["findings"][0]
    finding_id = first_finding["id"]

    # Submit feedback (useful)
    fb_resp = await client.post(
        f"/api/v1/findings/{finding_id}/feedback",
        json={"is_useful": True, "reason": "Accurate SQL injection detection"}
    )
    assert fb_resp.status_code == 201
    fb_data = fb_resp.json()
    assert fb_data["is_useful"] is True

    # Check evaluation metrics
    metrics_resp = await client.get("/api/v1/evaluation/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert "precision" in metrics_data
    assert "recall" in metrics_data
    assert metrics_data["total_feedbacks_recorded"] >= 1
