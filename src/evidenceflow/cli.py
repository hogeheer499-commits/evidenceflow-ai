from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .assurance import (
    AssuranceReport,
    PilotScope,
    RepositoryPolicyScanner,
    ScannerTriageProvider,
    build_evidence_pack,
    import_sarif,
    merge_reports,
    report_to_case,
)
from .audit import AuditLog
from .evaluation import evaluate
from .models import EvidenceCase, EvidenceSource
from .persistence import DirectoryPublisher, SQLiteRepository
from .providers import KeywordProvider, OpenAICompatibleProvider
from .reporting import build_management_summary, build_pilot_metrics
from .scanners import ScannerExecution, ScannerRunner
from .validation import validate_assurance_assessment
from .web import serve_dashboard
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


def _assurance_provider(scope: PilotScope):
    base_url = os.getenv("EVIDENCEFLOW_BASE_URL")
    model = os.getenv("EVIDENCEFLOW_MODEL")
    if not base_url and not model:
        return ScannerTriageProvider()
    if not base_url or not model:
        raise ValueError(
            "EVIDENCEFLOW_BASE_URL and EVIDENCEFLOW_MODEL must be set together"
        )
    scope.require_provider_url_allowed(base_url)
    timeout_seconds = float(os.getenv("EVIDENCEFLOW_TIMEOUT_SECONDS", "45"))
    max_tokens = int(os.getenv("EVIDENCEFLOW_MAX_TOKENS", "1200"))
    if timeout_seconds <= 0 or max_tokens <= 0:
        raise ValueError("model timeout and max tokens must be positive")
    return OpenAICompatibleProvider(
        base_url=base_url,
        model=model,
        api_key=os.getenv("EVIDENCEFLOW_API_KEY", "local"),
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        disable_thinking=os.getenv("EVIDENCEFLOW_DISABLE_THINKING") == "1",
        assessment_validator=validate_assurance_assessment,
    )


def assure(
    *,
    scope_path: Path,
    repository_path: Path,
    repository_id: str,
    sarif_path: Path | None,
    output_dir: Path,
) -> None:
    scope = PilotScope.load(scope_path)
    check = "sarif-import" if sarif_path else "repository-policy"
    scope.authorize(repository_id, repository_path, check)
    if sarif_path:
        report = import_sarif(
            sarif_path,
            engagement_id=scope.engagement_id,
            repository_id=repository_id,
        )
    else:
        report = RepositoryPolicyScanner().scan(
            repository_path,
            repository_id,
            scope.engagement_id,
        )

    _process_assurance_report(report, scope=scope, output_dir=output_dir)


def _process_assurance_report(
    report: AssuranceReport,
    *,
    scope: PilotScope,
    output_dir: Path,
    executions: tuple[ScannerExecution, ...] = (),
) -> None:
    repository_id = report.repository_id
    destination = output_dir / repository_id
    destination.mkdir(parents=True, exist_ok=True)
    raw_scan = destination / "raw-scan.json"
    raw_scan.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if executions:
        (destination / "scanner-executions.json").write_text(
            json.dumps(
                [
                    {
                        "scanner": execution.scanner,
                        "executable": execution.executable,
                        "output": str(execution.output),
                        "return_code": execution.return_code,
                        "network_isolated": execution.network_isolated,
                        "duration_ms": execution.duration_ms,
                    }
                    for execution in executions
                ],
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    evidence_case = report_to_case(report)
    (destination / "evidence-case.json").write_text(
        json.dumps(asdict(evidence_case), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    audit = AuditLog(output_dir / "audit.jsonl")
    workflow = EvidenceWorkflow(
        _assurance_provider(scope),
        SQLiteRepository(output_dir / "workflow.db"),
        audit,
        assessment_validators=(validate_assurance_assessment,),
    )
    record = workflow.analyze(evidence_case)
    provider_durations = workflow.telemetry.durations_ms.get("provider_latency", [])
    metrics = build_pilot_metrics(
        report,
        record.assessment,
        executions,
        audit_verified=audit.verify(),
        provider_duration_ms=(provider_durations[-1] if provider_durations else None),
    )
    (destination / "assessment.json").write_text(
        json.dumps(asdict(record.assessment), default=str, indent=2) + "\n",
        encoding="utf-8",
    )
    (destination / "evidence-pack.md").write_text(
        build_evidence_pack(
            report,
            record.assessment,
            audit_verified=audit.verify(),
        ),
        encoding="utf-8",
    )
    (destination / "metrics.json").write_text(
        json.dumps(metrics, default=str, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "management-summary.md").write_text(
        build_management_summary(metrics),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "repository_id": repository_id,
                "observations": len(report.observations),
                "state": record.state.value,
                "case_id": record.case.case_id,
                "output_dir": str(destination),
            },
            indent=2,
        )
    )


def pilot(
    *,
    scope_path: Path,
    repository_path: Path,
    repository_id: str,
    checks: tuple[str, ...],
    output_dir: Path,
    rules: Path,
    offline_database: Path | None,
) -> None:
    supported = {"repository-policy", "semgrep", "gitleaks", "osv"}
    unknown = set(checks) - supported
    if unknown:
        raise ValueError(f"unsupported checks: {', '.join(sorted(unknown))}")
    if not checks:
        raise ValueError("at least one check is required")
    scope = PilotScope.load(scope_path)
    for check in checks:
        scope.authorize(repository_id, repository_path, check)
    reports: list[AssuranceReport] = []
    executions: list[ScannerExecution] = []
    scanner_output = output_dir / repository_id / "scanner-raw"
    if "repository-policy" in checks:
        reports.append(
            RepositoryPolicyScanner().scan(
                repository_path,
                repository_id,
                scope.engagement_id,
            )
        )
    external_checks = set(checks) - {"repository-policy"}
    if external_checks:
        runner = ScannerRunner(require_network_isolation=True)
        if "semgrep" in external_checks:
            executions.append(runner.semgrep(repository_path, scanner_output, rules))
        if "gitleaks" in external_checks:
            executions.append(runner.gitleaks(repository_path, scanner_output))
        if "osv" in external_checks:
            if offline_database is None:
                raise ValueError("--offline-db is required for the OSV check")
            executions.append(
                runner.osv(
                    repository_path,
                    scanner_output,
                    offline_database,
                )
            )
        reports.extend(
            runner.report(
                execution,
                engagement_id=scope.engagement_id,
                repository_id=repository_id,
            )
            for execution in executions
        )
    report = merge_reports(
        tuple(reports),
        engagement_id=scope.engagement_id,
        repository_id=repository_id,
    )
    _process_assurance_report(
        report,
        scope=scope,
        output_dir=output_dir,
        executions=tuple(executions),
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
    assure_parser = subparsers.add_parser("assure")
    assure_parser.add_argument("--scope", type=Path, required=True)
    assure_parser.add_argument("--repo", type=Path, required=True)
    assure_parser.add_argument("--repo-id", required=True)
    assure_parser.add_argument("--sarif", type=Path)
    assure_parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/assurance")
    )
    pilot_parser = subparsers.add_parser("pilot")
    pilot_parser.add_argument("--scope", type=Path, required=True)
    pilot_parser.add_argument("--repo", type=Path, required=True)
    pilot_parser.add_argument("--repo-id", required=True)
    pilot_parser.add_argument(
        "--checks",
        nargs="+",
        default=["repository-policy", "semgrep"],
        choices=["repository-policy", "semgrep", "gitleaks", "osv"],
    )
    pilot_parser.add_argument(
        "--rules",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "rules" / "semgrep",
    )
    pilot_parser.add_argument("--offline-db", type=Path)
    pilot_parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/pilot")
    )
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--json", action="store_true")
    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("--state-db", type=Path, required=True)
    approve_parser.add_argument("--audit", type=Path, required=True)
    approve_parser.add_argument("--case-id", required=True)
    approve_parser.add_argument("--reviewer", required=True)
    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--state-db", type=Path, required=True)
    publish_parser.add_argument("--audit", type=Path, required=True)
    publish_parser.add_argument("--case-id", required=True)
    publish_parser.add_argument("--destination", type=Path, required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--state-db", type=Path, required=True)
    status_parser.add_argument("--case-id")
    verify_parser = subparsers.add_parser("verify-audit")
    verify_parser.add_argument("--audit", type=Path, required=True)
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--state-db", type=Path, required=True)
    serve_parser.add_argument("--audit", type=Path, required=True)
    serve_parser.add_argument("--approved-dir", type=Path, required=True)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
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
    elif args.command == "assure":
        assure(
            scope_path=args.scope,
            repository_path=args.repo,
            repository_id=args.repo_id,
            sarif_path=args.sarif,
            output_dir=args.output_dir,
        )
    elif args.command == "pilot":
        pilot(
            scope_path=args.scope,
            repository_path=args.repo,
            repository_id=args.repo_id,
            checks=tuple(args.checks),
            output_dir=args.output_dir,
            rules=args.rules,
            offline_database=args.offline_db,
        )
    elif args.command == "preflight":
        preflight = ScannerRunner.preflight()
        print(json.dumps(preflight, indent=2))
        if not preflight["network_sandbox_usable"] or any(
            executable is None for executable in preflight["scanners"].values()
        ):
            raise SystemExit(2)
    elif args.command == "approve":
        flow = EvidenceWorkflow(
            KeywordProvider(),
            SQLiteRepository(args.state_db),
            AuditLog(args.audit),
        )
        record = flow.approve(args.case_id, args.reviewer)
        print(
            json.dumps(
                {
                    "case_id": record.case.case_id,
                    "state": record.state.value,
                    "reviewer": record.reviewer,
                },
                indent=2,
            )
        )
    elif args.command == "publish":
        flow = EvidenceWorkflow(
            KeywordProvider(),
            SQLiteRepository(args.state_db),
            AuditLog(args.audit),
        )
        record = flow.publish(
            args.case_id,
            DirectoryPublisher(args.destination),
        )
        print(
            json.dumps(
                {
                    "case_id": record.case.case_id,
                    "state": record.state.value,
                    "receipt": record.receipt,
                },
                indent=2,
            )
        )
    elif args.command == "status":
        repository = SQLiteRepository(args.state_db)
        records = (
            (repository.get(args.case_id),)
            if args.case_id
            else repository.list_records()
        )
        print(
            json.dumps(
                [
                    {
                        "case_id": record.case.case_id,
                        "title": record.case.title,
                        "state": record.state.value,
                        "risk": (
                            record.assessment.risk.value if record.assessment else None
                        ),
                        "reviewer": record.reviewer,
                        "receipt": record.receipt,
                    }
                    for record in records
                    if record is not None
                ],
                indent=2,
            )
        )
    elif args.command == "verify-audit":
        audit = AuditLog(args.audit)
        valid = audit.verify()
        print(json.dumps({"audit": str(args.audit), "valid": valid}, indent=2))
        if not valid:
            raise SystemExit(1)
    elif args.command == "serve":
        serve_dashboard(
            host=args.host,
            port=args.port,
            state_db=args.state_db,
            audit_path=args.audit,
            approved_dir=args.approved_dir,
        )
