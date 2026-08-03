from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from .assurance import AssuranceReport, import_sarif


class ScannerError(RuntimeError):
    pass


class ScannerUnavailable(ScannerError):
    pass


@dataclass(frozen=True)
class ScannerExecution:
    scanner: str
    executable: str
    output: Path
    return_code: int
    network_isolated: bool
    duration_ms: float


class ScannerRunner:
    """Run fixed scanner commands without a shell.

    Network isolation can be made mandatory for every scanner process.
    """

    def __init__(self, *, require_network_isolation: bool = True) -> None:
        self.require_network_isolation = require_network_isolation
        self.bwrap = shutil.which("bwrap")
        if require_network_isolation and not self.bwrap:
            raise ScannerUnavailable(
                "bubblewrap is required to enforce scanner network isolation"
            )
        if require_network_isolation:
            usable, diagnostic = self._check_network_sandbox(self.bwrap)
            if not usable:
                raise ScannerUnavailable(
                    "bubblewrap is installed but network isolation is unavailable: "
                    f"{diagnostic}"
                )

    def semgrep(
        self,
        repository: Path,
        output_dir: Path,
        rules: Path,
        *,
        timeout_seconds: int = 300,
    ) -> ScannerExecution:
        executable = self._required_executable("semgrep")
        output = output_dir / "semgrep.sarif"
        command = [
            executable,
            "scan",
            "--config",
            str(rules.resolve()),
            "--sarif",
            "--output",
            str(output.resolve()),
            "--metrics=off",
            "--disable-version-check",
            str(repository.resolve()),
        ]
        return self._run(
            "semgrep", command, repository, output_dir, output, {0}, timeout_seconds
        )

    def gitleaks(
        self,
        repository: Path,
        output_dir: Path,
        *,
        timeout_seconds: int = 300,
    ) -> ScannerExecution:
        executable = self._required_executable("gitleaks")
        output = output_dir / "gitleaks.sarif"
        command = [
            executable,
            "dir",
            str(repository.resolve()),
            "--redact=100",
            "--no-banner",
            "--no-color",
            "--report-format=sarif",
            f"--report-path={output.resolve()}",
        ]
        return self._run(
            "gitleaks", command, repository, output_dir, output, {0, 1}, timeout_seconds
        )

    def osv(
        self,
        repository: Path,
        output_dir: Path,
        offline_database: Path,
        *,
        timeout_seconds: int = 300,
    ) -> ScannerExecution:
        executable = self._required_executable("osv-scanner")
        if not offline_database.is_dir():
            raise ScannerError("OSV offline database directory does not exist")
        output = output_dir / "osv.sarif"
        command = [
            executable,
            "scan",
            "source",
            "--format=sarif",
            "--offline",
            "--offline-vulnerabilities",
            "--recursive",
            f"--output-file={output.resolve()}",
            str(repository.resolve()),
        ]
        return self._run(
            "osv",
            command,
            repository,
            output_dir,
            output,
            {0, 1},
            timeout_seconds,
            extra_env={"XDG_CACHE_HOME": str(offline_database.resolve())},
        )

    def report(
        self,
        execution: ScannerExecution,
        *,
        engagement_id: str,
        repository_id: str,
    ) -> AssuranceReport:
        return import_sarif(
            execution.output,
            engagement_id=engagement_id,
            repository_id=repository_id,
        )

    @staticmethod
    def preflight() -> dict[str, object]:
        sandbox = shutil.which("bwrap")
        sandbox_usable, sandbox_error = ScannerRunner._check_network_sandbox(sandbox)
        return {
            "network_sandbox": sandbox,
            "network_sandbox_usable": sandbox_usable,
            "network_sandbox_error": sandbox_error,
            "scanners": {
                name: ScannerRunner._find_executable(executable)
                for name, executable in {
                    "semgrep": "semgrep",
                    "gitleaks": "gitleaks",
                    "osv": "osv-scanner",
                }.items()
            },
        }

    @staticmethod
    def _check_network_sandbox(executable: str | None) -> tuple[bool, str | None]:
        if not executable:
            return False, "bubblewrap is not installed"
        try:
            completed = subprocess.run(
                [
                    executable,
                    "--die-with-parent",
                    "--unshare-net",
                    "--ro-bind",
                    "/",
                    "/",
                    "--dev",
                    "/dev",
                    "--proc",
                    "/proc",
                    "--",
                    "/bin/true",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)[-600:]
        if completed.returncode == 0:
            return True, None
        diagnostic = completed.stderr.strip()[-600:] or (
            f"bubblewrap exited with code {completed.returncode}"
        )
        return False, diagnostic

    @staticmethod
    def _required_executable(name: str) -> str:
        executable = ScannerRunner._find_executable(name)
        if not executable:
            raise ScannerUnavailable(f"required scanner is not installed: {name}")
        return executable

    @staticmethod
    def _find_executable(name: str) -> str | None:
        executable = shutil.which(name)
        if executable:
            return executable
        project_local = Path(__file__).resolve().parents[2] / ".tools" / "bin" / name
        return str(project_local) if os.access(project_local, os.X_OK) else None

    def _run(
        self,
        scanner: str,
        command: list[str],
        repository: Path,
        output_dir: Path,
        output: Path,
        accepted_codes: set[int],
        timeout_seconds: int,
        extra_env: dict[str, str] | None = None,
    ) -> ScannerExecution:
        repository = repository.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        scanner_home = output_dir / ".scanner-home"
        scanner_tmp = output_dir / ".scanner-tmp"
        scanner_home.mkdir(exist_ok=True)
        scanner_tmp.mkdir(exist_ok=True)
        env = {
            "HOME": str(scanner_home),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": os.defpath,
            "SEMGREP_SEND_METRICS": "off",
            "SEMGREP_ENABLE_VERSION_CHECK": "0",
            "TMPDIR": str(scanner_tmp),
        }
        env.update(extra_env or {})
        isolated_command = command
        if self.require_network_isolation:
            isolated_command = [
                str(self.bwrap),
                "--die-with-parent",
                "--unshare-net",
                "--ro-bind",
                "/",
                "/",
                "--dev",
                "/dev",
                "--proc",
                "/proc",
                "--bind",
                str(output_dir),
                str(output_dir),
                "--chdir",
                str(repository),
                "--",
                *command,
            ]
        started = perf_counter()
        try:
            completed = subprocess.run(
                isolated_command,
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScannerError(f"{scanner} exceeded its time limit") from exc
        if completed.returncode not in accepted_codes:
            diagnostic = completed.stderr.strip()[-1200:]
            raise ScannerError(
                f"{scanner} failed with exit code {completed.returncode}: {diagnostic}"
            )
        if not output.is_file():
            raise ScannerError(f"{scanner} did not produce a SARIF report")
        return ScannerExecution(
            scanner=scanner,
            executable=command[0],
            output=output,
            return_code=completed.returncode,
            network_isolated=self.require_network_isolation,
            duration_ms=(perf_counter() - started) * 1000,
        )
