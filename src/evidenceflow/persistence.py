from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    Assessment,
    Citation,
    EvidenceCase,
    EvidenceSource,
    Risk,
    WorkflowRecord,
    WorkflowState,
)


class PersistenceError(RuntimeError):
    pass


class SQLiteRepository:
    """Durable single-node workflow state for permissioned pilots."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_records (
                    case_id TEXT PRIMARY KEY,
                    case_fingerprint TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA temp_store=MEMORY")
        return connection

    def get(self, case_id: str) -> WorkflowRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM workflow_records WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return _decode_record(row[0]) if row else None

    def save(self, record: WorkflowRecord) -> None:
        payload = _encode_record(record)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT case_fingerprint FROM workflow_records WHERE case_id = ?",
                (record.case.case_id,),
            ).fetchone()
            if existing and existing[0] != record.case.fingerprint:
                raise PersistenceError(
                    "case_id already exists with a different evidence fingerprint"
                )
            connection.execute(
                """
                INSERT INTO workflow_records (
                    case_id, case_fingerprint, payload, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    record.case.case_id,
                    record.case.fingerprint,
                    payload,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def list_records(self) -> tuple[WorkflowRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM workflow_records ORDER BY updated_at DESC"
            ).fetchall()
        return tuple(_decode_record(row[0]) for row in rows)


@dataclass
class DirectoryPublisher:
    """Idempotently export an approved assessment to a local handoff directory."""

    destination: Path

    def publish(self, record: WorkflowRecord, idempotency_key: str) -> str:
        if record.assessment is None or not record.reviewer:
            raise PersistenceError("approved assessment and reviewer are required")
        self.destination.mkdir(parents=True, exist_ok=True)
        slug = hashlib.sha256(record.case.case_id.encode()).hexdigest()[:20]
        output = self.destination / f"approved-{slug}.json"
        payload = {
            "version": 1,
            "product": "Kleine Koe EvidenceFlow — Sovereign OSS Assurance",
            "case": asdict(record.case),
            "assessment": asdict(record.assessment),
            "reviewer": record.reviewer,
            "approved_exported_at": datetime.now(UTC).isoformat(),
            "idempotency_key": idempotency_key,
        }
        if output.exists():
            existing = json.loads(output.read_text(encoding="utf-8"))
            if existing.get("idempotency_key") != idempotency_key:
                raise PersistenceError("export path contains a different assessment")
            return f"file:{output.resolve()}"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.destination, prefix=".evidenceflow-", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
        return f"file:{output.resolve()}"


def _encode_record(record: WorkflowRecord) -> str:
    return json.dumps(asdict(record), default=str, sort_keys=True)


def _decode_record(payload: str) -> WorkflowRecord:
    raw = json.loads(payload)
    case_raw = raw["case"]
    case = EvidenceCase(
        case_id=case_raw["case_id"],
        title=case_raw["title"],
        sources=tuple(EvidenceSource(**source) for source in case_raw["sources"]),
    )
    assessment_raw = raw.get("assessment")
    assessment = None
    if assessment_raw:
        assessment = Assessment(
            risk=Risk(assessment_raw["risk"]),
            summary=assessment_raw["summary"],
            labels=tuple(assessment_raw["labels"]),
            citations=tuple(
                Citation(**citation) for citation in assessment_raw["citations"]
            ),
            confidence=float(assessment_raw["confidence"]),
        )
    return WorkflowRecord(
        case=case,
        state=WorkflowState(raw["state"]),
        assessment=assessment,
        reviewer=raw.get("reviewer"),
        receipt=raw.get("receipt"),
    )
