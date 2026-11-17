import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.repository import Repository, RepositorySettings
from app.models.review import PRReview, ReviewFinding
from app.models.audit import AuditLogEntry


@pytest.mark.asyncio
async def test_human_approval_enforcement(client: AsyncClient, db_session: AsyncSession):
    # Setup test repository and review
    repo = Repository(
        full_name="org/secure-app",
        owner="org",
        name="secure-app",
        default_branch="main",
        is_demo=True,
        indexing_status="completed",
        indexed_commit_sha="sha123"
    )
    db_session.add(repo)
    await db_session.flush()

    review = PRReview(
        repository_id=repo.id,
        pr_number=55,
        title="PR #55: Fix SQL Injection",
        base_commit_sha="sha123",
        head_commit_sha="sha456",
        status="completed",
        summary="Found 1 finding."
    )
    db_session.add(review)
    await db_session.flush()

    finding = ReviewFinding(
        review_id=review.id,
        severity="high",
        title="SQL Injection Vulnerability",
        explanation="Raw SQL query used.",
        file_path="services/payment.py",
        start_line=42,
        end_line=44,
        why_problem="Risk of data breach",
        suggested_improvement="Use parameterized query",
        confidence=0.95,
        is_confirmed_problem=True,
        published_to_github=False
    )
    db_session.add(finding)
    await db_session.commit()

    # 1. Attempt to publish WITHOUT explicit approval -> MUST FAIL (422 or 400)
    resp = await client.post(
        f"/api/v1/repositories/{repo.id}/reviews/{review.id}/publish",
        json={
            "finding_ids": [finding.id],
            "explicit_user_approval": False,
            "user_identifier": "alice"
        }
    )
    assert resp.status_code in {400, 422}

    # Verify nothing was published
    await db_session.refresh(finding)
    assert finding.published_to_github is False

    # 2. Attempt to publish WITH explicit user approval -> MUST SUCCEED
    resp = await client.post(
        f"/api/v1/repositories/{repo.id}/reviews/{review.id}/publish",
        json={
            "finding_ids": [finding.id],
            "explicit_user_approval": True,
            "user_identifier": "alice"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["published_count"] == 1
    assert finding.id in data["published_findings"]

    # 3. Verify audit log entry was created
    audit_id = data["audit_log_id"]
    audit_entry = await db_session.get(AuditLogEntry, audit_id)
    assert audit_entry is not None
    assert audit_entry.action_type == "publish_review_comments"
    assert audit_entry.user_id == "alice"
    assert audit_entry.repo_full_name == "org/secure-app"
    assert audit_entry.pr_number == 55
    assert audit_entry.status == "success"


@pytest.mark.asyncio
async def test_optional_ci_check_disabled_by_default(client: AsyncClient, db_session: AsyncSession):
    # Setup repo with CI check disabled
    repo = Repository(
        full_name="org/ci-test-repo",
        owner="org",
        name="ci-test-repo",
        default_branch="main",
        is_demo=True,
        indexing_status="completed",
        indexed_commit_sha="sha000"
    )
    db_session.add(repo)
    await db_session.flush()

    settings_obj = RepositorySettings(
        repository_id=repo.id,
        optional_ci_enabled=False  # Disabled by default
    )
    db_session.add(settings_obj)

    review = PRReview(
        repository_id=repo.id,
        pr_number=12,
        title="PR #12",
        base_commit_sha="sha000",
        head_commit_sha="sha111",
        status="completed"
    )
    db_session.add(review)
    await db_session.commit()

    # Attempt to dispatch CI check summary while disabled -> MUST FAIL (403 Forbidden)
    resp = await client.post(f"/api/v1/repositories/{repo.id}/reviews/{review.id}/ci-check")
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()

    # Now enable CI check in settings
    put_resp = await client.put(
        f"/api/v1/repositories/{repo.id}/settings",
        json={"optional_ci_enabled": True, "auto_review_prs": False, "min_severity_to_alert": "medium"}
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["optional_ci_enabled"] is True

    # Now dispatch CI check -> MUST SUCCEED
    resp2 = await client.post(f"/api/v1/repositories/{repo.id}/reviews/{review.id}/ci-check")
    assert resp2.status_code == 200
