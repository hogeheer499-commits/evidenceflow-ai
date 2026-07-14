from __future__ import annotations

from .models import Assessment, EvidenceCase

MAX_SOURCE_CHARS = 100_000


class ValidationError(ValueError):
    pass


def validate_case(case: EvidenceCase) -> None:
    if not case.case_id.strip():
        raise ValidationError("case_id is required")
    if not case.title.strip():
        raise ValidationError("title is required")
    if not case.sources:
        raise ValidationError("at least one evidence source is required")
    ids = [source.source_id for source in case.sources]
    if any(not source_id.strip() for source_id in ids):
        raise ValidationError("source_id is required")
    if len(ids) != len(set(ids)):
        raise ValidationError("source_id values must be unique")
    if any(not source.text.strip() for source in case.sources):
        raise ValidationError("evidence text cannot be empty")
    if sum(len(source.text) for source in case.sources) > MAX_SOURCE_CHARS:
        raise ValidationError("evidence exceeds the configured size limit")


def validate_assessment(case: EvidenceCase, assessment: Assessment) -> None:
    if not assessment.summary.strip():
        raise ValidationError("assessment summary is required")
    if not 0.0 <= assessment.confidence <= 1.0:
        raise ValidationError("confidence must be between 0 and 1")
    if not assessment.citations:
        raise ValidationError("at least one grounded citation is required")
    sources = {source.source_id: source.text for source in case.sources}
    for citation in assessment.citations:
        if citation.source_id not in sources:
            raise ValidationError(f"unknown citation source: {citation.source_id}")
        if (
            not citation.quote.strip()
            or citation.quote not in sources[citation.source_id]
        ):
            raise ValidationError(
                f"citation quote does not resolve in source: {citation.source_id}"
            )
