from pathlib import Path

import pytest

from evidenceflow.audit import AuditLog
from evidenceflow.models import Assessment, Citation, EvidenceCase, EvidenceSource, Risk
from evidenceflow.providers import (
    KeywordProvider,
    OpenAICompatibleProvider,
    ProviderError,
    TransientProviderError,
)
from evidenceflow.validation import ValidationError
from evidenceflow.workflow import (
    ApprovalRequired,
    EvidenceWorkflow,
    InMemoryPublisher,
    InMemoryRepository,
    RetryPolicy,
    WorkflowError,
)


def case(case_id: str = "case-1") -> EvidenceCase:
    return EvidenceCase(
        case_id,
        "Synthetic alert",
        (EvidenceSource("source-1", "Unauthorized access was detected."),),
    )


def workflow(tmp_path: Path, provider=None) -> EvidenceWorkflow:
    return EvidenceWorkflow(
        provider or KeywordProvider(),
        InMemoryRepository(),
        AuditLog(tmp_path / "audit.jsonl"),
        retry_policy=RetryPolicy(attempts=3, base_delay_seconds=0),
    )


def test_requires_named_approval_before_publish(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    flow.analyze(case())
    publisher = InMemoryPublisher()
    with pytest.raises(ApprovalRequired):
        flow.publish("case-1", publisher)
    assert publisher.calls == []
    flow.approve("case-1", "reviewer@example.test")
    flow.publish("case-1", publisher)
    assert len(publisher.calls) == 1


def test_publish_is_idempotent(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    flow.analyze(case())
    flow.approve("case-1", "reviewer")
    publisher = InMemoryPublisher()
    first = flow.publish("case-1", publisher)
    second = flow.publish("case-1", publisher)
    assert first.receipt == second.receipt
    assert len(publisher.calls) == 1


def test_rejects_ungrounded_citation(tmp_path: Path) -> None:
    class UngroundedProvider:
        def analyze(self, evidence_case: EvidenceCase) -> Assessment:
            return Assessment(
                Risk.HIGH,
                "summary",
                (),
                (Citation("source-1", "quote not in evidence"),),
                0.9,
            )

    flow = workflow(tmp_path, UngroundedProvider())
    with pytest.raises(ValidationError, match="does not resolve"):
        flow.analyze(case())


def test_retries_transient_provider_failure(tmp_path: Path) -> None:
    class FlakyProvider:
        calls = 0

        def analyze(self, evidence_case: EvidenceCase) -> Assessment:
            self.calls += 1
            if self.calls < 3:
                raise TransientProviderError("temporary")
            return KeywordProvider().analyze(evidence_case)

    provider = FlakyProvider()
    flow = workflow(tmp_path, provider)
    flow.analyze(case())
    assert provider.calls == 3
    assert flow.telemetry.counters["provider_retry"] == 2


def test_permanent_provider_failure_is_audited(tmp_path: Path) -> None:
    class BrokenProvider:
        def analyze(self, evidence_case: EvidenceCase) -> Assessment:
            raise ProviderError("malformed response")

    flow = workflow(tmp_path, BrokenProvider())
    with pytest.raises(ProviderError, match="malformed response"):
        flow.analyze(case())
    assert flow.repository.get("case-1").state.value == "failed"
    assert flow.telemetry.counters["analysis_failed"] == 1
    assert "analysis_failed" in (tmp_path / "audit.jsonl").read_text()


def test_openai_provider_repairs_one_schema_error() -> None:
    class RepairingProvider(OpenAICompatibleProvider):
        responses = iter(
            [
                '{"risk":"high","summary":"x","labels":[],"citations":'
                '[{"source_id":"source-1","text":"wrong key"}],'
                '"confidence":0.8}',
                '{"risk":"high","summary":"Grounded","labels":[],"citations":'
                '[{"source_id":"source-1","quote":"Unauthorized access was '
                'detected."}],"confidence":0.8}',
            ]
        )

        def _complete(self, messages: list[dict[str, str]]) -> str:
            return next(self.responses)

    assessment = RepairingProvider("http://local", "test").analyze(case())
    assert assessment.risk == Risk.HIGH
    assert assessment.citations[0].quote == "Unauthorized access was detected."


def test_same_id_with_changed_evidence_is_rejected(tmp_path: Path) -> None:
    flow = workflow(tmp_path)
    flow.analyze(case())
    changed = EvidenceCase(
        "case-1",
        "Synthetic alert",
        (EvidenceSource("source-1", "Different evidence."),),
    )
    with pytest.raises(WorkflowError, match="different evidence"):
        flow.analyze(changed)


def test_hash_chain_detects_tampering(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    audit.append("first", "case-1")
    audit.append("second", "case-1")
    assert audit.verify()
    text = audit.path.read_text().replace('"event": "first"', '"event": "changed"')
    audit.path.write_text(text)
    assert not audit.verify()
