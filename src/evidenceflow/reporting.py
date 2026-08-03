from __future__ import annotations

from collections import Counter
from dataclasses import asdict

from .assurance import AssuranceReport
from .models import Assessment
from .scanners import ScannerExecution


def build_pilot_metrics(
    report: AssuranceReport,
    assessment: Assessment,
    executions: tuple[ScannerExecution, ...],
    *,
    audit_verified: bool,
    provider_duration_ms: float | None,
) -> dict[str, object]:
    statuses = Counter(item.status for item in report.observations)
    severities = Counter(item.severity for item in report.observations)
    return {
        "version": 1,
        "product": "Kleine Koe EvidenceFlow — Sovereign OSS Assurance",
        "engagement_id": report.engagement_id,
        "repository_id": report.repository_id,
        "report_fingerprint": report.fingerprint,
        "observations": len(report.observations),
        "status_counts": dict(sorted(statuses.items())),
        "severity_counts": dict(sorted(severities.items())),
        "assessment": {
            "risk": assessment.risk.value,
            "confidence": assessment.confidence,
            "citation_count": len(assessment.citations),
            "labels": list(assessment.labels),
        },
        "scanner_executions": [asdict(execution) for execution in executions],
        "external_scanners_network_isolated": all(
            execution.network_isolated for execution in executions
        ),
        "audit_verified": audit_verified,
        "provider_duration_ms": provider_duration_ms,
        "claims": {
            "complete_vulnerability_coverage": False,
            "compliance_certification": False,
            "active_production_testing": False,
        },
    }


def build_management_summary(metrics: dict[str, object]) -> str:
    assessment = metrics["assessment"]
    status_counts = metrics["status_counts"]
    severity_counts = metrics["severity_counts"]
    executions = metrics["scanner_executions"]
    scanners = ", ".join(item["scanner"] for item in executions) or "geen extern"
    duration = metrics.get("provider_duration_ms")
    if duration is None:
        duration_text = "niet gemeten"
    elif duration < 100:
        duration_text = "minder dan 0,1 seconde"
    else:
        duration_text = f"{duration / 1000:.1f} seconden"
    severity_text = (
        ", ".join(f"{key}: {value}" for key, value in severity_counts.items())
        or "geen observaties"
    )
    return f"""# Managementsamenvatting — Sovereign OSS Assurance

**Kleine Koe EvidenceFlow** heeft repository `{metrics["repository_id"]}` binnen
engagement `{metrics["engagement_id"]}` verwerkt. De workflow bleef lokaal,
gebruikte alleen toegestane checks en publiceerde niets zonder menselijke
goedkeuring.

## Uitkomst

- Samengestelde risicoclassificatie: **{assessment["risk"]}**.
- Observaties: **{metrics["observations"]}** totaal;
  **{status_counts.get("review", 0)}** vereisen menselijke review en
  **{status_counts.get("pass", 0)}** zijn als zichtbaar control-signaal geslaagd.
- Verdeling: {severity_text}.
- Externe scanners: **{scanners}**.
- Netwerkisolatie voor externe scanners:
  **{str(metrics["external_scanners_network_isolated"]).lower()}**.
- Exact herleidbare AI-citaties: **{assessment["citation_count"]}**.
- Model-/triageduur: **{duration_text}**.
- Auditketen geldig: **{str(metrics["audit_verified"]).lower()}**.

## Betekenis

Dit resultaat is een reproduceerbare triage van gedefinieerde scanner- en
repositorysignalen. Het is geen bewijs dat alle kwetsbaarheden zijn gevonden en
geen compliancecertificering. Een reviewer moet bereikbaarheid, ernst, eigenaar
en herstelbesluit bevestigen voordat een ticket, pull request of melding wordt
gemaakt.

## Beslispunt

Gebruik de pilot om triagetijd, duplicaten, eigenaarschap en geaccepteerde
herstelacties te vergelijken met de beginsituatie. Schaal alleen op wanneer de
afgesproken acceptatiecriteria aantoonbaar zijn gehaald.
"""
