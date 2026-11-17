import asyncio
import sys
import argparse
from typing import Dict, Any, List
from app.evaluation.benchmark_data import (
    SYNTHETIC_BENCHMARK_CASES,
    SYNTHETIC_SUMMARY_BENCHMARK_CASES,
    BENCHMARK_VERSION
)
from app.services.ai.factory import get_llm_provider
from app.services.reviewer.engine import SYSTEM_PROMPT_REVIEW
from app.services.github.mock import MOCK_REPOSITORIES
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.services.profiler.builder import RepositoryProfiler


async def run_evaluation(strict_regression: bool = False) -> Dict[str, Any]:
    print("=" * 70)
    print(f" RepoSage AI Code Review & Summary Accuracy Benchmark (v{BENCHMARK_VERSION})")
    print("=" * 70)

    llm = get_llm_provider()
    print(f"Active Evaluated Model: {llm.provider_name}\n")

    # -------------------------------------------------------------
    # 1. Evaluate PR Code Review Benchmark
    # -------------------------------------------------------------
    print("--- 1. Pull Request Review Precision / Recall Benchmark ---")
    tp = 0
    fp = 0
    fn = 0
    tn = 0

    for case in SYNTHETIC_BENCHMARK_CASES:
        case_id = case["case_id"]
        title = case["title"]
        expected_findings = case["expected_findings"]

        prompt = (
            f"Pull Request Review Task: {title}\n"
            f"File: {case['file_path']}\n\n"
            f"Unified Diff:\n{case['diff']}\n\n"
            "Review this diff and return JSON with keys 'summary' and 'findings'."
        )

        try:
            output = await llm.generate_structured(prompt, system_prompt=SYSTEM_PROMPT_REVIEW)
            model_findings = output.get("findings", [])
        except Exception as e:
            print(f"[{case_id}] Generation failed: {e}")
            model_findings = []

        # Evaluate matches
        case_matched_expected = set()

        for mf in model_findings:
            m_path = mf.get("file_path", "")
            m_title = (mf.get("title", "") + " " + mf.get("explanation", "")).lower()

            matched = False
            for idx, exp in enumerate(expected_findings):
                if exp["file_path"] in m_path or m_path in exp["file_path"]:
                    if any(k.lower() in m_title for k in exp["keywords"]):
                        matched = True
                        case_matched_expected.add(idx)
                        break

            if matched:
                tp += 1
            else:
                fp += 1

        missed = len(expected_findings) - len(case_matched_expected)
        fn += missed

        if len(expected_findings) == 0 and len(model_findings) == 0:
            tn += 1

        status_str = "PASS" if missed == 0 and (len(model_findings) > 0 or len(expected_findings) == 0) else "FLAG"
        print(f"[{status_str}] {case_id}: {title} (Found: {len(model_findings)}, Expected: {len(expected_findings)})")

    # PR Metrics calculation
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # -------------------------------------------------------------
    # 2. Evaluate Repository Summary Accuracy Benchmark
    # -------------------------------------------------------------
    print("\n--- 2. Repository Summary Truth & Evidence Citation Benchmark ---")
    incorrect_claims = 0
    unsupported_claims = 0
    missing_expected_facts = 0
    total_citations_checked = 0
    valid_citations = 0

    for s_case in SYNTHETIC_SUMMARY_BENCHMARK_CASES:
        s_id = s_case["case_id"]
        repo_name = s_case["repo_name"]
        mock_data = MOCK_REPOSITORIES.get(repo_name)
        if not mock_data:
            print(f"[{s_id}] Mock repo {repo_name} not found!")
            continue

        mock_repo = Repository(
            id=mock_data["id"],
            full_name=mock_data["full_name"],
            owner=mock_data["owner"],
            name=mock_data["name"],
            default_branch=mock_data["default_branch"],
            indexed_commit_sha=mock_data["commit_sha"],
            indexing_status="completed"
        )

        # Build chunks from files
        mock_chunks = []
        for f_path, f_content in mock_data["files"].items():
            lines = f_content.split("\n")
            mock_chunks.append(CodeChunk(
                repository_id=mock_repo.id,
                commit_sha=mock_repo.indexed_commit_sha,
                file_path=f_path,
                start_line=1,
                end_line=len(lines),
                content=f_content,
                language="Python" if f_path.endswith(".py") else "TypeScript" if f_path.endswith(".ts") else "Text"
            ))

        profiler = RepositoryProfiler(mock_repo, mock_chunks)
        overview, deep, summary_md = profiler.build_profile()

        # Check expected facts
        case_missing = 0
        summary_lower = (summary_md + " " + overview.purpose).lower()

        for exp in s_case["expected_facts"]:
            found = False
            for kw in exp["keywords"]:
                if kw.lower() in summary_lower:
                    found = True
                    break
            if not found:
                missing_expected_facts += 1
                case_missing += 1

        # Check disallowed claims (e.g. Cassandra or PyTorch from misleading README)
        case_incorrect = 0
        for dis in s_case.get("disallowed_claims", []):
            for kw in dis["keywords"]:
                # Check if kw appears as a confirmed fact in overview (not in unconfirmed list)
                confirmed_in_frameworks = any(kw.lower() in f["name"].lower() for f in overview.frameworks)
                confirmed_in_integrations = any(kw.lower() in i["name"].lower() for i in overview.integrations)
                if confirmed_in_frameworks or confirmed_in_integrations:
                    incorrect_claims += 1
                    case_incorrect += 1

        # Check citation validity
        for cit in overview.purpose_evidence:
            total_citations_checked += 1
            if cit.file_path in mock_data["files"]:
                valid_citations += 1
            else:
                unsupported_claims += 1

        for f in overview.frameworks:
            if "file_path" in f:
                total_citations_checked += 1
                if f["file_path"] in mock_data["files"]:
                    valid_citations += 1
                else:
                    unsupported_claims += 1

        for i in overview.integrations:
            if "file_path" in i:
                total_citations_checked += 1
                if i["file_path"] in mock_data["files"]:
                    valid_citations += 1
                else:
                    unsupported_claims += 1

        status_str = "PASS" if case_missing == 0 and case_incorrect == 0 else "FLAG"
        print(f"[{status_str}] {s_id}: {repo_name} (Expected Facts: {len(s_case['expected_facts'])}, Missing: {case_missing}, False Claims: {case_incorrect})")

    citation_accuracy = valid_citations / total_citations_checked if total_citations_checked > 0 else 1.0

    # -------------------------------------------------------------
    # 3. Evaluate Language Coverage & Analysis Mode Distribution
    # -------------------------------------------------------------
    print("\n--- 3. Language Adapter & Analysis Mode Distribution ---")
    from app.services.languages.detect import detect_file_language
    from app.services.parser.chunker import chunk_file

    lang_stats: Dict[str, Dict[str, int]] = {}
    for repo_name, repo_data in MOCK_REPOSITORIES.items():
        for f_path, f_content in repo_data.get("files", {}).items():
            adapter, _ = detect_file_language(f_path, f_content)
            chunks, _ = chunk_file(f_content, f_path)
            mode = "parser_aware" if any(c.analysis_mode == "parser_aware" for c in chunks) else "text_fallback"

            if adapter.name not in lang_stats:
                lang_stats[adapter.name] = {"parser_aware": 0, "text_fallback": 0, "chunks": 0}
            lang_stats[adapter.name][mode] += 1
            lang_stats[adapter.name]["chunks"] += len(chunks)

    print(f"{'Language':<18} | {'Parser-Aware Files':<18} | {'Fallback Files':<16} | {'Total Chunks':<12}")
    print("-" * 72)
    for lang, stats in sorted(lang_stats.items()):
        print(f"{lang:<18} | {stats['parser_aware']:<18} | {stats['text_fallback']:<16} | {stats['chunks']:<12}")

    print("\n" + "=" * 70)
    print(" COMPREHENSIVE BENCHMARK PERFORMANCE REPORT")
    print("=" * 70)
    print("--- Pull Request Code Review Metrics ---")
    print(f"Total Synthetic Cases  : {len(SYNTHETIC_BENCHMARK_CASES)}")
    print(f"True Positives (TP)    : {tp}")
    print(f"False Positives (FP)   : {fp}")
    print(f"False Negatives (FN)   : {fn}")
    print(f"Precision              : {precision:.3f} ({precision * 100:.1f}%)")
    print(f"Recall                 : {recall:.3f} ({recall * 100:.1f}%)")
    print(f"F1 Score               : {f1:.3f}")
    print(f"False Positive Rate    : {fpr:.3f}")

    print("\n--- Repository Summary Accuracy & Truth Metrics ---")
    print(f"Total Summary Cases    : {len(SYNTHETIC_SUMMARY_BENCHMARK_CASES)}")
    print(f"Missing Expected Facts : {missing_expected_facts}")
    print(f"Incorrect Claims       : {incorrect_claims}")
    print(f"Unsupported Claims     : {unsupported_claims}")
    print(f"Citation Accuracy      : {citation_accuracy:.3f} ({citation_accuracy * 100:.1f}%)")
    print("=" * 70)

    # Regression quality gates
    failed_regression = False
    if strict_regression:
        if precision < 0.70:
            print(f"[REGRESSION FAILURE] Precision {precision:.2f} is below 0.70 threshold.")
            failed_regression = True
        if recall < 0.70:
            print(f"[REGRESSION FAILURE] Recall {recall:.2f} is below 0.70 threshold.")
            failed_regression = True
        if incorrect_claims > 0:
            print(f"[REGRESSION FAILURE] Incorrect claims detected: {incorrect_claims}.")
            failed_regression = True
        if unsupported_claims > 0:
            print(f"[REGRESSION FAILURE] Unsupported claims detected: {unsupported_claims}.")
            failed_regression = True
        if citation_accuracy < 0.90:
            print(f"[REGRESSION FAILURE] Citation accuracy {citation_accuracy:.2f} is below 0.90 threshold.")
            failed_regression = True

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": fpr,
        "missing_expected_facts": missing_expected_facts,
        "incorrect_claims": incorrect_claims,
        "unsupported_claims": unsupported_claims,
        "citation_accuracy": citation_accuracy,
        "failed_regression": failed_regression
    }


def main():
    parser = argparse.ArgumentParser(description="RepoSage AI Code Review Benchmark & Evaluation Suite")
    parser.add_argument("--regression", action="store_true", help="Fail with non-zero exit code if quality drops below threshold")
    args = parser.parse_args()

    results = asyncio.run(run_evaluation(strict_regression=args.regression))
    if results.get("failed_regression"):
        sys.exit(1)


if __name__ == "__main__":
    main()
