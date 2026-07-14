from pathlib import Path

from evidenceflow.evaluation import evaluate
from evidenceflow.providers import KeywordProvider


def test_golden_dataset_is_a_green_regression_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root / "evals/golden.jsonl", KeywordProvider())
    assert report["cases"] == 4
    assert report["risk_accuracy"] == 1.0
    assert report["citation_validity"] == 1.0
