import json
from datetime import date
from pathlib import Path

import pytest

from evidenceflow.assurance import (
    MAX_MODEL_OBSERVATIONS,
    AssuranceObservation,
    AssuranceReport,
    PilotScope,
    RepositoryPolicyScanner,
    ScannerTriageProvider,
    ScopeError,
    build_evidence_pack,
    import_sarif,
    report_to_case,
)
from evidenceflow.audit import AuditLog
from evidenceflow.models import Assessment, Citation, EvidenceCase, EvidenceSource, Risk
from evidenceflow.validation import ValidationError, validate_assurance_assessment
from evidenceflow.workflow import EvidenceWorkflow, InMemoryRepository


def write_scope(tmp_path: Path, repo: Path, **overrides: object) -> Path:
    payload = {
        "version": 1,
        "engagement_id": "pilot-1",
        "customer": "Synthetic customer",
        "expires_on": "2030-01-01",
        "egress": "deny",
        "repositories": [
            {
                "repository_id": "sample-repo",
                "path": str(repo),
                "allowed_checks": ["repository-policy", "sarif-import"],
            }
        ],
    }
    payload.update(overrides)
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_scope_authorizes_only_declared_repository_and_check(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    scope = PilotScope.load(write_scope(tmp_path, repo))
    scope.authorize("sample-repo", repo, "repository-policy")
    with pytest.raises(ScopeError, match="outside pilot scope"):
        scope.authorize("other-repo", repo, "repository-policy")
    with pytest.raises(ScopeError, match="outside pilot scope"):
        scope.authorize("sample-repo", repo, "active-exploitation")


def test_scope_rejects_expired_authorization(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    scope = PilotScope.load(write_scope(tmp_path, repo))
    with pytest.raises(ScopeError, match="expired"):
        scope.authorize(
            "sample-repo",
            repo,
            "repository-policy",
            today=date(2031, 1, 1),
        )


def test_local_only_scope_rejects_external_model_endpoint(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    scope = PilotScope.load(write_scope(tmp_path, repo))
    scope.require_provider_url_allowed("http://127.0.0.1:11434/v1")
    with pytest.raises(ScopeError, match="local model endpoints"):
        scope.require_provider_url_allowed("https://models.example.test/v1")


def test_repository_policy_scan_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("Apache-2.0", encoding="utf-8")
    report = RepositoryPolicyScanner().scan(tmp_path, "repo", "pilot")
    assert len(report.observations) == 5
    license_result = next(
        item for item in report.observations if item.check == "license"
    )
    security_result = next(
        item for item in report.observations if item.check == "security-policy"
    )
    assert license_result.status == "pass"
    assert security_result.status == "review"


def test_sarif_import_preserves_message_and_location(tmp_path: Path) -> None:
    sarif = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "SyntheticScanner"}},
                "results": [
                    {
                        "ruleId": "demo.rule",
                        "level": "warning",
                        "message": {"text": "Synthetic finding"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/demo.py"}
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }
    path = tmp_path / "result.sarif"
    path.write_text(json.dumps(sarif), encoding="utf-8")
    report = import_sarif(path, engagement_id="pilot", repository_id="repo")
    assert report.observations[0].message == "Synthetic finding"
    assert report.observations[0].path == "src/demo.py"
    assert report.observations[0].severity == "medium"


def test_evidence_pack_is_grounded_and_stays_pending_approval(tmp_path: Path) -> None:
    report = RepositoryPolicyScanner().scan(tmp_path, "repo", "pilot")
    case = report_to_case(report)
    audit = AuditLog(tmp_path / "audit.jsonl")
    record = EvidenceWorkflow(
        ScannerTriageProvider(), InMemoryRepository(), audit
    ).analyze(case)
    pack = build_evidence_pack(
        report,
        record.assessment,
        audit_verified=audit.verify(),
    )
    assert "pending_approval" in pack
    assert "Risk: **medium**" in pack
    assert record.assessment.citations[0].quote in pack
    assert "named reviewer" in pack


def test_model_input_is_bounded_and_prioritizes_high_severity() -> None:
    observations = tuple(
        AssuranceObservation(
            f"obs-{index}",
            "synthetic",
            "review",
            "critical" if index == 150 else "low",
            f"file-{index}",
            "Synthetic observation",
        )
        for index in range(151)
    )
    case = report_to_case(AssuranceReport("eng", "repo", "test", observations))
    assert len(case.sources) == MAX_MODEL_OBSERVATIONS + 1
    assert case.sources[0].source_id == "obs-150"
    assert case.sources[-1].source_id == "scanner-selection-summary"


def test_assurance_validator_rejects_unsupported_compliance_claim() -> None:
    case = EvidenceCase(
        "case",
        "Synthetic",
        (EvidenceSource("source", "A governance file is present."),),
    )
    assessment = Assessment(
        Risk.LOW,
        "The repository demonstrates strong compliance.",
        ("compliance",),
        (Citation("source", "A governance file is present."),),
        0.9,
    )
    with pytest.raises(ValidationError, match="prohibited assurance"):
        validate_assurance_assessment(case, assessment)
