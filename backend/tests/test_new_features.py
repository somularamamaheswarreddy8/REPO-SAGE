import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_onboarding_guide_endpoint(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    assert list_resp.status_code == 200
    repo_id = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Request Onboarding Guide ("Start here" view)
    resp = await client.get(f"/api/v1/repositories/{repo_id}/onboarding")
    assert resp.status_code == 200
    data = resp.json()
    assert "entry_points" in data
    assert "modules" in data
    assert "module_connections" in data
    assert "module_tests" in data
    assert "unconfirmed_note" in data

    # Verify entry points have citations
    if len(data["entry_points"]) > 0:
        ep = data["entry_points"][0]
        assert "citation" in ep
        assert "status_label" in ep

    # Verify module tests distinction
    for mt in data["module_tests"]:
        assert "status_label" in mt
        if not mt["has_tests"]:
            assert mt["status_label"] == "Not confirmed from indexed files."


@pytest.mark.asyncio
async def test_pr_impact_and_test_gap_advisor(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo_id = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Create PR review
    rev_resp = await client.post(
        f"/api/v1/repositories/{repo_id}/reviews",
        json={"pr_number": 101, "title": "feat: Payment Retry & Webhook Verification"}
    )
    assert rev_resp.status_code == 201
    review_id = rev_resp.json()["id"]

    # Request PR Impact Analysis & Test-Gap Advisor
    impact_resp = await client.get(f"/api/v1/repositories/{repo_id}/reviews/{review_id}/impact")
    assert impact_resp.status_code == 200
    impact = impact_resp.json()
    assert "changed_files" in impact
    assert "downstream_impacts" in impact
    assert "affected_tests" in impact
    assert "untraced_areas" in impact
    assert "test_gaps" in impact
    assert "execution_policy" in impact
    assert "coverage_notice" in impact

    # Verify test gaps suggest specific test cases
    if len(impact["test_gaps"]) > 0:
        gap = impact["test_gaps"][0]
        assert "suggested_test" in gap
        assert "why_it_matters" in gap
        assert "citation" in gap
        assert gap["gap_category"] in ("no_related_test_found", "untested_behavior")


@pytest.mark.asyncio
async def test_commit_and_branch_comparison(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo_id = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Request comparison between main and develop
    comp_resp = await client.get(f"/api/v1/repositories/{repo_id}/compare?base=main&head=develop")
    assert comp_resp.status_code == 200
    comp = comp_resp.json()
    assert "base" in comp
    assert "head" in comp
    assert "summary" in comp
    assert "files_changed" in comp
    assert "architecture_diff" in comp
    assert "findings_diff" in comp
    assert "status_notice" in comp
    assert comp["base"]["ref_name"] == "main"
    assert comp["head"]["ref_name"] == "develop"


@pytest.mark.asyncio
async def test_dependency_inventory_endpoint(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo_id = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Request dependency inventory
    dep_resp = await client.get(f"/api/v1/repositories/{repo_id}/dependencies")
    assert dep_resp.status_code == 200
    dep_data = dep_resp.json()
    assert "manifest_files" in dep_data
    assert "summary" in dep_data
    assert "dependencies" in dep_data
    assert "verification_source" in dep_data
    assert "vulnerability_notice" in dep_data
    assert "checked_at" in dep_data

    # Verify direct vs transitive classification
    for dep in dep_data["dependencies"]:
        assert "name" in dep
        assert "declared_version" in dep
        assert "manifest_file" in dep
        assert "is_transitive" in dep


@pytest.mark.asyncio
async def test_repository_feedback_controls(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]
    repo_id = repo["id"]
    commit_sha = repo.get("indexed_commit_sha") or "7b9f8e4a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f"

    # Submit feedback for an answer
    fb_resp = await client.post(
        f"/api/v1/repositories/{repo_id}/feedback",
        json={
            "commit_sha": commit_sha,
            "target_type": "answer",
            "target_id": "ans_test_001",
            "is_useful": True,
            "reason": "Clear citation to services/payment.py"
        }
    )
    assert fb_resp.status_code == 201
    fb = fb_resp.json()
    assert fb["target_type"] == "answer"
    assert fb["target_id"] == "ans_test_001"
    assert fb["is_useful"] is True

    # List feedback for repository
    list_fb_resp = await client.get(f"/api/v1/repositories/{repo_id}/feedback")
    assert list_fb_resp.status_code == 200
    feedbacks = list_fb_resp.json()
    assert len(feedbacks) >= 1
    assert any(f["target_id"] == "ans_test_001" for f in feedbacks)
