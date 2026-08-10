from pathlib import Path

import pytest

from evidenceflow.audit import AuditLog
from evidenceflow.models import EvidenceCase, EvidenceSource, WorkflowState
from evidenceflow.persistence import DirectoryPublisher, SQLiteRepository
from evidenceflow.providers import KeywordProvider
from evidenceflow.workflow import ApprovalRequired, EvidenceWorkflow


def sample_case() -> EvidenceCase:
    return EvidenceCase(
        "durable-1",
        "Durable synthetic case",
        (EvidenceSource("source-1", "Unauthorized access was detected."),),
    )


def workflow(tmp_path: Path) -> EvidenceWorkflow:
    return EvidenceWorkflow(
        KeywordProvider(),
        SQLiteRepository(tmp_path / "state.db"),
        AuditLog(tmp_path / "audit.jsonl"),
    )


def test_sqlite_repository_survives_workflow_restart(tmp_path: Path) -> None:
    first = workflow(tmp_path)
    first.analyze(sample_case())
    second = workflow(tmp_path)
    assert second.repository.get("durable-1").state == WorkflowState.PENDING_APPROVAL
    second.approve("durable-1", "reviewer@kleinekoe.nl")
    third = workflow(tmp_path)
    assert third.repository.get("durable-1").reviewer == "reviewer@kleinekoe.nl"


def test_directory_publish_requires_approval_and_is_idempotent(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    flow.analyze(sample_case())
    publisher = DirectoryPublisher(tmp_path / "approved")
    with pytest.raises(ApprovalRequired):
        flow.publish("durable-1", publisher)
    flow.approve("durable-1", "reviewer@kleinekoe.nl")
    first = flow.publish("durable-1", publisher)
    second = workflow(tmp_path).publish("durable-1", publisher)
    assert first.receipt == second.receipt
    assert len(list((tmp_path / "approved").glob("approved-*.json"))) == 1


def test_list_records_returns_saved_cases(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "state.db")
    flow = EvidenceWorkflow(
        KeywordProvider(), repository, AuditLog(tmp_path / "audit.jsonl")
    )
    flow.analyze(sample_case())
    assert [record.case.case_id for record in repository.list_records()] == [
        "durable-1"
    ]
