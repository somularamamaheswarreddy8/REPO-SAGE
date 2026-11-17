import json
import hashlib
import math
import re
from typing import List, Dict, Any, Optional
from app.services.ai.base import BaseLLMProvider, BaseEmbeddingProvider
from app.core.config import settings


class MockLLMProvider(BaseLLMProvider):
    """
    Mock AI Provider for Demo Mode.
    Produces evidence-grounded code intelligence and structured PR reviews
    derived dynamically from the retrieved repository chunks.
    """

    @property
    def provider_name(self) -> str:
        return "mock:evidence-v1"

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.2
    ) -> str:
        # 1. Parse Developer Question
        q_match = re.search(r"Developer Question:\s*(.*?)(?:\n\nPlease|$)", prompt, re.DOTALL)
        question = q_match.group(1).strip() if q_match else ""

        # 2. Parse Retrieved Code Blocks
        blocks = re.findall(
            r"--- BEGIN UNTRUSTED REPOSITORY CODE \[file:\s*([^,\]]+),\s*lines:\s*([^\]]+)\] ---\n(.*?)\n--- END UNTRUSTED REPOSITORY CODE",
            prompt,
            re.DOTALL
        )

        if not blocks:
            return "The retrieved codebase evidence does not contain sufficient information to answer this question. Not confirmed from indexed files."

        # 3. Extract meaningful question keywords
        stop_words = {
            "what", "where", "how", "when", "why", "who", "whom", "which", "whose",
            "does", "did", "do", "done", "the", "and", "or", "for", "with", "from",
            "this", "that", "these", "those", "show", "explain", "tell", "are", "is",
            "was", "were", "be", "been", "being", "have", "has", "had", "any", "all",
            "can", "could", "would", "should", "code", "file", "files", "function",
            "class", "method", "module", "please", "about", "in", "on", "at", "by",
            "to", "of", "an", "a", "as", "it", "its", "if", "so", "than", "then",
            "there", "here", "their", "them", "they", "we", "us", "our", "you", "your",
            "my", "me", "into", "also", "just", "like", "up", "out", "no", "not",
            "defined", "define", "handled", "handling", "handle", "executes", "execute",
            "configured", "configure", "located", "location", "invoked", "invoke", "call",
            "repository"
        }
        q_tokens = [
            t.lower()
            for t in re.findall(r"[a-zA-Z0-9_\-\.]+", question)
            if len(t) >= 2 and t.lower() not in stop_words
        ]

        if not q_tokens:
            return (
                f"The retrieved codebase evidence does not contain sufficient information to answer '{question}'. "
                "Not confirmed from indexed files."
            )

        # 4. Strict File & Symbol Matching
        # Check if question explicitly targets specific files
        files_in_q = [
            t for t in q_tokens
            if re.search(r"\.(?:py|js|ts|tsx|jsx|json|md|html|css|yml|yaml)$", t)
        ]

        candidate_blocks = blocks
        if files_in_q:
            matching_file_blocks = [
                b for b in blocks
                if any(fq in b[0].lower() for fq in files_in_q)
            ]
            if not matching_file_blocks:
                return (
                    "The retrieved codebase evidence does not contain sufficient information to answer this question. "
                    "Not confirmed from indexed files."
                )
            candidate_blocks = matching_file_blocks

        # Identify core specific identifiers in question (proper nouns, camelCase, PascalCase, snake_case, domain terms)
        raw_words = re.findall(r"[a-zA-Z0-9_\-\.]+", question)
        primary_identifiers = []
        for idx, w in enumerate(raw_words):
            w_lower = w.lower()
            # Proper noun (capitalized not at sentence start)
            is_proper = (idx > 0 and w[0].isupper())
            is_special = any(c.isupper() for c in w[1:]) or "_" in w or "." in w or len(w) >= 7
            if is_proper or is_special:
                primary_identifiers.append(w_lower)

        generic_terms = {
            "deployment", "validate", "validating", "signature", "configured",
            "configuring", "handling", "handled", "implemented", "implementing",
            "creation", "creating", "initialization", "initializing", "repository",
            "question", "answers", "answer", "configuration", "configurations",
            "config", "settings", "setup"
        }
        core_identifiers = [t for t in primary_identifiers if t not in generic_terms and t not in stop_words]

        # Match tokens against candidate blocks
        matching = []
        for fpath, lrange, code in candidate_blocks:
            code_lower = code.lower()
            fpath_lower = fpath.lower()
            matched = [t for t in q_tokens if t in code_lower or t in fpath_lower]

            # If core specific identifiers exist in question, at least one MUST be present in the chunk
            if core_identifiers:
                has_core = any(ci in code_lower or ci in fpath_lower for ci in core_identifiers)
                if not has_core:
                    continue

            # Check for strong match on a specific core identifier (class, function, or domain symbol)
            has_strong_core = any(
                ci in code_lower or ci in fpath_lower
                for ci in core_identifiers
                if len(ci) >= 8 or any(c.isupper() for c in ci[1:]) or "_" in ci
            )

            # Require matching strong core identifier, at least 50% of question tokens, or multiple matched tokens
            match_ratio = len(matched) / len(q_tokens) if q_tokens else 0
            if has_strong_core or match_ratio >= 0.5 or len(matched) >= 2 or (len(q_tokens) == 1 and len(matched) == 1):
                matching.append((fpath, lrange, code, matched))

        if not matching:
            return (
                "The retrieved codebase evidence does not contain sufficient information to answer this question. "
                "Not confirmed from indexed files."
            )

        # 5. Build dynamic evidence-grounded answer citing the actual files and lines
        selected_blocks = matching[:3]
        findings = []
        citations = []

        for fpath, lrange, code, *rest in selected_blocks:
            first_line = lrange.split("-")[0] if "-" in lrange else lrange.replace("+", "")
            
            # Identify declared functions, classes, or symbols
            defs = re.findall(r"(?:def|class|type|pub struct|public class|func|fn)\s+([a-zA-Z0-9_]+)", code)
            if defs:
                symbol_desc = f"defines symbol `{defs[0]}`"
            else:
                first_stmt = [
                    l.strip() for l in code.split("\n")
                    if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))
                ]
                symbol_desc = f"implements `{first_stmt[0][:50]}`" if first_stmt else "contains core logic"

            findings.append(f"- In `[{fpath}:L{lrange}](file:///{fpath}#{first_line})`, the codebase {symbol_desc}.")
            citations.append(f"`{fpath}:L{lrange}`")

        answer = (
            "Based on the indexed repository source code:\n"
            + "\n".join(findings)
            + "\n\nReference evidence: "
            + ", ".join(citations)
        )
        return answer

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        findings: List[Dict[str, Any]] = []

        # Extract files that actually appear in the reviewed diff
        diff_files = re.findall(r"(?:---|\+\+\+)\s+[ab]/(.+?)(?:\s|$)", prompt)
        if not diff_files:
            file_match = re.search(r"File:\s*([^\s\n]+)", prompt)
            if file_match:
                diff_files = [file_match.group(1)]
        
        # Deduplicate and clean file paths
        seen_files = set()
        clean_diff_files = []
        for df in diff_files:
            clean_f = df.strip().replace("/dev/null", "").strip()
            if clean_f and clean_f not in seen_files:
                seen_files.add(clean_f)
                clean_diff_files.append(clean_f)

        target_file = clean_diff_files[0] if clean_diff_files else "code_diff"

        # Extract hunk line numbers if available (e.g. @@ -1,5 +10,12 @@)
        hunk_match = re.search(r"@@\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s*@@", prompt)
        start_line = int(hunk_match.group(1)) if hunk_match else 1
        line_count = int(hunk_match.group(2)) if hunk_match and hunk_match.group(2) else 10
        end_line = start_line + line_count

        # Context-aware finding generation strictly scoped to files in the diff
        if "select" in prompt_lower and ("where" in prompt_lower or "user_id" in prompt_lower) and ("f\"" in prompt_lower or "f'" in prompt_lower or "%" in prompt_lower):
            findings.append({
                "severity": "high",
                "title": "Missing SQL Parameterization / Injection Risk",
                "explanation": f"Query construction in {target_file} uses direct string interpolation instead of parameterized placeholders, risking SQL injection vulnerabilities.",
                "file_path": target_file,
                "start_line": start_line,
                "end_line": end_line,
                "why_problem": "Raw user input is interpolated directly into the SQL statement, allowing attackers to execute arbitrary database queries.",
                "suggested_improvement": "Use parameterized bind variables: `query = select(Model).where(Model.user_id == user_id)`.",
                "suggested_tests": "Add unit test with malicious SQL payload `'; DROP TABLE users; --` to ensure statement fails safely or is escaped.",
                "confidence": 0.95,
                "is_confirmed_problem": True
            })

        if ("httpx" in prompt_lower or "requests" in prompt_lower or "fetch(" in prompt_lower) and ("timeout=" not in prompt_lower and "timeout =" not in prompt_lower and "timeout:" not in prompt_lower):
            findings.append({
                "severity": "medium",
                "title": "Missing Timeout on External Network Call",
                "explanation": f"External HTTP request in {target_file} lacks an explicit timeout parameter, risking hung connections and worker starvation.",
                "file_path": target_file,
                "start_line": start_line,
                "end_line": end_line,
                "why_problem": "If the remote service experiences high latency or drops the socket, threads will block indefinitely.",
                "suggested_improvement": "Supply explicit timeout parameter: `timeout=10.0`.",
                "suggested_tests": "Unit test simulating HTTP timeout verifying fallback.",
                "confidence": 0.92,
                "is_confirmed_problem": True
            })

        if "hardcoded" in prompt_lower or "secret-12345" in prompt_lower or "super-secret" in prompt_lower or "jwt_secret = \"" in prompt_lower:
            findings.append({
                "severity": "critical",
                "title": "Hardcoded Cryptographic Secret",
                "explanation": f"Cryptographic key or secret is hardcoded directly in application source code in {target_file}.",
                "file_path": target_file,
                "start_line": start_line,
                "end_line": end_line,
                "why_problem": "Hardcoded secrets are exposed to everyone with read access to the repository and cannot be rotated without code deployment.",
                "suggested_improvement": "Load secret securely from environment variable: `os.environ.get('SECRET_KEY')`.",
                "suggested_tests": "Verify error is raised if environment variable is missing.",
                "confidence": 0.98,
                "is_confirmed_problem": True
            })

        if findings:
            summary_msg = f"Identified {len(findings)} finding(s) in {target_file}."
        else:
            summary_msg = "Review completed: no high or critical security findings identified in the provided diff."

        return {
            "summary": summary_msg,
            "findings": findings
        }


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-random vector generator for Demo Mode.
    Produces 1536-dimensional unit vectors where semantically similar texts
    share higher cosine similarity.
    """

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    def _text_to_vector(self, text: str) -> List[float]:
        dim = self.dimension
        vec = [0.0] * dim
        tokens = text.lower().split()
        if not tokens:
            tokens = ["empty"]

        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx1 = h % dim
            idx2 = (h >> 16) % dim
            idx3 = (h >> 32) % dim
            sign1 = 1.0 if (h & 1) else -1.0
            sign2 = 1.0 if (h & 2) else -1.0
            sign3 = 1.0 if (h & 4) else -1.0
            vec[idx1] += sign1
            vec[idx2] += sign2 * 0.7
            vec[idx3] += sign3 * 0.5

        # Normalize vector to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vector(t) for t in texts]

    async def get_embedding(self, text: str) -> List[float]:
        return self._text_to_vector(text)
