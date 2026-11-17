# RepoSage: Secure AI Code Review & Repository Intelligence

**RepoSage** is an enterprise-grade, evidence-grounded AI Code Review and Repository Intelligence platform. It connects to GitHub repositories, indexes source code asynchronously across 35+ programming languages, answers developer questions grounded in code evidence, and delivers structured, evidence-backed pull request reviews, change impact analysis, and test-gap advisory.

---

## Core Principles & Safety Guarantees

1. **Developer Always in Control**: RepoSage will **never** alter source code or publish review comments to GitHub without an explicit user approval action.
2. **Explicit Human Confirmation**: Before publishing review comments, developers are presented with a detailed confirmation modal displaying the exact target file, line range, and comment text to be posted.
3. **Cryptographically Chained Audit Trail**: All user-approved write operations (posting review comments, toggling security settings, or applying code patches) are logged to an append-only, tamper-evident SHA-256 cryptographic hash chain verifiable at any time.
4. **Advisory CI Checks Are Opt-In**: The optional pull request CI summary check is **disabled by default**. A repository owner must explicitly enable it in Settings. Even when enabled, it produces advisory check summaries and **does not block merges by default**.
5. **Prompt Injection & Untrusted Code Defense**: All repository code, comments, README files, and PR descriptions are treated as untrusted input. Prompts wrap source files within strict isolation boundaries (`--- BEGIN UNTRUSTED REPOSITORY CODE ---`), with instructions forbidding the model from executing commands found within files.
6. **Deep Content Secret Scanning & Zero-Leakage**: RepoSage scans both filenames and file contents using pattern analysis and Shannon entropy. Secrets, keys, and credentials are never previewed, embedded, logged, or sent to AI models.
7. **Repository Access Authorization & Tenant Isolation**: Secure user authentication connects GitHub users, verifying that each user is authorized to access the specific repository. Repository boundaries are enforced in the backend on all requests.
8. **Static Analysis & Untrusted Code Execution Policy**: RepoSage **never executes repository code, scripts, package installers, or build steps** to determine architecture, relationships, impact, or test gaps. All insights are derived through static parsing and AST analysis.
9. **Zero-Credential Demo Mode**: RepoSage can run out-of-the-box without GitHub App credentials or external LLM API keys. Pre-seeded demo repositories (`reposage-demo/ecommerce-api`, `reposage-demo/polyglot-platform`), sample PR diffs, and mock providers allow immediate end-to-end evaluation.

---

## Features & Capabilities

### 1. Repository Onboarding Guide ("Start here" view)
- **Likely Entry Points**: Identifies application entry points (`main.py`, `server.go`, `index.ts`, `Dockerfile`, etc.) with clickable file and line citations.
- **Core Modules & Responsibilities**: Groups source code into logical modules, deriving responsibilities from code docstrings and top-level symbols.
- **Static Module Connections**: Traces how modules connect via imports and function calls using static relationship graphs.
- **Existing Module Tests**: Maps test suites to modules. Any relationship or test that cannot be verified statically is explicitly labeled `"Not confirmed from indexed files."`

### 2. Pull-Request Change Impact Analysis
- **Changed Files & Symbols**: Highlights modified files and exact functions/classes affected by the PR.
- **Downstream Callers**: Statically traces modules and components that import or call the modified symbols.
- **Potentially Affected Tests**: Identifies existing tests that exercise the changed symbols.
- **Uncertainty Demarcation**: Marks dynamic runtime behaviors (reflection, `eval`, `getattr`, event emitters) as `"Uncertain: dynamic/runtime relationship not confirmed from indexed files."`

### 3. Test-Gap Advisor
- **Coverage Gap Detection**: Statically checks whether changed functions and symbols are exercised by existing test suites.
- **Nuanced Diagnostics**: Clearly distinguishes between `"No related test found"` and `"This behavior appears to lack dedicated test coverage"`.
- **Recommended Test Cases**: Suggests concrete test case implementations with explanations of why each test matters for boundary validation and regression defense.
- **No False Coverage Claims**: Does not claim line coverage percentages without configured coverage data tools.

### 4. Commit & Branch Comparison
- **File Diffs**: Displays added, modified, deleted, and renamed files with exact line numbers and citations.
- **Architecture Shift Summary**: Computes changes in modules, services, and cross-module dependencies between base and head.
- **Review Findings Evolution**: Identifies newly introduced vs. resolved review findings between commits.
- **Staleness Tracking**: Clearly flags when a commit is not indexed or analysis is stale.

### 5. Dependency Inventory
- **Multi-Ecosystem Manifest & Lockfile Parsing**: Supports `package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `Cargo.lock`, `go.mod`, and `pom.xml`.
- **Classification**: Distinguishes direct vs. transitive dependencies strictly when manifest data confirms it.
- **Trusted Source Attribution**: Displays parsing verification source and check date, without asserting false vulnerability claims when external vulnerability feeds are unconfigured.

### 6. Repository Feedback Controls
- **Dual Target Support**: Allows developers to rate both PR review findings and Code Q&A answers as "Useful" or "Incorrect" with an optional explanation.
- **Traceable Benchmarking**: Stores feedback alongside repository ID, commit SHA, and target ID for continuous evaluation without silently altering model review rules.

### 7. File Explorer & Broad Language Support
- **Full Repository Tree**: Expandable/collapsible file tree with search, filtering by language, status, and category.
- **Broad Language Support**: 35+ programming languages supported via parser-aware AST chunking and generic text fallback with exact line ranges.
- **Safe Previews**: Syntax-highlighted file preview for allowed files; secret, binary, and oversized files are shielded with clear exclusion reasons.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│  RepoSage Web App (Responsive Workspace with Left Sidebar)             │
│  ┌───────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ Left Sidebar Navigation│ │ Active Workspace Area                  │ │
│  │ - Connected User      │  │ - 🧭 Start Here (Onboarding Guide)     │ │
│  │ - Repo Switcher       │  │ - 📁 File Explorer (Tree + Preview)    │ │
│  │ - Indexing Progress   │  │ - 🛡️ Index Health & Safety             │ │
│  │ - Start Here          │  │ - 📊 Repository Overview               │ │
│  │ - File Explorer       │  │ - 🔀 PR Impact & Test Gaps             │ │
│  │ - Index Health        │  │ - ⚖️ Commit Comparison                 │ │
│  │ - PR Impact & Gaps    │  │ - 📦 Dependency Inventory              │ │
│  │ - Commit Comparison   │  │ - 💬 Evidence-Grounded Code Q&A        │ │
│  │ - Dependencies        │  │ - 🔍 PR Reviews & Audit Trails         │ │
│  │ - Code Q&A            │  │ - 🕸️ System Architecture Map           │ │
│  │ - PR Reviews          │  │ - 📜 Immutable Audit Log               │ │
│  │ - System Architecture │  │ - ⚙️ Settings & Benchmarks             │ │
│  │ - Audit Log           │  └────────────────────────────────────────┘ │
│  │ - Settings & Eval     │                                             │
│  └───────────────────────┘                                             │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTP / REST
                                     ▼
                ┌──────────────────────────────────────────┐
                │          FastAPI Backend Service         │
                │  - Onboarding Guide Builder              │
                │  - PR Impact & Test-Gap Analyzer         │
                │  - Commit & Branch Comparator            │
                │  - Dependency Inventory Scanner          │
                │  - Repository Feedback & Eval Engine     │
                │  - AST & Symbol Regex Chunker            │
                │  - Zero-Leakage Security Classifier      │
                └───────┬────────────┬─────────────┬───────┘
                        │            │             │
         ┌──────────────┘            │             └──────────────┐
         ▼                           ▼                            ▼
┌─────────────────────────┐  ┌──────────────────────────┐  ┌─────────────────────────┐
│   PostgreSQL + pgvector │  │      Redis + Celery      │  │    Modular Providers    │
│  (Portable SQLite adapt)│  │   (Async Worker Tasks)   │  │  - AI: OpenAI, Anthropic│
│  - repository_files     │  │  - Polyglot indexing     │  │        Gemini, Mock     │
│  - code_chunks          │  │  - PR Review analysis    │  │  - GitHub: App API,     │
│  - code_relationships   │  │  - Safe retries          │  │           Mock Provider │
│  - repository_feedback  │  └──────────────────────────┘  └─────────────────────────┘
└─────────────────────────┘
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- SQLite (default portable fallback) or PostgreSQL with pgvector

### Running Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Running Frontend
```bash
cd frontend
npm install
npm run dev
```

### Running Test Suite
```bash
cd backend
pytest tests/ -v
```
All 45 test cases pass with 100% verification coverage.
