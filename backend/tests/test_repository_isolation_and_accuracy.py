import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.services.indexing.pipeline import run_indexing_pipeline


@pytest.mark.asyncio
async def test_cross_repository_isolation(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that selecting one repository never returns facts, search results, or citations
    from another repository. Confirms repository identity in the answer.
    """
    # Connect task-manager-api
    resp1 = await client.post(
        "/api/v1/repositories",
        json={"full_name": "reposage-demo/task-manager-api", "is_demo": True}
    )
    assert resp1.status_code in {201, 409}
    repo1_data = resp1.json() if resp1.status_code == 201 else (
        await client.get("/api/v1/repositories")
    ).json()
    repo1 = [r for r in (repo1_data if isinstance(repo1_data, list) else [repo1_data]) if "task-manager" in r["full_name"]][0]
    repo1_id = repo1["id"]

    # Connect inventory-service
    resp2 = await client.post(
        "/api/v1/repositories",
        json={"full_name": "reposage-demo/inventory-service", "is_demo": True}
    )
    assert resp2.status_code in {201, 409}
    repos = (await client.get("/api/v1/repositories")).json()
    repo2 = [r for r in repos if "inventory" in r["full_name"]][0]
    repo2_id = repo2["id"]

    # Index both repositories
    await run_indexing_pipeline(db_session, repo1_id, force_full_reindex=True)
    await run_indexing_pipeline(db_session, repo2_id, force_full_reindex=True)

    # Q&A on task-manager asking about warehouse sku stock
    qa1_resp = await client.post(
        f"/api/v1/repositories/{repo1_id}/qa",
        json={"query": "How is warehouse sku stock replenishment implemented?"}
    )
    assert qa1_resp.status_code == 200
    qa1_data = qa1_resp.json()
    
    # Must explicitly state repository identity
    assert "reposage-demo/task-manager-api" in qa1_data["answer"]
    assert "reposage-demo/inventory-service" not in qa1_data["answer"]
    
    # Must not contain any citations from inventory-service
    for cit in qa1_data["citations"]:
        assert "warehouse.ts" not in cit["file_path"]
        assert "inventory" not in cit["file_path"]

    # Q&A on inventory-service asking about task creation
    qa2_resp = await client.post(
        f"/api/v1/repositories/{repo2_id}/qa",
        json={"query": "How are task deadlines and projects created?"}
    )
    assert qa2_resp.status_code == 200
    qa2_data = qa2_resp.json()
    assert "reposage-demo/inventory-service" in qa2_data["answer"]
    assert "reposage-demo/task-manager-api" not in qa2_data["answer"]
    for cit in qa2_data["citations"]:
        assert "tasks.py" not in cit["file_path"]
        assert "task" not in cit["file_path"].lower()


@pytest.mark.asyncio
async def test_misleading_readme_vs_source_truth(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that repository profile matches actual source files even when the README is
    intentionally misleading or incomplete (README claims Cassandra ML pipeline, but code is FastAPI + SQLite).
    """
    resp = await client.post(
        "/api/v1/repositories",
        json={"full_name": "reposage-demo/task-manager-api", "is_demo": True}
    )
    assert resp.status_code in {201, 409}
    repos = (await client.get("/api/v1/repositories")).json()
    task_repo = [r for r in repos if "task-manager" in r["full_name"]][0]
    await run_indexing_pipeline(db_session, task_repo["id"], force_full_reindex=True)

    # Get summary
    summ_resp = await client.get(f"/api/v1/repositories/{task_repo['id']}/summary")
    assert summ_resp.status_code == 200
    data = summ_resp.json()

    overview = data["overview"]
    assert overview is not None

    # Verified frameworks and databases from actual code
    framework_names = [f["name"] for f in overview["frameworks"]]
    assert "FastAPI" in framework_names
    assert "SQLAlchemy" in framework_names

    integration_names = [i["name"] for i in overview["integrations"]]
    assert "SQLite" in integration_names

    # False README claims MUST NOT be claimed as confirmed
    assert "Cassandra" not in framework_names
    assert "Cassandra" not in integration_names
    assert "PyTorch" not in framework_names

    # Unconfirmed list must explicitly identify the discrepancy
    unconfirmed_text = " ".join(overview["unconfirmed"])
    assert "Cassandra" in unconfirmed_text
    assert "Not confirmed from the indexed files" in unconfirmed_text


@pytest.mark.asyncio
async def test_incomplete_or_failed_indexing_guard(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that an incomplete or failed indexing job CANNOT produce a completed summary.
    Returns clear reason and lets user retry.
    """
    # Create an unindexed repository
    unindexed = Repository(
        full_name="test-org/unindexed-project",
        owner="test-org",
        name="unindexed-project",
        default_branch="main",
        indexing_status="not_indexed",
        indexing_progress=0.0
    )
    db_session.add(unindexed)
    await db_session.commit()
    await db_session.refresh(unindexed)

    # 1. Summary request on not_indexed repo must return 409 Conflict
    resp1 = await client.get(f"/api/v1/repositories/{unindexed.id}/summary")
    assert resp1.status_code == 409
    assert "analysis unavailable" in resp1.json()["detail"].lower()
    assert "please index the repository" in resp1.json()["detail"].lower()

    # 2. Q&A request on not_indexed repo must return 409 Conflict
    qa_resp1 = await client.post(
        f"/api/v1/repositories/{unindexed.id}/qa",
        json={"query": "What does this repo do?"}
    )
    assert qa_resp1.status_code == 409
    assert "cannot be queried" in qa_resp1.json()["detail"]

    # 3. Summary request on failed indexing repo must return 409 with the failure reason
    unindexed.indexing_status = "failed"
    unindexed.indexing_error = "Rate limit exceeded on external git tree fetch."
    await db_session.commit()

    resp2 = await client.get(f"/api/v1/repositories/{unindexed.id}/summary")
    assert resp2.status_code == 409
    assert "Rate limit exceeded" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_branch_and_commit_refresh(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that changing branch or commit SHA refreshes the analysis, commit SHA, and citations.
    """
    resp = await client.post(
        "/api/v1/repositories",
        json={"full_name": "reposage-demo/task-manager-api", "is_demo": True}
    )
    assert resp.status_code in {201, 409}
    repos = (await client.get("/api/v1/repositories")).json()
    task_repo = [r for r in repos if "task-manager" in r["full_name"]][0]

    # Initial state is on main (commit_task_main_11111)
    await run_indexing_pipeline(db_session, task_repo["id"], branch="main", force_full_reindex=True)
    repo_obj = await db_session.get(Repository, task_repo["id"])
    assert repo_obj.indexed_commit_sha == "commit_task_main_11111"

    # Switch branch to develop
    repo_obj.default_branch = "develop"
    await db_session.commit()

    # Re-index on develop branch
    await run_indexing_pipeline(db_session, repo_obj.id, branch="develop", force_full_reindex=True)

    # Verify commit SHA updated to develop commit
    await db_session.refresh(repo_obj)
    assert repo_obj.indexed_commit_sha == "commit_task_dev_22222"

    # Verify summary endpoint reflects new commit SHA and newly added files
    summ_resp = await client.get(f"/api/v1/repositories/{repo_obj.id}/summary")
    assert summ_resp.status_code == 200
    s_data = summ_resp.json()
    assert s_data["commit_sha"] == "commit_task_dev_22222"
    assert s_data["branch"] == "develop"

    # Chunks must now include notification.py from develop branch
    chunks_stmt = select(CodeChunk).where(
        CodeChunk.repository_id == repo_obj.id,
        CodeChunk.commit_sha == "commit_task_dev_22222"
    )
    res = await db_session.execute(chunks_stmt)
    chunks = res.scalars().all()
    file_paths = [c.file_path for c in chunks]
    assert "services/notification.py" in file_paths


@pytest.mark.asyncio
async def test_citation_validity_against_commit_chunks(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that every displayed citation points to a real line in the analyzed commit.
    Unsupported claims are omitted or labeled unconfirmed.
    """
    resp = await client.post(
        "/api/v1/repositories",
        json={"full_name": "reposage-demo/task-manager-api", "is_demo": True}
    )
    assert resp.status_code in {201, 409}
    repos = (await client.get("/api/v1/repositories")).json()
    task_repo = [r for r in repos if "task-manager" in r["full_name"]][0]
    await run_indexing_pipeline(db_session, task_repo["id"], force_full_reindex=True)

    for r in repos:
        if r.get("indexing_status") != "completed":
            continue

        summ_resp = await client.get(f"/api/v1/repositories/{r['id']}/summary")
        if summ_resp.status_code != 200:
            continue

        data = summ_resp.json()
        overview = data.get("overview")
        if not overview:
            continue

        # Get all chunks for this repo and commit
        chunks_stmt = select(CodeChunk).where(
            CodeChunk.repository_id == r["id"],
            CodeChunk.commit_sha == data["commit_sha"]
        )
        res = await db_session.execute(chunks_stmt)
        chunks = res.scalars().all()
        files_dict = {c.file_path: c for c in chunks}

        # Validate purpose evidence
        for cit in overview.get("purpose_evidence", []):
            assert cit["file_path"] in files_dict, f"Cited file {cit['file_path']} does not exist in commit!"
            chunk = files_dict[cit["file_path"]]
            assert cit["start_line"] >= 1
            assert cit["start_line"] <= chunk.end_line

        # Validate framework evidence
        for f in overview.get("frameworks", []):
            if "file_path" in f:
                assert f["file_path"] in files_dict, f"Framework file {f['file_path']} does not exist in commit!"

        # Validate integration evidence
        for i in overview.get("integrations", []):
            if "file_path" in i:
                assert i["file_path"] in files_dict, f"Integration file {i['file_path']} does not exist in commit!"

        # Validate command evidence
        for c in overview.get("commands", []):
            if "file_path" in c:
                assert c["file_path"] in files_dict, f"Command file {c['file_path']} does not exist in commit!"
