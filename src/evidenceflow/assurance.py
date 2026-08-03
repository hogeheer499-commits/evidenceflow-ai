from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .models import Assessment, Citation, EvidenceCase, EvidenceSource, Risk


class ScopeError(ValueError):
    """Raised when an assurance action is outside the signed-off pilot scope."""


MAX_SARIF_BYTES = 50_000_000
MAX_SARIF_RESULTS = 10_000
MAX_MODEL_OBSERVATIONS = 100
MAX_MODEL_EVIDENCE_CHARS = 90_000


@dataclass(frozen=True)
class RepositoryAuthorization:
    repository_id: str
    path: Path
    allowed_checks: tuple[str, ...]


@dataclass(frozen=True)
class PilotScope:
    engagement_id: str
    customer: str
    expires_on: date
    egress: str
    repositories: tuple[RepositoryAuthorization, ...]

    @classmethod
    def load(cls, path: Path) -> PilotScope:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != 1:
            raise ScopeError("scope version must be 1")
        if payload.get("egress") not in {"deny", "local-only", "allow"}:
            raise ScopeError("egress must be deny, local-only, or allow")
        base = path.resolve().parent
        repositories = tuple(
            RepositoryAuthorization(
                repository_id=str(item["repository_id"]),
                path=(base / str(item["path"])).resolve(),
                allowed_checks=tuple(str(check) for check in item["allowed_checks"]),
            )
            for item in payload.get("repositories", [])
        )
        if not repositories:
            raise ScopeError("scope must authorize at least one repository")
        if any(
            not re.fullmatch(r"[A-Za-z0-9._-]+", repo.repository_id)
            for repo in repositories
        ):
            raise ScopeError("repository_id contains unsupported characters")
        if len({repo.repository_id for repo in repositories}) != len(repositories):
            raise ScopeError("repository_id values must be unique")
        return cls(
            engagement_id=str(payload["engagement_id"]),
            customer=str(payload["customer"]),
            expires_on=date.fromisoformat(str(payload["expires_on"])),
            egress=str(payload["egress"]),
            repositories=repositories,
        )

    def authorize(
        self,
        repository_id: str,
        repository_path: Path,
        check: str,
        *,
        today: date | None = None,
    ) -> RepositoryAuthorization:
        if self.expires_on < (today or date.today()):
            raise ScopeError("pilot authorization has expired")
        authorization = next(
            (repo for repo in self.repositories if repo.repository_id == repository_id),
            None,
        )
        if authorization is None:
            raise ScopeError(f"repository is outside pilot scope: {repository_id}")
        if repository_path.resolve() != authorization.path:
            raise ScopeError("repository path does not match the authorized checkout")
        if check not in authorization.allowed_checks:
            raise ScopeError(f"check is outside pilot scope: {check}")
        return authorization

    def require_provider_url_allowed(self, base_url: str) -> None:
        if self.egress == "allow":
            return
        parsed = urlparse(base_url)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not host:
            raise ScopeError("provider URL must be an absolute HTTP(S) URL")
        if host == "localhost":
            return
        try:
            if ipaddress.ip_address(host).is_loopback:
                return
        except ValueError:
            pass
        raise ScopeError("scope permits local model endpoints only")


@dataclass(frozen=True)
class AssuranceObservation:
    observation_id: str
    check: str
    status: str
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class AssuranceReport:
    engagement_id: str
    repository_id: str
    scanner: str
    observations: tuple[AssuranceObservation, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class RepositoryPolicyScanner:
    """Deterministic, read-only checks for visible repository controls."""

    REQUIRED_CONTROLS = (
        ("license", ("LICENSE", "LICENSE.md", "LICENSE.txt"), "medium"),
        ("security-policy", ("SECURITY.md", ".github/SECURITY.md"), "medium"),
        ("codeowners", ("CODEOWNERS", ".github/CODEOWNERS"), "low"),
        ("publiccode", ("publiccode.yml", "publiccode.yaml"), "low"),
        (
            "dependency-updates",
            (".github/dependabot.yml", ".github/dependabot.yaml"),
            "low",
        ),
    )

    def scan(
        self, root: Path, repository_id: str, engagement_id: str
    ) -> AssuranceReport:
        root = root.resolve()
        observations: list[AssuranceObservation] = []
        for check, candidates, missing_severity in self.REQUIRED_CONTROLS:
            found = next(
                (candidate for candidate in candidates if (root / candidate).is_file()),
                None,
            )
            status = "pass" if found else "review"
            path = found or candidates[0]
            message = (
                f"Control is visible at {found}."
                if found
                else f"No {check} control was found at the checked standard locations."
            )
            observations.append(
                AssuranceObservation(
                    observation_id=f"repo-policy:{check}",
                    check=check,
                    status=status,
                    severity="info" if found else missing_severity,
                    path=path,
                    message=message,
                )
            )
        return AssuranceReport(
            engagement_id=engagement_id,
            repository_id=repository_id,
            scanner="evidenceflow-repository-policy/v1",
            observations=tuple(observations),
        )


class ScannerTriageProvider:
    """Deterministic baseline triage for normalized scanner observations."""

    RISK_ORDER = {
        "info": Risk.LOW,
        "low": Risk.LOW,
        "medium": Risk.MEDIUM,
        "high": Risk.HIGH,
        "critical": Risk.CRITICAL,
    }

    def analyze(self, case: EvidenceCase) -> Assessment:
        parsed: list[tuple[EvidenceSource, dict[str, object]]] = []
        for source in case.sources:
            try:
                observation = json.loads(source.text)
            except json.JSONDecodeError:
                observation = {"severity": "low", "status": "review"}
            parsed.append((source, observation))
        review_items = [
            item for item in parsed if str(item[1].get("status")) == "review"
        ]
        candidates = review_items or parsed
        risk = max(
            (
                self.RISK_ORDER.get(str(item[1].get("severity")), Risk.MEDIUM)
                for item in candidates
            ),
            default=Risk.LOW,
            key=lambda value: list(Risk).index(value),
        )
        citations = tuple(
            Citation(source_id=source.source_id, quote=source.text)
            for source, _ in candidates[:10]
        )
        return Assessment(
            risk=risk,
            summary=(
                f"Deterministic triage found {len(review_items)} observation(s) "
                "requiring human review."
            ),
            labels=(
                "deterministic-baseline",
                ("human-review-required" if review_items else "no-review-observations"),
            ),
            citations=citations,
            confidence=1.0,
        )


def import_sarif(
    path: Path, *, engagement_id: str, repository_id: str
) -> AssuranceReport:
    """Normalize SARIF results while preserving their original messages."""

    if path.stat().st_size > MAX_SARIF_BYTES:
        raise ValueError("SARIF report exceeds the configured size limit")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("runs", []), list):
        raise ValueError("SARIF report must contain a runs array")
    observations: list[AssuranceObservation] = []
    for run_index, run in enumerate(payload.get("runs", []), start=1):
        tool = run.get("tool", {}).get("driver", {}).get("name", "unknown")
        tool_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(tool)).strip("-")
        for result_index, result in enumerate(run.get("results", []), start=1):
            if len(observations) >= MAX_SARIF_RESULTS:
                raise ValueError("SARIF report exceeds the configured result limit")
            location = (result.get("locations") or [{}])[0]
            physical = location.get("physicalLocation", {})
            uri = physical.get("artifactLocation", {}).get("uri", "unknown")
            rule_id = str(result.get("ruleId", "unclassified"))
            observations.append(
                AssuranceObservation(
                    observation_id=(
                        f"sarif:{tool_slug}:{run_index}:{result_index}:{rule_id}"
                    ),
                    check=f"sarif:{tool}:{rule_id}",
                    status="review",
                    severity=_sarif_severity(result.get("level")),
                    path=str(uri),
                    message=str(result.get("message", {}).get("text", "No message")),
                )
            )
    return AssuranceReport(
        engagement_id=engagement_id,
        repository_id=repository_id,
        scanner="sarif-import/v1",
        observations=tuple(observations),
    )


def merge_reports(
    reports: tuple[AssuranceReport, ...],
    *,
    engagement_id: str,
    repository_id: str,
) -> AssuranceReport:
    if not reports:
        raise ValueError("at least one assurance report is required")
    for report in reports:
        if report.engagement_id != engagement_id:
            raise ValueError("cannot merge reports from different engagements")
        if report.repository_id != repository_id:
            raise ValueError("cannot merge reports from different repositories")
    observations = tuple(
        observation for report in reports for observation in report.observations
    )
    return AssuranceReport(
        engagement_id=engagement_id,
        repository_id=repository_id,
        scanner="kleine-koe-assurance-suite/v1",
        observations=observations,
    )


def report_to_case(report: AssuranceReport) -> EvidenceCase:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    ordered = sorted(
        report.observations,
        key=lambda item: (severity_order.get(item.severity, 2), item.observation_id),
    )
    selected: list[EvidenceSource] = []
    total_chars = 0
    for observation in ordered:
        text = json.dumps(asdict(observation), sort_keys=True)
        if len(selected) >= MAX_MODEL_OBSERVATIONS:
            break
        if total_chars + len(text) > MAX_MODEL_EVIDENCE_CHARS:
            break
        selected.append(EvidenceSource(observation.observation_id, text))
        total_chars += len(text)
    sources = tuple(selected)
    omitted = len(report.observations) - len(sources)
    if omitted:
        sources += (
            EvidenceSource(
                source_id="scanner-selection-summary",
                text=(
                    f"{omitted} lower-priority observations were preserved in the "
                    "raw report but omitted from model input by configured limits."
                ),
            ),
        )
    if not sources:
        sources = (
            EvidenceSource(
                source_id="scanner-summary",
                text="The authorized deterministic scan returned no observations.",
            ),
        )
    return EvidenceCase(
        case_id=(
            f"{report.engagement_id}:{report.repository_id}:{report.fingerprint[:16]}"
        ),
        title=f"Assurance observations for {report.repository_id}",
        sources=sources,
    )


def build_evidence_pack(
    report: AssuranceReport,
    assessment: Assessment,
    *,
    audit_verified: bool,
) -> str:
    findings = json.dumps(report.to_dict(), indent=2, sort_keys=True).replace(
        "```", "` ` `"
    )
    citations = "\n".join(
        f"- `{citation.source_id}`: {citation.quote}"
        for citation in assessment.citations
    )
    return (
        "# Kleine Koe EvidenceFlow\n\n"
        f"## Private assurance evidence pack — {report.repository_id}\n\n"
        f"Engagement: `{report.engagement_id}`  \n"
        f"Scanner: `{report.scanner}`  \n"
        f"Audit chain verified: `{str(audit_verified).lower()}`  \n"
        "Workflow state: `pending_approval`\n\n"
        "## AI-assisted triage\n\n"
        f"Risk: **{assessment.risk.value}**  \n"
        f"Confidence: **{assessment.confidence:.2f}**\n\n"
        f"{assessment.summary}\n\n"
        "## Grounded citations\n\n"
        f"{citations}\n\n"
        "## Deterministic scanner evidence\n\n"
        f"```json\n{findings}\n```\n\n"
        "## Required decision\n\n"
        "A named reviewer must validate scope, severity, reachability and the "
        "proposed recipient before any external publication or ticket creation.\n"
    )


def _sarif_severity(level: object) -> str:
    return {
        "error": "high",
        "warning": "medium",
        "note": "low",
        "none": "info",
    }.get(str(level), "medium")
