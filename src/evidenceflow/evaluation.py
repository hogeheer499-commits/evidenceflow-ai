from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .audit import AuditLog
from .models import EvidenceCase, EvidenceSource
from .providers import AnalysisProvider
from .workflow import EvidenceWorkflow, InMemoryRepository


def evaluate(dataset: Path, provider: AnalysisProvider) -> dict[str, object]:
    rows = [json.loads(line) for line in dataset.read_text().splitlines() if line]
    correct = 0
    citation_valid = 0
    with TemporaryDirectory() as directory:
        workflow = EvidenceWorkflow(
            provider,
            InMemoryRepository(),
            AuditLog(Path(directory) / "eval-audit.jsonl"),
        )
        for row in rows:
            case = EvidenceCase(
                case_id=row["case_id"],
                title=row["title"],
                sources=tuple(
                    EvidenceSource(source_id=s["source_id"], text=s["text"])
                    for s in row["sources"]
                ),
            )
            record = workflow.analyze(case)
            correct += record.assessment.risk.value == row["expected_risk"]
            citation_valid += bool(record.assessment.citations)
    total = len(rows)
    return {
        "dataset": str(dataset),
        "cases": total,
        "risk_accuracy": correct / total if total else 0.0,
        "citation_validity": citation_valid / total if total else 0.0,
        "note": "Synthetic regression dataset; not an enterprise benchmark.",
    }
