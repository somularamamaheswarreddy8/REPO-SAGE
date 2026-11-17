import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.languages.detect import detect_file_language
from app.services.languages.registry import language_registry
from app.services.parser.filters import classify_file_safety, should_index_file
from app.services.parser.chunker import chunk_file, line_based_fallback_chunks


def test_extensible_language_registry_and_detection():
    # 1. Recognized filenames
    docker_adapter, docker_mode = detect_file_language("Dockerfile")
    assert docker_adapter.name == "dockerfile"
    assert docker_mode == "text_fallback"

    make_adapter, make_mode = detect_file_language("Makefile")
    assert make_adapter.name == "makefile"
    assert make_mode == "text_fallback"

    # 2. Extensions (35+ supported languages)
    test_cases = [
        ("main.rs", "rust", "parser_aware"),
        ("server.go", "go", "parser_aware"),
        ("App.java", "java", "parser_aware"),
        ("Program.cs", "csharp", "parser_aware"),
        ("module.py", "python", "parser_aware"),
        ("index.ts", "typescript", "parser_aware"),
        ("app.js", "javascript", "parser_aware"),
        ("token.sol", "solidity", "text_fallback"),
        ("view.vue", "vue", "text_fallback"),
        ("comp.svelte", "svelte", "text_fallback"),
        ("run.sh", "bash", "text_fallback"),
        ("script.ps1", "powershell", "text_fallback"),
        ("query.sql", "sql", "text_fallback"),
        ("config.yaml", "yaml", "text_fallback"),
        ("Cargo.toml", "toml", "text_fallback"),
        ("data.json", "json", "text_fallback"),
        ("README.md", "markdown", "text_fallback"),
    ]
    for filename, expected_lang, expected_mode in test_cases:
        adapter, mode = detect_file_language(filename)
        assert adapter.name == expected_lang, f"Failed for {filename}: expected {expected_lang}, got {adapter.name}"
        assert mode == expected_mode, f"Mode mismatch for {filename}"

    # 3. Shebang detection
    bash_code = "#!/bin/bash\necho 'hello'"
    ad, mode = detect_file_language("scripts/deploy", bash_code)
    assert ad.name == "bash"

    python_code = "#!/usr/bin/env python\nprint('hello')"
    ad, mode = detect_file_language("bin/tool", python_code)
    assert ad.name == "python"

    # 4. Unknown readable source does NOT disappear; uses generic fallback
    unknown_adapter, unknown_mode = detect_file_language("custom/algo.unknownlang", "BEGIN\nPROCESS\nEND")
    assert unknown_adapter.name == "generic_code"
    assert unknown_mode == "text_fallback"


def test_file_safety_classification_and_zero_leakage():
    # Sensitive secrets
    allowed, reason, category, is_secret, is_binary = classify_file_safety(".env", 50)
    assert not allowed
    assert is_secret is True
    assert "sensitive" in reason.lower()

    allowed, reason, category, is_secret, is_binary = classify_file_safety("keys/id_rsa", 1024)
    assert not allowed
    assert is_secret is True

    # Binaries
    allowed, reason, category, is_secret, is_binary = classify_file_safety("assets/logo.png", 5000)
    assert not allowed
    assert is_binary is True

    # Excluded directories (node_modules, .git)
    allowed, reason, category, is_secret, is_binary = classify_file_safety("node_modules/vue/index.js", 200)
    assert not allowed
    assert category == "vendor"


def test_chunking_preserves_exact_lines_and_path():
    rust_code = """pub struct Engine {
    workers: usize,
}

impl Engine {
    pub fn start(&self) {
        println!("Started");
    }
}
"""
    chunks, _ = chunk_file(rust_code, "src/engine.rs")
    assert len(chunks) >= 1
    for c in chunks:
        assert c.file_path == "src/engine.rs"
        assert c.start_line >= 1
        assert c.end_line >= c.start_line
        assert c.language == "rust"

    # Unknown fallback preserves line numbers
    fallback_code = "\n".join([f"Instruction {i}" for i in range(1, 100)])
    chunks, _ = chunk_file(fallback_code, "custom/algo.unknown")
    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert chunks[0].file_path == "custom/algo.unknown"
    assert chunks[0].analysis_mode == "text_fallback"


@pytest.mark.asyncio
async def test_file_tree_api_contains_all_paths_and_coverage():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Connect polyglot demo repo
        res = await ac.post("/api/v1/repositories", json={
            "full_name": "reposage-demo/polyglot-platform",
            "is_demo": True
        })
        if res.status_code == 409:
            list_res = await ac.get("/api/v1/repositories")
            repos = list_res.json()
            repo_id = [r["id"] for r in repos if r["full_name"] == "reposage-demo/polyglot-platform"][0]
        else:
            assert res.status_code == 201
            repo_id = res.json()["id"]

        # Trigger indexing
        await ac.post(f"/api/v1/indexing/{repo_id}/index")

        # Query full file tree
        tree_res = await ac.get(f"/api/v1/repositories/{repo_id}/tree")
        assert tree_res.status_code == 200
        data = tree_res.json()

        assert data["repository_id"] == repo_id
        assert data["full_name"] == "reposage-demo/polyglot-platform"

        # Check coverage totals
        cov = data["coverage"]
        assert cov["total_files"] >= 15
        assert cov["parser_aware"] >= 3  # Rust, Go, Java, C#
        assert cov["fallback"] >= 4      # Bash, SQL, YAML, TOML, Markdown, Unknown
        assert cov["excluded"] >= 3      # .env, keys/id_rsa, assets/diagram.png, node_modules

        file_paths = [f["file_path"] for f in data["files"]]
        # Ensure excluded files are present in the tree
        assert ".env" in file_paths
        assert "keys/id_rsa" in file_paths
        assert "assets/diagram.png" in file_paths
        # Ensure unknown language readable source is present in the tree
        assert "custom/parser.customlang" in file_paths


@pytest.mark.asyncio
async def test_file_content_safety_and_preview_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_res = await ac.get("/api/v1/repositories")
        repos = list_res.json()
        poly_repo = [r for r in repos if r["full_name"] == "reposage-demo/polyglot-platform"][0]
        repo_id = poly_repo["id"]

        # 1. Allowed source file returns full syntax-highlightable content
        source_res = await ac.get(f"/api/v1/repositories/{repo_id}/files/content?path=src/main.rs")
        assert source_res.status_code == 200
        source_data = source_res.json()
        assert source_data["allowed"] is True
        assert "pub struct TaskEngine" in source_data["content"]
        assert source_data["language"] == "rust"
        assert source_data["analysis_mode"] == "parser_aware"
        assert source_data["lines_count"] > 0

        # 2. Secret file (.env) returns allowed=False and ZERO content
        secret_res = await ac.get(f"/api/v1/repositories/{repo_id}/files/content?path=.env")
        assert secret_res.status_code == 200
        secret_data = secret_res.json()
        assert secret_data["allowed"] is False
        assert secret_data["content"] is None
        assert secret_data["is_secret"] is True
        assert "sensitive" in secret_data["exclusion_reason"].lower()

        # 3. Private key (keys/id_rsa) returns allowed=False and ZERO content
        key_res = await ac.get(f"/api/v1/repositories/{repo_id}/files/content?path=keys/id_rsa")
        assert key_res.status_code == 200
        key_data = key_res.json()
        assert key_data["allowed"] is False
        assert key_data["content"] is None
        assert key_data["is_secret"] is True

        # 4. Binary file (assets/diagram.png) returns allowed=False and ZERO content
        bin_res = await ac.get(f"/api/v1/repositories/{repo_id}/files/content?path=assets/diagram.png")
        assert bin_res.status_code == 200
        bin_data = bin_res.json()
        assert bin_data["allowed"] is False
        assert bin_data["content"] is None
        assert bin_data["is_binary"] is True


@pytest.mark.asyncio
async def test_file_tree_search_and_language_filtering():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_res = await ac.get("/api/v1/repositories")
        repos = list_res.json()
        poly_repo = [r for r in repos if r["full_name"] == "reposage-demo/polyglot-platform"][0]
        repo_id = poly_repo["id"]

        # Search by keyword
        search_res = await ac.get(f"/api/v1/repositories/{repo_id}/tree?search=server.go")
        assert search_res.status_code == 200
        s_data = search_res.json()
        assert len(s_data["files"]) == 1
        assert s_data["files"][0]["file_path"] == "src/server.go"

        # Filter by language
        lang_res = await ac.get(f"/api/v1/repositories/{repo_id}/tree?language=rust")
        assert lang_res.status_code == 200
        l_data = lang_res.json()
        assert all(f["language"] == "rust" for f in l_data["files"])

        # Filter by status (excluded)
        ex_res = await ac.get(f"/api/v1/repositories/{repo_id}/tree?status=excluded")
        assert ex_res.status_code == 200
        e_data = ex_res.json()
        assert all(f["status"] == "excluded" for f in e_data["files"])
