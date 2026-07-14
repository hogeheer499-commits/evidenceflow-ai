from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from .audit import AuditLog
from .models import EvidenceCase, WorkflowRecord, WorkflowState
from .providers import AnalysisProvider, ProviderError, TransientProviderError
from .telemetry import Telemetry
from .validation import validate_assessment, validate_case


class WorkflowError(RuntimeError):
    pass


class ApprovalRequired(WorkflowError):
    pass


class Publisher(Protocol):
    def publish(self, record: WorkflowRecord, idempotency_key: str) -> str: ...


@dataclass
class InMemoryRepository:
    records: dict[str, WorkflowRecord] = field(default_factory=dict)

    def get(self, case_id: str) -> WorkflowRecord | None:
        return self.records.get(case_id)

    def save(self, record: WorkflowRecord) -> None:
        self.records[record.case.case_id] = record


@dataclass
class InMemoryPublisher:
    calls: list[str] = field(default_factory=list)

    def publish(self, record: WorkflowRecord, idempotency_key: str) -> str:
        if idempotency_key not in self.calls:
            self.calls.append(idempotency_key)
        return f"receipt:{idempotency_key[:16]}"


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 0.01


class EvidenceWorkflow:
    def __init__(
        self,
        provider: AnalysisProvider,
        repository: InMemoryRepository,
        audit: AuditLog,
        telemetry: Telemetry | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.audit = audit
        self.telemetry = telemetry or Telemetry()
        self.retry_policy = retry_policy or RetryPolicy()

    def analyze(self, case: EvidenceCase) -> WorkflowRecord:
        existing = self.repository.get(case.case_id)
        if existing:
            if existing.case.fingerprint != case.fingerprint:
                raise WorkflowError("case_id already exists with different evidence")
            self.audit.append("analysis_deduplicated", case.case_id)
            self.telemetry.increment("analysis_deduplicated")
            return existing

        try:
            validate_case(case)
        except ValueError as exc:
            self.audit.append("input_rejected", case.case_id, reason=str(exc))
            self.telemetry.increment("input_rejected")
            raise

        record = WorkflowRecord(case=case)
        self.audit.append("case_received", case.case_id)
        assessment = None
        with self.telemetry.measure("provider_latency"):
            for attempt in range(1, self.retry_policy.attempts + 1):
                try:
                    assessment = self.provider.analyze(case)
                    break
                except TransientProviderError as exc:
                    self.audit.append(
                        "provider_retry", case.case_id, attempt=attempt, reason=str(exc)
                    )
                    self.telemetry.increment("provider_retry")
                    if attempt == self.retry_policy.attempts:
                        record.state = WorkflowState.FAILED
                        self.repository.save(record)
                        self.audit.append("analysis_failed", case.case_id)
                        self.telemetry.increment("analysis_failed")
                        raise
                    time.sleep(
                        self.retry_policy.base_delay_seconds * 2 ** (attempt - 1)
                    )
                except ProviderError as exc:
                    record.state = WorkflowState.FAILED
                    self.repository.save(record)
                    self.audit.append("analysis_failed", case.case_id, reason=str(exc))
                    self.telemetry.increment("analysis_failed")
                    raise
        if assessment is None:
            raise AssertionError("provider retry loop ended without a result")
        try:
            validate_assessment(case, assessment)
        except ValueError as exc:
            record.state = WorkflowState.FAILED
            self.repository.save(record)
            self.audit.append("analysis_failed", case.case_id, reason=str(exc))
            self.telemetry.increment("analysis_failed")
            raise
        record.assessment = assessment
        record.state = WorkflowState.PENDING_APPROVAL
        self.repository.save(record)
        self.audit.append(
            "analysis_completed", case.case_id, risk=assessment.risk.value
        )
        self.telemetry.increment("analysis_completed")
        return record

    def approve(self, case_id: str, reviewer: str) -> WorkflowRecord:
        record = self._required_record(case_id)
        if record.state == WorkflowState.PUBLISHED:
            return record
        if record.state != WorkflowState.PENDING_APPROVAL:
            raise WorkflowError(f"cannot approve a case in state {record.state}")
        if not reviewer.strip():
            raise WorkflowError("a named reviewer is required")
        record.reviewer = reviewer
        record.state = WorkflowState.APPROVED
        self.repository.save(record)
        self.audit.append("case_approved", case_id, reviewer=reviewer)
        self.telemetry.increment("case_approved")
        return record

    def publish(self, case_id: str, publisher: Publisher) -> WorkflowRecord:
        record = self._required_record(case_id)
        if record.state == WorkflowState.PUBLISHED:
            self.audit.append("publish_deduplicated", case_id)
            self.telemetry.increment("publish_deduplicated")
            return record
        if record.state != WorkflowState.APPROVED or record.assessment is None:
            self.audit.append("publish_blocked", case_id, state=record.state.value)
            self.telemetry.increment("publish_blocked")
            raise ApprovalRequired("explicit human approval is required")
        key = f"{record.case.fingerprint}:{record.assessment.fingerprint}"
        with self.telemetry.measure("publish_latency"):
            record.receipt = publisher.publish(record, key)
        record.state = WorkflowState.PUBLISHED
        self.repository.save(record)
        self.audit.append("case_published", case_id, receipt=record.receipt)
        self.telemetry.increment("case_published")
        return record

    def _required_record(self, case_id: str) -> WorkflowRecord:
        record = self.repository.get(case_id)
        if record is None:
            raise WorkflowError(f"unknown case_id: {case_id}")
        return record
