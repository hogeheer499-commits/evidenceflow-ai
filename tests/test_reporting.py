from pathlib import Path

from evidenceflow.assurance import AssuranceObservation, AssuranceReport
from evidenceflow.models import Assessment, Citation, Risk
from evidenceflow.reporting import build_management_summary, build_pilot_metrics
from evidenceflow.scanners import ScannerExecution


def test_metrics_preserve_limits_and_isolation() -> None:
    report = AssuranceReport(
        "eng",
        "repo",
        "suite",
        (
            AssuranceObservation(
                "obs-1", "policy", "review", "medium", "SECURITY.md", "Missing"
            ),
        ),
    )
    assessment = Assessment(
        Risk.MEDIUM,
        "Review required",
        ("deterministic",),
        (Citation("obs-1", "quote"),),
        1.0,
    )
    execution = ScannerExecution(
        "semgrep", "/bin/semgrep", Path("result.sarif"), 0, True, 5.0
    )
    metrics = build_pilot_metrics(
        report,
        assessment,
        (execution,),
        audit_verified=True,
        provider_duration_ms=10.0,
    )
    assert metrics["external_scanners_network_isolated"] is True
    assert metrics["claims"]["complete_vulnerability_coverage"] is False
    assert "geen compliancecertificering" in build_management_summary(metrics)
