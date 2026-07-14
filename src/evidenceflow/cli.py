from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .audit import AuditLog
from .evaluation import evaluate
from .models import EvidenceCase, EvidenceSource
from .providers import KeywordProvider, OpenAICompatibleProvider
from .workflow import EvidenceWorkflow, InMemoryPublisher, InMemoryRepository


def _workflow(provider=None, audit_name: str = "audit.jsonl") -> EvidenceWorkflow:
    return EvidenceWorkflow(
        provider or KeywordProvider(),
        InMemoryRepository(),
        AuditLog(Path("artifacts") / audit_name),
    )


def _case_from_json(path: Path) -> EvidenceCase:
    payload = json.loads(path.read_text())
    return EvidenceCase(
        case_id=payload["case_id"],
        title=payload["title"],
        sources=tuple(
            EvidenceSource(source_id=s["source_id"], text=s["text"])
            for s in payload["sources"]
        ),
    )


def demo() -> None:
    workflow = _workflow(audit_name="demo-audit.jsonl")
    case = EvidenceCase(
        case_id="demo-001",
        title="Synthetic access-control alert",
        sources=(
            EvidenceSource(
                "alert-1",
                "Unauthorized access was detected for a synthetic service account.",
            ),
        ),
    )
    publisher = InMemoryPublisher()
    record = workflow.analyze(case)
    print(f"state after analysis: {record.state}")
    workflow.approve(case.case_id, reviewer="local-demo-reviewer")
    record = workflow.publish(case.case_id, publisher)
    workflow.publish(case.case_id, publisher)
    print(f"state after approval and publish: {record.state}")
    print(f"publisher calls: {len(publisher.calls)}")
    print(json.dumps(workflow.telemetry.snapshot(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="evidenceflow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("demo")
    evaluate_parser = subparsers.add_parser("eval")
    evaluate_parser.add_argument(
        "--dataset", type=Path, default=Path("evals/golden.jsonl")
    )
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("case", type=Path)
    args = parser.parse_args()

    if args.command == "demo":
        demo()
    elif args.command == "eval":
        report = evaluate(args.dataset, KeywordProvider())
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/eval-report.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(json.dumps(report, indent=2))
    elif args.command == "analyze":
        provider = OpenAICompatibleProvider(
            base_url=os.environ["EVIDENCEFLOW_BASE_URL"],
            model=os.environ["EVIDENCEFLOW_MODEL"],
            api_key=os.getenv("EVIDENCEFLOW_API_KEY", "local"),
        )
        record = _workflow(provider, "model-audit.jsonl").analyze(
            _case_from_json(args.case)
        )
        print(json.dumps(asdict(record.assessment), default=str, indent=2))
