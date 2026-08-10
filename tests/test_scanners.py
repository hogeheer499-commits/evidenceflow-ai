import json
from pathlib import Path

import pytest

from evidenceflow.scanners import ScannerError, ScannerExecution, ScannerRunner


def test_preflight_has_fixed_scanner_names() -> None:
    preflight = ScannerRunner.preflight()
    assert set(preflight["scanners"]) == {"semgrep", "gitleaks", "osv"}
    assert isinstance(preflight["network_sandbox_usable"], bool)
    assert "network_sandbox_error" in preflight


def test_scanner_report_imports_existing_sarif(tmp_path: Path) -> None:
    path = tmp_path / "result.sarif"
    path.write_text(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "test"}},
                        "results": [
                            {
                                "ruleId": "test.rule",
                                "level": "error",
                                "message": {"text": "Synthetic result"},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    execution = ScannerExecution("test", "test", path, 0, True, 12.0)
    report = ScannerRunner(require_network_isolation=False).report(
        execution, engagement_id="eng", repository_id="repo"
    )
    assert report.observations[0].severity == "high"


def test_osv_requires_existing_offline_database(tmp_path: Path) -> None:
    runner = ScannerRunner(require_network_isolation=False)
    runner._required_executable = lambda name: "/usr/bin/true"
    with pytest.raises(ScannerError, match="database directory"):
        runner.osv(tmp_path, tmp_path / "out", tmp_path / "missing")
