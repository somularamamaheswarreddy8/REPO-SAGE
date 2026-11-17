import pytest
from app.evaluation.evaluate import run_evaluation


@pytest.mark.asyncio
async def test_benchmark_evaluation():
    metrics = await run_evaluation(strict_regression=True)
    assert metrics["precision"] >= 0.70
    assert metrics["recall"] >= 0.70
    assert metrics["f1_score"] >= 0.70
    assert metrics["false_positive_rate"] <= 0.30
    assert metrics["failed_regression"] is False
