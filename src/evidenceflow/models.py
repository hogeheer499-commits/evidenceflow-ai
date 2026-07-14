from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowState(StrEnum):
    RECEIVED = "received"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    text: str


@dataclass(frozen=True)
class EvidenceCase:
    case_id: str
    title: str
    sources: tuple[EvidenceSource, ...]

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Citation:
    source_id: str
    quote: str


@dataclass(frozen=True)
class Assessment:
    risk: Risk
    summary: str
    labels: tuple[str, ...]
    citations: tuple[Citation, ...]
    confidence: float

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class WorkflowRecord:
    case: EvidenceCase
    state: WorkflowState = WorkflowState.RECEIVED
    assessment: Assessment | None = None
    reviewer: str | None = None
    receipt: str | None = None
