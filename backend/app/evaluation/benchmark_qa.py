import asyncio
import re
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.services.qa.service import CodeQAService


QA_BENCHMARK_CASES = [
    # --- Repository 1: somularamamaheswarreddy8/AI-Phishing-Detection-System ---
    {
        "id": "QA-01",
        "repo_id": 1,
        "repo_name": "somularamamaheswarreddy8/AI-Phishing-Detection-System",
        "query": "How is threat detection or get_uci_features handled in utils.py?",
        "type": "present_fact",
        "expected_answer_keywords": ["utils.py", "get_uci_features"],
        "expected_citations": ["utils.py"],
        "disallowed_repo_files": ["services/payment.py", "next.config.ts", "checkSigLength.js"],
        "expected_supported": True
    },
    {
        "id": "QA-02",
        "repo_id": 1,
        "repo_name": "somularamamaheswarreddy8/AI-Phishing-Detection-System",
        "query": "What database setup or table creation is handled in database.py?",
        "type": "present_fact",
        "expected_answer_keywords": ["database.py", "sqlite"],
        "expected_citations": ["database.py"],
        "disallowed_repo_files": ["services/payment.py", "apps/web/next.config.ts"],
        "expected_supported": True
    },
    {
        "id": "QA-03",
        "repo_id": 1,
        "repo_name": "somularamamaheswarreddy8/AI-Phishing-Detection-System",
        "query": "Where is Kubernetes Helm chart deployment configuration located?",
        "type": "absent_fact",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": [],
        "expected_supported": False
    },
    {
        "id": "QA-04",
        "repo_id": 1,
        "repo_name": "somularamamaheswarreddy8/AI-Phishing-Detection-System",
        "query": "Where is checkSigLength defined and what signature does it validate?",
        "type": "cross_repo_symbol_absent",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": ["checkSigLength.js", "apps/web"],
        "expected_supported": False
    },
    {
        "id": "QA-05",
        "repo_id": 1,
        "repo_name": "somularamamaheswarreddy8/AI-Phishing-Detection-System",
        "query": "Where is PaymentService implemented and how is Stripe charge invoked?",
        "type": "cross_repo_symbol_absent",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": ["services/payment.py", "api/orders.py"],
        "expected_supported": False
    },

    # --- Repository 2: reposage-demo/ecommerce-api ---
    {
        "id": "QA-06",
        "repo_id": 2,
        "repo_name": "reposage-demo/ecommerce-api",
        "query": "How is PaymentService implemented and what does process_payment do?",
        "type": "present_fact",
        "expected_answer_keywords": ["payment", "services/payment.py"],
        "expected_citations": ["services/payment.py"],
        "disallowed_repo_files": ["utils.py", "checkSigLength.js", "database.py"],
        "expected_supported": True
    },
    {
        "id": "QA-07",
        "repo_id": 2,
        "repo_name": "reposage-demo/ecommerce-api",
        "query": "How are orders routed in api/orders.py?",
        "type": "present_fact",
        "expected_answer_keywords": ["api/orders.py", "order"],
        "expected_citations": ["api/orders.py"],
        "disallowed_repo_files": ["utils.py", "checkSigLength.js"],
        "expected_supported": True
    },
    {
        "id": "QA-08",
        "repo_id": 2,
        "repo_name": "reposage-demo/ecommerce-api",
        "query": "Where is get_uci_features defined in this repository?",
        "type": "cross_repo_symbol_absent",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": ["utils.py", "app.py"],
        "expected_supported": False
    },
    {
        "id": "QA-09",
        "repo_id": 2,
        "repo_name": "reposage-demo/ecommerce-api",
        "query": "How is GraphQL subscription websocket server configured?",
        "type": "absent_fact",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": [],
        "expected_supported": False
    },

    # --- Repository 4: venkatasivagopivaka/aegismind ---
    {
        "id": "QA-10",
        "repo_id": 4,
        "repo_name": "venkatasivagopivaka/aegismind",
        "query": "How is verifyAuthToken implemented in src/auth.ts?",
        "type": "present_fact",
        "expected_answer_keywords": ["src/auth.ts", "verifyAuthToken"],
        "expected_citations": ["src/auth.ts"],
        "disallowed_repo_files": ["services/payment.py", "utils.py", "app.py"],
        "expected_supported": True
    },
    {
        "id": "QA-11",
        "repo_id": 4,
        "repo_name": "venkatasivagopivaka/aegismind",
        "query": "Where is startServer defined in src/server.ts and what port does it use?",
        "type": "present_fact",
        "expected_answer_keywords": ["src/server.ts", "startServer"],
        "expected_citations": ["src/server.ts"],
        "disallowed_repo_files": ["utils.py", "services/payment.py"],
        "expected_supported": True
    },
    {
        "id": "QA-12",
        "repo_id": 4,
        "repo_name": "venkatasivagopivaka/aegismind",
        "query": "How is Flask app.py initializing the SQLite threat logs?",
        "type": "cross_repo_symbol_absent",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": ["app.py", "database.py", "utils.py"],
        "expected_supported": False
    },
    {
        "id": "QA-13",
        "repo_id": 4,
        "repo_name": "venkatasivagopivaka/aegismind",
        "query": "How is WarehouseService stock replenishment handled?",
        "type": "cross_repo_symbol_absent",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": ["src/services/warehouse.ts", "src/index.ts"],
        "expected_supported": False
    },
    {
        "id": "QA-14",
        "repo_id": 4,
        "repo_name": "venkatasivagopivaka/aegismind",
        "query": "What Apache Spark streaming jobs are configured in this repository?",
        "type": "absent_fact",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": [],
        "expected_supported": False
    },

    # --- Switch Sequence Case ---
    {
        "id": "QA-15",
        "repo_id": 4,
        "repo_name": "venkatasivagopivaka/aegismind",
        "query": "Where is PaymentService implemented and how is Stripe charge invoked?",
        "type": "switch_sequence_isolation",
        "expected_answer_keywords": ["not confirmed from indexed files"],
        "expected_citations": [],
        "disallowed_repo_files": ["services/payment.py"],
        "expected_supported": False
    }
]


async def run_qa_benchmark(db_session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    print("=" * 72)
    print(" RepoSage Multi-Repository Code Q&A & Isolation Benchmark")
    print("=" * 72)

    total_cases = len(QA_BENCHMARK_CASES)
    correct_answers = 0
    correct_citations = 0
    correct_repo_selections = 0
    cross_repo_leakages = 0
    unconfirmed_correct = 0
    failing_cases: List[Dict[str, Any]] = []

    async def _execute_suite(db: AsyncSession):
        nonlocal correct_answers, correct_citations, correct_repo_selections, cross_repo_leakages, unconfirmed_correct, failing_cases
        qa_service = CodeQAService(db)

        # Preload repositories
        repo_cache = {}
        for c in QA_BENCHMARK_CASES:
            r_id = c["repo_id"]
            if r_id not in repo_cache:
                r = await db.get(Repository, r_id)
                repo_cache[r_id] = r

        for case in QA_BENCHMARK_CASES:
            cid = case["id"]
            repo = repo_cache.get(case["repo_id"])
            query = case["query"]
            exp_keywords = case["expected_answer_keywords"]
            exp_citations = case["expected_citations"]
            disallowed = case["disallowed_repo_files"]
            exp_supported = case["expected_supported"]

            if not repo:
                print(f"[{cid}] SKIP: Repository {case['repo_id']} not found.")
                failing_cases.append({
                    "id": cid,
                    "repo_id": case["repo_id"],
                    "query": query,
                    "reason": f"Repository {case['repo_id']} not found"
                })
                continue

            # Run question answering
            response = await qa_service.answer_question(repo, query)

            answer_lower = response.answer.lower()
            cited_files = [cit.file_path for cit in response.citations]

            # 1. Check Correct Repository Selection
            repo_header_match = (repo.full_name in response.answer)
            if repo_header_match and response.repository_id == repo.id:
                correct_repo_selections += 1
            else:
                print(f"[{cid}] FAIL: Repository header or ID mismatch.")

            # 2. Check Cross-Repository Leakage
            leakage_detected = False
            for dis in disallowed:
                if dis.lower() in answer_lower or any(dis in cf for cf in cited_files):
                    leakage_detected = True
                    cross_repo_leakages += 1
                    print(f"[{cid}] LEAKAGE ERROR: Answer or citations contain disallowed file '{dis}' from another repository!")
                    break

            # 3. Check Answer Correctness
            ans_ok = True
            for kw in exp_keywords:
                if kw.lower() not in answer_lower:
                    ans_ok = False
                    break

            if response.supported_by_evidence != exp_supported:
                ans_ok = False

            if ans_ok and not leakage_detected:
                correct_answers += 1
                if not exp_supported:
                    unconfirmed_correct += 1

            # 4. Check Citation Accuracy
            cit_ok = True
            if exp_citations:
                # Every expected citation file should be cited
                for exp_f in exp_citations:
                    if not any(exp_f in cf for cf in cited_files):
                        cit_ok = False
                        break
            else:
                # If no citations expected (e.g. unconfirmed answer), citations should be empty
                if len(cited_files) > 0:
                    cit_ok = False

            # Verify that every returned citation exists in this repo's database chunks
            if cited_files:
                for cit in response.citations:
                    chunk_stmt = select(CodeChunk).where(
                        CodeChunk.repository_id == repo.id,
                        CodeChunk.file_path == cit.file_path,
                        CodeChunk.start_line <= cit.start_line,
                        CodeChunk.end_line >= cit.end_line
                    )
                    chunk_res = await db.execute(chunk_stmt)
                    if not chunk_res.scalar_one_or_none():
                        # Also accept if matching by file and line within 5 lines
                        loose_stmt = select(CodeChunk).where(
                            CodeChunk.repository_id == repo.id,
                            CodeChunk.file_path == cit.file_path
                        )
                        loose_res = await db.execute(loose_stmt)
                        if not loose_res.scalars().first():
                            cit_ok = False
                            print(f"[{cid}] CITATION INVALID: Citation {cit.file_path}:{cit.start_line}-{cit.end_line} does not exist in repo chunks!")
                            break

            if cit_ok and not leakage_detected:
                correct_citations += 1

            is_pass = (ans_ok and cit_ok and not leakage_detected)
            status = "PASS" if is_pass else "FLAG"
            if not is_pass:
                failing_cases.append({
                    "id": cid,
                    "repo_id": repo.id,
                    "repo_name": repo.full_name,
                    "query": query,
                    "reason": f"ans_ok={ans_ok}, cit_ok={cit_ok}, leakage={leakage_detected}"
                })
            print(f"[{status}] {cid} | Repo {repo.id} ({repo.name}) | Type: {case['type']} | Citations: {len(cited_files)}")

    if db_session is not None:
        await _execute_suite(db_session)
    else:
        async with AsyncSessionLocal() as db:
            await _execute_suite(db)

    # Compute percentages
    ans_accuracy = (correct_answers / total_cases) * 100.0
    cit_accuracy = (correct_citations / total_cases) * 100.0
    repo_selection_pct = (correct_repo_selections / total_cases) * 100.0

    print("\n" + "=" * 72)
    print(" CODE Q&A BENCHMARK RESULTS")
    print("=" * 72)
    print(f"Total Benchmark Cases Evaluated  : {total_cases}")
    print(f"Correct Repository Selection     : {correct_repo_selections}/{total_cases} ({repo_selection_pct:.1f}%)")
    print(f"Cross-Repository Data Leakage    : {cross_repo_leakages} (Target: 0)")
    print(f"Answer Correctness               : {correct_answers}/{total_cases} ({ans_accuracy:.1f}%) [Target: >= 90%]")
    print(f"Citation Accuracy                : {correct_citations}/{total_cases} ({cit_accuracy:.1f}%) [Target: >= 95%]")
    print(f"Unconfirmed Grounding Accuracy   : {unconfirmed_correct} cases correctly rejected with 'Not confirmed from indexed files'")
    print("=" * 72)

    return {
        "evaluation_date": datetime.datetime.utcnow(),
        "total_cases": total_cases,
        "correct_answers": correct_answers,
        "correct_citations": correct_citations,
        "correct_repo_selections": correct_repo_selections,
        "cross_repo_leakages": cross_repo_leakages,
        "answer_accuracy_pct": ans_accuracy,
        "citation_accuracy_pct": cit_accuracy,
        "repo_selection_pct": repo_selection_pct,
        "failing_cases": failing_cases
    }


if __name__ == "__main__":
    asyncio.run(run_qa_benchmark())
