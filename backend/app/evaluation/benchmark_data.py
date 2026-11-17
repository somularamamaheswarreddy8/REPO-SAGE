"""
Synthetic Benchmark Dataset for RepoSage Evaluation & Regression Testing.
Version: 1.0.0
Author: RepoSage Quality Engineering
Contains curated, safe, synthetic code review scenarios with ground truth findings.
"""

BENCHMARK_VERSION = "1.0.0"

SYNTHETIC_BENCHMARK_CASES = [
    {
        "case_id": "SYNTH-001",
        "title": "SQL Injection in User Query Handler",
        "description": "Direct string interpolation into SQL query statement instead of parameterization",
        "file_path": "services/payment.py",
        "diff": """diff --git a/services/payment.py b/services/payment.py
--- a/services/payment.py
+++ b/services/payment.py
@@ -42,5 +42,7 @@ class PaymentService:
     def execute_raw_user_query(self, user_id: str, db_session: Any) -> Any:
-        query = select(Payment).where(Payment.user_id == user_id)
+        # Unsafe string concatenation
+        query = f"SELECT id, amount FROM payments WHERE user_id = '{user_id}'"
         return db_session.execute(query)
""",
        "expected_findings": [
            {
                "file_path": "services/payment.py",
                "severity": "high",
                "keywords": ["sql", "injection", "parameter"],
                "target_line": 44
            }
        ]
    },
    {
        "case_id": "SYNTH-002",
        "title": "Missing Timeout on External Gateway HTTP Request",
        "description": "Network request without timeout can lead to thread exhaustion and hanging connections",
        "file_path": "services/payment.py",
        "diff": """diff --git a/services/payment.py b/services/payment.py
--- a/services/payment.py
+++ b/services/payment.py
@@ -60,4 +60,7 @@ class PaymentService:
     def call_external_gateway(self, payload: dict) -> dict:
+        import httpx
+        # Missing timeout parameter
+        response = httpx.post("https://api.stripe.com/v1/charges", json=payload)
+        return response.json()
""",
        "expected_findings": [
            {
                "file_path": "services/payment.py",
                "severity": "medium",
                "keywords": ["timeout", "hang", "unhandled"],
                "target_line": 63
            }
        ]
    },
    {
        "case_id": "SYNTH-003",
        "title": "Hardcoded Cryptographic Salt/Secret",
        "description": "Embedding hardcoded secret in source code",
        "file_path": "auth/jwt.py",
        "diff": """diff --git a/auth/jwt.py b/auth/jwt.py
--- a/auth/jwt.py
+++ b/auth/jwt.py
@@ -10,3 +10,4 @@
-def get_secret(): return os.environ.get("JWT_SECRET")
+def get_secret():
+    return "super-secret-hardcoded-salt-12345"
""",
        "expected_findings": [
            {
                "file_path": "auth/jwt.py",
                "severity": "critical",
                "keywords": ["hardcoded", "secret", "credential"],
                "target_line": 12
            }
        ]
    },
    {
        "case_id": "SYNTH-004",
        "title": "Benign Clean Refactoring (Negative Control)",
        "description": "Refactoring helper with proper typing and docstring, no bugs introduced",
        "file_path": "models/user.py",
        "diff": """diff --git a/models/user.py b/models/user.py
--- a/models/user.py
+++ b/models/user.py
@@ -15,4 +15,6 @@
+    def is_valid_email(self) -> bool:
+        \"\"\"Helper check for email format.\"\"\"
+        return "@" in self.email and "." in self.email
""",
        "expected_findings": []  # Clean diff, no findings expected
    }
]

SYNTHETIC_SUMMARY_BENCHMARK_CASES = [
    {
        "case_id": "SUMM-001",
        "repo_name": "reposage-demo/task-manager-api",
        "description": "Task manager with FastAPI & SQLite and intentionally misleading Cassandra README",
        "expected_facts": [
            {"fact": "FastAPI framework", "expected_file": "requirements.txt", "keywords": ["fastapi"]},
            {"fact": "SQLite database", "expected_file": "database.py", "keywords": ["sqlite"]},
            {"fact": "Task management purpose", "expected_file": "models/task.py", "keywords": ["task", "project"]}
        ],
        "disallowed_claims": [
            {"claim": "Cassandra database", "keywords": ["cassandra"]},
            {"claim": "PyTorch ML cluster", "keywords": ["pytorch", "deep learning"]}
        ]
    },
    {
        "case_id": "SUMM-002",
        "repo_name": "reposage-demo/inventory-service",
        "description": "TypeScript Express inventory warehouse service with Redis caching",
        "expected_facts": [
            {"fact": "Express web framework", "expected_file": "package.json", "keywords": ["express"]},
            {"fact": "Redis cache datastore", "expected_file": "package.json", "keywords": ["redis", "ioredis"]},
            {"fact": "Warehouse inventory purpose", "expected_file": "src/services/warehouse.ts", "keywords": ["warehouse", "stock", "sku"]}
        ],
        "disallowed_claims": [
            {"claim": "PostgreSQL database", "keywords": ["postgres", "postgresql"]},
            {"claim": "Django framework", "keywords": ["django"]}
        ]
    },
    {
        "case_id": "SUMM-003",
        "repo_name": "reposage-demo/ecommerce-api",
        "description": "E-Commerce backend API with order processing, Stripe, and JWT",
        "expected_facts": [
            {"fact": "Stripe payment integration", "expected_file": "services/payment.py", "keywords": ["stripe", "payment"]},
            {"fact": "JWT authentication token", "expected_file": "auth/jwt.py", "keywords": ["jwt", "token"]},
            {"fact": "Order management", "expected_file": "api/orders.py", "keywords": ["order"]}
        ],
        "disallowed_claims": [
            {"claim": "GraphQL endpoint", "keywords": ["graphql"]}
        ]
    }
]
