import pytest
import json
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_and_profile(client: AsyncClient):
    # Test valid login with seeded connected developer account
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "developer", "password": "DeveloperPassword123!"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "developer"
    assert "role" not in data["user"]
    token = data["access_token"]

    # Test me endpoint with bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "developer"
    assert "role" not in me_data

    # Test invalid login credentials
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "developer", "password": "WrongPassword!"}
    )
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_audit_trail_cryptographic_verification(client: AsyncClient):
    # Verify cryptographic hash chain integrity
    verify_resp = await client.get("/api/v1/audit/verify")
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["is_valid"] is True
    assert v_data["total_entries"] >= 0
    assert v_data["tampered_entry_id"] is None


@pytest.mark.asyncio
async def test_health_dashboard_endpoint(client: AsyncClient):
    # Get repositories
    list_resp = await client.get("/api/v1/repositories")
    assert list_resp.status_code == 200
    repos = list_resp.json()
    assert len(repos) > 0
    repo_id = [r for r in repos if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Query health dashboard
    hd_resp = await client.get(f"/api/v1/repositories/{repo_id}/health-dashboard")
    assert hd_resp.status_code == 200
    hd = hd_resp.json()
    assert "total_discovered_files" in hd
    assert "indexed_files_count" in hd
    assert "parser_aware_count" in hd
    assert "text_fallback_count" in hd
    assert "excluded_secrets_count" in hd
    assert "database_mode" in hd
    assert "database_vector_capabilities" in hd
    assert "files_summary" in hd


@pytest.mark.asyncio
async def test_review_exports_sarif_json_markdown(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo_id = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Create PR review
    rev_resp = await client.post(
        f"/api/v1/repositories/{repo_id}/reviews",
        json={
            "pr_number": 202,
            "title": "fix: Harden input validation and connection pooling"
        }
    )
    assert rev_resp.status_code == 201
    review_id = rev_resp.json()["id"]

    # Export as Markdown
    md_resp = await client.get(f"/api/v1/repositories/{repo_id}/reviews/{review_id}/export?format=markdown")
    assert md_resp.status_code == 200
    assert md_resp.headers["content-type"].startswith("text/markdown")
    assert "# RepoSage Code Review Report" in md_resp.text

    # Export as JSON
    json_resp = await client.get(f"/api/v1/repositories/{repo_id}/reviews/{review_id}/export?format=json")
    assert json_resp.status_code == 200
    data = json_resp.json()
    assert data["pr_number"] == 202
    assert "findings" in data

    # Export as SARIF
    sarif_resp = await client.get(f"/api/v1/repositories/{repo_id}/reviews/{review_id}/export?format=sarif")
    assert sarif_resp.status_code == 200
    sarif = sarif_resp.json()
    assert sarif["version"] == "2.1.0"
    assert "$schema" in sarif
    assert len(sarif["runs"]) == 1
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "RepoSage AI Code Reviewer"


@pytest.mark.asyncio
async def test_repository_access_authorization(client: AsyncClient):
    list_resp = await client.get("/api/v1/repositories")
    repo_id = [r for r in list_resp.json() if r.get("full_name") == "reposage-demo/ecommerce-api"][0]["id"]

    # Login as developer (authorized)
    dev_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "developer", "password": "DeveloperPassword123!"}
    )
    dev_token = dev_login.json()["access_token"]

    # Developer can update repository settings
    settings_resp = await client.put(
        f"/api/v1/repositories/{repo_id}/settings",
        json={"blocking_ci_enabled": True},
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert settings_resp.status_code == 200
    assert settings_resp.json()["blocking_ci_enabled"] is True


@pytest.mark.asyncio
async def test_content_secret_scanning_protection(client: AsyncClient):
    # Check content scanner
    from app.services.parser.filters import classify_file_safety
    sample_secret_code = "AWS_SECRET_KEY = 'AKIAIOSFODNN7EXAMPLE'\nSECRET = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"
    allowed, reason, category, is_secret, _ = classify_file_safety("config.py", len(sample_secret_code), content=sample_secret_code)
    assert allowed is False
    assert is_secret is True
